"""Guarded generation of one detected EVENTS section on VENUE.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import random

from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources
from .actions_venue_themes import (
    INSTRUMENT_ALIGN, KEYFRAME_ALIGN_LABELS, MANUAL_LIGHTING,
    _active_camera_pool, _camera_companions,
    _camera_events, _choose, _instrument_note_qns, _keyframes,
    _muted_instruments, _next_measure_qn, _project_qn_to_tick,
    _resolved_pacing, _snap_half, _tick_to_project_qn,
)
from .venue import (
    INSTRUMENT_NAMES, VenueReadError, build_event_sections, read_named_track,
)
from .venue_themes import (
    build_lighting_pool, build_postproc_pool, get_section_preset,
)


class VenueSectionGenerationError(Exception):
    pass


def section_key(section):
    return '%s_%s' % (section['name'], section.get('num') or '')


def default_section_config():
    return {
        'lighting': '', 'postproc': '', 'keyframe_rate': 2,
        'light_blendin': 0, 'pp_blendin': 0, 'dircut': '',
        'bonusfx': False,
    }


def load_venue_sections(host):
    """Read selectable sections without changing the project."""
    try:
        unused_track, venue_contexts, unused_rows = read_named_track(
            host, 'VENUE')
        unused_track, event_contexts, event_rows = read_named_track(
            host, 'EVENTS')
    except VenueReadError as exc:
        raise VenueSectionGenerationError(str(exc))
    if len(venue_contexts) != 1:
        raise VenueSectionGenerationError(
            'Section gen requires exactly one MIDI item on VENUE; found %d.' %
            len(venue_contexts))
    song_end = venue_contexts[0]['end']
    return build_event_sections(event_rows, song_end), event_contexts


def _event_kind(message):
    if message.startswith('[coop_') or message.startswith('[directed_'):
        return 'camera'
    if message.startswith('[lighting ('):
        return 'lighting'
    if message.endswith('.pp]'):
        return 'postproc'
    return 'other'


def _incoming_presets(context, section_start_qn):
    lighting = None
    postproc = None
    camera = None
    for event in context['parsed'].text_events(1):
        qn = _tick_to_project_qn(context, event.absolute_tick)
        if qn >= section_start_qn:
            continue
        row = (qn, event.absolute_tick, event.meta_payload)
        kind = _event_kind(event.meta_payload)
        if kind == 'lighting' and (lighting is None or qn > lighting[0]):
            lighting = row
        elif kind == 'postproc' and (postproc is None or qn > postproc[0]):
            postproc = row
        elif kind == 'camera' and (camera is None or qn > camera[0]):
            camera = row
    return lighting, postproc, camera


def _template_config(theme, section, incoming_lighting, incoming_postproc,
                     rng):
    preset = get_section_preset(
        theme, section['name'], section.get('num'))
    if not preset:
        return default_section_config(), None
    lighting = _choose(
        build_lighting_pool(preset), incoming_lighting, rng) or ''
    postproc = _choose(
        build_postproc_pool(preset), incoming_postproc, rng) or ''
    return {
        'lighting': lighting,
        'postproc': postproc,
        'keyframe_rate': preset.get('keyframe_rate', 2),
        'light_blendin': preset.get('lightpreset_blendin', 0),
        'pp_blendin': preset.get('postproc_blendin', 0),
        'dircut': preset.get('dircut_at_start', ''),
        'bonusfx': bool(preset.get('bonusfx_at_start', False)),
    }, preset


def _message(value, category):
    if not value:
        return ''
    if value.startswith('['):
        return value
    if category == 'lighting':
        return '[lighting (%s)]' % value
    return '[%s]' % value


def _validated_config(config):
    result = dict(default_section_config(), **(config or {}))
    limits = (
        ('keyframe_rate', 1.0, 8.0, 'Keyframe rate'),
        ('light_blendin', 0.0, 8.0, 'Light blendin'),
        ('pp_blendin', 0.0, 8.0, 'PP blendin'),
    )
    for key, low, high, label in limits:
        try:
            value = float(result.get(key))
        except (TypeError, ValueError):
            raise VenueSectionGenerationError(
                '%s must be a number from %s to %s beats.' %
                (label, int(low), int(high)))
        if value < low or value > high:
            raise VenueSectionGenerationError(
                '%s must be from %s to %s beats; received %s.' %
                (label, int(low), int(high), result.get(key)))
        result[key] = value
    return result


def build_section_events(host, context, section, config, options,
                         theme=None, rng=None):
    """Return replacement rows, range, statistics, and read guards."""
    rng = rng or random.Random()
    start_qn = host.time_to_qn(section['t_start'])
    end_qn = host.time_to_qn(section['t_end'])
    item_start_qn = context['start_qn']
    item_end_qn = host.time_to_qn(context['end'])
    start_qn = max(item_start_qn, start_qn)
    end_qn = min(item_end_qn, end_qn)
    if end_qn <= start_qn:
        raise VenueSectionGenerationError(
            'The selected section does not overlap the VENUE MIDI item.')

    incoming_lt, incoming_pp, incoming_camera = _incoming_presets(
        context, start_qn)
    incoming_lt_text = incoming_lt[2] if incoming_lt else None
    incoming_pp_text = incoming_pp[2] if incoming_pp else None
    if theme is not None:
        config, preset = _template_config(
            theme, section, incoming_lt_text, incoming_pp_text, rng)
    else:
        config = dict(default_section_config(), **(config or {}))
        preset = config
    config = _validated_config(config)

    lighting = _message(config.get('lighting', ''), 'lighting')
    postproc = _message(config.get('postproc', ''), 'postproc')
    max_blend = max(float(config.get('light_blendin', 0)),
                    float(config.get('pp_blendin', 0)))
    clear_start_qn = max(item_start_qn, start_qn - max_blend)
    for incoming in (incoming_lt, incoming_pp):
        if incoming and clear_start_qn <= incoming[0]:
            clear_start_qn = max(
                clear_start_qn,
                _tick_to_project_qn(context, incoming[1] + 1))

    muted = _muted_instruments(host)
    camera_pool = _active_camera_pool(muted)
    if not camera_pool:
        raise VenueSectionGenerationError(
            'All instrument tracks are muted or absent; no camera events are available.')
    beat_seconds = host.qn_to_time(start_qn + 1.0) - host.qn_to_time(start_qn)
    bpm = 60.0 / beat_seconds if beat_seconds > 0 else 120.0
    pacing_theme = theme or {'camera_pacing': 'medium'}
    interval = _resolved_pacing(pacing_theme, options, bpm)
    guards = []
    phrase_qns = None
    if int(options.get('camera_pacing', 0)) == 7:
        phrase_qns, phrase_contexts = _instrument_note_qns(
            host, 'PART VOCALS', 105, 105)
        guards.extend(phrase_contexts)
        camera_anchor = start_qn - 0.001
    else:
        camera_anchor = (incoming_camera[0] + interval / 4.0
                         if incoming_camera else start_qn + interval / 4.0)
        while camera_anchor < start_qn:
            camera_anchor += interval / 4.0

    cameras = _camera_events(
        start_qn, end_qn, camera_anchor, camera_pool, interval,
        bool(options.get('camera_jitter', True)), phrase_qns, rng)
    cameras, companions = _camera_companions(
        cameras, camera_pool, muted, rng)
    generated = list(cameras)
    directed = _message(config.get('dircut', ''), 'directed')
    if directed:
        generated.append((round(start_qn), directed, False))

    align = int(options.get('keyframe_align', 0))
    subdivision = int(options.get('keyframe_subdivision', 0))
    note_qns = []
    if align in INSTRUMENT_ALIGN:
        note_qns, note_contexts = _instrument_note_qns(
            host, *INSTRUMENT_ALIGN[align])
        guards.extend(note_contexts)

    lighting_count = 0
    postproc_count = 0
    control_count = 0
    kept_lighting = bool(lighting and lighting == incoming_lt_text)
    kept_postproc = bool(postproc and postproc == incoming_pp_text)
    if lighting and not kept_lighting:
        blend_qn = start_qn - float(config.get('light_blendin', 0))
        if (config.get('light_blendin') and incoming_lt and
                blend_qn > incoming_lt[0]):
            generated.append((blend_qn, incoming_lt_text, False))
            lighting_count += 1
        generated.append((start_qn, lighting, False))
        lighting_count += 1
    if lighting in MANUAL_LIGHTING:
        keyframes = _keyframes(
            _snap_half(start_qn), end_qn,
            config.get('keyframe_rate', 2), align, subdivision, note_qns,
            lambda value: _next_measure_qn(host, value))
        if kept_lighting:
            keyframes = [row for row in keyframes if row[1] != '[first]']
        generated.extend(keyframes)
        control_count += len(keyframes)
    if postproc and not kept_postproc:
        blend_qn = start_qn - float(config.get('pp_blendin', 0))
        if (config.get('pp_blendin') and incoming_pp and
                blend_qn > incoming_pp[0]):
            generated.append((blend_qn, incoming_pp_text, False))
            postproc_count += 1
        generated.append((start_qn, postproc, False))
        postproc_count += 1
    if config.get('bonusfx'):
        generated.append((start_qn, '[bonusfx]', False))

    clear_start_tick = _project_qn_to_tick(context, clear_start_qn)
    start_tick = _project_qn_to_tick(context, start_qn)
    end_tick = _project_qn_to_tick(context, end_qn)
    rows = []
    for event in context['parsed'].text_events(1):
        tick = event.absolute_tick
        if not clear_start_tick <= tick < end_tick:
            continue
        kind = _event_kind(event.meta_payload)
        keep = ((tick < start_tick and kind == 'camera') or
                (tick > start_tick and kind in ('lighting', 'postproc')))
        if keep:
            rows.append({'tick': tick, 'payload': event.meta_payload})
    for qn, message, no_snap in generated:
        placed_qn = qn if no_snap else _snap_half(qn)
        if clear_start_qn <= placed_qn < end_qn:
            rows.append({'tick': _project_qn_to_tick(context, placed_qn),
                         'payload': message})

    stats = {
        'camera': len(cameras), 'directed': 1 if directed else 0,
        'companions': companions, 'lighting': lighting_count,
        'postproc': postproc_count, 'control': control_count,
        'bonusfx': 1 if config.get('bonusfx') else 0,
        'kept_lighting': lighting if kept_lighting else '',
        'kept_postproc': postproc if kept_postproc else '',
        'phrase_count': len(phrase_qns or ()), 'muted': muted,
        'clear_start_tick': clear_start_tick, 'end_tick': end_tick,
        'preset_found': preset is not None, 'inserted': len(generated),
    }
    return rows, stats, guards


def generate_venue_section(host, section, config, options, theme=None,
                           rng=None):
    try:
        unused_track, contexts, unused_rows = read_named_track(host, 'VENUE')
    except VenueReadError as exc:
        raise VenueSectionGenerationError(str(exc))
    if len(contexts) != 1:
        raise VenueSectionGenerationError(
            'Section gen requires exactly one MIDI item on VENUE; found %d.' %
            len(contexts))
    context = contexts[0]
    current_sections, event_contexts = load_venue_sections(host)
    matching = [value for value in current_sections
                if (section_key(value) == section_key(section) and
                    abs(value['t_start'] - section['t_start']) < 1e-7 and
                    abs(value['t_end'] - section['t_end']) < 1e-7)]
    if len(matching) != 1:
        raise VenueSectionGenerationError(
            'The selected EVENTS section changed; press Refresh and try again.')
    section = matching[0]
    rows, stats, guards = build_section_events(
        host, context, section, config, options, theme, rng)
    guards.extend(event_contexts)
    verify_unshared_pool_sources(host, [context])
    expected = context['parsed'].with_replaced_meta_events(
        stats['clear_start_tick'], stats['end_tick'], rows, 0x01)
    guard_plans = [{
        'item': value['item'], 'original': value['chunk'],
        'fingerprint': value['fingerprint'], 'expected': value['chunk'],
    } for value in guards]
    label = section['name'][:1].upper() + section['name'][1:]
    if section.get('num') is not None:
        label += ' %s' % section['num']
    undo = 'Generate VENUE section: %s' % label
    apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'fingerprint': context['fingerprint'], 'expected': expected,
    }], undo, guard_plans)

    muted_names = sorted(INSTRUMENT_NAMES[key] for key in stats['muted'])
    lines = [
        'Generated %d total events for section: %s' %
        (stats['inserted'], label), '',
        'Camera:             %d' % stats['camera'],
        'Camera companions:  %d' % stats['companions'],
        'Directed camera:    %d' % stats['directed'],
        'Lighting:           %d' % stats['lighting'],
        'Control [first]/[next]: %d' % stats['control'],
        'Post-process:       %d' % stats['postproc'],
        'Bonus FX:           %d' % stats['bonusfx'],
        'Muted/absent:       %s' % (', '.join(muted_names) or 'None'),
    ]
    if stats['kept_lighting']:
        lines.append('Lighting kept:      %s was already running' %
                     stats['kept_lighting'])
    if stats['kept_postproc']:
        lines.append('Post-process kept:  %s was already running' %
                     stats['kept_postproc'])
    if (int(options.get('camera_pacing', 0)) == 7 and
            not stats['phrase_count']):
        lines.append('No PART VOCALS phrase markers were found in this section.')
    lines.extend(('', 'Undo: %s' % undo))
    return 'Generated %d VENUE events for %s.' % (
        stats['inserted'], label), '\n'.join(lines)
