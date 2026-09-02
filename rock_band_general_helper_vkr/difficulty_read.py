"""Legacy REAPER chart reader for calibrated difficulty scoring.

The REAPER 4.20 Python API has no MIDI event API. This reader converts the
verified item-state chunk ticks into project quarter notes and seconds through
the old TimeMap2 functions. Non-zero source offsets and stretched takes are
refused until their legacy mapping has an exact compatibility proof.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk import SUPPORTED_PPQ, parse_midi_chunk
from .difficulty_models import RB_DIFFICULTY_MODELS
from .difficulty_predict import display_rank, predict_rank
from .difficulty_score import (
    derive_spans_from_events,
    normalize_spans,
    score_bass,
    score_guitar,
    score_drums,
    score_keys,
)
from .difficulty_tiers import tier_for_rank, tier_name, tier_position


ANIM_PLAYING = frozenset(('[play]', '[play_solo]', '[mellow]', '[intense]'))
ANIM_IDLE = frozenset(('[idle]', '[idle_realtime]', '[idle_intense]'))
CHORD_WINDOW_S = 0.002


class DifficultyReadError(Exception):
    pass


def _load_items(host, track):
    contexts = []
    for index in range(host.item_count(track)):
        item = host.get_item(track, index)
        chunk = host.read_item_chunk(item)
        # Match the modern reader's TakeIsMIDI guard: unrelated audio items on
        # an authored track are ignored, not treated as a chart-read failure.
        if '<SOURCE MIDI' not in chunk:
            continue
        take = host.active_take(item)
        if not take:
            raise DifficultyReadError('item %d has no active take' % (index + 1))
        offset = host.take_start_offset(take)
        rate = host.take_play_rate(take)
        if abs(offset) > 1e-9:
            raise DifficultyReadError(
                'item %d has a non-zero take start offset (%g)' %
                (index + 1, offset))
        if abs(rate - 1.0) > 1e-9:
            raise DifficultyReadError(
                'item %d has a non-unit take play rate (%g)' %
                (index + 1, rate))
        parsed = parse_midi_chunk(chunk)
        if parsed.ppq != SUPPORTED_PPQ:
            raise DifficultyReadError(
                'item %d uses %d PPQ; calibrated scoring currently requires '
                '%d PPQ' % (index + 1, parsed.ppq, SUPPORTED_PPQ))
        position = host.item_position(item)
        contexts.append({
            'item': item,
            'parsed': parsed,
            'position': position,
            'end': position + host.item_length(item),
            'start_qn': host.time_to_qn(position),
        })
    return contexts


def _tick_to_qn(context, tick):
    return context['start_qn'] + float(tick) / context['parsed'].ppq


def _tick_to_time(host, context, tick):
    return host.qn_to_time(_tick_to_qn(context, tick))


def read_gem_events(host, contexts, lo=96, hi=100):
    notes = []
    for context in contexts:
        for note in context['parsed'].notes():
            if lo <= note.pitch <= hi:
                notes.append({
                    's': _tick_to_time(host, context, note.start_tick),
                    'e': _tick_to_time(host, context, note.end_tick),
                    'qn': _tick_to_qn(context, note.start_tick),
                    'qn_e': _tick_to_qn(context, note.end_tick),
                    'pitch': note.pitch,
                })
    notes.sort(key=lambda note: (note['s'], note['pitch']))
    events = []
    index = 0
    while index < len(notes):
        first = notes[index]
        event = {
            's': first['s'], 'e': first['e'],
            'qn': first['qn'], 'qn_e': first['qn_e'],
            'pitches': [first['pitch']], 'held': [],
        }
        following = index + 1
        while (following < len(notes) and
               notes[following]['s'] - event['s'] <= CHORD_WINDOW_S):
            note = notes[following]
            event['pitches'].append(note['pitch'])
            if note['e'] > event['e']:
                event['e'] = note['e']
                event['qn_e'] = note['qn_e']
            following += 1
        event['pitches'].sort()
        events.append(event)
        index = following
    return events


def read_playing_spans(host, contexts):
    states = []
    for context in contexts:
        for event in context['parsed'].text_events(0x01):
            message = (event.meta_payload or '').lower()
            if message in ANIM_PLAYING or message in ANIM_IDLE:
                states.append({
                    't': _tick_to_time(host, context, event.absolute_tick),
                    'playing': message in ANIM_PLAYING,
                    'solo': message == '[play_solo]',
                })
    states.sort(key=lambda state: state['t'])
    track_end = max([context['end'] for context in contexts] or [0])
    spans = []
    solo_spans = []
    open_at = None
    solo_at = None
    for state in states:
        if state['playing']:
            if open_at is None:
                open_at = state['t']
            if state['solo']:
                if solo_at is None:
                    solo_at = state['t']
            elif solo_at is not None:
                if state['t'] > solo_at:
                    solo_spans.append({'s': solo_at, 'e': state['t']})
                solo_at = None
        else:
            if open_at is not None:
                if state['t'] > open_at:
                    spans.append({'s': open_at, 'e': state['t']})
                open_at = None
            if solo_at is not None:
                if state['t'] > solo_at:
                    solo_spans.append({'s': solo_at, 'e': state['t']})
                solo_at = None
    if open_at is not None and track_end > open_at:
        spans.append({'s': open_at, 'e': track_end})
    if solo_at is not None and track_end > solo_at:
        solo_spans.append({'s': solo_at, 'e': track_end})
    return normalize_spans(spans), len(states), normalize_spans(solo_spans)


def read_marker_spans(host, contexts, pitch):
    spans = []
    for context in contexts:
        for note in context['parsed'].notes():
            if note.pitch == pitch:
                start = _tick_to_time(host, context, note.start_tick)
                end = _tick_to_time(host, context, note.end_tick)
                if end > start:
                    spans.append({'s': start, 'e': end})
    return normalize_spans(spans)


def count_pitches(contexts, pitches):
    counts = dict((pitch, 0) for pitch in pitches)
    for context in contexts:
        for note in context['parsed'].notes():
            if note.pitch in counts:
                counts[note.pitch] += 1
    return counts


def _prediction(instrument, factors):
    model = RB_DIFFICULTY_MODELS[instrument]
    rank, clamped, raw_rank, error = predict_rank(model, factors)
    if error:
        raise DifficultyReadError(
            '%s model factor missing: %s' % (instrument, error))
    tier = tier_for_rank(instrument, rank)
    return {
        'rank': rank,
        'rank_shown': display_rank(rank),
        'raw_rank': raw_rank,
        'clamped': clamped,
        'tier': tier,
        'tier_name': tier_name(tier),
        'tier_position': tier_position(
            instrument, rank, model['rank_hi'], model['rank_lo']),
        'factors': factors,
    }


def suggest_bass(host, track):
    contexts = _load_items(host, track)
    events = read_gem_events(host, contexts)
    spans, state_count, unused_solos = read_playing_spans(host, contexts)
    span_source = 'anim'
    if not spans:
        spans = derive_spans_from_events(events)
        span_source = ('fallback_idle_only' if state_count > 0
                       else 'fallback_no_events')
    factors = score_bass(events, spans)
    result = _prediction('bass', factors)
    result.update({
        'span_source': span_source,
        'animation_states': state_count,
    })
    return result


def suggest_guitar(host, track):
    contexts = _load_items(host, track)
    events = read_gem_events(host, contexts)
    spans, state_count, unused_solos = read_playing_spans(host, contexts)
    span_source = 'anim'
    if not spans:
        spans = derive_spans_from_events(events)
        span_source = ('fallback_idle_only' if state_count > 0
                       else 'fallback_no_events')
    overrides = count_pitches(contexts, (101, 102))
    factors = score_guitar(
        events,
        spans,
        marked_solo_spans=read_marker_spans(host, contexts, 103),
        tremolo_spans=read_marker_spans(host, contexts, 126),
        trill_spans=read_marker_spans(host, contexts, 127),
        force_hopo_count=overrides[101],
        force_strum_count=overrides[102])
    result = _prediction('guitar', factors)
    result.update({
        'span_source': span_source,
        'animation_states': state_count,
        'force_hopo_count': overrides[101],
        'force_strum_count': overrides[102],
    })
    return result


def _suggest_keys(host, track, instrument, lo, hi, span_track=None):
    contexts = _load_items(host, track)
    events = read_gem_events(host, contexts, lo, hi)
    span_contexts = (_load_items(host, span_track)
                     if span_track is not None else contexts)
    spans, state_count, unused_solos = read_playing_spans(
        host, span_contexts)
    span_source = 'anim'
    if not spans:
        spans = derive_spans_from_events(events)
        span_source = ('fallback_idle_only' if state_count > 0
                       else 'fallback_no_events')
    factors = score_keys(
        events, spans, pro_keys=(instrument == 'real_keys'))
    result = _prediction(instrument, factors)
    result.update({
        'span_source': span_source,
        'animation_states': state_count,
    })
    return result


def suggest_keys(host, track):
    return _suggest_keys(host, track, 'keys', 96, 100)


def suggest_real_keys(host, track, span_track=None):
    # PART REAL_KEYS_X has no animation states. The modern scorer reads them
    # from PART KEYS, falling back to the Pro Keys note track when absent.
    return _suggest_keys(
        host, track, 'real_keys', 48, 72, span_track or track)


def suggest_drums(host, track):
    contexts = _load_items(host, track)
    events = read_gem_events(host, contexts)
    spans, state_count, unused_solos = read_playing_spans(host, contexts)
    span_source = 'anim'
    if not spans:
        spans = derive_spans_from_events(events)
        span_source = ('fallback_idle_only' if state_count > 0
                       else 'fallback_no_events')
    tom_spans = {}
    for gem_pitch, marker_pitch in ((98, 110), (99, 111), (100, 112)):
        marker_spans = read_marker_spans(host, contexts, marker_pitch)
        if marker_spans:
            tom_spans[gem_pitch] = marker_spans
    roll_spans = (read_marker_spans(host, contexts, 126) +
                  read_marker_spans(host, contexts, 127))
    factors = score_drums(
        events, spans, tom_spans=tom_spans, roll_spans=roll_spans)
    result = _prediction('drum', factors)
    result.update({
        'span_source': span_source,
        'animation_states': state_count,
        'tom_marker_count': sum(len(value) for value in tom_spans.values()),
        'roll_marker_count': len(roll_spans),
    })
    return result
