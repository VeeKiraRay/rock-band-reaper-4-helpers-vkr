"""User-facing annotations for calibrated difficulty suggestions.

This is the Python 2.7 counterpart of difficulty_explain.lua. It describes
unusual measured properties; it deliberately does not treat regression
coefficients as causal explanations.
"""

from __future__ import unicode_literals

from .difficulty_predict import factor_z_scores, out_of_range
from .difficulty_tiers import tier_band, tier_name


NOTABLE_Z = 1.0
MAX_EXPLANATIONS = 3
COLLINEAR_R = 0.70
BOUNDARY_LOW = 0.15
BOUNDARY_HIGH = 0.85
BRE_NOTABLE_FRAC = 0.05


FACTOR_INFO = {
    'playing_s': ('playing time', 'Long playing time - the demand is sustained',
                  'Short playing time'),
    'notes_total': ('total gems', 'A very high total gem count',
                    'Few gems overall'),
    'total_changes': ('total changes',
                      'A very high number of gem changes overall',
                      'Few gem changes overall'),
    'density_avg': ('average gem density', 'High average gem density',
                    'Low average gem density'),
    'density_peak': ('peak gem density', 'Very high peak gem density',
                     'No especially dense passages'),
    'density_peak_noroll': (
        'peak gem density outside rolls', 'Very high peak gem density',
        'No especially dense passages'),
    'attack_density_avg': ('average attack rate',
                           'A high average attack rate',
                           'A low average attack rate'),
    'attack_density_peak': ('peak attack rate',
                            'Very high peak attack density',
                            'No especially fast passages'),
    'attack_density_peak_noroll': (
        'peak attack rate outside rolls', 'Very high peak attack density',
        'No especially fast passages'),
    'change_rate': ('change rate', 'Gem shapes change very often',
                    'Gem shapes change rarely'),
    'tight_p10': ('tightest change spacing',
                  'Even the tightest changes are widely spaced',
                  'Long stretches of closely spaced changes'),
    'tight_med': ('typical change spacing',
                  'Changes are widely spaced throughout',
                  'Changes arrive close together throughout'),
    'chord_size_mean': ('average chord size', 'Mostly chords',
                        'Mostly single notes'),
    'chord_span_mean': ('average chord width', 'Wide chord shapes',
                        'Narrow chord shapes'),
    'chord_change_frac': ('changes into a chord',
                          'Most changes re-form a whole chord shape',
                          'Most changes move a single note'),
    'move_mean': ('average hand movement',
                  'Large average hand movement between gems',
                  'Very little hand movement'),
    'move_p90': ('largest hand movements',
                 'Frequent large jumps between notes',
                 'Few large jumps between notes'),
    'anchor_frac': ('anchored changes',
                    'The hand can stay anchored through most changes',
                    'Almost every change moves the hand'),
    'solo_frac_marked': ('authored solo coverage',
                         'A large share of the chart sits inside an authored solo',
                         'Little or no authored solo'),
    'solo_change_ratio': ('solo vs the rest',
                          'Difficulty is concentrated in the authored solo',
                          'The authored solo is no busier than the rest of the chart'),
    'sustain_frac': ('sustained notes', 'Many sustained notes',
                     'Almost no sustains'),
    'force_hopo_rate': ('forced hammer-on markers',
                        'Frequent forced hammer-on markers',
                        'Few forced hammer-on markers'),
    'force_strum_rate': ('forced strum markers',
                         'Frequent forced strum markers',
                         'Few forced strum markers'),
    'tremolo_frac': ('tremolo lanes', 'Long tremolo lanes',
                     'Almost no tremolo lanes'),
    'trill_frac': ('trill lanes', 'Long trill lanes',
                   'Almost no trill lanes'),
    'entropy_h2': ('shape unpredictability',
                   'The next gem shape is hard to predict',
                   'Highly repetitive, predictable figures'),
    'entropy_h2_rel': ('motion unpredictability',
                       'The next hand motion is hard to predict',
                       'One figure repeated, moved around the lanes'),
    'complex_peak': ('dense and unpredictable together',
                     'Dense and unpredictable at the same time',
                     'Where it is dense, it is predictable'),
    'kick_density': ('kick rate', 'A busy kick pattern',
                     'A sparse kick pattern'),
    'kick_density_peak': ('peak kick rate', 'Very fast kick passages',
                          'No especially fast kick passages'),
    'hand_density_peak_noroll': (
        'peak hand rate outside rolls', 'Very fast hand passages',
        'No especially fast hand passages'),
    'stick_size_mean': ('limbs landing together',
                        'Many hits land on several limbs at once',
                        'Mostly single-limb streams'),
    'tom_frac': ('tom coverage', 'A lot of toms', 'Little to no toms'),
    'roll_frac': ('roll lanes', 'Long roll lanes', 'Almost no roll lanes'),
    'offbeat_frac': ('offbeat onsets', 'Most onsets fall off the beat',
                     'Most onsets land squarely on the beat'),
    'pro_stations_peak': ('pads covered in the busiest passage',
                          'The busiest passages move between many different pads',
                          'The busiest passages stay on a few pads'),
    'syl_density_avg': ('syllable rate', 'A high syllable rate',
                        'A slow syllable rate'),
    'syl_density_peak': ('peak syllable rate',
                         'Very fast syllable passages',
                         'No especially fast passages'),
    'pc_interval_mean': ('average interval',
                         'Large average intervals between notes',
                         'Mostly stepwise motion'),
    'notated_range': ('notated range', 'A wide vocal register',
                      'A narrow vocal register'),
    'pitch_p90': ('upper register', 'Sits high in the vocal register',
                  'Sits low in the vocal register'),
    'octave_jump_rate': ('octave leaps', 'Frequent octave leaps',
                         'Few octave leaps'),
    'parts_3': ('full three-part harmony',
                'Full three-part harmony is associated with the official vocal scale',
                'Fewer than three vocal parts'),
    'high_time_70': ('time sung high',
                     'Much of the singing sits above the top of a comfortable range',
                     'Little time spent high in the register'),
    'pc_change_rate': ('note change rate',
                       'The melody changes note constantly',
                       'The melody holds or repeats notes'),
}


