"""Legacy REAPER chart reader for calibrated difficulty scoring.

The REAPER 4.20 Python API has no MIDI event API. This reader converts the
verified item-state chunk ticks into project quarter notes and seconds through
the old TimeMap2 functions. Take source offsets are applied in musical time;
stretched takes remain guarded until their legacy mapping has an exact
compatibility proof.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import re

from lib.midi_chunk import SUPPORTED_PPQ, parse_midi_chunk
from .difficulty_models import RB_DIFFICULTY_MODELS
from .difficulty_predict import display_rank, predict_rank
from .difficulty_score import (
    derive_spans_from_events,
    normalize_spans,
    normalize_vocal_phrases,
    score_bass,
    score_guitar,
    score_drums,
    score_keys,
    score_vocals,
)
from .difficulty_tiers import tier_for_rank, tier_name, tier_position


ANIM_PLAYING = frozenset(('[play]', '[play_solo]', '[mellow]', '[intense]'))
ANIM_IDLE = frozenset(('[idle]', '[idle_realtime]', '[idle_intense]'))
CHORD_WINDOW_S = 0.002
_SOFFS_RE = re.compile(
    r'^\s*SOFFS\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)'
    r'(?:\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?))?',
    re.MULTILINE)


class DifficultyReadError(Exception):
    pass


def _source_offset_qn(host, chunk, position, offset_seconds, start_qn):
    """Prefer REAPER's explicit musical offset, with an old-format fallback."""
    match = _SOFFS_RE.search(chunk)
    if match and match.group(2) is not None:
        return float(match.group(2))
    return host.time_to_qn(position + offset_seconds) - start_qn


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
        start_qn = host.time_to_qn(position)
        # D_STARTOFFS is a source-time offset. For an unstretched MIDI take,
        # convert that local duration through the project tempo map at the
        # item start. A positive offset means the item begins later in its
        # source, so source tick zero lies before the item position.
        offset_qn = _source_offset_qn(
            host, chunk, position, offset, start_qn)
        contexts.append({
            'item': item,
            'parsed': parsed,
            'position': position,
            'end': position + host.item_length(item),
            'start_qn': start_qn,
            'offset_qn': offset_qn,
        })
    return contexts


def _tick_to_qn(context, tick):
    return (context['start_qn'] - context['offset_qn'] +
            float(tick) / context['parsed'].ppq)


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


def read_vocal_notes(host, contexts):
    notes = []
    for context in contexts:
        by_tick = {}
        for note in context['parsed'].notes():
            if 36 <= note.pitch <= 84:
                record = {
                    's': _tick_to_time(host, context, note.start_tick),
                    'e': _tick_to_time(host, context, note.end_tick),
                    'qn': _tick_to_qn(context, note.start_tick),
                    'qn_e': _tick_to_qn(context, note.end_tick),
                    'pitch': note.pitch,
                    'lyric': None,
                }
                notes.append(record)
                by_tick[note.start_tick] = record
        for event in context['parsed'].text_events():
            if event.meta_type in (0x01, 0x05):
                note = by_tick.get(event.absolute_tick)
                if note is not None and note['lyric'] is None:
                    note['lyric'] = event.meta_payload
    notes.sort(key=lambda note: note['s'])
    return notes


def read_phrase_spans(host, contexts):
    spans = []
    for context in contexts:
        for note in context['parsed'].notes():
            if note.pitch in (105, 106):
                start = _tick_to_time(host, context, note.start_tick)
                end = _tick_to_time(host, context, note.end_tick)
                if end > start:
                    spans.append({'s': start, 'e': end})
    return normalize_vocal_phrases(spans)


def read_percussion_spans(host, contexts):
    marks = []
    pattern = re.compile(r'^\[(tambourine|cowbell|clap)_(start|end)\]$')
    for context in contexts:
        for event in context['parsed'].text_events():
            if event.meta_type not in (0x01, 0x05):
                continue
            message = event.meta_payload or ''
            try:
                message = message.decode('latin-1')
            except AttributeError:
                pass
            match = pattern.match(message)
            if match:
                marks.append({
                    't': _tick_to_time(host, context, event.absolute_tick),
                    'kind': match.group(2),
                })
    marks.sort(key=lambda mark: mark['t'])
    spans = []
    open_at = None
    for mark in marks:
        if mark['kind'] == 'start':
            if open_at is None:
                open_at = mark['t']
        elif open_at is not None:
            if mark['t'] > open_at:
                spans.append({'s': open_at, 'e': mark['t']})
            open_at = None
    if open_at is not None:
        track_end = max([context['end'] for context in contexts] or [0])
        if track_end > open_at:
            spans.append({'s': open_at, 'e': track_end})
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
        'instrument': instrument,
        'model': model,
        'status': model.get('status'),
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


def read_coda_time(host, track):
    best = None
    for context in _load_items(host, track):
        for event in context['parsed'].text_events():
            if event.meta_type not in (0x01, 0x05):
                continue
            message = event.meta_payload or ''
            try:
                message = message.decode('latin-1')
            except AttributeError:
                pass
            if 'coda' in message.lower():
                moment = _tick_to_time(host, context, event.absolute_tick)
                if best is None or moment < best:
                    best = moment
    return best


def _add_bre_context(result, events, coda_time):
    if coda_time is None:
        return result
    inside = sum(1 for event in events if event['s'] >= coda_time)
    last = max([event.get('e', 0) for event in events] or [0])
    result['bre_gem_frac'] = (float(inside) / len(events)
                              if events else 0)
    result['bre_seconds'] = max(0, last - coda_time)
    return result


def suggest_bass(host, track, coda_time=None):
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
    return _add_bre_context(result, events, coda_time)


def suggest_guitar(host, track, coda_time=None):
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
    return _add_bre_context(result, events, coda_time)


def _suggest_keys(host, track, instrument, lo, hi, span_track=None,
                  coda_time=None):
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
    return _add_bre_context(result, events, coda_time)


def suggest_keys(host, track, coda_time=None):
    return _suggest_keys(host, track, 'keys', 96, 100,
                         coda_time=coda_time)


def suggest_real_keys(host, track, span_track=None, coda_time=None):
    # PART REAL_KEYS_X has no animation states. The modern scorer reads them
    # from PART KEYS, falling back to the Pro Keys note track when absent.
    return _suggest_keys(
        host, track, 'real_keys', 48, 72, span_track or track,
        coda_time)


def suggest_drums(host, track, coda_time=None):
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
    return _add_bre_context(result, events, coda_time)


def suggest_vocals(host, track, vocal_parts=1):
    contexts = _load_items(host, track)
    notes = read_vocal_notes(host, contexts)
    spans = read_phrase_spans(host, contexts)
    state_count = 0
    span_source = 'phrase'
    if not spans:
        spans, state_count, unused_solos = read_playing_spans(
            host, contexts)
        span_source = 'anim'
    if not spans:
        spans = derive_spans_from_events(notes)
        span_source = ('fallback_idle_only' if state_count > 0
                       else 'fallback_no_events')
    factors = score_vocals(
        notes, spans,
        percussion_spans=read_percussion_spans(host, contexts),
        vocal_parts=vocal_parts)
    result = _prediction('vocals', factors)
    result.update({
        'span_source': span_source,
        'animation_states': state_count,
        'vocal_parts': vocal_parts,
    })
    return result


def count_vocal_parts(host, harmony_tracks):
    """Count HARM2/HARM3 tracks that contain sung notes."""
    parts = 1
    for track in harmony_tracks:
        if read_vocal_notes(host, _load_items(host, track)):
            parts += 1
    return parts
