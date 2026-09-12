"""Text and lyric mutation implementations for :mod:`lib.midi_chunk`.

Python 2.7 compatible.
"""

import base64
import re
import sys

from lib.midi_chunk import MidiChunkError, MidiEvent, _EXTENDED_EVENT_RE


PYTHON_3 = sys.version_info[0] >= 3
_EXTENDED_SUMMARY_RE = re.compile(
    r'^\s+0(\s+0\s+0\s+)[+-]?\d+(?:\s+.*)?$')


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
    if not PYTHON_3:
        return value
    try:
        return value.decode('utf-8')
    except UnicodeDecodeError:
        return value.decode('latin-1')


def _one_byte(value):
    if PYTHON_3:
        return bytes(bytearray([value]))
    return chr(value)


def safe_extended_summary(payload):
    """Return REAPER's readable event summary for simple ASCII payloads."""
    for value in bytearray(payload):
        if value < 0x20 or value > 0x7e or value in (0x22, 0x5c):
            return None
    text = _bytes_as_text(payload)
    if not text or any(character.isspace() for character in text):
        return '"%s"' % text
    return text


def with_inserted_meta_event(parsed, tick, meta_type, payload):
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
    for event in parsed.events:
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
    summary = safe_extended_summary(payload)
    if summary_prefix is not None and summary is not None:
        header_tail = '%s%d %s' % (summary_prefix, meta_type, summary)
    ordinal = max([event.ordinal for event in parsed.events] or [-1]) + 1
    raw_lines = [
        '%s<%s 0 0%s%s' % (
            indent, marker, header_tail, parsed.newline),
        '%s%s%s' % (payload_indent, encoded, parsed.newline),
        '%s>%s' % (close_indent, parsed.newline),
    ]
    inserted = MidiEvent('extended', raw_lines, 0, int(tick), ordinal)
    inserted.meta_type = int(meta_type)
    inserted.meta_payload_bytes = payload
    inserted.meta_payload = _bytes_as_text(payload)
    inserted.inserted = True
    same_tick_short_ordinals = [
        event.ordinal for event in parsed.events
        if event.absolute_tick == int(tick) and event.kind == 'short']
    if same_tick_short_ordinals:
        inserted.render_order = min(same_tick_short_ordinals) - 0.5
    return parsed._render_mutated_events(
        [event.clone() for event in parsed.events] + [inserted])


def with_replaced_meta_events(parsed, start_tick, end_tick, replacements,
                              meta_type=0x01):
    start_tick = int(start_tick)
    end_tick = int(end_tick)
    meta_type = int(meta_type)
    if start_tick < 0 or end_tick <= start_tick:
        raise MidiChunkError('Meta-event replacement range is invalid.')
    if meta_type not in (0x01, 0x05):
        raise MidiChunkError('Only FF 01 text and FF 05 lyric are supported.')
    kept = [event.clone() for event in parsed.events
            if not (event.kind == 'extended' and
                    event.meta_type == meta_type and
                    start_tick <= event.absolute_tick < end_tick)]
    chunk = parsed._render_mutated_events(kept)
    for replacement in sorted(
            replacements, key=lambda value: int(value['tick'])):
        tick = int(replacement['tick'])
        if not start_tick <= tick < end_tick:
            raise MidiChunkError(
                'Replacement meta event is outside the target range.')
        current = parsed.__class__(chunk)
        chunk = with_inserted_meta_event(
            current, tick, meta_type, replacement['payload'])
    return chunk


def with_replaced_meta_event_windows(parsed, windows, replacements,
                                     meta_type=0x01, payloads=None):
    meta_type = int(meta_type)
    if meta_type not in (0x01, 0x05):
        raise MidiChunkError('Only FF 01 text and FF 05 lyric are supported.')
    ordered_windows = sorted((int(start), int(end))
                             for start, end in windows)
    previous_end = None
    for start_tick, end_tick in ordered_windows:
        if start_tick < 0 or end_tick <= start_tick:
            raise MidiChunkError('Meta-event replacement window is invalid.')
        if previous_end is not None and start_tick < previous_end:
            raise MidiChunkError('Meta-event replacement windows overlap.')
        previous_end = end_tick
    payloads = frozenset(payloads) if payloads is not None else None

    def should_remove(event):
        if event.kind != 'extended' or event.meta_type != meta_type:
            return False
        if payloads is not None and event.meta_payload not in payloads:
            return False
        return any(start <= event.absolute_tick < end
                   for start, end in ordered_windows)

    kept = [event.clone() for event in parsed.events
            if not should_remove(event)]
    chunk = parsed._render_mutated_events(kept)
    for replacement in sorted(
            replacements, key=lambda value: int(value['tick'])):
        tick = int(replacement['tick'])
        if not any(start <= tick < end for start, end in ordered_windows):
            raise MidiChunkError(
                'Replacement meta event is outside its windows.')
        current = parsed.__class__(chunk)
        chunk = with_inserted_meta_event(
            current, tick, meta_type, replacement['payload'])
    return chunk
