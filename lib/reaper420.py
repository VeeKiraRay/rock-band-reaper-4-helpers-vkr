"""Small read-only REAPER 4.20 host adapter.

Keep calls to the legacy ``reaper_python`` module at the edge of the
application.  Feature code can then be tested on a normal Python install by
passing a fake host with the same methods.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

try:
    import reaper_python as _reaper
    REAPER_IMPORT_ERROR = None
except ImportError as exc:
    _reaper = None
    REAPER_IMPORT_ERROR = exc


ITEM_CHUNK_CAPACITY = 16 * 1024 * 1024
ITEM_CHUNK_MARGIN = 1024


class Reaper420Error(Exception):
    pass


def _safe_text(value):
    try:
        return value if isinstance(value, str) else str(value)
    except Exception:
        return '<unprintable value>'


class Reaper420Host(object):
    """Read-only subset of the API verified by the compatibility probes."""

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
