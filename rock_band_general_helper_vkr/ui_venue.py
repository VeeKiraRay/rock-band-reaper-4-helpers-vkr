"""Tk Venue tab for the REAPER 4.20 General Helper.

Modern counterpart:
rock_band_general_helper_vkr/ui_venue.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.reaper420 import Reaper420Host
from .actions_venue_validate import validate_venue_lighting
from .actions_venue_validate_camera import validate_venue_camera
from .ui_venue_events import VenueEventsView
from .ui_venue_keyframes import VenueKeyframesView
from .ui_venue_manual import VenueManualView
from .ui_venue_section import VenueSectionView
from .ui_venue_themes import VenueThemesView
from .venue import list_event_sections, list_lighting_postproc, list_venue_events


class VenueView(ttk.Frame):
    def __init__(self, parent, show_result, host=None):
        ttk.Frame.__init__(self, parent)
        self.show_result = show_result
        self.host = host or Reaper420Host()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        actions = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(actions, text='Actions')
        self._build_actions(actions)
        events = VenueEventsView(self.notebook, self)
        self.notebook.add(events, text='Events')
        themes = VenueThemesView(self.notebook, self)
        self.notebook.add(themes, text='Themes gen')
        self.sections_view = VenueSectionView(self.notebook, self)
        self.notebook.add(self.sections_view, text='Section gen')
        manual = VenueManualView(self.notebook, self)
        self.notebook.add(manual, text='Manual gen')
        keyframes = VenueKeyframesView(self.notebook, self)
        self.notebook.add(keyframes, text='Keyframes')
        for label in ('Preview',):
            pane = ttk.Frame(self.notebook, padding=12)
            ttk.Label(
                pane,
                text='%s is planned for a later Venue implementation slice.' % label,
                anchor='center', justify=tk.CENTER).pack(
                    fill=tk.BOTH, expand=True, padx=20, pady=20)
            self.notebook.add(pane, text=label)
        self.notebook.bind('<<NotebookTabChanged>>', self._tab_changed)

    def _build_actions(self, parent):
        ttk.Label(
            parent,
            text=('Inspect and validate the complete EVENTS and VENUE tracks. '
                  'These actions are read-only and create no Undo point.'),
            justify=tk.LEFT, wraplength=700).pack(anchor='w', fill=tk.X)

        analyze = ttk.LabelFrame(parent, text='Analyze', padding=8)
        analyze.pack(fill=tk.X, pady=(10, 0))
        row = ttk.Frame(analyze)
        row.pack(fill=tk.X)
        self._button(row, 'List venue events', list_venue_events)
        self._button(row, 'List event sections', list_event_sections)
        self._button(row, 'List lighting/postproc', list_lighting_postproc)

        validate = ttk.LabelFrame(parent, text='Validate', padding=8)
        validate.pack(fill=tk.X, pady=(10, 0))
        row = ttk.Frame(validate)
        row.pack(fill=tk.X)
        self._button(row, 'Validate lighting/blends', validate_venue_lighting)
        self._button(row, 'Validate camera stacks', validate_venue_camera)

        future = ttk.LabelFrame(parent, text='Later Venue slices', padding=8)
        future.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(
            future,
            text=('Generate sing along and VENUE subtrack copy actions remain '
                  'disabled until their note/text mutation paths have dedicated '
                  'legacy fixtures and REAPER 4.20 validation.'),
            foreground='#666666', justify=tk.LEFT, wraplength=700).pack(
                anchor='w', fill=tk.X)

    def _button(self, parent, label, action):
        ttk.Button(
            parent, text=label,
            command=lambda fn=action: self._run(fn)).pack(
                side=tk.LEFT, padx=(0, 6), pady=(0, 2))

    def _run(self, action):
        try:
            status, report = action(self.host)
            self.show_result(status, report)
        except Exception as exc:
            self.show_result(
                'Venue action could not run',
                'The read-only Venue action could not safely inspect the '
                'project. No project changes were made.\n\n%s' % exc)

    def refresh_current(self):
        # Venue project reads remain behind explicit buttons on REAPER 4.20.
        pass

    def _tab_changed(self, unused_event=None):
        if self.notebook.select() == str(self.sections_view):
            self.sections_view.refresh_on_open()
