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
    designated_sprite_package, find_sprite_sheet, find_sprite_sheets,
    normalize_sprite_key, sprite_package_status,
)
from rock_band_general_helper_vkr.venue import CAMERA_EVENTS, POSTPROC_EVENTS
from rock_band_general_helper_vkr.venue_themes import LIGHTING_NAMES
from rock_band_general_helper_vkr.venue_tooltips import (
    DIRECTED_TIPS, LIGHTING_TIPS, POSTPROC_TIPS,
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


def test_responsive_label_wraps_to_available_container_width():
    try:
        import Tkinter as tk
        import ttk
    except ImportError:
        import tkinter as tk
        from tkinter import ttk
    from lib.tk_common import ResponsiveLabel

    root = tk.Tk()
    root.withdraw()
    container = ttk.Frame(root)
    label = ResponsiveLabel(
        container, text='A long body-copy label.', wraplength=700)
    try:
        event = type('ResizeEvent', (object,), {'width': 420})()
        label._container_resized(event)
        expect(int(str(label.cget('wraplength'))) == 396,
               'responsive label did not follow a narrow container')
        event.width = 900
        label._container_resized(event)
        expect(int(str(label.cget('wraplength'))) == 700,
               'responsive label exceeded its intended wide-screen limit')
    finally:
        root.destroy()


def test_event_description_tables_cover_every_described_manual_event():
    directed = set(name for name in CAMERA_EVENTS
                   if name.startswith('directed_'))
    expect(set(DIRECTED_TIPS) == directed,
           'directed tooltip coverage differs from the selectable events')
    expect(set(LIGHTING_TIPS) == set(LIGHTING_NAMES),
           'lighting tooltip coverage differs from the selectable events')
    expect(set(POSTPROC_TIPS) == set(POSTPROC_EVENTS),
           'post-process tooltip coverage differs from the selectable events')
    expect(all(DIRECTED_TIPS.values()) and all(LIGHTING_TIPS.values()) and
           all(POSTPROC_TIPS.values()), 'an event tooltip is empty')


def test_designated_package_is_fixed_after_first_lookup():
    root = tempfile.mkdtemp(prefix='venue-sprites-')
    try:
        camera = os.path.join(root, 'camera')
        small = os.path.join(root, 'camera small')
        os.makedirs(small)
        small_path = os.path.join(small, 'dcrowd_f24_spritesheet.jpg')
        with open(small_path, 'wb') as handle:
            handle.write(b'fixture')
        found, count = find_sprite_sheet(root, 'Camera', 'directed_crowd')
        expect(found == small_path and count == 24,
               'small spritesheet fallback was not found')

        large_path = os.path.join(camera, 'dcrowd_f66_spritesheet.jpg')
        os.makedirs(camera)
        with open(large_path, 'wb') as handle:
            handle.write(b'fixture')
        found, count = find_sprite_sheet(root, 'Camera', 'directed_crowd')
        expect(found == small_path and count == 24,
               'designated package changed during the script session')
    finally:
        shutil.rmtree(root)


def test_designated_package_does_not_mix_jpeg_and_gif_sources():
    root = tempfile.mkdtemp(prefix='venue-sprites-')
    try:
        camera = os.path.join(root, 'camera')
        camera_gif = os.path.join(root, 'camera gif')
        os.makedirs(camera)
        os.makedirs(camera_gif)
        jpeg_path = os.path.join(camera, 'coopallnear_f66_spritesheet.jpg')
        gif_path = os.path.join(
            camera_gif, 'coopallfar_f66_spritesheet.gif')
        for path in (jpeg_path, gif_path):
            with open(path, 'wb') as handle:
                handle.write(b'fixture')

        found = find_sprite_sheets(root, 'Camera', 'coop_all_far')
        expect(found == [],
               'missing JPEG sheet was silently borrowed from GIF package')
    finally:
        shutil.rmtree(root)


def test_empty_package_folders_do_not_count_as_installed():
    root = tempfile.mkdtemp(prefix='venue-sprites-')
    try:
        for folder in ('camera', 'lighting', 'postproc'):
            os.makedirs(os.path.join(root, folder))
            with open(os.path.join(root, folder, '.gitkeep'), 'wb') as handle:
                handle.write(b'')
        gif_folder = os.path.join(root, 'camera gif')
        os.makedirs(gif_folder)
        gif_path = os.path.join(
            gif_folder, 'coopallfar_f66_spritesheet.gif')
        with open(gif_path, 'wb') as handle:
            handle.write(b'fixture')

        package = designated_sprite_package(root)
        expect(package['key'] == 'large_gif',
               'empty JPEG placeholders were treated as an installed pack')
        expect(find_sprite_sheets(root, 'Camera', 'coop_all_far') ==
               [(gif_path, 66)],
               'recognized GIF sheet was not indexed from the installed pack')
    finally:
        shutil.rmtree(root)


def test_package_priority_is_independent_of_preview_size():
    root = tempfile.mkdtemp(prefix='venue-sprites-')
    try:
        for folder in ('camera', 'camera gif', 'camera small',
                       'camera small gif'):
            os.makedirs(os.path.join(root, folder))
        paths = []
        for folder, extension in (
                ('camera', 'jpg'), ('camera gif', 'gif'),
                ('camera small', 'jpg'), ('camera small gif', 'gif')):
            path = os.path.join(
                root, folder, 'coopallfar_f2_spritesheet.' + extension)
            with open(path, 'wb') as handle:
                handle.write(b'fixture')
            paths.append(path)
        small = find_sprite_sheets(
            root, 'Camera', 'coop_all_far', preferred_size=1)
        large = find_sprite_sheets(
            root, 'Camera', 'coop_all_far', preferred_size=2)
        package = designated_sprite_package(root)
        expect(package['key'] == 'large_jpeg',
               'highest-priority installed package was not designated')
        expect(sprite_package_status(root) ==
               'Sprite package: Large JPEG',
               'package status did not use the user-facing package name')
        expect(small == [(paths[0], 2)],
               '1x did not retain the designated large JPEG package')
        expect(large == [(paths[0], 2)],
               '2x changed the designated large JPEG package')
    finally:
        shutil.rmtree(root)


def test_tk_preview_scaling_has_exact_1x_and_2x_dimensions():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.venue_sprites import VenueSpritePlayer

    root = tk.Tk()
    root.withdraw()
    player = VenueSpritePlayer(
        root, os.path.join(root.tk.call('pwd'), 'missing-sprites'),
        'Camera', 'missing', '', preferred_size=1)
    try:
        normal = tk.PhotoImage(width=426, height=240)
        scaled = player._scale_tk_frame(normal)
        expect((scaled.width(), scaled.height()) == (213, 120),
               'normal sheet frame did not render at exact 1x size')
        player.preferred_size = 2
        small = tk.PhotoImage(width=213, height=120)
        scaled = player._scale_tk_frame(small)
        expect((scaled.width(), scaled.height()) == (426, 240),
               'small sheet frame did not render at exact 2x size')
        player.display_scale = 1.5
        normal = tk.PhotoImage(width=426, height=240)
        scaled = player._scale_tk_frame(normal)
        expect((scaled.width(), scaled.height()) == (639, 360),
               '2x frame did not account for 150-percent display scaling')
        player.preferred_size = 1
        player.display_scale = 1.0
        player._show_fallback(
            'Preview failed in Large JPEG\n'
            'JPEG previews require Pillow 6.2.2.')
        expect(int(str(player.image_label.cget('wraplength'))) == 185,
               '1x fallback did not wrap inside the preview card')
        expect(int(str(player.image_label.cget('width'))) == 0,
               'fallback retained a clipping-prone character width')
    finally:
        player.destroy()
        root.destroy()


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
        coop = view.rows['coop']
        coop['variable'].set(coop['events'][0].label)
        combo = coop['combo']
        view.tk.call('ttk::combobox::Post', str(combo))
        root.update_idletasks()
        record = coop['preview_record']
        listbox = record['listbox']
        expect(listbox is not None,
               'native ttk popdown list was not discovered')
        view.tk.call(listbox, 'activate', 3)
        view.preview._preview_popdown_active(record, listbox)
        expect(view.preview.current_event.raw_event == '[coop_all_near]',
               'active dropdown row did not update the inline preview')
        view.tk.call('ttk::combobox::Unpost', str(combo))

        view.preview.set_mode('window')
        view.preview._combo_enter(record)
        window = view.preview.popup
        directed_row = view.rows['directed']
        directed = directed_row['preview_record']
        view.preview._preview_candidate(directed, 1)
        expect(view.preview.popup is window,
               'click preview window was recreated for a candidate')
        expect(view.preview.player.raw_event == '[directed_all]',
               'hovered candidate did not replace the click preview')
        expect(view.preview.player.description ==
               DIRECTED_TIPS['directed_all'],
               'directed description did not follow the live preview')
        expect(not bool(
                   view.preview.player.description_label.cget('foreground')),
               'event description did not use the normal tooltip text color')
        expect(bool(view.preview.player.event_label.cget('foreground')),
               'raw event name did not retain its secondary text color')

        lighting_row = view.rows['lighting']
        lighting_row['variable'].set('Chorus')
        lighting = lighting_row['preview_record']
        view.preview._selection_changed(lighting)
        expect(view.preview.popup is window and
               view.preview.player.raw_event == '[lighting (chorus)]',
               'selected event did not update the persistent click preview')
        view.preview._combo_enter(record)
        view.preview._action_enter(
            lambda: view._selected_preview(lighting_row),
            lighting_row['add'])
        expect(view.preview.popup is window and
               view.preview.player.raw_event == '[lighting (chorus)]',
               'dropdown/Add hover did not reuse the shared click window')

        view.preview.set_mode('tooltip')
        directed_row['variable'].set(directed_row['events'][0].label)
        combo = directed_row['combo']
        view.tk.call('ttk::combobox::Post', str(combo))
        root.update()
        expect(view.preview.popup is not None and
               view.preview.popup_is_tooltip,
               'open-list hover mode did not create its tooltip window')
        view.tk.call('ttk::combobox::Unpost', str(combo))
        root.update()
        view.preview._action_pressed(
            lambda: view._selected_preview(coop), coop['add'])
        expect(view.preview.popup is not None and
               view.preview.popup_is_tooltip and
               view.preview.player.raw_event == '[coop_all_behind]',
               'B-mode Add button did not open its row tooltip')
    finally:
        view.destroy()
        root.destroy()


def test_empty_manual_selection_never_reuses_a_stale_tooltip():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_manual import VenueManualView

    root = tk.Tk()
    root.withdraw()
    view = VenueManualView(root, object())
    try:
        for key in ('coop', 'directed', 'lighting', 'postproc'):
            row = view.rows[key]
            expect(row['variable'].get() == '(select)',
                   '%s did not start with the empty selection' % key)
            expect(row['combo'].cget('values')[0] == '(select)',
                   '%s omitted the empty row from its values' % key)

        coop = view.rows['coop']
        coop_record = coop['preview_record']
        view.preview._combo_posted(coop_record)
        root.update()
        expect(view.preview.popup is None and
               view.preview.current_event is None,
               'an empty first opening displayed a preview')

        view.preview._preview_candidate(coop_record, 1)
        root.update()
        expect(view.preview.popup is not None and
               view.preview.current_event.raw_event == '[coop_all_behind]',
               'first valid candidate did not create the tooltip')

        view.preview._preview_candidate(coop_record, 0)
        expect(view.preview.popup is None and
               view.preview.current_event is None,
               'returning to (select) retained the previous tooltip')

        view.preview._finish_popdown(coop_record)
        coop['variable'].set(coop['events'][0].label)
        view.preview._selection_changed(coop_record)
        view.preview._combo_enter(coop_record)
        view.preview._cancel_hover()
        view.preview._show_closed_tooltip(coop_record)
        expect(view.preview.popup is not None,
               'selected event did not create a closed tooltip')

        directed = view.rows['directed']['preview_record']
        view.preview._combo_enter(directed)
        view.preview._cancel_hover()
        view.preview._show_closed_tooltip(directed)
        expect(view.preview.popup is None and
               view.preview.current_event is None,
               'unselected dropdown reused another row\'s event')
    finally:
        view.destroy()
        root.destroy()


def test_manual_controls_have_original_explanatory_tooltips():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_manual import VenueManualView

    root = tk.Tk()
    root.withdraw()
    view = VenueManualView(root, object())
    try:
        texts = [tooltip.text for tooltip in view.text_tooltips]
        for phrase in (
                'currently running', 'first [next]', 'manual lighting event',
                'Camera-cut spacing', '+/-20%', 'Custom camera-cut interval',
                'Move the edit cursor forward', 'Removes all [coop_*]'):
            expect(any(phrase in text for text in texts),
                   'missing Manual gen control tooltip: %s' % phrase)

        view.remove_type.set('Post proc')
        view._sync_states()
        expect('post-process [*.pp]' in view.remove_tooltip.text and
               view.remove_button_tooltip.text == view.remove_tooltip.text,
               'remove tooltip did not follow its selected event type')

        panel_tip = view.text_tooltips[0]
        panel_tip._show()
        root.update_idletasks()
        expect(panel_tip.panel and panel_tip.window is not None,
               'Venue control tooltip did not use panel styling')
        topmost = panel_tip.window.wm_attributes('-topmost')
        expect(str(topmost).lower() in ('1', 'true'),
               'Venue control tooltip was not kept above a topmost window')
        body = panel_tip.window.winfo_children()[0]
        expect(isinstance(body, tk.Frame) and body.cget('relief') == 'solid',
               'Venue control tooltip did not match preview panel framing')
        panel_tip._hide()
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
