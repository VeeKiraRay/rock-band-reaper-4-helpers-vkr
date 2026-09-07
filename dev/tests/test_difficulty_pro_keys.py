"""Desktop tests for read-only Difficulty > Pro Keys validation."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_difficulty import (
    read_pro_keys_data,
    run_pro_keys_checks,
    validate_all_pro_keys,
)
from lib.reaper420 import Reaper420Host


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def midi_chunk(notes, ppq=480):
    events = []
    for pitch, start, end in notes:
        events.append((start, 0, '90', pitch, 96))
        events.append((end, 1, '80', pitch, 0))
    events.sort(key=lambda event: (event[0], event[1], event[3]))
    previous = 0
    lines = []
    for tick, unused_order, status, pitch, velocity in events:
        lines.append('E %d %s %02x %02x\n' % (
            tick - previous, status, pitch, velocity))
        previous = tick
    return ('<ITEM\n<SOURCE MIDI\nHASDATA 1 %d QN\n%s'
            'IGNTEMPO 0 120 4 4\n>\n>\n') % (ppq, ''.join(lines))


class FakeHost(object):
    def item_count(self, unused_track):
        return 1

    def get_item(self, track, unused_index):
        return track

    def active_take(self, unused_item):
        return 'take'

    def take_play_rate(self, unused_take):
        return 1.0

    def item_position(self, unused_item):
        return 0.0

    def item_length(self, unused_item):
        return 30.0

    def take_start_offset(self, unused_take):
        return 0.0

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, quarter_notes):
        return float(quarter_notes) / 2.0

    def read_item_chunk(self, item):
        return item

    def measure_at(self, seconds):
        return int(float(seconds) // 2.0) + 1


def test_reader_separates_lane_markers_and_playable_notes():
    host = FakeHost()
    chunk = midi_chunk([
        (0, 0, 60), (48, 0, 120), (60, 480, 600), (116, 960, 1080),
    ])
    notes, shifts, events = read_pro_keys_data(host, chunk)
    expect(len(notes) == 4, 'full Pro Keys note read differs')
    expect([note['pitch'] for note in shifts] == [0],
           'lane shift marker was not separated')
    expect([event['pitches'] for event in events] == [[48], [60]],
           'playable events included marker or overdrive notes')


def test_medium_flags_missing_initial_and_mid_song_shift():
    host = FakeHost()
    chunk = midi_chunk([(48, 0, 120), (5, 240, 300), (50, 480, 600)])
    unused_notes, shifts, events = read_pro_keys_data(host, chunk)
    report, total = run_pro_keys_checks(host, 'M', events, shifts)
    expect(total >= 2, 'Medium lane marker issues were not counted')
    expect('No initial range marker' in report,
           'missing initial Pro Keys range was not reported')
    expect('shift not allowed' in report,
           'mid-song Medium lane shift was not reported')


def test_hard_interval_jump_includes_edit_hint():
    host = FakeHost()
    chunk = midi_chunk([(0, 0, 60), (48, 0, 120), (72, 480, 600)])
    unused_notes, shifts, events = read_pro_keys_data(host, chunk)
    report, total = run_pro_keys_checks(host, 'H', events, shifts)
    expect(total >= 1 and 'jump of 24 semitones' in report,
           'Hard interval jump was not reported')
    expect('-> ' in report, 'interval jump did not include an edit hint')


def test_lower_track_checks_expert_timing_and_measures():
    host = FakeHost()
    expert_chunk = midi_chunk([(0, 0, 60), (48, 0, 120)])
    lower_chunk = midi_chunk([(0, 0, 60), (48, 1920, 2040)])
    unused, unused_shifts, expert = read_pro_keys_data(host, expert_chunk)
    unused, shifts, lower = read_pro_keys_data(host, lower_chunk)
    report, total = run_pro_keys_checks(
        host, 'H', lower, shifts, expert)
    expect(total >= 2 and 'no Expert note within 1/8 note' in report,
           'lower-only note was not reported')
    expect('Measure 1 has Expert notes but none here' in report,
           'missing Expert measure was not reported')


def test_validate_all_reports_unchanged_hard_copy():
    host = FakeHost()
    chart = midi_chunk([(0, 0, 60), (48, 0, 120), (50, 480, 600)])
    status, report = validate_all_pro_keys(
        host, {'X': chart, 'H': chart, 'M': None, 'E': None})
    expect('H:2' in status,
           'Hard Pro Keys progression issues were not summarized')
    expect('unchanged copy of Expert' in report and 'NOT REDUCED' in report,
           'unchanged Pro Keys copy guidance is missing')


def test_legacy_measure_formatter_tuple_is_parsed():
    class FakeApi(object):
        def RPR_format_timestr_pos(self, seconds, value, capacity, mode):
            return (seconds, '12.3.50', capacity, mode)

    expect(Reaper420Host(FakeApi()).measure_at(4.0) == 12,
           'legacy measure-format tuple was not parsed')


def test_ui_auto_detects_all_pro_keys_tracks():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_difficulty import DifficultyView

    class TrackHost(object):
        names = ('PART REAL_KEYS_M', 'PART KEYS', 'PART REAL_KEYS_X',
                 'PART REAL_KEYS_E', 'PART REAL_KEYS_H')

        def track_count(self):
            return len(self.names)

        def get_track(self, index):
            return index

        def track_name(self, track, unused_index):
            return self.names[track]

        def project_info(self):
            return {'identity': 'test-project', 'path': '', 'name': 'Test'}

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for Pro Keys UI test')
        if root is not None:
            root.destroy()
        return
    try:
        shown = []
        view = DifficultyView(
            root, lambda status, result: shown.append((status, result)),
            TrackHost())
        selected = view.pro_keys_pane.selected_tracks(view.track_records)
        expect(selected == {'X': 2, 'H': 4, 'M': 0, 'E': 3},
               'Pro Keys tracks were not auto-detected by exact name')
        view.refresh_tracks(focus='pro_keys')
        expect(shown[-1][0] == 'Pro Keys tracks auto-detected.' and
               'PART REAL_KEYS_X/H/M/E' in shown[-1][1],
               'Pro Keys refresh result used the wrong sub-tab wording')
        view.refresh_tracks(focus='keys')
        expect(shown[-1][0] == 'Keys track auto-detected.' and
               'PART KEYS' in shown[-1][1],
               'Keys refresh result used the wrong sub-tab wording')
    finally:
        root.destroy()


def main():
    tests = [
        test_reader_separates_lane_markers_and_playable_notes,
        test_medium_flags_missing_initial_and_mid_song_shift,
        test_hard_interval_jump_includes_edit_hint,
        test_lower_track_checks_expert_timing_and_measures,
        test_validate_all_reports_unchanged_hard_copy,
        test_legacy_measure_formatter_tuple_is_parsed,
        test_ui_auto_detects_all_pro_keys_tracks,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty Pro Keys tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
