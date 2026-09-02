"""Parity tests for the pure difficulty tiers and frozen models."""

from __future__ import print_function

import math
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.difficulty_models import (
    RB_DIFFICULTY_MODELS,
    RB_DIFFICULTY_MODELS_CSV_FINGERPRINT,
    RB_DIFFICULTY_MODELS_SCHEMA,
    RB_DIFFICULTY_MODEL_ORDER,
)
from rock_band_general_helper_vkr.difficulty_predict import (
    display_rank,
    factor_z_scores,
    model_inputs,
    out_of_range,
    predict_rank,
)
from rock_band_general_helper_vkr.difficulty_tiers import (
    RANK_TIER_THRESHOLDS,
    tier_band,
    tier_for_rank,
    tier_name,
    tier_position,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def close(left, right, tolerance=1e-10):
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def toy_model(**updates):
    model = {
        'candidate': 'toy',
        'scale': 'rank',
        'status': 'validated',
        'keys': ['density_peak', 'is_lego'],
        'mean': [10, 0],
        'sd': [2, 1],
        'coefs': [50, 7],
        'intercept': 200,
        'rank_lo': 100,
        'rank_hi': 400,
        'bounds': {
            'density_peak': {'min': 4, 'max': 16, 'p90': 14},
        },
    }
    model.update(updates)
    return model


def test_tier_boundaries_match_modern_helper():
    expect(tier_for_rank('guitar', 0) is None,
           'rank zero should mean no part')
    expect(tier_for_rank('kazoo', 200) is None,
           'unknown instrument should have no tier')
    expect(tier_name(None) == 'No Part', 'absent tier name differs')
    for instrument, thresholds in RANK_TIER_THRESHOLDS.items():
        for tier, threshold in enumerate(thresholds, 1):
            expect(tier_for_rank(instrument, threshold) == tier,
                   '%s threshold %d differs' % (instrument, tier))
            expect(tier_for_rank(instrument, threshold - 1) == tier - 1,
                   '%s lower edge %d differs' % (instrument, tier))


def test_tier_bands_and_positions_match_modern_examples():
    expect(tier_band('guitar', 0) == (1, 139),
           'open Warmup band differs')
    expect(tier_band('guitar', 0, 605, 75) == (75, 139),
           'model-floor Warmup band differs')
    expect(tier_band('guitar', 6, 605) == (409, 605),
           'closed Impossible band differs')
    expect(tier_band('guitar', 6) == (409, 485),
           'fallback Impossible band differs')
    expect(tier_for_rank('guitar', 271) == 4,
           'worked-example tier differs')
    expect(close(tier_position('guitar', 271, 605), 4.0 / 66.0),
           'worked-example position differs')
    expect(tier_position('guitar', 605, 605) == 1.0,
           'top position differs')


def test_display_rank_floors_without_crossing_tier_threshold():
    expect(display_rank(217.55) == 217,
           'display rank rounded instead of flooring')
    for instrument, thresholds in RANK_TIER_THRESHOLDS.items():
        for threshold in thresholds:
            below = threshold - 0.01
            above = threshold + 0.01
            expect(tier_for_rank(instrument, below) ==
                   tier_for_rank(instrument, display_rank(below)),
                   '%s display crossed threshold %d from below' %
                   (instrument, threshold))
            expect(tier_for_rank(instrument, above) ==
                   tier_for_rank(instrument, display_rank(above)),
                   '%s display crossed threshold %d from above' %
                   (instrument, threshold))


def test_predictor_standardizes_origins_and_clamps():
    model = toy_model()
    rank, clamped, raw, error = predict_rank(
        model, {'density_peak': 12})
    expect((rank, clamped, raw, error) == (250.0, False, 250.0, None),
           'standardized toy prediction differs')
    supplied, _, _, _ = predict_rank(
        model, {'density_peak': 10, 'is_lego': 1})
    expect(supplied == 200.0,
           'chart-supplied training origin changed prediction')
    rank, clamped, raw, error = predict_rank(
        model, {'density_peak': 100})
    expect(rank == 400 and clamped and raw > 400 and error is None,
           'upper rank clamp differs')
    rank, clamped, raw, error = predict_rank(model, {})
    expect(rank is None and error == 'density_peak',
           'missing factor was not reported')


def test_log_scale_and_explanation_inputs():
    model = toy_model(
        scale='log(rank)', intercept=math.log(250), coefs=[0, 0])
    rank, clamped, raw, error = predict_rank(
        model, {'density_peak': 12})
    expect(close(rank, 250), 'log-rank inverse differs')
    expect(not clamped and error is None, 'log-rank prediction flags differ')

    rows = factor_z_scores(toy_model(), {'density_peak': 14})
    expect(len(rows) == 1 and rows[0]['key'] == 'density_peak',
           'origin flag leaked into z-scores')
    expect(rows[0]['z'] == 2.0, 'factor z-score differs')
    expect(out_of_range(toy_model(), {'density_peak': 10}) == [],
           'in-range value produced a warning')
    expect(out_of_range(toy_model(), {'density_peak': 20})[0]['side'] ==
           'above', 'above-range value was not reported')


def test_generated_artifact_is_complete_and_consistent():
    expect(RB_DIFFICULTY_MODELS_SCHEMA == 5,
           'generated schema differs')
    expect(RB_DIFFICULTY_MODELS_CSV_FINGERPRINT == 864960590,
           'generated corpus fingerprint differs')
    expect(RB_DIFFICULTY_MODEL_ORDER == [
        'guitar', 'bass', 'drum', 'keys', 'real_keys', 'vocals'],
        'generated model order differs')
    for instrument in RB_DIFFICULTY_MODEL_ORDER:
        model = RB_DIFFICULTY_MODELS[instrument]
        count = len(model['keys'])
        expect(count == len(model['mean']) == len(model['sd']) ==
               len(model['coefs']),
               '%s model vector lengths differ' % instrument)
        expect(all(value > 0 for value in model['sd']),
               '%s model contains a non-positive deviation' % instrument)
        expect(model['rank_lo'] < model['rank_hi'],
               '%s model rank bounds are inverted' % instrument)
        expect(isinstance(model['corr'], dict),
               '%s correlation map is not a dictionary' % instrument)


def test_all_six_predictions_match_lua_reference():
    # Expected values were produced by DifficultyPredictRank in the modern
    # Lua helper. Each real factor is displaced from its model mean by a
    # repeating -0.2/0/+0.2/+0.4/-0.4 sd pattern; origin flags remain zero.
    expected = {
        'guitar': 258.38072132578111,
        'bass': 212.97775850565901,
        'drum': 223.04018823505291,
        'keys': 271.24993078032088,
        'real_keys': 277.90398734253966,
        'vocals': 234.76749051433046,
    }
    for instrument in RB_DIFFICULTY_MODEL_ORDER:
        model = RB_DIFFICULTY_MODELS[instrument]
        factors = {}
        for index, key in enumerate(model['keys']):
            lua_index = index + 1
            if not key.startswith('is_'):
                factors[key] = (
                    model['mean'][index] +
                    ((lua_index % 5) - 2) * 0.2 * model['sd'][index])
        rank, clamped, unused_raw, error = predict_rank(model, factors)
        expect(error is None and not clamped,
               '%s parity fixture did not predict cleanly' % instrument)
        expect(close(rank, expected[instrument]),
               '%s Python/Lua rank differs: %.17g vs %.17g' %
               (instrument, rank, expected[instrument]))


def main():
    tests = [
        test_tier_boundaries_match_modern_helper,
        test_tier_bands_and_positions_match_modern_examples,
        test_display_rank_floors_without_crossing_tier_threshold,
        test_predictor_standardizes_origins_and_clamps,
        test_log_scale_and_explanation_inputs,
        test_generated_artifact_is_complete_and_consistent,
        test_all_six_predictions_match_lua_reference,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty model parity tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
