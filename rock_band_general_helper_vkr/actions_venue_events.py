"""Guarded EVENTS-track insertion for Venue > Events.

Modern counterpart:
rock_band_general_helper_vkr/actions_venue_events.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources
from .actions_difficulty_shared import format_time
from .venue import VenueReadError, read_named_track


class VenueEventsError(Exception):
    pass


def scan_events_text_events(events):
    rows = []
    for event in events:
        if event['meta_type'] != 1:
            continue
        row = dict(event)
        row['label'] = format_time(event['t'])
        rows.append(row)
    rows.sort(key=lambda value: (value['ppq'], value.get('ordinal', 0)))
    by_message = {}
    for row in rows:
        if row['msg'] not in by_message:
            by_message[row['msg']] = row
    return {'events': rows, 'by_msg': by_message}


def _is_crowd(message):
    return (message or '').startswith('[crowd_')


def _bare_form(base, number, is_generic):
    if number == 0:
        return '[prc_%s]' % base
    if is_generic:
        return '[prc_%s%d]' % (base, number)
    return '[prc_%s_%d]' % (base, number)


def _letter_form(base, number, letter, is_generic):
    if is_generic:
        return None
    if number == 0:
        return '[prc_%s_%s]' % (base, letter)
    return '[prc_%s_%d%s]' % (base, number, letter)


def _family_span(scan, base, number, is_generic):
    messages = [_bare_form(base, number, is_generic)]
    if not is_generic:
        messages.extend(_letter_form(base, number, chr(code), False)
                        for code in range(ord('a'), ord('z') + 1))
    rows = [scan['by_msg'][message] for message in messages
            if message in scan['by_msg']]
    if not rows:
        return None, None
    return (min(rows, key=lambda row: row['t']),
            max(rows, key=lambda row: row['t']))


def _spot_conflict(scan, insert_ppq):
    for row in scan['events']:
        if row['ppq'] == insert_ppq and not _is_crowd(row['msg']):
            return row
    return None


def next_section_event(scan, base, number, caps, is_generic,
                       use_letters, insert_time, insert_ppq):
    """Return ``(event, None)`` or ``(None, refusal_reason)``."""
    number = int(number)
    if number < 0 or number > 9:
        return None, 'Section number must be between 0 (bare) and 9.'
    if not is_generic:
        cap = caps[number:number + 1]
        if not cap:
            return None, '[prc_%s] has no _%d variant' % (base, number)

    numbered_first = None
    for candidate in range(1, 10):
        numbered_first, unused_last = _family_span(
            scan, base, candidate, is_generic)
        if numbered_first:
            break
    bare_first, unused_last = _family_span(scan, base, 0, is_generic)
    if number == 0 and numbered_first:
        return (None, 'Numbered %s exists - bare and numbered must not '
                'co-exist. Use bare for a single section, numbers for repeats.' %
                numbered_first['msg'])
    if number >= 1 and bare_first:
        return (None, 'Bare %s exists - remove it before adding numbered '
                'variants.' % bare_first['msg'])
    if number >= 2:
        previous, unused_last = _family_span(
            scan, base, number - 1, is_generic)
        if not previous:
            return (None, 'Add %s first - numbers must be used in order.' %
                    _bare_form(base, number - 1, is_generic))

    bare = _bare_form(base, number, is_generic)
    cap = '.' if is_generic else caps[number:number + 1]
    if use_letters and not is_generic and cap != '.':
        plain = scan['by_msg'].get(bare)
        if plain:
            return (None, '%s exists at %s - it must not be mixed with '
                    'lettered parts. Remove it, or disable letter suffix.' %
                    (bare, plain['label']))
        slots = [_letter_form(base, number, chr(code), False)
                 for code in range(ord('a'), ord(cap) + 1)]
        target_index = None
        for index, message in enumerate(slots):
            if message not in scan['by_msg']:
                target_index = index
                break
        if target_index is None:
            return None, 'No more letters available for %s (max %s)' % (bare, cap)
    else:
        if not is_generic and cap != '.':
            for code in range(ord('a'), ord(cap) + 1):
                row = scan['by_msg'].get(
                    _letter_form(base, number, chr(code), False))
                if row:
                    return (None, 'Lettered %s exists - enable letter suffix '
                            'to add more parts, or remove the lettered events.' %
                            row['msg'])
        duplicate = scan['by_msg'].get(bare)
        if duplicate:
            return None, '%s already exists at %s' % (bare, duplicate['label'])
        slots, target_index = [bare], 0
    target = slots[target_index]

    previous = None
    for index in range(target_index - 1, -1, -1):
        previous = scan['by_msg'].get(slots[index])
        if previous:
            break
    if not previous:
        for candidate in range(number - 1, 0, -1):
            unused_first, previous = _family_span(
                scan, base, candidate, is_generic)
            if previous:
                break
    following = None
    for index in range(target_index + 1, len(slots)):
        following = scan['by_msg'].get(slots[index])
        if following:
            break
    if not following:
        for candidate in range(number + 1, 10):
            following, unused_last = _family_span(
                scan, base, candidate, is_generic)
            if following:
                break
    if previous and insert_time <= previous['t']:
        return (None, '%s must be placed after %s (%s)' %
                (target, previous['msg'], previous['label']))
    if following and insert_time >= following['t']:
        return (None, '%s must be placed before %s (%s)' %
                (target, following['msg'], following['label']))
    conflict = _spot_conflict(scan, insert_ppq)
    if conflict:
        return (None, '%s is already at this position (%s)' %
                (conflict['msg'], conflict['label']))
    return target, None


def validate_plain_insert(scan, message, insert_ppq):
    if _is_crowd(message):
        return True, None
    duplicate = scan['by_msg'].get(message)
    if duplicate:
        return False, '%s already exists at %s' % (message, duplicate['label'])
    conflict = _spot_conflict(scan, insert_ppq)
    if conflict:
        return (False, '%s is already at this position (%s)' %
                (conflict['msg'], conflict['label']))
    return True, None


def _read_insert_context(host):
    try:
        track, contexts, events = read_named_track(host, 'EVENTS')
    except VenueReadError as exc:
        raise VenueEventsError(str(exc))
    cursor = host.cursor_position()
    targets = [context for context in contexts
               if context['position'] <= cursor < context['end']]
    if not targets:
        raise VenueEventsError(
            'Move the edit cursor inside a MIDI item on the EVENTS track.')
    if len(targets) > 1:
        raise VenueEventsError(
            'The edit cursor overlaps multiple EVENTS MIDI items; insertion '
            'is ambiguous.')
    context = targets[0]
    source_qn = (host.time_to_qn(cursor) - context['start_qn'] +
                 context['offset_qn'])
    source_tick = int(round(source_qn * context['parsed'].ppq))
    project_ppq = int(round(host.time_to_qn(cursor) * 480.0))
    return track, context, events, cursor, source_tick, project_ppq


def _insert(host, context, message):
    verify_unshared_pool_sources(host, [context])
    expected = context['parsed'].with_inserted_meta_event(
        context['insert_tick'], 0x01, message)
    apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'fingerprint': context['fingerprint'], 'expected': expected,
    }], 'Insert EVENTS event: %s' % message)
    return ('Inserted %s at playhead (EVENTS).' % message,
            'Inserted %s at %s.\nUndo: Insert EVENTS event: %s' %
            (message, format_time(context['insert_time']), message))


def insert_events_event(host, message):
    unused_track, context, events, cursor, source_tick, project_ppq = (
        _read_insert_context(host))
    scan = scan_events_text_events(events)
    accepted, reason = validate_plain_insert(scan, message, project_ppq)
    if not accepted:
        return 'EVENTS insertion blocked.', reason
    context['insert_tick'] = source_tick
    context['insert_time'] = cursor
    return _insert(host, context, message)


def add_section_event(host, base, number, caps, is_generic, use_letters):
    unused_track, context, events, cursor, source_tick, project_ppq = (
        _read_insert_context(host))
    scan = scan_events_text_events(events)
    message, reason = next_section_event(
        scan, base, number, caps, is_generic, use_letters,
        cursor, project_ppq)
    if message is None:
        return 'EVENTS insertion blocked.', reason
    context['insert_tick'] = source_tick
    context['insert_time'] = cursor
    return _insert(host, context, message)
