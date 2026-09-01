"""Tk rendering for General Helper Tab Input and future MIDI tabs.

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
from . import defaults
from .actions_guitar_guide import add_empty_note, guitar_tab_guide
from .actions_keys_guides import pro_keys_tab_guide, vocal_tab_guide


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