def dot_count(tier):
    return min(tier or 0, 5)


def _correlation(model, left, right):
    correlations = model.get('corr') or {}
    return correlations.get('%s|%s' % (left, right),
                            correlations.get('%s|%s' % (right, left), 0))


def explanations(record):
    rows = sorted(factor_z_scores(record['model'], record['factors']),
                  key=lambda row: (-abs(row['z']), row['key']))
    chosen = []
    for row in rows:
        if len(chosen) >= MAX_EXPLANATIONS:
            break
        info = FACTOR_INFO.get(row['key'])
        if not info or abs(row['z']) < NOTABLE_Z:
            continue
        if any(abs(_correlation(record['model'], prior['key'], row['key'])) >=
               COLLINEAR_R for prior in chosen):
            continue
        chosen.append({
            'key': row['key'],
            'text': info[1] if row['z'] > 0 else info[2],
        })
    return chosen


def ruler(record):
    band = tier_band(record['instrument'], record['tier'],
                     record['model']['rank_hi'], record['model']['rank_lo'])
    if not band:
        return None
    tier = record['tier']
    lo_label = ('min %d' % band[0] if tier == 0 else
                '%s (%d)' % (tier_name(tier), band[0]))
    hi_label = ('max %d' % band[1] if tier == 6 else
                '%s (%d)' % (tier_name(tier + 1), band[1]))
    pinned = None
    if record['clamped']:
        pinned = ('hi' if record['raw_rank'] > record['model']['rank_hi']
                  else 'lo')
    return {'lo': band[0], 'hi': band[1], 'lo_label': lo_label,
            'hi_label': hi_label, 'pos': record['tier_position'],
            'pinned': pinned}


def _actual_items(actual):
    return enumerate(actual) if isinstance(actual, list) else actual.items()


