"""Desktop tests for VENUE spritesheet lookup."""

from __future__ import print_function

import os
import shutil
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.venue_sprites import (
    find_sprite_sheet, normalize_sprite_key,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def test_sprite_key_aliases_match_upstream_names():
    expect(normalize_sprite_key('Camera', 'directed_crowd') == 'dcrowd',
           'directed camera alias differs')
    expect(normalize_sprite_key('Camera', 'coop_all_far') == 'coopallfar',
           'normal camera normalization differs')
    expect(normalize_sprite_key('Lighting', 'loop_cool') == 'loopcool',
           'lighting normalization differs')
    expect(normalize_sprite_key('PostProc', 'ProFilm_b.pp') == 'colormuted',
           'post-process alias or .pp stripping differs')


def test_lookup_checks_large_then_small_and_parses_frame_count():
    root = tempfile.mkdtemp(prefix='venue-sprites-')
    try:
        camera = os.path.join(root, 'camera')
        small = os.path.join(root, 'camera small')
        os.makedirs(camera)
        os.makedirs(small)
        small_path = os.path.join(small, 'dcrowd_f24_spritesheet.gif')
        with open(small_path, 'wb') as handle:
            handle.write(b'fixture')
        found, count = find_sprite_sheet(root, 'Camera', 'directed_crowd')
        expect(found == small_path and count == 24,
               'small spritesheet fallback was not found')

        large_path = os.path.join(camera, 'dcrowd_f66_spritesheet.jpg')
        with open(large_path, 'wb') as handle:
            handle.write(b'fixture')
        found, count = find_sprite_sheet(root, 'Camera', 'directed_crowd')
        expect(found == large_path and count == 66,
               'large spritesheet did not take priority')
    finally:
        shutil.rmtree(root)


def test_manual_preview_reuses_click_window_and_switches_candidate():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_manual import VenueManualView

    root = tk.Tk()
    root.withdraw()
    view = VenueManualView(root, object())
    try:
        combo = view.rows[0]['combo']
        view.tk.call('ttk::combobox::Post', str(combo))
        root.update_idletasks()
        record = view.rows[0]['preview_record']
        listbox = record['listbox']
        expect(listbox is not None,
               'native ttk popdown list was not discovered')
        view.tk.call(listbox, 'activate', 1)
        view.preview._preview_popdown_active(record, listbox)
        expect(view.preview.current_event.raw_event == '[coop_all_near]',
               'active dropdown row did not update the inline preview')
        view.tk.call('ttk::combobox::Unpost', str(combo))

        view.preview_mode.set('window')
        view._change_mode()
        view.preview._combo_enter(record)
        window = view.preview.popup
        directed = view.rows[1]['preview_record']
        view.preview._preview_candidate(directed, 0)
        expect(view.preview.popup is window,
               'click preview window was recreated for a candidate')
        expect(view.preview.player.raw_event == '[directed_crowd]',
               'hovered candidate did not replace the click preview')

        view.rows[2]['variable'].set('Chorus')
        lighting = view.rows[2]['preview_record']
        view.preview._selection_changed(lighting)
        expect(view.preview.popup is window and
               view.preview.player.raw_event == '[lighting (chorus)]',
               'selected event did not update the persistent click preview')
        view.preview._combo_enter(record)
        view.preview._action_enter(
            lambda: view._selected_event(view.rows[2]),
            view.rows[2]['add'])
        expect(view.preview.popup is window and
               view.preview.player.raw_event == '[lighting (chorus)]',
               'dropdown/Add hover did not reuse the shared click window')

        view.preview_mode.set('tooltip')
        view._change_mode()
        combo = view.rows[1]['combo']
        view.tk.call('ttk::combobox::Post', str(combo))
        root.update()
        expect(view.preview.popup is not None and
               view.preview.popup_is_tooltip,
               'open-list hover mode did not create its tooltip window')
        view.tk.call('ttk::combobox::Unpost', str(combo))
        root.update()
        view.preview._action_pressed(
            lambda: view._selected_event(view.rows[0]),
            view.rows[0]['add'])
        expect(view.preview.popup is not None and
               view.preview.popup_is_tooltip and
               view.preview.player.raw_event == '[coop_all_far]',
               'B-mode Add button did not open its row tooltip')
    finally:
        view.destroy()
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
