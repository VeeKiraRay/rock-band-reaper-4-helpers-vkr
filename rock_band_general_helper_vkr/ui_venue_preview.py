"""Reusable Tk VENUE event preview popup management.

The public attachment API uses ordinary Tk widgets. Live hover inside an open
ttk Combobox uses Tk's private popdown listbox when available and otherwise
falls back to selected-value previews without disabling the surrounding UI.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk

from .venue_sprites import VenueSpritePlayer


PREVIEW_TOOLTIP = 'tooltip'
PREVIEW_WINDOW = 'window'
PREVIEW_MODES = (PREVIEW_TOOLTIP, PREVIEW_WINDOW)


class VenuePreviewEvent(object):
    def __init__(self, label, category, bare_name, raw_event,
                 description=''):
        self.label = label
        self.category = category
        self.bare_name = bare_name
        self.raw_event = raw_event
        self.description = description or ''

    def key(self):
        return (self.category, self.bare_name, self.raw_event,
                self.description)


class VenuePreviewManager(object):
    """Share one tooltip or persistent window among attached controls."""

    def __init__(self, owner, sprite_root_getter, mode=PREVIEW_TOOLTIP,
                 fallback_callback=None):
        self.owner = owner
        self.tk = owner.tk
        self.sprite_root_getter = sprite_root_getter
        self.fallback_callback = fallback_callback
        self.mode = PREVIEW_TOOLTIP
        self.current_event = None
        self.popup = None
        self.player = None
        self.popup_is_tooltip = None
        self.hover_after_id = None
        self.position_after_id = None
        self.open_record = None
        self.bound_popdowns = {}
        self.tcl_commands = []
        self.list_preview_supported = None
        self.fallback_reported = False
        self.set_mode(mode)

    def attach_combobox(self, combo, events, selected_getter):
        """Attach an ordered event list matching a readonly combobox's rows."""
        record = {
            'combo': combo,
            'events': tuple(events),
            'selected': selected_getter,
            'listbox': None,
        }
        old_post = str(combo.cget('postcommand') or '')
        post = self._register(lambda rec=record: self._combo_posted(rec))
        combo.configure(postcommand=(old_post + ';' + post if old_post else post))
        combo.bind(
            '<<ComboboxSelected>>',
            lambda event, rec=record: self._selection_changed(rec), add='+')
        combo.bind(
            '<Enter>', lambda event, rec=record: self._combo_enter(rec), add='+')
        combo.bind(
            '<Leave>', lambda event, rec=record: self._combo_leave(rec), add='+')
        combo.bind('<ButtonPress-1>', self._cancel_hover, add='+')
        combo.bind(
            '<KeyRelease-Up>',
            lambda event, rec=record: self._closed_key_changed(rec), add='+')
        combo.bind(
            '<KeyRelease-Down>',
            lambda event, rec=record: self._closed_key_changed(rec), add='+')
        return record

    def attach_action(self, widget, selected_getter):
        """Preview an action's selected event without replacing its command."""
        widget.bind(
            '<Enter>',
            lambda event, get=selected_getter, anchor=widget:
                self._action_enter(get, anchor), add='+')
        widget.bind(
            '<Leave>', lambda event: self._action_leave(), add='+')
        widget.bind(
            '<ButtonPress-1>',
            lambda event, get=selected_getter, anchor=widget:
                self._action_pressed(get, anchor), add='+')

    def set_mode(self, mode):
        if mode not in PREVIEW_MODES:
            raise ValueError('Unknown VENUE preview mode: %s' % mode)
        self.mode = mode
        self._cancel_hover()
        self.close()

    def refresh_assets(self):
        self._update_player()

    def close(self):
        self._cancel_position()
        if self.player is not None:
            self.player.stop()
            self.player = None
        if self.popup is not None:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
            self.popup = None
            self.popup_is_tooltip = None

    def destroy(self):
        self._cancel_hover()
        self.close()
        for command in self.tcl_commands:
            try:
                self.owner.deletecommand(command)
            except tk.TclError:
                pass
        self.tcl_commands = []

    def _register(self, callback):
        command = self.owner.register(callback)
        self.tcl_commands.append(command)
        return command

    def _selected(self, record):
        try:
            return record['selected']()
        except Exception:
            return None

    def _set_event(self, event):
        if event is None:
            self.current_event = None
            if self.player is not None:
                self.player.clear_event()
            return
        if (self.current_event is not None and
                self.current_event.key() == event.key()):
            return
        self.current_event = event
        self._update_player()

    def _update_player(self):
        if self.player is None or self.current_event is None:
            return
        event = self.current_event
        self.player.set_event(
            self.sprite_root_getter(), event.category,
            event.bare_name, event.raw_event, event.description)

    def _combo_enter(self, record):
        selected = self._selected(record)
        self._set_event(selected)
        if selected is None and self.mode == PREVIEW_TOOLTIP:
            self.close()
        if self.mode == PREVIEW_TOOLTIP and self.open_record is None:
            self._cancel_hover()
            self.hover_after_id = self.owner.after(
                350, lambda rec=record: self._show_closed_tooltip(rec))
        elif self.mode == PREVIEW_WINDOW:
            self._open_popup(False, anchor_widget=record['combo'])

    def _combo_leave(self, record):
        self._cancel_hover()
        if self.mode == PREVIEW_TOOLTIP and self.open_record is not record:
            self.close()

    def _show_closed_tooltip(self, record):
        self.hover_after_id = None
        if self.mode == PREVIEW_TOOLTIP and self.open_record is None:
            selected = self._selected(record)
            self._set_event(selected)
            if selected is None:
                self.close()
                return
            self._open_popup(True, anchor_widget=record['combo'])

    def _selection_changed(self, record):
        selected = self._selected(record)
        self._set_event(selected)
        if selected is None and self.mode == PREVIEW_TOOLTIP:
            self.close()

    def _closed_key_changed(self, record):
        self.owner.after_idle(
            lambda rec=record: self._closed_selection_changed(rec))

    def _closed_selection_changed(self, record):
        selected = self._selected(record)
        self._set_event(selected)
        if selected is None and self.mode == PREVIEW_TOOLTIP:
            self.close()

    def _action_enter(self, selected_getter, anchor):
        self._set_event(selected_getter())
        if self.mode == PREVIEW_TOOLTIP:
            self._cancel_hover()
            self.hover_after_id = self.owner.after(
                350, lambda get=selected_getter, item=anchor:
                    self._show_action_tooltip(get, item))
        else:
            self._open_popup(False, anchor_widget=anchor)

    def _show_action_tooltip(self, selected_getter, anchor):
        self.hover_after_id = None
        if self.mode == PREVIEW_TOOLTIP and self.open_record is None:
            self._set_event(selected_getter())
            self._open_popup(True, anchor_widget=anchor)

    def _action_leave(self):
        self._cancel_hover()
        if self.mode == PREVIEW_TOOLTIP and self.open_record is None:
            self.close()

    def _action_pressed(self, selected_getter, anchor):
        self._cancel_hover()
        self._set_event(selected_getter())
        self._open_popup(
            self.mode == PREVIEW_TOOLTIP, anchor_widget=anchor)

    def _cancel_hover(self, unused_event=None):
        if self.hover_after_id is not None:
            try:
                self.owner.after_cancel(self.hover_after_id)
            except Exception:
                pass
            self.hover_after_id = None

    def _combo_posted(self, record):
        self._cancel_hover()
        self.open_record = record
        selected = self._selected(record)
        self._set_event(selected)
        if selected is None and self.mode == PREVIEW_TOOLTIP:
            self.close()
        combo = record['combo']
        try:
            popdown = self.tk.call(
                'ttk::combobox::PopdownWindow', str(combo))
            listbox = str(popdown) + '.f.l'
            record['listbox'] = listbox
            if listbox not in self.bound_popdowns:
                self._bind_popdown(record, listbox)
                self.bound_popdowns[listbox] = True
            self.list_preview_supported = True
        except tk.TclError:
            record['listbox'] = None
            self.list_preview_supported = False
            self._report_fallback()
        self.owner.after_idle(
            lambda rec=record: self._after_combo_posted(rec))

    def _bind_popdown(self, record, listbox):
        motion = self._register(
            lambda y, rec=record, path=listbox:
                self._popdown_motion(rec, path, y))
        key = self._register(
            lambda rec=record, path=listbox:
                self._popdown_key(rec, path))
        unmap = self._register(
            lambda rec=record: self._popdown_unmapped(rec))
        self.tk.call('bind', listbox, '<Motion>', motion + ' %y')
        self.tk.call('bind', listbox, '<KeyRelease>', key)
        self.tk.call('bind', listbox, '<Unmap>', unmap)

    def _after_combo_posted(self, record):
        if self.open_record is not record:
            return
        listbox = record['listbox']
        if self.mode == PREVIEW_TOOLTIP and listbox:
            self._open_popup(True, listbox=listbox)
        elif self.mode == PREVIEW_WINDOW:
            self._open_popup(False, anchor_widget=record['combo'])

    def _popdown_motion(self, record, listbox, y):
        try:
            index = int(self.tk.call(listbox, 'nearest', int(y)))
        except (tk.TclError, TypeError, ValueError):
            return
        self._preview_candidate(record, index)

    def _popdown_key(self, record, listbox):
        self.owner.after_idle(
            lambda rec=record, path=listbox:
                self._preview_popdown_active(rec, path))

    def _preview_popdown_active(self, record, listbox):
        try:
            index = int(self.tk.call(listbox, 'index', 'active'))
        except (tk.TclError, TypeError, ValueError):
            return
        self._preview_candidate(record, index)

    def _preview_candidate(self, record, index):
        events = record['events']
        if 0 <= index < len(events):
            candidate = events[index]
            self._set_event(candidate)
            if candidate is None:
                if self.mode == PREVIEW_TOOLTIP:
                    self.close()
                return
            if self.open_record is record and self.popup is None:
                if self.mode == PREVIEW_TOOLTIP:
                    self._open_popup(
                        True, listbox=record.get('listbox'))
                else:
                    self._open_popup(
                        False, anchor_widget=record['combo'])

    def _popdown_unmapped(self, record):
        self.owner.after_idle(
            lambda rec=record: self._finish_popdown(rec))

    def _finish_popdown(self, record):
        if self.open_record is record:
            self.open_record = None
        self._set_event(self._selected(record))
        if self.mode == PREVIEW_TOOLTIP:
            self.close()

    def _report_fallback(self):
        if self.fallback_reported or self.fallback_callback is None:
            return
        self.fallback_reported = True
        self.fallback_callback()

    def _open_popup(self, tooltip, anchor_widget=None, listbox=None):
        if self.current_event is None:
            return
        if self.popup is not None and self.popup_is_tooltip == bool(tooltip):
            self._update_player()
            if tooltip:
                self._position_tooltip(anchor_widget, listbox)
            else:
                try:
                    self.popup.lift()
                except tk.TclError:
                    pass
            return
        self.close()
        popup = tk.Toplevel(self.owner)
        popup.withdraw()
        self.popup = popup
        self.popup_is_tooltip = bool(tooltip)
        if tooltip:
            popup.wm_overrideredirect(True)
            try:
                popup.wm_attributes('-topmost', True)
            except tk.TclError:
                pass
            body = tk.Frame(
                popup, relief='solid', borderwidth=1, padx=8, pady=8)
        else:
            popup.title('VENUE event preview')
            popup.transient(self.owner.winfo_toplevel())
            popup.protocol('WM_DELETE_WINDOW', self.close)
            body = tk.Frame(popup, padx=10, pady=10)
        body.pack(fill=tk.BOTH, expand=True)
        event = self.current_event
        self.player = VenueSpritePlayer(
            body, self.sprite_root_getter(), event.category,
            event.bare_name, event.raw_event, event.description)
        self.player.pack(fill=tk.BOTH, expand=True)
        if not tooltip:
            tk.Button(body, text='Close', command=self.close).pack(
                anchor='e', pady=(8, 0))
        self._retry_position(tooltip, anchor_widget, listbox)

    def _retry_position(self, tooltip, anchor_widget, listbox):
        self._cancel_position()
        self.position_after_id = self.owner.after(
            25, lambda tip=tooltip, anchor=anchor_widget, path=listbox:
                self._finish_position(tip, anchor, path))

    def _finish_position(self, tooltip, anchor_widget, listbox):
        self.position_after_id = None
        if self.popup is None or self.popup_is_tooltip != bool(tooltip):
            return
        if tooltip:
            positioned = self._position_tooltip(anchor_widget, listbox)
        else:
            positioned = self._position_window(anchor_widget)
        if not positioned:
            self._retry_position(tooltip, anchor_widget, listbox)
            return
        try:
            self.popup.deiconify()
            self.popup.lift()
        except tk.TclError:
            pass

    def _cancel_position(self):
        if self.position_after_id is not None:
            try:
                self.owner.after_cancel(self.position_after_id)
            except Exception:
                pass
            self.position_after_id = None

    def _position_window(self, anchor_widget):
        if self.popup is None or anchor_widget is None:
            return False
        self.popup.update_idletasks()
        try:
            anchor_x = anchor_widget.winfo_rootx()
            x = anchor_x + anchor_widget.winfo_width() + 8
            y = anchor_widget.winfo_rooty()
            if x + self.popup.winfo_reqwidth() > self.owner.winfo_screenwidth():
                x = max(0, anchor_x - self.popup.winfo_reqwidth() - 8)
            self.popup.wm_geometry('+%d+%d' % (x, y))
            return True
        except tk.TclError:
            return False

    def _position_tooltip(self, anchor_widget=None, listbox=None):
        if self.popup is None:
            return False
        self.popup.update_idletasks()
        try:
            if listbox:
                if not int(self.tk.call('winfo', 'ismapped', listbox)):
                    return False
                anchor_x = int(self.tk.call('winfo', 'rootx', listbox))
                anchor_y = int(self.tk.call('winfo', 'rooty', listbox))
                anchor_width = int(self.tk.call('winfo', 'width', listbox))
                x = anchor_x + anchor_width + 6
                y = anchor_y
            else:
                x = (anchor_widget.winfo_rootx() +
                     anchor_widget.winfo_width() + 6)
                y = anchor_widget.winfo_rooty()
            self.popup.wm_geometry('+%d+%d' % (x, y))
            return True
        except tk.TclError:
            return False
