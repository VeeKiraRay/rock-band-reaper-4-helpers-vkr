"""Parity tests for legacy chart timing and the first Bass scorer slice."""

from __future__ import print_function

import base64
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.difficulty_read import (
    DifficultyReadError,
    suggest_bass,
    suggest_guitar,
)
from rock_band_general_helper_vkr.difficulty_score import (
    derive_spans_from_events,
    score_bass,
    score_guitar,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def close(left, right, tolerance=1e-10):
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def test_bass_factors_match_lua_reference():
    pitches = [96, 97, 96, 98, 96, 99, 99]
    times = [0, 1, 2, 3, 4, 10, 11]
    events = [
        {'s': time, 'e': time + 0.25, 'qn': time * 2,
         'qn_e': time * 2 + 0.5, 'pitches': [pitch], 'held': []}
        for pitch, time in zip(pitches, times)]
    factors = score_bass(events, [{'s': 0, 'e': 12}])
    expect(factors['total_changes'] == 5,
           'Lua parity change count differs')
    expect(close(factors['density_peak'], 0.58749999999999991),
           'Lua parity peak density differs')
    expect(close(factors['entropy_h2'], 0.57707801635558531),
           'Lua parity conditional entropy differs')


def test_fallback_spans_split_on_more_than_eight_qn():
    events = [
        {'s': 0, 'e': 1, 'qn': 0, 'pitches': [96]},
        {'s': 1, 'e': 2, 'qn': 8, 'pitches': [97]},
        {'s': 10, 'e': 11, 'qn': 16.01, 'pitches': [98]},
    ]
    spans = derive_spans_from_events(events)
    expect(spans == [{'s': 0, 'e': 2}, {'s': 10, 'e': 11}],
           'fallback span gap rule differs')


def test_guitar_selected_factors_match_lua_reference():
    pitches = [
        [96], [97], [97, 99], [98], [96], [100], [96, 100], [97]]
    times = [0, 1, 2, 3, 4, 10, 11, 12]
    lengths = [0.25, 0.5, 1, 0.25, 1, 0.25, 0.5, 1]
    events = []
    for event_pitches, time, length in zip(pitches, times, lengths):
        events.append({
            's': time, 'e': time + length / 2.0,
            'qn': time * 2, 'qn_e': time * 2 + length,
            'pitches': event_pitches, 'held': [],
        })
    factors = score_guitar(
        events, [{'s': 0, 'e': 5}, {'s': 10, 'e': 13}],
        marked_solo_spans=[{'s': 1.5, 'e': 4.5}],
        tremolo_spans=[{'s': 3, 'e': 4}],
        trill_spans=[{'s': 10, 'e': 11.5}],
        force_hopo_count=2, force_strum_count=1)
    expected = {
        'playing_s': 8,
        'attack_density_avg': 1,
        'attack_density_peak': 0.58124999999999993,
        'change_rate': 0.75,
        'tight_p10': 2,
        'tight_med': 2,
        'chord_size_mean': 1.25,
        'chord_span_mean': 3,
        'chord_change_frac': 0.33333333333333331,
        'move_mean': 1.1666666666666667,
        'move_p90': 2,
        'anchor_frac': 0.33333333333333331,
        'solo_frac_marked': 0.375,
        'solo_change_ratio': 1,
        'sustain_frac': 0.625,
        'force_hopo_rate': 0.25,
        'force_strum_rate': 0.125,
        'tremolo_frac': 0.125,
        'trill_frac': 0.1875,
        'notes_total': 10,
        'total_changes': 6,
    }
    for key, value in expected.items():
        expect(close(factors[key], value),
               'Lua parity Guitar factor %s differs: %.17g vs %.17g' %
               (key, factors[key], value))


def _meta_event(tick, message):
    payload = b'\xff\x01' + message.encode('ascii')
    encoded = base64.b64encode(payload)
    if not isinstance(encoded, str):
        encoded = encoded.decode('ascii')
    return '<X %d 0\n  %s\n>\n' % (tick, encoded)


def _bass_chunk():
    # Constant 120 BPM: 480 ticks/QN and 0.5 seconds/QN.
    return ('<ITEM\nPOSITION 0\nLENGTH 6\n<SOURCE MIDI\n'
            'HASDATA 1 480 QN\n' +
            _meta_event(0, '[play]') +
            'E 0 90 60 64\nE 120 80 60 00\n'
            'E 360 90 61 64\nE 120 80 61 00\n'
            'E 360 90 62 64\nE 120 80 62 00\n' +
            _meta_event(360, '[idle]') +
            'IGNTEMPO 0 120 4 4\n>\n>\n')


class FakeTimingHost(object):
    def __init__(self, offset=0, rate=1):
        self.offset = offset
        self.rate = rate

    def item_count(self, track):
        return 1

    def get_item(self, track, index):
        return 'item'

    def active_take(self, item):
        return 'take'

    def take_start_offset(self, take):
        return self.offset

    def take_play_rate(self, take):
        return self.rate

    def read_item_chunk(self, item):
        return _bass_chunk()

    def item_position(self, item):
        return 0

    def item_length(self, item):
        return 6

    def time_to_qn(self, seconds):
        return seconds * 2

    def qn_to_time(self, quarter_notes):
        return quarter_notes / 2.0


def test_legacy_reader_reaches_calibrated_bass_model():
    suggestion = suggest_bass(FakeTimingHost(), 'track')
    expect(suggestion['factors']['total_changes'] == 2,
           'legacy chunk change count differs')
    expect(suggestion['span_source'] == 'anim',
           'animation playing span was not used')
    expect(suggestion['animation_states'] == 2,
           'animation state count differs')
    expect(suggestion['rank'] > 0 and suggestion['tier'] is not None,
           'calibrated Bass prediction was not produced')


def test_legacy_reader_reaches_calibrated_guitar_model():
    suggestion = suggest_guitar(FakeTimingHost(), 'track')
    expect(suggestion['factors']['total_changes'] == 2,
           'legacy Guitar chunk change count differs')
    expect(suggestion['span_source'] == 'anim',
           'Guitar animation playing span was not used')
    expect(suggestion['rank'] > 0 and suggestion['tier'] is not None,
           'calibrated Guitar prediction was not produced')


def test_nonstandard_take_mapping_is_refused():
    for host in (FakeTimingHost(offset=0.5), FakeTimingHost(rate=2)):
        try:
            suggest_bass(host, 'track')
        except DifficultyReadError:
            pass
        else:
            raise AssertionError('nonstandard take mapping was accepted')


def main():
    tests = [
        test_bass_factors_match_lua_reference,
        test_fallback_spans_split_on_more_than_eight_qn,
        test_guitar_selected_factors_match_lua_reference,
        test_legacy_reader_reaches_calibrated_bass_model,
        test_legacy_reader_reaches_calibrated_guitar_model,
        test_nonstandard_take_mapping_is_refused,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty scoring tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
