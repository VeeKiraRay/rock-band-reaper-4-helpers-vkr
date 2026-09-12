"""Note mutation implementations for :mod:`lib.midi_chunk`.

Python 2.7 compatible.
"""

from lib.midi_chunk import MidiChunkError, MidiEvent


def with_note_end(parsed, note_index, new_end_tick):
    return with_note_ends(parsed, {int(note_index): int(new_end_tick)})


def with_note_ends(parsed, changes):
    """Return a chunk with several paired note-off ticks changed."""
    notes = parsed.notes()
    events = [event.clone() for event in parsed.events]
    by_ordinal = dict((event.ordinal, event) for event in events)
    for note_index, new_end_tick in changes.items():
        note_index = int(note_index)
        new_end_tick = int(new_end_tick)
        if note_index < 0 or note_index >= len(notes):
            raise MidiChunkError('Note index is out of range.')
        note = notes[note_index]
        if note.overlapping_same_pitch:
            raise MidiChunkError(
                'Selected note overlaps another note of the same pitch/channel.')
        if new_end_tick <= note.start_tick:
            raise MidiChunkError('New note end must be after its start.')
        target = by_ordinal.get(note.off_event.ordinal)
        if target is None:
            raise MidiChunkError('Could not locate the note-off event.')
        target.absolute_tick = new_end_tick
    return parsed._render_mutated_events(events)


def _validate_note_stream(parsed):
    notes = parsed.notes()
    paired_ordinals = set()
    for note in notes:
        paired_ordinals.add(note.on_event.ordinal)
        paired_ordinals.add(note.off_event.ordinal)
    unpaired = [
        event for event in parsed.events
        if (event.is_note_on() or event.is_note_off()) and
        event.ordinal not in paired_ordinals]
    if unpaired:
        raise MidiChunkError(
            'Mutation blocked: MIDI stream has %d unpaired note event(s).' %
            len(unpaired))
    return notes


def _new_note_events(parsed, replacement, ordinal):
    start_tick = int(replacement['start_tick'])
    end_tick = int(replacement['end_tick'])
    pitch = int(replacement['pitch'])
    velocity = int(replacement.get('velocity', 100))
    channel = int(replacement.get('channel', 0))
    if start_tick < 0 or end_tick <= start_tick:
        raise MidiChunkError('Replacement note has invalid start/end ticks.')
    if not 0 <= pitch <= 127 or not 1 <= velocity <= 127:
        raise MidiChunkError('Replacement note pitch or velocity is invalid.')
    if not 0 <= channel <= 15:
        raise MidiChunkError('Replacement note channel is invalid.')

    on_event = MidiEvent(
        'short', ['E 0 %02x %02x %02x%s' %
                  (0x90 | channel, pitch, velocity, parsed.newline)],
        0, start_tick, ordinal)
    on_event.status = 0x90 | channel
    on_event.channel = channel
    on_event.data1 = pitch
    on_event.data2 = velocity
    on_event.inserted = True
    off_event = MidiEvent(
        'short', ['E 0 %02x %02x 00%s' %
                  (0x80 | channel, pitch, parsed.newline)],
        0, end_tick, ordinal + 1)
    off_event.status = 0x80 | channel
    off_event.channel = channel
    off_event.data1 = pitch
    off_event.data2 = 0
    off_event.inserted = True
    return on_event, off_event


def with_replaced_note_windows(parsed, pitch_lo, pitch_hi, windows):
    pitch_lo = int(pitch_lo)
    pitch_hi = int(pitch_hi)
    if pitch_lo < 0 or pitch_hi > 127 or pitch_lo > pitch_hi:
        raise MidiChunkError('Replacement pitch range is invalid.')
    ordered_windows = sorted(windows, key=lambda value: (
        int(value['start_tick']), int(value['end_tick'])))
    previous_end = None
    for window in ordered_windows:
        start_tick = int(window['start_tick'])
        end_tick = int(window['end_tick'])
        if start_tick < 0 or end_tick <= start_tick:
            raise MidiChunkError('Replacement window is invalid.')
        if previous_end is not None and start_tick < previous_end:
            raise MidiChunkError('Replacement windows overlap.')
        previous_end = end_tick

    notes = _validate_note_stream(parsed)

    def in_replaced_window(note):
        if not pitch_lo <= note.pitch <= pitch_hi:
            return False
        return any(int(window['start_tick']) <= note.start_tick <
                   int(window['end_tick']) for window in ordered_windows)

    remove_ordinals = set()
    for note in notes:
        if in_replaced_window(note):
            remove_ordinals.add(note.on_event.ordinal)
            remove_ordinals.add(note.off_event.ordinal)
    events = [event.clone() for event in parsed.events
              if event.ordinal not in remove_ordinals]
    next_ordinal = max([event.ordinal for event in parsed.events] or [-1]) + 1
    for window in ordered_windows:
        for replacement in window.get('notes', ()):
            start_tick = int(replacement['start_tick'])
            end_tick = int(replacement['end_tick'])
            pitch = int(replacement['pitch'])
            if start_tick < 0 or end_tick <= start_tick:
                raise MidiChunkError(
                    'Replacement note has invalid start/end ticks.')
            if not (int(window['start_tick']) <= start_tick <
                    int(window['end_tick'])):
                raise MidiChunkError('Replacement note starts outside its window.')
            if not pitch_lo <= pitch <= pitch_hi:
                raise MidiChunkError(
                    'Replacement note is outside the target pitch range.')
            on_event, off_event = _new_note_events(
                parsed, replacement, next_ordinal)
            events.extend((on_event, off_event))
            next_ordinal += 2
    return parsed._render_mutated_events(events)


def with_replaced_notes(parsed, pitch_lo, pitch_hi, replacements):
    pitch_lo = int(pitch_lo)
    pitch_hi = int(pitch_hi)
    if pitch_lo < 0 or pitch_hi > 127 or pitch_lo > pitch_hi:
        raise MidiChunkError('Replacement pitch range is invalid.')
    notes = _validate_note_stream(parsed)
    remove_ordinals = set()
    for note in notes:
        if pitch_lo <= note.pitch <= pitch_hi:
            remove_ordinals.add(note.on_event.ordinal)
            remove_ordinals.add(note.off_event.ordinal)
    events = [event.clone() for event in parsed.events
              if event.ordinal not in remove_ordinals]
    next_ordinal = max([event.ordinal for event in parsed.events] or [-1]) + 1
    ordered = sorted(replacements, key=lambda value: (
        int(value['start_tick']), int(value['pitch']),
        int(value['end_tick'])))
    for replacement in ordered:
        on_event, off_event = _new_note_events(
            parsed, replacement, next_ordinal)
        events.extend((on_event, off_event))
        next_ordinal += 2
    return parsed._render_mutated_events(events)
