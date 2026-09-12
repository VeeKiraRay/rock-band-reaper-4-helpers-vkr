"""Desktop tests for Venue > Themes gen."""

from __future__ import print_function

import base64
import os
import random
import shutil
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.midi_chunk import parse_midi_chunk
from rock_band_general_helper_vkr.actions_venue_themes import (
    build_theme_events, generate_venue_events)
from rock_band_general_helper_vkr.venue_themes import (
    build_lighting_pool, get_section_preset, get_theme_camera_interval,
    load_venue_themes, parse_theme, theme_display_label)
from rock_band_general_helper_vkr.venue import VENUE_VALID, read_named_track


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def _payload(meta_type, message):
    raw = b'\xff' + bytes(bytearray([meta_type])) + message.encode('ascii')
    value = base64.b64encode(raw)
    return value if isinstance(value, str) else value.decode('ascii')


def midi_chunk(events):
    rows = []
    previous = 0
    for tick, meta_type, message in sorted(events, key=lambda row: row[0]):
        rows.append('<X %d 0 0 0 %d %s\n  %s\n>\n' % (
            tick - previous, meta_type, message,
            _payload(meta_type, message)))
        previous = tick
    return ('<ITEM\n<SOURCE MIDI\nHASDATA 1 480 QN\n%s'
            'IGNTEMPO 0 120 4 4\n>\n>\n') % ''.join(rows)


class FakeHost(object):
    def __init__(self):
        self.tracks = [
            ['VENUE', midi_chunk([(0, 3, 'VENUE'), (960, 1, '[old]')]),
             0.0, 30.0, False],
            ['EVENTS', midi_chunk([
                (0, 3, 'EVENTS'), (1920, 1, '[music_start]'),
                (3840, 1, '[prc_verse_1a]'),
                (5760, 1, '[prc_verse_1b]'),
                (7680, 1, '[prc_chorus_1]'),
                (19200, 1, '[end]')]), 0.0, 30.0, False],
        ]
        for name in ('PART DRUMS', 'PART VOCALS', 'PART BASS',
                     'PART GUITAR', 'PART KEYS'):
            self.tracks.append([name, None, 0.0, 30.0, False])
        self.writes = []
        self.undo = []
        self.arranges = 0

    def track_count(self):
        return len(self.tracks)

    def get_track(self, index):
        return index

    def track_name(self, track, unused_index):
        return self.tracks[track][0]

    def track_muted(self, track):
        return self.tracks[track][4]

    def item_count(self, track):
        return 1 if self.tracks[track][1] is not None else 0

    def get_item(self, track, unused_index):
        return track

    def project_item_count(self):
        return sum(track[1] is not None for track in self.tracks)

    def get_project_item(self, index):
        return [position for position, track in enumerate(self.tracks)
                if track[1] is not None][index]

    def active_take(self, item):
        return 'take-%d' % item

    def take_start_offset(self, unused_take):
        return 0.0

    def take_play_rate(self, unused_take):
        return 1.0

    def item_position(self, item):
        return self.tracks[item][2]

    def item_length(self, item):
        return self.tracks[item][3]

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, qn):
        return float(qn) / 2.0

    def read_item_chunk(self, item):
        return self.tracks[item][1]

    def write_item_chunk(self, item, chunk):
        self.writes.append((item, chunk))
        self.tracks[item][1] = chunk

    def begin_undo(self):
        self.undo.append('begin')

    def end_undo(self, description):
        self.undo.append(description)

    def update_arrange(self):
        self.arranges += 1


THEME_TEXT = """
(camera_pacing fast)
(section_presets
  (default (allowed_lightpresets loop_cool loop_warm invalid)
           (allowed_postprocs ProFilm_a.pp invalid.pp))
  (verse1 (allowed_lightpresets manual_cool)
          (allowed_postprocs film_16mm.pp)
          (keyframe_rate 2) (lightpreset_blendin 1))
  (chorus1 (allowed_lightpresets chorus)
           (allowed_postprocs bloom.pp)
           (keyframe_rate 1) (dircut_at_start directed_all)
           (bonusfx_at_start))
)
"""


