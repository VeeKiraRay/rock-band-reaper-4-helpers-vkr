"""Tk Venue > Events view.

Modern counterpart:
rock_band_general_helper_vkr/ui_venue_events.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import PALETTE, ResponsiveLabel

from .actions_venue_events import add_section_event, insert_events_event
from .section_events import SECTION_EVENT_BASE, SECTION_EVENT_GROUPS


class VenueEventsView(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.selected = {}
        self.numbers = {}
        self.letters = tk.BooleanVar()
        self.letters.set(True)

        body = ttk.Frame(self, padding=12)
        body.pack(fill=tk.X)

        ResponsiveLabel(
            body,
            text=('Insert section, crowd, and global events on the EVENTS '
                  'track at the current REAPER edit cursor.'),
            justify=tk.LEFT, wraplength=700).grid(
                row=0, column=0, columnspan=5, sticky='w', pady=(0, 10))

        ttk.Label(body, text='Use letter suffix').grid(
            row=1, column=0, sticky='w', pady=(0, 8))
        ttk.Checkbutton(body, variable=self.letters).grid(
            row=1, column=1, sticky='w', pady=(0, 8))

        row_index = 2
        for group in SECTION_EVENT_GROUPS:
            ttk.Label(body, text=group['label']).grid(
                row=row_index, column=0, sticky='w', padx=(0, 10), pady=3)
            selected = tk.StringVar()
            self.selected[group['key']] = selected
            if group['kind'] == 'plain':
                values = group['events']
            else:
                values = tuple(value['base'] for value in group['bases'])
            combo = ttk.Combobox(
                body, state='readonly', width=26, textvariable=selected,
                values=values)
            combo.grid(row=row_index, column=1, columnspan=(2 if group['kind'] == 'plain' else 1),
                       sticky='ew', padx=(0, 6), pady=3)
            if group['kind'] == 'plain':
                ttk.Label(body, text='').grid(row=row_index, column=3)
            else:
                number = tk.IntVar()
                number.set(0)
                self.numbers[group['key']] = number
                tk.Spinbox(
                    body, from_=0, to=9, width=4, textvariable=number,
                    justify=tk.CENTER).grid(
                        row=row_index, column=3, sticky='w', padx=(0, 6), pady=3)
            ttk.Button(
                body, text='Add', width=9,
                command=lambda value=group: self._add(value)).grid(
                    row=row_index, column=4, sticky='w', pady=3)
            row_index += 1

        body.columnconfigure(1, weight=1)
        quick = ttk.LabelFrame(body, text='Quick actions', padding=8)
        quick.grid(row=row_index, column=0, columnspan=5, sticky='ew', pady=(12, 0))
        first = ttk.Button(quick, text='Insert bookends', state=tk.DISABLED)
        first.pack(side=tk.LEFT, padx=(0, 6))
        second = ttk.Button(quick, text='Clear all', state=tk.DISABLED)
        second.pack(side=tk.LEFT)
        ResponsiveLabel(
            quick,
            text=('Deferred: bookends need a verified legacy measure walk; '
                  'Clear all needs a separately confirmed bulk-delete workflow.'),
            foreground=PALETTE['muted'], justify=tk.LEFT,
            wraplength=520).pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

    def _add(self, group):
        selection = self.selected[group['key']].get()
        if not selection:
            self.controller.show_result(
                'Select an EVENTS event first.',
                'Choose a value in the %s row, then press Add.' % group['label'])
            return
        try:
            if group['kind'] == 'plain':
                status, report = insert_events_event(
                    self.controller.host, selection)
            else:
                number = self.numbers[group['key']].get()
                caps = SECTION_EVENT_BASE[selection]['caps']
                status, report = add_section_event(
                    self.controller.host, selection, number, caps,
                    group['kind'] == 'generic', self.letters.get())
            self.controller.show_result(status, report)
        except Exception as exc:
            self.controller.show_result(
                'EVENTS insertion could not complete',
                'The guarded insertion stopped. No unverified project change '
                'was accepted.\n\n%s' % exc)
