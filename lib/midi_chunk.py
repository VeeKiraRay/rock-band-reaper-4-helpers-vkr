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
import hashlib
import re
import sys


SUPPORTED_PPQ = 480
CODEC_REVISION = 6
PYTHON_3 = sys.version_info[0] >= 3

_SHORT_EVENT_RE = re.compile(
    r'^(\s*)([Ee])(\s+)([+-]?\d+)(\s+)([0-9A-Fa-f]{2})'
    r'(\s+)([0-9A-Fa-f]{2})(\s+)([0-9A-Fa-f]{2})(.*?)(\r?\n)?$')
_EXTENDED_EVENT_RE = re.compile(
    r'^(\s*)(<([Xx]))(\s+)([+-]?\d+)(.*?)(\r?\n)?$')
_EXTENDED_SUMMARY_RE = re.compile(
    r'^\s+0(\s+0\s+0\s+)[+-]?\d+(?:\s+.*)?$')
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


def _as_bytes(value):
    if PYTHON_3:
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode('utf-8')
    else:
        if isinstance(value, unicode):
            return value.encode('utf-8')
    return value


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


def _one_byte(value):
    if PYTHON_3:
        return bytes(bytearray([value]))
    return chr(value)


def _safe_extended_summary(payload):
    """Return REAPER's readable event summary for simple ASCII payloads."""
    for value in bytearray(payload):
        if value < 0x20 or value > 0x7e or value in (0x22, 0x5c):
            return None
    text = _bytes_as_text(payload)
    if not text or any(character.isspace() for character in text):
        return '"%s"' % text
    return text


def sha256_text(value):
    return hashlib.sha256(_as_bytes(value)).hexdigest()


def first_difference(left, right):
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return index
    if len(left) != len(right):
        return limit
    return None


def _known_extended_header(event):
    """Describe a verified minimal or readable-summary X-event header."""
    match = _EXTENDED_EVENT_RE.match(event.raw_lines[0])
    if not match:
        return None
    tail = match.group(6) or ''
    if re.match(r'^\s+0\s*$', tail):
        style = 'minimal'
    else:
        rich = re.match(
            r'^\s+0\s+0\s+0\s+([+-]?\d+)(?:\s+(.*?))?\s*$', tail)
        if not rich or event.decode_error:
            return None
        if int(rich.group(1)) != event.meta_type:
            return None
        expected_summary = _safe_extended_summary(event.meta_payload_bytes)
        if expected_summary is None or rich.group(2) != expected_summary:
            return None
        style = 'rich'
    return (match.group(1) or '', match.group(3), match.group(4), style)


