"""Parity tests for legacy chart timing and all six difficulty scorers."""

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
    suggest_drums,
    suggest_guitar,
    suggest_keys,
    suggest_real_keys,
    suggest_vocals,
    count_vocal_parts,
    read_coda_time,
)
from rock_band_general_helper_vkr.difficulty_explain import annotate_suggestion
from rock_band_general_helper_vkr.difficulty_score import (
    derive_spans_from_events,
    score_bass,
    score_drums,
    score_guitar,
    score_keys,
    score_vocals,
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


def test_keyboard_selected_factors_match_lua_reference():
    times = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 9, 9.5, 10, 10.5]
    pitches = [
        [96], [97], [98], [97], [96], [97, 99],
        [98], [99], [96, 100], [97, 99], [98], [100]]
    events = [
        {'s': time, 'e': time + 0.25, 'qn': time * 2,
         'qn_e': time * 2 + 0.5, 'pitches': event_pitches, 'held': []}
        for time, event_pitches in zip(times, pitches)]
    factors = score_keys(
        events, [{'s': 0, 'e': 4}, {'s': 9, 'e': 11}])
    expected = {
        'total_changes': 10,
        'attack_density_peak': 0.93124999999999991,
        'tight_p10': 1,
        'tight_med': 1,
        'playing_s': 6,
        'entropy_h2_rel': 0.88117908038892157,
        'complex_peak': 1.3020089529316279,
        'chord_size_mean': 1.25,
    }
    for key, value in expected.items():
        expect(close(factors[key], value),
               'Lua parity Keyboard factor %s differs: %.17g vs %.17g' %
               (key, factors[key], value))


def test_drum_selected_factors_match_lua_reference():
    times = [0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 10, 10.5, 11, 12, 13]
    pitches = [
        [96, 97], [98], [96, 98], [99], [96, 100], [98, 99], [97],
        [96], [100], [96, 99], [98], [96, 100], [97, 99], [96]]
    events = []
    for index, (time, event_pitches) in enumerate(zip(times, pitches), 1):
        qn = time * 2 + (0.25 if index % 3 == 0 else 0)
        events.append({
            's': time, 'e': time + 0.25, 'qn': qn, 'qn_e': qn + 0.5,
            'pitches': event_pitches, 'held': [],
        })
    factors = score_drums(
        events, [{'s': 0, 'e': 6}, {'s': 10, 'e': 14}],
        tom_spans={
            98: [{'s': 0.5, 'e': 2.5}],
            99: [{'s': 9, 'e': 11.5}],
        },
        roll_spans=[{'s': 2, 'e': 3.5}])
    expected = {
        'playing_s': 10,
        'density_avg': 2.1000000000000001,
        'density_peak_noroll': 1,
        'change_rate': 1.2,
        'attack_density_avg': 1.3999999999999999,
        'attack_density_peak_noroll': 0.66874999999999996,
        'tight_p10': 0.77500000000000002,
        'tight_med': 1.25,
        'chord_size_mean': 1.5,
        'chord_span_mean': 2.4285714285714284,
        'chord_change_frac': 0.41666666666666669,
        'move_mean': 1.25,
        'move_p90': 2,
        'anchor_frac': 0.083333333333333329,
        'kick_density': 0.69999999999999996,
        'kick_density_peak': 0.41874999999999996,
        'hand_density_peak_noroll': 0.625,
        'stick_size_mean': 1.1666666666666667,
        'tom_frac': 0.5,
        'roll_frac': 0.14999999999999999,
        'offbeat_frac': 0.2857142857142857,
        'pro_stations_peak': 5.3499999999999996,
        'entropy_h2': 0.6492127684000335,
        'entropy_h2_rel': 0.6492127684000335,
        'notes_total': 21,
        'total_changes': 12,
    }
    for key, value in expected.items():
        expect(close(factors[key], value),
               'Lua parity Drum factor %s differs: %.17g vs %.17g' %
               (key, factors[key], value))


