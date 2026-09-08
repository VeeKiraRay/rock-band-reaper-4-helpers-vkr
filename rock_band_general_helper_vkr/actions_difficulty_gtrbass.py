"""Guitar/Bass difficulty validation and guarded tier copying.

Modern counterpart:
rock_band_general_helper_vkr/actions_difficulty_gtrbass.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .actions_difficulty import pitch_name
from .actions_difficulty_5k import format_time
from .actions_difficulty_shared import (
    check_difficulty_progression, compress_chord_offsets)
from .difficulty_read import _load_items, read_midi_notes
from lib.midi_chunk import MidiChunkError
from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources


GB_RANGE = {
    'X': {'lo': 96, 'hi': 100},
    'H': {'lo': 84, 'hi': 88},
    'M': {'lo': 72, 'hi': 75},
    'E': {'lo': 60, 'hi': 62},
}
GB_MAX_CHORD = {'X': 3, 'H': 2, 'M': 2, 'E': 1}
GB_MAX_SPAN = {'H': 3, 'M': 2}
GB_FORCE_HOPO_ALLOWED = {'X': True, 'H': True, 'M': False, 'E': False}
GB_ADVISORY_SPACING = {'M': 1.0, 'E': 2.0}
DIFFICULTY_NAMES = {
    'X': 'Expert', 'H': 'Hard', 'M': 'Medium', 'E': 'Easy'}
DIFFICULTY_ORDER = ('X', 'H', 'M', 'E')
ADJACENT_HIGHER = {'H': 'X', 'M': 'H', 'E': 'M'}
INSTRUMENTS = {
    'gtr': {'label': 'Guitar', 'track': 'PART GUITAR'},
    'bass': {'label': 'Bass', 'track': 'PART BASS'},
}
GEM_NAMES = ('Green', 'Red', 'Yellow', 'Blue', 'Orange')
GRACE = 0.05
EPS_QN = 0.01


def gem_name(pitch):
    for value in GB_RANGE.values():
        offset = pitch - value['lo']
        if 0 <= offset <= 4:
            return GEM_NAMES[offset]
    return pitch_name(pitch)


def event_label(pitches):
    names = [gem_name(pitch) for pitch in pitches]
    return names[0] if len(names) == 1 else '[%s]' % '+'.join(names)


def _all_track_notes(host, track):
    return read_midi_notes(host, _load_items(host, track))


def read_gtrbass_events(host, track, difficulty, all_notes=None):
    value = GB_RANGE[difficulty]
    if all_notes is None:
        all_notes = _all_track_notes(host, track)
    notes = [note for note in all_notes
             if value['lo'] <= note['pitch'] <= value['lo'] + 4]
    events = []
    index = 0
    while index < len(notes):
        first = notes[index]
        event = {
            's': first['s'], 'e': first['e'],
            'qn': first['qn'], 'qn_e': first['qn_e'],
            'pitches': [first['pitch']],
        }
        following = index + 1
        while (following < len(notes) and
               notes[following]['s'] - event['s'] <= 0.002):
            note = notes[following]
            event['pitches'].append(note['pitch'])
            if note['e'] > event['e']:
                event['e'] = note['e']
                event['qn_e'] = note['qn_e']
            following += 1
        event['pitches'].sort()
        events.append(event)
        index = following
    return events


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


def _check_chord_count(events, maximum, difficulty):
    issues = []
    for event in events:
        if len(event['pitches']) > maximum:
            limit = 'no chords' if maximum == 1 else 'max %d' % maximum
            issues.append('%s: %s has %d notes (%s for %s)' % (
                format_time(event['s']), event_label(event['pitches']),
                len(event['pitches']), limit,
                DIFFICULTY_NAMES[difficulty]))
    return issues


def _check_chord_shape(events, difficulty):
    issues = []
    advisories = []
    for event in events:
        if len(event['pitches']) < 2:
            continue
        span = event['pitches'][-1] - event['pitches'][0]
        if difficulty == 'X' and len(event['pitches']) == 3 and span == 4:
            issues.append(
                '%s: %s illegal 3-note chord '
                '(Green+Orange combination not allowed)' %
                (format_time(event['s']), event_label(event['pitches'])))
        elif difficulty == 'X' and len(event['pitches']) == 2 and span == 4:
            advisories.append('%s: %s (Green+Orange) - use as sparingly as possible' %
                              (format_time(event['s']),
                               event_label(event['pitches'])))
        elif difficulty in GB_MAX_SPAN and span > GB_MAX_SPAN[difficulty]:
            issues.append('%s: %s spans %d frets (max %d for %s)' % (
                format_time(event['s']), event_label(event['pitches']), span,
                GB_MAX_SPAN[difficulty], DIFFICULTY_NAMES[difficulty]))
    return issues, advisories


def _duration_seconds(host, qn, length):
    return host.qn_to_time(qn + length) - host.qn_to_time(qn)


def _check_note_length(host, events):
    issues = []
    for event in events:
        minimum = _duration_seconds(host, event['qn'], 0.0625)
        duration = event['e'] - event['s']
        if duration < minimum - 0.001:
            issues.append(
                '%s: %s is %.1f ms long (min 1/64 note ~= %.1f ms)' %
                (format_time(event['s']), event_label(event['pitches']),
                 duration * 1000, minimum * 1000))
    return issues


def _check_overlap(events):
    issues = []
    for previous, current in zip(events, events[1:]):
        if current['s'] < previous['e'] - 0.001:
            issues.append(
                '%s: %s starts %.1f ms before previous event ends' %
                (format_time(current['s']), event_label(current['pitches']),
                 (previous['e'] - current['s']) * 1000))
    return issues


def _check_sustain_gaps(host, events, difficulty):
    issues = []
    for event, following in zip(events, events[1:]):
        if following['s'] < event['e'] - 0.001:
            continue
        duration_qn = event['qn_e'] - event['qn']
        if difficulty in ('M', 'E'):
            if duration_qn < 0.5 - EPS_QN:
                continue
            minimum_qn = 1.0
            label = '1/4 note'
        else:
            sustain_threshold = _duration_seconds(
                host, event['qn'], 0.75)
            if event['e'] - event['s'] <= sustain_threshold + 0.001:
                continue
            minimum_qn = 0.125
            label = '1/32 note'
        gap_qn = following['qn'] - event['qn_e']
        if gap_qn < minimum_qn * (1 - GRACE):
            minimum = _duration_seconds(host, event['qn_e'], minimum_qn)
            issues.append(
                '%s: %s ends %.1f ms before %s '
                '(need %s gap ~= %.1f ms)' %
                (format_time(following['s']), event_label(event['pitches']),
                 (following['s'] - event['e']) * 1000,
                 event_label(following['pitches']), label, minimum * 1000))
    return issues


def _check_spacing_advisory(host, events, difficulty):
    spacing = GB_ADVISORY_SPACING.get(difficulty)
    if spacing is None:
        return []
    issues = []
    for previous, current in zip(events, events[1:]):
        gap_qn = current['qn'] - previous['qn']
        if gap_qn < spacing * (1 - GRACE):
            minimum = _duration_seconds(host, previous['qn'], spacing)
            label = '1/4 note' if spacing == 1.0 else '1/2 note'
            issues.append(
                '%s: %s is %.0f ms after previous '
                '(advisory: %s grid ~= %.0f ms recommended for %s)' %
                (format_time(current['s']), event_label(current['pitches']),
                 (current['s'] - previous['s']) * 1000, label,
                 minimum * 1000, DIFFICULTY_NAMES[difficulty]))
    return issues


def _check_force_hopo(all_notes, difficulty):
    value = GB_RANGE[difficulty]
    force_pitches = (value['lo'] + 5, value['lo'] + 6)
    return [
        '%s: force-HOPO marker found (not allowed on %s)' %
        (format_time(note['s']), DIFFICULTY_NAMES[difficulty])
        for note in all_notes if note['pitch'] in force_pitches]


def _check_trill_velocity(all_notes):
    issues = []
    for note in all_notes:
        if note['pitch'] in (126, 127) and note['velocity'] <= 40:
            kind = 'Tremolo' if note['pitch'] == 126 else 'Trill'
            issues.append(
                '%s: %s marker velocity %d (need 41-50 for Hard '
                'eligibility - Magma will report a spacing error)' %
                (format_time(note['s']), kind, note['velocity']))
    return issues


def _build_report(header, categories):
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
    return '\n'.join(lines), total


def run_gtrbass_checks(host, difficulty, events, all_notes, header=None):
    value = GB_RANGE[difficulty]
    maximum = GB_MAX_CHORD[difficulty]
    shape_issues, shape_advisories = _check_chord_shape(events, difficulty)
    categories = [
        ('Notes outside valid range',
         _check_out_of_range(events, value['hi'])),
        (('Chords (none allowed on Easy)' if difficulty == 'E' else
          'Max chord (%d notes)' % maximum),
         _check_chord_count(events, maximum, difficulty)),
        ('Chord shape restrictions', shape_issues),
    ]
    if shape_advisories:
        categories.append((
            'Advisory: Green+Orange chords (use sparingly)',
            shape_advisories))
    categories.extend((
        ('Note length (min 1/64)', _check_note_length(host, events)),
        ('Overlapping notes', _check_overlap(events)),
        (('Sustain gaps (min 1/4 note gap to next)'
          if difficulty in ('M', 'E') else
          'Sustain gaps (min 1/32 note)'),
         _check_sustain_gaps(host, events, difficulty)),
    ))
    if difficulty in GB_ADVISORY_SPACING:
        categories.append((
            'Advisory: note density grid',
            _check_spacing_advisory(host, events, difficulty)))
    if not GB_FORCE_HOPO_ALLOWED[difficulty]:
        categories.append((
            'Force-HOPO markers (not allowed on Medium/Easy)',
            _check_force_hopo(all_notes, difficulty)))
    if difficulty == 'H':
        categories.append((
            'Trill/Tremolo velocity (Hard eligibility)',
            _check_trill_velocity(all_notes)))
    return _build_report(
        header or 'Guitar/Bass %s Validation' %
        DIFFICULTY_NAMES[difficulty], categories)


def validate_gtrbass(host, track, instrument, difficulty):
    spec = INSTRUMENTS[instrument]
    value = GB_RANGE[difficulty]
    all_notes = _all_track_notes(host, track)
    events = read_gtrbass_events(
        host, track, difficulty, all_notes=all_notes)
    if not events:
        return (
            'Validate %s %s: no notes in MIDI range %d-%d.' %
            (spec['label'], difficulty, value['lo'], value['hi']),
            'No %s notes (MIDI %d-%d) on %s track.' %
            (DIFFICULTY_NAMES[difficulty], value['lo'], value['hi'],
             spec['track']))
    report, total = run_gtrbass_checks(
        host, difficulty, events, all_notes,
        '%s %s Validation  [%s-%s, %d-%d]' %
        (spec['label'], DIFFICULTY_NAMES[difficulty],
         pitch_name(value['lo']), pitch_name(value['hi']),
         value['lo'], value['hi']))
    higher = ADJACENT_HIGHER.get(difficulty)
    if higher:
        higher_events = read_gtrbass_events(
            host, track, higher, all_notes=all_notes)
        progression, extra = check_difficulty_progression(
            DIFFICULTY_NAMES[difficulty], DIFFICULTY_NAMES[higher],
            events, higher_events, value['lo'], GB_RANGE[higher]['lo'])
        if progression:
            report = '\n'.join(progression) + '\n\n' + report
        total += extra
    status = ('Validate %s %s: all checks passed.' %
              (spec['label'], difficulty)
              if total == 0 else
              'Validate %s %s: %d issue%s found.' %
              (spec['label'], difficulty, total,
               '' if total == 1 else 's'))
    return status, report


def validate_all_gtrbass(host, track, instrument):
    spec = INSTRUMENTS[instrument]
    all_notes = _all_track_notes(host, track)
    lines = ['%s Validate All' % spec['label'], '']
    summary = []
    previous_difficulty = None
    previous_events = []
    for difficulty in DIFFICULTY_ORDER:
        value = GB_RANGE[difficulty]
        events = read_gtrbass_events(
            host, track, difficulty, all_notes=all_notes)
        if not events:
            summary.append(difficulty + ':empty')
            lines.extend((
                '=== %s ===  (no notes in range %d-%d)' %
                (DIFFICULTY_NAMES[difficulty], value['lo'], value['hi']),
                ''))
        else:
            report, total = run_gtrbass_checks(
                host, difficulty, events, all_notes,
                '=== %s %s  [%d-%d] ===' %
                (spec['label'], DIFFICULTY_NAMES[difficulty],
                 value['lo'], value['hi']))
            if (difficulty != 'X' and
                    previous_difficulty == ADJACENT_HIGHER[difficulty]):
                progression, extra = check_difficulty_progression(
                    DIFFICULTY_NAMES[difficulty],
                    DIFFICULTY_NAMES[previous_difficulty],
                    events, previous_events, value['lo'],
                    GB_RANGE[previous_difficulty]['lo'])
                if progression:
                    report = '\n'.join(progression) + '\n\n' + report
                total += extra
            summary.append(
                difficulty + (':OK' if total == 0 else ':%d' % total))
            lines.extend(report.split('\n'))
        previous_difficulty, previous_events = difficulty, events
    return ('Validate All %s: %s' %
            (spec['label'], ' | '.join(summary)), '\n'.join(lines))


def _context_source_events(host, context, source):
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


def _gtrbass_copy_preview(host, track, instrument, difficulty):
    if instrument not in INSTRUMENTS:
        raise MidiChunkError('Unknown Guitar/Bass instrument selection.')
    higher = ADJACENT_HIGHER.get(difficulty)
    if higher is None:
        raise MidiChunkError(
            'Guitar/Bass can only copy to Hard, Medium, or Easy.')
    contexts = _load_items(host, track)
    if not contexts:
        raise MidiChunkError('%s has no MIDI items.' %
                             INSTRUMENTS[instrument]['track'])

    source = GB_RANGE[higher]
    target = GB_RANGE[difficulty]
    target_max = target['hi'] - target['lo']
    source_count = 0
    target_count = 0
    output_count = 0
    replacements_by_context = []
    for context in contexts:
        events = _context_source_events(host, context, source)
        replacements = []
        for event in events:
            source_count += len(event['offsets'])
            new_offsets = compress_chord_offsets(
                event['offsets'], target_max)
            for offset in new_offsets:
                replacements.append({
                    'start_tick': event['start_tick'],
                    'end_tick': event['end_tick'],
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
            'plans': [], 'source': higher, 'target': difficulty,
            'source_count': 0, 'output_count': 0,
            'target_count': target_count,
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
        'plans': plans, 'source': higher, 'target': difficulty,
        'source_count': source_count, 'output_count': output_count,
        'target_count': target_count,
    }


def copy_gtrbass(host, track, instrument, difficulty,
                 confirm_overwrite=None):
    """Copy the adjacent higher Guitar/Bass tier into ``difficulty``."""
    spec = INSTRUMENTS[instrument]
    preview = _gtrbass_copy_preview(
        host, track, instrument, difficulty)
    higher = preview['source']
    if preview['source_count'] == 0:
        value = GB_RANGE[higher]
        return (
            'Copy %s to %s: no notes on %s to copy.' %
            (spec['label'], DIFFICULTY_NAMES[difficulty],
             DIFFICULTY_NAMES[higher]),
            '%s %s range (%d-%d) has no notes.' %
            (spec['label'], DIFFICULTY_NAMES[higher], value['lo'],
             value['hi']))

    if preview['target_count'] > 0:
        message = ('%s %s range already has %d note%s. Clear it and '
                   'overwrite it with a copy of %s?' %
                   (spec['label'], DIFFICULTY_NAMES[difficulty],
                    preview['target_count'],
                    '' if preview['target_count'] == 1 else 's',
                    DIFFICULTY_NAMES[higher]))
        if confirm_overwrite is None or not confirm_overwrite(message):
            return ('Copy %s to %s cancelled.' %
                    (spec['label'], DIFFICULTY_NAMES[difficulty]),
                    'No project changes were made.')

    description = 'Copy %s %s to %s' % (
        spec['label'], higher, difficulty)
    changed_items = apply_verified_item_chunks(
        host, preview['plans'], description)
    compression_note = ''
    if preview['output_count'] != preview['source_count']:
        compression_note = (' Chord compression produced %d target notes '
                            'from %d source notes.' %
                            (preview['output_count'],
                             preview['source_count']))
    return (
        'Copy %s to %s: copied %d notes from %s.' %
        (spec['label'], DIFFICULTY_NAMES[difficulty],
         preview['output_count'], DIFFICULTY_NAMES[higher]),
        'Replaced the %s range on %d MIDI item%s. Undo: %s.%s' %
        (DIFFICULTY_NAMES[difficulty], changed_items,
         '' if changed_items == 1 else 's', description,
         compression_note))
