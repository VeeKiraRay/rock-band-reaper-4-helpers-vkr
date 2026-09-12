"""Loss-preserving parser for REAPER 4.20 MIDI item-state chunks.

The parser keeps every source line byte-for-byte. Read-only parsing and exact
serialization tolerate unknown records. Mutation is deliberately stricter: it
is allowed only when every line in the MIDI event stream is a supported E/e or
X/x record and the source declares 480 ticks per quarter note.

Python 2.7 compatible.
"""

from __future__ import print_function

import base64
import copy
import re
import sys

from lib.midi_chunk_verification import (
    first_difference, midi_chunks_semantically_equivalent, sha256_text,
)


SUPPORTED_PPQ = 480
CODEC_REVISION = 6
PYTHON_3 = sys.version_info[0] >= 3

_SHORT_EVENT_RE = re.compile(
    r'^(\s*)([Ee])(\s+)([+-]?\d+)(\s+)([0-9A-Fa-f]{2})'
    r'(\s+)([0-9A-Fa-f]{2})(\s+)([0-9A-Fa-f]{2})(.*?)(\r?\n)?$')
_EXTENDED_EVENT_RE = re.compile(
    r'^(\s*)(<([Xx]))(\s+)([+-]?\d+)(.*?)(\r?\n)?$')
_HASDATA_RE = re.compile(r'^\s*HASDATA\s+\S+\s+(\d+)(?:\s|$)')
_POOLED_EVENTS_RE = re.compile(
    r'^\s*POOLEDEVTS\s+(\{[0-9A-Fa-f-]+\})\s*$')
_SOURCE_GUID_RE = re.compile(
    r'^\s*GUID\s+(\{[0-9A-Fa-f-]+\})\s*$')
_CCINTERP_RE = re.compile(r'^\s*CCINTERP\s+[+-]?\d+\s*$')
_CHASE_CC_TAKEOFFS_RE = re.compile(
    r'^\s*CHASE_CC_TAKEOFFS\s+[+-]?\d+\s*$')


class MidiChunkError(Exception):
    pass


def _bytes_as_text(value):
    """Expose decoded MIDI text consistently as str on Python 2 and 3."""
    if not PYTHON_3:
        return value
    try:
        return value.decode('utf-8')
    except UnicodeDecodeError:
        # Preserve every byte for legacy/unknown project encodings. Choosing
        # the production encoding for non-ASCII text is a later compatibility
        # decision; ASCII probes are unaffected by this fallback.
        return value.decode('latin-1')


def _is_open_line(stripped):
    return stripped.startswith('<') and stripped != '>'


def _find_matching_close(lines, start):
    depth = 0
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if _is_open_line(stripped):
            depth += 1
        elif stripped == '>':
            depth -= 1
            if depth == 0:
                return index
    raise MidiChunkError('Unterminated chunk block at line %d.' % (start + 1))


def _replace_short_delta(raw_lines, delta):
    match = _SHORT_EVENT_RE.match(raw_lines[0])
    if not match:
        raise MidiChunkError('Short event header became unparsable.')
    groups = list(match.groups())
    groups[3] = str(int(delta))
    return [''.join(part or '' for part in groups)]


def _replace_extended_delta(raw_lines, delta):
    match = _EXTENDED_EVENT_RE.match(raw_lines[0])
    if not match:
        raise MidiChunkError('Extended event header became unparsable.')
    header = '%s%s%s%s%s%s' % (
        match.group(1) or '',
        match.group(2) or '',
        match.group(4) or '',
        str(int(delta)),
        match.group(6) or '',
        match.group(7) or '')
    return [header] + raw_lines[1:]


class RawRecord(object):
    def __init__(self, raw_lines, reason):
        self.raw_lines = list(raw_lines)
        self.reason = reason
        self.role = None

    def render(self):
        return ''.join(self.raw_lines)


