"""Desktop tests for Venue > Keyframes."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.midi_chunk import MidiChunkError, parse_midi_chunk
from rock_band_general_helper_vkr.actions_venue_keyframes import (
    VenueKeyframeGenerationError, regenerate_venue_keyframes,
)
from test_venue_themes import FakeHost, midi_chunk


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class KeyframeHost(FakeHost):
    def __init__(self, selection=(None, None)):
        FakeHost.__init__(self)
        self.selection = selection

    def time_selection(self):
        return self.selection


def _fixture(host):
    host.tracks[0][1] = midi_chunk([
        (0, 3, 'VENUE'),
        (480, 1, '[lighting (verse)]'),
        (480, 1, '[first]'),
        (720, 1, '[coop_all_far]'),
        (960, 1, '[lighting (verse)]'),
        (1200, 1, '[previous]'),
        (1440, 1, '[next]'),
        (1920, 1, '[lighting (loop_cool)]'),
        (2400, 1, '[lighting (chorus)]'),
        (2400, 1, '[first]'),
        (3360, 1, '[next]'),
        (3840, 1, '[lighting (chorus)]'),
        (4800, 1, '[lighting (verse)]'),
    ])


def _texts(host):
    return [(event.absolute_tick, event.meta_payload)
            for event in parse_midi_chunk(host.tracks[0][1]).text_events(1)]


def test_full_regeneration_uses_real_lighting_changes():
    host = KeyframeHost()
    _fixture(host)
    status, report = regenerate_venue_keyframes(host, 2, 0, 0)
    rows = _texts(host)
    expect('Regenerated' in status and '3 manual lighting span(s)' in report,
           'full keyframe result or span count differs')
    expect((480, '[first]') in rows and (2400, '[first]') in rows and
           (4800, '[first]') in rows,
           'manual lighting changes did not receive [first]')
    expect((960, '[first]') not in rows and (3840, '[first]') not in rows,
           'blend restatements incorrectly started keyframe spans')
    expect((1200, '[previous]') not in rows,
           'old [previous] event survived regenerated span')
    expect((720, '[coop_all_far]') in rows and
           (1920, '[lighting (loop_cool)]') in rows,
           'keyframe regeneration changed unrelated VENUE events')
    expect(len(host.writes) == 1 and host.undo[-1] ==
           'Regenerate VENUE keyframes',
           'keyframes did not use one guarded transaction')


def test_time_selection_only_starts_lighting_inside_selection():
    host = KeyframeHost((2.4, 4.5))
    _fixture(host)
    before = _texts(host)
    status, report = regenerate_venue_keyframes(host, 1, 0, 0)
    after = _texts(host)
    expect('time selection' in report and '1 manual lighting span(s)' in report,
           'time-selection keyframe scope differs')
    expect((480, '[first]') in after and (2400, '[first]') in after,
           'selection changed keyframes belonging to an outside trigger')
    expect([(tick, text) for tick, text in before if tick < 2304] ==
           [(tick, text) for tick, text in after if tick < 2304],
           'selection changed content before its first span')


def test_no_manual_lighting_is_a_noop_and_rate_is_validated():
    host = KeyframeHost()
    host.tracks[0][1] = midi_chunk([
        (0, 3, 'VENUE'), (480, 1, '[lighting (loop_cool)]')])
    status, report = regenerate_venue_keyframes(host, 2, 0, 0)
    expect(status == 'No manual lighting changes found.' and
           'No project changes were made' in report and not host.writes,
           'no-manual-lighting action was not a clean no-op')
    try:
        regenerate_venue_keyframes(host, 9, 0, 0)
    except VenueKeyframeGenerationError as exc:
        expect('1 to 8' in str(exc), 'invalid rate message differs')
    else:
        raise AssertionError('out-of-range keyframe rate was accepted')


def test_windowed_codec_preserves_other_payloads():
    chunk = midi_chunk([
        (0, 3, 'VENUE'), (480, 1, '[first]'),
        (720, 1, '[coop_all_far]'), (960, 1, '[next]')])
    changed = parse_midi_chunk(chunk).with_replaced_meta_event_windows(
        [(400, 1000)], [{'tick': 500, 'payload': '[first]'}],
        1, ('[first]', '[next]', '[previous]'))
    rows = [(event.absolute_tick, event.meta_payload)
            for event in parse_midi_chunk(changed).text_events(1)]
    expect((500, '[first]') in rows and (720, '[coop_all_far]') in rows and
           (480, '[first]') not in rows and (960, '[next]') not in rows,
           'windowed codec replaced the wrong meta events')
    try:
        parse_midi_chunk(chunk).with_replaced_meta_event_windows(
            [(400, 800), (700, 1000)], [], 1)
    except MidiChunkError:
        pass
    else:
        raise AssertionError('overlapping meta-event windows were accepted')


def test_keyframes_ui_constructs_and_clamps_rate():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_keyframes import VenueKeyframesView
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for Keyframes UI test')
        if root is not None:
            root.destroy()
        return
    try:
        class Controller(object):
            host = KeyframeHost()
            def show_result(self, unused_status, unused_result):
                pass
        view = VenueKeyframesView(root, Controller())
        view.rate.set(-3)
        view._clamp_rate()
        expect(view.rate.get() == 1,
               'Keyframes UI did not clamp the rate to 1-8')
        view.align.set('Guitar notes')
        view._sync_states()
        expect(view.subdivision_combo.instate(['readonly']),
               'instrument alignment did not enable subdivision')
    finally:
        root.destroy()


def main():
    tests = [
        test_full_regeneration_uses_real_lighting_changes,
        test_time_selection_only_starts_lighting_inside_selection,
        test_no_manual_lighting_is_a_noop_and_rate_is_validated,
        test_windowed_codec_preserves_other_payloads,
        test_keyframes_ui_constructs_and_clamps_rate,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Venue Keyframes tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
