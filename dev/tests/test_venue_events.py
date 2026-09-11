"""Desktop tests for guarded Venue > Events insertion."""

from __future__ import print_function

import base64
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.midi_chunk import parse_midi_chunk
from rock_band_general_helper_vkr.actions_venue_events import (
    VenueEventsError, add_section_event, insert_events_event,
    next_section_event, scan_events_text_events, validate_plain_insert)
from rock_band_general_helper_vkr.section_events import (
    SECTION_EVENT_BASE, SECTION_EVENT_GROUPS)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def _payload(meta_type, message):
    raw = b'\xff' + bytes(bytearray([meta_type])) + message.encode('ascii')
    encoded = base64.b64encode(raw)
    return encoded if isinstance(encoded, str) else encoded.decode('ascii')


def midi_chunk(events=(), pool_guid=None, rich_headers=False):
    rows = []
    previous = 0
    for tick, meta_type, message in sorted(events, key=lambda row: row[0]):
        summary = (' 0 0 %d %s' % (meta_type, message)
                   if rich_headers else '')
        rows.append('<X %d 0%s\n  %s\n>\n' %
                    (tick - previous, summary,
                     _payload(meta_type, message)))
        previous = tick
    pool = 'POOLEDEVTS %s\n' % pool_guid if pool_guid else ''
    return ('<ITEM\n<SOURCE MIDI\nHASDATA 1 480 QN\n%s%s'
            'IGNTEMPO 0 120 4 4\n>\n>\n') % (pool, ''.join(rows))


class FakeHost(object):
    def __init__(self, tracks, cursor=2.0):
        self.tracks = [list(track) for track in tracks]
        self.cursor = cursor
        self.writes = []
        self.undo = []
        self.arranges = 0
        self.reads = {}
        self.stale_on_second_read = False

    def track_count(self):
        return len(self.tracks)

    def get_track(self, index):
        return index

    def track_name(self, track, unused_index):
        return self.tracks[track][0]

    def item_count(self, track):
        return 1 if self.tracks[track][1] is not None else 0

    def get_item(self, track, unused_index):
        return track

    def active_take(self, item):
        return 'take-%d' % item

    def take_play_rate(self, unused_take):
        return 1.0

    def take_start_offset(self, unused_take):
        return 0.0

    def item_position(self, unused_item):
        return 0.0

    def item_length(self, unused_item):
        return 30.0

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, quarter_notes):
        return float(quarter_notes) / 2.0

    def cursor_position(self):
        return self.cursor

    def read_item_chunk(self, item):
        self.reads[item] = self.reads.get(item, 0) + 1
        if self.stale_on_second_read and item == 0 and self.reads[item] == 2:
            self.tracks[item][1] = self.tracks[item][1].replace(
                'IGNTEMPO 0 120', 'IGNTEMPO 0 121')
        return self.tracks[item][1]

    def write_item_chunk(self, item, chunk):
        self.writes.append((item, chunk))
        self.tracks[item][1] = chunk

    def project_item_count(self):
        return len([track for track in self.tracks if track[1] is not None])

    def get_project_item(self, index):
        return [position for position, track in enumerate(self.tracks)
                if track[1] is not None][index]

    def begin_undo(self):
        self.undo.append('begin')

    def end_undo(self, description):
        self.undo.append(description)

    def update_arrange(self):
        self.arranges += 1


def make_scan(rows):
    return scan_events_text_events([
        {'msg': message, 't': time_value, 'ppq': int(time_value * 960),
         'meta_type': 1, 'ordinal': index}
        for index, (message, time_value) in enumerate(rows)])


def inserted_texts(host):
    return [event.meta_payload for event in
            parse_midi_chunk(host.tracks[0][1]).text_events(0x01)]


def test_vocabulary_shape_and_caps():
    expect(len(SECTION_EVENT_GROUPS) == 11,
           'the modern Events groups were not all ported')
    expect(SECTION_EVENT_BASE['verse']['caps'] == 'ffffdddddd',
           'verse caps differ from the source vocabulary')
    expect(SECTION_EVENT_BASE['gtr_solo']['caps'] == 'snnnnnnnnn',
           'guitar solo caps differ from the source vocabulary')
    expect(SECTION_EVENT_BASE['bre']['caps'] == '.',
           'bare-only BRE vocabulary was not preserved')


def test_plain_lettered_sequence_and_exclusivity():
    empty = make_scan([])
    caps = SECTION_EVENT_BASE['verse']['caps']
    expect(next_section_event(empty, 'verse', 0, caps, False, False,
                              10, 9600)[0] == '[prc_verse]',
           'plain bare form is wrong')
    expect(next_section_event(empty, 'verse', 1, caps, False, True,
                              10, 9600)[0] == '[prc_verse_1a]',
           'lettered numbered form is wrong')
    scan = make_scan([('[prc_verse_1a]', 2), ('[prc_verse_1c]', 6)])
    expect(next_section_event(scan, 'verse', 1, caps, False, True,
                              4, 3840)[0] == '[prc_verse_1b]',
           'the first missing letter was not selected')
    unused_event, reason = next_section_event(
        scan, 'verse', 1, caps, False, False, 4, 3840)
    expect('Lettered [prc_verse_1a] exists' in reason,
           'plain/lettered mixing was not refused')
    unused_event, reason = next_section_event(
        empty, 'verse', 2, caps, False, True, 4, 3840)
    expect('[prc_verse_1]' in reason and 'in order' in reason,
           'out-of-order numbering was not refused')


