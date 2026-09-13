"""Desktop tests for Venue > Manual gen guarded actions."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.midi_chunk import parse_midi_chunk
from rock_band_general_helper_vkr.actions_venue_manual import (
    advance_camera_pacing, blend_venue_preset, generate_manual_keyframes,
    insert_venue_event, remove_venue_events,
)
from test_venue_themes import FakeHost, midi_chunk


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class ManualHost(FakeHost):
    def __init__(self):
        FakeHost.__init__(self)
        self.cursor = 1.0
        self.selection = (None, None)

    def cursor_position(self):
        return self.cursor

    def set_cursor_position(self, seconds):
        self.cursor = float(seconds)

    def time_selection(self):
        return self.selection

    def master_tempo(self):
        return 120.0


class MidRng(object):
    def random(self):
        return 0.5


def _texts(host):
    return [(event.absolute_tick, event.meta_payload)
            for event in parse_midi_chunk(host.tracks[0][1]).text_events(1)]


def test_insert_and_first_guard_use_cursor_tick():
    host = ManualHost()
    host.tracks[0][1] = midi_chunk([
        (0, 3, 'VENUE'), (480, 1, '[lighting (verse)]')])
    status, unused_report = insert_venue_event(host, '[coop_all_far]')
    expect('Inserted' in status and (960, '[coop_all_far]') in _texts(host),
           'camera event was not inserted at cursor')
    status, report = insert_venue_event(host, '[first]')
    expect('blocked' in status and 'manual lighting' in report,
           '[first] was accepted away from manual lighting')


def test_blend_and_manual_keyframes_are_guarded():
    host = ManualHost()
    host.cursor = 0.5
    host.tracks[0][1] = midi_chunk([
        (0, 3, 'VENUE'), (480, 1, '[lighting (verse)]'),
        (2400, 1, '[lighting (chorus)]')])
    status, unused_report = generate_manual_keyframes(host, 1, 0, 0)
    expect('Generated' in status and (480, '[first]') in _texts(host),
           'manual keyframe train did not start at lighting event')
    host.cursor = 1.5
    status, unused_report = blend_venue_preset(host, 'lighting')
    expect('blend anchor' in status and
           (1440, '[lighting (verse)]') in _texts(host),
           'active lighting was not copied as blend anchor')
    expect(host.undo.count('begin') == 2,
           'accepted manual actions did not create one undo block each')


def test_remove_is_scoped_and_advance_uses_qn():
    host = ManualHost()
    host.tracks[0][1] = midi_chunk([
        (0, 3, 'VENUE'), (480, 1, '[coop_all_far]'),
        (960, 1, '[lighting (verse)]'), (1440, 1, '[directed_all]')])
    host.selection = (0.4, 1.2)
    status, report = remove_venue_events(host, 0)
    expect('Removed 1 Camera' in status and 'time selection' in report,
           'camera removal did not respect time selection')
    expect((480, '[coop_all_far]') not in _texts(host) and
           (1440, '[directed_all]') in _texts(host),
           'camera removal changed an event outside its range')

    host.cursor = 2.0
    status, unused_report = advance_camera_pacing(
        host, 1, 16, True, MidRng())
    expect('Advanced' in status and abs(host.cursor - 5.0) < 1e-8,
           'slow pacing did not advance by 24 sixteenths at 120 BPM')


def run():
    tests = [value for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    for test in tests:
        test()
        print('PASS', test.__name__)
    print('Venue Manual gen tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    run()
