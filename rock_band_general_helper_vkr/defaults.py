"""Initial General Helper state.

Modern counterpart:
rock_band_general_helper_vkr/defaults.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals


WINDOW_TITLE = 'Rock Band General Helper VKR - REAPER 4.20 WIP'
WINDOW_GEOMETRY = '780x620'

TAB_FORMAT_HORIZONTAL = 0
TAB_FORMAT_VERTICAL = 1

MODE_GUITAR = 0
MODE_KEYS = 1
MODE_VOCAL = 2

DEFAULT_STATUS = 'Ready.'

FORMAT_TOOLTIP = (
    'Horizontal: one event per line, low E to high e. Example: '
    'x 3 2 0 1 0. Blank lines separate phrases.\n\n'
    'Vertical: six rows in standard ASCII-tab order, high e to low E. '
    'Columns are events; an all-dash column separates phrases.')

ADD_NOTE_TOOLTIP = (
    'Append an empty six-string event. Horizontal mode adds one line; '
    'vertical mode pads the six rows and adds one column.')

MODE_TOOLTIPS = {
    MODE_GUITAR: (
        'Convert the tab into a Rock Band five-lane gem reference. '
        'Nothing is written to the project.'),
    MODE_KEYS: (
        'Shift the tab pitches into C2-C4 and suggest a Pro Keys lane '
        'window. Animation mode uses the complete C2-C4 range.'),
    MODE_VOCAL: (
        'Shift the tab pitches into the C1-C5 vocal range and report '
        'notes that still do not fit.'),
}
