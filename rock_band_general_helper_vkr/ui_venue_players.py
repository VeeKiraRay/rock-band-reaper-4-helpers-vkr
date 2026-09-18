"""Reusable Tk active-player row for Venue views.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import time

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.reaper420 import Reaper420Host
from lib.tk_common import Tooltip

from .actions_difficulty_shared import format_time
from .venue import INSTRUMENT_NAMES
from .venue_players import (
    PLAYER_ORDER, compute_player_states, player_tooltip,
    read_instrument_availability, read_instrument_play_states,
)


STOPPED_POLL_MS = 250
PLAYING_POLL_MS = 500
AVAILABILITY_REFRESH_SECONDS = 1.0
FULL_REFRESH_SECONDS = 5.0
STATE_COLORS = {
    'active': '#44dd44',
    'idle': '#4499ff',
    'muted': '#ff4444',
    'nodata': '#ffaa00',
}
ROW_TOOLTIP = (
    'Instrument track and play-state status at the playhead:\n\n'
    'green   active ([play]/[mellow]/[intense])\n'
    'blue    idle ([idle]/[idle_realtime])\n'
    'red     track muted or missing\n'
    'orange  no play-state events (shown with the [play] fallback)\n\n'
    'Muted or missing tracks are excluded from venue generation.\n'
    'Follows the play cursor during playback, the edit cursor otherwise.\n'
    'Hover an instrument for details.')


class VenueActivePlayersRow(ttk.Frame):
    """A cached, polling view of the five Venue instrument states."""

    def __init__(self, parent, host=None):
        ttk.Frame.__init__(self, parent, padding=(10, 5, 10, 6))
        self.host = host or Reaper420Host()
        self.snapshot = None
        self.active = False
        self.after_id = None
        self.last_full_refresh = 0.0
        self.last_availability_refresh = 0.0
        self.last_playhead = None
        self.project_identity = None
        self.indicators = {}

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 5))
        body = ttk.Frame(self)
        body.pack(fill=tk.X)
        heading = ttk.Label(body, text='Active players:')
        heading.pack(side=tk.LEFT)
        Tooltip(heading, ROW_TOOLTIP)

        style = ttk.Style(self)
        background = style.lookup('TFrame', 'background') or '#f0f0f0'
        for letter in PLAYER_ORDER:
            group = ttk.Frame(body)
            group.pack(side=tk.LEFT, padx=(14, 0))
            dot = tk.Canvas(
                group, width=12, height=14, highlightthickness=0,
                borderwidth=0, background=background)
            dot.pack(side=tk.LEFT, padx=(0, 4))
            oval = dot.create_oval(2, 3, 10, 11, fill=STATE_COLORS['nodata'],
                                   outline='')
            label = ttk.Label(group, text=INSTRUMENT_NAMES[letter])
            label.pack(side=tk.LEFT)
            dot_tip = Tooltip(dot, '')
            label_tip = Tooltip(label, '')
            self.indicators[letter] = {
                'canvas': dot, 'oval': oval,
                'tooltips': (dot_tip, label_tip),
            }

    def start(self):
        if self.active:
            return
        self.active = True
        if self.snapshot is None:
            self.refresh()
        else:
            self._update_row()
        self._schedule()

    def stop(self):
        self.active = False
        if self.after_id is not None:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def refresh(self):
        try:
            self.snapshot = read_instrument_play_states(self.host)
        except Exception as exc:
            self.snapshot = {
                'states': {}, 'no_data': set(PLAYER_ORDER),
                'muted': {}, 'missing': {},
                'errors': dict((letter, str(exc)) for letter in PLAYER_ORDER),
            }
        now = time.time()
        self.last_full_refresh = now
        self.last_availability_refresh = now
        self.project_identity = self._project_identity()
        self._update_row()

    def _project_identity(self):
        getter = getattr(self.host, 'project_info', None)
        if getter is None:
            return None
        try:
            return getter().get('identity')
        except Exception:
            return None

    def _transport(self):
        state_getter = getattr(self.host, 'play_state', None)
        playing = bool(int(state_getter()) & 1) if state_getter else False
        if playing:
            getter = getattr(self.host, 'play_position', None)
            if getter is not None:
                return True, float(getter())
        return playing, float(self.host.cursor_position())

    def _refresh_availability(self):
        changed = False
        try:
            unused_tracks, muted, missing = read_instrument_availability(
                self.host)
            changed = (muted != self.snapshot.get('muted', {}) or
                       missing != self.snapshot.get('missing', {}))
            self.snapshot['muted'] = muted
            self.snapshot['missing'] = missing
        except Exception:
            pass
        self.last_availability_refresh = time.time()
        return changed

    def _update_row(self, playhead=None):
        if self.snapshot is None:
            return
        if playhead is None:
            try:
                unused_playing, playhead = self._transport()
            except Exception:
                playhead = 0.0
        row = compute_player_states(playhead, self.snapshot)
        for letter in PLAYER_ORDER:
            info = row[letter]
            indicator = self.indicators[letter]
            indicator['canvas'].itemconfigure(
                indicator['oval'], fill=STATE_COLORS[info['state']])
            tip = player_tooltip(letter, info, self.snapshot, format_time)
            for tooltip in indicator['tooltips']:
                tooltip.text = tip
        self.last_playhead = playhead

    def _schedule(self):
        if self.active and self.after_id is None:
            try:
                playing, unused_playhead = self._transport()
            except Exception:
                playing = False
            delay = PLAYING_POLL_MS if playing else STOPPED_POLL_MS
            self.after_id = self.after(delay, self._poll)

    def _poll(self):
        self.after_id = None
        if not self.active:
            return
        now = time.time()
        try:
            playing, playhead = self._transport()
        except Exception:
            self._schedule()
            return
        project_identity = self._project_identity()
        project_changed = (
            project_identity is not None and
            self.project_identity is not None and
            project_identity != self.project_identity)
        if (project_changed or
                (not playing and
                 now - self.last_full_refresh >= FULL_REFRESH_SECONDS)):
            self.refresh()
        else:
            availability_changed = False
            if (now - self.last_availability_refresh >=
                    AVAILABILITY_REFRESH_SECONDS):
                availability_changed = self._refresh_availability()
            if availability_changed or playhead != self.last_playhead:
                self._update_row(playhead)
        self._schedule()

    def destroy(self):
        self.stop()
        ttk.Frame.destroy(self)


__all__ = ['VenueActivePlayersRow']
