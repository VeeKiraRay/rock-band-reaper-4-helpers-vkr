"""Tk rendering for Metadata > Genre.

Modern counterpart:
rock_band_general_helper_vkr/ui_metadata_genre.lua

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
from .metadata_genres_ext import GENRE_FAMILIES, GENRE_FAMILY_ORDER
from .metadata_genres_lookup import (
    format_genre_recommendation,
    genres_in_family,
    resolve_extended_genre,
)


INTRODUCTION = (
    'Rock Band accepts 29 major genres and 126 subgenres. Pick the genre '
    'you would actually call the song and this suggests the closest '
    'supported pair. The result is advisory and contains display names, '
    'not songs.dta tokens.')

ADVISORY = (
    'Where a style belongs is a judgment call, and some genres genuinely '
    'map more than one way. If a suggestion looks plainly wrong, the mapping '
    'is meant to be questioned and corrected.')


class MetadataGenreView(ttk.Frame):
    def __init__(self, parent, show_result):
        ttk.Frame.__init__(self, parent, padding=12)
        self.show_result = show_result
        self.family_keys = list(GENRE_FAMILY_ORDER)
        self.entries = []

        ttk.Label(
            self,
            text='Genre converter',
            font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        ttk.Label(
            self,
            text=INTRODUCTION,
            justify=tk.LEFT,
            wraplength=680).pack(anchor='w', fill=tk.X, pady=(8, 6))
        ttk.Label(
            self,
            text=ADVISORY,
            foreground='#666666',
            justify=tk.LEFT,
            wraplength=680).pack(anchor='w', fill=tk.X, pady=(0, 12))

        form = ttk.Frame(self)
        form.pack(anchor='w', fill=tk.X)

        ttk.Label(form, text='Family', width=14).grid(
            row=0, column=0, sticky='w', pady=3)
        self.family_combo = ttk.Combobox(
            form,
            state='readonly',
            width=30,
            values=[GENRE_FAMILIES[key] for key in self.family_keys])
        self.family_combo.grid(row=0, column=1, sticky='w', pady=3)
        self.family_combo.current(0)
        self.family_combo.bind('<<ComboboxSelected>>', self._family_changed)
        Tooltip(
            self.family_combo,
            'Choose a broad family first to keep the authored genre list '
            'short enough to browse.')

        ttk.Label(form, text='Your genre', width=14).grid(
            row=1, column=0, sticky='w', pady=3)
        self.genre_combo = ttk.Combobox(
            form, state='readonly', width=30)
        self.genre_combo.grid(row=1, column=1, sticky='w', pady=3)
        self.genre_combo.bind('<<ComboboxSelected>>', self._genre_changed)
        Tooltip(
            self.genre_combo,
            'Choose the real-world style you would use to describe the song.')

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(
            fill=tk.X, pady=(14, 10))
        ttk.Label(
            self,
            text='The supported recommendation and its reasoning appear in '
                 'the Result panel below.',
            justify=tk.LEFT,
            wraplength=680).pack(anchor='w', fill=tk.X)

        self._load_family(0)

    def _family_changed(self, unused_event=None):
        self._load_family(self.family_combo.current())
        self.refresh_current()

    def _genre_changed(self, unused_event=None):
        self.refresh_current()

    def _load_family(self, index):
        if index < 0 or index >= len(self.family_keys):
            index = 0
        family_key = self.family_keys[index]
        self.entries = list(genres_in_family(family_key))
        self.genre_combo.configure(
            values=[entry['label'] for entry in self.entries])
        if self.entries:
            self.genre_combo.current(0)
        else:
            self.genre_combo.set('')

    def refresh_current(self):
        index = self.genre_combo.current()
        if index < 0 or index >= len(self.entries):
            self.show_result(
                'Genre converter: no selection',
                'No genres are available in this family.')
            return
        entry = self.entries[index]
        result = resolve_extended_genre(entry['key'])
        self.show_result(
            'Genre converter: %s' % entry['label'],
            format_genre_recommendation(result))

