"""Tk rendering for General Helper Tab Input and MIDI tabs.

Modern counterpart:
rock_band_general_helper_vkr/ui_midi.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import Tooltip, make_scrolled_text, read_text, replace_text
from lib.reaper420 import Reaper420Host
from . import defaults
from .actions_guitar_guide import add_empty_note, guitar_tab_guide
from .actions_keys_guides import pro_keys_tab_guide, vocal_tab_guide
from .actions_midi_length import (
    adjust_midi_note_lengths,
    resize_all_midi_items,
    sustain_gap_default,
)
from .actions_midi_replace import (
    DIFFICULTY_LABELS,
    capture_pattern,
    fill_range,
    get_pattern_pitch_range,
    go_to_match,
    list_matches,
    new_pattern_state,
    replace_all,
    reset_pattern_state,
)


MODE_LABELS = ('Guitar / Bass', 'Keys / Pro Keys', 'Vocal')


class TabInputPane(ttk.Frame):
    def __init__(self, parent, controller, mode):
        ttk.Frame.__init__(self, parent, padding=10)
        self.controller = controller
        self.mode = mode
        self.current_format = controller.state['format']
        self.format_var = tk.IntVar()
        self.format_var.set(self.current_format)

        format_row = ttk.Frame(self)
        format_row.pack(fill=tk.X)
        horizontal = ttk.Radiobutton(
            format_row, text='Horizontal', variable=self.format_var,
            value=defaults.TAB_FORMAT_HORIZONTAL,
            command=self._format_changed)
        vertical = ttk.Radiobutton(
            format_row, text='Vertical', variable=self.format_var,
            value=defaults.TAB_FORMAT_VERTICAL,
            command=self._format_changed)
        horizontal.pack(side=tk.LEFT)
        vertical.pack(side=tk.LEFT, padx=(16, 0))
        Tooltip(horizontal, defaults.FORMAT_TOOLTIP)
        Tooltip(vertical, defaults.FORMAT_TOOLTIP)

        self.animation_var = tk.BooleanVar()
        self.animation_var.set(False)
        if mode == defaults.MODE_KEYS:
            animation = ttk.Checkbutton(
                self,
                text='For animation (full C2-C4, no lane windows)',
                variable=self.animation_var)
            animation.pack(anchor='w', pady=(10, 0))
            Tooltip(animation, defaults.MODE_TOOLTIPS[mode])

        input_group = ttk.LabelFrame(self, text='Six-string tab input')
        input_group.pack(fill=tk.BOTH, expand=True, pady=(10, 8))
        text_container, self.text = make_scrolled_text(
            input_group,
            height=12,
            wrap=tk.NONE,
            undo=True,
            font=('Courier New', 10))
        text_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        button_row = ttk.Frame(self)
        button_row.pack(fill=tk.X)
        add_button = ttk.Button(
            button_row, text='Add note', command=self._add_note)
        run_button = ttk.Button(
            button_row, text='Run guide', command=self._run_guide)
        add_button.pack(side=tk.LEFT)
        run_button.pack(side=tk.LEFT, padx=(8, 0))
        Tooltip(add_button, defaults.ADD_NOTE_TOOLTIP)
        Tooltip(run_button, defaults.MODE_TOOLTIPS[mode])

    def save(self):
        self.controller.state[
            'vertical' if self.current_format else 'horizontal'] = read_text(
                self.text)

    def load(self):
        self.current_format = self.controller.state['format']
        self.format_var.set(self.current_format)
        value = self.controller.state[
            'vertical' if self.current_format else 'horizontal']
        replace_text(self.text, value)

    def _format_changed(self):
        requested = int(self.format_var.get())
        self.controller.change_format(self, requested)

    def _add_note(self):
        self.save()
        key = 'vertical' if self.current_format else 'horizontal'
        self.controller.state[key] = add_empty_note(
            self.controller.state[key], bool(self.current_format))
        self.controller.load_all()
        self.text.focus_set()

    def _run_guide(self):
        self.save()
        text = self.controller.state[
            'vertical' if self.current_format else 'horizontal']
        vertical = bool(self.current_format)
        if self.mode == defaults.MODE_GUITAR:
            status, result = guitar_tab_guide(text, vertical)
        elif self.mode == defaults.MODE_KEYS:
            status, result = pro_keys_tab_guide(
                text, vertical, bool(self.animation_var.get()))
        else:
            status, result = vocal_tab_guide(text, vertical)
        self.controller.show_result(status, result)


class TabInputView(ttk.Frame):
    def __init__(self, parent, show_result):
        ttk.Frame.__init__(self, parent)
        self.show_result = show_result
        self.state = {
            'format': defaults.TAB_FORMAT_HORIZONTAL,
            'horizontal': '',
            'vertical': '',
        }
        self.active_index = 0
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.panes = []
        for mode, label in enumerate(MODE_LABELS):
            pane = TabInputPane(self.notebook, self, mode)
            self.panes.append(pane)
            self.notebook.add(pane, text=label)
        self.load_all()
        self.notebook.bind('<<NotebookTabChanged>>', self._tab_changed)

    def change_format(self, source, requested):
        source.save()
        self.state['format'] = requested
        self.load_all()

    def load_all(self):
        for pane in self.panes:
            pane.load()

    def _tab_changed(self, unused_event=None):
        try:
            new_index = int(self.notebook.index(self.notebook.select()))
        except Exception:
            return
        if 0 <= self.active_index < len(self.panes):
            self.panes[self.active_index].save()
        self.active_index = new_index
        self.panes[new_index].load()


class MidiLengthPane(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, padding=12)
        self.controller = controller
        note_group = ttk.LabelFrame(self, text='MIDI note', padding=8)
        note_group.pack(fill=tk.X)

        ttk.Label(note_group, text='Source track', width=16).grid(
            row=0, column=0, sticky='w', pady=3)
        self.track_var = tk.StringVar()
        self.track_combo = ttk.Combobox(
            note_group, state='readonly', width=42,
            textvariable=self.track_var)
        self.track_combo.grid(row=0, column=1, sticky='ew', pady=3)
        refresh = ttk.Button(
            note_group, text='Refresh tracks',
            command=controller.refresh_tracks)
        refresh.grid(row=0, column=2, padx=(8, 0), pady=3)
        Tooltip(refresh, 'Refresh the project track list.')

        ttk.Label(note_group, text='Difficulty', width=16).grid(
            row=1, column=0, sticky='w', pady=3)
        self.difficulty_var = tk.StringVar()
        self.difficulty_var.set('Expert')
        difficulty = ttk.Combobox(
            note_group, state='readonly', width=15,
            values=('Expert', 'Hard', 'Medium', 'Easy'),
            textvariable=self.difficulty_var)
        difficulty.grid(row=1, column=1, sticky='w', pady=3)
        difficulty.bind('<<ComboboxSelected>>', self._difficulty_changed)

        ttk.Label(note_group, text='Note type', width=16).grid(
            row=2, column=0, sticky='w', pady=3)
        self.note_type_var = tk.StringVar()
        self.note_type_var.set('non_sustains')
        modes = ttk.Frame(note_group)
        modes.grid(row=2, column=1, sticky='w', pady=3)
        for value, label in (('non_sustains', 'Non-sustains'),
                             ('sustains', 'Only sustains')):
            ttk.Radiobutton(
                modes, text=label, variable=self.note_type_var, value=value,
                command=self._note_type_changed).pack(
                    side=tk.LEFT, padx=(0, 14))

        self.option_frame = ttk.Frame(note_group)
        self.option_frame.grid(row=3, column=0, columnspan=3,
                               sticky='ew', pady=3)
        self.note_size_label = ttk.Label(
            self.option_frame, text='Note size', width=16)
        self.note_size_var = tk.StringVar()
        self.note_size_var.set('1/32')
        self.note_size_combo = ttk.Combobox(
            self.option_frame, state='readonly', width=15,
            values=('1/16', '1/32', '1/64', '1/128'),
            textvariable=self.note_size_var)
        self.gap_label = ttk.Label(
            self.option_frame, text='32nd note amount', width=16)
        self.gap_var = tk.IntVar()
        self.gap_var.set(sustain_gap_default('Expert'))
        self.gap_spin = tk.Spinbox(
            self.option_frame, from_=0, to=32, width=8,
            textvariable=self.gap_var)
        self._note_type_changed()

        adjust = ttk.Button(
            note_group, text='Adjust notes', command=controller.adjust_notes)
        adjust.grid(row=4, column=0, columnspan=3, sticky='w', pady=(8, 2))
        Tooltip(adjust, 'Use the active time selection when one exists; '
                'otherwise adjust the first MIDI item on the selected track.')
        note_group.columnconfigure(1, weight=1)

        track_group = ttk.LabelFrame(self, text='MIDI track', padding=8)
        track_group.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(track_group, text='Reference track', width=16).grid(
            row=0, column=0, sticky='w', pady=3)
        self.reference_var = tk.StringVar()
        self.reference_combo = ttk.Combobox(
            track_group, state='readonly', width=42,
            textvariable=self.reference_var)
        self.reference_combo.grid(row=0, column=1, sticky='ew', pady=3)
        ttk.Button(
            track_group, text='Resize all MIDI',
            command=controller.resize_all).grid(
                row=1, column=0, columnspan=2, sticky='w', pady=(8, 2))
        ttk.Label(
            track_group,
            text=('Legacy status: shrinking is supported; a batch that '
                  'would extend a MIDI source is safely refused.'),
            foreground='#666666', justify=tk.LEFT,
            wraplength=560).grid(
                row=2, column=0, columnspan=2, sticky='w', pady=(5, 2))
        track_group.columnconfigure(1, weight=1)

        ttk.Label(
            self,
            text=('Chunk edits are stale-checked, read back after writing, '
                  'and create one Undo point only when data changes.'),
            foreground='#666666', justify=tk.LEFT,
            wraplength=660).pack(anchor='w', fill=tk.X, pady=(12, 0))

    def _difficulty_changed(self, unused_event=None):
        self.gap_var.set(sustain_gap_default(self.difficulty_var.get()))

    def _note_type_changed(self):
        for child in self.option_frame.winfo_children():
            child.pack_forget()
        if self.note_type_var.get() == 'sustains':
            self.gap_label.pack(side=tk.LEFT)
            self.gap_spin.pack(side=tk.LEFT)
        else:
            self.note_size_label.pack(side=tk.LEFT)
            self.note_size_combo.pack(side=tk.LEFT)


class MidiPatternPane(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, padding=12)
        self.controller = controller
        source = ttk.LabelFrame(self, text='Pattern source', padding=8)
        source.pack(fill=tk.X)
        ttk.Label(source, text='Source track', width=16).grid(
            row=0, column=0, sticky='w', pady=3)
        self.track_var = tk.StringVar()
        self.track_combo = ttk.Combobox(
            source, state='readonly', width=42,
            textvariable=self.track_var)
        self.track_combo.grid(row=0, column=1, sticky='ew', pady=3)
        self.track_combo.bind('<<ComboboxSelected>>', self.update_range)
        ttk.Button(
            source, text='Refresh tracks',
            command=controller.refresh_tracks).grid(
                row=0, column=2, padx=(8, 0), pady=3)

        ttk.Label(source, text='Difficulty', width=16).grid(
            row=1, column=0, sticky='w', pady=3)
        self.difficulty_var = tk.StringVar()
        self.difficulty_var.set('All')
        self.difficulty_combo = ttk.Combobox(
            source, state='readonly', width=15,
            values=DIFFICULTY_LABELS,
            textvariable=self.difficulty_var)
        self.difficulty_combo.grid(row=1, column=1, sticky='w', pady=3)
        self.difficulty_combo.bind('<<ComboboxSelected>>', self.update_range)
        self.range_var = tk.StringVar()
        self.range_var.set('Pitch range: 0-127')
        ttk.Label(source, textvariable=self.range_var,
                  foreground='#666666').grid(
                      row=2, column=1, sticky='w', pady=(0, 3))
        source.columnconfigure(1, weight=1)

        actions = ttk.LabelFrame(self, text='Pattern actions', padding=8)
        actions.pack(fill=tk.X, pady=(12, 0))
        self.action_buttons = {}
        rows = (
            (('Set Search', controller.set_search),
             ('Set Replace', controller.set_replace)),
            (('Replace All', controller.replace_all),
             ('Fill Range', controller.fill_range)),
            (('Go Prev', lambda: controller.go_match(-1)),
             ('Go Next', lambda: controller.go_match(1)),
             ('List Search', controller.list_search)),
        )
        for row_actions in rows:
            row = ttk.Frame(actions)
            row.pack(fill=tk.X, pady=2)
            for label, callback in row_actions:
                button = ttk.Button(
                    row, text=label, command=callback, width=14)
                button.pack(side=tk.LEFT, padx=(0, 6))
                self.action_buttons[label] = button

        captured = ttk.LabelFrame(self, text='Captured patterns', padding=8)
        captured.pack(fill=tk.X, pady=(12, 0))
        self.search_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.refresh_labels()
        ttk.Label(captured, text='Search:', width=10).grid(
            row=0, column=0, sticky='nw')
        ttk.Label(captured, textvariable=self.search_var,
                  wraplength=560, justify=tk.LEFT).grid(
                      row=0, column=1, sticky='w')
        ttk.Label(captured, text='Replace:', width=10).grid(
            row=1, column=0, sticky='nw', pady=(6, 0))
        ttk.Label(captured, textvariable=self.replace_var,
                  wraplength=560, justify=tk.LEFT).grid(
                      row=1, column=1, sticky='w', pady=(6, 0))
        captured.columnconfigure(1, weight=1)

        ttk.Label(
            self,
            text=('Set Search and Set Replace capture the active time '
                  'selection. Replace All scans that selection, or the '
                  'whole first MIDI item when no selection is active.'),
            foreground='#666666', justify=tk.LEFT,
            wraplength=660).pack(anchor='w', fill=tk.X, pady=(12, 0))

    def difficulty_index(self):
        try:
            return DIFFICULTY_LABELS.index(self.difficulty_var.get())
        except ValueError:
            return 0

    def update_range(self, unused_event=None):
        track = self.controller.selected_track(self.track_combo)
        name = self.controller.track_name(track) if track is not None else ''
        lo, hi = get_pattern_pitch_range(name, self.difficulty_index())
        self.range_var.set('Pitch range: %d-%d' % (lo, hi))

    def refresh_labels(self):
        state = self.controller.pattern_state
        self.search_var.set(state.get('search_label') or 'not set')
        self.replace_var.set(state.get('replace_label') or 'not set')
        has_search = state.get('search_notes') is not None
        has_replace = state.get('replace_notes') is not None
        enabled = {
            'Replace All': has_search and has_replace,
            'Fill Range': has_replace,
            'Go Prev': has_search,
            'Go Next': has_search,
            'List Search': has_search,
        }
        for label, is_enabled in enabled.items():
            self.action_buttons[label].state(
                ['!disabled'] if is_enabled else ['disabled'])


class MidiView(ttk.Frame):
    def __init__(self, parent, show_result, host=None):
        ttk.Frame.__init__(self, parent)
        self.show_result = show_result
        self.host = host or Reaper420Host()
        self.track_records = []
        self.project_identity = None
        self.has_scanned_tracks = False
        self.pattern_state = new_pattern_state()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.length_pane = MidiLengthPane(self.notebook, self)
        self.pattern_pane = MidiPatternPane(self.notebook, self)
        self.notebook.add(self.length_pane, text='Length')
        self.notebook.add(self.pattern_pane, text='Pattern')
        self._clear_tracks('(scan when MIDI tab opens)')

    def _project_info(self):
        try:
            return self.host.project_info()
        except Exception:
            return None

    def refresh_current(self):
        info = self._project_info()
        identity = info.get('identity') if info else None
        if not self.has_scanned_tracks:
            self.refresh_tracks(show_result=False, reset_selections=True)
            return
        if (identity is not None and self.project_identity is not None and
                identity != self.project_identity):
            reset_pattern_state(self.pattern_state)
            self.pattern_pane.refresh_labels()
            self._clear_tracks('(scanning current project...)')
            self.refresh_tracks(show_result=False, reset_selections=True)

    def _clear_tracks(self, prompt=''):
        self.track_records = []
        for combo in (self.length_pane.track_combo,
                      self.length_pane.reference_combo,
                      self.pattern_pane.track_combo):
            combo['values'] = ()
            combo.set(prompt)
        self.pattern_pane.update_range()

    def refresh_tracks(self, show_result=True, reset_selections=False):
        try:
            combos = (self.length_pane.track_combo,
                      self.length_pane.reference_combo,
                      self.pattern_pane.track_combo)
            previous_tracks = ([None, None, None] if reset_selections else
                               [self.selected_track(combo)
                                for combo in combos])
            records = []
            for index in range(self.host.track_count()):
                track = self.host.get_track(index)
                if self.host.track_has_midi(track):
                    records.append((
                        index, track, self.host.track_name(track, index)))
            self.track_records = records
            values = ['%d: %s' % (index + 1, name)
                      for index, unused_track, name in records]
            for combo, previous_track in zip(combos, previous_tracks):
                combo['values'] = values
                if records:
                    selected = 0
                    for position, record in enumerate(records):
                        if record[1] == previous_track:
                            selected = position
                            break
                    combo.current(selected)
                else:
                    combo.set('(no MIDI tracks found)')
            info = self._project_info()
            self.project_identity = (
                info.get('identity') if info else self.project_identity)
            self.has_scanned_tracks = True
            self.pattern_pane.update_range()
            if show_result:
                self.show_result(
                    'MIDI tracks refreshed: %d MIDI track%s found.' %
                    (len(records), '' if len(records) == 1 else 's'),
                    'Only tracks containing at least one MIDI item are shown.')
        except Exception as exc:
            self.has_scanned_tracks = False
            self._clear_tracks('(MIDI track scan failed)')
            if show_result:
                self.show_result('MIDI track refresh failed', str(exc))

    def selected_track(self, combo):
        position = combo.current()
        if 0 <= position < len(self.track_records):
            return self.track_records[position][1]
        return None

    def track_name(self, track):
        for unused_index, candidate, name in self.track_records:
            if candidate == track:
                return name
        return ''

    def _require_track(self, combo):
        track = self.selected_track(combo)
        if track is None:
            raise ValueError('Refresh tracks and select a MIDI source track.')
        return track

    def _run(self, action_name, callback):
        try:
            status, report = callback()
            self.show_result(status, report)
            self.pattern_pane.refresh_labels()
        except Exception as exc:
            self.show_result(
                '%s could not complete' % action_name,
                'The MIDI action stopped safely. No unverified project '
                'change was accepted.\n\n%s' % exc)

    def adjust_notes(self):
        pane = self.length_pane
        denominator = int(pane.note_size_var.get().split('/')[1])
        self._run('Adjust notes', lambda: adjust_midi_note_lengths(
            self.host, self._require_track(pane.track_combo),
            pane.difficulty_var.get(), pane.note_type_var.get(),
            denominator, int(pane.gap_var.get())))

    def resize_all(self):
        self._run('Resize all MIDI', lambda: resize_all_midi_items(
            self.host, self._require_track(self.length_pane.reference_combo)))

    def _pattern_args(self):
        pane = self.pattern_pane
        return (self.host, self._require_track(pane.track_combo),
                pane.difficulty_index(), self.pattern_state)

    def set_search(self):
        self._run('Set Search', lambda: capture_pattern(
            *(self._pattern_args() + ('search',))))

    def set_replace(self):
        self._run('Set Replace', lambda: capture_pattern(
            *(self._pattern_args() + ('replace',))))

    def replace_all(self):
        self._run('Replace All', lambda: replace_all(*self._pattern_args()))

    def fill_range(self):
        self._run('Fill Range', lambda: fill_range(*self._pattern_args()))

    def list_search(self):
        self._run('List Search', lambda: list_matches(*self._pattern_args()))

    def go_match(self, direction):
        self._run('Go to match', lambda: go_to_match(
            *(self._pattern_args() + (direction,))))
