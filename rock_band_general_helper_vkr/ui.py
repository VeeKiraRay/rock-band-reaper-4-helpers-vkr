"""Main Tk shell for the REAPER 4.20 General Helper.

Modern counterpart:
rock_band_general_helper_vkr/ui.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import (
    install_callback_builtins_guard,
    make_scrolled_text,
    replace_text,
    run_blocking_event_loop,
)
from . import defaults
from .ui_difficulty import DifficultyView
from .ui_midi import MidiView, TabInputView
from .ui_metadata import MetadataView
from .ui_workflow import WorkflowView


MAIN_TABS = ('General', 'Difficulty', 'Tab Input', 'MIDI', 'Venue', 'Metadata')


class GeneralHelperApp(object):
    def __init__(self, root):
        self.root = root
        root.title(defaults.WINDOW_TITLE)
        root.geometry(defaults.WINDOW_GEOMETRY)
        root.minsize(620, 520)

        outer = ttk.Frame(root, padding=8)
        outer.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.tabs = {}
        for label in MAIN_TABS:
            frame = ttk.Frame(self.notebook)
            self.tabs[label] = frame
            self.notebook.add(frame, text=label)

        self.workflow_view = WorkflowView(
            self.tabs['General'], self.show_result)
        self.workflow_view.pack(fill=tk.BOTH, expand=True)
        tab_input = TabInputView(
            self.tabs['Tab Input'], self.show_result)
        tab_input.pack(fill=tk.BOTH, expand=True)
        self.midi_view = MidiView(self.tabs['MIDI'], self.show_result)
        self.midi_view.pack(fill=tk.BOTH, expand=True)
        self.difficulty_view = DifficultyView(
            self.tabs['Difficulty'], self.show_result)
        self.difficulty_view.pack(fill=tk.BOTH, expand=True)
        self.metadata_view = MetadataView(
            self.tabs['Metadata'], self.show_result)
        self.metadata_view.pack(fill=tk.BOTH, expand=True)

        for label in MAIN_TABS:
            if label in ('General', 'Difficulty', 'Tab Input', 'MIDI',
                         'Metadata'):
                continue
            placeholder = ttk.Label(
                self.tabs[label],
                text='%s is planned for a later implementation slice.' % label,
                anchor='center')
            placeholder.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        result_group = ttk.LabelFrame(outer, text='Result')
        result_group.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        result_container, self.result_text = make_scrolled_text(
            result_group,
            height=10,
            wrap=tk.WORD,
            font=('Courier New', 9))
        result_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.result_text.configure(state=tk.DISABLED)

        bottom = ttk.Frame(outer)
        bottom.pack(fill=tk.X, pady=(6, 0))
        self.status_var = tk.StringVar()
        self.status_var.set(defaults.DEFAULT_STATUS)
        ttk.Label(bottom, textvariable=self.status_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bottom, text='Copy result', command=self.copy_result).pack(
            side=tk.RIGHT)
        self.topmost_var = tk.BooleanVar()
        self.topmost_var.set(True)
        self.topmost_check = ttk.Checkbutton(
            bottom,
            text='Always on top',
            variable=self.topmost_var,
            command=self.apply_topmost)
        self.topmost_check.pack(side=tk.RIGHT, padx=(0, 10))

        self.notebook.select(self.tabs['Tab Input'])
        self.notebook.bind('<<NotebookTabChanged>>', self._main_tab_changed)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after_idle(self.apply_topmost)

    def show_result(self, status, result):
        self.status_var.set(status)
        self.result_text.configure(state=tk.NORMAL)
        replace_text(self.result_text, result)
        self.result_text.configure(state=tk.DISABLED)

    def _main_tab_changed(self, unused_event=None):
        try:
            selected = self.notebook.tab(self.notebook.select(), 'text')
        except Exception:
            return
        if selected == 'General':
            self.workflow_view.refresh_current()
        elif selected == 'Metadata':
            self.metadata_view.refresh_current()
        elif selected == 'Difficulty':
            self.difficulty_view.refresh_current()
        elif selected == 'MIDI':
            self.midi_view.refresh_current()

    def copy_result(self):
        value = self.result_text.get('1.0', 'end-1c')
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status_var.set('Result copied to the clipboard.')

    def apply_topmost(self):
        """Keep the external Tk window visible while working in REAPER."""
        try:
            self.root.wm_attributes(
                '-topmost', 1 if self.topmost_var.get() else 0)
        except Exception:
            # Keep an unsupported window-manager option from breaking the
            # helper on a non-Windows or unusually old Tk installation.
            self.topmost_var.set(False)
            try:
                self.topmost_check.configure(state=tk.DISABLED)
            except Exception:
                pass

    def close(self):
        self.root.destroy()


def run():
    install_callback_builtins_guard(tk)
    root = tk.Tk()
    GeneralHelperApp(root)
    run_blocking_event_loop(root, tk)
