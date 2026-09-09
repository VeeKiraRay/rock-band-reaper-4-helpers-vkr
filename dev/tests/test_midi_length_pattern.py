"""Desktop tests for the legacy MIDI Length and Pattern feature slice."""

from __future__ import print_function

import base64
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.midi_chunk import parse_midi_chunk
from lib.reaper420 import Reaper420Host
from rock_band_general_helper_vkr.actions_midi_length import (
    adjust_midi_note_lengths,
    resize_all_midi_items,
)
from rock_band_general_helper_vkr.actions_midi_common import MidiActionError
from rock_band_general_helper_vkr.actions_midi_replace import (
    capture_pattern,
    fill_range,
    get_pattern_pitch_range,
    go_to_match,
    list_matches,
    new_pattern_state,
    replace_all,
)
from rock_band_general_helper_vkr.ui_midi import MidiView


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def midi_chunk(notes, text=None):
    events = []
    if text is not None:
        payload = base64.b64encode(b'\xff\x01' + text.encode('ascii'))
        if not isinstance(payload, str):
            payload = payload.decode('ascii')
        events.append((0, -1, '<X 0 0\n  %s\n>\n' % payload))
    for pitch, start, end in notes:
        events.append((start, 1, ('E %%d 90 %02x 60\n' % pitch)))
        events.append((end, 0, ('E %%d 80 %02x 00\n' % pitch)))
    events.sort(key=lambda value: (value[0], value[1]))
    previous = 0
    rendered = []
    for tick, unused_order, template in events:
        if template.startswith('<X'):
            rendered.append(template)
        else:
            rendered.append(template % (tick - previous))
        previous = tick
    return ('<ITEM\nPOSITION 0\nLENGTH 8\n<SOURCE MIDI\n'
            'HASDATA 1 480 QN\n%sIGNTEMPO 0 120 4 4\n>\n>\n' %
            ''.join(rendered))


class FakeHost(object):
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.lengths = [8.0 for unused in chunks]
        self.selection = (None, None)
        self.cursor = 0.0
        self.undo = []
        self.writes = 0

    def track_count(self):
        return 1

    def get_track(self, unused_index):
        return 'track'

    def track_name(self, unused_track, unused_index):
        return 'PART DRUMS'

    def item_count(self, unused_track):
        return len(self.chunks)

    def get_item(self, unused_track, index):
        return index

    def project_item_count(self):
        return len(self.chunks)

    def get_project_item(self, index):
        return index

    def active_take(self, item):
        return 'take-%d' % item

    def take_play_rate(self, unused_take):
        return 1.0

    def take_start_offset(self, unused_take):
        return 0.0

    def item_position(self, unused_item):
        return 0.0

    def item_length(self, item):
        return self.lengths[item]

    def set_item_length(self, item, length):
        self.lengths[item] = float(length)

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, qn):
        return float(qn) / 2.0

    def time_selection(self):
        return self.selection

    def measure_at(self, seconds):
        return int(seconds) + 1

    def cursor_position(self):
        return self.cursor

    def set_cursor_position(self, seconds):
        self.cursor = float(seconds)

    def read_item_chunk(self, item):
        return self.chunks[item]

    def write_item_chunk(self, item, chunk):
        self.writes += 1
        self.chunks[item] = chunk

    def begin_undo(self):
        self.undo.append('begin')

    def end_undo(self, description):
        self.undo.append(description)

    def update_arrange(self):
        pass


def note_tuples(chunk):
    return [(note.pitch, note.start_tick, note.end_tick)
            for note in parse_midi_chunk(chunk).notes()]


def test_window_codec_preserves_unrelated_notes_and_text():
    original = midi_chunk([(96, 0, 120), (84, 960, 1080)], '[play]')
    parsed = parse_midi_chunk(original)
    changed = parsed.with_replaced_note_windows(96, 100, [{
        'start_tick': 0, 'end_tick': 480,
        'notes': [{'pitch': 98, 'start_tick': 0, 'end_tick': 240}],
    }])
    expect(note_tuples(changed) == [(98, 0, 240), (84, 960, 1080)],
           'window replacement changed an unrelated difficulty note')
    expect(parse_midi_chunk(changed).text_events(1)[0].meta_payload == '[play]',
           'window replacement did not preserve MIDI text')


