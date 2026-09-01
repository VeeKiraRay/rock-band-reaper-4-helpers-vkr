"""Desktop tests for the Metadata Difficulty compatibility inventory."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.metadata_difficulty import (
    CHART_SPECS,
    analyse_project,
    card_summary,
    format_inventory,
)
from lib.reaper420 import Reaper420Error, Reaper420Host


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def midi_chunk(events, ppq=480):
    return ('<ITEM\n<SOURCE MIDI\nHASDATA 1 %d QN\n%s'
            'IGNTEMPO 0 120 4 4\n>\n>\n') % (ppq, ''.join(events))


class FakeHost(object):
    def __init__(self, tracks):
        self.tracks = tracks

    def track_count(self):
        return len(self.tracks)

    def get_track(self, index):
        return self.tracks[index]

    def track_name(self, track, unused_index):
        return track['name']

    def track_muted(self, track):
        return track.get('muted', False)

    def item_count(self, track):
        return len(track.get('items', []))

    def get_item(self, track, index):
        return track['items'][index]

    def read_item_chunk(self, item):
        if isinstance(item, Exception):
            raise item
        return item


class FakeReaperApi(object):
    def RPR_CountTracks(self, project):
        return 1

    def RPR_GetTrack(self, project, index):
        return 'track-handle'

    def RPR_GetSetMediaTrackInfo_String(self, track, key, value, write):
        return (True, track, key, 'PART GUITAR', write)

    def RPR_GetMediaTrackInfo_Value(self, track, key):
        return 1.0

    def RPR_CountTrackMediaItems(self, track):
        return 1

    def RPR_GetTrackMediaItem(self, track, index):
        return 'item-handle'

    def RPR_GetSetItemState(self, item, value, capacity):
        return (True, item, midi_chunk([]), capacity)


def test_specs_match_modern_six_instruments():
    expect([spec['key'] for spec in CHART_SPECS] == [
        'guitar', 'bass', 'drum', 'keys', 'real_keys', 'vocals'],
        'chart spec order differs')
    expect(CHART_SPECS[4]['lo'] == 48 and CHART_SPECS[4]['hi'] == 72,
           'Pro Keys pitch window differs')
    expect(CHART_SPECS[5]['lo'] == 36 and CHART_SPECS[5]['hi'] == 84,
           'vocal pitch window differs')


def test_legacy_host_adapter_tuple_shapes():
    host = Reaper420Host(FakeReaperApi())
    track = host.get_track(0)
    expect(host.track_count() == 1, 'legacy track count differs')
    expect(host.track_name(track, 0) == 'PART GUITAR',
           'legacy track-name tuple was read incorrectly')
    expect(host.track_muted(track), 'legacy mute value was not read')
    expect(host.item_count(track) == 1, 'legacy item count differs')
    item = host.get_item(track, 0)
    expect(host.read_item_chunk(item).startswith('<ITEM'),
           'legacy item-state tuple was read incorrectly')

    try:
        Reaper420Host(api=None).require()
    except Reaper420Error:
        pass
    else:
        raise AssertionError('missing REAPER module was not rejected')


def test_guitar_notes_are_grouped_into_onsets():
    chunk = midi_chunk([
        'E 0 90 60 64\n',
        'E 0 90 64 64\n',
        'E 120 80 60 00\n',
        'E 0 80 64 00\n',
        'E 120 90 62 64\n',
        'E 120 80 62 00\n',
    ])
    results = analyse_project(FakeHost([
        {'name': 'PART GUITAR', 'items': [chunk]},
    ]))
    guitar = results[0]
    expect(guitar['playable_notes'] == 3, 'guitar note count differs')
    expect(guitar['playable_onsets'] == 2, 'guitar onset count differs')
    expect(guitar['chord_onsets'] == 1, 'guitar chord count differs')
    expect(guitar['max_chord_size'] == 2, 'maximum chord size differs')
    expect(guitar['longest_note_ticks'] == 120,
           'longest note length differs')
    expect(guitar['status'] == 'Chart read', 'read status differs')


def test_absent_muted_empty_and_failed_are_distinct():
    results = analyse_project(FakeHost([
        {'name': 'PART BASS', 'muted': True,
         'items': [midi_chunk(['E 0 90 60 64\n',
                              'E 120 80 60 00\n'])]},
        {'name': 'PART DRUMS', 'items': []},
        {'name': 'PART KEYS', 'items': [RuntimeError('fixture failure')]},
    ]))
    expect(results[0]['status'] == 'Not found', 'absent status differs')
    expect(results[1]['status'] == 'Muted', 'muted status differs')
    expect(results[2]['status'] == 'No MIDI items', 'empty status differs')
    expect(results[3]['status'] == 'Read warning', 'failure status differs')
    expect(card_summary(results[3]) == 'MIDI read failed',
           'failed card summary differs')


def test_report_disclaims_calibrated_ranks():
    results = analyse_project(FakeHost([]))
    report = format_inventory(results)
    expect('not suggested difficulty ranks' in report,
           'rank disclaimer is missing')
    expect('Guitar - Not found' in report and 'Vocals - Not found' in report,
           'report does not contain all chart records')


def test_ui_modules_import_without_starting_tk():
    from rock_band_general_helper_vkr import ui_metadata_difficulty
    expect(hasattr(ui_metadata_difficulty, 'MetadataDifficultyView'),
           'Difficulty view is missing')


def main():
    tests = [
        test_specs_match_modern_six_instruments,
        test_legacy_host_adapter_tuple_shapes,
        test_guitar_notes_are_grouped_into_onsets,
        test_absent_muted_empty_and_failed_are_distinct,
        test_report_disclaims_calibrated_ranks,
        test_ui_modules_import_without_starting_tk,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Metadata Difficulty compatibility tests: PASS (%d tests)' %
          len(tests))


if __name__ == '__main__':
    main()
