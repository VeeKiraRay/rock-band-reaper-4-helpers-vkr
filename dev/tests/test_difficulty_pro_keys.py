"""Desktop tests for read-only Difficulty > Pro Keys validation."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_difficulty import (
    copy_pro_keys,
    read_pro_keys_data,
    run_pro_keys_checks,
    validate_all_pro_keys,
)
from lib.midi_chunk import MidiChunkError, parse_midi_chunk
from lib.midi_chunk_transaction import MidiChunkTransactionError
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


class CopyHost(object):
    def __init__(self, chunks, positions=None, lengths=None):
        self.chunks = dict((track, list(values))
                           for track, values in chunks.items())
        self.positions = positions or {}
        self.lengths = lengths or {}
        self.write_calls = 0
        self.undo_begin = 0
        self.undo_end = []

    def item_count(self, track):
        return len(self.chunks[track])

    def get_item(self, track, index):
        return (track, index)

    def active_take(self, item):
        return 'take-%s-%d' % item

    def take_play_rate(self, unused_take):
        return 1.0

    def item_position(self, item):
        return self.positions.get(item, 0.0)

    def item_length(self, item):
        return self.lengths.get(item, 30.0)

    def take_start_offset(self, unused_take):
        return 0.0

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, quarter_notes):
        return float(quarter_notes) / 2.0

    def read_item_chunk(self, item):
        return self.chunks[item[0]][item[1]]

    def write_item_chunk(self, item, chunk):
        self.write_calls += 1
        self.chunks[item[0]][item[1]] = chunk

    def begin_undo(self):
        self.undo_begin += 1

    def end_undo(self, description):
        self.undo_end.append(description)

    def update_arrange(self):
        pass


def copied_notes(host, track, item_index=0):
    return parse_midi_chunk(host.chunks[track][item_index]).notes()


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


def test_pro_keys_copy_replaces_playable_and_lane_markers_only():
    source = midi_chunk([
        (0, 0, 60), (48, 0, 120), (60, 480, 720), (116, 0, 960),
    ])
    target = midi_chunk([(2, 0, 60), (50, 0, 120), (116, 0, 960)])
    host = CopyHost({'source': [source], 'target': [target]})
    confirmations = []
    status, report = copy_pro_keys(
        host, 'source', 'target', 'H',
        lambda message: confirmations.append(message) or True)
    notes = copied_notes(host, 'target')
    expect([note.pitch for note in notes] == [0, 48, 116, 60],
           'Pro Keys target ranges were not replaced correctly')
    copied = [note for note in notes if note.pitch != 116]
    expect([note.velocity for note in copied] == [100, 100, 100],
           'copied Pro Keys notes did not use velocity 100')
    expect(confirmations and 'PART REAL_KEYS_H already has 2' in
           confirmations[0], 'Pro Keys overwrite was not confirmed')
    expect(host.chunks['source'][0] == source,
           'Pro Keys source track was modified')
    expect('copied 3 notes from Expert' in status and
           'playable notes and lane-shift markers' in report,
           'Pro Keys copy result differs')
    expect(host.undo_begin == 1 and
           host.undo_end == ['Copy Pro Keys X to H'],
           'Pro Keys copy Undo point differs')


def test_pro_keys_copy_maps_notes_across_target_items():
    source = midi_chunk([(0, 0, 120), (60, 2400, 2520)])
    host = CopyHost(
        {'source': [source], 'target': [midi_chunk([]), midi_chunk([])]},
        positions={('target', 0): 0.0, ('target', 1): 2.5},
        lengths={('target', 0): 2.0, ('target', 1): 2.0})
    status, report = copy_pro_keys(host, 'source', 'target', 'H')
    expect([note.pitch for note in copied_notes(host, 'target', 0)] == [0],
           'first Pro Keys note mapped to the wrong target item')
    second = copied_notes(host, 'target', 1)
    expect(len(second) == 1 and second[0].pitch == 60 and
           second[0].start_tick == 0 and second[0].end_tick == 120,
           'later Pro Keys note lost its target-local tick context')
    expect('copied 2 notes' in status and '2 target MIDI items' in report,
           'multi-item Pro Keys copy summary differs')
    expect(len(host.undo_end) == 1,
           'multi-item Pro Keys copy did not use one Undo point')


def test_changed_pro_keys_source_blocks_target_write():
    source = midi_chunk([(48, 0, 120)])
    target = midi_chunk([(50, 0, 120)])
    host = CopyHost({'source': [source], 'target': [target]})

    def confirm_and_change(unused_message):
        host.chunks['source'][0] = source.replace(
            '<ITEM\n', '<ITEM\nNAME changed\n')
        return True

    try:
        copy_pro_keys(
            host, 'source', 'target', 'H', confirm_and_change)
    except MidiChunkTransactionError as exc:
        expect('changed after analysis' in str(exc),
               'changed Pro Keys source used the wrong refusal')
    else:
        raise AssertionError('changed Pro Keys source was accepted')
    expect(host.chunks['target'][0] == target and host.write_calls == 0 and
           host.undo_begin == 0,
           'changed Pro Keys source allowed a target write')


def test_declined_pro_keys_overwrite_makes_no_change():
    source = midi_chunk([(48, 0, 120)])
    target = midi_chunk([(50, 0, 120)])
    host = CopyHost({'source': [source], 'target': [target]})
    status, report = copy_pro_keys(
        host, 'source', 'target', 'H', lambda unused_message: False)
    expect(status == 'Copy to Hard cancelled.' and
           report == 'No project changes were made.',
           'declined Pro Keys overwrite result differs')
    expect(host.chunks['target'][0] == target and host.write_calls == 0 and
           host.undo_begin == 0,
           'declined Pro Keys overwrite changed the target')


def test_uncovered_or_same_target_track_is_refused():
    source = midi_chunk([(48, 0, 120)])
    host = CopyHost(
        {'source': [source], 'target': [midi_chunk([])]},
        positions={('target', 0): 5.0})
    try:
        copy_pro_keys(host, 'source', 'target', 'H')
    except MidiChunkError as exc:
        expect('no target item covers it' in str(exc),
               'uncovered note used the wrong refusal')
    else:
        raise AssertionError('uncovered Pro Keys note was accepted')
    expect(host.write_calls == 0 and host.undo_begin == 0,
           'uncovered-note refusal changed the target')
    try:
        copy_pro_keys(host, 'source', 'source', 'H')
    except MidiChunkError as exc:
        expect('must be different' in str(exc),
               'same-track refusal detail differs')
    else:
        raise AssertionError('same Pro Keys source and target was accepted')


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
        test_pro_keys_copy_replaces_playable_and_lane_markers_only,
        test_pro_keys_copy_maps_notes_across_target_items,
        test_changed_pro_keys_source_blocks_target_write,
        test_declined_pro_keys_overwrite_makes_no_change,
        test_uncovered_or_same_target_track_is_refused,
        test_legacy_measure_formatter_tuple_is_parsed,
        test_ui_auto_detects_all_pro_keys_tracks,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty Pro Keys tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