def test_non_sustain_length_adjustment_and_noop_undo():
    host = FakeHost([midi_chunk([(96, 0, 20), (97, 480, 600),
                                (98, 960, 1440)])])
    status, unused_report = adjust_midi_note_lengths(
        host, 'track', 'Expert', 'non_sustains', 32, 3)
    expect('2 non-sustain' in status and
           note_tuples(host.chunks[0]) == [
               (96, 0, 60), (97, 480, 540), (98, 960, 1440)],
           'non-sustain adjustment did not preserve the sustain')
    undo_count = len(host.undo)
    adjust_midi_note_lengths(
        host, 'track', 'Expert', 'non_sustains', 32, 3)
    expect(len(host.undo) == undo_count,
           'no-op note adjustment created an Undo point')


def test_sustain_gap_uses_note_buried_under_sustain():
    host = FakeHost([midi_chunk([(96, 0, 960), (97, 720, 780)])])
    status, unused_report = adjust_midi_note_lengths(
        host, 'track', 'Expert', 'sustains', 32, 3)
    expect('1 sustain' in status and
           note_tuples(host.chunks[0])[0] == (96, 0, 540),
           'sustain did not stop before an overlapping following note')


def test_pattern_capture_replace_list_and_navigation():
    host = FakeHost([midi_chunk([
        (96, 0, 120), (97, 240, 360),
        (98, 960, 1080),
        (96, 1920, 2040), (97, 2160, 2280),
    ])])
    state = new_pattern_state()
    host.selection = (0.0, 1.0)
    capture_pattern(host, 'track', 1, state, 'search')
    host.selection = (1.0, 2.0)
    capture_pattern(host, 'track', 1, state, 'replace')
    host.selection = (None, None)
    status, report = list_matches(host, 'track', 1, state)
    expect('2 matches' in report and 'Listed 2' in status,
           'pattern scan did not find both instances')
    host.cursor = 0.2
    go_to_match(host, 'track', 1, state, 1)
    expect(abs(host.cursor - 2.0) < 1e-9,
           'Go Next did not move to the second match')
    status, unused_report = replace_all(host, 'track', 1, state)
    expert = [value for value in note_tuples(host.chunks[0])
              if 96 <= value[0] <= 100]
    expect('Replaced 2' in status and expert == [
        (98, 0, 120), (98, 960, 1080), (98, 1920, 2040)],
        'Replace All did not replace only matching windows')


def test_fill_range_tiles_complete_slots_only():
    host = FakeHost([midi_chunk([(98, 960, 1080)])])
    state = new_pattern_state()
    host.selection = (1.0, 2.0)
    capture_pattern(host, 'track', 1, state, 'replace')
    host.selection = (0.0, 2.5)
    status, unused_report = fill_range(host, 'track', 1, state)
    expert = [value for value in note_tuples(host.chunks[0])
              if 96 <= value[0] <= 100]
    expect('2 slots' in status and expert == [
        (98, 0, 120), (98, 960, 1080)],
        'Fill Range did not tile complete captured durations')


def test_pitch_ranges_match_rock_band_tracks():
    expect(get_pattern_pitch_range('PART DRUMS', 3) == (72, 76),
           'tiered Pattern pitch range differs')
    expect(get_pattern_pitch_range('PART REAL_KEYS_X', 0) == (48, 72),
           'Pro Keys Pattern pitch range differs')
    expect(get_pattern_pitch_range('EVENTS', 0) == (0, 127),
           'unknown-track Pattern range should be unrestricted')


def test_resize_refuses_unverified_source_extension():
    host = FakeHost([midi_chunk([(96, 0, 120)]),
                     midi_chunk([(97, 0, 120)])])
    host.lengths = [8.0, 4.0]
    try:
        resize_all_midi_items(host, 'track')
    except MidiActionError as exc:
        expect('cannot safely extend' in str(exc),
               'source-extension refusal used the wrong detail')
    else:
        raise AssertionError('unverified MIDI source extension was accepted')
    expect(host.lengths == [8.0, 4.0] and not host.undo,
           'source-extension refusal changed the project')


