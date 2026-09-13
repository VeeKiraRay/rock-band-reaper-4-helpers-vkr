"""Small Tkinter compatibility helpers shared by REAPER 4.20 windows.

Python 2.7 and Python 3 compatible.
"""

from __future__ import unicode_literals

import time

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk


def install_callback_builtins_guard(tk_module=None):
    """Keep Tk callbacks usable when an embedded host clears built-ins.

    Some REAPER/Python combinations retain Tk's native event loop after the
    ReaScript execution namespace has been cleaned.  Tkinter's callback
    wrapper then fails before reaching our callback because even ``len`` and
    ``SystemExit`` are missing from the built-ins mapping captured when the
    module was imported.  Restore that exact mapping at the callback boundary.

    Normal desktop Python and the REAPER 4.20/Python 2 target are unaffected;
    installing the guard more than once is harmless.
    """
    module = tk_module or tk
    wrapper = module.CallWrapper
    if getattr(wrapper, '_reaper_builtins_guard', False):
        return

    original_call = wrapper.__call__
    mapping = getattr(original_call, '__builtins__', None)
    if mapping is None:
        globals_dict = getattr(original_call, 'func_globals', {})
        mapping = globals_dict.get('__builtins__')
    if hasattr(mapping, '__dict__'):
        mapping = mapping.__dict__
    if not hasattr(mapping, 'update'):
        return
    preserved = dict(mapping)

    # Everything needed before ``original_call`` begins is captured in the
    # closure. No built-in name lookup occurs before the mapping is restored.
    def guarded_call(self, *args):
        mapping.update(preserved)
        return original_call(self, *args)

    wrapper.__call__ = guarded_call
    wrapper._reaper_builtins_guard = True


def run_blocking_event_loop(root, tk_module=None, poll_seconds=0.01):
    """Run Tk without relying on ``_tkinter.tkapp.mainloop``.

    REAPER's Python 3.14 embedding can begin invalidating the native Tk main
    loop while the ReaScript is still using it. Keeping this small Python
    frame active avoids that teardown boundary. It remains intentionally
    blocking, matching the accepted REAPER 4.20/Tk behavior.
    """
    module = tk_module or tk
    update = root.update
    exists = root.winfo_exists
    sleep = time.sleep
    tcl_error = module.TclError
    while True:
        try:
            update()
            if not exists():
                break
        except tcl_error:
            break
        sleep(poll_seconds)


def replace_text(widget, value):
    widget.delete('1.0', tk.END)
    widget.insert('1.0', value)


def read_text(widget):
    return widget.get('1.0', 'end-1c')


class Tooltip(object):
    """A conservative hover tooltip that works with Tk 8.5."""

    def __init__(self, widget, text, delay_ms=450, panel=True):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.panel = bool(panel)
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
        self.window = tk.Toplevel(self.widget)
        self.window.withdraw()
        self.window.wm_overrideredirect(True)
        if self.panel:
            try:
                self.window.wm_attributes('-topmost', True)
            except tk.TclError:
                pass
            body = tk.Frame(
                self.window, relief='solid', borderwidth=1,
                padx=8, pady=8)
            body.pack(fill=tk.BOTH, expand=True)
            label = ttk.Label(
                body, text=self.text, justify=tk.LEFT,
                anchor='w', wraplength=520)
            label.pack(fill=tk.BOTH, expand=True)
        else:
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
        self.window.update_idletasks()
        if self.panel:
            anchor_x = self.widget.winfo_rootx()
            x = anchor_x + self.widget.winfo_width() + 6
            y = self.widget.winfo_rooty()
            if x + self.window.winfo_reqwidth() > self.widget.winfo_screenwidth():
                x = max(0, anchor_x - self.window.winfo_reqwidth() - 6)
        else:
            x = self.widget.winfo_rootx() + 16
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        if y + self.window.winfo_reqheight() > self.widget.winfo_screenheight():
            y = max(0, self.widget.winfo_screenheight() -
                    self.window.winfo_reqheight())
        self.window.wm_geometry('+%d+%d' % (x, y))
        self.window.deiconify()
        self.window.lift()

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