def reliability_note(model, tier, label):
    reliability = model.get('reliability') or {}
    here = reliability.get(tier)
    if not here or not here.get('n_pred'):
        return None
    if here['n_pred'] >= 15:
        harder = easier = 0
        for actual_tier, count in _actual_items(here.get('actual') or {}):
            if actual_tier >= tier + 2:
                harder += count
            elif actual_tier <= tier - 2:
                easier += count
        hard_share = float(harder) / here['n_pred']
        easy_share = float(easier) / here['n_pred']
        if hard_share >= 0.10 or easy_share >= 0.10:
            worse = hard_share >= easy_share
            share = hard_share if worse else easy_share
            return ('Of %d reference charts this model rated %s, %.0f%% were '
                    'officially two or more tiers %s.' %
                    (here['n_pred'], tier_name(tier), share * 100,
                     'harder' if worse else 'easier'))
    if tier >= 4:
        predicted = sum((reliability.get(value) or {}).get('n_pred', 0)
                        for value in (5, 6))
        actual = sum((reliability.get(value) or {}).get('n_act', 0)
                     for value in (5, 6))
        if actual and float(predicted) / actual < 0.50:
            tail = ('A rating this high is unusual from it.' if tier >= 5 else
                    'A genuinely top-end chart is likely to be rated below '
                    'its real difficulty.')
            return ('This model rarely rates %s at the top of the scale: %d '
                    'reference charts are officially in the highest two '
                    'tiers and it placed %d there. %s' %
                    (label, actual, predicted, tail))
    return None


def warnings(record):
    result = []
    model = record['model']
    factors = record['factors']
    position = record.get('tier_position')
    if position is not None and not record['clamped']:
        if position <= BOUNDARY_LOW and record['tier'] > 0:
            result.append('Near the lower tier boundary - the tier below is a close call.')
        elif position >= BOUNDARY_HIGH and record['tier'] < 6:
            result.append('Near the upper tier boundary - the tier above is a close call.')
    concentration = model.get('conc') or {}
    solo_ratio = factors.get('solo_change_ratio', 0)
    if (concentration.get('solo_change_ratio', 0) > 1 and
            solo_ratio > concentration['solo_change_ratio']):
        result.append(
            'The authored solo is %.1fx busier than the rest of the chart. '
            'Rated on its hardest passage this would read higher; players '
            'wanting a sustained challenge may find the rest easier than '
            'the tier suggests.' % solo_ratio)
    elif (concentration.get('density_ratio') and
          factors.get('density_avg', 0) > 0 and
          factors.get('density_peak', 0) /
          factors['density_avg'] > concentration['density_ratio']):
        ratio = factors['density_peak'] / factors['density_avg']
        result.append('Difficulty is concentrated in a short passage - its '
                      'busiest stretch is %.1fx the chart average.' % ratio)
    if record['clamped']:
        if record['raw_rank'] > model['rank_hi']:
            result.append('%d is as high as this tool can score, and this '
                          'chart came in above it. It may well deserve more '
                          'than %s.' %
                          (model['rank_hi'], record['tier_name']))
        else:
            result.append('%d is as low as this tool can score, and this '
                          'chart came in under it. Worth judging for yourself '
                          'whether %s is right.' %
                          (model['rank_lo'], record['tier_name']))
    if record.get('span_source') in ('fallback_idle_only',
                                     'fallback_no_events'):
        result.append('This track has no authored playing states, so playing '
                      'time was inferred from the notes. Authoring them will '
                      'make the suggestion more reliable.')
    reliability = reliability_note(model, record['tier'], record['label'])
    if reliability:
        result.append(reliability)
    return result


def annotate_suggestion(record, label):
    record['label'] = label
    record['explanations'] = explanations(record)
    record['warnings'] = warnings(record)
    record['ruler'] = ruler(record)
    record['out_of_range'] = out_of_range(
        record['model'], record['factors'])
    return record


def song_notes(records):
    scored = [record for record in records if record.get('suggestion')]
    with_bre = [record['suggestion'] for record in scored
                if record['suggestion'].get('bre_gem_frac') is not None]
    if not with_bre:
        return []
    seconds = max([record.get('bre_seconds', 0) for record in with_bre] or [0])
    parts = ['%s %.0f%%' % (record['label'], record['bre_gem_frac'] * 100)
             for record in with_bre
             if record['bre_gem_frac'] >= BRE_NOTABLE_FRAC]
    text = 'This song has a Big Rock Ending'
    if seconds > 0:
        text += ' (%.0f seconds)' % seconds
    text += ('. Rock Band 3 does not require the notes authored there to be '
             'played, but they are rated as authored - nothing is excluded '
             'from the suggestion.')
    if parts:
        text += ' Gems inside it: %s.' % ', '.join(parts)
    return [text]
