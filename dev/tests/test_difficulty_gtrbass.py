"""Desktop tests for read-only Difficulty > Guitar/Bass validation."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_difficulty_gtrbass import (
    read_gtrbass_events,
    run_gtrbass_checks,
    validate_all_gtrbass,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def midi_chunk(notes, ppq=480):
    events = []
    for record in notes:
        pitch, start, end = record[:3]
        velocity = record[3] if len(record) > 3 else 96
        events.append((start, 0, '90', pitch, velocity))
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


def all_notes(host, chunk):
    from rock_band_general_helper_vkr.actions_difficulty_gtrbass import (
        _all_track_notes,
    )
    return _all_track_notes(host, chunk)


def test_medium_reads_forbidden_orange_and_flags_chord():
    host = FakeHost()
    chunk = midi_chunk([(72, 0, 120), (74, 0, 120), (76, 0, 120)])
    notes = all_notes(host, chunk)
    events = read_gtrbass_events(host, chunk, 'M', notes)
    report, total = run_gtrbass_checks(host, 'M', events, notes)
    expect(events[0]['pitches'] == [72, 74, 76],
           'Medium fifth gem slot was hidden')
    expect(total >= 3 and 'outside the valid range' in report,
           'Medium Orange or chord restrictions were not reported')
    expect('spans 4 frets' in report,
           'Medium chord span restriction was not reported')


def test_expert_green_orange_shapes_match_rules():
    host = FakeHost()
    chunk = midi_chunk([
        (96, 0, 120), (98, 0, 120), (100, 0, 120),
        (96, 480, 600), (100, 480, 600),
    ])
    notes = all_notes(host, chunk)
    events = read_gtrbass_events(host, chunk, 'X', notes)
    report, total = run_gtrbass_checks(host, 'X', events, notes)
    expect(total == 2,
           'Expert Green+Orange issue/advisory count differs')
    expect('illegal 3-note chord' in report and 'use as sparingly' in report,
           'Expert Green+Orange wording is missing')


def test_easy_force_hopo_and_spacing_are_reported():
    host = FakeHost()
    chunk = midi_chunk([
        (60, 0, 120), (61, 240, 360), (65, 0, 60),
    ])
    notes = all_notes(host, chunk)
    events = read_gtrbass_events(host, chunk, 'E', notes)
    report, total = run_gtrbass_checks(host, 'E', events, notes)
    expect(total >= 2 and 'force-HOPO marker found' in report,
           'Easy force-HOPO marker was not reported')
    expect('Advisory: note density grid' in report,
           'Easy spacing advisory was not reported')


def test_hard_trill_velocity_is_reported():
    host = FakeHost()
    chunk = midi_chunk([(84, 0, 120), (127, 0, 480, 40)])
    notes = all_notes(host, chunk)
    events = read_gtrbass_events(host, chunk, 'H', notes)
    report, total = run_gtrbass_checks(host, 'H', events, notes)
    expect(total == 1 and 'Trill marker velocity 40' in report,
           'Hard trill eligibility rule was not reported')


def test_validate_all_reports_unchanged_hard_copy():
    host = FakeHost()
    chunk = midi_chunk([
        (96, 0, 120), (97, 480, 600),
        (84, 0, 120), (85, 480, 600),
    ])
    status, report = validate_all_gtrbass(host, chunk, 'gtr')
    expect('H:2' in status,
           'Guitar Hard progression issues were not summarized')
    expect('unchanged copy of Expert' in report and 'NOT REDUCED' in report,
           'Guitar adjacent-tier guidance is missing')


def test_ui_preserves_guitar_and_bass_track_selections():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_difficulty import DifficultyView

    class TrackHost(object):
        names = ('PART BASS', 'OTHER', 'PART GUITAR')

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
        print('SKIP: Tk display unavailable for Guitar/Bass UI test')
        if root is not None:
            root.destroy()
        return
    try:
        shown = []
        view = DifficultyView(
            root, lambda status, result: shown.append((status, result)),
            TrackHost())
        pane = view.gtrbass_pane
        expect(pane.selected_track(view.track_records) == 2,
               'PART GUITAR was not auto-detected')
        pane.instrument_var.set('bass')
        pane._instrument_changed()
        expect(pane.selected_track(view.track_records) == 0,
               'PART BASS selection was overwritten during instrument switch')
        pane.instrument_var.set('gtr')
        pane._instrument_changed()
        expect(pane.selected_track(view.track_records) == 2,
               'PART GUITAR selection was not preserved')
        view.refresh_tracks(focus='gtrbass')
        expect(shown[-1][0] == 'Guitar/Bass tracks auto-detected.' and
               'PART GUITAR and PART BASS' in shown[-1][1],
               'Guitar/Bass refresh used the wrong wording')
    finally:
        root.destroy()


def main():
    tests = [
        test_medium_reads_forbidden_orange_and_flags_chord,
        test_expert_green_orange_shapes_match_rules,
        test_easy_force_hopo_and_spacing_are_reported,
        test_hard_trill_velocity_is_reported,
        test_validate_all_reports_unchanged_hard_copy,
        test_ui_preserves_guitar_and_bass_track_selections,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty Guitar/Bass tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
