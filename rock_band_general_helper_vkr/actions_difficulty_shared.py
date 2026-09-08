"""Shared pure helpers for Difficulty validation and reduction guidance.

Modern counterpart:
rock_band_general_helper_vkr/actions_difficulty_shared.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals


DIFFICULTY_NAMES = {
    'X': 'Expert', 'H': 'Hard', 'M': 'Medium', 'E': 'Easy'}
DIFFICULTY_ORDER = ('X', 'H', 'M', 'E')
ADJACENT_HIGHER = {'H': 'X', 'M': 'H', 'E': 'M'}
NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B')


def format_time(seconds):
    """Format a non-negative project time as minutes and seconds."""
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return '%d:%06.3f' % (minutes, remainder)


def pitch_name(pitch):
    """Return the Rock Band octave name for a MIDI pitch."""
    pitch = max(0, min(127, int(round(pitch))))
    return '%s%d' % (NOTE_NAMES[pitch % 12], pitch // 12 - 2)


def count_notes(events):
    return sum(len(event['pitches']) for event in events)


def charts_are_identical(lower_events, higher_events, lower_lo, higher_lo):
    if len(lower_events) != len(higher_events):
        return False
    for lower, higher in zip(lower_events, higher_events):
        if (abs(lower['s'] - higher['s']) > 0.005 or
                abs(lower['e'] - higher['e']) > 0.005):
            return False
        if len(lower['pitches']) != len(higher['pitches']):
            return False
        for lower_pitch, higher_pitch in zip(
                lower['pitches'], higher['pitches']):
            if ((lower_pitch - lower_lo) !=
                    (higher_pitch - higher_lo)):
                return False
    return True


def check_difficulty_progression(lower_label, higher_label,
                                 lower_events, higher_events,
                                 lower_lo, higher_lo):
    """Return report lines and issue count for adjacent authored tiers."""
    lines = []
    issues = 0
    lower_count = count_notes(lower_events)
    higher_count = count_notes(higher_events)

    if higher_events and lower_events and charts_are_identical(
            lower_events, higher_events, lower_lo, higher_lo):
        lines.append(
            '%s appears to be an unchanged copy of %s (%d identical notes, '
            'same timing and shape) - some reduction is expected between '
            'difficulties' % (lower_label, higher_label, lower_count))
        issues += 1

    if higher_count:
        if lower_count < higher_count:
            lines.append('%s has %d notes and %s has %d notes: OK' % (
                higher_label, higher_count, lower_label, lower_count))
        else:
            lines.append(
                '%s has %d notes and %s has %d notes: NOT REDUCED '
                '(expected fewer than %s)' %
                (higher_label, higher_count, lower_label, lower_count,
                 higher_label))
            issues += 1

    return lines, issues


def compress_chord_offsets(offsets, target_max_offset):
    """Fit a sorted 5-lane chord into a lower tier's authored lane limit."""
    if not offsets or offsets[-1] <= target_max_offset:
        return list(offsets)
    shift = offsets[-1] - target_max_offset
    if len(offsets) <= 2 and offsets[0] - shift >= 0:
        return [offset - shift for offset in offsets]
    return [offset for offset in offsets if offset <= target_max_offset]