def test_timeline_spot_generic_and_plain_rules():
    caps = SECTION_EVENT_BASE['verse']['caps']
    scan = make_scan([('[prc_verse_1]', 10), ('[prc_verse_3]', 30)])
    expect(next_section_event(scan, 'verse', 2, caps, False, False,
                              20, 19200)[0] == '[prc_verse_2]',
           'ordered number insertion was blocked')
    unused_event, reason = next_section_event(
        scan, 'verse', 2, caps, False, False, 40, 38400)
    expect('before [prc_verse_3]' in reason,
           'timeline ordering after a later family was not refused')
    expect(next_section_event(make_scan([]), 'a', 3, None, True, True,
                              10, 9600)[1].startswith('Add [prc_a2]'),
           'generic numbering did not use the no-underscore form')
    occupied = make_scan([('[prc_chorus]', 5)])
    expect(next_section_event(occupied, 'verse', 0, caps, False, True,
                              5, 4800)[0] is None,
           'same-position section event was not refused')
    scan = make_scan([('[crowd_normal]', 2), ('[music_start]', 4)])
    expect(validate_plain_insert(scan, '[crowd_normal]', 3840)[0],
           'crowd stacking should be allowed')
    expect(not validate_plain_insert(scan, '[music_start]', 8000)[0],
           'duplicate global event was not refused')


def test_guarded_letter_insert_and_one_step_undo():
    chunk = midi_chunk([(0, 3, 'EVENTS')], rich_headers=True)
    host = FakeHost([('EVENTS', chunk)])
    caps = SECTION_EVENT_BASE['verse']['caps']
    status, report = add_section_event(
        host, 'verse', 1, caps, False, True)
    expect('[prc_verse_1a]' in status and 'Undo:' in report,
           'first lettered insertion did not report success')
    host.cursor = 4.0
    status, unused_report = add_section_event(
        host, 'verse', 1, caps, False, True)
    expect('[prc_verse_1b]' in status,
           'second insertion did not advance the letter')
    expect(inserted_texts(host) == ['[prc_verse_1a]', '[prc_verse_1b]'],
           'inserted FF 01 events did not read back exactly')
    expect('<X 1920 0 0 0 1 [prc_verse_1a]\n' in host.tracks[0][1],
           'insertion did not match REAPER full text-event headers')
    expect(len(host.writes) == 2 and len(host.undo) == 4 and
           host.undo[0] == 'begin',
           'each accepted insertion did not create one transaction')


def test_refusal_crowd_stack_and_cursor_bounds():
    chunk = midi_chunk([(0, 3, 'EVENTS'), (1920, 1, '[music_start]')])
    host = FakeHost([('EVENTS', chunk)], cursor=2.0)
    status, reason = insert_events_event(host, '[music_end]')
    expect('blocked' in status.lower() and 'already at this position' in reason,
           'same-position global insertion was not blocked')
    expect(not host.writes and not host.undo,
           'refused insertion touched the project or Undo history')
    status, unused_report = insert_events_event(host, '[crowd_normal]')
    expect('Inserted' in status and '[crowd_normal]' in inserted_texts(host),
           'crowd event could not stack on an occupied position')
    outside = FakeHost([('EVENTS', chunk)], cursor=31.0)
    try:
        insert_events_event(outside, '[crowd_normal]')
    except VenueEventsError as exc:
        expect('inside a MIDI item' in str(exc),
               'out-of-item cursor returned the wrong reason')
    else:
        raise AssertionError('out-of-item cursor was accepted')


def test_stale_and_shared_sources_are_refused():
    chunk = midi_chunk([(0, 3, 'EVENTS')])
    stale = FakeHost([('EVENTS', chunk)])
    stale.stale_on_second_read = True
    try:
        insert_events_event(stale, '[crowd_normal]')
    except Exception as exc:
        expect('changed after analysis' in str(exc),
               'stale item returned the wrong reason')
    else:
        raise AssertionError('stale EVENTS chunk was written')
    expect(not stale.writes and not stale.undo,
           'stale-state refusal occurred after mutation began')

    pooled = midi_chunk(
        [(0, 3, 'EVENTS')],
        '{11111111-1111-1111-1111-111111111111}')
    shared = FakeHost([('EVENTS', pooled), ('OTHER', pooled)])
    try:
        insert_events_event(shared, '[crowd_normal]')
    except Exception as exc:
        expect('pooled/shared' in str(exc),
               'shared pool returned the wrong reason')
    else:
        raise AssertionError('shared pooled source was written')
    expect(not shared.writes and not shared.undo,
           'shared-pool refusal touched the project or Undo history')


def test_events_ui_constructs_in_the_venue_tab():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_venue import VenueView
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for Events UI test')
        if root is not None:
            root.destroy()
        return
    try:
        view = VenueView(root, lambda unused_status, unused_result: None,
                         FakeHost([]))
        expect(view.notebook.tab(view.notebook.tabs()[1], 'text') == 'Events',
               'Events view is not in the expected Venue sub-tab')
        events_view = view.nametowidget(view.notebook.tabs()[1])
        expect(events_view.letters.get(),
               'Use letter suffix is not enabled by default')
    finally:
        root.destroy()


def main():
    tests = [
        test_vocabulary_shape_and_caps,
        test_plain_lettered_sequence_and_exclusivity,
        test_timeline_spot_generic_and_plain_rules,
        test_guarded_letter_insert_and_one_step_undo,
        test_refusal_crowd_stack_and_cursor_bounds,
        test_stale_and_shared_sources_are_refused,
        test_events_ui_constructs_in_the_venue_tab,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Venue Events tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
