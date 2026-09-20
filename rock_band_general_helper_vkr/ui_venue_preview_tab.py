"""Reusable Tk Venue Preview view for embedded and standalone hosts.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import time

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.reaper420 import Reaper420Host
from lib.tk_common import (
    AutoVerticalScrolledFrame, PALETTE, ResponsiveLabel, Tooltip,
    apply_window_branding,
)

from .actions_difficulty_shared import format_time
from .actions_venue_themes import _muted_instruments
from .ui_venue_players import VenueActivePlayersRow
from .venue_preview import (
    FALLBACK_NOTE, PLAYER_COMBOS, VenueReadError, bare_sprite_name,
    build_grouped_timeline, combo_muted, get_venue_events_for_preview,
    resolve_group, surrounding_from_timeline, transition_text,
)
from .venue_sprites import (
    VenueSpritePlayer, default_sprite_root, designated_sprite_package,
    preview_dimensions, sprite_package_status, tk_display_scale,
)


STOPPED_POLL_MS = 250
AUTO_REFRESH_SECONDS = 5.0
SLOW_READ_SECONDS = 0.15
PLAYBACK_POLL_OPTIONS = (50, 100, 200, 500)

_CATEGORIES = (
    ('Camera', 'camera', 'Camera'),
    ('Lighting', 'lighting', 'Lighting'),
    ('Post-Process', 'postproc', 'PostProc'),
)

# REAPER keeps imported modules alive after a ReaScript action returns, while
# local variables from that action are not a dependable lifetime boundary.
# Keep detached windows and their views strongly referenced here until Tk
# reports that the window has actually been destroyed.
_OPEN_PREVIEW_WINDOWS = []


class VenueTimelinePreviewView(ttk.Frame):
    """Read-only VENUE timeline preview shared by both application shells."""

    def __init__(self, parent, host=None, allow_detach=False):
        ttk.Frame.__init__(self, parent)
        self.host = host or Reaper420Host()
        self.sprite_root = default_sprite_root()
        self.display_scale = tk_display_scale(self)
        self.data = None
        self.timelines = {}
        self.last_read_time = 0.0
        self.after_id = None
        self.active = False
        self.players = []
        self.actual_muted = {}
        self.cards = {}
        self.layout_surrounding = None
        self.last_transport_running = None
        self.warning_label = None
        self.fallback_label = None
        self.control_tooltips = []

        self.combo_var = tk.IntVar(); self.combo_var.set(0)
        self.size_var = tk.IntVar(); self.size_var.set(1)
        self.animate_var = tk.BooleanVar(); self.animate_var.set(True)
        self.surrounding_var = tk.BooleanVar(); self.surrounding_var.set(False)
        self.poll_var = tk.IntVar(); self.poll_var.set(100)
        self.show_settings_var = tk.BooleanVar(); self.show_settings_var.set(True)
        self.category_vars = {}
        for category in ('camera', 'lighting', 'postproc'):
            variable = tk.BooleanVar(); variable.set(True)
            self.category_vars[category] = variable
        self.status_var = tk.StringVar(); self.status_var.set('Open Preview to read VENUE.')

        controls = ttk.Frame(self, padding=(12, 12, 12, 6))
        controls.pack(fill=tk.X)
        settings_header = ttk.Frame(controls)
        settings_header.pack(fill=tk.X)
        ttk.Checkbutton(
            settings_header, text='Show settings',
            variable=self.show_settings_var,
            command=self._toggle_settings).pack(side=tk.LEFT)
        if allow_detach:
            ttk.Button(
                settings_header, text='Open separate window',
                command=self._open_detached).pack(side=tk.RIGHT)
        self.detached_window = None
        self.detached_view = None
        self.settings_frame = ttk.Frame(controls)
        self.settings_frame.pack(fill=tk.X, pady=(5, 0))
        self._radio_row(
            self.settings_frame, 0, 'Players', self.combo_var,
            tuple((index, value[0]) for index, value in enumerate(PLAYER_COMBOS)),
            'Choose which two of Bass, Guitar, and Keys are present in the band. '
            'Stacked camera shots are resolved with the game camera priority.')
        self._radio_row(
            self.settings_frame, 1, 'Preview size', self.size_var,
            ((1, '1x'), (2, '2x')),
            {
                1: ('1x displays each preview at 213 x 120 logical pixels. '
                    'Monitor DPI scaling is applied automatically. The source '
                    'may come from either the normal or small spritesheet '
                    'folder, depending on what is installed.'),
                2: ('2x displays each preview at 426 x 240 logical pixels. '
                    'Monitor DPI scaling is applied automatically. The source '
                    'may come from either the normal or small spritesheet '
                    'folder, depending on what is installed.'),
            })
        self._radio_row(
            self.settings_frame, 2, 'Sprites', self.animate_var,
            ((True, 'Animated'), (False, 'Still')),
            'Animate every available sprite frame, or show the middle frame only.')
        self._radio_row(
            self.settings_frame, 3, 'Show', self.surrounding_var,
            ((False, 'Current only'), (True, 'Surrounding events')),
            'Show only the state at the playhead, or the previous, current, and '
            'next event positions for each category.')
        self._category_row(self.settings_frame, 4)
        self._radio_row(
            self.settings_frame, 5, 'Playback refresh', self.poll_var,
            tuple((value, '%d ms' % value)
                  for value in PLAYBACK_POLL_OPTIONS),
            'How often Preview checks the REAPER play position. Shorter '
            'intervals track rapid cuts more closely but use more CPU.')
        self.settings_frame.columnconfigure(1, weight=1)

        self.status_label = ResponsiveLabel(
            controls, textvariable=self.status_var,
            foreground=PALETTE['muted'],
            justify=tk.LEFT, wraplength=680)
        self.status_label.pack(fill=tk.X, pady=(7, 0))

        self.body = ttk.Frame(self, padding=(12, 4, 12, 12))
        self.body.pack(fill=tk.X)

    def _radio_row(self, parent, row, label, variable, choices, tip):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky='w', padx=(0, 14), pady=2)
        group = ttk.Frame(parent)
        group.grid(row=row, column=1, sticky='w', pady=2)
        for value, text in choices:
            button = ttk.Radiobutton(
                group, text=text, variable=variable, value=value,
                command=self._settings_changed)
            button.pack(side=tk.LEFT, padx=(0, 14))
            text = tip.get(value, '') if isinstance(tip, dict) else tip
            self.control_tooltips.append(Tooltip(button, text))

    def _category_row(self, parent, row):
        ttk.Label(parent, text='Categories').grid(
            row=row, column=0, sticky='w', padx=(0, 14), pady=2)
        group = ttk.Frame(parent)
        group.grid(row=row, column=1, sticky='w', pady=2)
        for key, label in (
                ('camera', 'Camera'), ('lighting', 'Lighting'),
                ('postproc', 'Post-process')):
            ttk.Checkbutton(
                group, text=label, variable=self.category_vars[key],
                command=lambda value=key: self._category_changed(value)
            ).pack(side=tk.LEFT, padx=(0, 14))

    def _toggle_settings(self):
        if self.show_settings_var.get():
            if not self.settings_frame.winfo_manager():
                self.settings_frame.pack(
                    fill=tk.X, pady=(5, 0), before=self.status_label)
        else:
            self.settings_frame.pack_forget()

    def _open_detached(self):
        if self.detached_window is not None:
            try:
                if self.detached_window.winfo_exists():
                    self.detached_window.deiconify()
                    self.detached_window.lift()
                    return
            except tk.TclError:
                pass
        window, view = open_venue_preview_window(
            self.winfo_toplevel(), host=self.host,
            on_close=self._detached_closed)
        self.detached_window = window
        self.detached_view = view

    def _detached_closed(self):
        self.detached_window = None
        self.detached_view = None

    def _category_changed(self, changed):
        if not any(variable.get() for variable in self.category_vars.values()):
            self.category_vars[changed].set(True)
        self._settings_changed()

    def _enabled_categories(self):
        return tuple(key for unused_label, key, unused_sprite in _CATEGORIES
                     if self.category_vars[key].get())

    def start(self):
        if self.active:
            return
        self.active = True
        if self.data is None:
            self.refresh_now()
        else:
            for player in self.players:
                player.start()
            self._update_display()
        self._schedule_poll()

    def stop(self):
        self.active = False
        if self.after_id is not None:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
        for player in self.players:
            player.stop()

    def refresh_now(self):
        started = time.time()
        try:
            data = get_venue_events_for_preview(self.host)
        except VenueReadError as exc:
            self.data = None
            self.timelines = {}
            self._clear_body(str(exc))
            self.status_var.set(str(exc))
            self.last_read_time = time.time()
            return
        except Exception as exc:
            self.data = None
            self.timelines = {}
            message = 'Preview could not safely read VENUE: %s' % exc
            self._clear_body(message)
            self.status_var.set(message)
            self.last_read_time = time.time()
            return

        elapsed = time.time() - started
        self.data = data
        self.timelines = dict(
            (key, build_grouped_timeline(data.get(key, ())))
            for key in ('camera', 'lighting', 'postproc'))
        try:
            self.actual_muted = _muted_instruments(self.host)
        except Exception:
            self.actual_muted = {}
        self.last_read_time = time.time()
        if elapsed >= SLOW_READ_SECONDS:
            self.status_var.set(
                'Preview updated in %.0f ms. Automatic VENUE reads run only '
                'while transport is stopped.' % (elapsed * 1000.0))
        else:
            self.status_var.set(self._read_summary(data))
        running, playhead = self._transport_snapshot()
        self.last_transport_running = running
        self._update_display(playhead)

    def _read_summary(self, data):
        count = sum(len(data.get(key, ())) for key in
                    ('camera', 'lighting', 'postproc'))
        suffix = '' if count == 1 else 's'
        if not self._sprites_found():
            return ('Read %d preview event%s. %s Event names remain '
                    'available.' % (
                        count, suffix, sprite_package_status(self.sprite_root)))
        return 'Read %d preview event%s. %s' % (
            count, suffix, sprite_package_status(self.sprite_root))

    def _sprites_found(self):
        return designated_sprite_package(self.sprite_root) is not None

    def _settings_changed(self):
        self._update_display()
        if self.active and self.after_id is not None:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
            self._schedule_poll()

    def _transport_snapshot(self):
        state_getter = getattr(self.host, 'play_state', None)
        if state_getter is None:
            return False, float(self.host.cursor_position())
        state = int(state_getter())
        running = bool(state & 1)
        if running:
            position_getter = getattr(self.host, 'play_position', None)
            if position_getter is not None:
                return True, float(position_getter())
        return running, float(self.host.cursor_position())

    def _schedule_poll(self):
        if self.active and self.after_id is None:
            delay = (int(self.poll_var.get()) if self.last_transport_running
                     else STOPPED_POLL_MS)
            self.after_id = self.after(delay, self._poll)

    def _poll(self):
        self.after_id = None
        if not self.active:
            return
        now = time.time()
        try:
            running, playhead = self._transport_snapshot()
        except Exception as exc:
            self.status_var.set('Preview position could not be read: %s' % exc)
            self._schedule_poll()
            return
        stopped_now = self.last_transport_running is True and not running
        self.last_transport_running = running
        if (not running and
                (stopped_now or
                 now - self.last_read_time >= AUTO_REFRESH_SECONDS)):
            self.refresh_now()
        else:
            self._update_display(playhead)
        self._schedule_poll()

    def _clear_body(self, message=None):
        for player in self.players:
            player.destroy()
        self.players = []
        self.cards = {}
        self.layout_surrounding = None
        self.warning_label = None
        self.fallback_label = None
        for child in self.body.winfo_children():
            child.destroy()
        if message:
            ResponsiveLabel(
                self.body, text=message, foreground=PALETTE['muted'],
                justify=tk.LEFT, wraplength=680).pack(fill=tk.X)

    def _ensure_layout(self):
        surrounding = bool(self.surrounding_var.get())
        layout_key = (surrounding, self._enabled_categories())
        if self.layout_surrounding == layout_key and self.cards:
            return False
        self._clear_body()
        self.layout_surrounding = layout_key
        self.warning_label = ResponsiveLabel(
            self.body, foreground=PALETTE['warning'], justify=tk.LEFT,
            wraplength=680)
        headings = ('Previous', 'Current', 'Next') if surrounding else (
            'Current',)
        for label, key, unused_sprite_category in _CATEGORIES:
            if key not in layout_key[1]:
                continue
            group_frame = ttk.LabelFrame(self.body, text=label, padding=8)
            group_frame.pack(fill=tk.X, expand=True, pady=(0, 10))
            cards = []
            for column_index, heading in enumerate(headings):
                card_frame = ttk.Frame(
                    group_frame, padding=(0, 0, 12, 0))
                card_frame.grid(
                    row=(column_index if surrounding else 0), column=0,
                    sticky='nw', pady=(0, 8) if surrounding else 0)
                heading_label = ttk.Label(
                    card_frame, text=heading,
                    foreground=PALETTE['muted'])
                heading_label.pack(anchor='w')
                event_label = ttk.Label(card_frame)
                event_label.pack(anchor='w', pady=(6, 0))
                time_label = ttk.Label(
                    card_frame, foreground=PALETTE['muted'])
                time_label.pack(anchor='w')
                transition_label = ttk.Label(
                    card_frame, text=' ', foreground=PALETTE['muted'])
                transition_label.pack(anchor='w')
                media = ttk.Frame(card_frame)
                media.pack(fill=tk.BOTH, expand=True)
                media.pack_propagate(False)
                cards.append({
                    'event_label': event_label,
                    'time_label': time_label,
                    'transition_label': transition_label,
                    'media': media,
                    'player': None,
                    'event_identity': object(),
                    'sprite_config': None,
                    'transition': None,
                })
            self.cards[key] = cards
        self.fallback_label = ResponsiveLabel(
            self.body, text=FALLBACK_NOTE, foreground=PALETTE['warning'],
            justify=tk.LEFT, wraplength=680)
        return True

    def _update_display(self, playhead=None):
        if self.data is None:
            return
        if playhead is None:
            try:
                unused_running, playhead = self._transport_snapshot()
            except Exception as exc:
                self.status_var.set(
                    'Preview position could not be read: %s' % exc)
                return
        display_changed = self._ensure_layout()
        muted = combo_muted(self.combo_var.get())
        combo_name = PLAYER_COMBOS[self.combo_var.get()][0]
        selected_letters = tuple(letter for letter in ('b', 'g', 'k')
                                 if not muted.get(letter))
        warnings = [letter.upper() for letter in selected_letters
                    if self.actual_muted.get(letter)]
        if warnings:
            warning_text = '%s muted or missing in the project.' % ', '.join(
                warnings)
            if self.warning_label.cget('text') != warning_text:
                self.warning_label.configure(text=warning_text)
                display_changed = True
            if not self.warning_label.winfo_manager():
                self.warning_label.pack(fill=tk.X, pady=(0, 6), before=(
                    self.body.winfo_children()[1]))
                display_changed = True
        else:
            if self.warning_label.winfo_manager():
                self.warning_label.pack_forget()
                display_changed = True

        any_filtered = False
        for label, key, sprite_category in _CATEGORIES:
            if key not in self.cards:
                continue
            groups = surrounding_from_timeline(self.timelines[key], playhead)
            if self.surrounding_var.get():
                selected_groups = groups
            else:
                selected_groups = (groups[1],)
            for card, group in zip(self.cards[key], selected_groups):
                event, filtered = resolve_group(
                    group, muted if key == 'camera' else None)
                any_filtered = any_filtered or filtered
                display_changed = self._update_card(
                    card, event, sprite_category, filtered, combo_name,
                    playhead) or display_changed
        if any_filtered:
            if not self.fallback_label.winfo_manager():
                self.fallback_label.pack(fill=tk.X)
                display_changed = True
        else:
            if self.fallback_label.winfo_manager():
                self.fallback_label.pack_forget()
                display_changed = True
        if display_changed:
            self.body.update_idletasks()

    def _update_card(self, card, event, category, filtered, combo_name,
                     playhead):
        size = int(self.size_var.get())
        sprite_config = (
            self.sprite_root, size, bool(self.animate_var.get()), category)
        identity = (None if event is None else
                    (event.get('ppq'), event.get('t'), event.get('msg'),
                     bool(filtered)))
        transition = transition_text(event, playhead)
        if (identity == card['event_identity'] and
                sprite_config == card['sprite_config']):
            if transition != card['transition']:
                self._set_transition(card, transition)
                return True
            return False

        card['event_identity'] = identity
        config_changed = sprite_config != card['sprite_config']
        card['sprite_config'] = sprite_config
        if event is None:
            card['event_label'].configure(
                text='No event found', foreground=PALETTE['muted'])
            card['time_label'].configure(text='')
            self._replace_media(card, None, category, False, combo_name)
            self._set_transition(card, '')
            return True
        card['event_label'].configure(
            text=event['msg'],
            foreground=(PALETTE['error'] if filtered else ''))
        card['time_label'].configure(
            text=self._format_event_time(event['t']))
        self._set_transition(card, transition)
        if filtered:
            self._replace_media(card, event, category, True, combo_name)
            return True
        player = card['player']
        if player is not None and not config_changed:
            player.set_event(
                self.sprite_root, category, bare_sprite_name(event, category),
                '', '')
        else:
            self._replace_media(card, event, category, False, combo_name)
        return True

    def _set_transition(self, card, transition):
        card['transition'] = transition
        card['transition_label'].configure(
            text=transition or ' ',
            foreground=(PALETTE['warning']
                        if transition == 'Blending now'
                        else PALETTE['muted']))

    def _replace_media(self, card, event, category, filtered, combo_name):
        old_player = card['player']
        if old_player is not None:
            old_player.destroy()
            if old_player in self.players:
                self.players.remove(old_player)
        card['player'] = None
        media = card['media']
        for child in media.winfo_children():
            child.destroy()
        size = int(self.size_var.get())
        display_width, display_height = preview_dimensions(
            size, self.display_scale)
        media.configure(width=display_width, height=display_height)
        if event is None:
            ttk.Label(
                media, text=' ', anchor='center').pack(
                    fill=tk.BOTH, expand=True)
        elif filtered:
            ttk.Label(
                media, text='No suitable event\nfor %s' % combo_name,
                foreground=PALETTE['error'], anchor='center',
                justify=tk.CENTER,
                padding=20, relief='sunken').pack(fill=tk.BOTH, expand=True)
        else:
            player = VenueSpritePlayer(
                media, self.sprite_root, category,
                bare_sprite_name(event, category), '', '',
                animate=self.animate_var.get(), preferred_size=size,
                show_event_label=False, display_scale=self.display_scale)
            player.pack(fill=tk.BOTH, expand=True)
            card['player'] = player
            self.players.append(player)

    def _format_event_time(self, seconds):
        try:
            measure = self.host.measure_at(seconds)
        except Exception:
            measure = None
        prefix = 'M%s - ' % measure if measure is not None else ''
        return prefix + format_time(seconds)

    def destroy(self):
        self.stop()
        self._clear_body()
        ttk.Frame.destroy(self)


def open_venue_preview_window(owner, host=None, on_close=None):
    """Open Preview as a Toplevel managed by an existing Tk interpreter."""
    window = tk.Toplevel(owner)
    window.title('Rock Band Venue Preview VKR - REAPER 4.20 WIP')
    apply_window_branding(window)
    window.geometry('740x720')
    window.minsize(560, 420)
    players_row = VenueActivePlayersRow(window, host=host)
    players_row.pack(side=tk.BOTTOM, fill=tk.X)
    page = AutoVerticalScrolledFrame(window)
    page.pack(fill=tk.BOTH, expand=True)
    view = VenueTimelinePreviewView(page.content, host=host)
    view.pack(fill=tk.X)
    try:
        window.wm_attributes('-topmost', True)
    except tk.TclError:
        pass
    record = {
        'window': window, 'view': view, 'players_row': players_row,
        'page': page,
        'closed': False,
    }
    _OPEN_PREVIEW_WINDOWS.append(record)

    def finish_close():
        if record['closed']:
            return
        record['closed'] = True
        view.stop()
        players_row.stop()
        try:
            _OPEN_PREVIEW_WINDOWS.remove(record)
        except ValueError:
            pass
        if on_close is not None:
            on_close()

    def close_window():
        if record['closed']:
            return
        view.stop()
        try:
            window.destroy()
        except tk.TclError:
            pass
        finish_close()

    def window_destroyed(event):
        if event.widget is window:
            finish_close()

    window.protocol('WM_DELETE_WINDOW', close_window)
    window.bind('<Destroy>', window_destroyed, add='+')
    # A direct reference is useful to host shells and also keeps the close
    # callback alive on older Tkinter builds after the launching action exits.
    window._venue_preview_close = close_window
    players_row.start()
    view.start()
    return window, view


def existing_tk_root():
    """Return the live default Tk root shared by this Python interpreter."""
    root = getattr(tk, '_default_root', None)
    if root is None:
        return None
    try:
        return root if root.winfo_exists() else None
    except tk.TclError:
        return None


__all__ = [
    'VenueTimelinePreviewView', 'existing_tk_root',
    'open_venue_preview_window',
]
