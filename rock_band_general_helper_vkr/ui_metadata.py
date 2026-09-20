"""Tk rendering for the General Helper Metadata tab.

Modern counterpart:
rock_band_general_helper_vkr/ui_metadata.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import PinnedTabNotebook

from .ui_metadata_genre import MetadataGenreView
from .ui_metadata_difficulty import MetadataDifficultyView


class MetadataView(ttk.Frame):
    def __init__(self, parent, show_result):
        ttk.Frame.__init__(self, parent)
        self.notebook = PinnedTabNotebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        genre_content, self.genre_page = (
            self.notebook.add_scrolled_page('Genre'))
        difficulty_content, self.difficulty_page = (
            self.notebook.add_scrolled_page('Difficulty'))
        self.genre_tab = MetadataGenreView(genre_content, show_result)
        self.genre_tab.pack(fill=tk.X)
        self.difficulty_tab = MetadataDifficultyView(
            difficulty_content, show_result)
        self.difficulty_tab.pack(fill=tk.X)
        self.notebook.bind(
            '<<NotebookTabChanged>>', self._tab_changed, add='+')

    def _tab_changed(self, unused_event=None):
        # Tk posts an initial nested-notebook change while the whole Metadata
        # view is still hidden during application construction. Do not let
        # that internal event populate the shared Result area on startup.
        if not self.winfo_ismapped():
            return
        self.refresh_current()

    def refresh_current(self):
        try:
            index = self.notebook.index(self.notebook.select())
        except Exception:
            return
        if index == 0:
            self.genre_tab.refresh_current()
        elif index == 1:
            self.difficulty_tab.refresh_current()
