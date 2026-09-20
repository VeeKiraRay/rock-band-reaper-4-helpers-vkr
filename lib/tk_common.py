"""Small Tkinter compatibility helpers shared by REAPER 4.20 windows.

Python 2.7 and Python 3 compatible.
"""

from __future__ import unicode_literals

import os
import time

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk


PALETTE = {
    'window': '#1e2228',
    'panel': '#252a32',
    'input': '#171a1f',
    'border': '#414854',
    'accent': '#3478b8',
    'accent_active': '#438acb',
    'text': '#eef1f5',
    'muted': '#aab2bf',
    'disabled': '#747d8a',
    'selection': '#285f91',
    'warning': '#e0a84f',
    'error': '#ef7777',
}


def window_icon_path():
    """Return the distributable Windows icon used by helper windows."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(
        project_root, 'resources', 'icon', 'rock_blue.ico')


def _request_dark_windows_title_bar(window):
    """Ask supported Windows versions for a native dark title bar.

    This is deliberately best-effort. Older Windows/DWM versions, unusual Tk
    window handles, and non-Windows platforms retain their system title bar.
    """
    if os.name != 'nt':
        return False
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.c_void_p(int(window.winfo_id()))
        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        parent = user32.GetParent(hwnd)
        if parent:
            hwnd = ctypes.c_void_p(parent)

        enabled = ctypes.c_int(1)
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        # Attribute 20 is current; 19 is used by an earlier Windows 10 build.
        for attribute in (20, 19):
            result = dwm.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(enabled),
                ctypes.sizeof(enabled))
            if result == 0:
                return True
    except Exception:
        pass
    return False


def apply_window_branding(window):
    """Apply the packaged icon and request native dark window chrome."""
    icon_path = window_icon_path()
    if os.path.isfile(icon_path):
        try:
            window.iconbitmap(icon_path)
        except tk.TclError:
            pass
        try:
            # Also make subsequently-created Toplevel windows inherit it.
            window.iconbitmap(default=icon_path)
        except (TypeError, tk.TclError):
            pass
    try:
        window.after_idle(
            lambda: _request_dark_windows_title_bar(window))
    except tk.TclError:
        pass


def apply_theme(root):
    """Apply the shared dependency-free dark theme to a Tk interpreter."""
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except tk.TclError:
        # Keep the window usable on an unusual Tk build without clam.
        pass

    colours = PALETTE
    root.configure(background=colours['window'])
    style.configure('.',
                    background=colours['window'],
                    foreground=colours['text'],
                    bordercolor=colours['border'],
                    lightcolor=colours['border'],
                    darkcolor=colours['border'])
    style.configure('TFrame', background=colours['window'])
    style.configure('TLabel', background=colours['window'],
                    foreground=colours['text'])
    style.configure('TLabelframe', background=colours['window'],
                    bordercolor=colours['border'])
    style.configure('TLabelframe.Label', background=colours['window'],
                    foreground=colours['text'])
    style.configure('TButton', background=colours['accent'],
                    foreground=colours['text'], padding=(8, 4),
                    bordercolor=colours['border'])
    style.map('TButton',
              background=[('disabled', colours['panel']),
                          ('pressed', colours['selection']),
                          ('active', colours['accent_active'])],
              foreground=[('disabled', colours['disabled'])])
    style.configure('TCheckbutton', background=colours['window'],
                    foreground=colours['text'], indicatorsize=16,
                    indicatormargin=(2, 2, 7, 2), padding=(2, 2))
    style.configure('TRadiobutton', background=colours['window'],
                    foreground=colours['text'], indicatorsize=16,
                    indicatormargin=(2, 2, 7, 2), padding=(2, 2))
    for widget_style in ('TCheckbutton', 'TRadiobutton'):
        style.map(widget_style,
                  background=[('active', colours['panel'])],
                  foreground=[('disabled', colours['disabled'])],
                  indicatorbackground=[
                      ('disabled', colours['panel']),
                      ('selected', colours['accent']),
                      ('active', colours['border']),
                      ('!selected', colours['input'])],
                  indicatorforeground=[
                      ('disabled', colours['disabled']),
                      ('selected', colours['text'])],
                  upperbordercolor=[
                      ('selected', colours['accent_active']),
                      ('!selected', colours['border'])],
                  lowerbordercolor=[
                      ('selected', colours['selection']),
                      ('!selected', colours['border'])])
    style.configure('TNotebook', background=colours['window'],
                    bordercolor=colours['border'], tabmargins=(2, 2, 2, 0))
    style.configure('TNotebook.Tab', background=colours['panel'],
                    foreground=colours['muted'], padding=(9, 5))
    style.map('TNotebook.Tab',
              background=[('selected', colours['accent']),
                          ('active', colours['border'])],
              foreground=[('selected', colours['text']),
                          ('active', colours['text'])])
    style.configure('TEntry', fieldbackground=colours['input'],
                    foreground=colours['text'], insertcolor=colours['text'])
    style.configure('TCombobox', fieldbackground=colours['input'],
                    background=colours['panel'], foreground=colours['text'],
                    arrowcolor=colours['text'])
    style.map('TCombobox',
              fieldbackground=[('readonly', colours['input']),
                               ('disabled', colours['panel'])],
              foreground=[('readonly', colours['text']),
                          ('disabled', colours['disabled'])])
    style.configure('TScrollbar', background=colours['panel'],
                    troughcolor=colours['input'],
                    bordercolor=colours['border'],
                    arrowcolor=colours['text'])

    # Option database entries cover plain Tk widgets created after this call.
    options = {
        '*Canvas.background': colours['window'],
        '*Canvas.highlightBackground': colours['border'],
        '*Frame.background': colours['panel'],
        '*Label.background': colours['panel'],
        '*Label.foreground': colours['text'],
        '*Button.background': colours['accent'],
        '*Button.foreground': colours['text'],
        '*Button.activeBackground': colours['accent_active'],
        '*Button.activeForeground': colours['text'],
        '*Listbox.background': colours['input'],
        '*Listbox.foreground': colours['text'],
        '*Listbox.selectBackground': colours['selection'],
        '*Listbox.selectForeground': colours['text'],
        '*Text.background': colours['input'],
        '*Text.foreground': colours['text'],
        '*Text.insertBackground': colours['text'],
        '*Text.selectBackground': colours['selection'],
        '*Text.selectForeground': colours['text'],
        '*Spinbox.background': colours['input'],
        '*Spinbox.foreground': colours['text'],
        '*Spinbox.buttonBackground': colours['panel'],
        '*Spinbox.disabledBackground': colours['panel'],
        '*Spinbox.disabledForeground': colours['disabled'],
        '*Spinbox.readonlyBackground': colours['input'],
        '*Spinbox.insertBackground': colours['text'],
        '*TCombobox*Listbox.background': colours['input'],
        '*TCombobox*Listbox.foreground': colours['text'],
        '*TCombobox*Listbox.selectBackground': colours['selection'],
        '*TCombobox*Listbox.selectForeground': colours['text'],
    }
    for pattern, value in options.items():
        root.option_add(pattern, value)
    try:
        root.update_idletasks()
    except tk.TclError:
        pass
    return style


class AutoVerticalScrolledFrame(ttk.Frame):
    """A width-aware page that shows a vertical scrollbar only as needed."""

    def __init__(self, parent, **options):
        ttk.Frame.__init__(self, parent, **options)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.content = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(
            (0, 0), window=self.content, anchor='nw')
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.content.bind('<Configure>', self._content_resized)
        self.canvas.bind('<Configure>', self._canvas_resized)

    def _content_resized(self, unused_event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self._update_scrollbar()

    def _canvas_resized(self, event):
        self.canvas.itemconfigure(self._window, width=max(1, event.width))
        self.after_idle(self._update_scrollbar)

    def _update_scrollbar(self):
        try:
            needed = self.content.winfo_reqheight() > self.canvas.winfo_height()
        except tk.TclError:
            return
        if needed:
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.grid(row=0, column=1, sticky='ns')
        elif self.scrollbar.winfo_ismapped():
            self.canvas.yview_moveto(0.0)
            self.scrollbar.grid_remove()


class PinnedTabNotebook(ttk.Notebook):
    """Notebook with a fixed tab row and one scrollable content page per tab."""

    def add_scrolled_page(self, text):
        page = AutoVerticalScrolledFrame(self)
        ttk.Notebook.add(self, page, text=text)
        return page.content, page


def make_labeled_spinbox(parent, variable, low, high, suffix, width=7):
    """Return a compact (container, Spinbox) with an adjacent unit label."""
    field = ttk.Frame(parent)
    spin = tk.Spinbox(
        field, from_=low, to=high, width=width, textvariable=variable,
        justify=tk.CENTER, background=PALETTE['input'],
        foreground=PALETTE['text'], buttonbackground=PALETTE['panel'],
        disabledbackground=PALETTE['panel'],
        disabledforeground=PALETTE['disabled'],
        readonlybackground=PALETTE['input'],
        insertbackground=PALETTE['text'])
    spin.pack(side=tk.LEFT)
    ttk.Label(field, text=suffix).pack(side=tk.LEFT, padx=(8, 0))
    return field, spin


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


class ResponsiveLabel(ttk.Label):
    """A wrapped label whose line width follows its containing widget."""

    def __init__(self, master, **options):
        self.wrap_padding = int(options.pop('wrap_padding', 24))
        requested = options.get('wraplength')
        self.wrap_limit = int(requested) if requested else None
        ttk.Label.__init__(self, master, **options)
        if self.wrap_limit is not None:
            master.bind('<Configure>', self._container_resized, add='+')

    def _container_resized(self, event):
        available = max(120, int(event.width) - self.wrap_padding)
        try:
            self.configure(wraplength=min(self.wrap_limit, available))
        except tk.TclError:
            pass


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
                padx=8, pady=8, background=PALETTE['panel'],
                highlightbackground=PALETTE['border'])
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
                foreground='#202020',
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
    options.setdefault('background', PALETTE['input'])
    options.setdefault('foreground', PALETTE['text'])
    options.setdefault('insertbackground', PALETTE['text'])
    options.setdefault('selectbackground', PALETTE['selection'])
    options.setdefault('selectforeground', PALETTE['text'])
    options.setdefault('relief', tk.FLAT)
    options.setdefault('borderwidth', 1)
    options.setdefault('highlightthickness', 1)
    options.setdefault('highlightbackground', PALETTE['border'])
    options.setdefault('highlightcolor', PALETTE['accent'])
    text = tk.Text(container, **options)
    scrollbar = ttk.Scrollbar(
        container, orient=tk.VERTICAL, command=text.yview)

    def update_scrollbar(first, last):
        scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if scrollbar.winfo_ismapped():
                scrollbar.grid_remove()
        elif not scrollbar.winfo_ismapped():
            scrollbar.grid()

    text.configure(yscrollcommand=update_scrollbar)
    text.grid(row=0, column=0, sticky='nsew')
    scrollbar.grid(row=0, column=1, sticky='ns')
    container.rowconfigure(0, weight=1)
    container.columnconfigure(0, weight=1)
    return container, text
