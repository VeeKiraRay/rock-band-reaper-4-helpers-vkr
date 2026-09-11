"""Read-only VENUE lighting, keyframe, and blend validation.

Modern counterpart:
rock_band_general_helper_vkr/actions_venue_validate.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .actions_difficulty_shared import format_time
from .venue import (
    MANUAL_LIGHTING, VenueReadError, categorize_venue_event,
    is_blend_anchor, read_named_track,
)


def _nearest_index(events, ppq, cursor):
    if not events:
        return None, 0
    index = max(0, min(cursor, len(events) - 1))
    while index + 1 < len(events) and events[index + 1]['ppq'] <= ppq:
        index += 1
    best = index
    if (index + 1 < len(events) and
            abs(events[index + 1]['ppq'] - ppq) <
            abs(events[index]['ppq'] - ppq)):
        best = index + 1
    return best, index


def validate_lighting_blends(lighting, postproc, firsts, tolerance=0,
                             near_ppq=0):
    """Return pure findings over project-PPQ event dictionaries."""
    findings = {
        'missing_first': [], 'stray_first': [],
        'blend': {
            'lt': {'missing': [], 'changes': 0, 'anchored': 0},
            'pp': {'missing': [], 'changes': 0, 'anchored': 0},
        },
        'changes': 0, 'manual_changes': 0,
    }
    changes = []
    for index, event in enumerate(lighting):
        changed = index == 0 or lighting[index - 1]['msg'] != event['msg']
        changes.append(changed)
        if changed:
            findings['changes'] += 1
            if event['msg'] in MANUAL_LIGHTING:
                findings['manual_changes'] += 1

    has_first = []
    first_index = 0
    for event in lighting:
        while (first_index < len(firsts) and
               firsts[first_index]['ppq'] < event['ppq'] - tolerance):
            first_index += 1
        has_first.append(
            first_index < len(firsts) and
            abs(firsts[first_index]['ppq'] - event['ppq']) <= tolerance)

    wants_first = set()
    for index, event in enumerate(lighting):
        if (changes[index] and event['msg'] in MANUAL_LIGHTING and
                not has_first[index]):
            wants_first.add(index)
            row = dict(event)
            row['idx'] = index
            findings['missing_first'].append(row)

    cursor = 0
    previous_ppq = None
    for first in firsts:
        kind = None
        lighting_event = None
        delta = None
        lighting_index = None
        if (previous_ppq is not None and
                abs(first['ppq'] - previous_ppq) <= tolerance):
            kind = 'duplicate'
        elif not lighting:
            kind = 'orphan'
        else:
            lighting_index, cursor = _nearest_index(
                lighting, first['ppq'], cursor)
            lighting_event = lighting[lighting_index]
            delta = first['ppq'] - lighting_event['ppq']
            if abs(delta) <= tolerance:
                if lighting_event['msg'] not in MANUAL_LIGHTING:
                    kind = 'on_auto'
                elif not changes[lighting_index]:
                    kind = 'on_restatement'
            elif abs(delta) <= near_ppq and lighting_index in wants_first:
                kind = 'misaligned'
            else:
                kind = 'orphan'
        if kind:
            row = dict(first)
            row.update({'kind': kind, 'lt': lighting_event, 'delta': delta})
            findings['stray_first'].append(row)
        previous_ppq = first['ppq']

    for stray in findings['stray_first']:
        if stray['kind'] != 'misaligned':
            continue
        for missing in findings['missing_first']:
            if missing['idx'] == lighting.index(stray['lt']):
                missing['near_delta'] = stray['delta']

    def scan_blends(events, accumulator):
        for index in range(1, len(events)):
            if events[index]['msg'] == events[index - 1]['msg']:
                continue
            accumulator['changes'] += 1
            if is_blend_anchor(events[index - 2] if index >= 2 else None,
                               events[index - 1]):
                accumulator['anchored'] += 1
            else:
                row = dict(events[index])
                row.update({'from_ppq': events[index - 1]['ppq'],
                            'from_msg': events[index - 1]['msg'],
                            'from_t': events[index - 1].get('t')})
                accumulator['missing'].append(row)

    scan_blends(lighting, findings['blend']['lt'])
    scan_blends(postproc, findings['blend']['pp'])
    return findings


def _scope(findings, start, end):
    if start is None:
        return findings
    scoped = dict(findings)
    scoped['blend'] = {
        'lt': dict(findings['blend']['lt']),
        'pp': dict(findings['blend']['pp']),
    }

    def keep(rows):
        return [row for row in rows if start <= row.get('t', -1) <= end]

    scoped['missing_first'] = keep(findings['missing_first'])
    scoped['stray_first'] = keep(findings['stray_first'])
    scoped['blend']['lt']['missing'] = keep(findings['blend']['lt']['missing'])
    scoped['blend']['pp']['missing'] = keep(findings['blend']['pp']['missing'])
    return scoped


def validate_venue_lighting(host):
    try:
        unused_track, unused_contexts, events = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        return 'VENUE lighting validation could not run.', str(exc)
    text = [event for event in events if event['meta_type'] == 1]
    lighting = [event for event in text
                if categorize_venue_event(event['msg']) == 'lighting']
    postproc = [event for event in text
                if categorize_venue_event(event['msg']) == 'postproc']
    firsts = [event for event in text if event['msg'] == '[first]']
    if not lighting and not postproc and not firsts:
        return ('VENUE has no lighting or post proc events.',
                'The VENUE track has no [lighting*], *.pp] or [first] events '
                'to validate.')
    findings = validate_lighting_blends(
        lighting, postproc, firsts, tolerance=480 // 32, near_ppq=480)
    start, end = host.time_selection()
    scoped = _scope(findings, start, end)
    scope = ('whole song' if start is None else 'time selection %s - %s' %
             (format_time(start), format_time(end)))
    total = (len(scoped['missing_first']) + len(scoped['stray_first']) +
             len(scoped['blend']['lt']['missing']) +
             len(scoped['blend']['pp']['missing']))
    lines = [('VENUE lighting validation - %s  (%s)' %
              ('no issues' if total == 0 else '%d issue%s' %
               (total, '' if total == 1 else 's'), scope)), '']

    missing = scoped['missing_first']
    if missing:
        lines.append('Manual lighting changes missing a [first] (%d):' % len(missing))
        for row in missing:
            extra = ''
            if row.get('near_delta') is not None:
                extra = ' - a [first] sits %.2f beats away' % (
                    abs(row['near_delta']) / 480.0)
            lines.append('  %s   %s%s' % (format_time(row['t']), row['msg'], extra))
    else:
        lines.append('Manual lighting changes missing a [first]: none.')
    lines.append('')

    stray = scoped['stray_first']
    if stray:
        lines.append('[first] events off a lighting change (%d):' % len(stray))
        reasons = {
            'on_auto': 'automatic lighting takes no keyframes; delete it',
            'on_restatement': 'blend anchors do not start keyframes; delete it',
            'duplicate': 'a second [first] is on the same tick; delete one',
            'orphan': 'no lighting event is on this tick; delete it',
        }
        for row in stray:
            if row['kind'] == 'misaligned':
                relation = 'after' if row['delta'] > 0 else 'before'
                reason = ('%.2f beats %s %s; move it onto that event' %
                          (abs(row['delta']) / 480.0, relation,
                           row['lt']['msg']))
            else:
                reason = reasons[row['kind']]
            lines.append('  %s   %s' % (format_time(row['t']), reason))
    else:
        lines.append('[first] events off a lighting change: none.')
    lines.append('')

    for label, key in (('Lighting', 'lt'), ('Post proc', 'pp')):
        missing_blends = scoped['blend'][key]['missing']
        if missing_blends:
            lines.append('%s changes with no blend anchor (%d):' %
                         (label, len(missing_blends)))
            for row in missing_blends:
                lines.append('  %s   %s  ->  %s' %
                             (format_time(row['t']), row['from_msg'], row['msg']))
            lines.append('  A hard cut is valid; only add anchors where you wanted a fade.')
        else:
            lines.append('%s changes with no blend anchor: none.' % label)
        lines.append('')

    lines.extend((
        'Checked (whole track):',
        '  %d lighting events - %d preset changes, %d manual' %
        (len(lighting), findings['changes'], findings['manual_changes']),
        '  %d [first] events' % len(firsts),
        '  Lighting blends:  %d of %d changes anchored' %
        (findings['blend']['lt']['anchored'], findings['blend']['lt']['changes']),
        '  Post proc blends: %d of %d changes anchored' %
        (findings['blend']['pp']['anchored'], findings['blend']['pp']['changes']),
    ))
    status = ('VENUE lighting: no issues found.' if total == 0 else
              'VENUE lighting: %d issue%s found.' %
              (total, '' if total == 1 else 's'))
    return status, '\n'.join(lines)
