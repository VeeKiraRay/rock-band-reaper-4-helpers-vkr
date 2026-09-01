"""Apply a frozen calibrated difficulty model to scored chart factors.

Direct Python counterpart of ``lib/reaper_difficulty_predict.lua`` in the
modern helper. Python 2.7 compatible.
"""

from __future__ import unicode_literals

import math


def model_inputs(model, factors):
    values = []
    for key in model['keys']:
        if key.startswith('is_'):
            values.append(0.0)
        else:
            value = factors.get(key)
            if not isinstance(value, (int, float)):
                return None, key
            values.append(value)
    return values, None


def predict_rank(model, factors):
    """Return ``(rank, clamped, raw_rank, error_key)``."""
    values, missing = model_inputs(model, factors)
    if values is None:
        return None, False, None, missing

    transformed = model['intercept']
    for coefficient, value, mean, deviation in zip(
            model['coefs'], values, model['mean'], model['sd']):
        transformed += coefficient * ((value - mean) / deviation)

    scale = model['scale']
    if scale == 'rank':
        raw = transformed
    elif scale == 'log(rank)':
        raw = math.exp(transformed)
    else:
        return None, False, None, 'scale:%s' % scale

    rank = max(model['rank_lo'], min(model['rank_hi'], raw))
    return rank, rank != raw, raw, None


def factor_z_scores(model, factors):
    rows = []
    for index, key in enumerate(model['keys']):
        if key.startswith('is_'):
            continue
        value = factors.get(key)
        if not isinstance(value, (int, float)):
            continue
        deviation = model['sd'][index]
        rows.append({
            'key': key,
            'value': value,
            'mean': model['mean'][index],
            'sd': deviation,
            'z': ((value - model['mean'][index]) / deviation
                  if deviation > 0 else 0),
        })
    return rows


def out_of_range(model, factors):
    rows = []
    bounds = model.get('bounds') or {}
    for key in model['keys']:
        if key.startswith('is_') or key not in bounds:
            continue
        value = factors.get(key)
        if not isinstance(value, (int, float)):
            continue
        limit = bounds[key]
        side = None
        if value < limit['min']:
            side = 'below'
        elif value > limit['max']:
            side = 'above'
        if side:
            rows.append({
                'key': key,
                'value': value,
                'lo': limit['min'],
                'hi': limit['max'],
                'side': side,
            })
    return rows
