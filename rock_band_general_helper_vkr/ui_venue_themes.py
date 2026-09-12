"""Tk Venue > Themes gen view.

Modern counterpart: rock_band_general_helper_vkr/ui_venue.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from .actions_venue_themes import (
    KEYFRAME_ALIGN_LABELS, generate_venue_events,
)
from .venue_themes import load_venue_themes


PACING_LABELS = (
    'Theme default', 'Minimal (32 16ths)', 'Slow (24 16ths)',
    'Medium (16 16ths)', 'Fast (8 16ths)', 'Crazy (4 16ths)',
    'Custom', 'Vocal phrase start',
)
SUBDIVISION_LABELS = ('Every beat', 'Every half beat', 'Every quarter beat')


class VenueThemesView(ttk.Frame):
    def __init__(self, parent, controller, themes_dir=None):
        ttk.Frame.__init__(self, parent, padding=12)
        self.controller = controller
        if themes_dir is None:
            themes_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'resources', 'themes')
        self.themes, self.theme_errors = load_venue_themes(themes_dir)
        self.by_label = dict((theme['label'], theme) for theme in self.themes)

        self.theme_name = tk.StringVar()
        self.camera_pacing = tk.StringVar()
        self.camera_pacing.set(PACING_LABELS[0])
        self.camera_jitter = tk.BooleanVar()
        self.camera_jitter.set(True)
        self.camera_custom = tk.IntVar()
        self.camera_custom.set(16)
        self.keyframe_align = tk.StringVar()
        self.keyframe_align.set(KEYFRAME_ALIGN_LABELS[0])
        self.subdivision = tk.StringVar()
        self.subdivision.set(SUBDIVISION_LABELS[0])
        if self.themes:
            self.theme_name.set(self.themes[0]['label'])

        ttk.Label(
            self,
            text='Generate venue events using a .rbtheme for the whole song.',
            justify=tk.LEFT, wraplength=700).grid(
                row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(
            self,
            text=('Generation replaces type-1 text events inside the single '
                  'VENUE MIDI item, while preserving its notes, track-name '
                  'event, source metadata, and events outside the song range.'),
            foreground='#666666', justify=tk.LEFT, wraplength=700).grid(
                row=1, column=0, columnspan=3, sticky='w', pady=(3, 12))

        if not self.themes:
            ttk.Label(
                self, text='No .rbtheme files were found in resources/themes.',
                foreground='#aa3333').grid(
                    row=2, column=0, columnspan=3, sticky='w', pady=(0, 8))
        elif self.theme_errors:
            ttk.Label(
                self, text='%d theme file(s) could not be loaded.' %
                len(self.theme_errors), foreground='#aa6600').grid(
                    row=2, column=0, columnspan=3, sticky='w', pady=(0, 8))

        self._label(3, 'Theme')
        ttk.Combobox(
            self, state='readonly', width=32, textvariable=self.theme_name,
            values=tuple(theme['label'] for theme in self.themes)).grid(
                row=3, column=1, columnspan=2, sticky='ew', pady=3)

        self._label(4, 'Camera pacing')
        pacing = ttk.Combobox(
            self, state='readonly', width=32,
            textvariable=self.camera_pacing, values=PACING_LABELS)
        pacing.grid(row=4, column=1, sticky='ew', pady=3)
        pacing.bind('<<ComboboxSelected>>', self._sync_states)
        self.jitter_check = ttk.Checkbutton(
            self, text='Include jitter', variable=self.camera_jitter)
        self.jitter_check.grid(
            row=4, column=2, sticky='w', padx=(8, 0), pady=3)

        self._label(5, 'Custom interval')
        self.custom_spin = tk.Spinbox(
            self, from_=2, to=128, width=7,
            textvariable=self.camera_custom, justify=tk.CENTER)
        self.custom_spin.grid(row=5, column=1, sticky='w', pady=3)
        ttk.Label(self, text='16th notes').grid(
            row=5, column=2, sticky='w', padx=(8, 0), pady=3)

        self._label(6, 'Keyframe align')
        align = ttk.Combobox(
            self, state='readonly', width=32,
            textvariable=self.keyframe_align, values=KEYFRAME_ALIGN_LABELS)
        align.grid(row=6, column=1, columnspan=2, sticky='ew', pady=3)
        align.bind('<<ComboboxSelected>>', self._sync_states)

        self._label(7, 'Subdivision')
        self.subdivision_combo = ttk.Combobox(
            self, state='readonly', width=32,
            textvariable=self.subdivision, values=SUBDIVISION_LABELS)
        self.subdivision_combo.grid(
            row=7, column=1, columnspan=2, sticky='ew', pady=3)

        self.generate_button = ttk.Button(
            self, text='Generate venue events', command=self._generate)
        self.generate_button.grid(row=8, column=0, columnspan=3,
                                  sticky='w', pady=(14, 0))
        if not self.themes:
            self.generate_button.configure(state=tk.DISABLED)
        self.columnconfigure(1, weight=1)
        self._sync_states()

    def _label(self, row, text):
        ttk.Label(self, text=text).grid(
            row=row, column=0, sticky='w', padx=(0, 12), pady=3)

    def _sync_states(self, unused_event=None):
        custom = self.camera_pacing.get() == PACING_LABELS[6]
        self.custom_spin.configure(state=(tk.NORMAL if custom else tk.DISABLED))
        phrase = self.camera_pacing.get() == PACING_LABELS[7]
        # Phrase positions are exact, so interval jitter has no effect.
        self.jitter_check.configure(
            state=(tk.DISABLED if phrase else tk.NORMAL))
        instrument = self.keyframe_align.get() in KEYFRAME_ALIGN_LABELS[3:]
        self.subdivision_combo.configure(
            state=('readonly' if instrument else tk.DISABLED))

    def _generate(self):
        theme = self.by_label.get(self.theme_name.get())
        if theme is None:
            self.controller.show_result(
                'Select a Venue theme first.',
                'Choose a .rbtheme preset, then press Generate venue events.')
            return
        options = {
            'camera_pacing': PACING_LABELS.index(self.camera_pacing.get()),
            'camera_jitter': self.camera_jitter.get(),
            'camera_custom': self.camera_custom.get(),
            'keyframe_align': KEYFRAME_ALIGN_LABELS.index(
                self.keyframe_align.get()),
            'keyframe_subdivision': SUBDIVISION_LABELS.index(
                self.subdivision.get()),
        }
        try:
            status, report = generate_venue_events(
                self.controller.host, theme, options)
            self.controller.show_result(status, report)
        except Exception as exc:
            self.controller.show_result(
                'Venue theme generation could not complete',
                'The guarded generator stopped. No unverified project change '
                'was accepted.\n\n%s' % exc)
