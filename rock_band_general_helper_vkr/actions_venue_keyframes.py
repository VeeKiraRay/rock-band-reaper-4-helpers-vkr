"""Guarded bulk regeneration of VENUE lighting keyframes.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources
from .actions_venue_themes import (
    INSTRUMENT_ALIGN, MANUAL_LIGHTING, _instrument_note_qns, _keyframes,
    _next_measure_qn, _project_qn_to_tick, _tick_to_project_qn,
)
from .actions_difficulty_shared import format_time
from .venue import VenueReadError, read_named_track


KEYFRAME_PAYLOADS = frozenset(('[first]', '[next]', '[previous]'))
KEYFRAME_ALIGN_LABELS = (
    'Lighting start', 'Closest beat', 'Downbeat', 'Guitar notes',
    'Bass notes', 'Keys notes', 'Drum kicks', 'Drum snare',
)


class VenueKeyframeGenerationError(Exception):
    pass


def _processing_times(host, context):
    selection_start, selection_end = host.time_selection()
    if selection_start is None:
        return context['position'], context['end'], False
    return (max(context['position'], selection_start),
            min(context['end'], selection_end), True)


def _lighting_spans(context, range_start_tick, range_end_tick):
    lighting = []
    for event in context['parsed'].text_events(1):
        if event.meta_payload.startswith('[lighting'):
            lighting.append(event)
    lighting.sort(key=lambda event: (event.absolute_tick, event.ordinal))
    spans = []
    for index, event in enumerate(lighting):
        previous = lighting[index - 1] if index else None
        restates = (previous is not None and
                    previous.meta_payload == event.meta_payload)
        if (event.meta_payload not in MANUAL_LIGHTING or restates or
                not range_start_tick <= event.absolute_tick < range_end_tick):
            continue
        span_end = range_end_tick
        for following in lighting[index + 1:]:
            if following.meta_payload != event.meta_payload:
                span_end = min(span_end, following.absolute_tick)
                break
        if span_end > event.absolute_tick:
            spans.append((event.absolute_tick, span_end,
                          event.meta_payload))
    return spans


def build_keyframe_plan(host, context, rate, align, subdivision):
    try:
        rate = int(rate)
    except (TypeError, ValueError):
        raise VenueKeyframeGenerationError(
            'Keyframe rate must be a whole number from 1 to 8 beats.')
    if rate < 1 or rate > 8:
        raise VenueKeyframeGenerationError(
            'Keyframe rate must be from 1 to 8 beats; received %s.' % rate)
    align = int(align)
    subdivision = int(subdivision)
    if not 0 <= align < len(KEYFRAME_ALIGN_LABELS):
        raise VenueKeyframeGenerationError('Keyframe alignment is invalid.')
    if subdivision not in (0, 1, 2):
        raise VenueKeyframeGenerationError('Keyframe subdivision is invalid.')

    start_time, end_time, has_selection = _processing_times(host, context)
    if end_time <= start_time:
        return [], [], [], has_selection, start_time, end_time
    start_tick = _project_qn_to_tick(
        context, host.time_to_qn(start_time))
    end_tick = _project_qn_to_tick(context, host.time_to_qn(end_time))
    spans = _lighting_spans(context, start_tick, end_tick)
    guards = []
    note_qns = []
    if align in INSTRUMENT_ALIGN:
        note_qns, note_contexts = _instrument_note_qns(
            host, *INSTRUMENT_ALIGN[align])
        guards.extend(note_contexts)

    rows = []
    for span_start, span_end, unused_lighting in spans:
        start_qn = _tick_to_project_qn(context, span_start)
        end_qn = _tick_to_project_qn(context, span_end)
        generated = _keyframes(
            start_qn, end_qn, rate, align, subdivision, note_qns,
            lambda value: _next_measure_qn(host, value))
        for qn, payload, unused_no_snap in generated:
            tick = _project_qn_to_tick(context, qn)
            if span_start <= tick < span_end:
                rows.append({'tick': tick, 'payload': payload})
    windows = [(start, end) for start, end, unused_name in spans]
    return rows, windows, guards, has_selection, start_time, end_time


def regenerate_venue_keyframes(host, rate, align, subdivision):
    try:
        unused_track, contexts, unused_rows = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        raise VenueKeyframeGenerationError(str(exc))
    if len(contexts) != 1:
        raise VenueKeyframeGenerationError(
            'Keyframes requires exactly one MIDI item on VENUE; found %d.' %
            len(contexts))
    context = contexts[0]
    rows, windows, guards, has_selection, start_time, end_time = (
        build_keyframe_plan(host, context, rate, align, subdivision))
    if not windows:
        scope = ('the time selection' if has_selection else 'the VENUE item')
        return ('No manual lighting changes found.',
                'No qualifying manual lighting change starts inside %s.\n\n'
                'No project changes were made.' % scope)

    verify_unshared_pool_sources(host, [context])
    expected = context['parsed'].with_replaced_meta_event_windows(
        windows, rows, 0x01, KEYFRAME_PAYLOADS)
    guard_plans = [{
        'item': value['item'], 'original': value['chunk'],
        'fingerprint': value['fingerprint'], 'expected': value['chunk'],
    } for value in guards]
    undo = 'Regenerate VENUE keyframes'
    changed = apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'fingerprint': context['fingerprint'], 'expected': expected,
    }], undo, guard_plans)
    scope = ('time selection %s - %s' %
             (format_time(start_time), format_time(end_time))
             if has_selection else 'full VENUE item')
    lines = [
        'Regenerated %d keyframe events across %d manual lighting span(s).'
        % (len(rows), len(windows)), '',
        'Scope:           %s' % scope,
        'Keyframe align:  %s' % KEYFRAME_ALIGN_LABELS[int(align)],
        'Keyframe rate:   %s beats' % int(rate),
        'MIDI items changed: %d' % changed,
        '', 'Undo: %s' % undo,
    ]
    return 'Regenerated %d VENUE keyframes.' % len(rows), '\n'.join(lines)
