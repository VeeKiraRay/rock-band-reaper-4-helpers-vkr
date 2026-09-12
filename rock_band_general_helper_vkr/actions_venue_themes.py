"""Guarded whole-song Venue theme generation.

Modern counterparts: venue_generator.lua, venue_camera.lua,
venue_lighting.lua, and venue_awareness.lua.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import random

from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources
from .actions_venue_validate_camera import coop_required_instruments
from .venue import (
    CAMERA_EVENTS, INSTRUMENT_NAMES, INSTRUMENT_TRACKS, VenueReadError,
    build_event_sections, find_named_track, read_named_track,
)
from .venue_themes import (
    build_lighting_pool, build_postproc_pool, get_section_preset,
    get_theme_camera_interval,
)


MANUAL_LIGHTING = frozenset(
    '[lighting (%s)]' % name for name in
    ('verse', 'chorus', 'manual_cool', 'manual_warm', 'dischord', 'stomp'))
CAMERA_PACING = (None, 'minimal', 'slow', 'medium', 'fast', 'crazy')
KEYFRAME_ALIGN_LABELS = (
    'Keyframe rate only', 'Closest beat', 'Downbeat', 'Guitar notes',
    'Bass notes', 'Keys notes', 'Drum kicks', 'Drum snare',
)
INSTRUMENT_ALIGN = {
    3: ('PART GUITAR', 96, 100),
    4: ('PART BASS', 96, 100),
    5: ('PART KEYS', 96, 100),
    6: ('PART DRUMS', 96, 96),
    7: ('PART DRUMS', 97, 97),
}


class VenueThemeGenerationError(Exception):
    pass


def _project_qn_to_tick(context, qn):
    return int(round((qn - context['start_qn'] + context['offset_qn']) *
                     context['parsed'].ppq))


def _tick_to_project_qn(context, tick):
    return (context['start_qn'] - context['offset_qn'] +
            float(tick) / context['parsed'].ppq)


def _snap_half(qn):
    return round(float(qn) * 2.0) / 2.0


def _next_measure_qn(host, qn):
    """Find the next REAPER measure boundary, with a 4/4 fallback."""
    measure_at = getattr(host, 'measure_at', None)
    if measure_at is None:
        return (int(float(qn) / 4.0) + 1) * 4.0
    try:
        current = measure_at(host.qn_to_time(qn + 1e-7))
    except Exception:
        current = None
    if current is None:
        return (int(float(qn) / 4.0) + 1) * 4.0
    low = float(qn)
    high = low + 0.25
    for unused_index in range(256):
        if measure_at(host.qn_to_time(high)) != current:
            break
        low, high = high, high + 0.25
    else:
        return (int(float(qn) / 4.0) + 1) * 4.0
    for unused_index in range(30):
        middle = (low + high) / 2.0
        if measure_at(host.qn_to_time(middle)) == current:
            low = middle
        else:
            high = middle
    return high


def _choose(pool, previous, rng):
    if not pool:
        return None
    alternatives = [value for value in pool if value != previous]
    return rng.choice(alternatives or list(pool))


def _muted_instruments(host):
    muted = {}
    for letter, name in INSTRUMENT_TRACKS.items():
        track = find_named_track(host, name)
        if track is None or host.track_muted(track):
            muted[letter] = True
    return muted


def _active_camera_pool(muted):
    result = []
    for bare in CAMERA_EVENTS:
        if not bare.startswith('coop_'):
            continue
        message = '[%s]' % bare
        if not any(muted.get(letter)
                   for letter in coop_required_instruments(message)):
            result.append(message)
    return result


def _read_sections(host, song_end):
    try:
        unused_track, contexts, events = read_named_track(host, 'EVENTS')
    except VenueReadError:
        return [], [], []
    return build_event_sections(events, song_end), contexts, events


def _event_time(events, message):
    matches = [event['t'] for event in events
               if event['meta_type'] == 1 and event['msg'] == message]
    return min(matches) if matches else None


def _instrument_note_qns(host, track_name, pitch_lo, pitch_hi):
    track = find_named_track(host, track_name)
    if track is None:
        return [], []
    from .difficulty_read import _load_items
    contexts = _load_items(host, track)
    qns = []
    for context in contexts:
        for note in context['parsed'].notes():
            if pitch_lo <= note.pitch <= pitch_hi:
                qns.append(_tick_to_project_qn(context, note.start_tick))
    return sorted(qns), contexts


def _keyframes(start_qn, end_qn, rate, align, subdivision,
               note_qns=None, next_measure=None):
    events = [(start_qn, '[first]', True)]
    rate = max(1.0, float(rate))
    if align >= 3:
        step = (0.25 if subdivision == 2 else
                0.5 if subdivision == 1 else 1.0)
        position = (int(start_qn / step) + 1) * step
        tolerance = 1.0 / 32.0
        note_qns = note_qns or []
        while position < end_qn:
            if any(abs(value - position) <= tolerance for value in note_qns):
                events.append((position, '[next]', True))
            position += step
        return events
    if align == 2:
        position = (next_measure(start_qn) if next_measure else
                    (int(start_qn / 4.0) + 1) * 4.0)
    else:
        anchor = max(start_qn, round(start_qn)) if align == 1 else start_qn
        if align == 1 and anchor > start_qn:
            events.append((anchor, '[next]', True))
        beat_anchor = anchor if align == 1 else round(start_qn)
        position = beat_anchor + rate
    while position < end_qn:
        events.append((position, '[next]', True))
        position += rate
    return events


def _resolved_pacing(theme, options, bpm):
    mode = int(options.get('camera_pacing', 0))
    if 1 <= mode <= 5:
        return get_theme_camera_interval(CAMERA_PACING[mode], bpm)
    if mode == 6:
        base = int(options.get('camera_custom', 16))
        return int(base * 1.5 + 0.5) if bpm >= 150.0 else base
    return get_theme_camera_interval(theme.get('camera_pacing'), bpm)


def _camera_events(start_qn, end_qn, music_start_qn, pool, interval_16ths,
                   jitter, phrase_qns, rng):
    events = []
    previous = None
    if start_qn <= music_start_qn < end_qn:
        previous = _choose(pool, previous, rng)
        if previous:
            events.append((music_start_qn, previous, False))
    if phrase_qns is not None:
        positions = [value for value in phrase_qns
                     if music_start_qn < value < end_qn - 2.0]
    else:
        positions = []
        position = music_start_qn + interval_16ths / 4.0
        while position < end_qn - 2.0:
            positions.append(position)
            factor = rng.uniform(0.8, 1.2) if jitter else 1.0
            position += max(0.25, interval_16ths * factor / 4.0)
    for position in positions:
        previous = _choose(pool, previous, rng)
        if previous:
            events.append((position, previous, False))
    return events


def _camera_companions(events, pool, muted, rng):
    """Stack a g/b/k alternative for affected shots when all three exist."""
    if any(muted.get(letter) for letter in ('g', 'b', 'k')):
        return list(events), 0
    result = []
    count = 0
    for event in events:
        result.append(event)
        required = coop_required_instruments(event[1])
        if not any(letter in required for letter in ('g', 'b', 'k')):
            continue
        available = [letter for letter in ('g', 'b', 'k')
                     if letter not in required]
        candidates = [message for message in pool
                      if coop_required_instruments(message) in
                      [[letter] for letter in available]]
        companion = _choose(candidates, event[1], rng)
        if companion:
            result.append((event[0], companion, event[2]))
            count += 1
    return result, count


def build_theme_events(host, context, theme, options, rng=None):
    """Return generated project-QN events, statistics, and read guards."""
    rng = rng or random.Random()
    start_t, item_end_t = context['position'], context['end']
    start_qn = context['start_qn']
    item_end_qn = host.time_to_qn(item_end_t)
    sections, event_contexts, event_rows = _read_sections(host, item_end_t)
    end_t = _event_time(event_rows, '[end]')
    if end_t is None or not start_t < end_t <= item_end_t:
        end_t = item_end_t
        used_end_fallback = True
    else:
        used_end_fallback = False
    end_qn = host.time_to_qn(end_t)
    music_start_t = _event_time(event_rows, '[music_start]')
    if music_start_t is not None and start_t <= music_start_t < end_t:
        music_start_qn = host.time_to_qn(music_start_t)
        explicit_music_start = True
    else:
        measure_2 = _next_measure_qn(host, start_qn)
        measure_3 = _next_measure_qn(host, measure_2 + 1e-7)
        measure_4 = _next_measure_qn(host, measure_3 + 1e-7)
        candidates = (measure_3, measure_4)
        target = start_t + 3.0
        music_start_qn = min(candidates,
                             key=lambda value: abs(host.qn_to_time(value) - target))
        explicit_music_start = False

    muted = _muted_instruments(host)
    camera_pool = _active_camera_pool(muted)
    if not camera_pool:
        raise VenueThemeGenerationError(
            'All instrument tracks are muted or absent; no camera events are available.')
    beat_seconds = host.qn_to_time(start_qn + 1.0) - host.qn_to_time(start_qn)
    bpm = 60.0 / beat_seconds if beat_seconds > 0 else 120.0
    interval = _resolved_pacing(theme, options, bpm)

    guards = list(event_contexts)
    phrase_qns = None
    if int(options.get('camera_pacing', 0)) == 7:
        phrase_qns, phrase_contexts = _instrument_note_qns(
            host, 'PART VOCALS', 105, 105)
        guards.extend(phrase_contexts)
    generated = []
    generated.append((start_qn, '[coop_all_far]', False))
    generated.append((start_qn, '[lighting (intro)]', False))
    generated.append((start_qn, '[ProFilm_a.pp]', False))
    cameras = _camera_events(
        start_qn, end_qn, music_start_qn, camera_pool, interval,
        bool(options.get('camera_jitter', True)), phrase_qns, rng)
    cameras, companion_count = _camera_companions(
        cameras, camera_pool, muted, rng)
    generated.extend(cameras)

    align = int(options.get('keyframe_align', 0))
    subdivision = int(options.get('keyframe_subdivision', 0))
    note_qns = []
    if align in INSTRUMENT_ALIGN:
        note_qns, note_contexts = _instrument_note_qns(
            host, *INSTRUMENT_ALIGN[align])
        guards.extend(note_contexts)

    stats = {'camera': len(cameras) + 1, 'lighting': 2,
             'postproc': 1, 'control': 0, 'bonusfx': 0,
             'sections': len(sections)}
    current_lighting = '[lighting (intro)]'
    current_postproc = '[ProFilm_a.pp]'
    matched = 0
    previous_section_start = start_qn
    for section in sections:
        section_start = host.time_to_qn(section['t_start'])
        section_end = min(end_qn, host.time_to_qn(section['t_end']))
        if section_start >= end_qn or section_end <= start_qn:
            continue
        if section_start <= start_qn + 0.001:
            section_start = music_start_qn
        preset = get_section_preset(theme, section['name'], section['num'])
        if not preset:
            continue
        matched += 1
        lighting = _choose(build_lighting_pool(preset), current_lighting, rng)
        postproc = _choose(build_postproc_pool(preset), current_postproc, rng)
        if lighting:
            lighting_changed = lighting != current_lighting
            if lighting_changed:
                blend = float(preset.get('lightpreset_blendin', 0))
                blend_qn = section_start - blend
                if blend and blend_qn > previous_section_start:
                    generated.append((blend_qn, current_lighting, False))
                    stats['lighting'] += 1
                generated.append((section_start, lighting, False))
                stats['lighting'] += 1
            if lighting in MANUAL_LIGHTING:
                keyframes = _keyframes(
                    _snap_half(section_start), section_end,
                    preset.get('keyframe_rate', rng.randint(1, 4)), align,
                    subdivision, note_qns,
                    lambda value: _next_measure_qn(host, value))
                if not lighting_changed:
                    # A continuing manual preset gets a fresh [next] train but
                    # no [first], matching the modern section emitter.
                    keyframes = [event for event in keyframes
                                 if event[1] != '[first]']
                generated.extend(keyframes)
                stats['control'] += len(keyframes)
            current_lighting = lighting
        if postproc and postproc != current_postproc:
            blend = float(preset.get('postproc_blendin', 0))
            blend_qn = section_start - blend
            if blend and blend_qn > previous_section_start:
                generated.append((blend_qn, current_postproc, False))
                stats['postproc'] += 1
            generated.append((section_start, postproc, False))
            stats['postproc'] += 1
            current_postproc = postproc
        if preset.get('dircut_at_start'):
            generated.append((round(section_start),
                              '[%s]' % preset['dircut_at_start'], False))
            stats['camera'] += 1
        if preset.get('bonusfx_at_start'):
            generated.append((section_start, '[bonusfx]', False))
            stats['bonusfx'] += 1
        previous_section_start = section_start

    if not matched:
        default = get_section_preset(theme, 'default')
        pool = build_lighting_pool(default)
        position = start_qn + 8.0
        fallback_lighting = []
        while position < end_qn:
            lighting = _choose(pool, current_lighting, rng)
            if lighting:
                generated.append((position, lighting, False))
                fallback_lighting.append((position, lighting))
                stats['lighting'] += 1
                current_lighting = lighting
            position += rng.uniform(24.0, 40.0)
        for index, (lighting_qn, lighting) in enumerate(fallback_lighting):
            if lighting not in MANUAL_LIGHTING:
                continue
            span_end = (fallback_lighting[index + 1][0]
                        if index + 1 < len(fallback_lighting) else end_qn)
            keyframes = _keyframes(
                _snap_half(lighting_qn), span_end, rng.randint(1, 4),
                align, subdivision, note_qns,
                lambda value: _next_measure_qn(host, value))
            generated.extend(keyframes)
            stats['control'] += len(keyframes)

    music_end_t = _event_time(event_rows, '[music_end]')
    music_end_qn = (host.time_to_qn(music_end_t)
                    if music_end_t is not None else None)
    near_end = False
    if music_end_qn is not None and music_end_qn < end_qn:
        boundary = music_end_qn
        for unused_index in range(10):
            boundary = _next_measure_qn(host, boundary + 1e-7)
            if boundary >= end_qn:
                near_end = True
                break
    final_qn = music_end_qn if near_end else end_qn - 8.0
    if final_qn > start_qn:
        generated.append((final_qn, '[lighting (blackout_spot)]', False))

    rows = []
    for qn, message, no_snap in generated:
        placed_qn = qn if no_snap else _snap_half(qn)
        if start_qn <= placed_qn < end_qn:
            rows.append({'tick': _project_qn_to_tick(context, placed_qn),
                         'payload': message})
    stats.update({
        'matched': matched, 'muted': muted, 'available': len(camera_pool),
        'end_fallback': used_end_fallback,
        'explicit_music_start': explicit_music_start,
        'phrase_count': len(phrase_qns or ()),
        'companions': companion_count,
        'start_tick': _project_qn_to_tick(context, start_qn),
        'end_tick': _project_qn_to_tick(context, end_qn),
    })
    return rows, stats, guards


def generate_venue_events(host, theme, options, rng=None):
    try:
        unused_track, contexts, unused_events = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        raise VenueThemeGenerationError(str(exc))
    if len(contexts) != 1:
        raise VenueThemeGenerationError(
            'Themes gen currently requires exactly one MIDI item on VENUE; found %d.' %
            len(contexts))
    context = contexts[0]
    rows, stats, guards = build_theme_events(
        host, context, theme, options, rng)
    verify_unshared_pool_sources(host, [context])
    expected = context['parsed'].with_replaced_meta_events(
        stats['start_tick'], stats['end_tick'], rows, 0x01)
    guard_plans = [{
        'item': value['item'], 'original': value['chunk'],
        'fingerprint': value['fingerprint'], 'expected': value['chunk'],
    } for value in guards]
    apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'fingerprint': context['fingerprint'], 'expected': expected,
    }], 'Generate VENUE events from theme', guard_plans)

    muted_names = sorted(INSTRUMENT_NAMES[key] for key in stats['muted'])
    lines = [
        'Generated %d total events on VENUE track.' % len(rows), '',
        'Theme:              %s' % theme['label'],
        'Sections detected:  %d' % stats['sections'],
        'Sections matched:   %d' % stats['matched'], '',
        'Muted/absent:       %s' % (', '.join(muted_names) or 'None'),
        'Available coop:     %d' % stats['available'], '',
        'Camera:             %d' % stats['camera'],
        'Camera companions:  %d' % stats['companions'],
        'Lighting:           %d' % stats['lighting'],
        'Control [first]/[next]: %d' % stats['control'],
        'Post-process:       %d' % stats['postproc'],
        'Bonus FX:           %d' % stats['bonusfx'],
        'Music start anchor: %s' % (
            'explicit [music_start] marker' if stats['explicit_music_start']
            else '~3s fallback'),
        'Song end:           %s' % (
            'MIDI item length (fallback)' if stats['end_fallback']
            else 'explicit [end] marker'),
        '', 'Undo: Generate VENUE events from theme',
    ]
    if int(options.get('camera_pacing', 0)) == 7 and not stats['phrase_count']:
        lines.insert(-2, 'No PART VOCALS phrase markers found; recurring camera cuts were skipped.')
    return 'Generated %d VENUE events.' % len(rows), '\n'.join(lines)
