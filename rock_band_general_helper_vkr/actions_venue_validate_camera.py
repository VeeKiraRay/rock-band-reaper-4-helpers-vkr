"""Read-only VENUE camera-stack validation.

Modern counterparts:
rock_band_general_helper_vkr/actions_venue_validate_camera.lua
rock_band_general_helper_vkr/venue_camera_priority.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import re

from .actions_difficulty_shared import format_time
from .venue import (
    INSTRUMENT_NAMES, INSTRUMENT_TRACKS, VenueReadError, find_named_track,
    read_named_track,
)


PRIORITY_TIERS = (
    ('coop_generic', ('coop_all_behind', 'coop_all_far', 'coop_all_near')),
    ('coop_front', ('coop_front_behind', 'coop_front_near')),
    ('coop_single', (
        'coop_d_behind', 'coop_d_near', 'coop_v_behind', 'coop_v_near',
        'coop_b_behind', 'coop_b_near', 'coop_g_behind', 'coop_g_near',
        'coop_k_behind', 'coop_k_near')),
    ('coop_closeup', (
        'coop_d_closeup_hand', 'coop_d_closeup_head', 'coop_v_closeup',
        'coop_b_closeup_hand', 'coop_b_closeup_head',
        'coop_g_closeup_hand', 'coop_g_closeup_head',
        'coop_k_closeup_hand', 'coop_k_closeup_head')),
    ('coop_duo', (
        'coop_dv_near', 'coop_bd_near', 'coop_dg_near',
        'coop_bv_behind', 'coop_bv_near', 'coop_gv_behind', 'coop_gv_near',
        'coop_kv_behind', 'coop_kv_near', 'coop_bg_behind', 'coop_bg_near',
        'coop_bk_behind', 'coop_bk_near', 'coop_gk_behind', 'coop_gk_near')),
    ('directed', (
        'directed_all', 'directed_all_cam', 'directed_all_yeah',
        'directed_all_lt', 'directed_bre', 'directed_brej',
        'directed_crowd', 'directed_drums', 'directed_drums_pnt',
        'directed_drums_np', 'directed_drums_lt', 'directed_drums_kd',
        'directed_vocals', 'directed_vocals_np', 'directed_vocals_cls',
        'directed_vocals_cam_pr', 'directed_vocals_cam_pt',
        'directed_stagedive', 'directed_crowdsurf', 'directed_bass',
        'directed_crowd_b', 'directed_bass_np', 'directed_bass_cam',
        'directed_bass_cls', 'directed_guitar', 'directed_crowd_g',
        'directed_guitar_np', 'directed_guitar_cls',
        'directed_guitar_cam_pr', 'directed_guitar_cam_pt',
        'directed_keys', 'directed_keys_cam', 'directed_keys_np',
        'directed_duo_drums', 'directed_duo_guitar', 'directed_duo_bass',
        'directed_duo_kv', 'directed_duo_gb', 'directed_duo_kb',
        'directed_duo_kg')),
)
KEYS_EXCEPTION = (
    'coop_k_behind', 'coop_k_near',
    'coop_k_closeup_hand', 'coop_k_closeup_head',
)
_deferred = frozenset(KEYS_EXCEPTION)
_priority_order = []
for _tier, _names in PRIORITY_TIERS:
    _priority_order.extend(name for name in _names if name not in _deferred)
    if _tier == 'coop_duo':
        _priority_order.extend(KEYS_EXCEPTION)
CAM_PRIORITY = dict((name, index + 1)
                    for index, name in enumerate(_priority_order))
COOP_DUO = frozenset('[%s]' % name for tier, names in PRIORITY_TIERS
                     if tier == 'coop_duo' for name in names)
GENERIC_FALLBACK = ('[coop_all_behind]', '[coop_all_far]', '[coop_all_near]')


def coop_required_instruments(message):
    match = re.match(r'^\[coop_(.+)\]$', message or '')
    if not match:
        return []
    inner = match.group(1)
    if inner.startswith(('all', 'front')):
        return []
    match = re.match(r'^([a-z]+)_', inner)
    return [letter for letter in (match.group(1) if match else '')
            if letter in INSTRUMENT_TRACKS]


def directed_required_instruments(message):
    match = re.match(r'^\[directed_(.+)\]$', message or '')
    if not match:
        return []
    inner = match.group(1)
    if (inner.startswith('all') or inner in
            ('stagedive', 'crowdsurf', 'crowd')):
        return []
    if inner == 'crowd_b':
        return ['b']
    if inner == 'crowd_g':
        return ['g']
    if inner.startswith('duo_'):
        part = inner[4:]
        named = {'drums': ['d', 'v'], 'bass': ['b', 'v'],
                 'guitar': ['g', 'v']}
        if part in named:
            return named[part]
        return [letter for letter in part if letter in INSTRUMENT_TRACKS]
    for prefix, letter in (('drums', 'd'), ('vocals', 'v'), ('bass', 'b'),
                           ('guitar', 'g'), ('keys', 'k')):
        if inner.startswith(prefix):
            return [letter]
    return []


def camera_shot_fits_band(message, muted):
    if message.startswith('[coop_'):
        required = coop_required_instruments(message)
    elif message.startswith('[directed_'):
        required = directed_required_instruments(message)
    else:
        return True
    return not any(muted.get(letter) for letter in required)


def pick_priority_camera_event(group, muted):
    best = None
    best_rank = None
    for event in group:
        if not camera_shot_fits_band(event['msg'], muted):
            continue
        name = event['msg'][1:-1] if event['msg'].startswith('[') else event['msg']
        rank = CAM_PRIORITY.get(name, 0)
        if best is None or rank >= best_rank:
            best, best_rank = event, rank
    return best


def build_band_lineups(muted):
    trio = ('b', 'g', 'k')
    present = [letter for letter in trio if not muted.get(letter)]

    def lineup(on_stage):
        lineup_muted = dict(muted)
        for letter in trio:
            if letter not in on_stage:
                lineup_muted[letter] = True
        label = (' + '.join(INSTRUMENT_NAMES[letter] for letter in on_stage)
                 if on_stage else 'Drums + Vocals only')
        return {'label': label, 'muted': lineup_muted}

    if len(present) < 3:
        return [lineup(present)]
    return [lineup(('b', 'g')), lineup(('b', 'k')), lineup(('g', 'k'))]


def validate_camera_stacks(camera, lineups, near_ppq=0):
    findings = {
        'duplicates': [], 'near_stacks': [], 'unreachable': [],
        'uncovered': [], 'spots': 0, 'stacked': 0, 'events': len(camera),
    }
    index = 0
    previous_ppq = None
    previous_last = None
    while index < len(camera):
        ppq = camera[index]['ppq']
        end = index + 1
        while end < len(camera) and camera[end]['ppq'] == ppq:
            end += 1
        raw_group = camera[index:end]
        findings['spots'] += 1
        counts = {}
        group = []
        for event in raw_group:
            counts[event['msg']] = counts.get(event['msg'], 0) + 1
            if counts[event['msg']] == 1:
                group.append(event)
        for message in [event['msg'] for event in group]:
            if counts[message] > 1:
                row = dict(group[[event['msg'] for event in group].index(message)])
                row['count'] = counts[message]
                findings['duplicates'].append(row)
        if len(group) > 1:
            findings['stacked'] += 1
        if (previous_ppq is not None and near_ppq > 0 and
                ppq - previous_ppq <= near_ppq):
            row = dict(group[0])
            row.update({'prev_ppq': previous_ppq, 'prev_msg': previous_last,
                        'delta': ppq - previous_ppq})
            findings['near_stacks'].append(row)

        won = set()
        blind = []
        for lineup in lineups:
            chosen = pick_priority_camera_event(group, lineup['muted'])
            if chosen:
                won.add(chosen['msg'])
            else:
                kind, note = 'generic', None
                if len(group) == 1 and group[0]['msg'] in COOP_DUO:
                    remaining = [INSTRUMENT_NAMES[letter]
                                 for letter in coop_required_instruments(group[0]['msg'])
                                 if not lineup['muted'].get(letter)]
                    if remaining:
                        kind, note = 'duo_single', ' + '.join(remaining)
                blind.append({'label': lineup['label'], 'kind': kind, 'note': note})
        if blind:
            row = dict(group[0])
            row.update({'shots': [event['msg'] for event in group],
                        'lineups': blind})
            findings['uncovered'].append(row)
        if len(group) > 1:
            for event in group:
                if event['msg'] in won:
                    continue
                fits = False
                beaten_by = None
                for lineup in lineups:
                    if camera_shot_fits_band(event['msg'], lineup['muted']):
                        fits = True
                        winner = pick_priority_camera_event(group, lineup['muted'])
                        if winner:
                            beaten_by = winner['msg']
                row = dict(event)
                row.update({'fits_any': fits, 'beaten_by': beaten_by})
                findings['unreachable'].append(row)
        previous_ppq, previous_last = ppq, group[-1]['msg']
        index = end
    return findings


def _muted_instruments(host):
    muted = {}
    for letter, name in INSTRUMENT_TRACKS.items():
        track = find_named_track(host, name)
        if track is None or host.track_muted(track):
            muted[letter] = True
    return muted


def validate_venue_camera(host):
    try:
        unused_track, unused_contexts, events = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        return 'VENUE camera validation could not run.', str(exc)
    camera = [event for event in events if event['meta_type'] == 1 and
              event['msg'].startswith(('[coop_', '[directed_'))]
    if not camera:
        return ('VENUE has no camera events.',
                'The VENUE track has no [coop_*] or [directed_*] events to validate.')
    lineups = build_band_lineups(_muted_instruments(host))
    findings = validate_camera_stacks(camera, lineups, 60)  # 1/8 QN at 480 PPQ
    start, end = host.time_selection()
    scope = ('whole song' if start is None else 'time selection %s - %s' %
             (format_time(start), format_time(end)))

    def scoped(rows):
        if start is None:
            return rows
        return [row for row in rows if start <= row['t'] <= end]

    duplicates = scoped(findings['duplicates'])
    near = scoped(findings['near_stacks'])
    unreachable = scoped(findings['unreachable'])
    uncovered = scoped(findings['uncovered'])
    total = len(duplicates) + len(near) + len(unreachable) + len(uncovered)
    lines = [('VENUE camera validation - %s  (%s)' %
              ('no issues' if total == 0 else '%d issue%s' %
               (total, '' if total == 1 else 's'), scope)), '',
             'Lineups this project can put on stage (%d):' % len(lineups)]
    lines.extend('  ' + lineup['label'] for lineup in lineups)
    lines.append('')

    if duplicates:
        lines.append('Shots written twice on one tick (%d):' % len(duplicates))
        lines.extend('  %s   %s  x%d' %
                     (format_time(row['t']), row['msg'], row['count'])
                     for row in duplicates)
    else:
        lines.append('Shots written twice on one tick: none.')
    lines.append('')
    if near:
        lines.append('Shots too close to be separate cuts (%d):' % len(near))
        lines.extend('  %s   %s is %d ticks after %s; stack them on one tick' %
                     (format_time(row['t']), row['msg'], row['delta'],
                      row['prev_msg']) for row in near)
    else:
        lines.append('Shots too close to be separate cuts: none.')
    lines.append('')
    if unreachable:
        lines.append('Stacked shots that never play (%d):' % len(unreachable))
        for row in unreachable:
            reason = ('needs an instrument no lineup puts on stage'
                      if not row['fits_any'] else
                      'is outranked by %s wherever it fits' % row['beaten_by'])
            lines.append('  %s   %s - %s' %
                         (format_time(row['t']), row['msg'], reason))
    else:
        lines.append('Stacked shots that never play: none.')
    lines.append('')
    if uncovered:
        lines.append('Spots with no valid camera shot for some lineup (%d):' %
                     len(uncovered))
        for row in uncovered[:40]:
            labels = ', '.join(lineup['label'] for lineup in row['lineups'])
            lines.append('  %s   %s - no valid shot for %s' %
                         (format_time(row['t']), ', '.join(row['shots']), labels))
        if len(uncovered) > 40:
            lines.append('  ... and %d more spots.' % (len(uncovered) - 40))
        lines.append('  Game fallback shots are %s.' % ', '.join(GENERIC_FALLBACK))
        lines.append('  Letting the game fall back is valid where deliberate.')
    else:
        lines.append('Spots with no valid camera shot for some lineup: none.')
    lines.extend(('', 'Checked (whole track):',
                  '  %d camera events across %d spots, %d stacked' %
                  (findings['events'], findings['spots'], findings['stacked']),
                  '  %d lineup%s replayed at every spot' %
                  (len(lineups), '' if len(lineups) == 1 else 's')))
    status = ('VENUE camera: no issues found.' if total == 0 else
              'VENUE camera: %d issue%s found.' %
              (total, '' if total == 1 else 's'))
    return status, '\n'.join(lines)
