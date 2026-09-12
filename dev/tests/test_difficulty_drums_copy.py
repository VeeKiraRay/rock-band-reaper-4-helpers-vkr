"""Desktop tests for guarded Difficulty > Drums copy actions."""

from __future__ import print_function

import base64
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.midi_chunk import MidiChunkError, parse_midi_chunk
from lib.midi_chunk_transaction import MidiChunkTransactionError
from lib.reaper420 import Reaper420Host
from lib.runtime_flags import (
    set_development_mode, set_semantic_midi_write_verification)
from rock_band_general_helper_vkr.actions_difficulty_drums import copy_drums


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def _meta_event(delta, message):
    payload = b'\xff\x01' + message.encode('ascii')
    encoded = base64.b64encode(payload)
    if not isinstance(encoded, str):
        encoded = encoded.decode('ascii')
    return '<X %d 0\n  %s\n>\n' % (delta, encoded)


def midi_chunk(notes, pooled=False, text=None, current_metadata=False):
    events = []
    for pitch, start, end in notes:
        events.append((start, 1, '90', pitch, 96))
        events.append((end, 0, '80', pitch, 0))
    events.sort(key=lambda event: (event[0], event[1], event[3]))
    previous = 0
    lines = []
    if text is not None:
        lines.append(_meta_event(0, text))
    for tick, unused_order, status, pitch, velocity in events:
        lines.append('E %d %s %02x %02x\n' %
                     (tick - previous, status, pitch, velocity))
        previous = tick
    pool_line = ('POOLEDEVTS {11111111-1111-1111-1111-111111111111}\n'
                 if pooled else '')
    leading = ('CCINTERP 32\n' if current_metadata else '')
    trailing = (('CCINTERP 32\nCHASE_CC_TAKEOFFS 1\n'
                 'GUID {22222222-2222-2222-2222-222222222222}\n')
                if current_metadata else '')
    return (('<ITEM\nPOSITION 0\nLENGTH 30\n<SOURCE MIDI\n'
             'HASDATA 1 480 QN\n%s%s%s%sIGNTEMPO 0 120 4 4\n>\n>\n') %
            (leading, pool_line, ''.join(lines), trailing))


class FakeHost(object):
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.write_calls = 0
        self.undo_begin = 0
        self.undo_end = []
        self.arrange_updates = 0
        self.corrupt_next_write = False

    def item_count(self, unused_track):
        return len(self.chunks)

    def get_item(self, unused_track, index):
        return index

    def project_item_count(self):
        return len(self.chunks)

    def get_project_item(self, index):
        return index

    def active_take(self, item):
        return 'take-%d' % item

    def take_play_rate(self, unused_take):
        return 1.0

    def item_position(self, unused_item):
        return 0.0

    def item_length(self, unused_item):
        return 30.0

    def take_start_offset(self, unused_take):
        return 0.0

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, quarter_notes):
        return float(quarter_notes) / 2.0

    def read_item_chunk(self, item):
        return self.chunks[item]

    def write_item_chunk(self, item, chunk):
        self.write_calls += 1
        if self.corrupt_next_write:
            self.corrupt_next_write = False
            self.chunks[item] = chunk + 'CORRUPTED'
        else:
            self.chunks[item] = chunk

    def begin_undo(self):
        self.undo_begin += 1

    def end_undo(self, description):
        self.undo_end.append(description)

    def update_arrange(self):
        self.arrange_updates += 1


def pitches(chunk):
    return [note.pitch for note in parse_midi_chunk(chunk).notes()]