def midi_chunks_semantically_equivalent(expected, actual):
    """Allow only known redundant X-header normalization.

    This is intentionally not a broad MIDI equivalence test. Everything other
    than a verified minimal/rich extended-event header must remain byte-exact.
    """
    try:
        left = MidiChunk(expected)
        right = MidiChunk(actual)
    except (MidiChunkError, TypeError, ValueError):
        return False
    if left.mutation_blockers() or right.mutation_blockers():
        return False
    if (left.lines[:left.hasdata_index + 1] !=
            right.lines[:right.hasdata_index + 1]):
        return False
    if (left.lines[left.event_end_index:] !=
            right.lines[right.event_end_index:]):
        return False
    if len(left.records) != len(right.records):
        return False

    saw_header_difference = False
    for left_record, right_record in zip(left.records, right.records):
        if isinstance(left_record, RawRecord):
            if (not isinstance(right_record, RawRecord) or
                    left_record.raw_lines != right_record.raw_lines):
                return False
            continue
        if not isinstance(right_record, MidiEvent):
            return False
        if left_record.kind != right_record.kind:
            return False
        if left_record.kind == 'short':
            if left_record.raw_lines != right_record.raw_lines:
                return False
            continue

        left_header = _known_extended_header(left_record)
        right_header = _known_extended_header(right_record)
        if left_header is None or right_header is None:
            return False
        if left_header[:3] != right_header[:3]:
            return False
        if (left_record.delta != right_record.delta or
                left_record.absolute_tick != right_record.absolute_tick or
                left_record.selected != right_record.selected or
                left_record.meta_type != right_record.meta_type or
                left_record.meta_payload_bytes != right_record.meta_payload_bytes or
                left_record.raw_lines[1:] != right_record.raw_lines[1:]):
            return False
        if left_record.raw_lines[0] != right_record.raw_lines[0]:
            saw_header_difference = True
    return saw_header_difference


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
        return self.with_note_ends({int(note_index): int(new_end_tick)})

    def with_note_ends(self, changes):
        """Return a chunk with several paired note-off ticks changed."""
        notes = self.notes()
        events = [event.clone() for event in self.events]
        by_ordinal = dict((event.ordinal, event) for event in events)
        for note_index, new_end_tick in changes.items():
            note_index = int(note_index)
            new_end_tick = int(new_end_tick)
            if note_index < 0 or note_index >= len(notes):
                raise MidiChunkError('Note index is out of range.')
            note = notes[note_index]
            if note.overlapping_same_pitch:
                raise MidiChunkError(
                    'Selected note overlaps another note of the same '
                    'pitch/channel.')
            if new_end_tick <= note.start_tick:
                raise MidiChunkError('New note end must be after its start.')
            target = by_ordinal.get(note.off_event.ordinal)
            if target is None:
                raise MidiChunkError('Could not locate the note-off event.')
            target.absolute_tick = new_end_tick
        return self._render_mutated_events(events)

    def with_replaced_note_windows(self, pitch_lo, pitch_hi, windows):
        """Replace notes starting in selected tick windows.

        Each window is a dictionary containing ``start_tick``, ``end_tick``,
        and a ``notes`` sequence in the same shape accepted by
        :meth:`with_replaced_notes`. Windows must not overlap.
        """
        pitch_lo = int(pitch_lo)
        pitch_hi = int(pitch_hi)
        if pitch_lo < 0 or pitch_hi > 127 or pitch_lo > pitch_hi:
            raise MidiChunkError('Replacement pitch range is invalid.')
        ordered_windows = sorted(windows, key=lambda value: (
            int(value['start_tick']), int(value['end_tick'])))
        previous_end = None
        for window in ordered_windows:
            start_tick = int(window['start_tick'])
            end_tick = int(window['end_tick'])
            if start_tick < 0 or end_tick <= start_tick:
                raise MidiChunkError('Replacement window is invalid.')
            if previous_end is not None and start_tick < previous_end:
                raise MidiChunkError('Replacement windows overlap.')
            previous_end = end_tick

        notes = self.notes()
        paired_ordinals = set()
        for note in notes:
            paired_ordinals.add(note.on_event.ordinal)
            paired_ordinals.add(note.off_event.ordinal)
        unpaired = [
            event for event in self.events
            if (event.is_note_on() or event.is_note_off()) and
            event.ordinal not in paired_ordinals]
        if unpaired:
            raise MidiChunkError(
                'Mutation blocked: MIDI stream has %d unpaired note event(s).'
                % len(unpaired))

        def in_replaced_window(note):
            if not pitch_lo <= note.pitch <= pitch_hi:
                return False
            for window in ordered_windows:
                if (int(window['start_tick']) <= note.start_tick <
                        int(window['end_tick'])):
                    return True
            return False

        remove_ordinals = set()
        for note in notes:
            if in_replaced_window(note):
                remove_ordinals.add(note.on_event.ordinal)
                remove_ordinals.add(note.off_event.ordinal)
        events = [event.clone() for event in self.events
                  if event.ordinal not in remove_ordinals]
        next_ordinal = max([event.ordinal for event in self.events] or [-1]) + 1
        for window in ordered_windows:
            for replacement in window.get('notes', ()):
                start_tick = int(replacement['start_tick'])
                end_tick = int(replacement['end_tick'])
                pitch = int(replacement['pitch'])
                velocity = int(replacement.get('velocity', 100))
                channel = int(replacement.get('channel', 0))
                if start_tick < 0 or end_tick <= start_tick:
                    raise MidiChunkError(
                        'Replacement note has invalid start/end ticks.')
                if not (int(window['start_tick']) <= start_tick <
                        int(window['end_tick'])):
                    raise MidiChunkError(
                        'Replacement note starts outside its window.')
                if not pitch_lo <= pitch <= pitch_hi:
                    raise MidiChunkError(
                        'Replacement note is outside the target pitch range.')
                if not 0 <= pitch <= 127 or not 1 <= velocity <= 127:
                    raise MidiChunkError(
                        'Replacement note pitch or velocity is invalid.')
                if not 0 <= channel <= 15:
                    raise MidiChunkError('Replacement note channel is invalid.')
                on_event = MidiEvent(
                    'short', ['E 0 %02x %02x %02x%s' %
                              (0x90 | channel, pitch, velocity, self.newline)],
                    0, start_tick, next_ordinal)
                on_event.status = 0x90 | channel
                on_event.channel = channel
                on_event.data1 = pitch
                on_event.data2 = velocity
                on_event.inserted = True
                next_ordinal += 1
                off_event = MidiEvent(
                    'short', ['E 0 %02x %02x 00%s' %
                              (0x80 | channel, pitch, self.newline)],
                    0, end_tick, next_ordinal)
                off_event.status = 0x80 | channel
                off_event.channel = channel
                off_event.data1 = pitch
                off_event.data2 = 0
                off_event.inserted = True
                next_ordinal += 1
                events.extend((on_event, off_event))
        return self._render_mutated_events(events)

    def with_replaced_notes(self, pitch_lo, pitch_hi, replacements):
        """Replace a pitch range while preserving every unrelated event.

        Replacement dictionaries use source-local ticks and may optionally
        provide ``velocity`` and ``channel``. New notes are unselected and
        use ordinary note-on/note-off short events.
        """
        pitch_lo = int(pitch_lo)
        pitch_hi = int(pitch_hi)
        if pitch_lo < 0 or pitch_hi > 127 or pitch_lo > pitch_hi:
            raise MidiChunkError('Replacement pitch range is invalid.')

        notes = self.notes()
        paired_ordinals = set()
        for note in notes:
            paired_ordinals.add(note.on_event.ordinal)
            paired_ordinals.add(note.off_event.ordinal)
        unpaired = [
            event for event in self.events
            if (event.is_note_on() or event.is_note_off()) and
            event.ordinal not in paired_ordinals]
        if unpaired:
            raise MidiChunkError(
                'Mutation blocked: MIDI stream has %d unpaired note event(s).'
                % len(unpaired))

        remove_ordinals = set()
        for note in notes:
            if pitch_lo <= note.pitch <= pitch_hi:
                remove_ordinals.add(note.on_event.ordinal)
                remove_ordinals.add(note.off_event.ordinal)
        events = [event.clone() for event in self.events
                  if event.ordinal not in remove_ordinals]

        next_ordinal = max([event.ordinal for event in self.events] or [-1]) + 1
        ordered_replacements = sorted(
            replacements,
            key=lambda value: (int(value['start_tick']),
                               int(value['pitch']),
                               int(value['end_tick'])))
        for replacement in ordered_replacements:
            start_tick = int(replacement['start_tick'])
            end_tick = int(replacement['end_tick'])
            pitch = int(replacement['pitch'])
            velocity = int(replacement.get('velocity', 100))
            channel = int(replacement.get('channel', 0))
            if start_tick < 0 or end_tick <= start_tick:
                raise MidiChunkError(
                    'Replacement note has invalid start/end ticks.')
            if not 0 <= pitch <= 127 or not 1 <= velocity <= 127:
                raise MidiChunkError(
                    'Replacement note pitch or velocity is invalid.')
            if not 0 <= channel <= 15:
                raise MidiChunkError('Replacement note channel is invalid.')

            on_event = MidiEvent(
                'short', ['E 0 %02x %02x %02x%s' %
                          (0x90 | channel, pitch, velocity, self.newline)],
                0, start_tick, next_ordinal)
            on_event.status = 0x90 | channel
            on_event.channel = channel
            on_event.data1 = pitch
            on_event.data2 = velocity
            on_event.inserted = True
            next_ordinal += 1

            off_event = MidiEvent(
                'short', ['E 0 %02x %02x 00%s' %
                          (0x80 | channel, pitch, self.newline)],
                0, end_tick, next_ordinal)
            off_event.status = 0x80 | channel
            off_event.channel = channel
            off_event.data1 = pitch
            off_event.data2 = 0
            off_event.inserted = True
            next_ordinal += 1
            events.extend((on_event, off_event))
        return self._render_mutated_events(events)

    def with_inserted_meta_event(self, tick, meta_type, payload):
        if meta_type not in (0x01, 0x05):
            raise MidiChunkError('Only FF 01 text and FF 05 lyric are supported.')
        if tick < 0:
            raise MidiChunkError('Event tick cannot be negative.')
        payload = _as_bytes(payload)
        encoded = base64.b64encode(
            _one_byte(0xFF) + _one_byte(meta_type) + payload)
        encoded = _bytes_as_text(encoded)

        indent = ''
        payload_indent = '  '
        close_indent = ''
        marker = 'X'
        summary_prefix = None
        found_layout = False
        for event in self.events:
            if event.kind == 'extended':
                match = _EXTENDED_EVENT_RE.match(event.raw_lines[0])
                if match:
                    if not found_layout:
                        indent = match.group(1)
                        marker = match.group(3).upper()
                        if len(event.raw_lines) > 1:
                            payload_indent = re.match(
                                r'^(\s*)', event.raw_lines[1]).group(1)
                        if len(event.raw_lines) > 2:
                            close_indent = re.match(
                                r'^(\s*)', event.raw_lines[-1]).group(1)
                        found_layout = True
                    summary_match = _EXTENDED_SUMMARY_RE.match(
                        match.group(6) or '')
                    if summary_match:
                        summary_prefix = summary_match.group(1)
                        break

        header_tail = ''
        summary = _safe_extended_summary(payload)
        if summary_prefix is not None and summary is not None:
            # Populated REAPER MIDI sources carry a redundant readable summary
            # after the remaining three legacy header fields. Matching it
            # prevents REAPER from normalizing the new line after the write and
            # tripping exact read-back verification.
            header_tail = '%s%d %s' % (summary_prefix, meta_type, summary)

        ordinal = max([event.ordinal for event in self.events] or [-1]) + 1
        raw_lines = [
            '%s<%s 0 0%s%s' % (
                indent, marker, header_tail, self.newline),
            '%s%s%s' % (payload_indent, encoded, self.newline),
            '%s>%s' % (close_indent, self.newline),
        ]
        inserted = MidiEvent(
            'extended', raw_lines, 0, int(tick), ordinal)
        inserted.meta_type = int(meta_type)
        inserted.meta_payload_bytes = payload
        inserted.meta_payload = _bytes_as_text(payload)
        inserted.inserted = True

        # REAPER's MIDI chunk representation places an extended event before
        # a short MIDI event at the same absolute tick. CAT 1.3.0 follows the
        # same convention. Give only the new event a temporary render order so
        # existing events retain their relative byte order.
        same_tick_short_ordinals = [
            event.ordinal for event in self.events
            if event.absolute_tick == int(tick) and event.kind == 'short']
        if same_tick_short_ordinals:
            inserted.render_order = min(same_tick_short_ordinals) - 0.5
        return self._render_mutated_events(
            [event.clone() for event in self.events] + [inserted])

    def with_replaced_meta_events(self, start_tick, end_tick, replacements,
                                  meta_type=0x01):
        """Replace one meta-event type in a half-open source-tick range.

        Replacement dictionaries contain ``tick`` and ``payload``. Notes,
        other meta types, source metadata, and events outside the range remain
        byte-preserved apart from the delta fields required by reordering.
        """
        start_tick = int(start_tick)
        end_tick = int(end_tick)
        meta_type = int(meta_type)
        if start_tick < 0 or end_tick <= start_tick:
            raise MidiChunkError('Meta-event replacement range is invalid.')
        if meta_type not in (0x01, 0x05):
            raise MidiChunkError(
                'Only FF 01 text and FF 05 lyric are supported.')
        kept = [event.clone() for event in self.events
                if not (event.kind == 'extended' and
                        event.meta_type == meta_type and
                        start_tick <= event.absolute_tick < end_tick)]
        chunk = self._render_mutated_events(kept)
        ordered = sorted(replacements, key=lambda value: int(value['tick']))
        for replacement in ordered:
            tick = int(replacement['tick'])
            if not start_tick <= tick < end_tick:
                raise MidiChunkError(
                    'Replacement meta event is outside the target range.')
            chunk = parse_midi_chunk(chunk).with_inserted_meta_event(
                tick, meta_type, replacement['payload'])
        return chunk


def parse_midi_chunk(chunk):
    return MidiChunk(chunk)
