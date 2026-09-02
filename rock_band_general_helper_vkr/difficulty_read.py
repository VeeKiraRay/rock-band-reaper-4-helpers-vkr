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
from .difficulty_predict import predict_rank
from .difficulty_score import derive_spans_from_events, normalize_spans, score_bass
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
        parsed = parse_midi_chunk(host.read_item_chunk(item))
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
    model = RB_DIFFICULTY_MODELS['bass']
    rank, clamped, raw_rank, error = predict_rank(model, factors)
    if error:
        raise DifficultyReadError('Bass model factor missing: %s' % error)
    tier = tier_for_rank('bass', rank)
    return {
        'rank': rank,
        'raw_rank': raw_rank,
        'clamped': clamped,
        'tier': tier,
        'tier_name': tier_name(tier),
        'tier_position': tier_position(
            'bass', rank, model['rank_hi'], model['rank_lo']),
        'factors': factors,
        'span_source': span_source,
        'animation_states': state_count,
    }
