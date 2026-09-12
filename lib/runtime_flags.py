"""Process-wide feature and diagnostic flags.

These defaults are intentionally code-controlled for now. A future Settings
view can call the setters without changing the lower-level feature modules.

Python 2.7 compatible.
"""

from __future__ import unicode_literals


# Keep False for normal use and releases. Temporarily switch to True while
# collecting bounded MIDI write/read-back diagnostics during development.
DEVELOPMENT_MODE = False

# Allow a narrowly checked semantic fallback when REAPER rewrites only the
# redundant readable header of an extended MIDI event. Keep this separate from
# DEVELOPMENT_MODE: diagnostics control error detail, while this controls which
# verified read-backs may be accepted. A future Settings view can expose it.
SEMANTIC_MIDI_WRITE_VERIFICATION = True


def set_development_mode(enabled):
    global DEVELOPMENT_MODE
    DEVELOPMENT_MODE = bool(enabled)


def development_mode_enabled():
    return DEVELOPMENT_MODE


def set_semantic_midi_write_verification(enabled):
    global SEMANTIC_MIDI_WRITE_VERIFICATION
    SEMANTIC_MIDI_WRITE_VERIFICATION = bool(enabled)


def semantic_midi_write_verification_enabled():
    return SEMANTIC_MIDI_WRITE_VERIFICATION
