"""Shared legacy MIDI helpers for the Length and Pattern actions.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import re

from lib.midi_chunk import SUPPORTED_PPQ, parse_midi_chunk, sha256_text


_SOFFS_RE = re.compile(
    r'^\s*SOFFS\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)'
    r'(?:\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?))?',
    re.MULTILINE)


class MidiActionError(Exception):
    pass


def load_first_midi_context(host, track):
    """Load the first MIDI item on a track and validate its take mapping."""
    for index in range(host.item_count(track)):
        item = host.get_item(track, index)
        chunk = host.read_item_chunk(item)
        if '<SOURCE MIDI' not in chunk:
            continue
        take = host.active_take(item)
        if not take:
            raise MidiActionError('The first MIDI item has no active take.')
        rate = host.take_play_rate(take)
        if abs(rate - 1.0) > 1e-9:
            raise MidiActionError(
                'The first MIDI item has an unsupported play rate (%g).' %
                rate)
        parsed = parse_midi_chunk(chunk)
        if parsed.ppq != SUPPORTED_PPQ:
            raise MidiActionError(
                'The MIDI source uses %d PPQ; this port currently requires '
                '%d PPQ.' % (parsed.ppq, SUPPORTED_PPQ))
        position = host.item_position(item)
        start_qn = host.time_to_qn(position)
        offset_seconds = host.take_start_offset(take)
        match = _SOFFS_RE.search(chunk)
        if match and match.group(2) is not None:
            offset_qn = float(match.group(2))
        else:
            offset_qn = host.time_to_qn(position + offset_seconds) - start_qn
        return {
            'item': item,
            'take': take,
            'chunk': chunk,
            'fingerprint': sha256_text(chunk),
            'parsed': parsed,
            'position': position,
            'end': position + host.item_length(item),
            'start_qn': start_qn,
            'offset_qn': offset_qn,
        }
    raise MidiActionError('No MIDI item was found on the selected track.')


def project_time_to_tick(host, context, seconds):
    source_qn = (host.time_to_qn(seconds) - context['start_qn'] +
                 context['offset_qn'])
    return int(round(source_qn * context['parsed'].ppq))


def tick_to_project_time(host, context, tick):
    project_qn = (context['start_qn'] - context['offset_qn'] +
                  float(tick) / context['parsed'].ppq)
    return host.qn_to_time(project_qn)


def selected_tick_scope(host, context, require_selection=False):
    start, end = host.time_selection()
    if start is None:
        if require_selection:
            raise MidiActionError('Set a time selection first.')
        start, end = context['position'], context['end']
    elif require_selection and (start < context['position'] - 0.001 or
                                end > context['end'] + 0.001):
        raise MidiActionError(
            'The time selection must be inside the first MIDI item.')
    else:
        start = max(start, context['position'])
        end = min(end, context['end'])
        if end <= start:
            raise MidiActionError(
                'The time selection does not overlap the first MIDI item.')
    return (project_time_to_tick(host, context, start),
            project_time_to_tick(host, context, end), start, end)


def track_display_name(host, track):
    for index in range(host.track_count()):
        if host.get_track(index) == track:
            return host.track_name(track, index)
    return ''
