"""Pure timeline helpers for the VENUE Preview views.

Modern counterparts:
rock_band_general_helper_vkr/venue.lua
rock_band_general_helper_vkr/ui_venue_preview.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import re
from bisect import bisect_right

from .actions_venue_validate_camera import pick_priority_camera_event
from .venue import VenueReadError, annotate_venue_blends, read_named_track


PLAYER_COMBOS = (
    ('Bass + Guitar', 'k'),
    ('Bass + Keys', 'g'),
    ('Guitar + Keys', 'b'),
)

FALLBACK_NOTE = (
    'No stacked camera shot matches the selected band. In game, the camera '
    'system falls back to a generic full-band shot. A normal duo shot may be '
    'converted to a single shot of the remaining member; directed cuts have '
    'no documented duo-to-single fallback.')


def get_venue_events_for_preview(host):
    """Read and categorize authored type-1 VENUE events."""
    unused_track, unused_contexts, events = read_named_track(host, 'VENUE')
    text_events = [event for event in events if event['meta_type'] == 1]
    camera = [event for event in text_events if
              event['msg'].startswith(('[coop_', '[directed_'))]
    lighting = [event for event in text_events if
                event['msg'].startswith('[lighting')]
    postproc = [event for event in text_events if event['msg'].endswith('.pp]')]
    return {
        'camera': camera,
        'lighting': annotate_venue_blends(lighting),
        'postproc': annotate_venue_blends(postproc),
    }


def group_at(events, index):
    """Return the complete same-position group containing ``index``."""
    ppq = events[index]['ppq']
    first = index
    last = index
    while first > 0 and events[first - 1]['ppq'] == ppq:
        first -= 1
    while last + 1 < len(events) and events[last + 1]['ppq'] == ppq:
        last += 1
    return events[first:last + 1], first, last


def surrounding_groups(events, playhead):
    """Return previous/current/next same-tick groups around ``playhead``."""
    if not events:
        return None, None, None
    current_index = None
    for index, event in enumerate(events):
        if event['t'] <= playhead:
            current_index = index
        else:
            break
    if current_index is None:
        return None, None, group_at(events, 0)[0]
    current, first, last = group_at(events, current_index)
    previous = group_at(events, first - 1)[0] if first > 0 else None
    following = group_at(events, last + 1)[0] if last + 1 < len(events) else None
    return previous, current, following


def build_grouped_timeline(events):
    """Pre-group same-tick events for inexpensive repeated playhead lookup."""
    groups = []
    times = []
    index = 0
    while index < len(events):
        group, unused_first, last = group_at(events, index)
        groups.append(group)
        times.append(group[0]['t'])
        index = last + 1
    return {'groups': tuple(groups), 'times': tuple(times)}


def surrounding_from_timeline(timeline, playhead):
    """Return surrounding groups using a precomputed binary-search index."""
    groups = timeline.get('groups', ())
    if not groups:
        return None, None, None
    current = bisect_right(timeline.get('times', ()), playhead) - 1
    if current < 0:
        return None, None, groups[0]
    previous = groups[current - 1] if current > 0 else None
    following = groups[current + 1] if current + 1 < len(groups) else None
    return previous, groups[current], following


def combo_muted(combo_index):
    """Return the instrument excluded by the selected four-player lineup."""
    try:
        absent = PLAYER_COMBOS[int(combo_index)][1]
    except (IndexError, TypeError, ValueError):
        absent = PLAYER_COMBOS[0][1]
    return {absent: True}


def resolve_group(group, muted=None):
    """Return ``(event, filtered)`` for one preview position."""
    if not group:
        return None, False
    if muted is None:
        return group[-1], False
    chosen = pick_priority_camera_event(group, muted)
    return (chosen, False) if chosen is not None else (group[-1], True)


def transition_text(event, playhead):
    """Describe how a lighting/post-process state hands off to the next."""
    if not event or 'next_t' not in event:
        return ''
    if 'blend_out_t' in event:
        if event['blend_out_t'] <= playhead < event['next_t']:
            return 'Blending now'
        return 'Blends into next'
    return 'Hard cut to next'


def bare_sprite_name(event, category):
    message = event['msg'] if event else ''
    if category == 'Lighting':
        match = re.match(r'^\[lighting \((.*?)\)\]$', message)
    else:
        match = re.match(r'^\[(.*?)\]$', message)
    return match.group(1) if match else message


def preview_signature(data, playhead, combo_index, surrounding):
    """Return a small signature used to avoid rebuilding animated widgets."""
    values = [int(combo_index), bool(surrounding)]
    muted = combo_muted(combo_index)
    for key in ('camera', 'lighting', 'postproc'):
        groups = surrounding_groups(data.get(key, ()), playhead)
        selected = groups if surrounding else (groups[1],)
        for group in selected:
            event, filtered = resolve_group(
                group, muted if key == 'camera' else None)
            values.append(None if event is None else (
                event.get('ppq'), event.get('msg'), bool(filtered),
                transition_text(event, playhead)))
    return tuple(values)


__all__ = [
    'FALLBACK_NOTE', 'PLAYER_COMBOS', 'VenueReadError', 'bare_sprite_name',
    'build_grouped_timeline', 'combo_muted', 'get_venue_events_for_preview',
    'group_at', 'preview_signature', 'resolve_group',
    'surrounding_from_timeline', 'surrounding_groups', 'transition_text',
]
