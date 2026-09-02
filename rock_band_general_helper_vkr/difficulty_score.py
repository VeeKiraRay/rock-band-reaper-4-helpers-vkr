"""Pure difficulty factors shared by the legacy chart readers.

The functions port the exact factors selected by the six frozen models and
retain the names and definitions of the modern Lua scorers.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import math


PEAK_WINDOW_S = 8.0
PEAK_PCTL = 0.95
ENTROPY_K = 2
FALLBACK_GAP_QN = 8.0
OFFBEAT_TOL = 0.02
VOCAL_PEAK_WINDOW_S = 10.0
VOCAL_PEAK_PCTL = 0.95


def percentile(sorted_values, proportion):
    count = len(sorted_values)
    if count == 0:
        return 0
    if count == 1:
        return sorted_values[0]
    index = proportion * (count - 1)
    lo = int(math.floor(index))
    hi = int(math.ceil(index))
    if lo == hi:
        return sorted_values[lo]
    fraction = index - lo
    return (sorted_values[lo] +
            (sorted_values[hi] - sorted_values[lo]) * fraction)


def normalize_spans(spans):
    ordered = sorted(
        ({'s': span['s'], 'e': span['e']} for span in (spans or [])
         if span['e'] > span['s']),
        key=lambda span: span['s'])
    merged = []
    for span in ordered:
        if merged and span['s'] <= merged[-1]['e']:
            merged[-1]['e'] = max(merged[-1]['e'], span['e'])
        else:
            merged.append(span)
    return merged


def normalize_vocal_phrases(spans):
    """Sort and clip vocal phrases without merging touching boundaries."""
    ordered = sorted(
        ({'s': span['s'], 'e': span['e']} for span in (spans or [])
         if span['e'] > span['s']),
        key=lambda span: (span['s'], span['e']))
    kept = []
    for span in ordered:
        if kept and span['s'] < kept[-1]['e']:
            span['s'] = kept[-1]['e']
        if span['e'] > span['s']:
            kept.append(span)
    return kept


def _subtract_vocal_percussion(spans, percussion_spans, notes):
    empty_ranges = []
    for percussion in percussion_spans or []:
        if not any(percussion['s'] <= note['s'] <= percussion['e']
                   for note in notes):
            empty_ranges.append(percussion)
    if not empty_ranges:
        return spans
    pieces = []
    for span in spans:
        remaining = [dict(span)]
        for drop in empty_ranges:
            following = []
            for piece in remaining:
                if drop['e'] <= piece['s'] or drop['s'] >= piece['e']:
                    following.append(piece)
                else:
                    if drop['s'] > piece['s']:
                        following.append(
                            {'s': piece['s'], 'e': drop['s']})
                    if drop['e'] < piece['e']:
                        following.append(
                            {'s': drop['e'], 'e': piece['e']})
            remaining = following
        pieces.extend(piece for piece in remaining
                      if piece['e'] > piece['s'])
    return normalize_spans(pieces)


def _vocal_lyric_class(text):
    if text is None:
        return 'syllable'
    try:
        text = text.decode('latin-1')
    except AttributeError:
        pass
    stripped = text.rstrip()
    if stripped == '+':
        return 'plus'
    if stripped.endswith('^'):
        return 'caret'
    if stripped.endswith('#'):
        return 'hash'
    return 'syllable'


def _vocal_pitch_class_distance(left, right):
    distance = (left - right) % 12
    return 12 - distance if distance > 6 else distance


def _vocal_peak(segments):
    rates = []
    for segment in segments:
        for index, note in enumerate(segment):
            total = 0
            for following in segment[index:]:
                if following['s'] - note['s'] > VOCAL_PEAK_WINDOW_S:
                    break
                if following['cls'] != 'plus':
                    total += 1
            rates.append(float(total) / VOCAL_PEAK_WINDOW_S)
    if not rates:
        return 0
    rates.sort()
    return percentile(rates, VOCAL_PEAK_PCTL)


def score_vocals(notes, spans, percussion_spans=None, vocal_parts=1):
    """Return the exact factors selected by the frozen Vocals model."""
    keys = (
        'syl_density_avg', 'syl_density_peak', 'tight_p10', 'tight_med',
        'pc_interval_mean', 'playing_s', 'notated_range', 'pitch_p90',
        'octave_jump_rate', 'parts_3', 'high_time_70',
        'pc_change_rate')
    result = dict((key, 0) for key in keys)
    result.update({
        'syllables_total': 0,
        'tubes_total': 0,
        'vocal_parts': vocal_parts,
        'parts_3': 1 if vocal_parts >= 3 else 0,
        'no_playing_time': False,
    })
    phrases = normalize_vocal_phrases(spans)
    phrases = _subtract_vocal_percussion(
        phrases, percussion_spans, notes)
    playing_s = total_span_seconds(phrases)
    result['playing_s'] = playing_s
    if playing_s <= 0:
        result['no_playing_time'] = True
        return result

    segments = events_in_segments(notes, phrases)
    in_span = [note for segment in segments for note in segment]
    if not in_span:
        return result
    for note in in_span:
        note['cls'] = _vocal_lyric_class(note.get('lyric'))

    result['tubes_total'] = len(in_span)
    result['syllables_total'] = sum(
        1 for note in in_span if note['cls'] != 'plus')
    result['syl_density_avg'] = (
        float(result['syllables_total']) / playing_s)
    result['syl_density_peak'] = _vocal_peak(segments)

    gaps = []
    pitch_class_intervals = []
    pitch_class_changes = 0
    for segment in segments:
        for index in range(1, len(segment)):
            note = segment[index]
            previous = segment[index - 1]
            distance = _vocal_pitch_class_distance(
                note['pitch'], previous['pitch'])
            pitch_class_intervals.append(distance)
            if distance > 0:
                pitch_class_changes += 1
            gaps.append(note['qn'] - previous['qn'])
    result['pc_change_rate'] = float(pitch_class_changes) / playing_s
    if pitch_class_intervals:
        result['pc_interval_mean'] = (
            float(sum(pitch_class_intervals)) /
            len(pitch_class_intervals))
    if gaps:
        gaps.sort()
        result['tight_p10'] = percentile(gaps, 0.10)
        result['tight_med'] = percentile(gaps, 0.50)

    pitched_segments = []
    for segment in segments:
        pitched = [note for note in segment
                   if note['cls'] not in ('hash', 'caret')]
        if pitched:
            pitched_segments.append(pitched)
    pitched_notes = [note for segment in pitched_segments
                     for note in segment]
    if pitched_notes:
        pitches = sorted(note['pitch'] for note in pitched_notes)
        result['notated_range'] = pitches[-1] - pitches[0]
        result['pitch_p90'] = percentile(pitches, 0.90)
        octave_jumps = 0
        for segment in pitched_segments:
            for index in range(1, len(segment)):
                if abs(segment[index]['pitch'] -
                       segment[index - 1]['pitch']) >= 12:
                    octave_jumps += 1
        result['octave_jump_rate'] = float(octave_jumps) / playing_s
        sung_s = sum(max(0, note['e'] - note['s'])
                     for note in pitched_notes)
        if sung_s > 0:
            high_s = sum(
                note['e'] - note['s'] for note in pitched_notes
                if note['pitch'] >= 70 and note['e'] > note['s'])
            result['high_time_70'] = float(high_s) / sung_s
    return result


def derive_spans_from_events(events, gap_qn=FALLBACK_GAP_QN):
    if not events:
        return []
    spans = []
    current_start = events[0]['s']
    current_end = max(events[0]['e'], events[0]['s'])
    previous_qn = events[0]['qn']
    for event in events[1:]:
        if event['qn'] - previous_qn > gap_qn:
            spans.append({'s': current_start, 'e': current_end})
            current_start = event['s']
            current_end = max(event['e'], event['s'])
        current_end = max(current_end, event['e'])
        previous_qn = event['qn']
    spans.append({'s': current_start, 'e': current_end})
    return normalize_spans(spans)


def events_in_segments(events, spans):
    segments = []
    span_index = 0
    current = None
    for event in events:
        while (span_index < len(spans) and
               spans[span_index]['e'] < event['s']):
            span_index += 1
            current = None
        if span_index >= len(spans):
            break
        span = spans[span_index]
        if span['s'] <= event['s'] <= span['e']:
            if current is None:
                current = []
                segments.append(current)
            current.append(event)
    return segments


def peak_density(segments, window_s=PEAK_WINDOW_S,
                 proportion=PEAK_PCTL, weight=None):
    if window_s <= 0:
        return 0, 0
    densities = []
    if weight is None:
        weight = lambda event: len(event['pitches'])
    for segment in segments:
        right = 0
        running = 0
        for left, event in enumerate(segment):
            if left > 0:
                running -= weight(segment[left - 1])
            limit = event['s'] + window_s
            while right < len(segment) and segment[right]['s'] <= limit:
                running += weight(segment[right])
                right += 1
            densities.append(float(running) / window_s)
    if not densities:
        return 0, 0
    densities.sort()
    return percentile(densities, proportion), densities[-1]


def _shape_key(event, unused_previous=None):
    return '.'.join(str(pitch) for pitch in event['pitches'])


def _motion_key(event, previous=None):
    step = (event['pitches'][0] - previous['pitches'][0]
            if previous is not None else 'x')
    if len(event['pitches']) == 1:
        return str(step)
    intervals = [pitch - event['pitches'][0]
                 for pitch in event['pitches'][1:]]
    return '%s/%s' % (step, '.'.join(str(value) for value in intervals))


def conditional_entropy(segments, context_length=ENTROPY_K,
                        key_function=None):
    if key_function is None:
        key_function = _shape_key
    counts = {}
    context_totals = {}
    transitions = 0
    for segment in segments:
        symbols = [key_function(event, segment[index - 1]
                                if index > 0 else None)
                   for index, event in enumerate(segment)]
        for index in range(context_length, len(symbols)):
            context = '|'.join(symbols[index - context_length:index])
            next_counts = counts.setdefault(context, {})
            symbol = symbols[index]
            next_counts[symbol] = next_counts.get(symbol, 0) + 1
            context_totals[context] = context_totals.get(context, 0) + 1
            transitions += 1
    if transitions == 0:
        return 0, 0
    entropy = 0.0
    cells = 0
    for context, next_counts in counts.items():
        context_total = context_totals[context]
        for count in next_counts.values():
            cells += 1
            entropy -= (float(count) / transitions) * (
                math.log(float(count) / context_total) / math.log(2))
    entropy += float(cells - 1) / (2 * transitions * math.log(2))
    return entropy, len(counts)


def local_complexity_peak(segments, window_s=PEAK_WINDOW_S,
                          proportion=PEAK_PCTL):
    values = []
    for segment in segments:
        for start, event in enumerate(segment):
            window = []
            gems = 0
            limit = event['s'] + window_s
            for following in segment[start:]:
                if following['s'] > limit:
                    break
                window.append(following)
                gems += len(following['pitches'])
            if len(window) >= 4:
                entropy, unused_contexts = conditional_entropy(
                    [window], 1, _motion_key)
                values.append((float(gems) / window_s) * entropy)
            else:
                values.append(0)
    if not values:
        return 0
    values.sort()
    return percentile(values, proportion)


def peak_stations(segments, window_s=PEAK_WINDOW_S,
                  proportion=PEAK_PCTL):
    if window_s <= 0:
        return 0
    counts = []
    for segment in segments:
        for start, event in enumerate(segment):
            seen = set()
            limit = event['s'] + window_s
            for following in segment[start:]:
                if following['s'] > limit:
                    break
                seen.update(following['pitches'])
            counts.append(len(seen))
    if not counts:
        return 0
    counts.sort()
    return percentile(counts, proportion)


def score_bass(events, spans):
    spans = normalize_spans(spans)
    segments = events_in_segments(events, spans)
    playing_s = total_span_seconds(spans)
    in_span = [event for segment in segments for event in segment]
    changes = 0
    for segment in segments:
        for index in range(1, len(segment)):
            if segment[index]['pitches'] != segment[index - 1]['pitches']:
                changes += 1
    density_peak, unused_max = peak_density(segments)
    entropy_h2, unused_contexts = conditional_entropy(segments)
    return {
        'total_changes': changes,
        'density_peak': density_peak,
        'density_avg': (float(sum(len(event['pitches'])
                                  for event in in_span)) / playing_s
                        if playing_s > 0 else 0),
        'entropy_h2': entropy_h2,
    }


def total_span_seconds(spans):
    return sum(max(0, span['e'] - span['s']) for span in spans)


def span_overlap_seconds(left, right):
    if not left or not right:
        return 0
    total = 0
    right_index = 0
    for first in left:
        while (right_index < len(right) and
               right[right_index]['e'] < first['s']):
            right_index += 1
        index = right_index
        while index < len(right) and right[index]['s'] <= first['e']:
            lo = max(first['s'], right[index]['s'])
            hi = min(first['e'], right[index]['e'])
            if hi > lo:
                total += hi - lo
            index += 1
    return total


def _in_spans(spans, value):
    for span in spans:
        if value < span['s']:
            return False
        if value <= span['e']:
            return True
    return False


def _pitch_set_changed(left, right):
    return left['pitches'] != right['pitches']


def _solo_change_ratio(segments, solo_spans):
    if not solo_spans:
        return 1.0
    changes_in = changes_out = 0
    qn_in = qn_out = 0.0
    for segment in segments:
        for index in range(1, len(segment)):
            event = segment[index]
            previous = segment[index - 1]
            event_in = _in_spans(solo_spans, event['s'])
            previous_in = _in_spans(solo_spans, previous['s'])
            if event_in != previous_in:
                continue
            difference = event['qn'] - previous['qn']
            changed = 1 if _pitch_set_changed(event, previous) else 0
            if event_in:
                changes_in += changed
                qn_in += difference
            else:
                changes_out += changed
                qn_out += difference
    if qn_in <= 0 or qn_out <= 0 or changes_out == 0:
        return 1.0
    return ((float(changes_in) / qn_in) /
            (float(changes_out) / qn_out))


def _hand_movement(segments):
    distances = []
    anchored = 0
    for segment in segments:
        for index in range(1, len(segment)):
            previous = segment[index - 1]
            event = segment[index]
            previous_center = (float(sum(previous['pitches'])) /
                               len(previous['pitches']))
            center = float(sum(event['pitches'])) / len(event['pitches'])
            distances.append(abs(center - previous_center))
            if set(previous['pitches']).intersection(event['pitches']):
                anchored += 1
    if not distances:
        return 0, 0, 0
    mean = float(sum(distances)) / len(distances)
    distances.sort()
    return mean, percentile(distances, 0.90), float(anchored) / len(distances)


def score_guitar(events, spans, marked_solo_spans=None,
                  tremolo_spans=None, trill_spans=None,
                  force_hopo_count=0, force_strum_count=0):
    """Return the exact factors selected by the frozen Guitar model."""
    spans = normalize_spans(spans)
    playing_s = total_span_seconds(spans)
    defaults = {
        'playing_s': 0, 'attack_density_avg': 0,
        'attack_density_peak': 0, 'change_rate': 0,
        'density_avg': 0, 'density_peak': 0,
        'tight_p10': 0, 'tight_med': 0, 'chord_size_mean': 0,
        'chord_span_mean': 0, 'chord_change_frac': 0,
        'move_mean': 0, 'move_p90': 0, 'anchor_frac': 0,
        'solo_frac_marked': 0, 'solo_change_ratio': 1.0,
        'sustain_frac': 0, 'force_hopo_rate': 0,
        'force_strum_rate': 0, 'tremolo_frac': 0, 'trill_frac': 0,
        'notes_total': 0, 'total_changes': 0,
    }
    if playing_s <= 0:
        return defaults

    segments = events_in_segments(events, spans)
    in_span = [event for segment in segments for event in segment]
    if not in_span:
        defaults['playing_s'] = playing_s
        return defaults

    changes = 0
    intervals = []
    chord_changes = 0
    for segment in segments:
        for index in range(1, len(segment)):
            event = segment[index]
            if _pitch_set_changed(event, segment[index - 1]):
                changes += 1
                intervals.append(event['qn'] - segment[index - 1]['qn'])
                if len(event['pitches']) > 1:
                    chord_changes += 1

    chord_events = [event for event in in_span
                    if len(event['pitches']) > 1]
    chord_span = sum(event['pitches'][-1] - event['pitches'][0]
                     for event in chord_events)
    move_mean, move_p90, anchor_frac = _hand_movement(segments)
    attack_peak, unused_max = peak_density(
        segments, weight=lambda unused_event: 1)
    gem_peak, unused_gem_max = peak_density(segments)
    intervals.sort()
    solo_spans = normalize_spans(marked_solo_spans or [])
    tremolo = normalize_spans(tremolo_spans or [])
    trill = normalize_spans(trill_spans or [])
    sustained = sum(
        1 for event in in_span
        if event.get('qn_e') is not None and
        event['qn_e'] - event['qn'] >= 0.5)

    return {
        'playing_s': playing_s,
        'attack_density_avg': float(len(in_span)) / playing_s,
        'attack_density_peak': attack_peak,
        'density_avg': float(sum(len(event['pitches'])
                                 for event in in_span)) / playing_s,
        'density_peak': gem_peak,
        'change_rate': float(changes) / playing_s,
        'tight_p10': percentile(intervals, 0.10) if intervals else 0,
        'tight_med': percentile(intervals, 0.50) if intervals else 0,
        'chord_size_mean': (float(sum(len(event['pitches'])
                                      for event in in_span)) /
                            len(in_span)),
        'chord_span_mean': (float(chord_span) / len(chord_events)
                            if chord_events else 0),
        'chord_change_frac': (float(chord_changes) / changes
                              if changes else 0),
        'move_mean': move_mean,
        'move_p90': move_p90,
        'anchor_frac': anchor_frac,
        'solo_frac_marked': (float(span_overlap_seconds(spans, solo_spans)) /
                             playing_s),
        'solo_change_ratio': _solo_change_ratio(segments, solo_spans),
        'sustain_frac': float(sustained) / len(in_span),
        'force_hopo_rate': float(force_hopo_count) / playing_s,
        'force_strum_rate': float(force_strum_count) / playing_s,
        'tremolo_frac': float(span_overlap_seconds(spans, tremolo)) / playing_s,
        'trill_frac': float(span_overlap_seconds(spans, trill)) / playing_s,
        'notes_total': sum(len(event['pitches']) for event in in_span),
        'total_changes': changes,
    }


def score_keys(events, spans, pro_keys=False):
    """Return factors selected by the five-lane or Pro Keys model."""
    spans = normalize_spans(spans)
    playing_s = total_span_seconds(spans)
    defaults = {
        'total_changes': 0,
        'attack_density_peak': 0,
        'tight_p10': 0,
        'tight_med': 0,
        'playing_s': playing_s,
        'entropy_h2_rel': 0,
        'complex_peak': 0,
        'chord_size_mean': 0,
        'density_avg': 0,
        'density_peak': 0,
    }
    if playing_s <= 0:
        return defaults
    segments = events_in_segments(events, spans)
    in_span = [event for segment in segments for event in segment]
    if not in_span:
        return defaults

    changes = 0
    intervals = []
    for segment in segments:
        for index in range(1, len(segment)):
            if _pitch_set_changed(segment[index], segment[index - 1]):
                changes += 1
                intervals.append(
                    segment[index]['qn'] - segment[index - 1]['qn'])
    intervals.sort()
    attack_peak, unused_max = peak_density(
        segments, weight=lambda unused_event: 1)
    gem_peak, unused_gem_max = peak_density(segments)
    relative_entropy, unused_contexts = conditional_entropy(
        segments, ENTROPY_K, _motion_key)
    return {
        'total_changes': changes,
        'attack_density_peak': attack_peak,
        'tight_p10': percentile(intervals, 0.10) if intervals else 0,
        'tight_med': percentile(intervals, 0.50) if intervals else 0,
        'playing_s': playing_s,
        'entropy_h2_rel': relative_entropy,
        'complex_peak': local_complexity_peak(segments),
        'chord_size_mean': (float(sum(len(event['pitches'])
                                      for event in in_span)) /
                            len(in_span)),
        'density_avg': (float(sum(len(event['pitches'])
                                  for event in in_span)) / playing_s),
        'density_peak': gem_peak,
    }


def _remap_pro_drums(events, tom_spans):
    remapped = []
    for event in events:
        pitches = []
        for pitch in event['pitches']:
            lane_spans = tom_spans.get(pitch)
            pitches.append(pitch - 0.5
                           if lane_spans and
                           _in_spans(lane_spans, event['s']) else pitch)
        copied = dict(event)
        copied['pitches'] = sorted(pitches)
        remapped.append(copied)
    return remapped


def score_drums(events, spans, tom_spans=None, roll_spans=None):
    """Return the exact factors selected by the frozen Drums model."""
    spans = normalize_spans(spans)
    playing_s = total_span_seconds(spans)
    keys = (
        'playing_s', 'density_avg', 'density_peak_noroll', 'change_rate',
        'attack_density_avg', 'attack_density_peak_noroll', 'tight_p10',
        'tight_med', 'chord_size_mean', 'chord_span_mean',
        'chord_change_frac', 'move_mean', 'move_p90', 'anchor_frac',
        'kick_density', 'kick_density_peak', 'hand_density_peak_noroll',
        'stick_size_mean', 'tom_frac', 'roll_frac', 'offbeat_frac',
        'pro_stations_peak', 'entropy_h2', 'entropy_h2_rel',
        'notes_total', 'total_changes')
    keys = keys + ('density_peak',)
    result = dict((key, 0) for key in keys)
    result['playing_s'] = playing_s
    if playing_s <= 0:
        return result

    # The Guitar-selected core contains the common pair, chord, and movement
    # definitions used unchanged by Drums.
    common = score_guitar(events, spans)
    for key in ('playing_s', 'change_rate', 'tight_p10', 'tight_med',
                'chord_size_mean', 'chord_span_mean',
                'chord_change_frac', 'move_mean', 'move_p90',
                'anchor_frac', 'notes_total', 'total_changes'):
        result[key] = common[key]

    segments = events_in_segments(events, spans)
    in_span = [event for segment in segments for event in segment]
    if not in_span:
        return result
    result['density_avg'] = float(result['notes_total']) / playing_s
    result['density_peak'] = peak_density(segments)[0]
    result['attack_density_avg'] = float(len(in_span)) / playing_s

    rolls = normalize_spans(roll_spans or [])
    under_roll = lambda event: _in_spans(rolls, event['s'])
    result['density_peak_noroll'] = peak_density(
        segments,
        weight=lambda event: 0 if under_roll(event)
        else len(event['pitches']))[0]
    result['attack_density_peak_noroll'] = peak_density(
        segments,
        weight=lambda event: 0 if under_roll(event) else 1)[0]

    kick_pitch = 96
    kick_count = 0
    hand_count = 0
    stick_events = 0
    for event in in_span:
        hands = sum(1 for pitch in event['pitches'] if pitch != kick_pitch)
        kick_count += sum(1 for pitch in event['pitches']
                          if pitch == kick_pitch)
        hand_count += hands
        if hands:
            stick_events += 1
    result['kick_density'] = float(kick_count) / playing_s
    result['kick_density_peak'] = peak_density(
        segments, weight=lambda event: sum(
            1 for pitch in event['pitches'] if pitch == kick_pitch))[0]
    result['hand_density_peak_noroll'] = peak_density(
        segments, weight=lambda event: 0 if under_roll(event) else sum(
            1 for pitch in event['pitches'] if pitch != kick_pitch))[0]
    result['stick_size_mean'] = (float(hand_count) / stick_events
                                 if stick_events else 0)

    tom_spans = tom_spans or {}
    marked = 0
    tom_total = 0
    for event in in_span:
        for pitch in event['pitches']:
            lane_spans = tom_spans.get(pitch)
            if lane_spans:
                tom_total += 1
                if _in_spans(lane_spans, event['s']):
                    marked += 1
    result['tom_frac'] = float(marked) / tom_total if tom_total else 0
    result['roll_frac'] = (float(span_overlap_seconds(spans, rolls)) /
                           playing_s)

    offbeat = 0
    for event in in_span:
        fraction = event['qn'] % 1
        if OFFBEAT_TOL < fraction < 1 - OFFBEAT_TOL:
            offbeat += 1
    result['offbeat_frac'] = float(offbeat) / len(in_span)

    result['entropy_h2'] = conditional_entropy(segments)[0]
    result['entropy_h2_rel'] = conditional_entropy(
        segments, ENTROPY_K, _motion_key)[0]
    pro_events = _remap_pro_drums(events, tom_spans)
    pro_segments = events_in_segments(pro_events, spans)
    result['pro_stations_peak'] = peak_stations(pro_segments)
    return result
