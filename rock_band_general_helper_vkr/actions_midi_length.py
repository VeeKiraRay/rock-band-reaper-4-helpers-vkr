"""MIDI note-length and MIDI-item length actions for REAPER 4.20.

Modern counterpart:
rock_band_general_helper_vkr/actions_midi_length.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk_transaction import apply_verified_item_chunks
from lib.midi_pool_safety import verify_unshared_pool_sources
from .actions_midi_common import (
    MidiActionError,
    load_first_midi_context,
    project_time_to_tick,
    track_display_name,
)
from .actions_midi_replace import get_pattern_pitch_range


SUSTAIN_MIN_DENOM = 8
FLOOR_DENOM = 32
SEARCH_WINDOW_32NDS = 16
SUSTAIN_GAP_BY_DIFF = {
    'Expert': 3, 'Hard': 4, 'Medium': 8, 'Easy': 16,
}


def note_length_ticks(ppq, denominator):
    return int(float(ppq) * 4.0 / int(denominator) + 0.5)


def sustain_gap_default(difficulty):
    return SUSTAIN_GAP_BY_DIFF[difficulty]


def _in_scope(note, lo, hi, scope_start, scope_end):
    return (lo <= note.pitch <= hi and
            (scope_start is None or note.start_tick >= scope_start) and
            (scope_end is None or note.start_tick < scope_end))


def adjust_midi_note_lengths(host, track, difficulty, note_type,
                             note_denominator=32, sustain_32nds=3):
    context = load_first_midi_context(host, track)
    parsed = context['parsed']
    track_name = track_display_name(host, track)
    diff_index = ('Expert', 'Hard', 'Medium', 'Easy').index(difficulty) + 1
    lo, hi = get_pattern_pitch_range(track_name, diff_index)
    selection_start, selection_end = host.time_selection()
    scope_start = (project_time_to_tick(host, context, selection_start)
                   if selection_start is not None else None)
    scope_end = (project_time_to_tick(host, context, selection_end)
                 if selection_end is not None else None)
    indexed_notes = [(index, note) for index, note in
                     enumerate(parsed.notes())
                     if _in_scope(note, lo, hi, scope_start, scope_end)]
    changes = {}

    if note_type == 'non_sustains':
        target = note_length_ticks(parsed.ppq, note_denominator)
        sustain_min = note_length_ticks(parsed.ppq, SUSTAIN_MIN_DENOM)
        starts = set()
        for index, note in indexed_notes:
            if note.length < sustain_min and note.end_tick != note.start_tick + target:
                changes[index] = note.start_tick + target
                starts.add(note.start_tick)
        count = len(starts)
        if changes:
            verify_unshared_pool_sources(host, [context])
        expected = parsed.with_note_ends(changes) if changes else context['chunk']
        apply_verified_item_chunks(host, [{
            'item': context['item'], 'original': context['chunk'],
            'expected': expected, 'fingerprint': context['fingerprint'],
        }], 'Adjust MIDI non-sustain lengths')
        status = 'Adjusted %d non-sustain note%s.' % (
            count, '' if count == 1 else 's')
        report = ('Set %d onset%s to 1/%d. Existing sustains were left '
                  'unchanged.' %
                  (count, '' if count == 1 else 's', note_denominator))
        if not changes:
            report += '\n\nNo project changes were needed; no Undo point was created.'
        return status, report

    if note_type != 'sustains':
        raise MidiActionError('Unknown MIDI note-length mode.')
    thirty_second = note_length_ticks(parsed.ppq, FLOOR_DENOM)
    sustain_min = note_length_ticks(parsed.ppq, SUSTAIN_MIN_DENOM)
    search_window = SEARCH_WINDOW_32NDS * thirty_second
    gap_target = int(sustain_32nds) * thirty_second
    sorted_notes = sorted(indexed_notes, key=lambda value: (
        value[1].start_tick, value[1].pitch, value[1].channel))
    counted = set()
    changed_starts = set()
    skipped = 0
    clamped_starts = set()
    for position, (index, note) in enumerate(sorted_notes):
        if note.length < sustain_min:
            continue
        next_tick = None
        for unused_index, following in sorted_notes[position + 1:]:
            if following.start_tick > note.start_tick:
                if (following.start_tick < note.end_tick or
                        following.start_tick - note.end_tick <= search_window):
                    next_tick = following.start_tick
                break
        first_at_start = note.start_tick not in counted
        counted.add(note.start_tick)
        if next_tick is None:
            if first_at_start:
                skipped += 1
            continue
        new_end = next_tick - gap_target
        floor_end = note.start_tick + thirty_second
        was_clamped = new_end < floor_end
        if was_clamped:
            new_end = floor_end
        if new_end != note.end_tick:
            changes[index] = new_end
            changed_starts.add(note.start_tick)
            if was_clamped:
                clamped_starts.add(note.start_tick)
    adjusted = len(changed_starts)
    clamped = len(clamped_starts)
    if changes:
        verify_unshared_pool_sources(host, [context])
    expected = parsed.with_note_ends(changes) if changes else context['chunk']
    apply_verified_item_chunks(host, [{
        'item': context['item'], 'original': context['chunk'],
        'expected': expected, 'fingerprint': context['fingerprint'],
    }], 'Adjust MIDI sustain gaps')
    status = 'Adjusted %d sustain%s.' % (
        adjusted, '' if adjusted == 1 else 's')
    lines = [
        '%d sustain%s adjusted; %d skipped (no next note in range).' %
        (adjusted, '' if adjusted == 1 else 's', skipped)]
    if clamped:
        lines.append('%d clamped to the 1/32-note floor.' % clamped)
    if not changes:
        lines.append('No project changes were needed; no Undo point was created.')
    return status, '\n'.join(lines)


def resize_all_midi_items(host, reference_track):
    reference = load_first_midi_context(host, reference_track)
    target_length = host.item_length(reference['item'])
    plans = []
    for track_index in range(host.track_count()):
        track = host.get_track(track_index)
        for item_index in range(host.item_count(track)):
            item = host.get_item(track, item_index)
            if abs(host.item_position(item)) > 0.001:
                continue
            chunk = host.read_item_chunk(item)
            if '<SOURCE MIDI' not in chunk:
                continue
            original = host.item_length(item)
            if abs(original - target_length) > 1e-9:
                plans.append((item, original))
    if not plans:
        return ('All MIDI items already match.',
                'No project changes were needed; no Undo point was created.')
    extending = [(item, original) for item, original in plans
                 if target_length > original + 1e-9]
    if extending:
        raise MidiActionError(
            'Resize would need to extend %d MIDI source%s. REAPER 4.20 '
            'cannot safely extend a MIDI source through the verified legacy '
            'API, so the entire batch was left unchanged.' %
            (len(extending), '' if len(extending) == 1 else 's'))
    for item, original in plans:
        if abs(host.item_length(item) - original) > 1e-9:
            raise MidiActionError(
                'A MIDI item changed after analysis; no changes were made.')
    written = []
    began = False
    try:
        host.begin_undo()
        began = True
        for item, original in plans:
            written.append((item, original))
            host.set_item_length(item, target_length)
            if abs(host.item_length(item) - target_length) > 1e-9:
                raise MidiActionError('MIDI item-length verification failed.')
        host.update_arrange()
        host.end_undo('Resize all MIDI items')
        began = False
    except Exception:
        for item, original in reversed(written):
            try:
                host.set_item_length(item, original)
            except Exception:
                pass
        try:
            host.update_arrange()
        except Exception:
            pass
        if began:
            host.end_undo('Resize all MIDI items FAILED; rollback attempted')
        raise
    return ('Resized %d MIDI item%s.' %
            (len(plans), '' if len(plans) == 1 else 's'),
            'Matched MIDI items at project position 0 to %.3f seconds.\n'
            'Undo: Resize all MIDI items' % target_length)
