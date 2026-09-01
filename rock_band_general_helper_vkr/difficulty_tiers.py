"""Rock Band rank-to-tier conversion.

Direct Python counterpart of ``lib/reaper_difficulty_tiers.lua`` in the
modern helper. Python 2.7 compatible.
"""

from __future__ import unicode_literals


RANK_TIER_THRESHOLDS = {
    'guitar': (139, 176, 221, 267, 333, 409),
    'bass': (135, 181, 228, 293, 364, 436),
    'drum': (124, 151, 178, 242, 345, 448),
    'vocals': (132, 175, 218, 279, 353, 427),
    'keys': (153, 211, 269, 327, 385, 443),
    'real_keys': (153, 211, 269, 327, 385, 443),
    'real_guitar': (150, 208, 267, 325, 384, 442),
    'real_bass': (150, 208, 267, 325, 384, 442),
    'band': (165, 215, 243, 267, 292, 345),
}

TIER_NAMES = (
    'Warmup', 'Apprentice', 'Solid', 'Moderate',
    'Challenging', 'Nightmare', 'Impossible')


def tier_for_rank(instrument, rank):
    thresholds = RANK_TIER_THRESHOLDS.get(instrument)
    if thresholds is None or rank is None or rank <= 0:
        return None
    tier = 0
    for index, threshold in enumerate(thresholds, 1):
        if rank >= threshold:
            tier = index
    return tier


def tier_name(tier):
    if tier is None:
        return 'No Part'
    if 0 <= tier < len(TIER_NAMES):
        return TIER_NAMES[tier]
    return '?%s' % tier


def tier_band(instrument, tier, rank_hi=None, rank_lo=None):
    thresholds = RANK_TIER_THRESHOLDS.get(instrument)
    if thresholds is None or tier is None or tier < 0 or tier > 6:
        return None
    if tier == 0:
        first = thresholds[0]
        lo = rank_lo if (rank_lo is not None and
                         0 < rank_lo < first) else 1
    else:
        lo = thresholds[tier - 1]
    if tier < 6:
        return lo, thresholds[tier]
    hi = rank_hi
    if hi is None or hi <= lo:
        hi = lo + (thresholds[5] - thresholds[4])
    return lo, hi


def tier_position(instrument, rank, rank_hi=None, rank_lo=None):
    tier = tier_for_rank(instrument, rank)
    if tier is None:
        return None
    effective_hi = max(rank_hi or 0, rank)
    effective_lo = min(rank_lo, rank) if rank_lo is not None else None
    band = tier_band(instrument, tier, effective_hi, effective_lo)
    if band is None or band[1] <= band[0]:
        return 0
    position = float(rank - band[0]) / float(band[1] - band[0])
    return max(0.0, min(1.0, position))
