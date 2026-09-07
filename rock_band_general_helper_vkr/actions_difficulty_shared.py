"""Shared pure helpers for Difficulty validation and reduction guidance.

Modern counterpart:
rock_band_general_helper_vkr/actions_difficulty_shared.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals


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
