"""Read-only 5-lane Keys difficulty validation.

Modern counterpart:
rock_band_general_helper_vkr/actions_difficulty_5k.lua

The first legacy Difficulty slice deliberately contains no project mutation.
Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .actions_difficulty_shared import (
    check_difficulty_progression,
    count_notes,
)
from .difficulty_read import _load_items, read_gem_events


K5_RANGE = {
    'X': {'lo': 96, 'hi': 100},
    'H': {'lo': 84, 'hi': 88},
    'M': {'lo': 72, 'hi': 75},
    'E': {'lo': 60, 'hi': 62},
}
K5_MAX_CHORD = {'X': 5, 'H': 3, 'M': 2, 'E': 1}
K5_MIN_SPACING = {'M': 1.0, 'E': 1.0}
K5_ADVISORY_SPACING = {'E': 2.0}
DIFFICULTY_NAMES = {
    'X': 'Expert', 'H': 'Hard', 'M': 'Medium', 'E': 'Easy'}
ADJACENT_HIGHER = {'H': 'X', 'M': 'H', 'E': 'M'}
GEM_NAMES = ('Green', 'Red', 'Yellow', 'Blue', 'Orange')
DIFFICULTY_ORDER = ('X', 'H', 'M', 'E')
GRACE = 0.05
EPS_QN = 0.01


class DifficultyValidationError(Exception):
    pass


def format_time(seconds):
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return '%d:%06.3f' % (minutes, remainder)


def gem_name(pitch):
    for value in K5_RANGE.values():
        offset = pitch - value['lo']
        if 0 <= offset <= 4:
            return GEM_NAMES[offset]
    return 'MIDI %d' % pitch


def event_label(pitches):
    names = [gem_name(pitch) for pitch in pitches]
    return names[0] if len(names) == 1 else '[%s]' % '+'.join(names)


def read_keys_events(host, track, difficulty):
    try:
        value = K5_RANGE[difficulty]
    except KeyError:
        raise DifficultyValidationError(
            'Unknown Keys difficulty %s.' % difficulty)
    contexts = _load_items(host, track)
    # Read all five conventional gem slots so forbidden Blue/Orange gems on
    # Medium/Easy remain visible to the range check.
    return read_gem_events(host, contexts, value['lo'], value['lo'] + 4)


def _check_out_of_range(events, high):
    issues = []
    for event in events:
        for pitch in event['pitches']:
            if pitch > high:
                issues.append(
                    '%s: %s (pitch %d) is outside the valid range for this '
                    'difficulty' %
                    (format_time(event['s']), gem_name(pitch), pitch))
    return issues


def _check_chords(events, maximum, difficulty):
    issues = []
    for event in events:
        if len(event['pitches']) > maximum:
            limit = 'no chords' if maximum == 1 else 'max %d' % maximum
            issues.append('%s: %s has %d notes (%s for %s)' % (
                format_time(event['s']), event_label(event['pitches']),
                len(event['pitches']), limit,
                DIFFICULTY_NAMES[difficulty]))
    return issues


def _duration_seconds(host, start_qn, duration_qn):
    return host.qn_to_time(start_qn + duration_qn) - host.qn_to_time(start_qn)


def _check_spacing(host, events, minimum, advisory=None):
    issues = []
    for previous, current in zip(events, events[1:]):
        gap_qn = current['qn'] - previous['qn']
        gap_seconds = current['s'] - previous['s']
        if gap_qn < minimum * (1 - GRACE):
            label = '1/4 note' if minimum == 1.0 else '1/2 note'
            required = _duration_seconds(host, previous['qn'], minimum)
            issues.append(
                '%s: %s is %.0f ms after previous (min %s = %.0f ms)' %
                (format_time(current['s']), event_label(current['pitches']),
                 gap_seconds * 1000, label, required * 1000))
        elif advisory and gap_qn < advisory * (1 - GRACE):
            label = '1/2 note' if advisory == 2.0 else '1/4 note'
            required = _duration_seconds(host, previous['qn'], advisory)
            issues.append(
                '%s: %s is %.0f ms after previous (advisory: %s = %.0f '
                'ms recommended for Easy)' %
                (format_time(current['s']), event_label(current['pitches']),
                 gap_seconds * 1000, label, required * 1000))
    return issues


def _check_note_length(host, events):
    issues = []
    for event in events:
        duration_qn = event['qn_e'] - event['qn']
        if duration_qn < 0.0625 * (1 - GRACE):
            required = _duration_seconds(host, event['qn'], 0.0625)
            issues.append('%s: %s is %.1f ms long (min 1/64 note = %.1f ms)' % (
                format_time(event['s']), event_label(event['pitches']),
                (event['e'] - event['s']) * 1000, required * 1000))
    return issues


def _check_sustain_length(host, events):
    issues = []
    for event in events:
        beat_seconds = _duration_seconds(host, event['qn'], 1.0)
        bpm = 60.0 / beat_seconds if beat_seconds > 0 else 120.0
        if bpm < 100:
            continue
        duration_qn = event['qn_e'] - event['qn']
        if (duration_qn >= 0.5 - EPS_QN and
                duration_qn < 0.75 * (1 - GRACE)):
            required = _duration_seconds(host, event['qn'], 0.75)
            issues.append(
                '%s: %s is %.0f ms (need >= 3/16 note = %.0f ms at '
                '%.0f BPM, or shorten to hit)' %
                (format_time(event['s']), event_label(event['pitches']),
                 (event['e'] - event['s']) * 1000,
                 required * 1000, bpm))
    return issues


def _check_sustain_gaps(host, events, difficulty):
    issues = []
    for event, following in zip(events, events[1:]):
        duration_qn = event['qn_e'] - event['qn']
        if duration_qn < 0.5 - EPS_QN:
            continue
        gap_qn = following['qn'] - event['qn_e']
        if gap_qn < 0:
            continue
        if difficulty in ('M', 'E'):
            minimum, label = 1.0, '1/4 note'
        elif len(event['pitches']) > 1:
            minimum, label = 0.5, '1/8 note'
        else:
            minimum, label = 0.25, '1/16 note'
        if gap_qn < minimum * (1 - GRACE):
            required = _duration_seconds(host, event['qn_e'], minimum)
            issues.append(
                '%s: %s ends %.0f ms before %s (need %s gap = %.0f ms)' %
                (format_time(following['s']), event_label(event['pitches']),
                 (following['s'] - event['e']) * 1000,
                 event_label(following['pitches']), label,
                 required * 1000))
    return issues


def _build_report(header, categories):
    lines = [header, '']
    total = 0
    passed = []
    for name, issues in categories:
        if issues:
            lines.append(name + ':')
            for issue in issues:
                lines.append('  ' + issue)
                total += 1
            lines.append('')
        else:
            passed.append(name)
    if not total:
        lines.extend(('No issues found.', ''))
    elif passed:
        lines.extend(('Passed: ' + ', '.join(passed), ''))
    return '\n'.join(lines), total


def run_keys_checks(host, difficulty, events, header=None):
    value = K5_RANGE[difficulty]
    maximum = K5_MAX_CHORD[difficulty]
    categories = [
        ('Notes outside valid range',
         _check_out_of_range(events, value['hi'])),
        (('Chords (none allowed on Easy)' if difficulty == 'E' else
          'Max chord (%d notes)' % maximum),
         _check_chords(events, maximum, difficulty)),
    ]
    if difficulty in K5_MIN_SPACING:
        categories.append((
            ('Note spacing (min 1/4 note, advisory 1/2 note)'
             if difficulty == 'E' else
             'Note spacing (min 1/4 note)'),
            _check_spacing(
                host, events, K5_MIN_SPACING[difficulty],
                K5_ADVISORY_SPACING.get(difficulty))))
    categories.append(
        ('Note length (min 1/64)', _check_note_length(host, events)))
    if difficulty in ('X', 'H'):
        categories.append((
            'Sustain length (min 3/16 at >=100 BPM)',
            _check_sustain_length(host, events)))
    categories.append((
        ('Sustain gaps (min 1/4 note gap to next)'
         if difficulty in ('M', 'E') else
         'Sustain gaps (min 1/16 single / 1/8 chord)'),
        _check_sustain_gaps(host, events, difficulty)))
    if header is None:
        header = '5-Lane Keys %s Validation  [%d-%d]' % (
            DIFFICULTY_NAMES[difficulty], value['lo'], value['hi'])
    return _build_report(header, categories)


def validate_keys(host, track, difficulty):
    events = read_keys_events(host, track, difficulty)
    value = K5_RANGE[difficulty]
    name = DIFFICULTY_NAMES[difficulty]
    if not events:
        return (
            'Validate 5-Key %s: no notes in MIDI range %d-%d.' %
            (difficulty, value['lo'], value['hi']),
            'No %s notes (MIDI %d-%d) on PART KEYS track.' %
            (name, value['lo'], value['hi']))

    report, total = run_keys_checks(host, difficulty, events)
    higher = ADJACENT_HIGHER.get(difficulty)
    if higher:
        higher_events = read_keys_events(host, track, higher)
        lines, extra = check_difficulty_progression(
            name, DIFFICULTY_NAMES[higher], events, higher_events,
            value['lo'], K5_RANGE[higher]['lo'])
        if lines:
            report = '\n'.join(lines) + '\n\n' + report
        total += extra
    if total:
        status = 'Validate 5-Key %s: %d issue%s found.' % (
            difficulty, total, '' if total == 1 else 's')
    else:
        status = 'Validate 5-Key %s: all checks passed.' % difficulty
    return status, report


def validate_all_keys(host, track):
    lines = ['5-Lane Keys Validate All', '']
    summary = []
    previous_difficulty = None
    previous_events = []

    for difficulty in DIFFICULTY_ORDER:
        value = K5_RANGE[difficulty]
        events = read_keys_events(host, track, difficulty)
        if not events:
            summary.append(difficulty + ':empty')
            lines.extend((
                '=== %s ===  (no notes in range %d-%d)' %
                (DIFFICULTY_NAMES[difficulty], value['lo'], value['hi']),
                ''))
        else:
            report, total = run_keys_checks(
                host, difficulty, events,
                '=== 5-Lane Keys %s  [%d-%d] ===' %
                (DIFFICULTY_NAMES[difficulty], value['lo'], value['hi']))
            if (difficulty != 'X' and
                    previous_difficulty == ADJACENT_HIGHER[difficulty]):
                progression, extra = check_difficulty_progression(
                    DIFFICULTY_NAMES[difficulty],
                    DIFFICULTY_NAMES[previous_difficulty],
                    events, previous_events, value['lo'],
                    K5_RANGE[previous_difficulty]['lo'])
                if progression:
                    report = '\n'.join(progression) + '\n\n' + report
                total += extra
            summary.append(
                difficulty + (':OK' if not total else ':%d' % total))
            lines.extend(report.split('\n'))
        previous_difficulty = difficulty
        previous_events = events

    return ('Validate All 5-Lane Keys: %s' % ' | '.join(summary),
            '\n'.join(lines))
