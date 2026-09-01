"""Small Tkinter compatibility helpers shared by REAPER 4.20 windows.

Python 2.7 and Python 3 compatible.
"""

from __future__ import unicode_literals

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk


def replace_text(widget, value):
    widget.delete('1.0', tk.END)
    widget.insert('1.0', value)


def read_text(widget):
    return widget.get('1.0', 'end-1c')


class Tooltip(object):
    """A conservative hover tooltip that works with Tk 8.5."""

    def __init__(self, widget, text, delay_ms=450):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.after_id = None
        self.window = None
        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')

    def _schedule(self, unused_event=None):
        self._cancel()
        self.after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _show(self):
        self.after_id = None
        if self.window is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry('+%d+%d' % (x, y))
        label = tk.Label(
            self.window,
            text=self.text,
            justify=tk.LEFT,
            anchor='w',
            background='#ffffe0',
            relief=tk.SOLID,
            borderwidth=1,
            padx=6,
            pady=4,
            wraplength=520)
        label.pack()

    def _hide(self, unused_event=None):
        self._cancel()
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None


def make_scrolled_text(parent, **options):
    """Return (container, Text) without relying on ScrolledText variants."""
    container = ttk.Frame(parent)
    text = tk.Text(container, **options)
    scrollbar = ttk.Scrollbar(
        container, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    return container, text