def test_theme_parser_and_helpers():
    theme = parse_theme(THEME_TEXT, 'ArenaRock')
    expect(theme['label'] == 'Arena Rock' and
           theme_display_label('SynthPop2') == 'Synth Pop2',
           'theme display labels differ')
    expect(theme['camera_pacing'] == 'fast', 'camera pacing was not parsed')
    default = get_section_preset(theme, 'unknown')
    expect(build_lighting_pool(default) == [
        '[lighting (loop_cool)]', '[lighting (loop_warm)]'],
        'invalid lighting names were not filtered')
    expect(get_section_preset(theme, 'verse', 3) is
           get_section_preset(theme, 'verse', 1),
           'numbered theme variants did not wrap')
    expect(get_theme_camera_interval('fast', 149) == 8 and
           get_theme_camera_interval('fast', 150) == 12,
           'high-tempo camera pacing differs')


def test_release_theme_folder_is_preserved_and_empty_folder_loads():
    expect(os.path.isfile(os.path.join(
        ROOT, 'resources', 'themes', '.gitkeep')),
        'empty release theme folder is not preserved')
    empty_dir = tempfile.mkdtemp(prefix='rb4-empty-themes-')
    try:
        themes, errors = load_venue_themes(empty_dir)
        expect(not themes and not errors,
               'an empty user theme folder did not load cleanly')
    finally:
        shutil.rmtree(empty_dir)


def test_pure_generation_uses_sections_and_bookends():
    host = FakeHost()
    context = read_named_track(host, 'VENUE')[1][0]
    rows, stats, guards = build_theme_events(
        host, context, parse_theme(THEME_TEXT, 'TestTheme'), {
            'camera_pacing': 0, 'camera_jitter': False,
            'keyframe_align': 0, 'keyframe_subdivision': 0,
        }, random.Random(4))
    messages = [row['payload'] for row in rows]
    expect('[coop_all_far]' in messages and
           '[lighting (intro)]' in messages and
           '[lighting (blackout_spot)]' in messages,
           'required theme bookends were not generated')
    expect('[lighting (manual_cool)]' in messages and
           '[lighting (chorus)]' in messages and '[first]' in messages,
           'section lighting/keyframes were not generated')
    expect(messages.count('[lighting (intro)]') >= 2,
           'outgoing lighting was not duplicated into a blend zone')
    expect('[directed_all]' in messages and '[bonusfx]' in messages,
           'theme section controls were not generated')
    expect(stats['companions'] > 0,
           'three-way guitar/bass/keys camera companions were not generated')
    expect(stats['matched'] == 2 and guards,
           'lettered section merging or read guards differ')


def test_theme_fixture_generates_valid_vocabulary():
    themes = [parse_theme(THEME_TEXT, 'FixtureTheme')]
    for theme in themes:
        host = FakeHost()
        context = read_named_track(host, 'VENUE')[1][0]
        rows, unused_stats, unused_guards = build_theme_events(
            host, context, theme, {
                'camera_pacing': 0, 'camera_jitter': False,
                'keyframe_align': 0, 'keyframe_subdivision': 0,
            }, random.Random(11))
        invalid = [row['payload'] for row in rows
                   if row['payload'] not in VENUE_VALID]
        expect(not invalid, '%s generated invalid events: %r' %
               (theme['stem'], invalid))


def test_default_manual_lighting_gets_keyframes_without_sections():
    theme = parse_theme(
        '(section_presets (default '
        '(allowed_lightpresets manual_warm manual_cool)))',
        'ManualDefault')
    host = FakeHost()
    host.tracks[1][1] = midi_chunk([
        (0, 3, 'EVENTS'), (1920, 1, '[music_start]'),
        (19200, 1, '[end]')])
    context = read_named_track(host, 'VENUE')[1][0]
    rows, stats, unused_guards = build_theme_events(
        host, context, theme, {
            'camera_pacing': 0, 'camera_jitter': False,
            'keyframe_align': 0, 'keyframe_subdivision': 0,
        }, random.Random(3))
    expect(stats['matched'] == 0 and stats['control'] > 0 and
           '[first]' in [row['payload'] for row in rows],
           'default manual lighting omitted its keyframe sequence')


