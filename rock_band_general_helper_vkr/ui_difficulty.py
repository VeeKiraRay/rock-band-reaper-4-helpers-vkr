"""Tk rendering for the General Helper Difficulty tab.

Modern counterpart:
rock_band_general_helper_vkr/ui_difficulty.lua

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
from lib.tk_common import Tooltip
from .actions_difficulty_5k import validate_keys, DIFFICULTY_ORDER
from .actions_difficulty import validate_all_pro_keys, validate_pro_keys


DIFFICULTY_LABELS = {
    'X': 'Expert', 'H': 'Hard', 'M': 'Medium', 'E': 'Easy'}


class ProKeysDifficultyPane(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, padding=12)
        self.controller = controller
        self.track_vars = {}
        self.track_combos = {}

        track_group = ttk.LabelFrame(
            self, text='Pro Keys tracks', padding=8)
        track_group.pack(fill=tk.X)
        for row_index, difficulty in enumerate(DIFFICULTY_ORDER):
            label = DIFFICULTY_LABELS[difficulty]
            ttk.Label(track_group, text=label, width=8).grid(
                row=row_index, column=0, sticky='w', pady=2)
            variable = tk.StringVar()
            combo = ttk.Combobox(
                track_group, state='readonly', width=38,
                textvariable=variable)
            combo.grid(row=row_index, column=1, sticky='ew', padx=(6, 8),
                       pady=2)
            self.track_vars[difficulty] = variable
            self.track_combos[difficulty] = combo
        track_group.columnconfigure(1, weight=1)
        refresh = ttk.Button(
            track_group, text='Refresh tracks',
            command=lambda: controller.refresh_tracks(focus='pro_keys'))
        refresh.grid(row=0, column=2, rowspan=2, sticky='n')
        Tooltip(refresh, 'Refresh the project track list and auto-select '
                'PART REAL_KEYS_X/H/M/E by exact name.')

        guide = ttk.LabelFrame(
            self, text='Authoring reduction guide', padding=8)
        guide.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(
            guide,
            text=(
                'Reduce from the immediately higher tier: Expert to Hard, '
                'Hard to Medium, then Medium to Easy. Validation checks '
                'adjacent gem counts and unchanged copies as well as each '
                'tier\'s Pro Keys authoring rules.\n\nAutomatic Copy to '
                'Hard/Medium/Easy remains deferred until guarded MIDI '
                'writers are implemented.'),
            justify=tk.LEFT, wraplength=660).pack(anchor='w', fill=tk.X)

        validation = ttk.LabelFrame(self, text='Validate', padding=8)
        validation.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(
            validation,
            text=('Check the complete selected Pro Keys track against chord, '
                  'lane-shift, interval, overlap, sustain, and '
                  'cross-difficulty rules.'),
            justify=tk.LEFT, wraplength=660).pack(anchor='w', fill=tk.X)
        first_row = ttk.Frame(validation)
        first_row.pack(fill=tk.X, pady=(8, 0))
        second_row = ttk.Frame(validation)
        second_row.pack(fill=tk.X)
        for index, difficulty in enumerate(DIFFICULTY_ORDER):
            parent_row = first_row if index < 3 else second_row
            ttk.Button(
                parent_row,
                text='Validate %s' % DIFFICULTY_LABELS[difficulty],
                command=lambda value=difficulty:
                    controller.run_pro_keys_validation(value)).pack(
                        side=tk.LEFT, padx=(0, 6), pady=(0, 6))
        ttk.Button(
            second_row, text='Validate All',
            command=lambda: controller.run_pro_keys_validation(None)).pack(
                side=tk.LEFT, pady=(0, 6))

        ttk.Label(
            self,
            text=('This view is read-only and always checks complete tracks. '
                  'It does not create an undo point.'),
            foreground='#666666', justify=tk.LEFT,
            wraplength=660).pack(anchor='w', fill=tk.X, pady=(10, 0))

    def set_track_records(self, records):
        values = ['%d: %s' % (index + 1, name)
                  for index, unused_track, name in records]
        for difficulty in DIFFICULTY_ORDER:
            combo = self.track_combos[difficulty]
            combo['values'] = values
            wanted = 'PART REAL_KEYS_' + difficulty
            selected = None
            for position, record in enumerate(records):
                if record[2].strip().upper() == wanted:
                    selected = position
                    break
            if selected is None:
                self.track_vars[difficulty].set('')
                combo.set('')
            else:
                combo.current(selected)

    def selected_tracks(self, records):
        selected = {}
        for difficulty, combo in self.track_combos.items():
            position = combo.current()
            selected[difficulty] = (
                records[position][1]
                if 0 <= position < len(records) else None)
        return selected


class KeysDifficultyPane(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, padding=12)
        self.controller = controller

        track_group = ttk.LabelFrame(self, text='Keys track', padding=8)
        track_group.pack(fill=tk.X)
        row = ttk.Frame(track_group)
        row.pack(fill=tk.X)
        ttk.Label(row, text='PART KEYS').pack(side=tk.LEFT)
        self.track_combo = ttk.Combobox(
            row, state='readonly', width=38,
            textvariable=controller.track_var)
        self.track_combo.pack(side=tk.LEFT, fill=tk.X, expand=True,
                              padx=(10, 8))
        refresh = ttk.Button(
            row, text='Refresh tracks',
            command=lambda: controller.refresh_tracks(focus='keys'))
        refresh.pack(side=tk.RIGHT)
        Tooltip(refresh, 'Refresh the project track list and auto-select the '
                'first exact PART KEYS match.')

        guide = ttk.LabelFrame(
            self, text='Authoring reduction guide', padding=8)
        guide.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(
            guide,
            text=(
                'Author each easier tier from the tier immediately above: '
                'Expert to Hard, Hard to Medium, then Medium to Easy. The '
                'validator checks that adjacent tiers contain fewer gems and '
                'warns when a tier is an unchanged octave-shifted copy.\n\n'
                'Automatic Copy to Hard/Medium/Easy is intentionally deferred '
                'until the guarded MIDI writer is added.'),
            justify=tk.LEFT, wraplength=660).pack(anchor='w', fill=tk.X)

        validation = ttk.LabelFrame(self, text='Validate', padding=8)
        validation.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(
            validation,
            text=('Read the complete PART KEYS chart and check one difficulty '
                  'range against Rock Band authoring rules.'),
            justify=tk.LEFT, wraplength=660).pack(anchor='w', fill=tk.X)
        button_row = ttk.Frame(validation)
        button_row.pack(fill=tk.X, pady=(8, 0))
        for difficulty in DIFFICULTY_ORDER:
            button = ttk.Button(
                button_row,
                text='Validate %s' % DIFFICULTY_LABELS[difficulty],
                command=lambda value=difficulty: self._validate(value))
            button.pack(side=tk.LEFT, padx=(0, 6), pady=(0, 6))
        ttk.Button(
            button_row, text='Validate All',
            command=self._validate_all).pack(side=tk.LEFT, pady=(0, 6))

        ttk.Label(
            self,
            text=('This first Difficulty slice is read-only and always checks '
                  'the whole track. It does not create an undo point.'),
            foreground='#666666', justify=tk.LEFT,
            wraplength=660).pack(anchor='w', fill=tk.X, pady=(10, 0))

    def _validate(self, difficulty):
        self.controller.run_validation(difficulty)

    def _validate_all(self):
        self.controller.run_validation(None)


class DifficultyView(ttk.Frame):
    def __init__(self, parent, show_result, host=None):
        ttk.Frame.__init__(self, parent)
        self.show_result = show_result
        self.host = host or Reaper420Host()
        self.track_var = tk.StringVar()
        self.track_records = []
        self.project_identity = None

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        for label in ('Pro Keys', 'Keys', 'Guitar/Bass', 'Drums'):
            if label == 'Pro Keys':
                self.pro_keys_pane = ProKeysDifficultyPane(
                    self.notebook, self)
                pane = self.pro_keys_pane
            elif label == 'Keys':
                self.keys_pane = KeysDifficultyPane(self.notebook, self)
                pane = self.keys_pane
            else:
                pane = ttk.Frame(self.notebook, padding=20)
                ttk.Label(
                    pane,
                    text=('%s validation will be added in the next '
                          'Difficulty slice.' % label),
                    anchor='center').pack(fill=tk.BOTH, expand=True)
            self.notebook.add(pane, text=label)
        self.track_combo = self.keys_pane.track_combo
        self.notebook.select(0)
        self.refresh_tracks(show_result=False)

    def _project_info(self):
        try:
            return self.host.project_info()
        except Exception:
            return None

    def refresh_current(self):
        info = self._project_info()
        identity = info.get('identity') if info else None
        if (identity is not None and self.project_identity is not None and
                identity != self.project_identity):
            self.refresh_tracks(show_result=False)

    def refresh_tracks(self, show_result=True, focus=None):
        try:
            records = []
            for index in range(self.host.track_count()):
                track = self.host.get_track(index)
                name = self.host.track_name(track, index)
                records.append((index, track, name))
            self.track_records = records
            values = ['%d: %s' % (index + 1, name)
                      for index, unused_track, name in records]
            self.track_combo['values'] = values
            self.pro_keys_pane.set_track_records(records)
            selected = None
            for position, record in enumerate(records):
                if record[2].strip().upper() == 'PART KEYS':
                    selected = position
                    break
            if selected is None and records:
                selected = 0
            if selected is None:
                self.track_var.set('')
            else:
                self.track_combo.current(selected)
            info = self._project_info()
            self.project_identity = (
                info.get('identity') if info else self.project_identity)
            if show_result:
                if focus == 'pro_keys':
                    status = 'Pro Keys tracks auto-detected.'
                    result = (
                        'Refreshed the project track list and selected exact '
                        'PART REAL_KEYS_X/H/M/E matches where available.')
                elif focus == 'keys':
                    status = 'Keys track auto-detected.'
                    result = (
                        'Refreshed the project track list and selected the '
                        'first exact PART KEYS match where available.')
                else:
                    status = ('Difficulty tracks refreshed: %d track%s found.' %
                              (len(records),
                               '' if len(records) == 1 else 's'))
                    result = 'Difficulty track selections refreshed.'
                self.show_result(status, result)
        except Exception as exc:
            self.track_records = []
            self.track_var.set('')
            self.track_combo['values'] = ()
            self.pro_keys_pane.set_track_records(())
            if show_result:
                self.show_result(
                    'Difficulty track refresh failed',
                    'Could not read the project track list.\n\n%s' % exc)

    def _selected_track(self):
        position = self.track_combo.current()
        if position < 0 or position >= len(self.track_records):
            return None
        return self.track_records[position][1]

    def run_validation(self, difficulty):
        track = self._selected_track()
        if track is None:
            self.show_result(
                'Error: PART KEYS track not selected.',
                'Refresh the track list and select PART KEYS in the '
                'Difficulty > Keys tab.')
            return
        try:
            if difficulty is not None:
                status, report = validate_keys(self.host, track, difficulty)
            else:
                from .actions_difficulty_5k import validate_all_keys
                status, report = validate_all_keys(self.host, track)
            self.show_result(status, report)
        except Exception as exc:
            self.show_result(
                'Keys validation could not run',
                'Difficulty validation could not safely read the selected '
                'track. No project changes were made.\n\n%s' % exc)

    def run_pro_keys_validation(self, difficulty):
        tracks = self.pro_keys_pane.selected_tracks(self.track_records)
        if difficulty is not None and tracks.get(difficulty) is None:
            name = DIFFICULTY_LABELS[difficulty]
            self.show_result(
                'Error: %s Pro Keys track not selected.' % name,
                'Refresh the track list and select PART REAL_KEYS_%s in the '
                'Difficulty > Pro Keys tab.' % difficulty)
            return
        try:
            if difficulty is None:
                status, report = validate_all_pro_keys(
                    self.host, tracks)
            else:
                status, report = validate_pro_keys(
                    self.host, tracks, difficulty)
            self.show_result(status, report)
        except Exception as exc:
            self.show_result(
                'Pro Keys validation could not run',
                'Difficulty validation could not safely read the selected '
                'tracks. No project changes were made.\n\n%s' % exc)
