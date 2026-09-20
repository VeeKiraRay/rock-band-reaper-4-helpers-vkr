"""Desktop tests for the first read-only Venue Actions slice."""

from __future__ import print_function

import base64
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_venue_validate import (
    validate_lighting_blends, validate_venue_lighting)
from rock_band_general_helper_vkr.actions_venue_validate_camera import (
    build_band_lineups, validate_camera_stacks, validate_venue_camera)
from rock_band_general_helper_vkr.venue import (
    annotate_venue_blends, build_event_sections, list_event_sections,
    list_lighting_postproc, list_venue_events, parse_prc_event)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def _meta_payload(meta_type, message):
    payload = b'\xff' + bytes(bytearray([meta_type])) + message.encode('ascii')
    encoded = base64.b64encode(payload)
    return encoded if isinstance(encoded, str) else encoded.decode('ascii')


def midi_chunk(events, ppq=480):
    lines = []
    previous = 0
    for tick, meta_type, message in sorted(events, key=lambda row: row[0]):
        lines.append('<X %d 0\n  %s\n>\n' %
                     (tick - previous, _meta_payload(meta_type, message)))
        previous = tick
    return ('<ITEM\n<SOURCE MIDI\nHASDATA 1 %d QN\n%s'
            'IGNTEMPO 0 120 4 4\n>\n>\n') % (ppq, ''.join(lines))


class FakeHost(object):
    def __init__(self, tracks, muted=(), selection=(None, None)):
        self.tracks = list(tracks)
        self.muted = set(muted)
        self.selection = selection
        self.writes = 0

    def track_count(self):
        return len(self.tracks)

    def get_track(self, index):
        return index

    def track_name(self, track, unused_index):
        return self.tracks[track][0]

    def track_muted(self, track):
        return self.tracks[track][0] in self.muted

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

    def read_item_chunk(self, item):
        return self.tracks[item][1]

    def time_to_qn(self, seconds):
        return float(seconds) * 2.0

    def qn_to_time(self, quarter_notes):
        return float(quarter_notes) / 2.0

    def time_selection(self):
        return self.selection

    def project_item_count(self):
        return len([track for track in self.tracks if track[1] is not None])

    def get_project_item(self, index):
        return [position for position, track in enumerate(self.tracks)
                if track[1] is not None][index]


def event(ppq, message, seconds=None):
    return {'ppq': ppq, 'msg': message,
            't': float(ppq) / 960.0 if seconds is None else seconds,
            'meta_type': 1}


def test_blend_annotation_and_lighting_rules():
    lighting = [
        event(0, '[lighting (verse)]'),
        event(720, '[lighting (verse)]'),
        event(960, '[lighting (chorus)]'),
        event(1920, '[lighting (loop_cool)]'),
    ]
    annotated = annotate_venue_blends(lighting)
    expect(len(annotated) == 3 and annotated[0]['blend_out_ppq'] == 720,
           'blend anchor was not collapsed and annotated')
    findings = validate_lighting_blends(
        lighting, [], [event(20, '[first]'), event(720, '[first]')], 15, 480)
    expect(len(findings['missing_first']) == 2,
           'manual lighting changes missing [first] were not found')
    expect(findings['stray_first'][0]['kind'] == 'misaligned',
           'near [first] was not recognized as misaligned')
    expect(findings['stray_first'][1]['kind'] == 'on_restatement',
           '[first] on a blend anchor was not rejected')
    expect(findings['blend']['lt']['anchored'] == 1,
           'anchored lighting change was not counted')


def test_prc_parser_and_lettered_section_merge():
    expect(parse_prc_event('[prc_verse_2b]') ==
           {'name': 'verse', 'num': 2, 'letter': 'b'},
           'numbered/lettered section did not parse')
    events = [
        dict(event(0, '[prc_intro]'), t=0.0),
        dict(event(480, '[prc_verse_1a]'), t=1.0),
        dict(event(960, '[prc_verse_1b]'), t=2.0),
        dict(event(1440, '[prc_chorus_1]'), t=3.0),
    ]
    sections = build_event_sections(events, 10.0)
    expect(len(sections) == 3 and sections[1]['sub_count'] == 2,
           'lettered section parts were not merged')
    expect(sections[1]['t_start'] == 1.0 and sections[1]['t_end'] == 3.0,
           'section bounds were not derived from neighboring sections')