class MidiEvent(object):
    def __init__(self, kind, raw_lines, delta, absolute_tick, ordinal):
        self.kind = kind
        self.raw_lines = list(raw_lines)
        self.delta = int(delta)
        self.absolute_tick = int(absolute_tick)
        self.ordinal = int(ordinal)
        self.selected = False
        self.status = None
        self.channel = None
        self.data1 = None
        self.data2 = None
        self.meta_type = None
        self.meta_payload = None
        self.meta_payload_bytes = None
        self.decode_error = None
        self.inserted = False

    def clone(self):
        return copy.deepcopy(self)

    def render(self, delta=None):
        if delta is None:
            return ''.join(self.raw_lines)
        if self.kind == 'short':
            return ''.join(_replace_short_delta(self.raw_lines, delta))
        if self.kind == 'extended':
            return ''.join(_replace_extended_delta(self.raw_lines, delta))
        raise MidiChunkError('Cannot render event kind %r.' % self.kind)

    def is_note_on(self):
        return (self.kind == 'short' and self.status is not None and
                self.status & 0xF0 == 0x90 and self.data2 != 0)

    def is_note_off(self):
        if self.kind != 'short' or self.status is None:
            return False
        return ((self.status & 0xF0 == 0x80) or
                (self.status & 0xF0 == 0x90 and self.data2 == 0))


class MidiNote(object):
    def __init__(self, on_event, off_event, overlapping):
        self.on_event = on_event
        self.off_event = off_event
        self.start_tick = on_event.absolute_tick
        self.end_tick = off_event.absolute_tick
        self.channel = on_event.channel
        self.pitch = on_event.data1
        self.velocity = on_event.data2
        self.overlapping_same_pitch = bool(overlapping)

    @property
    def length(self):
        return self.end_tick - self.start_tick


