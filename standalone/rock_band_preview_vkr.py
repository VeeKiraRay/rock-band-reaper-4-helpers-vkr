"""Optional standalone REAPER action for isolated Venue Preview testing.

Python 2.7 compatible.
"""

from __future__ import print_function

import os
import sys


def _project_root():
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        return os.getcwd()


def main():
    root_path = _project_root()
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    if not hasattr(sys, 'argv'):
        sys.argv = [os.path.join(
            root_path, 'standalone', 'rock_band_preview_vkr.py')]

    try:
        import Tkinter as tk
        import ttk
    except ImportError:
        import tkinter as tk
        from tkinter import ttk

    existing = getattr(tk, '_default_root', None)
    try:
        existing_alive = existing is not None and existing.winfo_exists()
    except tk.TclError:
        existing_alive = False
    if existing_alive:
        try:
            import tkMessageBox as messagebox
        except ImportError:
            from tkinter import messagebox
        messagebox.showwarning(
            'Rock Band helper already open',
            'REAPER cannot safely run two persistent Python actions at the '
            'same time.\n\nTo use Preview beside the General Helper, close '
            'this action and choose Venue > Preview > Open separate window '
            'inside the General Helper.',
            parent=existing)
        try:
            existing.lift()
        except tk.TclError:
            pass
        return

    from lib.reaper420 import Reaper420Host
    from lib.tk_common import (
        AutoVerticalScrolledFrame, apply_theme, apply_window_branding,
        install_callback_builtins_guard, run_blocking_event_loop,
    )
    from rock_band_general_helper_vkr.ui_venue_preview_tab import (
        VenueTimelinePreviewView,
    )
    from rock_band_general_helper_vkr.ui_venue_players import (
        VenueActivePlayersRow,
    )

    install_callback_builtins_guard(tk)
    root = tk.Tk()
    apply_theme(root)
    root.title('Rock Band Venue Preview VKR - REAPER 4.20 WIP')
    apply_window_branding(root)
    root.geometry('740x720')
    root.minsize(560, 420)

    host = Reaper420Host()
    bottom = ttk.Frame(root, padding=(10, 4, 10, 8))
    bottom.pack(side=tk.BOTTOM, fill=tk.X)
    topmost = tk.BooleanVar(); topmost.set(True)

    def apply_topmost():
        try:
            root.wm_attributes('-topmost', 1 if topmost.get() else 0)
        except Exception:
            topmost.set(False)
            topmost_check.configure(state=tk.DISABLED)

    topmost_check = ttk.Checkbutton(
        bottom, text='Always on top', variable=topmost,
        command=apply_topmost)
    topmost_check.pack(side=tk.RIGHT)

    players_row = VenueActivePlayersRow(root, host=host)
    players_row.pack(side=tk.BOTTOM, fill=tk.X)
    page = AutoVerticalScrolledFrame(root)
    page.pack(fill=tk.BOTH, expand=True)
    view = VenueTimelinePreviewView(page.content, host=host)
    view.pack(fill=tk.X)

    def close():
        view.stop()
        players_row.stop()
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    root.after_idle(apply_topmost)
    players_row.start()
    view.start()
    run_blocking_event_loop(root, tk)


if __name__ == '__main__':
    main()
