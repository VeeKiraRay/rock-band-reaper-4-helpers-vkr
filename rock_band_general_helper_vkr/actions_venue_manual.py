"""Guarded actions for Venue > Manual gen.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import random

from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources
from .actions_difficulty_shared import format_time
from .actions_venue_keyframes import KEYFRAME_PAYLOADS
from .actions_venue_themes import (
    INSTRUMENT_ALIGN, _instrument_note_qns, _keyframes, _next_measure_qn,
    _project_qn_to_tick, _tick_to_project_qn,
)
from .venue import (
    MANUAL_LIGHTING, VenueReadError, categorize_venue_event,
    is_blend_anchor, read_named_track,
)
from .venue_themes import get_theme_camera_interval


NO_LIGHTING_AT_CURSOR = (
    '[first] and manual keyframes require a manual lighting event at the '
    'edit cursor.')
REMOVE_LABELS = ('Camera', 'Lighting', 'Post proc', 'Special', 'All')
PACING_NAMES = ('minimal', 'slow', 'medium', 'fast', 'crazy')


class VenueManualError(Exception):
    pass


def _context(host, require_cursor=False):
    try:
        unused_track, contexts, unused_events = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        raise VenueManualError(str(exc))
    if len(contexts) != 1:
        raise VenueManualError(
            'Manual gen requires exactly one MIDI item on VENUE; found %d.' %
            len(contexts))
    context = contexts[0]
    cursor = host.cursor_position()
    if require_cursor and not context['position'] <= cursor < context['end']:
        raise VenueManualError(
            'Move the edit cursor inside the VENUE MIDI item.')
    return context, cursor


def _cursor_tick(host, context, cursor):
    return _project_qn_to_tick(context, host.time_to_qn(cursor))


def _manual_lighting_at(context, tick):
    tolerance = max(1, int(context['parsed'].ppq / 32))
    for event in context['parsed'].text_events(1):
        if (event.meta_payload in MANUAL_LIGHTING and
                abs(event.absolute_tick - tick) <= tolerance):
            return event
    return None


def _apply(host, context, expected, undo):
    verify_unshared_pool_sources(host, [context])
    changed = apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'fingerprint': context['fingerprint'], 'expected': expected,
    }], undo)
    return changed


def insert_venue_event(host, message):
    context, cursor = _context(host, True)
    tick = _cursor_tick(host, context, cursor)
    if message == '[first]' and _manual_lighting_at(context, tick) is None:
        return 'VENUE insertion blocked.', NO_LIGHTING_AT_CURSOR
    expected = context['parsed'].with_inserted_meta_event(
        tick, 0x01, message)
    undo = 'Insert VENUE event: %s' % message
    _apply(host, context, expected, undo)
    return ('Inserted %s at playhead.' % message,
            'Inserted %s at %s.\n\nUndo: %s' %
            (message, format_time(cursor), undo))


def resolve_blend_source(events, cursor_tick, tolerance=0):
    for event in events:
        if abs(event.absolute_tick - cursor_tick) <= tolerance:
            return None, 'occupied'
    previous = [event for event in events
                if event.absolute_tick < cursor_tick]
    if not previous:
        return None, 'none'
    last = previous[-1]
    second = previous[-2] if len(previous) > 1 else None
    if second is not None and is_blend_anchor(
            {'msg': second.meta_payload}, {'msg': last.meta_payload}):
        return None, 'blended'
    return last, None


def blend_venue_preset(host, kind):
    if kind not in ('lighting', 'postproc'):
        raise VenueManualError('Unknown blend type: %s' % kind)
    context, cursor = _context(host, True)
    tick = _cursor_tick(host, context, cursor)
    events = [event for event in context['parsed'].text_events(1)
              if categorize_venue_event(event.meta_payload) == kind]
    events.sort(key=lambda event: (event.absolute_tick, event.ordinal))
    source, reason = resolve_blend_source(
        events, tick, max(1, int(context['parsed'].ppq / 32)))
    label = 'post-process' if kind == 'postproc' else 'lighting'
    if source is None:
        messages = {
            'occupied': 'A %s event is already at the playhead.' % label,
            'none': 'No %s event exists before the playhead.' % label,
            'blended': 'The last two %s events already form a blend anchor.' %
                       label,
        }
        return 'VENUE blend blocked.', messages[reason]
    expected = context['parsed'].with_inserted_meta_event(
        tick, 0x01, source.meta_payload)
    undo = 'Blend VENUE %s' % label
    _apply(host, context, expected, undo)
    return ('Added %s blend anchor.' % label.capitalize(),
            'Copied %s to %s.\n\nUndo: %s' %
            (source.meta_payload, format_time(cursor), undo))


def generate_manual_keyframes(host, rate, align, subdivision):
    context, cursor = _context(host, True)
    try:
        rate = int(rate); align = int(align); subdivision = int(subdivision)
    except (TypeError, ValueError):
        raise VenueManualError('Keyframe settings are invalid.')
    if not 1 <= rate <= 8:
        raise VenueManualError('Keyframe rate must be from 1 to 8 beats.')
    if not 0 <= align <= 7 or subdivision not in (0, 1, 2):
        raise VenueManualError('Keyframe alignment is invalid.')
    start_tick = _cursor_tick(host, context, cursor)
    lighting = _manual_lighting_at(context, start_tick)
    if lighting is None:
        return 'Manual keyframes blocked.', NO_LIGHTING_AT_CURSOR
    end_tick = _project_qn_to_tick(context, host.time_to_qn(context['end']))
    selection_start, selection_end = host.time_selection()
    if selection_start is not None:
        end_tick = min(
            end_tick, _project_qn_to_tick(
                context, host.time_to_qn(selection_end)))
    half_beat = int(context['parsed'].ppq / 2)
    for event in context['parsed'].text_events(1):
        if (event.absolute_tick > start_tick + half_beat and
                event.meta_payload.startswith('[lighting') and
                event.meta_payload != lighting.meta_payload):
            end_tick = min(end_tick, event.absolute_tick)
            break
    if end_tick <= start_tick:
        return 'Manual keyframes blocked.', 'No range remains after the cursor.'
    guards = []
    note_qns = []
    if align in INSTRUMENT_ALIGN:
        note_qns, guards = _instrument_note_qns(
            host, *INSTRUMENT_ALIGN[align])
    start_qn = _tick_to_project_qn(context, start_tick)
    end_qn = _tick_to_project_qn(context, end_tick)
    generated = _keyframes(
        start_qn, end_qn, rate, align, subdivision, note_qns,
        lambda value: _next_measure_qn(host, value))
    rows = [{'tick': _project_qn_to_tick(context, qn), 'payload': payload}
            for qn, payload, unused_snap in generated]
    expected = context['parsed'].with_replaced_meta_event_windows(
        [(start_tick, end_tick)], rows, 0x01, KEYFRAME_PAYLOADS)
    verify_unshared_pool_sources(host, [context])
    guard_plans = [{
        'item': item['item'], 'original': item['chunk'],
        'fingerprint': item['fingerprint'], 'expected': item['chunk'],
    } for item in guards]
    undo = 'Generate manual VENUE keyframes'
    apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'fingerprint': context['fingerprint'], 'expected': expected,
    }], undo, guard_plans)
    return ('Generated %d keyframe events.' % len(rows),
            'Generated keyframes from %s until the next boundary.\n\nUndo: %s' %
            (format_time(cursor), undo))


def remove_venue_events(host, remove_type):
    context, unused_cursor = _context(host, False)
    try:
        remove_type = int(remove_type)
    except (TypeError, ValueError):
        raise VenueManualError('Removal type is invalid.')
    if not 0 <= remove_type < len(REMOVE_LABELS):
        raise VenueManualError('Removal type is invalid.')
    selection_start, selection_end = host.time_selection()
    if selection_start is None:
        start_tick = _project_qn_to_tick(
            context, host.time_to_qn(context['position']))
        end_tick = _project_qn_to_tick(
            context, host.time_to_qn(context['end'])) + 1
        scope = 'full VENUE item'
    else:
        range_start = max(context['position'], selection_start)
        range_end = min(context['end'], selection_end)
        if range_end <= range_start:
            return ('No %s events found.' % REMOVE_LABELS[remove_type],
                    'The time selection does not overlap the VENUE item.\n\n'
                    'No project changes were made.')
        start_tick = _project_qn_to_tick(
            context, host.time_to_qn(range_start))
        end_tick = _project_qn_to_tick(
            context, host.time_to_qn(range_end))
        scope = 'time selection'
    def matches(message):
        category = categorize_venue_event(message)
        if remove_type == 0:
            return category in ('coop', 'directed')
        if remove_type == 1:
            return category == 'lighting'
        if remove_type == 2:
            return category == 'postproc'
        if remove_type == 3:
            return category in ('special', 'keyframe')
        return True
    payloads = frozenset(
        event.meta_payload for event in context['parsed'].text_events(1)
        if start_tick <= event.absolute_tick < end_tick and
        matches(event.meta_payload))
    if not payloads:
        return ('No %s events found.' % REMOVE_LABELS[remove_type],
                'No project changes were made.')
    count = sum(1 for event in context['parsed'].text_events(1)
                if start_tick <= event.absolute_tick < end_tick and
                event.meta_payload in payloads)
    expected = context['parsed'].with_replaced_meta_event_windows(
        [(start_tick, end_tick)], [], 0x01, payloads)
    undo = 'Remove VENUE %s events' % REMOVE_LABELS[remove_type]
    _apply(host, context, expected, undo)
    return ('Removed %d %s events.' %
            (count, REMOVE_LABELS[remove_type]),
            'Scope: %s\n\nUndo: %s' % (scope, undo))


def advance_camera_pacing(host, mode, custom=16, jitter=True, rng=None):
    mode = int(mode)
    cursor = host.cursor_position()
    if mode == 6:
        try:
            unused_track, contexts, unused_events = read_named_track(
                host, 'PART VOCALS')
        except VenueReadError as exc:
            return 'Camera advance blocked.', str(exc)
        current_qn = host.time_to_qn(cursor)
        starts = []
        for context in contexts:
            for note in context['parsed'].notes():
                if note.pitch == 105:
                    qn = _tick_to_project_qn(context, note.start_tick)
                    if qn > current_qn:
                        starts.append(qn)
        if not starts:
            return 'Camera advance blocked.', 'No later vocal phrase was found.'
        target = host.qn_to_time(min(starts))
    else:
        bpm_getter = getattr(host, 'master_tempo', None)
        bpm = bpm_getter() if bpm_getter is not None else 120.0
        if 0 <= mode < len(PACING_NAMES):
            interval = get_theme_camera_interval(PACING_NAMES[mode], bpm)
        elif mode == 5:
            interval = max(2, min(128, int(custom)))
            if bpm >= 150:
                interval = int(interval * 1.5 + 0.5)
        else:
            raise VenueManualError('Camera pacing selection is invalid.')
        if jitter:
            rng = rng or random
            interval = max(1, int(
                interval * 0.8 + rng.random() * interval * 0.4 + 0.5))
        target = host.qn_to_time(host.time_to_qn(cursor) + interval * 0.25)
    host.set_cursor_position(target)
    return ('Advanced edit cursor.',
            'Moved from %s to %s.' %
            (format_time(cursor), format_time(target)))
