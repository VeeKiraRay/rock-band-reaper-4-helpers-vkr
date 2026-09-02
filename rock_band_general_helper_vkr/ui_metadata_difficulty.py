"""Tk rendering for Metadata > Difficulty.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import Tooltip
from .metadata_difficulty import (
    CHART_SPECS,
    analyse_project,
    card_summary,
    format_inventory,
)


class MetadataDifficultyView(ttk.Frame):
    def __init__(self, parent, show_result, analyser=None):
        ttk.Frame.__init__(self, parent, padding=12)
        self.show_result = show_result
        self.analyser = analyser or analyse_project
        self.has_refreshed = False
        self.status_vars = {}
        self.summary_vars = {}

        heading = ttk.Frame(self)
        heading.pack(fill=tk.X)
        ttk.Label(
            heading,
            text='Difficulty chart inventory',
            font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        refresh = ttk.Button(
            heading, text='Refresh charts', command=self.refresh)
        refresh.pack(side=tk.RIGHT)
        Tooltip(
            refresh,
            'Read the six chart tracks again. This does not modify the '
            'project or create an undo point.')

        ttk.Label(
            self,
            text='Bass now runs through the calibrated difficulty model. '
                 'The other five cards remain chart-inventory checks while '
                 'their larger factor scorers are ported.',
            justify=tk.LEFT,
            wraplength=680).pack(anchor='w', fill=tk.X, pady=(8, 12))

        cards = ttk.Frame(self)
        cards.pack(fill=tk.BOTH, expand=True)
        for column in range(3):
            cards.columnconfigure(column, weight=1)
        for row in range(2):
            cards.rowconfigure(row, weight=1)

        for index, spec in enumerate(CHART_SPECS):
            card = ttk.LabelFrame(cards, text=spec['label'], padding=9)
            card.grid(
                row=index // 3, column=index % 3,
                sticky='nsew', padx=4, pady=4)
            status_var = tk.StringVar()
            status_var.set('Not analysed')
            summary_var = tk.StringVar()
            summary_var.set(spec['track'])
            ttk.Label(
                card, textvariable=status_var,
                font=('TkDefaultFont', 9, 'bold')).pack(anchor='w')
            ttk.Label(
                card, textvariable=summary_var,
                justify=tk.LEFT, wraplength=190).pack(
                    anchor='w', fill=tk.X, pady=(5, 0))
            self.status_vars[spec['key']] = status_var
            self.summary_vars[spec['key']] = summary_var

    def refresh_current(self):
        if not self.has_refreshed:
            self.refresh()

    def refresh(self):
        try:
            results = self.analyser()
        except Exception as exc:
            self.show_result(
                'Difficulty inventory could not run',
                'Metadata Difficulty could not read the project.\n\n%s' % exc)
            return

        self.has_refreshed = True
        for result in results:
            self.status_vars[result['key']].set(result['status'])
            self.summary_vars[result['key']].set(card_summary(result))

        found = sum(1 for result in results if result['present'])
        readable = sum(1 for result in results
                       if result['parsed_items'] and not result['failed_items'])
        self.show_result(
            'Difficulty inventory: %d/6 tracks found, %d cleanly read' %
            (found, readable),
            format_inventory(results))
