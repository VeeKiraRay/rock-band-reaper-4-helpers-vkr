"""Tk Venue > Manual gen preview-presentation experiment.

This slice intentionally performs no REAPER writes. It is a small integration
harness for the reusable VENUE preview manager.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os

try:
    import Tkinter as tk
    import ttk
    import tkFileDialog as filedialog
except ImportError:
    import tkinter as tk
    from tkinter import ttk, filedialog

from .ui_venue_preview import (
    PREVIEW_TOOLTIP, PREVIEW_WINDOW, VenuePreviewEvent,
    VenuePreviewManager,
)
from .venue_sprites import default_sprite_root


PREVIEW_OPTIONS = (
    (PREVIEW_TOOLTIP, 'B - Tooltip preview'),
    (PREVIEW_WINDOW, 'C - Shared preview window'),
)

EVENT_GROUPS = (
    ('Normal camera', (
        VenuePreviewEvent(
            'All far', 'Camera', 'coop_all_far', '[coop_all_far]'),
        VenuePreviewEvent(
            'All near', 'Camera', 'coop_all_near', '[coop_all_near]'),
    )),
    ('Directed camera', (
        VenuePreviewEvent(
            'Crowd', 'Camera', 'directed_crowd', '[directed_crowd]'),
        VenuePreviewEvent(
            'All', 'Camera', 'directed_all', '[directed_all]'),
    )),
    ('Lighting', (
        VenuePreviewEvent(
            'Verse', 'Lighting', 'verse', '[lighting (verse)]'),
        VenuePreviewEvent(
            'Chorus', 'Lighting', 'chorus', '[lighting (chorus)]'),
    )),
    ('Post proc', (
        VenuePreviewEvent(
            'ProFilm A', 'PostProc', 'ProFilm_a.pp', '[ProFilm_a.pp]'),
        VenuePreviewEvent(
            'Film B+W', 'PostProc', 'film_b+w.pp', '[film_b+w.pp]'),
    )),
)


class VenueManualView(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, padding=12)
        self.controller = controller
        self.preview_mode = tk.StringVar()
        self.preview_mode.set(PREVIEW_TOOLTIP)
        self.sprite_root = tk.StringVar()
        self.sprite_root.set(default_sprite_root())
        self.rows = []

        self.preview = VenuePreviewManager(
            self, self.sprite_root.get, PREVIEW_TOOLTIP,
            self._preview_fallback)

        ttk.Label(
            self, text=('Reusable preview interaction test for Manual gen. '
                        'Add buttons only preview their event; this prototype '
                        'does not modify the REAPER project.'),
            justify=tk.LEFT, wraplength=720).grid(
                row=0, column=0, columnspan=3, sticky='w')

        modes = ttk.LabelFrame(self, text='Preview style', padding=8)
        modes.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(10, 8))
        for index, (value, label) in enumerate(PREVIEW_OPTIONS):
            ttk.Radiobutton(
                modes, text=label, value=value, variable=self.preview_mode,
                command=self._change_mode).grid(
                    row=0, column=index, sticky='w', padx=(0, 18))

        for row_index, (group_label, events) in enumerate(EVENT_GROUPS):
            grid_row = 2 + row_index
            variable = tk.StringVar()
            variable.set(events[0].label)
            ttk.Label(self, text=group_label).grid(
                row=grid_row, column=0, sticky='w', padx=(0, 12), pady=3)
            combo = ttk.Combobox(
                self, state='readonly', width=34, textvariable=variable,
                values=[event.label for event in events])
            combo.grid(row=grid_row, column=1, sticky='ew', pady=3)
            add_button = ttk.Button(self, text='Add')
            add_button.grid(
                row=grid_row, column=2, sticky='w', padx=(8, 0), pady=3)
            row = {
                'events': events, 'variable': variable, 'combo': combo,
                'add': add_button,
            }
            self.rows.append(row)
            selected = lambda current=row: self._selected_event(current)
            row['preview_record'] = self.preview.attach_combobox(
                combo, events, selected)
            self.preview.attach_action(add_button, selected)

        source_row = 2 + len(EVENT_GROUPS)
        source = ttk.LabelFrame(self, text='Optional preview assets', padding=8)
        source.grid(
            row=source_row, column=0, columnspan=3,
            sticky='ew', pady=(8, 8))
        source.columnconfigure(0, weight=1)
        ttk.Label(
            source,
            text=('Select the folder containing camera, lighting, and '
                  'postproc spritesheet folders. JPEG uses optional Pillow; '
                  'GIF works through Tk 8.5.'),
            justify=tk.LEFT, wraplength=680).grid(
                row=0, column=0, columnspan=2, sticky='w')
        ttk.Entry(
            source, textvariable=self.sprite_root, state='readonly').grid(
                row=1, column=0, sticky='ew', pady=(6, 0))
        ttk.Button(
            source, text='Choose folder...', command=self._choose_root).grid(
                row=1, column=1, sticky='w', padx=(8, 0), pady=(6, 0))

        self.note = ttk.Label(
            self, text=('B is the proposed default: one tooltip follows '
                        'closed dropdowns, open lists, and Add buttons. C keeps '
                        'one shared window open and retargets it from the same '
                        'controls.'),
            foreground='#666666', justify=tk.LEFT, wraplength=720)
        self.note.grid(
            row=source_row + 1, column=0, columnspan=3,
            sticky='w', pady=(0, 8))
        self.columnconfigure(1, weight=1)

    def _selected_event(self, row):
        selected = row['variable'].get()
        for event in row['events']:
            if event.label == selected:
                return event
        return row['events'][0]

    def _change_mode(self):
        self.preview.set_mode(self.preview_mode.get())

    def _choose_root(self):
        initial = self.sprite_root.get()
        if not os.path.isdir(initial):
            initial = os.path.dirname(default_sprite_root())
        chosen = filedialog.askdirectory(
            parent=self, initialdir=initial,
            title='Choose VENUE spritesheets folder')
        if chosen:
            self.sprite_root.set(os.path.abspath(chosen))
            self.preview.refresh_assets()

    def _preview_fallback(self):
        self.note.configure(
            text=('Live preview inside the open dropdown is unavailable in '
                  'this Tk environment. Selected-value, closed-dropdown, and '
                  'Add-button previews remain available.'))

    def destroy(self):
        self.preview.destroy()
        ttk.Frame.destroy(self)
