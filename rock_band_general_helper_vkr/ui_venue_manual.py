"""Tk Venue > Manual gen view.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import ResponsiveLabel, Tooltip

from .actions_venue_keyframes import KEYFRAME_ALIGN_LABELS
from .actions_venue_manual import (
    REMOVE_LABELS, advance_camera_pacing, blend_venue_preset,
    generate_manual_keyframes, insert_venue_event, remove_venue_events,
)
from .ui_venue_preview import (
    PREVIEW_TOOLTIP, VenuePreviewEvent, VenuePreviewManager,
)
from .ui_venue_themes import SUBDIVISION_LABELS
from .venue import CAMERA_EVENTS, POSTPROC_EVENTS
from .venue_sprites import default_sprite_root
from .venue_themes import LIGHTING_NAMES
from .venue_tooltips import (
    BLEND_LIGHTING_TIP, BLEND_POSTPROC_TIP, CAMERA_ADVANCE_TIP,
    CAMERA_CUSTOM_TIP, CAMERA_JITTER_TIP, CAMERA_PACING_TIP,
    DIRECTED_TIPS, KEYFRAME_ALIGN_TIP, KEYFRAME_GENERATE_TIP,
    KEYFRAME_RATE_TIP, LIGHTING_TIPS, POSTPROC_TIPS, remove_tip,
)


SELECT = '(select)'
PACING_LABELS = (
    'Minimal (32 16ths)', 'Slow (24 16ths)', 'Medium (16 16ths)',
    'Fast (8 16ths)', 'Crazy (4 16ths)', 'Custom',
    'Vocal phrase start',
)
SPECIAL_EVENTS = (
    ('Bonus FX', '[bonusfx]'),
    ('Bonus FX (optional)', '[bonusfx_optional]'),
    ('[first] keyframe', '[first]'),
    ('[next] keyframe', '[next]'),
    ('[previous] keyframe', '[previous]'),
)


def _label(name):
    text = name.replace('.pp', '').replace('_', ' ')
    return ' '.join(word[:1].upper() + word[1:] for word in text.split())


def _preview_events(names, category, wrapper, tips=None):
    tips = tips or {}
    return tuple(VenuePreviewEvent(
        _label(name), category, name, wrapper % name,
        tips.get(name, '')) for name in names)


COOP_NAMES = tuple(name for name in CAMERA_EVENTS if name.startswith('coop_'))
DIRECTED_NAMES = tuple(
    name for name in CAMERA_EVENTS if name.startswith('directed_'))
COOP_PREVIEWS = _preview_events(COOP_NAMES, 'Camera', '[%s]')
DIRECTED_PREVIEWS = _preview_events(
    DIRECTED_NAMES, 'Camera', '[%s]', DIRECTED_TIPS)
LIGHTING_PREVIEWS = _preview_events(
    LIGHTING_NAMES, 'Lighting', '[lighting (%s)]', LIGHTING_TIPS)
POSTPROC_PREVIEWS = _preview_events(
    POSTPROC_EVENTS, 'PostProc', '[%s]', POSTPROC_TIPS)


class VenueManualView(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.sprite_root = default_sprite_root()
        self.rows = {}
        self.bounded = []
        self.text_tooltips = []

        canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(
            self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body = ttk.Frame(canvas, padding=12)
        window = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda unused: canvas.configure(
            scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(
            window, width=event.width))

        self.preview_note = ResponsiveLabel(
            body, foreground='#666666', justify=tk.LEFT, wraplength=700)
        self.preview = VenuePreviewManager(
            body, lambda: self.sprite_root, PREVIEW_TOOLTIP,
            self._preview_fallback)

        ResponsiveLabel(
            body, text='Insert individual VENUE events at the edit cursor.',
            justify=tk.LEFT, wraplength=700).grid(
                row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))

        row = 1
        self._event_row(body, row, 'Normal camera', COOP_PREVIEWS, 'coop')
        row += 1
        self._event_row(
            body, row, 'Directed camera', DIRECTED_PREVIEWS, 'directed')
        row += 1
        self._event_row(
            body, row, 'Lighting', LIGHTING_PREVIEWS, 'lighting',
            blend_kind='lighting')
        row += 1

        keys = ttk.LabelFrame(body, text='Manual lighting keyframes', padding=8)
        keys.grid(row=row, column=0, columnspan=4, sticky='ew', pady=(8, 4))
        self.keyframe_align = tk.StringVar()
        self.keyframe_align.set(KEYFRAME_ALIGN_LABELS[0])
        self.subdivision = tk.StringVar()
        self.subdivision.set(SUBDIVISION_LABELS[0])
        self.keyframe_rate = tk.IntVar(); self.keyframe_rate.set(2)
        self._form_label(keys, 0, 'Keyframe align')
        self.align_combo = self._combo(
            keys, 0, self.keyframe_align, KEYFRAME_ALIGN_LABELS)
        self.align_combo.bind('<<ComboboxSelected>>', self._sync_states)
        self._tip(self.align_combo, KEYFRAME_ALIGN_TIP)
        self._form_label(keys, 1, 'Subdivision')
        self.subdivision_combo = self._combo(
            keys, 1, self.subdivision, SUBDIVISION_LABELS)
        self._form_label(keys, 2, 'Keyframe rate')
        self.keyframe_rate_spin = self._spin(
            keys, 2, self.keyframe_rate, 1, 8, 'beats')
        self._tip(self.keyframe_rate_spin, KEYFRAME_RATE_TIP)
        self.keyframe_button = ttk.Button(
            keys, text='Generate keyframes',
            command=self._generate_keyframes)
        self.keyframe_button.grid(
            row=3, column=0, columnspan=3, sticky='w', pady=(8, 0))
        self._tip(self.keyframe_button, KEYFRAME_GENERATE_TIP)
        keys.columnconfigure(1, weight=1)
        row += 1

        self._event_row(
            body, row, 'Post proc', POSTPROC_PREVIEWS, 'postproc',
            blend_kind='postproc')
        row += 1

        self.special = tk.StringVar(); self.special.set(SELECT)
        self._form_label(body, row, 'Special')
        special_values = (SELECT,) + tuple(value[0] for value in SPECIAL_EVENTS)
        self.special_combo = self._combo(
            body, row, self.special, special_values)
        self.special_combo.bind('<<ComboboxSelected>>', self._sync_states)
        self.special_add = ttk.Button(
            body, text='Add', command=self._add_special)
        self.special_add.grid(row=row, column=2, sticky='w', padx=(8, 0))
        row += 1

        pacing = ttk.LabelFrame(body, text='Camera pacing', padding=8)
        pacing.grid(row=row, column=0, columnspan=4, sticky='ew', pady=(8, 4))
        self.camera_pacing = tk.StringVar()
        self.camera_pacing.set(PACING_LABELS[1])
        self.camera_jitter = tk.BooleanVar(); self.camera_jitter.set(True)
        self.camera_custom = tk.IntVar(); self.camera_custom.set(16)
        self._form_label(pacing, 0, 'Interval')
        self.pacing_combo = self._combo(
            pacing, 0, self.camera_pacing, PACING_LABELS)
        self.pacing_combo.bind('<<ComboboxSelected>>', self._sync_states)
        self._tip(self.pacing_combo, CAMERA_PACING_TIP)
        self.jitter_check = ttk.Checkbutton(
            pacing, text='Include jitter', variable=self.camera_jitter)
        self.jitter_check.grid(row=0, column=2, sticky='w', padx=(8, 0))
        self._tip(self.jitter_check, CAMERA_JITTER_TIP)
        self._form_label(pacing, 1, 'Custom interval')
        self.custom_spin = self._spin(
            pacing, 1, self.camera_custom, 2, 128, '16th notes')
        self._tip(self.custom_spin, CAMERA_CUSTOM_TIP)
        self.advance_button = ttk.Button(
            pacing, text='Advance camera pacing',
            command=self._advance)
        self.advance_button.grid(
            row=2, column=0, columnspan=3, sticky='w', pady=(8, 0))
        self._tip(self.advance_button, CAMERA_ADVANCE_TIP)
        pacing.columnconfigure(1, weight=1)
        row += 1

        remove = ttk.LabelFrame(body, text='Remove VENUE events', padding=8)
        remove.grid(row=row, column=0, columnspan=4, sticky='ew', pady=(8, 4))
        self.remove_type = tk.StringVar(); self.remove_type.set(REMOVE_LABELS[0])
        ttk.Label(remove, text='Event type').grid(
            row=0, column=0, sticky='w', padx=(0, 12))
        self.remove_combo = self._combo(
            remove, 0, self.remove_type, REMOVE_LABELS)
        self.remove_combo.bind('<<ComboboxSelected>>', self._sync_states)
        self.remove_button = ttk.Button(
            remove, text='Remove', command=self._remove)
        self.remove_button.grid(
            row=0, column=2, sticky='w', padx=(8, 0))
        self.remove_tooltip = self._tip(
            self.remove_combo, remove_tip(self.remove_type.get()))
        self.remove_button_tooltip = self._tip(
            self.remove_button, remove_tip(self.remove_type.get()))
        ResponsiveLabel(
            remove,
            text=('Uses the active time selection when present; otherwise '
                  'uses the full VENUE item.'),
            foreground='#666666', justify=tk.LEFT, wraplength=700).grid(
                row=1, column=0, columnspan=3, sticky='w', pady=(6, 0))
        remove.columnconfigure(1, weight=1)
        row += 1

        self.preview_note.grid(
            row=row, column=0, columnspan=4, sticky='w', pady=(6, 0))
        body.columnconfigure(1, weight=1)
        self._sync_states()

    def _form_label(self, parent, row, text):
        ttk.Label(parent, text=text).grid(
            row=row, column=0, sticky='w', padx=(0, 12), pady=3)

    def _tip(self, widget, text):
        tooltip = Tooltip(widget, text)
        self.text_tooltips.append(tooltip)
        return tooltip

    def _combo(self, parent, row, variable, values):
        combo = ttk.Combobox(
            parent, state='readonly', width=34,
            textvariable=variable, values=values)
        combo.grid(row=row, column=1, sticky='ew', pady=3)
        return combo

    def _spin(self, parent, row, variable, low, high, suffix):
        spin = tk.Spinbox(
            parent, from_=low, to=high, width=7,
            textvariable=variable, justify=tk.CENTER)
        spin.grid(row=row, column=1, sticky='w', pady=3)
        ttk.Label(parent, text=suffix).grid(
            row=row, column=2, sticky='w', padx=(8, 0))
        self.bounded.append((variable, low, high))
        spin.bind('<FocusOut>', self._clamp)
        return spin

    def _event_row(self, parent, row, label, events, key, blend_kind=None):
        variable = tk.StringVar(); variable.set(SELECT)
        self._form_label(parent, row, label)
        combo = self._combo(
            parent, row, variable,
            (SELECT,) + tuple(event.label for event in events))
        buttons = ttk.Frame(parent)
        buttons.grid(row=row, column=2, columnspan=2, sticky='w', padx=(8, 0))
        add = ttk.Button(
            buttons, text='Add',
            command=lambda name=key: self._add_event(name))
        add.pack(side=tk.LEFT)
        blend = None
        if blend_kind is not None:
            blend = ttk.Button(
                buttons, text='Blend',
                command=lambda kind=blend_kind: self._blend(kind))
            blend.pack(side=tk.LEFT, padx=(6, 0))
            self._tip(
                blend, BLEND_LIGHTING_TIP if blend_kind == 'lighting'
                else BLEND_POSTPROC_TIP)
        entry = {
            'variable': variable, 'events': events, 'combo': combo,
            'add': add, 'blend': blend,
        }
        self.rows[key] = entry
        selected = lambda current=entry: self._selected_preview(current)
        # The leading None matches the visible (select) row.
        entry['preview_record'] = self.preview.attach_combobox(
            combo, (None,) + tuple(events), selected)
        self.preview.attach_action(add, selected)
        combo.bind('<<ComboboxSelected>>', self._sync_states, add='+')

    def _selected_preview(self, entry):
        selected = entry['variable'].get()
        for event in entry['events']:
            if event.label == selected:
                return event
        return None

    def _selected_message(self, key):
        event = self._selected_preview(self.rows[key])
        return event.raw_event if event is not None else None

    def _sync_states(self, unused_event=None):
        for entry in self.rows.values():
            entry['add'].configure(
                state=(tk.NORMAL if self._selected_preview(entry)
                       else tk.DISABLED))
        self.special_add.configure(
            state=(tk.NORMAL if self.special.get() != SELECT
                   else tk.DISABLED))
        custom = self.camera_pacing.get() == PACING_LABELS[5]
        phrase = self.camera_pacing.get() == PACING_LABELS[6]
        self.custom_spin.configure(
            state=(tk.NORMAL if custom else tk.DISABLED))
        self.jitter_check.configure(
            state=(tk.DISABLED if phrase else tk.NORMAL))
        removal_tip = remove_tip(self.remove_type.get())
        self.remove_tooltip.text = removal_tip
        self.remove_button_tooltip.text = removal_tip
        instrument = self.keyframe_align.get() in KEYFRAME_ALIGN_LABELS[3:]
        self.subdivision_combo.configure(
            state=('readonly' if instrument else tk.DISABLED))

    def _clamp(self, unused_event=None):
        for variable, low, high in self.bounded:
            try:
                value = int(variable.get())
            except (tk.TclError, TypeError, ValueError):
                value = low
            variable.set(max(low, min(high, value)))

    def _run(self, title, action):
        try:
            status, report = action()
            self.controller.show_result(status, report)
        except Exception as exc:
            self.controller.show_result(
                title,
                'The guarded Manual gen action stopped. No unverified project '
                'change was accepted.\n\n%s' % exc)

    def _add_event(self, key):
        message = self._selected_message(key)
        if message:
            self._run(
                'VENUE insertion could not complete',
                lambda: insert_venue_event(self.controller.host, message))

    def _add_special(self):
        by_label = dict(SPECIAL_EVENTS)
        message = by_label.get(self.special.get())
        if message:
            self._run(
                'VENUE insertion could not complete',
                lambda: insert_venue_event(self.controller.host, message))

    def _blend(self, kind):
        self._run(
            'VENUE blend could not complete',
            lambda: blend_venue_preset(self.controller.host, kind))

    def _generate_keyframes(self):
        self._clamp()
        self._run(
            'Manual keyframe generation could not complete',
            lambda: generate_manual_keyframes(
                self.controller.host, self.keyframe_rate.get(),
                KEYFRAME_ALIGN_LABELS.index(self.keyframe_align.get()),
                SUBDIVISION_LABELS.index(self.subdivision.get())))

    def _advance(self):
        self._clamp()
        self._run(
            'Camera pacing could not advance',
            lambda: advance_camera_pacing(
                self.controller.host,
                PACING_LABELS.index(self.camera_pacing.get()),
                self.camera_custom.get(), self.camera_jitter.get()))

    def _remove(self):
        self._run(
            'VENUE removal could not complete',
            lambda: remove_venue_events(
                self.controller.host,
                REMOVE_LABELS.index(self.remove_type.get())))

    def _preview_fallback(self):
        self.preview_note.configure(
            text=('Live preview inside the open dropdown is unavailable in '
                  'this Tk environment. Selected-value, closed-dropdown, and '
                  'Add-button previews remain available.'))

    def destroy(self):
        self.preview.destroy()
        ttk.Frame.destroy(self)