def test_vocal_selected_factors_match_lua_reference():
    notes = [
        {'s': 0, 'e': 0.5, 'qn': 0, 'qn_e': 1,
         'pitch': 60, 'lyric': 'la'},
        {'s': 0.5, 'e': 1, 'qn': 1, 'qn_e': 2,
         'pitch': 72, 'lyric': '+'},
        {'s': 1.5, 'e': 1.75, 'qn': 3, 'qn_e': 3.5,
         'pitch': 71, 'lyric': 'word-#'},
        {'s': 3, 'e': 4, 'qn': 6, 'qn_e': 8,
         'pitch': 67, 'lyric': 'hey'},
        {'s': 6, 'e': 6.5, 'qn': 12, 'qn_e': 13,
         'pitch': 65, 'lyric': 'yo^'},
        {'s': 7, 'e': 9, 'qn': 14, 'qn_e': 18,
         'pitch': 70, 'lyric': 'high'},
        {'s': 10, 'e': 11, 'qn': 20, 'qn_e': 22,
         'pitch': 82, 'lyric': 'up'},
        {'s': 11, 'e': 11.5, 'qn': 22, 'qn_e': 23,
         'pitch': 70, 'lyric': 'down'},
    ]
    factors = score_vocals(
        notes, [{'s': 0, 'e': 5}, {'s': 6, 'e': 12}],
        percussion_spans=[{'s': 8, 'e': 9}], vocal_parts=3)
    expected = {
        'syl_density_avg': 0.69999999999999996,
        'syl_density_peak': 0.26499999999999996,
        'tight_p10': 1.3999999999999999,
        'tight_med': 2,
        'pc_interval_mean': 2,
        'playing_s': 10,
        'notated_range': 22,
        'pitch_p90': 77,
        'octave_jump_rate': 0.20000000000000001,
        'parts_3': 1,
        'high_time_70': 0.72727272727272729,
        'pc_change_rate': 0.29999999999999999,
    }
    for key, value in expected.items():
        expect(close(factors[key], value),
               'Lua parity Vocal factor %s differs: %.17g vs %.17g' %
               (key, factors[key], value))


def _meta_event(tick, message, meta_type=1):
    payload = b'\xff' + chr(meta_type).encode('latin-1') + message.encode('ascii')
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


def _vocal_chunk():
    return ('<ITEM\nPOSITION 0\nLENGTH 2\n<SOURCE MIDI\n'
            'HASDATA 1 480 QN\n'
            'E 0 90 3c 64\nE 0 90 69 64\n' +
            _meta_event(0, 'la', 5) +
            'E 240 80 3c 00\nE 240 90 48 64\n' +
            _meta_event(0, '+', 1) +
            'E 240 80 48 00\nE 240 80 69 00\n'
            'IGNTEMPO 0 120 4 4\n>\n>\n')


class FakeTimingHost(object):
    def __init__(self, offset=0, rate=1, chunk=None, tempo=120):
        self.offset = offset
        self.rate = rate
        self.chunk = chunk or _bass_chunk()
        self.tempo = tempo

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
        return self.chunk

    def item_position(self, item):
        return 0

    def item_length(self, item):
        return 6

    def time_to_qn(self, seconds):
        return seconds * self.tempo / 60.0

    def qn_to_time(self, quarter_notes):
        return quarter_notes * 60.0 / self.tempo


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
    annotate_suggestion(suggestion, 'Bass')
    expect(suggestion['ruler'] and
           isinstance(suggestion['warnings'], list) and
           isinstance(suggestion['explanations'], list),
           'user-facing Bass annotations were not produced')


def test_legacy_reader_reaches_calibrated_guitar_model():
    suggestion = suggest_guitar(FakeTimingHost(), 'track')
    expect(suggestion['factors']['total_changes'] == 2,
           'legacy Guitar chunk change count differs')
    expect(suggestion['span_source'] == 'anim',
           'Guitar animation playing span was not used')
    expect(suggestion['rank'] > 0 and suggestion['tier'] is not None,
           'calibrated Guitar prediction was not produced')


def test_legacy_reader_reaches_both_keyboard_models():
    keys = suggest_keys(FakeTimingHost(), 'track')
    expect(keys['factors']['total_changes'] == 2 and keys['tier'] is not None,
           'five-lane Keys prediction was not produced')

    real_chunk = (_bass_chunk()
                  .replace('90 60', '90 30').replace('80 60', '80 30')
                  .replace('90 61', '90 31').replace('80 61', '80 31')
                  .replace('90 62', '90 32').replace('80 62', '80 32'))
    real_host = FakeTimingHost(chunk=real_chunk)
    real_keys = suggest_real_keys(real_host, 'real-track', 'span-track')
    expect(real_keys['factors']['total_changes'] == 2 and
           real_keys['tier'] is not None,
           'Pro Keys prediction was not produced')


