"""Read-only Drums difficulty validation for the legacy REAPER port.

Modern counterpart:
rock_band_general_helper_vkr/actions_difficulty_drums.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import re

from .actions_difficulty import pitch_name
from .actions_difficulty_5k import format_time
from .actions_difficulty_shared import check_difficulty_progression
from .difficulty_read import (
    _load_items, read_midi_notes, read_midi_text_events)


DRUMS_RANGE = {
    'X': {'lo': 96, 'hi': 100}, 'H': {'lo': 84, 'hi': 88},
    'M': {'lo': 72, 'hi': 76}, 'E': {'lo': 60, 'hi': 64},
}
DIFFICULTY_NAMES = {
    'X': 'Expert', 'H': 'Hard', 'M': 'Medium', 'E': 'Easy'}
DIFFICULTY_ORDER = ('X', 'H', 'M', 'E')
ADJACENT_HIGHER = {'H': 'X', 'M': 'H', 'E': 'M'}
GEM_NAMES = ('Kick', 'Red', 'Yellow', 'Blue', 'Green')
DIFF_BY_MIX_IDX = {0: 'Easy', 1: 'Medium', 2: 'Hard', 3: 'Expert'}
GRACE = 0.05
EPS_QN = 0.01
MIN_RUN_LEN = 4
_MIX_RE = re.compile(r'\[mix (\d+) drums(\d)([A-Za-z]*)\]')

DRUMS_HINTS = {
    'H': (
        'Try removing kicks from adjacent 8th or 16th notes.',
        'In a section filled with little snare accents, remove about half of them.',
        'Trim a note or two from the start of a fast roll.',
        'Reduce hand motion: if a crash happens right after a snare flam '
        '(Red+Yellow), consider making the flam a one-handed snare hit instead.',
    ),
    'M': ('It is usually best to reduce triplets to quarter notes.',),
    'E': ('Favor crash (Green) over kick when simplifying a beat.',),
}


def _text(value):
    try:
        return value.decode('latin-1')
    except AttributeError:
        return value


def _bpm(host, qn):
    duration = host.qn_to_time(qn + 1.0) - host.qn_to_time(qn)
    return 60.0 / duration if duration > 0 else 120.0


def _on_grid(qn, size, tolerance):
    fraction = qn % size
    return min(fraction, size - fraction) <= tolerance


def drum_gem_name(pitch):
    for value in DRUMS_RANGE.values():
        offset = pitch - value['lo']
        if 0 <= offset <= 4:
            return GEM_NAMES[offset]
    return pitch_name(pitch)


def drum_label(pitches):
    names = [drum_gem_name(pitch) for pitch in pitches]
    return names[0] if len(names) == 1 else '[%s]' % '+'.join(names)


def read_drums_events(difficulty, all_notes):
    value = DRUMS_RANGE[difficulty]
    notes = [note for note in all_notes
             if value['lo'] <= note['pitch'] <= value['lo'] + 4]
    events = []
    index = 0
    while index < len(notes):
        first = notes[index]
        event = {'s': first['s'], 'e': first['e'], 'qn': first['qn'],
                 'qn_e': first['qn_e'], 'pitches': [first['pitch']]}
        following = index + 1
        while (following < len(notes) and
               notes[following]['s'] - event['s'] <= 0.002):
            note = notes[following]
            event['pitches'].append(note['pitch'])
            if note['e'] > event['e']:
                event['e'], event['qn_e'] = note['e'], note['qn_e']
            following += 1
        event['pitches'].sort()
        events.append(event)
        index = following
    return events


def _has_offset(event, value, offset):
    return value['lo'] + offset in event['pitches']


def _check_out_of_range(events, high):
    return ['%s: %s (pitch %d) is outside the valid range for this difficulty' %
            (format_time(event['s']), drum_gem_name(pitch), pitch)
            for event in events for pitch in event['pitches'] if pitch > high]


def _check_max_chord(events, difficulty):
    return ['%s: %s has %d notes (max 2 simultaneous notes on %s)' %
            (format_time(event['s']), drum_label(event['pitches']),
             len(event['pitches']), DIFFICULTY_NAMES[difficulty])
            for event in events if len(event['pitches']) >= 3]


def _check_kick_pairing(events, value):
    return ['%s: %s pairs a gem with kick (not allowed on Easy)' %
            (format_time(event['s']), drum_label(event['pitches']))
            for event in events
            if len(event['pitches']) >= 2 and _has_offset(event, value, 0)]


def _check_kick_grid(host, events, value):
    issues = []
    for event in events:
        bpm = _bpm(host, event['qn'])
        if (_has_offset(event, value, 0) and bpm > 100 and
                not _on_grid(event['qn'], 1.0, GRACE)):
            issues.append('%s: kick at %.0f BPM is not on the quarter-note grid '
                          '(kicks on quarter notes only above 100 BPM)' %
                          (format_time(event['s']), bpm))
    return issues


def _check_kicks_per_measure(host, events, value):
    measure_at = getattr(host, 'measure_at', None)
    if measure_at is None:
        return [], False
    counts = {}
    first = {}
    for event in events:
        if not _has_offset(event, value, 0):
            continue
        measure = measure_at(event['s'])
        if measure is None:
            return [], False
        counts[measure] = counts.get(measure, 0) + 1
        first.setdefault(measure, event)
    issues = []
    for measure in sorted(counts):
        bpm = _bpm(host, first[measure]['qn'])
        if counts[measure] > 1 and bpm >= 170:
            issues.append('Measure %d has %d kicks at %.0f BPM '
                          '(max 1 per measure at >=170 BPM)' %
                          (measure, counts[measure], bpm))
    return issues, True


def _check_on_beat_crash_kick(events, value):
    return ['%s: off-beat/syncopated crash+kick not allowed on Medium '
            '(on-beat only)' % format_time(event['s'])
            for event in events
            if len(event['pitches']) == 2 and
            _has_offset(event, value, 0) and _has_offset(event, value, 4) and
            not _on_grid(event['qn'], 1.0, GRACE)]


def _check_double_crash(events, value):
    issues = []
    for index, event in enumerate(events):
        offsets = [pitch - value['lo'] for pitch in event['pitches']]
        if len(offsets) == 2 and offsets[1] == 4 and offsets[0] in (2, 3):
            if index == 0 or event['qn'] - events[index - 1]['qn'] < 1.0 - GRACE:
                issues.append('%s: %s double crash needs a quarter-note gap '
                              'before it to prepare, or should be reduced to '
                              'a single Green' %
                              (format_time(event['s']),
                               drum_label(event['pitches'])))
    return issues


def _check_fill_kicks(events, fills, value):
    issues = []
    for event in events:
        if _has_offset(event, value, 0) and any(
                event['s'] >= marker['s'] - .001 and
                event['s'] < marker['e'] + .001 for marker in fills):
            issues.append('%s: kick during a drum fill '
                          '(remove kicks from fills)' % format_time(event['s']))
    return issues


def _check_roll_grid(rolls):
    return ['%s: roll does not start on an 8th/quarter-note grid line' %
            format_time(roll['s']) for roll in rolls
            if not _on_grid(roll['qn'], .5, .5 * GRACE)]


def _roll_events(roll, events):
    return [event for event in events
            if event['s'] >= roll['s'] - .001 and
            event['s'] < roll['e'] + .001]


def _check_even_rolls(rolls, events):
    issues = []
    for roll in rolls:
        count = sum(len(event['pitches']) for event in _roll_events(roll, events))
        if count > 0 and count % 2:
            issues.append('%s: roll has %d hits (should be an even number)' %
                          (format_time(roll['s']), count))
    return issues


def _check_roll_density(host, rolls, events, difficulty):
    issues = []
    for roll in rolls:
        covered = _roll_events(roll, events)
        if len(covered) < 2:
            continue
        gap = (covered[-1]['qn'] - covered[0]['qn']) / (len(covered) - 1)
        bpm = _bpm(host, roll['qn'])
        if difficulty == 'H' and bpm >= 140 and gap < .375:
            issues.append('%s: roll at %.0f BPM is authored at 16th-note rate '
                          '(avoid 16ths at >=140 BPM on Hard)' %
                          (format_time(roll['s']), bpm))
        elif difficulty == 'M' and gap < .5 - EPS_QN:
            issues.append('%s: roll is faster than 8th-note rate '
                          '(Medium never plays rolls/fills at 16th-note rate)' %
                          format_time(roll['s']))
        elif difficulty == 'E' and bpm >= 120 and gap < 1.0 - EPS_QN:
            issues.append('%s: roll at %.0f BPM is faster than quarter-note '
                          'rate (reduce fills to quarter notes at >=120 BPM '
                          'on Easy)' % (format_time(roll['s']), bpm))
        elif difficulty == 'E' and bpm < 120 and gap < .5 - EPS_QN:
            issues.append('%s: roll is faster than 8th-note rate '
                          '(inherited from Medium - no Easy override below '
                          '120 BPM)' % format_time(roll['s']))
    return issues


def _check_general_density(host, events, difficulty):
    threshold = 170 if difficulty == 'H' else 140
    issues = []
    index = 0
    while index < len(events) - 1:
        end = index
        while (end < len(events) - 1 and
               abs(events[end + 1]['qn'] - events[end]['qn'] - .5) <= .5 * GRACE):
            end += 1
        length = end - index + 1
        if length >= MIN_RUN_LEN:
            bpm = _bpm(host, events[index]['qn'])
            if bpm >= threshold:
                issues.append('%s-%s: %d consecutive 8th notes at %.0f BPM '
                              '(reduce timekeeping density above %d BPM on %s)' %
                              (format_time(events[index]['s']),
                               format_time(events[end]['s']), length, bpm,
                               threshold, DIFFICULTY_NAMES[difficulty]))
            index = end + 1
        else:
            index += 1
    return issues


def _check_roll_velocity(all_notes):
    issues = []
    for note in all_notes:
        if note['pitch'] in (126, 127) and note['velocity'] <= 40:
            kind = ('Special/cymbal-swell roll'
                    if note['pitch'] == 127 else 'Roll')
            issues.append('%s: %s marker velocity %d (need 41-50 for Hard '
                          'eligibility - Magma will report a spacing error)' %
                          (format_time(note['s']), kind, note['velocity']))
    return issues


def _kick_count(events, value):
    return sum(1 for event in events for pitch in event['pitches']
               if pitch == value['lo'])


def _check_hard_kicks(events, expert_events):
    lower = _kick_count(events, DRUMS_RANGE['H'])
    higher = _kick_count(expert_events, DRUMS_RANGE['X'])
    if higher and lower >= higher:
        return ['Hard has %d kicks and Expert has %d kicks - Hard should have '
                'fewer kicks than Expert' % (lower, higher)]
    return []


def _mix_events(text_events):
    found = []
    for event in text_events:
        match = _MIX_RE.search(_text(event['text']))
        if match:
            found.append({'s': event['s'], 'index': int(match.group(1)),
                          'config': match.group(2), 'suffix': match.group(3)})
    return found


def _check_disco_unflip(text_events):
    return ['%s: Hard mix event uses the disco variant (drums%sd) - Hard '
            'should use the un-flipped/base config (drums%s or drums%snoflip)' %
            (format_time(event['s']), event['config'], event['config'],
             event['config']) for event in _mix_events(text_events)
            if event['index'] == 2 and event['suffix'] == 'd']


def scan_disco_status(text_events):
    found = _mix_events(text_events)
    if not found:
        return 'Disco flip: no [mix N drums...] events found on this track.'
    lines = ['Disco flip status (informational only - not pass/fail):']
    for event in found:
        name = DIFF_BY_MIX_IDX.get(event['index'], 'idx %d' % event['index'])
        lines.append('  %s: mix %d drums%s%s (%s)' %
                     (format_time(event['s']), event['index'],
                      event['config'], event['suffix'], name))
    return '\n'.join(lines)


def _build_report(header, categories, unchecked=None):
    lines = [header, '']
    total = 0
    passed = []
    for name, issues in categories:
        if issues:
            lines.append(name + ':')
            lines.extend('  ' + issue for issue in issues)
            lines.append('')
            total += len(issues)
        else:
            passed.append(name)
    if total == 0:
        lines.extend(('No issues found.', ''))
    elif passed:
        lines.extend(('Passed: ' + ', '.join(passed), ''))
    if unchecked:
        lines.extend(unchecked)
        lines.append('')
    return '\n'.join(lines), total


def run_drums_checks(host, difficulty, events, all_notes, header=None):
    value = DRUMS_RANGE[difficulty]
    categories = [('Notes outside valid range',
                   _check_out_of_range(events, value['hi']))]
    unchecked = []
    if difficulty in ('M', 'E'):
        categories.extend((
            ('Max chord size (2 notes)', _check_max_chord(events, difficulty)),
            ('Kicks on quarter-note grid',
             _check_kick_grid(host, events, value))))
        measure_issues, measured = _check_kicks_per_measure(host, events, value)
        if measured:
            categories.append(('Kicks per measure', measure_issues))
        else:
            unchecked.append(
                'Kicks per measure: not checked (measure formatting unavailable).')
    if difficulty == 'M':
        categories.append(('On-beat crash+kick only',
                           _check_on_beat_crash_kick(events, value)))
    elif difficulty == 'E':
        categories.append(('No gems paired with kick (Easy)',
                           _check_kick_pairing(events, value)))
    if difficulty != 'X':
        fills = [note for note in all_notes if 120 <= note['pitch'] <= 124]
        rolls = [note for note in all_notes if note['pitch'] in (126, 127)]
        categories.extend((
            ('Timekeeping density',
             _check_general_density(host, events, difficulty)),
            ('Double crash prep space', _check_double_crash(events, value)),
            ('No kicks in drum fills', _check_fill_kicks(events, fills, value)),
            ('Roll starts on grid', _check_roll_grid(rolls)),
            ('Even roll hit count', _check_even_rolls(rolls, events)),
            ('Roll/fill density',
             _check_roll_density(host, rolls, events, difficulty)),
        ))
    if difficulty == 'H':
        categories.append(('Roll/Trill velocity (Hard eligibility)',
                           _check_roll_velocity(all_notes)))
    return _build_report(
        header or 'Drums %s Validation' % DIFFICULTY_NAMES[difficulty],
        categories, unchecked)


def _hints(difficulty):
    hints = DRUMS_HINTS.get(difficulty, ())
    if not hints:
        return ''
    return '\n'.join(['Authoring hints (suggestions, not hard rules):'] +
                     ['  - ' + hint for hint in hints]) + '\n\n'


def _read_track(host, track):
    contexts = _load_items(host, track)
    return (read_midi_notes(host, contexts),
            read_midi_text_events(host, contexts, (0x01,)))


def validate_drums(host, track, difficulty):
    value = DRUMS_RANGE[difficulty]
    all_notes, text_events = _read_track(host, track)
    events = read_drums_events(difficulty, all_notes)
    if not events:
        return ('Validate Drums %s: no notes in %s-%s (%d-%d).' %
                (difficulty, pitch_name(value['lo']), pitch_name(value['hi']),
                 value['lo'], value['hi']),
                'No %s notes (%s-%s) on PART DRUMS track.' %
                (DIFFICULTY_NAMES[difficulty], pitch_name(value['lo']),
                 pitch_name(value['hi'])))
    report, total = run_drums_checks(
        host, difficulty, events, all_notes,
        'Drums %s Validation  [%s-%s, %d-%d]' %
        (DIFFICULTY_NAMES[difficulty], pitch_name(value['lo']),
         pitch_name(value['hi']), value['lo'], value['hi']))
    higher = ADJACENT_HIGHER.get(difficulty)
    if higher:
        higher_events = read_drums_events(higher, all_notes)
        progression, extra = check_difficulty_progression(
            DIFFICULTY_NAMES[difficulty], DIFFICULTY_NAMES[higher],
            events, higher_events, value['lo'], DRUMS_RANGE[higher]['lo'])
        if progression:
            report = '\n'.join(progression) + '\n\n' + report
        total += extra
        if difficulty == 'H':
            hard_issues = (_check_hard_kicks(events, higher_events) +
                           _check_disco_unflip(text_events))
            if hard_issues:
                report += '\n'.join(hard_issues) + '\n\n'
                total += len(hard_issues)
    report += _hints(difficulty) + scan_disco_status(text_events)
    status = ('Validate Drums %s: all checks passed.' % difficulty
              if total == 0 else
              'Validate Drums %s: %d issue%s found.' %
              (difficulty, total, '' if total == 1 else 's'))
    return status, report


def validate_all_drums(host, track):
    all_notes, text_events = _read_track(host, track)
    lines = ['Drums Validate All', '']
    summary = []
    previous_difficulty = None
    previous_events = []
    for difficulty in DIFFICULTY_ORDER:
        value = DRUMS_RANGE[difficulty]
        events = read_drums_events(difficulty, all_notes)
        if not events:
            summary.append(difficulty + ':empty')
            lines.extend(('=== %s ===  (no notes in range %d-%d)' %
                          (DIFFICULTY_NAMES[difficulty], value['lo'],
                           value['hi']), ''))
        else:
            report, total = run_drums_checks(
                host, difficulty, events, all_notes,
                '=== Drums %s  [%d-%d] ===' %
                (DIFFICULTY_NAMES[difficulty], value['lo'], value['hi']))
            if (difficulty != 'X' and
                    previous_difficulty == ADJACENT_HIGHER[difficulty]):
                progression, extra = check_difficulty_progression(
                    DIFFICULTY_NAMES[difficulty],
                    DIFFICULTY_NAMES[previous_difficulty], events,
                    previous_events, value['lo'],
                    DRUMS_RANGE[previous_difficulty]['lo'])
                if progression:
                    report = '\n'.join(progression) + '\n\n' + report
                total += extra
                if difficulty == 'H':
                    hard_issues = (_check_hard_kicks(events, previous_events) +
                                   _check_disco_unflip(text_events))
                    if hard_issues:
                        report += '\n'.join(hard_issues) + '\n\n'
                        total += len(hard_issues)
            report += _hints(difficulty)
            summary.append(difficulty + (':OK' if total == 0
                                         else ':%d' % total))
            lines.extend(report.split('\n'))
        previous_difficulty, previous_events = difficulty, events
    lines.append(scan_disco_status(text_events))
    return ('Validate All Drums: %s' % ' | '.join(summary), '\n'.join(lines))
