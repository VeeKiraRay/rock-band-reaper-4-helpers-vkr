"""Read-only Pro Keys difficulty validation.

Modern counterpart:
rock_band_general_helper_vkr/actions_difficulty.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .actions_difficulty_5k import format_time
from .actions_difficulty_shared import check_difficulty_progression
from .difficulty_read import _load_items, read_midi_notes


PK_MIN = 48
PK_MAX = 72
PK_LANE_SHIFTS = frozenset((0, 2, 4, 5, 7, 9))
PK_PREFERRED_SHIFTS = frozenset((0, 5, 9))
PK_RANGE_NAMES = {
    0: 'C range (C2-E3)', 2: 'D range (D2-F#3)',
    4: 'E range (E2-G#3)', 5: 'F range (F2-A3)',
    7: 'G range (G2-B3)', 9: 'A range (A2-C4)',
}
PK_MAX_CHORD = {'X': 4, 'H': 3, 'M': 2, 'E': 1}
PK_MAX_SPAN = {'X': 12, 'H': 11, 'M': 9}
PK_MAX_JUMP = {'H': 11, 'M': 9, 'E': 7}
PK_MIN_SPACING = {'M': 1.0, 'E': 2.0}
PK_ALLOW_SHIFT = {'X': True, 'H': True, 'M': False, 'E': False}
DIFFICULTY_NAMES = {
    'X': 'Expert', 'H': 'Hard', 'M': 'Medium', 'E': 'Easy'}
DIFFICULTY_ORDER = ('X', 'H', 'M', 'E')
ADJACENT_HIGHER = {'H': 'X', 'M': 'H', 'E': 'M'}
NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B')
GRACE = 0.05
EPS_QN = 0.01


def pitch_name(pitch):
    pitch = max(0, min(127, int(round(pitch))))
    return '%s%d' % (NOTE_NAMES[pitch % 12], pitch // 12 - 2)


def event_label(pitches):
    names = [pitch_name(pitch) for pitch in pitches]
    return names[0] if len(names) == 1 else '[%s]' % '+'.join(names)


def read_pro_keys_data(host, track):
    notes = read_midi_notes(host, _load_items(host, track))
    lane_shifts = [note for note in notes
                   if note['pitch'] in PK_LANE_SHIFTS]
    playable = [note for note in notes
                if PK_MIN <= note['pitch'] <= PK_MAX]
    events = []
    index = 0
    while index < len(playable):
        first = playable[index]
        event = {
            's': first['s'], 'e': first['e'],
            'qn': first['qn'], 'qn_e': first['qn_e'],
            'pitches': [first['pitch']],
        }
        following = index + 1
        while (following < len(playable) and
               playable[following]['s'] - event['s'] <= 0.002):
            note = playable[following]
            event['pitches'].append(note['pitch'])
            if note['e'] > event['e']:
                event['e'] = note['e']
                event['qn_e'] = note['qn_e']
            following += 1
        event['pitches'].sort()
        events.append(event)
        index = following
    return notes, lane_shifts, events


def _suggest_chord_reduction(pitches, maximum, max_span):
    if maximum <= 1 or len(pitches) <= 1:
        high, low = pitch_name(pitches[-1]), pitch_name(pitches[0])
        if high == low:
            return '-> suggest ' + high
        return '-> suggest %s (highest) or %s (lowest)' % (high, low)
    keep_high = None
    keep_low = None
    for left_index in range(len(pitches) - 1):
        for right_index in range(left_index + 1, len(pitches)):
            left, right = pitches[left_index], pitches[right_index]
            if max_span is not None and right - left > max_span:
                continue
            if right == pitches[-1] and keep_high is None:
                keep_high = [left, right]
            if left == pitches[0] and keep_low is None:
                keep_low = [left, right]
    if keep_high is None and keep_low is None:
        return _suggest_chord_reduction(pitches, 1, max_span)
    choices = []
    if keep_high is not None:
        choices.append(event_label(keep_high))
    if keep_low is not None and keep_low != keep_high:
        choices.append(event_label(keep_low))
    return '-> suggest ' + ' or '.join(choices)


def _check_chord_count(events, maximum, max_span):
    issues = []
    for event in events:
        if len(event['pitches']) > maximum:
            limit = 'single notes only' if maximum == 1 else 'max %d' % maximum
            issues.append('%s: %s has %d notes (%s) %s' % (
                format_time(event['s']), event_label(event['pitches']),
                len(event['pitches']), limit,
                _suggest_chord_reduction(
                    event['pitches'], maximum, max_span)))
    return issues


def _check_chord_span(events, maximum):
    issues = []
    for event in events:
        if len(event['pitches']) > 1:
            span = event['pitches'][-1] - event['pitches'][0]
            if span > maximum:
                issues.append('%s: %s spans %d semitones (max %d) %s' % (
                    format_time(event['s']), event_label(event['pitches']),
                    span, maximum, _suggest_chord_reduction(
                        event['pitches'], len(event['pitches']) - 1,
                        maximum)))
    return issues


def _suggest_jump_fix(previous, current, interval, maximum, frequencies):
    overshoot = interval - maximum
    if len(previous) != 1 or len(current) != 1:
        return '-> bring events %d semitone%s closer' % (
            overshoot, '' if overshoot == 1 else 's')
    first, second = previous[0], current[0]
    if second > first:
        fix_second, fix_first = second - overshoot, first + overshoot
    else:
        fix_second, fix_first = second + overshoot, first - overshoot
    want_first = frequencies.get(first, 0) <= frequencies.get(second, 0)
    want_second = frequencies.get(second, 0) <= frequencies.get(first, 0)
    if want_first and want_second:
        after_first = frequencies.get(fix_first, 0) + 1
        after_second = frequencies.get(fix_second, 0) + 1
        if after_first < after_second:
            want_second = False
        elif after_second < after_first:
            want_first = False

    def change(original, target):
        verb = 'raise' if target > original else 'lower'
        return '%s %s to %s' % (
            verb, pitch_name(original), pitch_name(target))

    if want_first and not want_second:
        return '-> ' + change(first, fix_first)
    if want_second and not want_first:
        return '-> ' + change(second, fix_second)
    return '-> %s, or %s' % (
        change(second, fix_second), change(first, fix_first))


def _check_interval_jumps(events, maximum):
    frequencies = {}
    for event in events:
        for pitch in event['pitches']:
            frequencies[pitch] = frequencies.get(pitch, 0) + 1
    issues = []
    for previous, current in zip(events, events[1:]):
        interval = min(abs(right - left)
                       for left in previous['pitches']
                       for right in current['pitches'])
        if interval > maximum:
            issues.append(
                '%s: jump of %d semitones from %s to %s (max %d) %s' %
                (format_time(current['s']), interval,
                 event_label(previous['pitches']),
                 event_label(current['pitches']), maximum,
                 _suggest_jump_fix(previous['pitches'], current['pitches'],
                                   interval, maximum, frequencies)))
    return issues


def _check_spacing(host, events, minimum):
    issues = []
    for previous, current in zip(events, events[1:]):
        gap_qn = current['qn'] - previous['qn']
        if gap_qn < minimum * (1 - GRACE):
            required = (host.qn_to_time(previous['qn'] + minimum) -
                        previous['s'])
            label = '1/4 note' if minimum == 1.0 else '1/2 note'
            issues.append(
                '%s: %s is %.0f ms after previous note (min %s = %.0f ms)' %
                (format_time(current['s']), event_label(current['pitches']),
                 (current['s'] - previous['s']) * 1000,
                 label, required * 1000))
    return issues


def _check_lane_shifts(lane_shifts, events, allow_extra):
    issues = []
    first_time = events[0]['s'] if events else None
    has_initial = any(first_time is None or
                      marker['s'] <= first_time + 0.001
                      for marker in lane_shifts)
    if first_time is not None and not has_initial:
        issues.append(
            'No initial range marker before first note '
            '(required on all difficulties)')
    if not allow_extra and first_time is not None:
        for marker in lane_shifts:
            if marker['s'] > first_time + 0.001:
                issues.append(
                    '%s: lane range shift not allowed on Medium or Easy' %
                    format_time(marker['s']))
    return issues


def _check_preferred_ranges(lane_shifts):
    issues = []
    for marker in lane_shifts:
        if marker['pitch'] not in PK_PREFERRED_SHIFTS:
            name = PK_RANGE_NAMES.get(
                marker['pitch'], 'pitch %d' % marker['pitch'])
            issues.append(
                '%s: %s - prefer C range (C2-E3), F range (F2-A3), '
                'or A range (A2-C4)' %
                (format_time(marker['s']), name))
    return issues


def _check_overlaps(events, difficulty):
    maximum = {'X': 4, 'H': 3}
    issues = []
    for index in range(1, len(events)):
        current = events[index]
        active_events = [previous for previous in events[:index]
                         if previous['e'] > current['s'] + 0.002]
        active = [pitch for event in active_events
                  for pitch in event['pitches']]
        if not active:
            continue
        if difficulty == 'M':
            latest_qn = max(event['qn'] for event in active_events)
            if current['qn'] - latest_qn >= 1.0 - EPS_QN:
                continue
        all_pitches = sorted(active + current['pitches'])
        span = all_pitches[-1] - all_pitches[0]
        count = len(all_pitches)
        if difficulty == 'E':
            issues.append(
                '%s: %s starts while %s still playing '
                '(no overlapping on Easy)' %
                (format_time(current['s']),
                 event_label(current['pitches']), event_label(sorted(active))))
        elif difficulty == 'M':
            issues.append(
                '%s: %s overlaps previous note (no overlapping on Medium '
                'unless >= quarter note apart)' %
                (format_time(current['s']), event_label(current['pitches'])))
        elif count > maximum[difficulty]:
            issues.append(
                '%s: %d notes active simultaneously '
                '(max %d overlapping for %s)' %
                (format_time(current['s']), count, maximum[difficulty],
                 DIFFICULTY_NAMES[difficulty]))
        if difficulty in ('X', 'H') and span > 12:
            issues.append(
                '%s: overlapping notes span %d semitones (max 12 = octave)' %
                (format_time(current['s']), span))
    return issues


def _simple_transition(first, second):
    first_chord = len(first) > 1
    second_chord = len(second) > 1
    if not first_chord and not second_chord:
        return True
    if not first_chord:
        return first[0] in second
    if not second_chord:
        return second[0] in first
    return first == second


def _check_sustain_gaps(host, events, difficulty):
    issues = []
    for event, following in zip(events, events[1:]):
        duration_qn = event['qn_e'] - event['qn']
        if duration_qn < 0.5 - EPS_QN:
            continue
        gap_qn = following['qn'] - event['qn_e']
        if gap_qn < 0:
            continue
        first_chord = len(event['pitches']) > 1
        second_chord = len(following['pitches']) > 1
        if difficulty in ('M', 'E'):
            minimum, label, prefix = 1.0, '1/4 note', ''
        elif _simple_transition(event['pitches'], following['pitches']):
            minimum, label, prefix = 0.25, '1/16 note', 'simple transition: '
        elif first_chord and second_chord:
            minimum, label, prefix = 0.5, '1/8 note', 'chord -> chord: '
        elif first_chord:
            minimum, label, prefix = (
                0.5, '1/8 note', 'chord -> unrelated note: ')
        else:
            minimum, label, prefix = (
                0.5, '1/8 note', 'note -> unrelated chord: ')
        if gap_qn < minimum * (1 - GRACE):
            required = (host.qn_to_time(event['qn_e'] + minimum) -
                        event['e'])
            issues.append(
                '%s: %s ends %.0f ms before %s (%sneed %s gap = %.0f ms)' %
                (format_time(following['s']), event_label(event['pitches']),
                 (following['s'] - event['e']) * 1000,
                 event_label(following['pitches']), prefix, label,
                 required * 1000))
    return issues


def _check_notes_above_expert(expert, lower):
    issues = []
    for event in lower:
        nearest = None
        distance = None
        for candidate in expert:
            value = abs(candidate['qn'] - event['qn'])
            if distance is None or value < distance:
                nearest, distance = candidate, value
        if nearest is None or distance > 0.5:
            issues.append('%s: %s has no Expert note within 1/8 note' % (
                format_time(event['s']), event_label(event['pitches'])))
        elif len(event['pitches']) > len(nearest['pitches']):
            issues.append(
                '%s: %s has more notes than nearest Expert chord %s' %
                (format_time(event['s']), event_label(event['pitches']),
                 event_label(nearest['pitches'])))
    return issues


def _check_missing_measures(host, expert, lower):
    measure_at = getattr(host, 'measure_at', None)
    if measure_at is None:
        return None
    try:
        expert_measures = set(measure_at(event['s']) for event in expert)
        lower_measures = set(measure_at(event['s']) for event in lower)
    except Exception:
        return None
    if None in expert_measures or None in lower_measures:
        return None
    missing = sorted(expert_measures - lower_measures)
    issues = []
    index = 0
    while index < len(missing):
        start = end = missing[index]
        while index + 1 < len(missing) and missing[index + 1] == end + 1:
            index += 1
            end = missing[index]
        if start == end:
            issues.append('Measure %d has Expert notes but none here' % start)
        else:
            issues.append('Measures %d-%d have Expert notes but none here' %
                          (start, end))
        index += 1
    return issues


def _build_report(header, categories, notes=None):
    lines = [header, '']
    total = 0
    for name, issues in categories:
        total += len(issues)
        if issues:
            lines.append('%s:  %d issue%s' %
                         (name, len(issues),
                          '' if len(issues) == 1 else 's'))
            lines.extend('  * ' + issue for issue in issues)
        else:
            lines.append(name + ':  OK')
        lines.append('')
    if notes:
        lines.extend(notes)
    return '\n'.join(lines), total


def run_pro_keys_checks(host, difficulty, events, lane_shifts,
                        expert_events=None, header=None):
    categories = []
    maximum = PK_MAX_CHORD[difficulty]
    categories.append((
        ('Chord count (single notes only)' if difficulty == 'E' else
         'Chord count (max %d)' % maximum),
        _check_chord_count(
            events, maximum, PK_MAX_SPAN.get(difficulty))))
    if difficulty in PK_MAX_SPAN:
        span = PK_MAX_SPAN[difficulty]
        categories.append(('Chord span (max %d semitones)' % span,
                           _check_chord_span(events, span)))
    if difficulty in PK_MAX_JUMP:
        jump = PK_MAX_JUMP[difficulty]
        categories.append(('Interval jumps (max %d semitones)' % jump,
                           _check_interval_jumps(events, jump)))
    if difficulty in PK_MIN_SPACING:
        spacing = PK_MIN_SPACING[difficulty]
        label = ('Note spacing (min 1/4 note start-to-start)'
                 if spacing == 1.0 else
                 'Note spacing (min 1/2 note start-to-start)')
        categories.append((label, _check_spacing(host, events, spacing)))
    categories.append(('Lane range markers', _check_lane_shifts(
        lane_shifts, events, PK_ALLOW_SHIFT[difficulty])))
    if PK_ALLOW_SHIFT[difficulty] and lane_shifts:
        categories.append(('Lane shift ranges (prefer C, F, A)',
                           _check_preferred_ranges(lane_shifts)))
    categories.append(('Overlapping gems',
                       _check_overlaps(events, difficulty)))
    categories.append(('Sustain gaps',
                       _check_sustain_gaps(host, events, difficulty)))
    notes = []
    if difficulty != 'X' and expert_events:
        categories.append(('Notes not in Expert',
                           _check_notes_above_expert(expert_events, events)))
        missing = _check_missing_measures(host, expert_events, events)
        if missing is None:
            notes.append(
                'Missing measures: not checked (measure formatting unavailable).')
        else:
            categories.append(('Missing measures', missing))
    return _build_report(
        header or 'Pro Keys %s Validation' % DIFFICULTY_NAMES[difficulty],
        categories, notes)


def validate_pro_keys(host, tracks, difficulty):
    track = tracks.get(difficulty)
    name = DIFFICULTY_NAMES[difficulty]
    if track is None:
        return ('Error: %s track not selected.' % name,
                'Select the PART REAL_KEYS_%s track in the Difficulty tab.' %
                difficulty)
    all_notes, lane_shifts, events = read_pro_keys_data(host, track)
    if not all_notes:
        return ('Validate %s: track is empty.' % difficulty,
                '%s track is empty.' % name)
    expert_events = None
    if difficulty != 'X' and tracks.get('X') is not None:
        unused_notes, unused_shifts, candidate = read_pro_keys_data(
            host, tracks['X'])
        if candidate:
            expert_events = candidate
    report, total = run_pro_keys_checks(
        host, difficulty, events, lane_shifts, expert_events)
    higher = ADJACENT_HIGHER.get(difficulty)
    if higher and tracks.get(higher) is not None:
        unused_notes, unused_shifts, higher_events = read_pro_keys_data(
            host, tracks[higher])
        progression, extra = check_difficulty_progression(
            name, DIFFICULTY_NAMES[higher], events, higher_events,
            PK_MIN, PK_MIN)
        if progression:
            report = '\n'.join(progression) + '\n\n' + report
        total += extra
    status = ('Validate %s: all checks passed.' % difficulty
              if total == 0 else
              'Validate %s: %d issue%s found.' %
              (difficulty, total, '' if total == 1 else 's'))
    return status, report


def validate_all_pro_keys(host, tracks):
    expert_events = None
    if tracks.get('X') is not None:
        unused_notes, unused_shifts, expert_events = read_pro_keys_data(
            host, tracks['X'])
        if not expert_events:
            expert_events = None
    lines = ['Pro Keys Validate All', '']
    summary = []
    previous_difficulty = None
    previous_events = []
    for difficulty in DIFFICULTY_ORDER:
        track = tracks.get(difficulty)
        if track is None:
            summary.append(difficulty + ':(none)')
            previous_difficulty, previous_events = difficulty, []
            continue
        notes, shifts, events = read_pro_keys_data(host, track)
        if not notes:
            summary.append(difficulty + ':empty')
            lines.extend(('=== %s ===  (track is empty)' %
                          DIFFICULTY_NAMES[difficulty], ''))
            previous_difficulty, previous_events = difficulty, []
            continue
        report, total = run_pro_keys_checks(
            host, difficulty, events, shifts,
            expert_events if difficulty != 'X' else None,
            '=== Pro Keys %s ===' % DIFFICULTY_NAMES[difficulty])
        if (difficulty != 'X' and
                previous_difficulty == ADJACENT_HIGHER[difficulty]):
            progression, extra = check_difficulty_progression(
                DIFFICULTY_NAMES[difficulty],
                DIFFICULTY_NAMES[previous_difficulty],
                events, previous_events, PK_MIN, PK_MIN)
            if progression:
                report = '\n'.join(progression) + '\n\n' + report
            total += extra
        summary.append(difficulty + (':OK' if total == 0 else ':%d' % total))
        lines.extend(report.split('\n'))
        previous_difficulty, previous_events = difficulty, events
    return ('Validate All Pro Keys: %s' % ' | '.join(summary),
            '\n'.join(lines))
