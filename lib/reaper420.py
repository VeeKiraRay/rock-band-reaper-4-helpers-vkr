"""Small read-only REAPER 4.20 host adapter.

Keep calls to the legacy ``reaper_python`` module at the edge of the
application.  Feature code can then be tested on a normal Python install by
passing a fake host with the same methods.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os
import re

try:
    import reaper_python as _reaper
    REAPER_IMPORT_ERROR = None
except ImportError as exc:
    _reaper = None
    REAPER_IMPORT_ERROR = exc


ITEM_CHUNK_CAPACITY = 16 * 1024 * 1024
ITEM_CHUNK_MARGIN = 1024
try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)


class Reaper420Error(Exception):
    pass


def _safe_text(value):
    try:
        return value if isinstance(value, str) else str(value)
    except Exception:
        return '<unprintable value>'


def _display_text(value):
    """Return UI-safe text on both Python 2 and Python 3."""
    try:
        text_type = unicode
    except NameError:
        text_type = str
    if isinstance(value, text_type):
        return value
    if isinstance(value, bytes):
        for encoding in ('mbcs', 'utf-8', 'latin-1'):
            try:
                return value.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                pass
    return text_type(value)


class Reaper420Host(object):
    """REAPER 4.20 API subset verified by compatibility probes."""

    def __init__(self, api=None):
        self.api = api if api is not None else _reaper

    def require(self):
        if self.api is None:
            detail = _safe_text(REAPER_IMPORT_ERROR or 'module unavailable')
            raise Reaper420Error(
                'This analysis must run inside REAPER: reaper_python could '
                'not be imported (%s).' % detail)

    def track_count(self):
        self.require()
        return int(self.api.RPR_CountTracks(0))

    def project_info(self):
        """Return stable active-project identity and a display name.

        EnumProjects was verified on REAPER 4.20. The project handle detects
        tab switches, while the returned path supplies the name because that
        release does not export GetProjectName.
        """
        self.require()
        result = self.api.RPR_EnumProjects(-1, '', 4096)
        if not isinstance(result, (tuple, list)) or len(result) < 3:
            raise Reaper420Error(
                'EnumProjects returned an unexpected value: %s' %
                _safe_text(repr(result)))
        handle = _safe_text(result[0])
        path = _display_text(result[2]) if result[2] else ''
        filename = os.path.basename(path)
        name = os.path.splitext(filename)[0] if filename else 'Unsaved project'
        return {'identity': handle, 'path': path, 'name': name}

    def get_track(self, index):
        self.require()
        return self.api.RPR_GetTrack(0, int(index))

    def track_name(self, track, index):
        self.require()
        result = self.api.RPR_GetSetMediaTrackInfo_String(
            track, 'P_NAME', '', False)
        if isinstance(result, (tuple, list)) and len(result) > 3:
            value = result[3]
        else:
            value = ''
        value = _safe_text(value) if value else ''
        return value or '(unnamed track %d)' % (int(index) + 1)

    def track_muted(self, track):
        self.require()
        return float(self.api.RPR_GetMediaTrackInfo_Value(
            track, 'B_MUTE')) > 0.5

    def item_count(self, track):
        self.require()
        return int(self.api.RPR_CountTrackMediaItems(track))

    def get_item(self, track, index):
        self.require()
        return self.api.RPR_GetTrackMediaItem(track, int(index))

    def project_item_count(self):
        self.require()
        return int(self.api.RPR_CountMediaItems(0))

    def get_project_item(self, index):
        self.require()
        return self.api.RPR_GetMediaItem(0, int(index))

    def item_position(self, item):
        self.require()
        return float(self.api.RPR_GetMediaItemInfo_Value(item, 'D_POSITION'))

    def item_length(self, item):
        self.require()
        return float(self.api.RPR_GetMediaItemInfo_Value(item, 'D_LENGTH'))

    def active_take(self, item):
        self.require()
        return self.api.RPR_GetActiveTake(item)

    def take_start_offset(self, take):
        self.require()
        return float(self.api.RPR_GetMediaItemTakeInfo_Value(
            take, 'D_STARTOFFS'))

    def take_play_rate(self, take):
        self.require()
        return float(self.api.RPR_GetMediaItemTakeInfo_Value(
            take, 'D_PLAYRATE'))

    def time_to_qn(self, seconds):
        self.require()
        return float(self.api.RPR_TimeMap2_timeToQN(0, float(seconds)))

    def qn_to_time(self, quarter_notes):
        self.require()
        return float(self.api.RPR_TimeMap2_QNToTime(
            0, float(quarter_notes)))

    def measure_at(self, seconds):
        """Return REAPER's one-based measure number for project time."""
        self.require()
        formatter = getattr(self.api, 'RPR_format_timestr_pos', None)
        if formatter is None:
            return None
        try:
            result = formatter(float(seconds), '', 64, 1)
        except Exception:
            return None
        values = result if isinstance(result, (tuple, list)) else (result,)
        for value in values:
            if not isinstance(value, STRING_TYPES):
                continue
            match = re.match(r'^\s*(\d+)\.', value)
            if match:
                return int(match.group(1))
        return None

    def read_item_chunk(self, item):
        self.require()
        result = self.api.RPR_GetSetItemState(
            item, '', ITEM_CHUNK_CAPACITY)
        if not isinstance(result, (tuple, list)) or len(result) < 3:
            raise Reaper420Error(
                'GetSetItemState returned an unexpected value: %s' %
                _safe_text(repr(result)))
        if not result[0]:
            raise Reaper420Error('GetSetItemState reported read failure.')
        chunk = result[2]
        if not isinstance(chunk, str):
            raise Reaper420Error('Item chunk is not a Python string.')
        if len(chunk) >= ITEM_CHUNK_CAPACITY - ITEM_CHUNK_MARGIN:
            raise Reaper420Error(
                'Item chunk may be truncated at %d bytes; refusing to '
                'analyse it.' % len(chunk))
        return chunk

    def write_item_chunk(self, item, chunk):
        self.require()
        capacity = max(len(chunk) + ITEM_CHUNK_MARGIN, 65536)
        result = self.api.RPR_GetSetItemState(item, chunk, capacity)
        if not isinstance(result, (tuple, list)) or not result:
            raise Reaper420Error(
                'GetSetItemState write returned an unexpected value: %s' %
                _safe_text(repr(result)))
        if not result[0]:
            raise Reaper420Error('GetSetItemState reported write failure.')

    def begin_undo(self):
        self.require()
        self.api.RPR_Undo_BeginBlock2(0)

    def end_undo(self, description):
        self.require()
        self.api.RPR_Undo_EndBlock2(0, description, -1)

    def update_arrange(self):
        self.require()
        self.api.RPR_UpdateArrange()
