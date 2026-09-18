"""REAPER action entry point for Rock Band General Helper VKR.

Modern counterpart: rock_band_general_helper_vkr.lua
Python 2.7 compatible.
"""

from __future__ import print_function

import os
import sys


def _project_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def main():
    root = _project_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    # REAPER 4.20's embedded Python module may not provide sys.argv, while
    # Tk 8.5 consults it during Tk() construction.
    if not hasattr(sys, 'argv'):
        sys.argv = [os.path.join(root, 'rock_band_general_helper_vkr.py')]

    # A second persistent Python ReaScript can invalidate ctypes and wrapper
    # objects retained by the first one in REAPER's embedded interpreter. Do
    # this check before importing any project or REAPER-facing modules.
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
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
            'same time.\n\nClose the standalone Preview, open the General '
            'Helper, then choose Venue > Preview > Open separate window.',
            parent=existing)
        try:
            existing.lift()
        except tk.TclError:
            pass
        return
    from rock_band_general_helper_vkr.ui import run
    run()


if __name__ == '__main__':
    main()