def test_copy_to_hard_replaces_target_and_preserves_other_events():
    original = midi_chunk([
        (96, 0, 120), (97, 480, 600),
        (84, 240, 360), (120, 0, 960),
    ], text='[mix 3 drums0]')
    host = FakeHost([original])
    confirmations = []
    status, report = copy_drums(
        host, 'track', 'H',
        lambda message: confirmations.append(message) or True)
    parsed = parse_midi_chunk(host.chunks[0])
    expect('copied 2 notes from Expert' in status,
           'successful Drums copy status differs')
    expect('one REAPER Undo point' not in report and
           'Undo: Copy Drums X to H' in report,
           'copy result did not identify its Undo action')
    expect(confirmations and 'already has 1 note' in confirmations[0],
           'populated target did not request confirmation')
    expect(pitches(host.chunks[0]) == [84, 96, 120, 85, 97],
           'target replacement or unrelated-note preservation differs')
    hard = [note for note in parsed.notes() if 84 <= note.pitch <= 88]
    expect([note.velocity for note in hard] == [100, 100],
           'copied Drums notes did not use velocity 100')
    expect(parsed.text_events(1)[0].meta_payload == '[mix 3 drums0]',
           'MIDI text event was not preserved')
    expect(host.undo_begin == 1 and
           host.undo_end == ['Copy Drums X to H'],
           'successful copy did not create exactly one Undo point')


def test_copy_without_existing_target_needs_no_confirmation():
    host = FakeHost([midi_chunk([(96, 0, 120)])])
    called = []
    copy_drums(host, 'track', 'H',
               lambda unused_message: called.append(True) or False)
    expect(not called and 84 in pitches(host.chunks[0]),
           'empty target unexpectedly required overwrite confirmation')


def test_medium_and_easy_use_the_adjacent_higher_tier():
    medium_host = FakeHost([midi_chunk([(84, 0, 120)])])
    medium_status, unused_report = copy_drums(
        medium_host, 'track', 'M')
    expect('from Hard' in medium_status and
           pitches(medium_host.chunks[0]) == [72, 84],
           'Copy to Medium did not use the Hard tier')

    easy_host = FakeHost([midi_chunk([(72, 0, 120)])])
    easy_status, unused_report = copy_drums(easy_host, 'track', 'E')
    expect('from Medium' in easy_status and
           pitches(easy_host.chunks[0]) == [60, 72],
           'Copy to Easy did not use the Medium tier')


def test_declined_overwrite_makes_no_project_change():
    original = midi_chunk([(96, 0, 120), (84, 0, 120)])
    host = FakeHost([original])
    status, report = copy_drums(
        host, 'track', 'H', lambda unused_message: False)
    expect('cancelled' in status and 'No project changes' in report,
           'cancel result differs')
    expect(host.chunks[0] == original and host.write_calls == 0 and
           host.undo_begin == 0,
           'declined overwrite changed the project or opened Undo')


def test_stale_chunk_is_refused_after_confirmation():
    original = midi_chunk([(96, 0, 120), (84, 0, 120)])
    host = FakeHost([original])

    def confirm_and_change(unused_message):
        host.chunks[0] = original.replace('LENGTH 30', 'LENGTH 31')
        return True

    try:
        copy_drums(host, 'track', 'H', confirm_and_change)
    except MidiChunkTransactionError as exc:
        expect('changed after analysis' in str(exc),
               'stale-item refusal used the wrong error')
    else:
        raise AssertionError('stale MIDI item was written')
    expect(host.write_calls == 0 and host.undo_begin == 0,
           'stale-item refusal called the setter or opened Undo')


def test_unique_pool_guid_is_allowed():
    host = FakeHost([midi_chunk([(96, 0, 120)], pooled=True)])
    status, unused_report = copy_drums(host, 'track', 'H')
    expect('copied 1 note' in status and 84 in pitches(host.chunks[0]),
           'unique POOLEDEVTS source was mistaken for a shared pool')


def test_current_reaper_source_metadata_is_preserved():
    original = midi_chunk(
        [(96, 0, 120)], pooled=True, current_metadata=True)
    host = FakeHost([original])
    status, unused_report = copy_drums(host, 'track', 'H')
    expect('copied 1 note' in status,
           'current REAPER source metadata blocked the copy')
    changed = host.chunks[0]
    expect(changed.count('CCINTERP 32\n') == 2 and
           'CHASE_CC_TAKEOFFS 1\n' in changed and
           'GUID {22222222-2222-2222-2222-222222222222}\n' in changed,
           'current REAPER source metadata was not preserved exactly')
    expect(parse_midi_chunk(changed).mutation_blockers() == [],
           'copied current-format chunk became mutation-unsafe')


