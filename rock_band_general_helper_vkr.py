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
    from rock_band_general_helper_vkr.ui import run
    run()


if __name__ == '__main__':
    main()

