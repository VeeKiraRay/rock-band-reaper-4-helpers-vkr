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

from .ui_metadata_genre import MetadataGenreView
from .ui_metadata_difficulty import MetadataDifficultyView


class MetadataView(ttk.Frame):
    def __init__(self, parent, show_result):
        ttk.Frame.__init__(self, parent)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.genre_tab = MetadataGenreView(self.notebook, show_result)
        self.difficulty_tab = MetadataDifficultyView(
            self.notebook, show_result)

        self.notebook.add(self.genre_tab, text='Genre')
        self.notebook.add(self.difficulty_tab, text='Difficulty')
        self.notebook.bind('<<NotebookTabChanged>>', self._tab_changed)

    def _tab_changed(self, unused_event=None):
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
