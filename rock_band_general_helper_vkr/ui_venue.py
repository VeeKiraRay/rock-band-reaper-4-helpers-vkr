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
from lib.tk_common import PinnedTabNotebook, ResponsiveLabel
from .actions_venue_validate import validate_venue_lighting
from .actions_venue_validate_camera import validate_venue_camera
from .ui_venue_events import VenueEventsView
from .ui_venue_keyframes import VenueKeyframesView
from .ui_venue_manual import VenueManualView
from .ui_venue_preview_tab import VenueTimelinePreviewView
from .ui_venue_players import VenueActivePlayersRow
from .ui_venue_section import VenueSectionView
from .ui_venue_themes import VenueThemesView
from .venue import list_event_sections, list_lighting_postproc, list_venue_events


class VenueView(ttk.Frame):
    def __init__(self, parent, show_result, host=None, players_parent=None):
        ttk.Frame.__init__(self, parent)
        self.show_result = show_result
        self.host = host or Reaper420Host()

        player_host = self if players_parent is None else players_parent
        self.players_row = VenueActivePlayersRow(player_host, host=self.host)
        self.players_row.pack(
            side=(tk.BOTTOM if players_parent is None else tk.TOP), fill=tk.X)
        self.notebook = PinnedTabNotebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        actions_content, self.actions_page = (
            self.notebook.add_scrolled_page('Actions'))
        actions = ttk.Frame(actions_content, padding=12)
        actions.pack(fill=tk.X)
        self._build_actions(actions)
        events_content, self.events_page = (
            self.notebook.add_scrolled_page('Events'))
        self.events_view = VenueEventsView(events_content, self)
        self.events_view.pack(fill=tk.X)
        themes_content, self.themes_page = (
            self.notebook.add_scrolled_page('Themes gen'))
        self.themes_view = VenueThemesView(themes_content, self)
        self.themes_view.pack(fill=tk.X)
        sections_content, self.sections_page = (
            self.notebook.add_scrolled_page('Section gen'))
        self.sections_view = VenueSectionView(sections_content, self)
        self.sections_view.pack(fill=tk.X)
        manual_content, self.manual_page = (
            self.notebook.add_scrolled_page('Manual gen'))
        self.manual_view = VenueManualView(manual_content, self)
        self.manual_view.pack(fill=tk.X)
        keyframes_content, self.keyframes_page = (
            self.notebook.add_scrolled_page('Keyframes'))
        self.keyframes_view = VenueKeyframesView(keyframes_content, self)
        self.keyframes_view.pack(fill=tk.X)
        preview_content, self.preview_page = (
            self.notebook.add_scrolled_page('Preview'))
        self.preview_view = VenueTimelinePreviewView(
            preview_content, host=self.host, allow_detach=True)
        self.preview_view.pack(fill=tk.X)
        self.notebook.bind(
            '<<NotebookTabChanged>>', self._tab_changed, add='+')

    def _build_actions(self, parent):
        ResponsiveLabel(
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
        self.players_row.start()
        if self.notebook.select() == str(self.preview_page):
            self.preview_view.start()

    def deactivate(self):
        self.players_row.stop()
        self.preview_view.stop()

    def _tab_changed(self, unused_event=None):
        selected = self.notebook.select()
        if selected == str(self.sections_page):
            self.sections_view.refresh_on_open()
        if selected == str(self.preview_page):
            self.preview_view.start()
        else:
            self.preview_view.stop()