def test_legacy_reader_reaches_calibrated_drum_model():
    suggestion = suggest_drums(FakeTimingHost(), 'track')
    expect(suggestion['factors']['total_changes'] == 2,
           'legacy Drum chunk change count differs')
    expect(suggestion['rank'] > 0 and suggestion['tier'] is not None,
           'calibrated Drum prediction was not produced')


def test_legacy_reader_reaches_calibrated_vocal_model():
    host = FakeTimingHost(chunk=_vocal_chunk())
    suggestion = suggest_vocals(host, 'track', vocal_parts=3)
    expect(suggestion['span_source'] == 'phrase',
           'authored Vocal phrase was not used')
    expect(suggestion['factors']['syllables_total'] == 1,
           'type 1/type 5 lyric pairing or plus handling differs')
    expect(suggestion['factors']['parts_3'] == 1,
           'three-part Vocal context was not passed to the model')
    expect(suggestion['rank'] > 0 and suggestion['tier'] is not None,
           'calibrated Vocal prediction was not produced')
    expect(count_vocal_parts(host, ['harm2', 'harm3']) == 3,
           'harmony tracks with sung notes were not counted')


def test_coda_time_and_bre_context_are_reported_without_changing_rank():
    coda_chunk = _bass_chunk().replace(
        _meta_event(0, '[play]'),
        _meta_event(0, '[play]') + _meta_event(480, '[coda]'), 1)
    host = FakeTimingHost(chunk=coda_chunk)
    coda = read_coda_time(host, 'events')
    expect(close(coda, 0.5), 'legacy [coda] event time differs')
    baseline = suggest_bass(host, 'track')
    with_context = suggest_bass(host, 'track', coda_time=coda)
    expect(close(with_context['rank'], baseline['rank']),
           'BRE context changed the shipped difficulty rank')
    expect(with_context['bre_gem_frac'] is not None and
           with_context['bre_seconds'] >= 0,
           'BRE share/duration context was not produced')


def test_one_tick_take_offset_at_210_bpm_is_supported():
    one_tick = 60.0 / 210.0 / 480.0
    baseline = suggest_guitar(FakeTimingHost(tempo=210), 'track')
    shifted = suggest_guitar(
        FakeTimingHost(offset=one_tick, tempo=210), 'track')
    expect(close(shifted['rank'], baseline['rank']),
           'one-tick source offset changed the relative Guitar score')
    for key in baseline['factors']:
        expect(close(shifted['factors'][key], baseline['factors'][key]),
               'one-tick source offset changed Guitar factor %s' % key)


def test_explicit_chunk_qn_offset_takes_priority():
    one_tick_seconds = 60.0 / 210.0 / 480.0
    one_tick_qn = 1.0 / 480.0
    chunk = _bass_chunk().replace(
        '<ITEM\n', '<ITEM\nSOFFS %.14f %.14f\n' %
        (one_tick_seconds, one_tick_qn), 1)
    baseline = suggest_guitar(FakeTimingHost(tempo=210), 'track')
    # Deliberately pass a wrong API seconds value. The explicit QN value in
    # the item-state chunk is authoritative and should still give a uniform
    # one-tick shift with identical relative factors.
    shifted = suggest_guitar(
        FakeTimingHost(offset=99, tempo=210, chunk=chunk), 'track')
    for key in baseline['factors']:
        expect(close(shifted['factors'][key], baseline['factors'][key]),
               'explicit QN offset changed Guitar factor %s' % key)


def test_stretched_take_mapping_is_refused():
    try:
        suggest_bass(FakeTimingHost(rate=2), 'track')
    except DifficultyReadError:
        pass
    else:
        raise AssertionError('stretched take mapping was accepted')


def main():
    tests = [
        test_bass_factors_match_lua_reference,
        test_fallback_spans_split_on_more_than_eight_qn,
        test_guitar_selected_factors_match_lua_reference,
        test_keyboard_selected_factors_match_lua_reference,
        test_drum_selected_factors_match_lua_reference,
        test_vocal_selected_factors_match_lua_reference,
        test_legacy_reader_reaches_calibrated_bass_model,
        test_legacy_reader_reaches_calibrated_guitar_model,
        test_legacy_reader_reaches_both_keyboard_models,
        test_legacy_reader_reaches_calibrated_drum_model,
        test_legacy_reader_reaches_calibrated_vocal_model,
        test_coda_time_and_bre_context_are_reported_without_changing_rank,
        test_one_tick_take_offset_at_210_bpm_is_supported,
        test_explicit_chunk_qn_offset_takes_priority,
        test_stretched_take_mapping_is_refused,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty scoring tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
