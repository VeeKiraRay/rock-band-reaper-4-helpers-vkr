"""Capture, find, replace, and tile MIDI patterns through legacy chunks.

Modern counterpart:
rock_band_general_helper_vkr/actions_midi_replace.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import math

from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources
from .actions_midi_common import (
    MidiActionError,
    load_first_midi_context,
    project_time_to_tick,
    selected_tick_scope,
    tick_to_project_time,
    track_display_name,
)


DIFFICULTY_LABELS = ('All', 'Expert', 'Hard', 'Medium', 'Easy')
DIFF_TIER_RANGE = {
    1: (96, 100), 2: (84, 88), 3: (72, 76), 4: (60, 64),
}
TIERED_TRACK_NAMES = frozenset((
    'PART DRUMS', 'PART GUITAR', 'PART BASS', 'PART KEYS'))
FIXED_RANGE_TRACK_NAMES = {
    'PART VOCALS': (36, 84), 'HARM1': (36, 84),
    'HARM2': (36, 84), 'HARM3': (36, 84),
}


def get_pattern_pitch_range(track_name, difficulty_index):
    name = (track_name or '').strip().upper()
    if name in TIERED_TRACK_NAMES:
        return DIFF_TIER_RANGE.get(int(difficulty_index), (60, 100))
    if name in FIXED_RANGE_TRACK_NAMES:
        return FIXED_RANGE_TRACK_NAMES[name]
    if name.startswith('PART REAL_KEYS') or name.startswith('PART KEYS_ANIM'):
        return 48, 72
    return 0, 127


def new_pattern_state():
    return {
        'search_notes': None, 'search_label': '', 'search_duration': 0,
        'search_step': 0, 'replace_notes': None, 'replace_label': '',
        'replace_duration': 0,
    }


def reset_pattern_state(state):
    state.clear()
    state.update(new_pattern_state())


def _read_pattern(parsed, start_tick, end_tick, lo, hi):
    notes = []
    for note in parsed.notes():
        if start_tick <= note.start_tick < end_tick and lo <= note.pitch <= hi:
            notes.append({
                'rel_start': note.start_tick - start_tick,
                'rel_end': note.end_tick - start_tick,
                'pitch': note.pitch,
            })
    notes.sort(key=lambda value: (value['rel_start'], value['pitch']))
    return notes


def _pattern_label(host, start_seconds, end_seconds, note_count):
    start_measure = host.measure_at(start_seconds)
    end_measure = host.measure_at(end_seconds)
    if start_measure is not None and end_measure is not None:
        count = max(0, end_measure - start_measure)
        return 'M%d-M%d (%d measure%s with %d note%s)' % (
            start_measure, max(start_measure, end_measure - 1), count,
            '' if count == 1 else 's', note_count,
            '' if note_count == 1 else 's')
    return '%.3f-%.3f seconds (%d note%s)' % (
        start_seconds, end_seconds, note_count,
        '' if note_count == 1 else 's')


def capture_pattern(host, track, difficulty_index, state, kind):
    context = load_first_midi_context(host, track)
    start_tick, end_tick, start_s, end_s = selected_tick_scope(
        host, context, require_selection=True)
    if end_tick - start_tick < 1:
        raise MidiActionError('The time selection is too short.')
    lo, hi = get_pattern_pitch_range(
        track_display_name(host, track), difficulty_index)
    notes = _read_pattern(context['parsed'], start_tick, end_tick, lo, hi)
    duration = end_tick - start_tick
    label = _pattern_label(host, start_s, end_s, len(notes))
    if kind == 'search':
        start_measure = host.measure_at(start_s)
        end_measure = host.measure_at(end_s)
        measure_count = ((end_measure - start_measure)
                         if start_measure is not None and
                         end_measure is not None else 0)
        state['search_notes'] = notes
        state['search_duration'] = duration
        state['search_step'] = (int(round(float(duration) / measure_count))
                                if measure_count > 0 else duration)
        state['search_label'] = label
        return 'Search pattern set.', label
    if kind != 'replace':
        raise MidiActionError('Unknown pattern capture type.')
    state['replace_notes'] = notes
    state['replace_duration'] = duration
    state['replace_label'] = label
    return 'Replace pattern set.', label


def _patterns_match(expected, candidate):
    if len(expected) != len(candidate):
        return False
    for left, right in zip(expected, candidate):
        if left['pitch'] != right['pitch']:
            return False
        if abs(left['rel_start'] - right['rel_start']) > 0.5:
            return False
    return True


def _scan_matches(parsed, scope_start, scope_end, lo, hi, state):
    duration = int(state['search_duration'])
    step = int(state['search_step'] or duration)
    if duration <= 0 or step <= 0:
        raise MidiActionError('The Search pattern has an invalid duration.')
    matches = []
    window = int(scope_start)
    while window + duration <= scope_end:
        candidate = _read_pattern(
            parsed, window, window + duration, lo, hi)
        if _patterns_match(state['search_notes'], candidate):
            matches.append(window)
            window += duration
        else:
            window += step
    return matches


def find_pattern_matches(host, track, difficulty_index, state):
    if state.get('search_notes') is None:
        raise MidiActionError('Set a Search pattern first.')
    if not state['search_notes']:
        raise MidiActionError('The Search pattern has 0 notes.')
    context = load_first_midi_context(host, track)
    scope_start, scope_end, unused_s, unused_e = selected_tick_scope(
        host, context)
    lo, hi = get_pattern_pitch_range(
        track_display_name(host, track), difficulty_index)
    return context, lo, hi, _scan_matches(
        context['parsed'], scope_start, scope_end, lo, hi, state)


def _absolute_replacements(pattern, window_start):
    return [{
        'start_tick': window_start + note['rel_start'],
        'end_tick': window_start + note['rel_end'],
        'pitch': note['pitch'], 'velocity': 100, 'channel': 0,
    } for note in pattern]


def _apply_windows(host, context, lo, hi, starts, duration, pattern,
                   undo_description):
    if not starts:
        return 0
    verify_unshared_pool_sources(host, [context])
    windows = [{
        'start_tick': start, 'end_tick': start + duration,
        'notes': _absolute_replacements(pattern, start),
    } for start in starts]
    expected = context['parsed'].with_replaced_note_windows(lo, hi, windows)
    return apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'expected': expected, 'fingerprint': context['fingerprint'],
    }], undo_description)


def replace_all(host, track, difficulty_index, state):
    if state.get('replace_notes') is None:
        raise MidiActionError('Set a Replace pattern first.')
    if abs(state['search_duration'] - state['replace_duration']) > 0.5:
        raise MidiActionError(
            'Search and Replace patterns must cover the same duration.')
    context, lo, hi, matches = find_pattern_matches(
        host, track, difficulty_index, state)
    if not matches:
        return 'No matches found.', 'No project changes were made.'
    count = len(matches)
    _apply_windows(
        host, context, lo, hi, matches, int(state['search_duration']),
        state['replace_notes'], 'Pattern Replace: %d replacement%s' %
        (count, '' if count == 1 else 's'))
    return ('Replaced %d instance%s.' %
            (count, '' if count == 1 else 's'),
            'Replaced the captured pattern at %d matching location%s.' %
            (count, '' if count == 1 else 's'))


def fill_range(host, track, difficulty_index, state):
    if state.get('replace_notes') is None:
        raise MidiActionError('Set a Replace pattern first.')
    context = load_first_midi_context(host, track)
    start_tick, end_tick, unused_s, unused_e = selected_tick_scope(
        host, context, require_selection=True)
    duration = int(state['replace_duration'])
    count = int(math.floor(float(end_tick - start_tick) / duration))
    if count < 1:
        raise MidiActionError(
            'The time selection is shorter than the Replace pattern.')
    starts = [start_tick + index * duration for index in range(count)]
    lo, hi = get_pattern_pitch_range(
        track_display_name(host, track), difficulty_index)
    _apply_windows(host, context, lo, hi, starts, duration,
                   state['replace_notes'],
                   'Pattern Replace: fill range (%d slot%s)' %
                   (count, '' if count == 1 else 's'))
    return ('Filled %d slot%s.' %
            (count, '' if count == 1 else 's'),
            'Tiled the Replace pattern across %d complete slot%s.' %
            (count, '' if count == 1 else 's'))


def list_matches(host, track, difficulty_index, state):
    context, unused_lo, unused_hi, matches = find_pattern_matches(
        host, track, difficulty_index, state)
    if not matches:
        return 'No matches found.', 'No Search-pattern matches were found.'
    lines = ['%d match%s found:' %
             (len(matches), '' if len(matches) == 1 else 'es'), '']
    for index, tick in enumerate(matches):
        seconds = tick_to_project_time(host, context, tick)
        minutes = int(seconds // 60)
        remainder = seconds - minutes * 60
        lines.append('%d. %d:%06.3f' % (index + 1, minutes, remainder))
    return ('Listed %d match%s.' %
            (len(matches), '' if len(matches) == 1 else 'es'),
            '\n'.join(lines))


def go_to_match(host, track, difficulty_index, state, direction):
    context, unused_lo, unused_hi, matches = find_pattern_matches(
        host, track, difficulty_index, state)
    cursor_tick = project_time_to_tick(host, context, host.cursor_position())
    epsilon = 0.5
    anchor = cursor_tick
    duration = int(state['search_duration'])
    if direction < 0:
        containing = [start for start in matches
                      if cursor_tick >= start - epsilon and
                      cursor_tick < start + duration]
        if containing:
            anchor = max(containing)
        candidates = [start for start in matches if start < anchor - epsilon]
        best = max(candidates) if candidates else None
    else:
        candidates = [start for start in matches
                      if start > cursor_tick + epsilon]
        best = min(candidates) if candidates else None
    if best is None:
        label = 'previous' if direction < 0 else 'next'
        return 'No %s instance found.' % label, 'The edit cursor was not moved.'
    host.set_cursor_position(tick_to_project_time(host, context, best))
    label = 'previous' if direction < 0 else 'next'
    return 'Moved to %s match.' % label, 'The edit cursor was moved.'