def test_legacy_time_selection_and_cursor_adapter_shapes():
    calls = []

    class Api(object):
        def RPR_GetSet_LoopTimeRange(self, is_set, is_loop, start, end,
                                     allow_seek):
            calls.append(('selection', is_set, is_loop, start, end,
                          allow_seek))
            return (False, False, 1.25, 3.5, False)

        def RPR_GetCursorPosition(self):
            return 2.0

        def RPR_SetEditCurPos(self, seconds, move_view, seek_play):
            calls.append(('cursor', seconds, move_view, seek_play))

    host = Reaper420Host(Api())
    expect(host.time_selection() == (1.25, 3.5) and
           host.cursor_position() == 2.0,
           'legacy selection/cursor tuple shape differs')
    host.set_cursor_position(4.25)
    expect(calls == [
        ('selection', False, False, 0.0, 0.0, False),
        ('cursor', 4.25, True, False)],
        'legacy cursor setter arguments differ')


def test_legacy_track_midi_filter_uses_item_chunks():
    class Api(object):
        def RPR_CountTrackMediaItems(self, unused_track):
            return 2

        def RPR_GetTrackMediaItem(self, unused_track, index):
            return index

        def RPR_GetActiveTake(self, item):
            return None if item == 0 else 'take'

        def RPR_GetSetItemState(self, item, unused_chunk, capacity):
            chunk = ('<ITEM\n<SOURCE MIDI\nHASDATA 1 480 QN\n>\n>\n'
                     if item == 1 else '<ITEM\n<SOURCE WAVE\n>\n>\n')
            return True, item, chunk, capacity

    host = Reaper420Host(Api())
    expect(host.track_has_midi('track'),
           'legacy MIDI filter did not detect the active MIDI item')


def test_midi_view_filters_tracks_and_updates_pattern_button_states():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk

    class ViewHost(object):
        tracks = ('audio', 'drums', 'venue')

        def track_count(self):
            return len(self.tracks)

        def get_track(self, index):
            return self.tracks[index]

        def track_name(self, track, unused_index):
            return {'audio': 'GUITAR', 'drums': 'PART DRUMS',
                    'venue': 'VENUE'}[track]

        def track_has_midi(self, track):
            return track != 'audio'

        def project_info(self):
            return {'identity': 'project'}

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for MIDI view test')
        if root is not None:
            root.destroy()
        return
    try:
        view = MidiView(
            root, lambda unused_status, unused_report: None, ViewHost())
        expect(tuple(view.pattern_pane.track_combo['values']) == (),
               'MIDI view scanned item chunks before explicit Refresh')
        expect(view.pattern_pane.track_var.get() ==
               '(scan when MIDI tab opens)',
               'empty MIDI selector does not explain when it will scan')
        view.refresh_current()
        values = tuple(view.pattern_pane.track_combo['values'])
        expect(values == ('2: PART DRUMS', '3: VENUE'),
               'MIDI selector did not filter the audio-only track')
        buttons = view.pattern_pane.action_buttons
        expect(buttons['Replace All'].instate(['disabled']) and
               buttons['Fill Range'].instate(['disabled']) and
               buttons['Go Prev'].instate(['disabled']) and
               buttons['Go Next'].instate(['disabled']) and
               buttons['List Search'].instate(['disabled']),
               'Pattern-dependent actions should start disabled')
        view.pattern_state['search_notes'] = []
        view.pattern_pane.refresh_labels()
        expect(not buttons['Go Prev'].instate(['disabled']) and
               not buttons['Go Next'].instate(['disabled']) and
               not buttons['List Search'].instate(['disabled']) and
               buttons['Replace All'].instate(['disabled']) and
               buttons['Fill Range'].instate(['disabled']),
               'Search capture enabled the wrong Pattern actions')
        view.pattern_state['replace_notes'] = []
        view.pattern_pane.refresh_labels()
        expect(not buttons['Replace All'].instate(['disabled']) and
               not buttons['Fill Range'].instate(['disabled']),
               'Replace capture did not enable replace/fill actions')
    finally:
        root.destroy()


def main():
    tests = [
        test_window_codec_preserves_unrelated_notes_and_text,
        test_non_sustain_length_adjustment_and_noop_undo,
        test_sustain_gap_uses_note_buried_under_sustain,
        test_pattern_capture_replace_list_and_navigation,
        test_fill_range_tiles_complete_slots_only,
        test_pitch_ranges_match_rock_band_tracks,
        test_resize_refuses_unverified_source_extension,
        test_legacy_time_selection_and_cursor_adapter_shapes,
        test_legacy_track_midi_filter_uses_item_chunks,
        test_midi_view_filters_tracks_and_updates_pattern_button_states,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('MIDI Length/Pattern tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
