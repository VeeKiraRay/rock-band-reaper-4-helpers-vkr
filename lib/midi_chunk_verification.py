"""Fingerprinting and narrow read-back equivalence for MIDI chunks.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import hashlib
import sys


PYTHON_3 = sys.version_info[0] >= 3


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
    import re
    from lib.midi_chunk import _EXTENDED_EVENT_RE
    from lib.midi_chunk_meta import safe_extended_summary

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
        expected_summary = safe_extended_summary(event.meta_payload_bytes)
        if expected_summary is None or rich.group(2) != expected_summary:
            return None
        style = 'rich'
    return (match.group(1) or '', match.group(3), match.group(4), style)


def midi_chunks_semantically_equivalent(expected, actual):
    """Allow only known redundant X-header normalization.

    Everything other than a verified minimal/rich extended-event header must
    remain byte-exact.
    """
    from lib.midi_chunk import (
        MidiChunk, MidiChunkError, MidiEvent, RawRecord,
    )

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
