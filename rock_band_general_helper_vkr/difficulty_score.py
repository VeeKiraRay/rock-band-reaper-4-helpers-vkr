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
                 proportion=PEAK_PCTL):
    if window_s <= 0:
        return 0, 0
    densities = []
    for segment in segments:
        right = 0
        running = 0
        for left, event in enumerate(segment):
            if left > 0:
                running -= len(segment[left - 1]['pitches'])
            limit = event['s'] + window_s
            while right < len(segment) and segment[right]['s'] <= limit:
                running += len(segment[right]['pitches'])
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
