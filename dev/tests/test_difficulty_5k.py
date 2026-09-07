"""Desktop tests for read-only Difficulty > Keys validation."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_difficulty_5k import (
    read_keys_events,
    validate_all_keys,
    validate_keys,
)
from rock_band_general_helper_vkr.actions_difficulty_shared import (
    charts_are_identical,
)


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
    def __init__(self, chunk):
        self.chunk = chunk

    def item_count(self, unused_track):
        return 1

    def get_item(self, unused_track, unused_index):
        return self.chunk

    def active_take(self, unused_item):
        return 'take'

    def take_play_rate(self, unused_take):
        return 1.0

    def item_position(self, unused_item):
        return 0.0

    def item_length(self, unused_item):
        return 20.0

    def take_start_offset(self, unused_take):
        return 0.0

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, quarter_notes):
        return float(quarter_notes) / 2.0

    def read_item_chunk(self, unused_item):
        return self.chunk


def event(moment, pitches, duration=0.125):
    return {
        's': moment, 'e': moment + duration,
        'qn': moment * 2.0, 'qn_e': (moment + duration) * 2.0,
        'pitches': pitches,
    }


def test_normalized_adjacent_charts_compare_equal():
    higher = [event(0.0, [96, 98]), event(1.0, [100])]
    lower = [event(0.0, [84, 86]), event(1.0, [88])]
    expect(charts_are_identical(lower, higher, 84, 96),
           'octave-shifted adjacent charts were not recognized')


def test_reader_keeps_forbidden_medium_orange_for_validation():
    host = FakeHost(midi_chunk([
        (72, 0, 120), (76, 0, 120),
    ]))
    events = read_keys_events(host, 'track', 'M')
    expect(events and events[0]['pitches'] == [72, 76],
           'reader hid the forbidden fifth Medium gem slot')
    unused_status, report = validate_keys(host, 'track', 'M')
    expect('outside the valid range' in report,
           'Medium Orange was not reported as out of range')


def test_medium_spacing_is_measured_in_qn():
    host = FakeHost(midi_chunk([
        (72, 0, 120), (73, 240, 360),
    ]))
    status, report = validate_keys(host, 'track', 'M')
    expect('issue' in status and 'min 1/4 note' in report,
           'half-beat Medium spacing was not rejected')


def test_validate_all_reports_unchanged_hard_copy():
    host = FakeHost(midi_chunk([
        (96, 0, 120), (97, 480, 600),
        (84, 0, 120), (85, 480, 600),
    ]))
    status, report = validate_all_keys(host, 'track')
    expect('H:2' in status,
           'Hard progression issues were not counted in summary')
    expect('unchanged copy of Expert' in report,
           'unchanged adjacent tier was not reported')
    expect('NOT REDUCED' in report,
           'equal adjacent note counts were not reported')


def test_ui_module_imports_without_starting_tk():
    from rock_band_general_helper_vkr import ui_difficulty
    expect(hasattr(ui_difficulty, 'DifficultyView'),
           'Difficulty Tk view is missing')


def test_ui_constructs_with_empty_track_list():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_difficulty import DifficultyView

    class EmptyProjectHost(object):
        def track_count(self):
            return 0

        def project_info(self):
            return {'identity': 'test-project', 'path': '', 'name': 'Test'}

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for construction test')
        if root is not None:
            root.destroy()
        return
    try:
        view = DifficultyView(
            root, lambda unused_status, unused_result: None,
            EmptyProjectHost())
        root.update_idletasks()
        expect(view.track_combo is view.keys_pane.track_combo,
               'Difficulty view does not own the Keys track combobox')
    finally:
        root.destroy()


def test_tk_callback_guard_restores_captured_builtins():
    from lib.tk_common import install_callback_builtins_guard

    try:
        import __builtin__ as builtins_module
    except ImportError:
        import builtins as builtins_module
    private_builtins = dict(vars(builtins_module))
    scope = {'__builtins__': private_builtins}
    source = (
        'class CallWrapper(object):\n'
        '    def __init__(self, callback):\n'
        '        self.callback = callback\n'
        '    def __call__(self, *args):\n'
        '        len(args)\n'
        '        try:\n'
        '            return self.callback(*args)\n'
        '        except SystemExit:\n'
        '            raise\n')
    eval(compile(source, '<callback-guard-test>', 'exec'), scope, scope)

    class FakeTkModule(object):
        pass

    fake_tk = FakeTkModule()
    fake_tk.CallWrapper = scope['CallWrapper']
    install_callback_builtins_guard(fake_tk)
    private_builtins.clear()
    result = fake_tk.CallWrapper(lambda: 'restored')()
    expect(result == 'restored' and 'len' in private_builtins,
           'callback guard did not restore Tkinter built-ins')


def test_blocking_event_loop_exits_when_window_is_destroyed():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from lib.tk_common import run_blocking_event_loop

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for event-loop test')
        if root is not None:
            root.destroy()
        return
    root.after(20, root.destroy)
    run_blocking_event_loop(root, tk, poll_seconds=0.001)


def main():
    tests = [
        test_normalized_adjacent_charts_compare_equal,
        test_reader_keeps_forbidden_medium_orange_for_validation,
        test_medium_spacing_is_measured_in_qn,
        test_validate_all_reports_unchanged_hard_copy,
        test_ui_module_imports_without_starting_tk,
        test_ui_constructs_with_empty_track_list,
        test_tk_callback_guard_restores_captured_builtins,
        test_blocking_event_loop_exits_when_window_is_destroyed,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty Keys compatibility tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
