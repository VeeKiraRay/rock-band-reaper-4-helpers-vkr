"""Desktop tests for the shared Venue active-player row."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import rock_band_general_helper_vkr.venue_players as players_module
from rock_band_general_helper_vkr.venue_players import (
    compute_player_states, player_tooltip, read_instrument_play_states,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class FakeHost(object):
    def __init__(self):
        self.playing = False
        self.cursor = 0.0
        self.playhead = 0.0
        self.tracks = [
            {'name': 'PART BASS', 'muted': False},
            {'name': 'PART GUITAR', 'muted': False},
            {'name': 'PART DRUMS', 'muted': True},
            {'name': 'PART VOCALS', 'muted': False},
        ]

    def track_count(self):
        return len(self.tracks)

    def get_track(self, index):
        return self.tracks[index]

    def track_name(self, track, unused_index):
        return track['name']

    def track_muted(self, track):
        return track['muted']

    def play_state(self):
        return 1 if self.playing else 0

    def play_position(self):
        return self.playhead

    def cursor_position(self):
        return self.cursor


def fixture_snapshot():
    host = FakeHost()
    text = {
        'PART BASS': [
            {'s': 1.0, 'text': '[idle]'},
            {'s': 3.0, 'text': '[play]'},
        ],
        'PART GUITAR': [],
        'PART DRUMS': [{'s': 0.0, 'text': '[play]'}],
        'PART VOCALS': [{'s': 5.0, 'text': '[idle_realtime]'}],
    }
    original_load = players_module._load_items
    original_text = players_module.read_midi_text_events
    players_module._load_items = lambda unused_host, track: [track]
    players_module.read_midi_text_events = (
        lambda unused_host, contexts, unused_types: text[contexts[0]['name']])
    try:
        return read_instrument_play_states(host)
    finally:
        players_module._load_items = original_load
        players_module.read_midi_text_events = original_text


def test_reader_and_point_in_time_states_match_upstream_rules():
    snapshot = fixture_snapshot()
    row = compute_player_states(2.0, snapshot)
    expect(row['b']['state'] == 'idle' and row['b']['msg'] == '[idle]',
           'Bass idle event was not active at the playhead')
    expect(row['g']['state'] == 'nodata',
           'present track without state events was not amber')
    expect(row['d']['state'] == 'muted',
           'muted Drums track was not red')
    expect(row['k']['state'] == 'muted' and snapshot['missing']['k'],
           'missing Keys track was not red and marked missing')
    expect(row['v']['state'] == 'active' and not row['v'].get('msg'),
           'state before first event did not default to active')
    expect(compute_player_states(6.0, snapshot)['v']['state'] == 'idle',
           'later vocal idle event was not applied')


def test_player_tooltips_explain_missing_nodata_and_timed_states():
    snapshot = fixture_snapshot()
    row = compute_player_states(2.0, snapshot)
    formatter = lambda seconds: 'T%.1f' % seconds
    expect('track is missing' in player_tooltip(
        'k', row['k'], snapshot, formatter),
        'missing-track tooltip differs')
    expect('no [play]/[idle]' in player_tooltip(
        'g', row['g'], snapshot, formatter),
        'no-data tooltip differs')
    expect('[idle] since T1.0' in player_tooltip(
        'b', row['b'], snapshot, formatter),
        'timed play-state tooltip differs')


def test_tk_row_uses_the_four_documented_colors():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_players import (
        STATE_COLORS, VenueActivePlayersRow,
    )

    root = tk.Tk()
    root.withdraw()
    widget = VenueActivePlayersRow(root, host=FakeHost())
    try:
        widget.snapshot = fixture_snapshot()
        widget._update_row(2.0)
        expected = {
            'b': 'idle', 'g': 'nodata', 'd': 'muted',
            'k': 'muted', 'v': 'active',
        }
        for letter, state in expected.items():
            indicator = widget.indicators[letter]
            color = indicator['canvas'].itemcget(indicator['oval'], 'fill')
            expect(color == STATE_COLORS[state],
                   '%s indicator used %s instead of %s' %
                   (letter, color, STATE_COLORS[state]))
    finally:
        widget.destroy()
        root.destroy()


def test_polling_uses_cached_cursor_lookup_and_stopped_rescan():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    import rock_band_general_helper_vkr.ui_venue_players as ui_module

    host = FakeHost()
    root = tk.Tk()
    root.withdraw()
    widget = ui_module.VenueActivePlayersRow(root, host=host)
    calls = []
    try:
        widget.snapshot = fixture_snapshot()
        widget.active = True
        widget.last_playhead = 0.0
        widget.last_full_refresh = ui_module.time.time()
        widget.last_availability_refresh = ui_module.time.time()
        original_update = widget._update_row
        widget._update_row = lambda playhead=None: calls.append(
            ('lookup', playhead))
        widget.refresh = lambda: calls.append(('refresh', None))

        host.cursor = 2.0
        widget._poll()
        expect(calls == [('lookup', 2.0)],
               'stopped cursor move reread MIDI instead of using the cache')
        if widget.after_id is not None:
            widget.after_cancel(widget.after_id)
            widget.after_id = None

        calls[:] = []
        widget.last_full_refresh = (
            ui_module.time.time() - ui_module.FULL_REFRESH_SECONDS - 1.0)
        widget._poll()
        expect(calls == [('refresh', None)],
               'stopped five-second interval did not request a MIDI rescan')
        if widget.after_id is not None:
            widget.after_cancel(widget.after_id)
            widget.after_id = None

        calls[:] = []
        host.playing = True
        host.playhead = 3.0
        widget.last_full_refresh = 0.0
        widget._poll()
        expect(calls == [('lookup', 3.0)],
               'playback polling performed a full MIDI rescan')
        expect(widget.after_id is not None,
               'playback polling did not schedule its next fixed update')
        widget._update_row = original_update
    finally:
        widget.stop()
        widget.destroy()
        root.destroy()


def run():
    tests = [value for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    for test in tests:
        test()
        print('PASS', test.__name__)
    print('%d tests passed.' % len(tests))


if __name__ == '__main__':
    run()
