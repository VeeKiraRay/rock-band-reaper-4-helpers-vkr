"""Desktop tests for the shared VENUE timeline preview."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.venue_preview import (
    bare_sprite_name, combo_muted, get_venue_events_for_preview,
    preview_signature, resolve_group, surrounding_groups, transition_text,
)
import rock_band_general_helper_vkr.venue_preview as preview_module
from lib.reaper420 import Reaper420Host


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def event(ppq, seconds, message, **extra):
    value = {'ppq': ppq, 't': seconds, 'msg': message, 'meta_type': 1}
    value.update(extra)
    return value


def test_surrounding_groups_keep_stacked_camera_spots_together():
    events = [
        event(0, 0.0, '[coop_all_far]'),
        event(480, 1.0, '[coop_bg_near]'),
        event(480, 1.0, '[coop_bk_near]'),
        event(960, 2.0, '[directed_all]'),
    ]
    previous, current, following = surrounding_groups(events, 1.5)
    expect([row['ppq'] for row in previous] == [0],
           'previous camera group differs')
    expect([row['msg'] for row in current] ==
           ['[coop_bg_near]', '[coop_bk_near]'],
           'stacked camera spot was split')
    expect([row['ppq'] for row in following] == [960],
           'next camera group differs')


def test_preview_reader_categorizes_and_collapses_blend_anchors():
    rows = [
        event(0, 0.0, 'VENUE', meta_type=3),
        event(0, 0.0, '[coop_all_far]'),
        event(480, 1.0, '[lighting (verse)]'),
        event(720, 1.5, '[lighting (verse)]'),
        event(960, 2.0, '[lighting (chorus)]'),
        event(0, 0.0, '[ProFilm_a.pp]'),
        event(480, 1.0, '[bonusfx]'),
    ]
    original = preview_module.read_named_track
    preview_module.read_named_track = lambda unused_host, unused_name: (
        object(), (), rows)
    try:
        data = get_venue_events_for_preview(object())
    finally:
        preview_module.read_named_track = original
    expect([row['msg'] for row in data['camera']] == ['[coop_all_far]'],
           'camera categorization differs')
    expect(len(data['lighting']) == 2 and
           data['lighting'][0]['blend_out_ppq'] == 720,
           'lighting blend anchor was not collapsed')
    expect([row['msg'] for row in data['postproc']] == ['[ProFilm_a.pp]'],
           'post-process categorization differs')


def test_position_before_first_event_has_only_a_next_group():
    events = [event(480, 1.0, '[lighting (verse)]')]
    previous, current, following = surrounding_groups(events, 0.5)
    expect(previous is None and current is None,
           'an event before the playhead was invented')
    expect(following[0]['msg'] == '[lighting (verse)]',
           'first future event was not returned as Next')


def test_camera_stack_uses_selected_lineup_and_priority():
    group = [
        event(480, 1.0, '[coop_bg_near]'),
        event(480, 1.0, '[coop_bk_near]'),
    ]
    chosen, filtered = resolve_group(group, combo_muted(0))
    expect(chosen['msg'] == '[coop_bg_near]' and not filtered,
           'Bass + Guitar did not select its matching stacked shot')
    chosen, filtered = resolve_group(
        [event(480, 1.0, '[coop_bk_near]')], combo_muted(0))
    expect(chosen['msg'] == '[coop_bk_near]' and filtered,
           'unplayable authored event was not retained and marked filtered')


def test_blend_transition_changes_only_inside_anchor_window():
    lighting = event(
        0, 0.0, '[lighting (verse)]', next_t=4.0, blend_out_t=3.0)
    expect(transition_text(lighting, 2.0) == 'Blends into next',
           'future blend was not described')
    expect(transition_text(lighting, 3.5) == 'Blending now',
           'active blend was not described')
    hard_cut = event(480, 4.0, '[lighting (chorus)]', next_t=8.0)
    expect(transition_text(hard_cut, 5.0) == 'Hard cut to next',
           'hard cut was not described')


def test_sprite_names_match_all_three_categories():
    expect(bare_sprite_name(
        event(0, 0, '[coop_all_far]'), 'Camera') == 'coop_all_far',
        'camera wrapper was not removed')
    expect(bare_sprite_name(
        event(0, 0, '[lighting (manual_warm)]'),
        'Lighting') == 'manual_warm', 'lighting wrapper was not removed')
    expect(bare_sprite_name(
        event(0, 0, '[ProFilm_a.pp]'), 'PostProc') == 'ProFilm_a.pp',
        'post-process wrapper was not removed')


def test_signature_changes_when_a_blend_becomes_active():
    data = {
        'camera': [],
        'lighting': [event(
            0, 0.0, '[lighting (verse)]', next_t=4.0, blend_out_t=3.0)],
        'postproc': [],
    }
    expect(preview_signature(data, 2.0, 0, False) !=
           preview_signature(data, 3.5, 0, False),
           'blend boundary did not trigger a preview redraw')


def test_host_preview_position_follows_transport_state():
    class FakeApi(object):
        def __init__(self, playing):
            self.playing = playing

        def RPR_GetPlayState(self):
            return 1 if self.playing else 0

        def RPR_GetPlayPosition(self):
            return 12.5

        def RPR_GetCursorPosition(self):
            return 3.25

    api = FakeApi(True)
    host = Reaper420Host(api)
    expect(host.preview_position() == 12.5,
           'playing Preview did not follow the transport')
    api.playing = False
    expect(host.preview_position() == 3.25,
           'stopped Preview did not follow the edit cursor')


def test_shared_tk_view_constructs_for_either_host_shell():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_preview_tab import (
        VenueTimelinePreviewView,
    )
    from rock_band_general_helper_vkr.venue_sprites import preview_dimensions

    class FakeHost(object):
        def cursor_position(self):
            return 0.0

        def measure_at(self, unused_seconds):
            return 1

        def track_count(self):
            return 0

    root = tk.Tk()
    root.withdraw()
    view = VenueTimelinePreviewView(root, host=FakeHost())
    try:
        view.sprite_root = os.path.join(ROOT, 'missing-preview-fixtures')
        view.data = {
            'camera': [event(0, 0.0, '[coop_all_far]')],
            'lighting': [], 'postproc': [],
        }
        view.timelines = dict(
            (key, preview_module.build_grouped_timeline(view.data[key]))
            for key in ('camera', 'lighting', 'postproc'))
        view._update_display(0.0)
        headings = [child.cget('text') for child in view.body.winfo_children()
                    if child.winfo_class() == 'TLabelframe']
        expect(headings == ['Camera', 'Lighting', 'Post-Process'],
               'shared Preview view did not construct its category rows')
        expect(view.poll_var.get() == 100,
               'playback refresh did not default to 100 ms')
        expect(view.show_settings_var.get() and
               set(view._enabled_categories()) ==
               set(('camera', 'lighting', 'postproc')),
               'Preview settings did not start expanded with all categories')
        tooltip_texts = [tooltip.text for tooltip in view.control_tooltips]
        expect(any('213 x 120 logical pixels' in text
                   for text in tooltip_texts) and
               any('426 x 240 logical pixels' in text
                   for text in tooltip_texts),
               'Preview size tooltips omitted their display dimensions')
        expected_width = preview_dimensions(1, view.display_scale)[0]
        expect(int(view.cards['camera'][0]['media'].cget('width')) ==
               expected_width,
               '1x card did not reserve its DPI-aware width')
        view.surrounding_var.set(True)
        view._update_display(0.0)
        groups = [child for child in view.body.winfo_children()
                  if child.winfo_class() == 'TLabelframe']
        expect(all(int(group.grid_columnconfigure(0)['weight']) == 0
                   for group in groups),
               'surrounding columns expanded into spare window width')
        view.size_var.set(2)
        view._update_display(0.0)
        expected_width = preview_dimensions(2, view.display_scale)[0]
        expect(int(view.cards['camera'][0]['media'].cget('width')) ==
               expected_width,
               '2x card did not reserve its DPI-aware width')
        camera_player = view.cards['camera'][1]['player']
        view.show_settings_var.set(False)
        view._toggle_settings()
        expect(not view.settings_frame.winfo_manager() and
               view.cards['camera'][1]['player'] is camera_player,
               'hiding settings rebuilt or restarted the preview')
        view.show_settings_var.set(True)
        view._toggle_settings()
        expect(bool(view.settings_frame.winfo_manager()),
               'settings block did not expand again')
        view.category_vars['lighting'].set(False)
        view.category_vars['postproc'].set(False)
        view._settings_changed()
        expect(set(view.cards) == set(('camera',)),
               'disabled categories retained active preview cards')
        view.category_vars['camera'].set(False)
        view._category_changed('camera')
        expect(view.category_vars['camera'].get(),
               'Preview allowed every category to be disabled')
    finally:
        view.destroy()
        root.destroy()


def test_detached_preview_reuses_root_and_cleans_up():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    import rock_band_general_helper_vkr.ui_venue_preview_tab as ui_module

    class FakeHost(object):
        def cursor_position(self):
            return 0.0

        def play_state(self):
            return 0

        def measure_at(self, unused_seconds):
            return 1

        def track_count(self):
            return 0

    root = tk.Tk()
    root.withdraw()
    closed = []
    window = None
    view = None
    try:
        expect(ui_module.existing_tk_root() is root,
               'live Tk root was not discovered')
        window, view = ui_module.open_venue_preview_window(
            root, host=FakeHost(), on_close=lambda: closed.append(True))
        window.withdraw()
        expect(isinstance(window, tk.Toplevel),
               'detached Preview created another Tk root')
        expect(window.tk is root.tk,
               'detached Preview did not reuse the root Tcl interpreter')
        expect(view.active and ui_module._OPEN_PREVIEW_WINDOWS,
               'detached Preview was not retained after opening')
        players_row = ui_module._OPEN_PREVIEW_WINDOWS[-1]['players_row']
        expect(players_row.active,
               'detached Preview did not start its Active players row')
        window._venue_preview_close()
        root.update_idletasks()
        expect(not view.active and not players_row.active and closed == [True],
               'detached Preview did not run its close lifecycle once')
        expect(not ui_module._OPEN_PREVIEW_WINDOWS,
               'closed detached Preview remained strongly referenced')
        window = None
    finally:
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass
        if view is not None:
            view.stop()
        root.destroy()


def test_action_launchers_reject_a_second_persistent_tool():
    try:
        import Tkinter as tk
        import tkMessageBox as messagebox
    except ImportError:
        import tkinter as tk
        from tkinter import messagebox
    from standalone import rock_band_preview_vkr as preview_launcher

    expect(os.path.normcase(preview_launcher._project_root()) ==
           os.path.normcase(ROOT),
           'moved standalone launcher did not resolve the repository root')

    launcher_path = os.path.join(ROOT, 'rock_band_general_helper_vkr.py')
    try:
        from importlib import util as importlib_util
        spec = importlib_util.spec_from_file_location(
            'rock_band_general_helper_launcher_test', launcher_path)
        general_launcher = importlib_util.module_from_spec(spec)
        spec.loader.exec_module(general_launcher)
    except ImportError:
        import imp
        general_launcher = imp.load_source(
            'rock_band_general_helper_launcher_test', launcher_path)
    root = tk.Tk()
    root.withdraw()
    warnings = []
    original_warning = messagebox.showwarning
    messagebox.showwarning = lambda title, message, **unused_options: (
        warnings.append((title, message)))
    try:
        preview_launcher.main()
        general_launcher.main()
        expect(len(warnings) == 2,
               'concurrent Action List launch was not rejected')
        expect(all('cannot safely run two persistent Python actions' in row[1]
                   for row in warnings),
               'concurrent-action warning did not explain the host limit')
        expect(tk._default_root is root and root.winfo_exists(),
               'launcher replaced or destroyed the running Tk root')
    finally:
        messagebox.showwarning = original_warning
        root.destroy()


def test_camera_change_preserves_other_category_players():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_preview_tab import (
        VenueTimelinePreviewView,
    )

    class FakeHost(object):
        def cursor_position(self):
            return 0.0

        def measure_at(self, unused_seconds):
            return 1

    root = tk.Tk()
    root.withdraw()
    view = VenueTimelinePreviewView(root, host=FakeHost())
    try:
        view.sprite_root = os.path.join(ROOT, 'missing-preview-fixtures')
        view.data = {
            'camera': [event(0, 0.0, '[coop_all_far]'),
                       event(480, 1.0, '[coop_all_near]')],
            'lighting': [event(0, 0.0, '[lighting (verse)]')],
            'postproc': [event(0, 0.0, '[ProFilm_a.pp]')],
        }
        view.timelines = dict(
            (key, preview_module.build_grouped_timeline(view.data[key]))
            for key in ('camera', 'lighting', 'postproc'))
        view._update_display(0.5)
        camera = view.cards['camera'][0]['player']
        lighting = view.cards['lighting'][0]['player']
        postproc = view.cards['postproc'][0]['player']
        view._update_display(1.1)
        expect(view.cards['camera'][0]['player'] is camera and
               camera.bare_name == 'coop_all_near',
               'changed camera card did not reuse its player widget')
        expect(view.cards['lighting'][0]['player'] is lighting,
               'camera change restarted the lighting player')
        expect(view.cards['postproc'][0]['player'] is postproc,
               'camera change restarted the post-process player')
    finally:
        view.destroy()
        root.destroy()


def test_transition_change_updates_label_without_restarting_sprite():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_preview_tab import (
        VenueTimelinePreviewView,
    )

    class FakeHost(object):
        def cursor_position(self):
            return 0.0

        def measure_at(self, unused_seconds):
            return 1

    root = tk.Tk()
    root.withdraw()
    view = VenueTimelinePreviewView(root, host=FakeHost())
    try:
        view.sprite_root = os.path.join(ROOT, 'missing-preview-fixtures')
        lighting = event(
            0, 0.0, '[lighting (verse)]', next_t=4.0, blend_out_t=3.0)
        view.data = {'camera': [], 'lighting': [lighting], 'postproc': []}
        view.timelines = dict(
            (key, preview_module.build_grouped_timeline(view.data[key]))
            for key in ('camera', 'lighting', 'postproc'))
        view._update_display(2.0)
        player = view.cards['lighting'][0]['player']
        view._update_display(3.5)
        card = view.cards['lighting'][0]
        expect(card['player'] is player,
               'blend label change restarted the lighting sprite')
        expect(card['transition_label'].cget('text') == 'Blending now',
               'blend label did not update independently')
    finally:
        view.destroy()
        root.destroy()


def test_automatic_midi_refresh_waits_until_playback_stops():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue_preview_tab import (
        VenueTimelinePreviewView,
    )

    class FakeHost(object):
        def __init__(self):
            self.running = True

        def play_state(self):
            return 1 if self.running else 0

        def play_position(self):
            return 4.0

        def cursor_position(self):
            return 5.0

    root = tk.Tk()
    root.withdraw()
    host = FakeHost()
    view = VenueTimelinePreviewView(root, host=host)
    calls = []
    try:
        view.active = True
        view.last_read_time = 0.0
        view.last_transport_running = True
        view.refresh_now = lambda: calls.append('refresh')
        view._update_display = lambda unused_position=None: calls.append(
            'position')
        view._poll()
        expect(calls == ['position'],
               'automatic MIDI refresh ran during playback')
        expect(view.poll_var.get() == 100,
               'playback polling did not retain the 100 ms default')
        if view.after_id is not None:
            view.after_cancel(view.after_id)
            view.after_id = None
        calls[:] = []
        host.running = False
        view._poll()
        expect(calls == ['refresh'],
               'stopping playback did not trigger one MIDI refresh')
    finally:
        view.stop()
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