def test_camera_stack_rules_and_lineups():
    lineups = build_band_lineups({'d': False, 'v': False})
    expect([row['label'] for row in lineups] ==
           ['Bass + Guitar', 'Bass + Keys', 'Guitar + Keys'],
           'three playable four-person lineups were not built')
    camera = [
        event(0, '[coop_bg_near]'), event(0, '[coop_bk_near]'),
        event(0, '[coop_gk_near]'), event(0, '[coop_gk_near]'),
        event(30, '[directed_keys]'),
    ]
    findings = validate_camera_stacks(camera, lineups, 60)
    expect(len(findings['duplicates']) == 1,
           'same-tick duplicate camera shot was not found')
    expect(len(findings['near_stacks']) == 1,
           'near-but-not-stacked camera shot was not found')
    expect(findings['spots'] == 2 and findings['stacked'] == 1,
           'camera spot counts are incorrect')


def test_full_reports_read_chunks_without_writing():
    venue = midi_chunk([
        (0, 3, 'VENUE'),
        (0, 1, '[lighting (verse)]'), (0, 1, '[first]'),
        (0, 1, '[coop_all_far]'),
        (480, 1, '[lighting (verse)]'),
        (720, 1, '[lighting (chorus)]'),
        (960, 1, '[ProFilm_a.pp]'),
        (1440, 1, '[mystery_event]'),
    ])
    events = midi_chunk([
        (0, 3, 'EVENTS'), (0, 1, '[prc_intro]'),
        (960, 1, '[prc_verse_1a]'), (1440, 1, '[prc_verse_1b]'),
    ])
    tracks = [('VENUE', venue), ('EVENTS', events),
              ('PART DRUMS', venue), ('PART VOCALS', venue),
              ('PART BASS', venue), ('PART GUITAR', venue),
              ('PART KEYS', venue)]
    host = FakeHost(tracks)
    status, report = list_venue_events(host)
    expect('7 events, 6 unique' in status and '[mystery_event]' in report,
           'VENUE inventory did not report totals and unknown events')
    status, report = list_lighting_postproc(host)
    expect('4 lighting/postproc events' in status and '[ProFilm_a.pp]' in report,
           'lighting/postproc inventory is incomplete')
    status, report = list_event_sections(host)
    expect('2 event sections' in status and '(2 parts)' in report,
           'EVENTS section report did not merge lettered markers')
    status, report = validate_venue_lighting(host)
    expect('issue' in status and 'blends' in report.lower(),
           'lighting validation integration report did not run')
    status, report = validate_venue_camera(host)
    expect('no issues' in status and 'three lineups' not in report.lower(),
           'camera validation integration report did not run')
    expect(host.writes == 0, 'a read-only Venue action attempted a write')


def test_missing_tracks_are_reported_without_exception():
    host = FakeHost([])
    for action in (list_venue_events, list_lighting_postproc,
                   list_event_sections, validate_venue_lighting,
                   validate_venue_camera):
        unused_status, report = action(host)
        expect('No track named' in report,
               '%s did not report its missing track' % action.__name__)


def test_venue_ui_exposes_all_subtabs():
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
        print('SKIP: Tk display unavailable for Venue UI test')
        if root is not None:
            root.destroy()
        return
    try:
        view = VenueView(root, lambda unused_status, unused_result: None,
                         FakeHost([]))
        labels = [view.notebook.tab(tab, 'text')
                  for tab in view.notebook.tabs()]
        expect(labels == ['Actions', 'Events', 'Themes gen', 'Section gen',
                          'Manual gen', 'Keyframes', 'Preview'],
               'Venue sub-tab order differs from the modern helper')
        for tab in view.notebook.tabs():
            page = view.notebook.nametowidget(tab)
            pending = list(page.winfo_children())
            scrollbars = []
            while pending:
                child = pending.pop()
                if child.winfo_class() == 'TScrollbar':
                    scrollbars.append(child)
                pending.extend(child.winfo_children())
            expect(len(scrollbars) == 1,
                   '%s does not have exactly one page scrollbar' %
                   view.notebook.tab(tab, 'text'))

        view.pack(fill=tk.BOTH, expand=True)
        root.geometry('520x240')
        root.deiconify()
        view.notebook.select(view.manual_page)
        root.update()
        view.manual_page.canvas.yview_moveto(0.0)
        root.update()
        header_y = view.notebook.winfo_rooty()
        content_y = view.manual_page.content.winfo_rooty()
        view.manual_page.canvas.yview_moveto(1.0)
        root.update()
        expect(view.notebook.winfo_rooty() == header_y,
               'Venue sub-tab row moved with its page content')
        expect(view.manual_page.content.winfo_rooty() != content_y,
               'Venue Manual page did not scroll independently of its tabs')
    finally:
        root.destroy()


def main():
    tests = [
        test_blend_annotation_and_lighting_rules,
        test_prc_parser_and_lettered_section_merge,
        test_camera_stack_rules_and_lineups,
        test_full_reports_read_chunks_without_writing,
        test_missing_tracks_are_reported_without_exception,
        test_venue_ui_exposes_all_subtabs,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Venue Actions tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
