"""Desktop tests for Venue > Section gen."""

from __future__ import print_function

import os
import random
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.midi_chunk import parse_midi_chunk
from rock_band_general_helper_vkr.actions_venue_section import (
    VenueSectionGenerationError, generate_venue_section, load_venue_sections,
)
from rock_band_general_helper_vkr.venue_themes import parse_theme
from test_venue_themes import FakeHost, midi_chunk


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def _texts(host):
    return [(event.absolute_tick, event.meta_payload)
            for event in parse_midi_chunk(host.tracks[0][1]).text_events(1)]


def test_refresh_reads_and_merges_lettered_sections():
    host = FakeHost()
    sections, guards = load_venue_sections(host)
    expect(len(sections) == 2 and sections[0]['name'] == 'verse' and
           sections[0]['sub_count'] == 2 and sections[1]['name'] == 'chorus',
           'Section gen did not reuse recognized/merged EVENTS sections')
    expect(guards, 'EVENTS read guards were not returned')


def test_custom_generation_is_section_scoped_and_guarded():
    host = FakeHost()
    host.tracks[0][1] = midi_chunk([
        (0, 3, 'VENUE'),
        (1920, 1, '[lighting (intro)]'),
        (3360, 1, '[coop_all_far]'),
        (3600, 1, '[bonusfx_optional]'),
        (3840, 1, '[coop_all_near]'),
        (4800, 1, '[bonusfx]'),
        (7000, 1, '[lighting (chorus)]'),
        (8000, 1, '[coop_all_behind]'),
    ])
    sections, unused_guards = load_venue_sections(host)
    status, report = generate_venue_section(host, sections[0], {
        'lighting': 'manual_cool', 'postproc': 'bloom.pp',
        'keyframe_rate': 2, 'light_blendin': 1, 'pp_blendin': 1,
        'dircut': 'directed_all', 'bonusfx': True,
    }, {
        'camera_pacing': 3, 'camera_jitter': False,
        'keyframe_align': 0, 'keyframe_subdivision': 0,
    }, rng=random.Random(7))
    texts = _texts(host)
    messages = [message for unused_tick, message in texts]
    expect('Verse 1' in status and 'Undo: Generate VENUE section: Verse 1' in report,
           'custom Section gen result differs')
    expect('[lighting (manual_cool)]' in messages and '[bloom.pp]' in messages and
           '[directed_all]' in messages and '[bonusfx]' in messages and
           '[first]' in messages and '[next]' in messages,
           'custom Section gen omitted configured values')
    expect((3360, '[coop_all_far]') in texts and
           (7000, '[lighting (chorus)]') in texts and
           (8000, '[coop_all_behind]') in texts,
           'section replacement did not preserve boundary content')
    expect('[bonusfx_optional]' not in messages and
           (3840, '[coop_all_near]') not in texts,
           'section replacement retained content that should be cleared')
    expect(len(host.writes) == 1 and host.undo[-1] ==
           'Generate VENUE section: Verse 1',
           'Section gen did not use one guarded transaction')


def test_template_mode_resolves_only_selected_section_preset():
    host = FakeHost()
    sections, unused_guards = load_venue_sections(host)
    theme = parse_theme(
        '(camera_pacing slow) (section_presets '
        '(default (allowed_lightpresets loop_warm)) '
        '(verse1 (allowed_lightpresets manual_warm) '
        '(allowed_postprocs video_bw.pp) (keyframe_rate 3) '
        '(bonusfx_at_start)))', 'SectionTheme')
    status, unused_report = generate_venue_section(
        host, sections[0], {}, {
            'camera_pacing': 0, 'camera_jitter': False,
            'keyframe_align': 0, 'keyframe_subdivision': 0,
        }, theme, random.Random(2))
    messages = [message for unused_tick, message in _texts(host)]
    expect('Verse 1' in status and '[lighting (manual_warm)]' in messages and
           '[video_bw.pp]' in messages and '[bonusfx]' in messages,
           'Template mode did not resolve the selected section variant')
    expect('[lighting (loop_warm)]' not in messages,
           'Template mode used the default instead of verse1')


def test_generation_rejects_values_outside_original_ranges():
    host = FakeHost()
    sections, unused_guards = load_venue_sections(host)
    try:
        generate_venue_section(host, sections[0], {
            'keyframe_rate': 9, 'light_blendin': 0, 'pp_blendin': 0,
        }, {
            'camera_pacing': 3, 'camera_jitter': False,
            'keyframe_align': 0, 'keyframe_subdivision': 0,
        })
    except VenueSectionGenerationError as exc:
        expect('Keyframe rate must be from 1 to 8' in str(exc),
               'invalid range message differs')
    else:
        raise AssertionError('out-of-range section config was accepted')
    expect(not host.writes, 'invalid section config changed the project')


def test_section_ui_auto_refreshes_clamps_and_has_template_rows():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue import VenueView
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for Section gen UI test')
        if root is not None:
            root.destroy()
        return
    try:
        class Controller(object):
            host = FakeHost()
            def show_result(self, unused_status, unused_result):
                pass
        venue = VenueView(root, lambda unused_status, unused_result: None,
                          Controller.host)
        venue.notebook.select(venue.sections_view)
        venue._tab_changed()
        view = venue.sections_view
        expect(len(view.sections) == 2 and
               not view.generate_button.instate(['disabled']),
               'opening Section gen did not scan and enable sections')
        view.keyframe_rate.set(99)
        view.light_blendin.set(-4)
        view.pp_blendin.set(12)
        view._save_config()
        expect(view.keyframe_rate.get() == 8 and
               view.light_blendin.get() == 0 and
               view.pp_blendin.get() == 8,
               'typed spinner values were not clamped to original ranges')
        rows = [int(widget.grid_info()['row'])
                for widget in view.template_values.values()]
        expect(len(rows) == len(set(rows)),
               'Template values do not each have their own row')
    finally:
        root.destroy()


def main():
    tests = [
        test_refresh_reads_and_merges_lettered_sections,
        test_custom_generation_is_section_scoped_and_guarded,
        test_template_mode_resolves_only_selected_section_preset,
        test_generation_rejects_values_outside_original_ranges,
        test_section_ui_auto_refreshes_clamps_and_has_template_rows,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Venue Section gen tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
