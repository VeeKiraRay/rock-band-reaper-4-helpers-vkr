"""Read-only VENUE/EVENTS parsing and reports for REAPER 4.20.

Modern counterparts:
rock_band_general_helper_vkr/venue.lua
rock_band_general_helper_vkr/venue_awareness.lua
rock_band_general_helper_vkr/actions_venue_subtracks.lua (categorization only)

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import re

from .actions_difficulty_shared import format_time
from .difficulty_read import _load_items, _tick_to_qn, _tick_to_time


DIRECTED_GAP_MIN = 2.0
META_NAMES = {
    1: 'Text', 2: 'Copyright', 3: 'Track Name',
    4: 'Instrument Name', 5: 'Lyric', 6: 'Marker', 7: 'Cue Point',
}

CAMERA_EVENTS = (
    'coop_all_behind', 'coop_all_far', 'coop_all_near',
    'coop_front_behind', 'coop_front_near',
    'coop_d_behind', 'coop_d_near', 'coop_v_behind', 'coop_v_near',
    'coop_b_behind', 'coop_b_near', 'coop_g_behind', 'coop_g_near',
    'coop_k_behind', 'coop_k_near', 'coop_d_closeup_hand',
    'coop_d_closeup_head', 'coop_v_closeup', 'coop_b_closeup_hand',
    'coop_b_closeup_head', 'coop_g_closeup_hand', 'coop_g_closeup_head',
    'coop_k_closeup_hand', 'coop_k_closeup_head', 'coop_dv_near',
    'coop_bd_near', 'coop_dg_near', 'coop_bv_behind', 'coop_bv_near',
    'coop_gv_behind', 'coop_gv_near', 'coop_kv_behind', 'coop_kv_near',
    'coop_bg_behind', 'coop_bg_near', 'coop_bk_behind', 'coop_bk_near',
    'coop_gk_behind', 'coop_gk_near',
    'directed_all', 'directed_all_cam', 'directed_all_lt',
    'directed_all_yeah', 'directed_bre', 'directed_brej',
    'directed_crowd', 'directed_drums', 'directed_drums_pnt',
    'directed_drums_np', 'directed_drums_lt', 'directed_drums_kd',
    'directed_vocals', 'directed_vocals_np', 'directed_vocals_cls',
    'directed_vocals_cam_pr', 'directed_vocals_cam_pt',
    'directed_stagedive', 'directed_crowdsurf', 'directed_bass',
    'directed_crowd_b', 'directed_bass_np', 'directed_bass_cam',
    'directed_bass_cls', 'directed_guitar', 'directed_crowd_g',
    'directed_guitar_np', 'directed_guitar_cls',
    'directed_guitar_cam_pr', 'directed_guitar_cam_pt', 'directed_keys',
    'directed_keys_cam', 'directed_keys_np', 'directed_duo_drums',
    'directed_duo_bass', 'directed_duo_guitar', 'directed_duo_kv',
    'directed_duo_gb', 'directed_duo_kb', 'directed_duo_kg',
)
POSTPROC_EVENTS = (
    'bloom.pp', 'bright.pp', 'clean_trails.pp', 'contrast_a.pp',
    'desat_blue.pp', 'desat_posterize_trails.pp', 'film_16mm.pp',
    'film_b+w.pp', 'film_blue_filter.pp', 'film_contrast.pp',
    'film_contrast_blue.pp', 'film_contrast_green.pp',
    'film_contrast_red.pp', 'film_sepia_ink.pp', 'film_silvertone.pp',
    'flicker_trails.pp', 'horror_movie_special.pp', 'photo_negative.pp',
    'photocopy.pp', 'posterize.pp', 'ProFilm_a.pp', 'ProFilm_b.pp',
    'ProFilm_mirror_a.pp', 'ProFilm_psychedelic_blue_red.pp',
    'shitty_tv.pp', 'space_woosh.pp', 'video_a.pp', 'video_bw.pp',
    'video_security.pp', 'video_trails.pp',
)
LIGHTING_NAMES = (
    '', 'verse', 'chorus', 'manual_cool', 'manual_warm', 'dischord',
    'stomp', 'loop_cool', 'loop_warm', 'harmony', 'frenzy',
    'silhouettes', 'silhouettes_spot', 'searchlights', 'sweep',
    'strobe_slow', 'strobe_fast', 'blackout_slow', 'blackout_fast',
    'flare_slow', 'flare_fast', 'bre', 'intro', 'blackout_spot',
)
MANUAL_LIGHTING = frozenset(
    '[lighting (%s)]' % name for name in
    ('verse', 'chorus', 'manual_cool', 'manual_warm', 'dischord', 'stomp'))
VENUE_VALID = frozenset(
    ['[bonusfx]', '[bonusfx_optional]', '[first]', '[previous]', '[next]'] +
    ['[%s]' % name for name in CAMERA_EVENTS] +
    ['[%s]' % name for name in POSTPROC_EVENTS] +
    ['[lighting (%s)]' % name for name in LIGHTING_NAMES])

INSTRUMENT_TRACKS = {
    'd': 'PART DRUMS', 'v': 'PART VOCALS', 'b': 'PART BASS',
    'g': 'PART GUITAR', 'k': 'PART KEYS',
}
INSTRUMENT_NAMES = {
    'd': 'Drums', 'v': 'Vocals', 'b': 'Bass', 'g': 'Guitar', 'k': 'Keys',
}


class VenueReadError(Exception):
    pass


def find_named_track(host, name):
    wanted = name.strip().upper()
    for index in range(host.track_count()):
        track = host.get_track(index)
        if host.track_name(track, index).strip().upper() == wanted:
            return track
    return None


def read_named_track(host, name):
    """Return ``(track, contexts, events)`` for every MIDI item on a track."""
    track = find_named_track(host, name)
    if track is None:
        raise VenueReadError('No track named "%s" found in this project.' % name)
    contexts = _load_items(host, track)
    if not contexts:
        raise VenueReadError('Found the %s track but it has no MIDI items.' % name)
    events = []
    for context_index, context in enumerate(contexts):
        for event in context['parsed'].text_events():
            qn = _tick_to_qn(context, event.absolute_tick)
            events.append({
                'msg': event.meta_payload or '',
                'meta_type': event.meta_type,
                't': _tick_to_time(host, context, event.absolute_tick),
                # A project-wide 480 PPQ axis lets validators safely span items.
                'ppq': int(round(qn * 480.0)),
                'source_tick': event.absolute_tick,
                'context_index': context_index,
                'ordinal': event.ordinal,
            })
    events.sort(key=lambda value: (
        value['t'], value['context_index'], value['ordinal']))
    return track, contexts, events


def categorize_venue_event(message):
    if message in ('[first]', '[next]', '[previous]'):
        return 'keyframe'
    if message.startswith('[coop_'):
        return 'coop'
    if message.startswith('[directed_'):
        return 'directed'
    if message.startswith('[lighting'):
        return 'lighting'
    if message.endswith('.pp]'):
        return 'postproc'
    return 'special'


def is_blend_anchor(previous, event):
    return previous is not None and event is not None and (
        previous['msg'] == event['msg'])


def annotate_venue_blends(events):
    """Collapse duplicate blend anchors and annotate the surviving states."""
    if not events:
        return []
    result = []
    raw_indexes = []
    for index, event in enumerate(events):
        if not is_blend_anchor(events[index - 1] if index else None, event):
            result.append(dict(event))
            raw_indexes.append(index)
    for out_index, event in enumerate(result[:-1]):
        raw_index = raw_indexes[out_index]
        next_index = raw_indexes[out_index + 1]
        event['next_t'] = events[next_index]['t']
        if next_index > raw_index + 1:
            event['blend_out_t'] = events[next_index - 1]['t']
            event['blend_out_ppq'] = events[next_index - 1]['ppq']
    return result


def _camera_gaps(events):
    primary, secondary = [], []
    for current, following in zip(events, events[1:]):
        row = {
            'gap': following['t'] - current['t'], 't': current['t'],
            'from': current['msg'], 'to': following['msg'],
        }
        if current['msg'].startswith('[coop'):
            primary.append(row)
        elif (current['msg'].startswith('[directed') and
              following['msg'].startswith('[coop')):
            secondary.append(row)
    return primary, secondary


def _append_gap_stats(lines, label, gaps):
    lines.append(label)
    if not gaps:
        lines.extend(('  No transitions found.', ''))
        return
    slowest = max(gaps, key=lambda value: value['gap'])
    fastest = min(gaps, key=lambda value: value['gap'])
    average = sum(value['gap'] for value in gaps) / float(len(gaps))
    lines.extend((
        '  Count:    %d' % len(gaps),
        '  Average:  %.2fs' % average,
        '  Slowest:  %.2fs  -  %s  (%s)' % (
            slowest['gap'], format_time(slowest['t']), slowest['from']),
        '  Fastest:  %.2fs  -  %s  (%s)' % (
            fastest['gap'], format_time(fastest['t']), fastest['from']),
        '',
    ))


def list_venue_events(host):
    try:
        unused_track, unused_contexts, all_events = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        return 'No VENUE data found.', str(exc)
    if not all_events:
        return 'VENUE track has no text events.', "VENUE track doesn't have any text events."

    track_names = [event for event in all_events if event['meta_type'] == 3]
    venue_events = [event for event in all_events
                    if event['meta_type'] == 1 and event['msg'].startswith('[')]
    unexpected = [event for event in all_events
                  if event not in track_names and event not in venue_events]
    lines = []
    if not track_names:
        lines.append('ERROR: Track name event missing - expected Track Name "VENUE" at 1.1.00.')
    elif len(track_names) > 1:
        lines.append('ERROR: Track name event duplicated (%d found):' % len(track_names))
        for event in track_names:
            lines.append('  %s  "%s"' % (format_time(event['t']), event['msg']))
    else:
        event = track_names[0]
        if event['source_tick'] != 0:
            lines.append('ERROR: Track name "%s" is not at 1.1.00 - found at %s.' %
                         (event['msg'], format_time(event['t'])))
        elif event['msg'] != 'VENUE':
            lines.append('ERROR: Track name is "%s" - expected "VENUE".' % event['msg'])
        else:
            lines.append('Track name: "VENUE" at 1.1.00.  OK')
    lines.append('')
    if unexpected:
        lines.append('Unexpected event types (%d):' % len(unexpected))
        for event in unexpected:
            label = META_NAMES.get(event['meta_type'], 'type %s' % event['meta_type'])
            lines.append('  %s  [%s]  "%s"' %
                         (format_time(event['t']), label, event['msg']))
    else:
        lines.append('All non-track-name events are type 1 (Text).  OK')
    lines.append('')
    unknown = []
    for event in venue_events:
        if event['msg'] not in VENUE_VALID and event['msg'] not in unknown:
            unknown.append(event['msg'])
    if unknown:
        lines.append('Unrecognized events (%d unique):' % len(unknown))
        lines.extend('  ' + message for message in unknown)
    else:
        lines.append('All text events are valid.')
    lines.append('')

    camera = [event for event in venue_events
              if event['msg'].startswith(('[coop', '[directed'))]
    repeats = [camera[index] for index in range(1, len(camera))
               if camera[index]['msg'] == camera[index - 1]['msg']]
    if repeats:
        lines.append('Consecutive repeated camera events (%d):' % len(repeats))
        lines.extend('  %s  %s' % (format_time(event['t']), event['msg'])
                     for event in repeats)
    else:
        lines.append('No consecutive repeated camera events.')
    lines.append('')
    short_directed = []
    for current, following in zip(camera, camera[1:]):
        gap = following['t'] - current['t']
        if current['msg'].startswith('[directed') and gap < DIRECTED_GAP_MIN:
            short_directed.append((current, following, gap))
    if short_directed:
        lines.append('Directed cuts - next camera event within 2s, double-check (%d):' %
                     len(short_directed))
        for current, following, gap in short_directed:
            lines.append('  %s  %s  ->  next in %.2fs  (%s)' %
                         (format_time(current['t']), current['msg'], gap,
                          following['msg']))
    else:
        lines.append('No directed cut spacing issues found.')
    lines.append('')
    primary, secondary = _camera_gaps(camera)
    _append_gap_stats(lines, 'Camera cut speed  (coop -> any):', primary)
    if secondary:
        _append_gap_stats(lines, 'Camera cut speed  (directed -> coop):', secondary)

    counts = {}
    for event in venue_events:
        counts[event['msg']] = counts.get(event['msg'], 0) + 1
    ordered = sorted(counts, key=lambda message: (-counts[message], message))
    lines.append('Event usage  (%d total, %d unique):' %
                 (len(venue_events), len(ordered)))
    lines.extend('  %3dx  %s' % (counts[message], message) for message in ordered)
    return ('VENUE: %d events, %d unique.' %
            (len(venue_events), len(ordered)), '\n'.join(lines))


def list_lighting_postproc(host):
    try:
        unused_track, unused_contexts, all_events = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        return 'No VENUE data found.', str(exc)
    events = [event for event in all_events if event['meta_type'] == 1 and
              categorize_venue_event(event['msg']) in ('lighting', 'postproc')]
    if not events:
        return ('No lighting or post-proc events found.',
                'The VENUE track has no [lighting*] or *.pp] text events.')
    lighting = sum(categorize_venue_event(event['msg']) == 'lighting'
                   for event in events)
    lines = ['Lighting/postproc events: %d total (%d lighting, %d postproc)' %
             (len(events), lighting, len(events) - lighting), '']
    lines.extend('%3d.  %s  %s' %
                 (index + 1, event['msg'], format_time(event['t']))
                 for index, event in enumerate(events))
    return '%d lighting/postproc events found.' % len(events), '\n'.join(lines)


_PRC_RE = re.compile(r'^\[prc_(.+)\]$')


def parse_prc_event(message):
    match = _PRC_RE.match(message or '')
    if not match:
        return None
    inner = match.group(1)
    match = re.match(r'^(.*)_(\d+)([a-z]?)$', inner)
    if match:
        return {'name': match.group(1), 'num': int(match.group(2)),
                'letter': match.group(3) or None}
    match = re.match(r'^(.*)_([a-z])$', inner)
    if match:
        return {'name': match.group(1), 'num': None, 'letter': match.group(2)}
    return {'name': inner, 'num': None, 'letter': None}


def build_event_sections(events, song_end):
    parsed = []
    for event in events:
        if event['meta_type'] != 1:
            continue
        value = parse_prc_event(event['msg'])
        if value:
            parsed.append((event['t'], value))
    parsed.sort(key=lambda row: row[0])
    sections = []
    for time_value, value in parsed:
        previous = sections[-1] if sections else None
        merge = (value['letter'] is not None and previous is not None and
                 previous['is_lettered'] and
                 previous['name'] == value['name'] and
                 previous['num'] == value['num'])
        if merge:
            previous['sub_count'] += 1
        else:
            sections.append({
                'name': value['name'], 'num': value['num'],
                'is_lettered': value['letter'] is not None, 'sub_count': 1,
                't_start': time_value, 't_end': song_end,
            })
    for index in range(len(sections) - 1):
        sections[index]['t_end'] = sections[index + 1]['t_start']
    return sections


def _project_end(host):
    end = 0.0
    count = getattr(host, 'project_item_count', lambda: 0)()
    for index in range(count):
        item = host.get_project_item(index)
        end = max(end, host.item_position(item) + host.item_length(item))
    return end


def list_event_sections(host):
    try:
        unused_track, unused_contexts, events = read_named_track(host, 'EVENTS')
    except VenueReadError as exc:
        return 'Error reading EVENTS track.', str(exc)
    song_end = _project_end(host)
    try:
        unused_track, venue_contexts, unused_events = read_named_track(host, 'VENUE')
        song_end = max(context['end'] for context in venue_contexts)
    except VenueReadError:
        pass
    sections = build_event_sections(events, song_end)
    if not sections:
        return ('No [prc_*] section markers found.',
                'The EVENTS track has no [prc_*] text events.\n\n'
                'Add section markers such as [prc_verse_1] and '
                '[prc_chorus_1] to enable section-aware generation.')
    lines = ['Event sections: %d total' % len(sections), '']
    for index, section in enumerate(sections):
        name = section['name'][:1].upper() + section['name'][1:]
        if section['num'] is not None:
            name += ' %d' % section['num']
        note = ('  (%d parts)' % section['sub_count']
                if section['is_lettered'] and section['sub_count'] > 1 else '')
        lines.append('%3d.  %s  %s  ->  %s%s' %
                     (index + 1, name, format_time(section['t_start']),
                      format_time(section['t_end']), note))
    return '%d event sections detected.' % len(sections), '\n'.join(lines)
