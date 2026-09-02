"""Read-only chart inventory for Metadata > Difficulty.

This is the compatibility foundation for the modern helper's calibrated
difficulty suggester.  It deliberately reports measured facts only: the
instrument-specific scorers and frozen rank models have not yet been ported,
so presenting an approximate rank here would be misleading.

Modern counterparts:
rock_band_general_helper_vkr/difficulty_read.lua
rock_band_general_helper_vkr/difficulty_suggester.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk import parse_midi_chunk
from lib.reaper420 import Reaper420Host
from .difficulty_read import suggest_bass


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


def _analyse_track(host, spec, matches):
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

    # Bass is the first calibrated end-to-end compatibility slice. Its frozen
    # model uses only three factors, making it the safest instrument with which
    # to verify legacy tick/time conversion before porting the larger scorers.
    if (spec['key'] == 'bass' and result['parsed_items'] and
            result['playable_notes'] and not result['failed_items'] and
            not result['muted']):
        try:
            result['suggestion'] = suggest_bass(host, track)
        except Exception as exc:
            result['errors'].append('calibrated Bass scoring: %s' % exc)

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
    return [_analyse_track(host, spec, matches) for spec in CHART_SPECS]


def card_summary(result):
    if not result['present']:
        return 'Not found'
    if result['status'] in ('No MIDI items', 'No playable notes'):
        return result['status']
    if result['failed_items'] and not result['parsed_items']:
        return 'MIDI read failed'
    if result.get('suggestion'):
        suggestion = result['suggestion']
        return 'Rank %d - %s\n%d notes / %d onsets' % (
            int(suggestion['rank'] + 0.5), suggestion['tier_name'],
            result['playable_notes'], result['playable_onsets'])
    noun = 'note' if result['playable_notes'] == 1 else 'notes'
    return '%d %s / %d onsets' % (
        result['playable_notes'], noun, result['playable_onsets'])


def format_inventory(results):
    lines = [
        'METADATA DIFFICULTY - CHART INVENTORY',
        '',
        'Read-only compatibility stage. Bass now uses the calibrated model; '
        'the other five instruments still show measured chart facts only.',
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
                lines.append('  Calibrated suggestion: rank %.2f - %s' % (
                    suggestion['rank'], suggestion['tier_name']))
                lines.append(
                    '  Bass factors: changes=%d, peak=%.6f, entropy=%.6f' %
                    (factors['total_changes'], factors['density_peak'],
                     factors['entropy_h2']))
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
