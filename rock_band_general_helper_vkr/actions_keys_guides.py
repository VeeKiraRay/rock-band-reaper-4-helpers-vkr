"""Pure Pro Keys and Vocal Tab Input guide actions.

Modern counterpart:
rock_band_general_helper_vkr/actions_keys_guides.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .actions_guitar_guide import parse_tab, pitch_name


PK_MIN = 48
PK_MAX = 72
VOC_MIN = 36
VOC_MAX = 84
SHIFTS = (-48, -36, -24, -12, 0, 12, 24)

PK_RANGES = (
    ('C2-E3', 48, 64, 1),
    ('D2-F3', 50, 65, 3),
    ('E2-G3', 52, 67, 2),
    ('F2-A3', 53, 69, 1),
    ('G2-B3', 55, 71, 3),
    ('A2-C4', 57, 72, 1),
)
PK_PREF_LABEL = {
    1: '[preferred]',
    2: '[common alternative]',
    3: '[less common]',
}


def _event_label(pitches):
    names = [pitch_name(pitch) for pitch in pitches]
    if len(names) == 1:
        return names[0]
    return '[' + '+'.join(names) + ']'


def _raw_events(text, vertical):
    result = []
    for event in parse_tab(text, vertical):
        result.append({
            'raws': sorted(event.pitches),
            'phrase_index': event.phrase_index,
        })
    return result


def _best_shift(events, minimum, maximum):
    best = None
    for shift in SHIFTS:
        pitches = sorted(raw + shift for event in events
                         for raw in event['raws'])
        outside = sum(1 for pitch in pitches
                      if pitch < minimum or pitch > maximum)
        median = pitches[(len(pitches) - 1) // 2]
        candidate = (outside, abs(median - 60), shift)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best[2], best[0]


def _shift_label(shift):
    if shift == 0:
        return '(no shift)'
    return '%+d oct (%+d semitones)' % (shift // 12, shift)


def _prepare(text, vertical, label, minimum, maximum):
    events = _raw_events(text, vertical)
    if not events:
        return None, None, None, (
            '%s: no notes found' % label,
            'No notes found. Use digits for played strings and dashes for '
            'unplayed strings.')
    shift, outside = _best_shift(events, minimum, maximum)
    for event in events:
        event['pitches'] = sorted(raw + shift for raw in event['raws'])
    return events, shift, outside, None


def _common_header(events, shift):
    total_notes = sum(len(event['pitches']) for event in events)
    phrases = events[-1]['phrase_index']
    note_text = ('%d events' % len(events) if total_notes == len(events)
                 else '%d events, %d notes total' % (
                     len(events), total_notes))
    phrase_text = ('1 phrase' if phrases == 1
                   else '%d phrases' % phrases)
    lines = [
        'Events after shift %s:' % _shift_label(shift),
        '  '.join(_event_label(event['pitches']) for event in events),
        '(%s, %s)' % (note_text, phrase_text),
        '',
    ]
    return lines


def _span_warnings(events):
    warnings = []
    for index, event in enumerate(events):
        pitches = event['pitches']
        if len(pitches) > 1 and pitches[-1] - pitches[0] > 12:
            warnings.append(
                '  Event %d: %s spans %d semitones (max 12 for Expert)' % (
                    index + 1, _event_label(pitches),
                    pitches[-1] - pitches[0]))
    return warnings


def pro_keys_tab_guide(text, vertical=False, animation=False):
    events, shift, outside, error = _prepare(
        text, vertical, 'Pro Keys guide', PK_MIN, PK_MAX)
    if error:
        return error
    lines = _common_header(events, shift)
    warnings = _span_warnings(events)

    if animation:
        lines.extend([
            'Animation mode - full C2-C4 range (no lane window).',
            '',
        ])
        if outside == 0:
            lines.append('All notes fit within C2-C4.')
        else:
            lines.append('%d note(s) fall outside C2-C4.' % outside)
        status = 'Pro Keys guide (animation): %s - %s' % (
            _shift_label(shift),
            'all fit C2-C4' if outside == 0 else '%d out of C2-C4' % outside)
    else:
        best = None
        for name, low, high, preference in PK_RANGES:
            in_count = sum(1 for event in events
                           if all(low <= pitch <= high
                                  for pitch in event['pitches']))
            all_pitches = [pitch for event in events
                           for pitch in event['pitches']]
            note_center = (min(all_pitches) + max(all_pitches)) / 2.0
            score = (in_count * 10000 -
                     abs(note_center - (low + high) / 2.0) * 10 -
                     preference)
            candidate = (score, name, low, high, preference, in_count)
            if best is None or candidate[0] > best[0]:
                best = candidate
        unused_score, name, low, high, preference, in_count = best
        lines.append('Suggested range: %s  %s  (%d/%d events fit)' % (
            name, PK_PREF_LABEL[preference], in_count, len(events)))
        out_events = []
        for index, event in enumerate(events):
            bad = [pitch for pitch in event['pitches']
                   if pitch < low or pitch > high]
            if bad:
                out_events.append('  Event %d (phrase %d): %s' % (
                    index + 1, event['phrase_index'],
                    _event_label(event['pitches'])))
        if out_events:
            lines.extend(['', 'Out of range for %s:' % name] + out_events)
        else:
            lines.extend(['', 'All %d events fit within %s.' % (
                len(events), name)])
        status = 'Pro Keys guide: %s - suggested %s (%d/%d fit)' % (
            _shift_label(shift), name, in_count, len(events))

    if warnings:
        lines.extend(['', 'Chord span warnings:'] + warnings)
    return status, '\n'.join(lines)


def vocal_tab_guide(text, vertical=False):
    events, shift, outside, error = _prepare(
        text, vertical, 'Vocal guide', VOC_MIN, VOC_MAX)
    if error:
        return error
    lines = _common_header(events, shift)
    if outside == 0:
        lines.append('All notes fit within C1-C5.')
    else:
        lines.extend([
            '%d note(s) fall outside C1-C5 after the best shift.' % outside,
            'Consider re-voicing those notes or splitting the passage.',
        ])
    warnings = _span_warnings(events)
    if warnings:
        lines.extend(['', 'Chord span warnings:'] + warnings)
    status = 'Vocal guide: %s - %s' % (
        _shift_label(shift),
        'all fit C1-C5' if outside == 0 else '%d out of C1-C5' % outside)
    return status, '\n'.join(lines)