def test_shared_pool_source_is_refused_before_write():
    first = midi_chunk([(96, 0, 120)], pooled=True)
    second = midi_chunk([(97, 480, 600)], pooled=True)
    host = FakeHost([first, second])
    try:
        copy_drums(host, 'track', 'H')
    except MidiChunkError as exc:
        expect('pooled/shared' in str(exc) and 'referenced 2 times' in str(exc),
               'shared-pool refusal detail differs')
    else:
        raise AssertionError('shared pooled MIDI source was accepted')
    expect(host.write_calls == 0 and host.undo_begin == 0,
           'shared-pool refusal called the setter or opened Undo')


def test_failed_readback_rolls_back_exactly():
    original = midi_chunk([(96, 0, 120)])
    host = FakeHost([original])
    host.corrupt_next_write = True
    try:
        copy_drums(host, 'track', 'H')
    except MidiChunkTransactionError as exc:
        expect('Rollback exact: yes' in str(exc),
               'failed write did not report verified rollback')
        expect('Expected bytes:' not in str(exc) and
               'Expected excerpt' not in str(exc),
               'default failure exposed development diagnostics')
    else:
        raise AssertionError('corrupt read-back was accepted')
    expect(host.chunks[0] == original and host.write_calls == 2,
           'failed write did not restore the exact original chunk')
    expect(host.undo_begin == 1 and len(host.undo_end) == 1 and
           'FAILED; rollback attempted' in host.undo_end[0],
           'failed transaction did not close its Undo block')


def test_development_mode_includes_readback_diagnostic():
    original = midi_chunk([(96, 0, 120)])
    host = FakeHost([original])
    host.corrupt_next_write = True
    set_development_mode(True)
    try:
        try:
            copy_drums(host, 'track', 'H')
        except MidiChunkTransactionError as exc:
            expect('Expected bytes:' in str(exc) and
                   'Expected excerpt' in str(exc) and
                   'Actual excerpt' in str(exc) and
                   'CORRUPTED' in str(exc),
                   'development mode omitted the read-back diagnostic')
        else:
            raise AssertionError('corrupt read-back was accepted')
    finally:
        set_development_mode(False)


def test_semantic_verification_accepts_only_known_extended_header_rewrite():
    original = midi_chunk([(96, 0, 120)], text='[mix 3 drums0]')
    host = FakeHost([original])
    original_write = host.write_item_chunk

    def normalize_header(item, chunk):
        if host.write_calls == 0:
            chunk = chunk.replace(
                '<X 0 0\n', '<X 0 0 0 0 1 "[mix 3 drums0]"\n')
        original_write(item, chunk)

    host.write_item_chunk = normalize_header
    set_semantic_midi_write_verification(True)
    status, unused_report = copy_drums(host, 'track', 'H')
    expect('copied 1 note' in status and host.write_calls == 1,
           'known extended header normalization was not accepted')


def test_exact_mode_rejects_known_extended_header_rewrite():
    original = midi_chunk([(96, 0, 120)], text='[mix 3 drums0]')
    host = FakeHost([original])
    original_write = host.write_item_chunk

    def normalize_header(item, chunk):
        if host.write_calls == 0:
            chunk = chunk.replace(
                '<X 0 0\n', '<X 0 0 0 0 1 "[mix 3 drums0]"\n')
        original_write(item, chunk)

    host.write_item_chunk = normalize_header
    set_semantic_midi_write_verification(False)
    try:
        try:
            copy_drums(host, 'track', 'H')
        except MidiChunkTransactionError as exc:
            expect('Rollback exact: yes' in str(exc),
                   'exact mode did not reject and roll back normalization')
        else:
            raise AssertionError('exact mode accepted a changed read-back')
    finally:
        set_semantic_midi_write_verification(True)


