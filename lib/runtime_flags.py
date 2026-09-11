"""Process-wide feature and diagnostic flags.

These defaults are intentionally code-controlled for now. A future Settings
view can call the setters without changing the lower-level feature modules.

Python 2.7 compatible.
"""

from __future__ import unicode_literals


DEVELOPMENT_MODE = False


def set_development_mode(enabled):
    global DEVELOPMENT_MODE
    DEVELOPMENT_MODE = bool(enabled)


def development_mode_enabled():
    return DEVELOPMENT_MODE
