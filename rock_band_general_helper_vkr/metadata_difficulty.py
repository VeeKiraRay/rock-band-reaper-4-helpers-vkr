"""Read-only chart inventory for Metadata > Difficulty.

This is the compatibility port of the modern helper's calibrated difficulty
suggester. It reports chart facts and model-based ranks for all six supported
instrument charts without modifying the project.

Modern counterparts:
rock_band_general_helper_vkr/difficulty_read.lua
rock_band_general_helper_vkr/difficulty_suggester.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk import parse_midi_chunk
from lib.reaper420 import Reaper420Host
from .difficulty_read import (
    read_coda_time,
    suggest_bass,
    suggest_guitar,
    suggest_drums,
    suggest_keys,
    suggest_real_keys,
    suggest_vocals,
    count_vocal_parts,
)
from .difficulty_explain import annotate_suggestion


CHART_SPECS = (
    {'key': 'guitar', 'label': 'Guitar', 'track': 'PART GUITAR',
     'lo': 96, 'hi': 100},
    {'key': 'bass', 'label': 'Bass', 'track': 'PART BASS',
     'lo': 96, 'hi': 100},
    {'key': 'drum', 'label': 'Drums', 'track': 'PART DRUMS',
     'lo': 96, 'hi': 100},
    {'key': 'keys', 'label': 'Keys', 'track': 'PART KEYS',
     'lo': 96, 'hi': 100},
    {'key': 'real_keys', 'label': 'Pro Keys',
     'track': 'PART REAL_KEYS_X', 'lo': 48, 'hi': 72},
    {'key': 'vocals', 'label': 'Vocals', 'track': 'PART VOCALS',
     'lo': 36, 'hi': 84, 'vocal': True},
)


def _empty_result(spec):
    return {
        'key': spec['key'],
        'label': spec['label'],
        'track_name': spec['track'],
        'track_index': None,
        'duplicate_tracks': 0,
        'present': False,
        'muted': False,
        'item_count': 0,
        'parsed_items': 0,
        'failed_items': 0,
        'playable_notes': 0,
        'playable_onsets': 0,
        'chord_onsets': 0,
        'max_chord_size': 0,
        'longest_note_ticks': 0,
        'lyric_events': 0,
        'phrase_markers': 0,
        'ppq_values': [],
        'unsupported_lines': 0,
        'errors': [],
        'status': 'Not found',
        'suggestion': None,
    }


def _matching_tracks(host):
    matches = {}
    for index in range(host.track_count()):
        track = host.get_track(index)
        name = host.track_name(track, index)
        key = name.strip().upper()
        matches.setdefault(key, []).append((index, track))
    return matches


def _analyse_track(host, spec, matches, coda_time=None):
    result = _empty_result(spec)
    found = matches.get(spec['track'].upper(), [])
    if not found:
        return result

    track_index, track = found[0]
    result['present'] = True
    result['track_index'] = track_index
    result['duplicate_tracks'] = max(0, len(found) - 1)
    try:
        result['muted'] = bool(host.track_muted(track))
    except Exception as exc:
        result['errors'].append('mute state: %s' % exc)

    result['item_count'] = host.item_count(track)
    onset_sizes = []
    ppq_values = set()

    for item_index in range(result['item_count']):
        try:
            item = host.get_item(track, item_index)
            parsed = parse_midi_chunk(host.read_item_chunk(item))
            result['parsed_items'] += 1
            ppq_values.add(parsed.ppq)
            result['unsupported_lines'] += len(parsed.unsupported_records)

            playable = [
                note for note in parsed.notes()
                if spec['lo'] <= note.pitch <= spec['hi']]
            result['playable_notes'] += len(playable)
            if playable:
                longest = max(note.length for note in playable)
                result['longest_note_ticks'] = max(
                    result['longest_note_ticks'], longest)
                by_tick = {}
                for note in playable:
                    by_tick.setdefault(note.start_tick, []).append(note)
                onset_sizes.extend(len(notes) for notes in by_tick.values())

            if spec.get('vocal'):
                result['lyric_events'] += len(parsed.text_events(0x05))
                result['phrase_markers'] += sum(
                    1 for note in parsed.notes()
                    if note.pitch in (105, 106))
        except Exception as exc:
            result['failed_items'] += 1
            result['errors'].append('item %d: %s' % (item_index + 1, exc))

    result['ppq_values'] = sorted(ppq_values)
    result['playable_onsets'] = len(onset_sizes)
    result['chord_onsets'] = sum(1 for size in onset_sizes if size > 1)
    result['max_chord_size'] = max(onset_sizes or [0])

    suggesters = {
        'guitar': suggest_guitar,
        'bass': suggest_bass,
        'drum': suggest_drums,
        'keys': suggest_keys,
        'real_keys': suggest_real_keys,
        'vocals': suggest_vocals,
    }
    if (spec['key'] in suggesters and result['parsed_items'] and
            result['playable_notes'] and not result['failed_items'] and
            not result['muted']):
        try:
            if spec['key'] == 'real_keys':
                keys_tracks = matches.get('PART KEYS', [])
                span_track = keys_tracks[0][1] if keys_tracks else track
                result['suggestion'] = suggest_real_keys(
                    host, track, span_track, coda_time)
            elif spec['key'] == 'vocals':
                harmony_tracks = []
                for name in ('HARM2', 'HARM3'):
                    found_harmony = matches.get(name, [])
                    if found_harmony:
                        harmony_tracks.append(found_harmony[0][1])
                try:
                    vocal_parts = count_vocal_parts(host, harmony_tracks)
                except Exception:
                    # Match the modern pcall guard: difficulty scoring still
                    # works as a lead-only chart if a harmony track is bad.
                    vocal_parts = 1
                result['suggestion'] = suggest_vocals(
                    host, track, vocal_parts)
            else:
                result['suggestion'] = suggesters[spec['key']](
                    host, track, coda_time)
            annotate_suggestion(result['suggestion'], spec['label'])
        except Exception as exc:
            result['errors'].append(
                'calibrated %s scoring: %s' % (spec['label'], exc))

    if result['failed_items']:
        result['status'] = 'Read warning'
    elif result['muted']:
        result['status'] = 'Muted'
    elif not result['item_count']:
        result['status'] = 'No MIDI items'
    elif not result['playable_notes']:
        result['status'] = 'No playable notes'
    else:
        result['status'] = 'Chart read'
    return result


def analyse_project(host=None):
    """Return one measured inventory record for every modern chart spec."""
    if host is None:
        host = Reaper420Host()
    matches = _matching_tracks(host)
    coda_time = None
    events_tracks = matches.get('EVENTS', [])
    if events_tracks:
        try:
            coda_time = read_coda_time(host, events_tracks[0][1])
        except Exception:
            # BRE context is advisory and must not cost all six suggestions.
            coda_time = None
    return [_analyse_track(host, spec, matches, coda_time)
            for spec in CHART_SPECS]


def current_project_info(host=None):
    if host is None:
        host = Reaper420Host()
    return host.project_info()


def project_identity_changed(previous, current):
    before = (previous or {}).get('identity')
    after = (current or {}).get('identity')
    return before is not None and after is not None and before != after


def card_summary(result):
    if not result['present']:
        return 'Not found'
    if result['status'] in ('No MIDI items', 'No playable notes'):
        return result['status']
    if result['failed_items'] and not result['parsed_items']:
        return 'MIDI read failed'
    if result.get('suggestion'):
        if result['key'] == 'vocals':
            return '%d notes' % result['playable_notes']
        return '%d gems / %d onsets' % (
            result['playable_notes'], result['playable_onsets'])
    noun = 'note' if result['playable_notes'] == 1 else 'notes'
    if result['key'] == 'vocals':
        return '%d %s' % (result['playable_notes'], noun)
    return '%d %s / %d onsets' % (
        result['playable_notes'], noun, result['playable_onsets'])


def format_inventory(results):
    lines = [
        'METADATA DIFFICULTY - CHART INVENTORY',
        '',
        'Read-only compatibility stage. All six instrument charts use '
        'calibrated models.',
        '',
    ]
    for result in results:
        lines.append('%s - %s' % (result['label'], result['status']))
        lines.append('  Track: %s%s' % (
            result['track_name'],
            (' (track %d)' % (result['track_index'] + 1)
             if result['track_index'] is not None else '')))
        if result['present']:
            lines.append('  MIDI items: %d (%d parsed, %d failed)' % (
                result['item_count'], result['parsed_items'],
                result['failed_items']))
            lines.append('  Playable notes/onsets: %d / %d' % (
                result['playable_notes'], result['playable_onsets']))
            lines.append('  Chord onsets/max size: %d / %d' % (
                result['chord_onsets'], result['max_chord_size']))
            lines.append('  Longest note: %d ticks' %
                         result['longest_note_ticks'])
            ppq = ', '.join(str(value) for value in result['ppq_values'])
            lines.append('  Source PPQ: %s' % (ppq or 'not read'))
            if result['key'] == 'vocals':
                lines.append('  Lyrics/phrase markers: %d / %d' % (
                    result['lyric_events'], result['phrase_markers']))
            if result.get('suggestion'):
                suggestion = result['suggestion']
                factors = suggestion['factors']
                lines.append('  Calibrated suggestion: rank %d - %s' % (
                    suggestion['rank_shown'], suggestion['tier_name']))
                lines.append(
                    '  Exact model rank for tier position: %.2f' %
                    suggestion['rank'])
                if result['key'] == 'bass':
                    lines.append(
                        '  Bass factors: changes=%d, peak=%.6f, '
                        'entropy=%.6f' %
                        (factors['total_changes'], factors['density_peak'],
                         factors['entropy_h2']))
                elif result['key'] == 'guitar':
                    lines.append(
                        '  Guitar speed: playing=%.3fs, attacks=%.6f/s, '
                        'peak=%.6f/s, changes=%d' %
                        (factors['playing_s'],
                         factors['attack_density_avg'],
                         factors['attack_density_peak'],
                         factors['total_changes']))
                    lines.append(
                        '  Guitar shape: chord=%.6f, movement=%.6f, '
                        'anchor=%.6f, sustain=%.6f' %
                        (factors['chord_size_mean'],
                         factors['move_mean'], factors['anchor_frac'],
                         factors['sustain_frac']))
                    lines.append(
                        '  Guitar markers: solo=%.6f, hopo=%.6f/s, '
                        'strum=%.6f/s, tremolo=%.6f, trill=%.6f' %
                        (factors['solo_frac_marked'],
                         factors['force_hopo_rate'],
                         factors['force_strum_rate'],
                         factors['tremolo_frac'], factors['trill_frac']))
                elif result['key'] in ('keys', 'real_keys'):
                    lines.append(
                        '  Keyboard speed: playing=%.3fs, peak=%.6f/s, '
                        'changes=%d, tight=%.6f/%.6f QN' %
                        (factors['playing_s'],
                         factors['attack_density_peak'],
                         factors['total_changes'], factors['tight_p10'],
                         factors['tight_med']))
                    lines.append(
                        '  Keyboard shape: motion entropy=%.6f, '
                        'complexity peak=%.6f, chord size=%.6f' %
                        (factors['entropy_h2_rel'],
                         factors['complex_peak'],
                         factors['chord_size_mean']))
                elif result['key'] == 'drum':
                    lines.append(
                        '  Drum speed: playing=%.3fs, gems=%.6f/s, '
                        'peak(no roll)=%.6f/s, changes=%d' %
                        (factors['playing_s'], factors['density_avg'],
                         factors['density_peak_noroll'],
                         factors['total_changes']))
                    lines.append(
                        '  Drum limbs: kick=%.6f/s, kick peak=%.6f/s, '
                        'hand peak(no roll)=%.6f/s, sticks=%.6f' %
                        (factors['kick_density'],
                         factors['kick_density_peak'],
                         factors['hand_density_peak_noroll'],
                         factors['stick_size_mean']))
                    lines.append(
                        '  Drum markers: tom=%.6f, roll=%.6f, '
                        'offbeat=%.6f, Pro stations=%.6f' %
                        (factors['tom_frac'], factors['roll_frac'],
                         factors['offbeat_frac'],
                         factors['pro_stations_peak']))
                elif result['key'] == 'vocals':
                    lines.append(
                        '  Vocal speed: playing=%.3fs, syllables=%.6f/s, '
                        'peak=%.6f/s, tight=%.6f/%.6f QN' %
                        (factors['playing_s'],
                         factors['syl_density_avg'],
                         factors['syl_density_peak'],
                         factors['tight_p10'], factors['tight_med']))
                    lines.append(
                        '  Vocal pitch: interval=%.6f, changes=%.6f/s, '
                        'range=%.6f, p90=%.6f, octave jumps=%.6f/s' %
                        (factors['pc_interval_mean'],
                         factors['pc_change_rate'],
                         factors['notated_range'], factors['pitch_p90'],
                         factors['octave_jump_rate']))
                    lines.append(
                        '  Vocal context: parts=%d, high-time=%.6f' %
                        (suggestion['vocal_parts'],
                         factors['high_time_70']))
                lines.append('  Playing spans: %s (%d animation states)' % (
                    suggestion['span_source'],
                    suggestion['animation_states']))
                if suggestion['clamped']:
                    lines.append(
                        '  Note: raw rank %.2f was clamped to model range.' %
                        suggestion['raw_rank'])
            if result['muted']:
                lines.append('  Note: track is muted.')
            if result['duplicate_tracks']:
                lines.append(
                    '  Warning: %d additional exact-name track(s) ignored.' %
                    result['duplicate_tracks'])
            if result['unsupported_lines']:
                lines.append(
                    '  Preserved unsupported stream lines: %d' %
                    result['unsupported_lines'])
            for error in result['errors']:
                lines.append('  Warning: %s' % error)
        lines.append('')
    return '\n'.join(lines).rstrip()