def test_guarded_generation_replaces_text_only():
    host = FakeHost()
    theme = parse_theme(THEME_TEXT, 'TestTheme')
    status, report = generate_venue_events(host, theme, {
        'camera_pacing': 3, 'camera_jitter': False,
        'keyframe_align': 0, 'keyframe_subdivision': 0,
    }, random.Random(7))
    parsed = parse_midi_chunk(host.tracks[0][1])
    texts = [event.meta_payload for event in parsed.text_events(1)]
    names = [event.meta_payload for event in parsed.text_events(3)]
    expect('Generated' in status and
           'Undo: Generate VENUE events from theme' in report,
           'generation did not return a success result')
    expect('[old]' not in texts and '[coop_all_far]' in texts,
           'old VENUE text was not replaced by generated events')
    expect('<X 0 0 0 0 1 "[lighting (intro)]"\n' in host.tracks[0][1],
           'spaced event payload did not use REAPER quoted summary syntax')
    expect(names == ['VENUE'], 'track-name meta event was not preserved')
    expect(len(host.writes) == 1 and host.undo == [
        'begin', 'Generate VENUE events from theme'],
        'generation did not use one verified write and Undo point')


def test_bulk_text_codec_preserves_notes_and_other_meta_types():
    chunk = midi_chunk([(0, 3, 'VENUE'), (0, 1, '[old]')])
    chunk = chunk.replace(
        'IGNTEMPO 0 120 4 4\n',
        'E 480 90 55 64\nE 120 80 55 00\nIGNTEMPO 0 120 4 4\n')
    parsed = parse_midi_chunk(chunk)
    changed = parsed.with_replaced_meta_events(0, 2000, [
        {'tick': 240, 'payload': '[coop_all_far]'},
        {'tick': 720, 'payload': '[lighting (intro)]'},
    ])
    reparsed = parse_midi_chunk(changed)
    expect([(note.pitch, note.start_tick, note.end_tick)
            for note in reparsed.notes()] == [(85, 480, 600)],
           'bulk text replacement changed an unrelated MIDI note')
    expect([event.meta_payload for event in reparsed.text_events(3)] ==
           ['VENUE'], 'bulk text replacement removed the track-name event')
    expect([event.meta_payload for event in reparsed.text_events(1)] ==
           ['[coop_all_far]', '[lighting (intro)]'],
           'bulk text replacement produced the wrong FF 01 events')


def test_themes_ui_constructs():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_themes import VenueThemesView
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for Themes UI test')
        if root is not None:
            root.destroy()
        return
    try:
        empty_dir = tempfile.mkdtemp(prefix='rb4-empty-themes-ui-')
        class Controller(object):
            host = FakeHost()
            def show_result(self, unused_status, unused_result):
                pass
        try:
            themes_view = VenueThemesView(root, Controller(), empty_dir)
            expect(not themes_view.themes and
                   themes_view.generate_button.instate(['disabled']),
                   'empty Themes gen did not disable generation')
            label_texts = [child.cget('text') for child in
                           themes_view.winfo_children()
                           if hasattr(child, 'cget')]
            expect(any('No .rbtheme files were found' in text
                       for text in label_texts),
                   'empty Themes gen did not show its alert')
            expect(themes_view.camera_jitter.get(),
                   'camera jitter is not enabled by default')
        finally:
            shutil.rmtree(empty_dir)
    finally:
        root.destroy()


def main():
    tests = [
        test_theme_parser_and_helpers,
        test_release_theme_folder_is_preserved_and_empty_folder_loads,
        test_pure_generation_uses_sections_and_bookends,
        test_theme_fixture_generates_valid_vocabulary,
        test_default_manual_lighting_gets_keyframes_without_sections,
        test_guarded_generation_replaces_text_only,
        test_bulk_text_codec_preserves_notes_and_other_meta_types,
        test_themes_ui_constructs,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Venue Themes tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
