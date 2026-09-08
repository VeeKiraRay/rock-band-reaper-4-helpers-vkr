"""5-lane Keys difficulty validation and guarded tier copying.

Modern counterpart:
rock_band_general_helper_vkr/actions_difficulty_5k.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .actions_difficulty_shared import (
    check_difficulty_progression,
    compress_chord_offsets,
    count_notes,
)
from .difficulty_read import _load_items, read_gem_events, read_midi_notes
from lib.midi_chunk import MidiChunkError
from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources


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
PK_PLAYABLE_LO = 48
PK_PLAYABLE_HI = 72
PK_REDUCE_TOLERANCE_QN = 0.125


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


def _context_keys_source_events(host, context, source):
    notes = [note for note in context['parsed'].notes()
             if source['lo'] <= note.pitch <= source['lo'] + 4]
    events = []
    index = 0
    while index < len(notes):
        first = notes[index]
        first_qn = (context['start_qn'] - context['offset_qn'] +
                    float(first.start_tick) / context['parsed'].ppq)
        first_time = host.qn_to_time(first_qn)
        event = {
            'start_tick': first.start_tick,
            'end_tick': first.end_tick,
            'qn': first_qn,
            'offsets': [first.pitch - source['lo']],
        }
        following = index + 1
        while following < len(notes):
            note = notes[following]
            note_qn = (context['start_qn'] - context['offset_qn'] +
                       float(note.start_tick) / context['parsed'].ppq)
            if host.qn_to_time(note_qn) - first_time > 0.002:
                break
            event['offsets'].append(note.pitch - source['lo'])
            event['end_tick'] = max(event['end_tick'], note.end_tick)
            following += 1
        event['offsets'].sort()
        events.append(event)
        index = following
    return events


def _read_pro_keys_guide(host, track):
    contexts = _load_items(host, track)
    notes = read_midi_notes(host, contexts, PK_PLAYABLE_LO, PK_PLAYABLE_HI)
    events = []
    index = 0
    while index < len(notes):
        first = notes[index]
        event = {'qn': first['qn'], 'qn_e': first['qn_e']}
        following = index + 1
        while (following < len(notes) and
               notes[following]['s'] - first['s'] <= 0.002):
            event['qn_e'] = max(event['qn_e'], notes[following]['qn_e'])
            following += 1
        events.append(event)
        index = following
    guards = [{
        'item': context['item'], 'original': context['chunk'],
        'fingerprint': context['fingerprint'],
    } for context in contexts]
    return events, guards


def _nearby_pro_keys_event(events, target_qn):
    best = None
    best_difference = None
    for event in events:
        difference = abs(event['qn'] - target_qn)
        if (difference <= PK_REDUCE_TOLERANCE_QN and
                (best_difference is None or difference < best_difference)):
            best = event
            best_difference = difference
    return best


def _keys_copy_preview(host, track, difficulty, guide_enabled=False,
                       guide_track=None):
    higher = ADJACENT_HIGHER.get(difficulty)
    if higher is None:
        raise MidiChunkError('Keys can only copy to Hard, Medium, or Easy.')
    contexts = _load_items(host, track)
    if not contexts:
        raise MidiChunkError('PART KEYS has no MIDI items.')

    guide_events = None
    guide_guards = []
    guide_skip_reason = None
    if guide_enabled:
        if guide_track is None:
            guide_skip_reason = 'PART REAL_KEYS_%s not selected' % difficulty
        else:
            guide_events, guide_guards = _read_pro_keys_guide(
                host, guide_track)
            if not guide_events:
                guide_events = None
                guide_skip_reason = ('PART REAL_KEYS_%s has no notes' %
                                     difficulty)

    source = K5_RANGE[higher]
    target = K5_RANGE[difficulty]
    target_max = target['hi'] - target['lo']
    source_count = 0
    target_count = 0
    output_count = 0
    kept_events = 0
    dropped_events = 0
    replacements_by_context = []
    for context in contexts:
        events = _context_keys_source_events(host, context, source)
        replacements = []
        for event in events:
            source_count += len(event['offsets'])
            guide_match = (_nearby_pro_keys_event(
                guide_events, event['qn']) if guide_events else None)
            if guide_events and guide_match is None:
                dropped_events += 1
                continue
            kept_events += 1
            end_tick = event['end_tick']
            if guide_match is not None:
                duration_qn = guide_match['qn_e'] - guide_match['qn']
                end_tick = event['start_tick'] + int(round(
                    duration_qn * context['parsed'].ppq))
                end_tick = max(event['start_tick'] + 1, end_tick)
            new_offsets = compress_chord_offsets(
                event['offsets'], target_max)
            for offset in new_offsets:
                replacements.append({
                    'start_tick': event['start_tick'],
                    'end_tick': end_tick,
                    'pitch': target['lo'] + offset,
                    'velocity': 100,
                    'channel': 0,
                })
                output_count += 1
        for note in context['parsed'].notes():
            if target['lo'] <= note.pitch <= target['lo'] + 4:
                target_count += 1
        replacements_by_context.append((context, replacements))

    if source_count == 0:
        return {
            'plans': [], 'guard_plans': [], 'source': higher,
            'source_count': 0, 'output_count': 0,
            'target_count': target_count, 'guide_enabled': guide_enabled,
            'guide_applied': False, 'guide_skip_reason': guide_skip_reason,
            'kept_events': 0, 'dropped_events': 0,
        }

    verify_unshared_pool_sources(host, contexts)
    plans = []
    for context, replacements in replacements_by_context:
        expected = context['parsed'].with_replaced_notes(
            target['lo'], target['lo'] + 4, replacements)
        plans.append({
            'item': context['item'], 'original': context['chunk'],
            'fingerprint': context['fingerprint'], 'expected': expected,
        })
    return {
        'plans': plans, 'guard_plans': guide_guards, 'source': higher,
        'source_count': source_count, 'output_count': output_count,
        'target_count': target_count, 'guide_enabled': guide_enabled,
        'guide_applied': guide_events is not None,
        'guide_skip_reason': guide_skip_reason,
        'kept_events': kept_events, 'dropped_events': dropped_events,
    }


def copy_keys(host, track, difficulty, guide_enabled=False,
              guide_track=None, confirm_overwrite=None):
    """Copy the adjacent Keys tier, optionally guided by same-tier Pro Keys."""
    preview = _keys_copy_preview(
        host, track, difficulty, guide_enabled, guide_track)
    higher = preview['source']
    if preview['source_count'] == 0:
        value = K5_RANGE[higher]
        return (
            'Copy to %s: no notes on %s to copy.' %
            (DIFFICULTY_NAMES[difficulty], DIFFICULTY_NAMES[higher]),
            '%s range (%d-%d) has no notes on PART KEYS.' %
            (DIFFICULTY_NAMES[higher], value['lo'], value['hi']))

    if preview['target_count'] > 0:
        message = ('%s range already has %d note%s. Clear it and overwrite '
                   'it with a copy of %s?' %
                   (DIFFICULTY_NAMES[difficulty], preview['target_count'],
                    '' if preview['target_count'] == 1 else 's',
                    DIFFICULTY_NAMES[higher]))
        if confirm_overwrite is None or not confirm_overwrite(message):
            return ('Copy to %s cancelled.' % DIFFICULTY_NAMES[difficulty],
                    'No project changes were made.')

    description = 'Copy Keys %s to %s' % (higher, difficulty)
    changed_items = apply_verified_item_chunks(
        host, preview['plans'], description, preview['guard_plans'])
    guide_note = ''
    if preview['guide_enabled']:
        if preview['guide_applied']:
            total_events = preview['kept_events'] + preview['dropped_events']
            guide_note = (' %d of %d events kept using PART REAL_KEYS_%s '
                          'as a guide.' %
                          (preview['kept_events'], total_events, difficulty))
        else:
            guide_note = (' Pro Keys reduction skipped: %s.' %
                          preview['guide_skip_reason'])
    compression_note = ''
    if (not preview['guide_applied'] and
            preview['output_count'] != preview['source_count']):
        compression_note = (' Chord compression produced %d target notes '
                            'from %d source notes.' %
                            (preview['output_count'],
                             preview['source_count']))
    return (
        'Copy to %s: copied %d notes from %s.' %
        (DIFFICULTY_NAMES[difficulty], preview['output_count'],
         DIFFICULTY_NAMES[higher]),
        'Replaced the %s range on %d MIDI item%s. Undo: %s.%s%s' %
        (DIFFICULTY_NAMES[difficulty], changed_items,
         '' if changed_items == 1 else 's', description,
         guide_note, compression_note))
