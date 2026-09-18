"""Instrument play-state data for Venue generation and status rows.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .difficulty_read import _load_items, read_midi_text_events
from .venue import INSTRUMENT_NAMES, INSTRUMENT_TRACKS


PLAYER_ORDER = ('b', 'g', 'd', 'k', 'v')
PLAY_STATE_ACTIVE = frozenset(('[play]', '[mellow]', '[intense]'))
PLAY_STATE_IDLE = frozenset(('[idle]', '[idle_realtime]'))


def read_instrument_availability(host):
    """Return muted and missing maps for every supported PART track."""
    muted = {}
    missing = {}
    tracks = {}
    wanted = dict((name.upper(), letter)
                  for letter, name in INSTRUMENT_TRACKS.items())
    for index in range(host.track_count()):
        track = host.get_track(index)
        letter = wanted.get(host.track_name(track, index).strip().upper())
        if letter is not None and letter not in tracks:
            tracks[letter] = track
    for letter in PLAYER_ORDER:
        track = tracks.get(letter)
        if track is None:
            muted[letter] = True
            missing[letter] = True
        elif host.track_muted(track):
            muted[letter] = True
    return tracks, muted, missing


def read_instrument_play_states(host):
    """Read PART-track play/idle timelines using legacy MIDI chunks."""
    tracks, muted, missing = read_instrument_availability(host)
    states = {}
    no_data = set()
    errors = {}
    for letter in PLAYER_ORDER:
        track = tracks.get(letter)
        if track is None:
            continue
        try:
            contexts = _load_items(host, track)
            text_events = read_midi_text_events(host, contexts, (1,))
        except Exception as exc:
            states[letter] = []
            no_data.add(letter)
            errors[letter] = str(exc)
            continue
        events = []
        for event in text_events:
            message = event['text']
            if message in PLAY_STATE_ACTIVE:
                events.append({
                    't': event['s'], 'is_active': True, 'msg': message})
            elif message in PLAY_STATE_IDLE:
                events.append({
                    't': event['s'], 'is_active': False, 'msg': message})
        events.sort(key=lambda value: value['t'])
        states[letter] = events
        if not events:
            no_data.add(letter)
    return {
        'states': states,
        'no_data': no_data,
        'muted': muted,
        'missing': missing,
        'errors': errors,
    }


def compute_player_states(playhead, snapshot):
    """Resolve each instrument's state at a project-time position."""
    states = snapshot.get('states', {})
    no_data = snapshot.get('no_data', set())
    muted = snapshot.get('muted', {})
    result = {}
    for letter in PLAYER_ORDER:
        if muted.get(letter):
            result[letter] = {'state': 'muted'}
            continue
        if letter in no_data:
            result[letter] = {'state': 'nodata'}
            continue
        last = None
        for event in states.get(letter, ()):
            if event['t'] <= playhead:
                last = event
            else:
                break
        if last is None:
            result[letter] = {'state': 'active'}
        else:
            result[letter] = {
                'state': 'active' if last['is_active'] else 'idle',
                'msg': last['msg'],
                't': last['t'],
            }
    return result


def player_tooltip(letter, info, snapshot, format_time):
    """Return the upstream-equivalent explanation for one player state."""
    track_name = INSTRUMENT_TRACKS[letter]
    if info['state'] == 'muted':
        if snapshot.get('missing', {}).get(letter):
            return '%s track is missing - excluded from venue generation.' % (
                track_name)
        return '%s is muted - excluded from venue generation.' % track_name
    if info['state'] == 'nodata':
        error = snapshot.get('errors', {}).get(letter)
        if error:
            return ('%s play-state events could not be read. The status row '
                    'uses the always-in-[play] fallback.\n\n%s' %
                    (track_name, error))
        return ('%s has no [play]/[idle] play-state events - the status row '
                'uses the always-in-[play] fallback.' % track_name)
    if info.get('msg'):
        return '%s - %s since %s.' % (
            track_name, info['msg'], format_time(info['t']))
    return '%s - active (before the first play-state event).' % track_name


__all__ = [
    'INSTRUMENT_NAMES', 'PLAYER_ORDER', 'compute_player_states',
    'player_tooltip', 'read_instrument_availability',
    'read_instrument_play_states',
]
