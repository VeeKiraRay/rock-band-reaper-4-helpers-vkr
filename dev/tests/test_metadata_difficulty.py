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
    project_identity_changed,
)
from rock_band_general_helper_vkr.difficulty_report import (
    format_suggestion_report,
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
    def RPR_EnumProjects(self, index, buffer_value, capacity):
        return ('project-handle', index, r'C:\Songs\example.rpp', capacity)

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

    def RPR_GetMediaItemInfo_Value(self, item, key):
        return {'D_POSITION': 2.0, 'D_LENGTH': 8.0}[key]

    def RPR_GetActiveTake(self, item):
        return 'take-handle'

    def RPR_GetMediaItemTakeInfo_Value(self, take, key):
        return {'D_STARTOFFS': 0.0, 'D_PLAYRATE': 1.0}[key]

    def RPR_TimeMap2_timeToQN(self, project, seconds):
        return seconds * 2.0

    def RPR_TimeMap2_QNToTime(self, project, quarter_notes):
        return quarter_notes / 2.0

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
    project = host.project_info()
    expect(project['identity'] == 'project-handle' and
           project['name'] == 'example',
           'legacy project identity/path tuple was read incorrectly')
    expect(host.track_name(track, 0) == 'PART GUITAR',
           'legacy track-name tuple was read incorrectly')
    expect(host.track_muted(track), 'legacy mute value was not read')
    expect(host.item_count(track) == 1, 'legacy item count differs')
    item = host.get_item(track, 0)
    expect(host.read_item_chunk(item).startswith('<ITEM'),
           'legacy item-state tuple was read incorrectly')
    expect(host.item_position(item) == 2.0 and host.item_length(item) == 8.0,
           'legacy item timing values differ')
    take = host.active_take(item)
    expect(host.take_start_offset(take) == 0.0 and
           host.take_play_rate(take) == 1.0,
           'legacy take mapping values differ')
    expect(host.time_to_qn(2.0) == 4.0 and host.qn_to_time(4.0) == 2.0,
           'legacy project time-map values differ')

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


def test_report_scopes_calibrated_ranks_to_six_instruments():
    results = analyse_project(FakeHost([]))
    report = format_inventory(results)
    expect('All six instrument charts use calibrated models' in report,
           'full calibration scope is missing')
    expect('Guitar - Not found' in report and 'Vocals - Not found' in report,
           'report does not contain all chart records')


def test_project_identity_change_requires_two_known_handles():
    expect(project_identity_changed(
        {'identity': 'one'}, {'identity': 'two'}),
        'project-tab switch was not detected')
    expect(not project_identity_changed(
        {'identity': None}, {'identity': 'two'}),
        'unknown initial project caused false invalidation')


def test_concise_report_omits_verification_details():
    suggestion = {
        'tier_name': 'Solid', 'tier': 2, 'rank_shown': 217,
        'warnings': ['Near a boundary.'],
        'explanations': [{'text': 'A high syllable rate'}],
        'ruler': {'lo_label': 'Solid (175)',
                  'hi_label': 'Moderate (218)'},
    }
    report = format_suggestion_report([
        {'label': 'Vocals', 'status': 'Chart read',
         'suggestion': suggestion},
    ], 'example_song', '2026-09-02 12:34:56')
    expect('example_song' in report and '2026-09-02 12:34:56' in report,
           'project provenance is missing from concise report')
    expect('Vocals - Solid (rank 217)' in report and 'Dots: 2/5' in report,
           'rank or dot count is missing from concise report')
    expect('Near a boundary.' in report and 'A high syllable rate' in report,
           'user-facing annotations are missing from concise report')
    expect('Source PPQ' not in report and 'factor' not in report.lower(),
           'verification details leaked into concise report')


def test_card_counts_use_onsets_but_vocals_omit_them():
    base = {
        'present': True, 'status': 'Chart read', 'failed_items': 0,
        'parsed_items': 1, 'playable_notes': 12, 'playable_onsets': 9,
        'suggestion': {'rank_shown': 200, 'tier_name': 'Solid'},
    }
    guitar = dict(base, key='guitar')
    vocals = dict(base, key='vocals')
    expect(card_summary(guitar) == '12 gems / 9 onsets',
           'gem card did not use onset terminology')
    expect(card_summary(vocals) == '12 notes',
           'Vocal card did not omit the chord/onset count')


def test_ui_modules_import_without_starting_tk():
    from rock_band_general_helper_vkr import ui_metadata_difficulty
    expect(hasattr(ui_metadata_difficulty, 'MetadataDifficultyView'),
           'Difficulty view is missing')
    expect('treat with a grain of salt' in
           ui_metadata_difficulty.DIFFICULTY_INTRODUCTION,
           'Lua advisory wording is missing')


def main():
    tests = [
        test_specs_match_modern_six_instruments,
        test_legacy_host_adapter_tuple_shapes,
        test_guitar_notes_are_grouped_into_onsets,
        test_absent_muted_empty_and_failed_are_distinct,
        test_report_scopes_calibrated_ranks_to_six_instruments,
        test_project_identity_change_requires_two_known_handles,
        test_concise_report_omits_verification_details,
        test_card_counts_use_onsets_but_vocals_omit_them,
        test_ui_modules_import_without_starting_tk,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Metadata Difficulty compatibility tests: PASS (%d tests)' %
          len(tests))


if __name__ == '__main__':
    main()