class MidiChunk(object):
    def __init__(self, chunk):
        if not isinstance(chunk, str):
            raise MidiChunkError('Chunk must be a byte string.')
        self.original = chunk
        self.lines = chunk.splitlines(True)
        if chunk and not self.lines:
            self.lines = [chunk]
        self.newline = '\r\n' if '\r\n' in chunk else '\n'
        self.source_start = None
        self.source_end = None
        self.hasdata_index = None
        self.event_end_index = None
        self.ppq = None
        self.records = []
        self.events = []
        self.unsupported_records = []
        self.source_metadata_records = []
        self.pool_guid = None
        self.source_guid = None
        self._parse()

    def _parse(self):
        source_candidates = []
        for index, line in enumerate(self.lines):
            if line.strip().startswith('<SOURCE MIDI'):
                source_candidates.append(index)
        if not source_candidates:
            raise MidiChunkError('No <SOURCE MIDI block found.')
        if len(source_candidates) != 1:
            raise MidiChunkError(
                'Expected one MIDI source, found %d.' % len(source_candidates))

        self.source_start = source_candidates[0]
        self.source_end = _find_matching_close(self.lines, self.source_start)

        for index in range(self.source_start + 1, self.source_end):
            match = _HASDATA_RE.match(self.lines[index])
            if match:
                if self.hasdata_index is not None:
                    raise MidiChunkError('Multiple HASDATA records found.')
                self.hasdata_index = index
                self.ppq = int(match.group(1))
        if self.hasdata_index is None:
            raise MidiChunkError('MIDI source has no HASDATA record.')

        self.event_end_index = self.source_end
        for index in range(self.hasdata_index + 1, self.source_end):
            if self.lines[index].lstrip().startswith('IGNTEMPO'):
                self.event_end_index = index
                break

        self._parse_records(
            self.hasdata_index + 1, self.event_end_index)
        self._classify_raw_records()

    def _parse_records(self, start, end):
        index = start
        absolute_tick = 0
        ordinal = 0
        while index < end:
            line = self.lines[index]
            short_match = _SHORT_EVENT_RE.match(line)
            if short_match:
                delta = int(short_match.group(4))
                absolute_tick += delta
                event = MidiEvent(
                    'short', [line], delta, absolute_tick, ordinal)
                event.selected = short_match.group(2) == 'e'
                event.status = int(short_match.group(6), 16)
                event.channel = event.status & 0x0F
                event.data1 = int(short_match.group(8), 16)
                event.data2 = int(short_match.group(10), 16)
                self.records.append(event)
                self.events.append(event)
                ordinal += 1
                index += 1
                continue

            extended_match = _EXTENDED_EVENT_RE.match(line)
            if extended_match:
                close_index = index + 1
                while (close_index < end and
                       self.lines[close_index].strip() != '>'):
                    close_index += 1
                if close_index >= end:
                    raise MidiChunkError(
                        'Unterminated extended event at line %d.' % (index + 1))
                raw_lines = self.lines[index:close_index + 1]
                delta = int(extended_match.group(5))
                absolute_tick += delta
                event = MidiEvent(
                    'extended', raw_lines, delta, absolute_tick, ordinal)
                event.selected = extended_match.group(3) == 'x'
                self._decode_extended(event)
                self.records.append(event)
                self.events.append(event)
                ordinal += 1
                index = close_index + 1
                continue

            record = RawRecord([line], 'unsupported event-stream line')
            self.records.append(record)
            index += 1

    def _classify_raw_records(self):
        event_positions = [index for index, record in enumerate(self.records)
                           if isinstance(record, MidiEvent)]
        first_event = min(event_positions) if event_positions else len(self.records)
        last_event = max(event_positions) if event_positions else -1

        for index, record in enumerate(self.records):
            if not isinstance(record, RawRecord):
                continue
            text = ''.join(record.raw_lines).strip()
            pooled_match = _POOLED_EVENTS_RE.match(text)
            guid_match = _SOURCE_GUID_RE.match(text)
            if pooled_match and index < first_event:
                record.role = 'leading_source_metadata'
                self.pool_guid = pooled_match.group(1)
                self.source_metadata_records.append(record)
            elif guid_match and index > last_event:
                record.role = 'trailing_source_metadata'
                self.source_guid = guid_match.group(1)
                self.source_metadata_records.append(record)
            elif ((_CCINTERP_RE.match(text) or
                   _CHASE_CC_TAKEOFFS_RE.match(text)) and
                  (index < first_event or index > last_event)):
                record.role = ('leading_source_metadata'
                               if index < first_event else
                               'trailing_source_metadata')
                self.source_metadata_records.append(record)
            else:
                record.role = 'unsupported'
                if text:
                    self.unsupported_records.append(record)

    def _decode_extended(self, event):
        encoded = ''.join(
            line.strip() for line in event.raw_lines[1:-1] if line.strip())
        try:
            decoded = base64.b64decode(encoded)
            if len(decoded) < 2:
                event.decode_error = 'decoded payload is shorter than 2 bytes'
                return
            value = decoded[1]
            event.meta_type = value if isinstance(value, int) else ord(value)
            event.meta_payload_bytes = decoded[2:]
            event.meta_payload = _bytes_as_text(event.meta_payload_bytes)
        except Exception as exc:
            event.decode_error = '%s: %s' % (
                exc.__class__.__name__, str(exc))

    def serialize_exact(self):
        body = ''.join(record.render() for record in self.records)
        return (''.join(self.lines[:self.hasdata_index + 1]) + body +
                ''.join(self.lines[self.event_end_index:]))

    def exact_roundtrip(self):
        rebuilt = self.serialize_exact()
        return rebuilt == self.original, rebuilt, first_difference(
            self.original, rebuilt)

    def mutation_blockers(self):
        blockers = []
        if self.ppq != SUPPORTED_PPQ:
            blockers.append(
                'source PPQ is %s, required %d' % (self.ppq, SUPPORTED_PPQ))
        if self.unsupported_records:
            excerpts = []
            for record in self.unsupported_records[:3]:
                value = ''.join(record.raw_lines).strip()
                excerpts.append(repr(value[:120]))
            blockers.append('%d unsupported event-stream line(s): %s' %
                            (len(self.unsupported_records),
                             ', '.join(excerpts)))
        decode_errors = [event for event in self.events
                         if event.kind == 'extended' and event.decode_error]
        if decode_errors:
            blockers.append('%d undecodable extended event(s)' %
                            len(decode_errors))
        ok, unused_rebuilt, difference = self.exact_roundtrip()
        if not ok:
            blockers.append('exact round-trip differs at byte %s' % difference)
        return blockers

    def notes(self):
        pending = {}
        notes = []
        for event in self.events:
            if event.is_note_on():
                key = (event.channel, event.data1)
                queue = pending.setdefault(key, [])
                overlapping = bool(queue)
                queue.append((event, overlapping))
            elif event.is_note_off():
                key = (event.channel, event.data1)
                queue = pending.get(key, [])
                if queue:
                    on_event, overlapping = queue.pop(0)
                    if queue:
                        overlapping = True
                    notes.append(MidiNote(on_event, event, overlapping))
        notes.sort(key=lambda note: (
            note.start_tick, note.pitch, note.channel, note.end_tick))
        return notes

    def text_events(self, meta_type=None):
        result = []
        for event in self.events:
            if event.kind != 'extended' or event.decode_error:
                continue
            if meta_type is None or event.meta_type == meta_type:
                result.append(event)
        return result

    def _render_mutated_events(self, events):
        blockers = self.mutation_blockers()
        if blockers:
            raise MidiChunkError('Mutation blocked: %s.' % '; '.join(blockers))
        ordered = sorted(events, key=lambda event: (
            event.absolute_tick,
            getattr(event, 'render_order', event.ordinal)))
        previous_tick = 0
        rendered = []
        for event in ordered:
            if event.absolute_tick < previous_tick:
                raise MidiChunkError('Event ordering produced a negative delta.')
            delta = event.absolute_tick - previous_tick
            rendered.append(event.render(delta))
            previous_tick = event.absolute_tick
        leading = ''.join(
            record.render() for record in self.records
            if isinstance(record, RawRecord) and
            record.role == 'leading_source_metadata')
        trailing = ''.join(
            record.render() for record in self.records
            if isinstance(record, RawRecord) and
            record.role == 'trailing_source_metadata')
        return (''.join(self.lines[:self.hasdata_index + 1]) +
                leading + ''.join(rendered) + trailing +
                ''.join(self.lines[self.event_end_index:]))

    def with_note_end(self, note_index, new_end_tick):
        from lib import midi_chunk_notes
        return midi_chunk_notes.with_note_end(self, note_index, new_end_tick)

    def with_note_ends(self, changes):
        from lib import midi_chunk_notes
        return midi_chunk_notes.with_note_ends(self, changes)

    def with_replaced_note_windows(self, pitch_lo, pitch_hi, windows):
        from lib import midi_chunk_notes
        return midi_chunk_notes.with_replaced_note_windows(
            self, pitch_lo, pitch_hi, windows)

    def with_replaced_notes(self, pitch_lo, pitch_hi, replacements):
        from lib import midi_chunk_notes
        return midi_chunk_notes.with_replaced_notes(
            self, pitch_lo, pitch_hi, replacements)

    def with_inserted_meta_event(self, tick, meta_type, payload):
        from lib import midi_chunk_meta
        return midi_chunk_meta.with_inserted_meta_event(
            self, tick, meta_type, payload)

    def with_replaced_meta_events(self, start_tick, end_tick, replacements,
                                  meta_type=0x01):
        from lib import midi_chunk_meta
        return midi_chunk_meta.with_replaced_meta_events(
            self, start_tick, end_tick, replacements, meta_type)

    def with_replaced_meta_event_windows(self, windows, replacements,
                                         meta_type=0x01, payloads=None):
        from lib import midi_chunk_meta
        return midi_chunk_meta.with_replaced_meta_event_windows(
            self, windows, replacements, meta_type, payloads)


def parse_midi_chunk(chunk):
    return MidiChunk(chunk)