def test_semantic_verification_rejects_payload_or_non_event_changes():
    original = midi_chunk([(96, 0, 120)], text='[mix 3 drums0]')

    def expect_rejected(transform, label):
        host = FakeHost([original])
        original_write = host.write_item_chunk

        def corrupt_item(item, chunk):
            if host.write_calls == 0:
                chunk = chunk.replace(
                    '<X 0 0\n',
                    '<X 0 0 0 0 1 "[mix 3 drums0]"\n')
                chunk = transform(chunk)
            original_write(item, chunk)

        host.write_item_chunk = corrupt_item
        try:
            copy_drums(host, 'track', 'H')
        except MidiChunkTransactionError as exc:
            expect('Rollback exact: yes' in str(exc),
                   'semantic mode did not roll back %s' % label)
        else:
            raise AssertionError('semantic mode accepted %s' % label)

    expect_rejected(
        lambda chunk: chunk.replace('POSITION 0', 'POSITION 1'),
        'an unrelated item change')
    expect_rejected(
        lambda chunk: chunk.replace(
            _meta_event(0, '[mix 3 drums0]').splitlines()[1],
            _meta_event(0, '[mix 3 drums1]').splitlines()[1]),
        'a changed MIDI payload')


def test_multiple_items_are_replaced_in_one_transaction():
    host = FakeHost([
        midi_chunk([(96, 0, 120)]),
        midi_chunk([(97, 480, 600), (84, 0, 120)]),
    ])
    status, report = copy_drums(
        host, 'track', 'H', lambda unused_message: True)
    expect('copied 2 notes' in status and '2 MIDI items' in report,
           'multi-item copy summary differs')
    expect(84 in pitches(host.chunks[0]) and
           pitches(host.chunks[1]) == [85, 97],
           'multi-item copy did not preserve source item/tick context')
    expect(host.undo_begin == 1 and len(host.undo_end) == 1,
           'multi-item copy did not use one Undo transaction')


def test_legacy_host_write_and_undo_adapter_shapes():
    calls = []

    class Api(object):
        def RPR_CountMediaItems(self, project):
            calls.append(('count-items', project))
            return 3

        def RPR_GetMediaItem(self, project, index):
            calls.append(('get-item', project, index))
            return 'item-%d' % index

        def RPR_GetSetItemState(self, item, chunk, capacity):
            calls.append(('write', item, chunk, capacity))
            return (True, item, chunk, capacity)

        def RPR_Undo_BeginBlock2(self, project):
            calls.append(('begin', project))

        def RPR_Undo_EndBlock2(self, project, description, flags):
            calls.append(('end', project, description, flags))

        def RPR_UpdateArrange(self):
            calls.append(('arrange',))

    host = Reaper420Host(Api())
    expect(host.project_item_count() == 3 and
           host.get_project_item(2) == 'item-2',
           'legacy project item enumeration shape differs')
    host.write_item_chunk('item', 'chunk')
    host.begin_undo()
    host.update_arrange()
    host.end_undo('Copy Drums X to H')
    expect(calls[2][:3] == ('write', 'item', 'chunk') and
           calls[2][3] >= 65536,
           'legacy item-state setter shape differs')
    expect(calls[:2] == [('count-items', 0), ('get-item', 0, 2)] and
           calls[3:] == [
        ('begin', 0), ('arrange',),
        ('end', 0, 'Copy Drums X to H', -1)],
        'legacy Undo/arrange adapter shape differs')


def main():
    tests = [
        test_copy_to_hard_replaces_target_and_preserves_other_events,
        test_copy_without_existing_target_needs_no_confirmation,
        test_medium_and_easy_use_the_adjacent_higher_tier,
        test_declined_overwrite_makes_no_project_change,
        test_stale_chunk_is_refused_after_confirmation,
        test_unique_pool_guid_is_allowed,
        test_current_reaper_source_metadata_is_preserved,
        test_shared_pool_source_is_refused_before_write,
        test_failed_readback_rolls_back_exactly,
        test_development_mode_includes_readback_diagnostic,
        test_semantic_verification_accepts_only_known_extended_header_rewrite,
        test_exact_mode_rejects_known_extended_header_rewrite,
        test_semantic_verification_rejects_payload_or_non_event_changes,
        test_multiple_items_are_replaced_in_one_transaction,
        test_legacy_host_write_and_undo_adapter_shapes,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty Drums copy tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
