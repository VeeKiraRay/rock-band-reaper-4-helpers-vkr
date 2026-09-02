"""Pure difficulty factors shared by the legacy chart readers.

This first scoring slice ports the exact factors selected by the frozen Bass
model. The functions retain the names and definitions of the modern Lua
scorer so further instrument factors can be added without a second framework.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import math


PEAK_WINDOW_S = 8.0
PEAK_PCTL = 0.95
ENTROPY_K = 2
FALLBACK_GAP_QN = 8.0


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


def _shape_key(event):
    return '.'.join(str(pitch) for pitch in event['pitches'])


def conditional_entropy(segments, context_length=ENTROPY_K):
    counts = {}
    context_totals = {}
    transitions = 0
    for segment in segments:
        symbols = [_shape_key(event) for event in segment]
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


def score_bass(events, spans):
    spans = normalize_spans(spans)
    segments = events_in_segments(events, spans)
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
