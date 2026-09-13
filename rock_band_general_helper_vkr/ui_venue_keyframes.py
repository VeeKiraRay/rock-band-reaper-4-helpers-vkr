"""Tk Venue > Keyframes view.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import ResponsiveLabel

from .actions_venue_keyframes import (
    KEYFRAME_ALIGN_LABELS, regenerate_venue_keyframes,
)
from .ui_venue_themes import SUBDIVISION_LABELS


class VenueKeyframesView(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, padding=12)
        self.controller = controller
        self.align = tk.StringVar(); self.align.set(KEYFRAME_ALIGN_LABELS[0])
        self.subdivision = tk.StringVar()
        self.subdivision.set(SUBDIVISION_LABELS[0])
        self.rate = tk.IntVar(); self.rate.set(2)

        ResponsiveLabel(
            self, text=('Regenerate [first]/[next] keyframes for every manual '
                        'lighting change already on the VENUE track.'),
            justify=tk.LEFT, wraplength=700).grid(
                row=0, column=0, columnspan=3, sticky='w')
        ResponsiveLabel(
            self, text=('With a time selection, only manual lighting changes '
                        'that start inside the selection are processed.'),
            foreground='#666666', justify=tk.LEFT, wraplength=700).grid(
                row=1, column=0, columnspan=3, sticky='w', pady=(3, 10))

        self._label(2, 'Keyframe align')
        align_combo = ttk.Combobox(
            self, state='readonly', width=32, textvariable=self.align,
            values=KEYFRAME_ALIGN_LABELS)
        align_combo.grid(row=2, column=1, columnspan=2, sticky='ew', pady=3)
        align_combo.bind('<<ComboboxSelected>>', self._sync_states)

        self._label(3, 'Subdivision')
        self.subdivision_combo = ttk.Combobox(
            self, state='readonly', width=32,
            textvariable=self.subdivision, values=SUBDIVISION_LABELS)
        self.subdivision_combo.grid(
            row=3, column=1, columnspan=2, sticky='ew', pady=3)

        self._label(4, 'Keyframe rate')
        self.rate_spin = tk.Spinbox(
            self, from_=1, to=8, width=7, textvariable=self.rate,
            justify=tk.CENTER)
        self.rate_spin.grid(row=4, column=1, sticky='w', pady=3)
        self.rate_spin.bind('<FocusOut>', self._clamp_rate)
        ttk.Label(self, text='beats').grid(
            row=4, column=2, sticky='w', padx=(8, 0))

        ttk.Button(
            self, text='Regenerate keyframes', command=self._regenerate).grid(
                row=5, column=0, columnspan=3, sticky='w', pady=(12, 0))
        self.columnconfigure(1, weight=1)
        self._sync_states()

    def _label(self, row, text):
        ttk.Label(self, text=text).grid(
            row=row, column=0, sticky='w', padx=(0, 12), pady=3)

    def _clamp_rate(self, unused_event=None):
        try:
            value = int(self.rate.get())
        except (tk.TclError, TypeError, ValueError):
            value = 1
        self.rate.set(max(1, min(8, value)))

    def _sync_states(self, unused_event=None):
        instrument = self.align.get() in KEYFRAME_ALIGN_LABELS[3:]
        self.subdivision_combo.configure(
            state=('readonly' if instrument else tk.DISABLED))

    def _regenerate(self):
        self._clamp_rate()
        try:
            status, report = regenerate_venue_keyframes(
                self.controller.host, self.rate.get(),
                KEYFRAME_ALIGN_LABELS.index(self.align.get()),
                SUBDIVISION_LABELS.index(self.subdivision.get()))
            self.controller.show_result(status, report)
        except Exception as exc:
            self.controller.show_result(
                'Venue keyframe regeneration could not complete',
                'The guarded generator stopped. No unverified project change '
                'was accepted.\n\n%s' % exc)
