"""Desktop tests for read-only Difficulty > Drums validation."""

from __future__ import print_function

import base64
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_difficulty_drums import (
    read_drums_events,
    run_drums_checks,
    validate_all_drums,
    validate_drums,
)
from rock_band_general_helper_vkr.difficulty_read import (
    _load_items, read_midi_notes)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def _encoded_meta(message):
    payload = b'\xff\x01' + message.encode('ascii')
    encoded = base64.b64encode(payload)
    if not isinstance(encoded, str):
        encoded = encoded.decode('ascii')
    return encoded


def midi_chunk(notes, texts=(), ppq=480):
    records = []
    for record in notes:
        pitch, start, end = record[:3]
        velocity = record[3] if len(record) > 3 else 96
        records.append((start, 1, 'note', ('90', pitch, velocity)))
        records.append((end, 0, 'note', ('80', pitch, 0)))
    for tick, message in texts:
        records.append((tick, 2, 'text', message))
    records.sort(key=lambda event: (event[0], event[1]))
    previous = 0
    lines = []
    for tick, unused_order, kind, data in records:
        delta = tick - previous
        if kind == 'note':
            lines.append('E %d %s %02x %02x\n' %
                         (delta, data[0], data[1], data[2]))
        else:
            lines.append('<X %d 0\n  %s\n>\n' %
                         (delta, _encoded_meta(data)))
        previous = tick
    return ('<ITEM\n<SOURCE MIDI\nHASDATA 1 %d QN\n%s'
            'IGNTEMPO 0 120 4 4\n>\n>\n') % (ppq, ''.join(lines))


class FakeHost(object):
    def __init__(self, tempo=120, measures=True):
        self.tempo = tempo
        self.measures = measures

    def item_count(self, unused_track):
        return 1

    def get_item(self, track, unused_index):
        return track

    def active_take(self, unused_item):
        return 'take'

    def take_play_rate(self, unused_take):
        return 1.0

    def item_position(self, unused_item):
        return 0.0

    def item_length(self, unused_item):
        return 30.0

    def take_start_offset(self, unused_take):
        return 0.0

    def time_to_qn(self, seconds):
        return float(seconds) * self.tempo / 60.0

    def qn_to_time(self, quarter_notes):
        return float(quarter_notes) * 60.0 / self.tempo

    def measure_at(self, seconds):
        if not self.measures:
            return None
        return int(self.time_to_qn(seconds) // 4) + 1

    def read_item_chunk(self, item):
        return item


def _all_notes(host, chunk):
    return read_midi_notes(host, _load_items(host, chunk))


def test_easy_chord_and_kick_pairing_rules():
    host = FakeHost()
    notes = _all_notes(host, midi_chunk([
        (60, 0, 120), (61, 0, 120), (62, 0, 120)]))
    events = read_drums_events('E', notes)
    report, total = run_drums_checks(host, 'E', events, notes)
    expect(total >= 2 and 'max 2 simultaneous notes' in report,
           'Easy three-note chord was not reported')
    expect('pairs a gem with kick' in report,
           'Easy kick pairing was not reported')


def test_medium_tempo_kick_rules_and_optional_measure_fallback():
    chunk = midi_chunk([(72, 240, 300), (72, 480, 540)])
    host = FakeHost(180)
    notes = _all_notes(host, chunk)
    events = read_drums_events('M', notes)
    report, unused_total = run_drums_checks(host, 'M', events, notes)
    expect('not on the quarter-note grid' in report,
           'off-grid fast-tempo kick was not reported')
    expect('Measure 1 has 2 kicks' in report,
           'fast-tempo per-measure kick limit was not reported')
    fallback = FakeHost(180, measures=False)
    fallback_notes = _all_notes(fallback, chunk)
    fallback_events = read_drums_events('M', fallback_notes)
    fallback_report, unused_total = run_drums_checks(
        fallback, 'M', fallback_events, fallback_notes)
    expect('not checked (measure formatting unavailable)' in fallback_report,
           'missing legacy measure formatting was not disclosed')


def test_fill_roll_grid_count_density_and_velocity_rules():
    host = FakeHost(180)
    chunk = midi_chunk([
        (84, 120, 180), (85, 240, 300), (85, 360, 420),
        (120, 0, 600), (126, 120, 600, 40),
    ])
    notes = _all_notes(host, chunk)
    events = read_drums_events('H', notes)
    report, total = run_drums_checks(host, 'H', events, notes)
    expect(total >= 4 and 'kick during a drum fill' in report,
           'kick-in-fill rule was not reported')
    expect('does not start on an 8th/quarter-note grid' in report,
           'off-grid roll marker was not reported')
    expect('roll has 3 hits' in report and '16th-note rate' in report,
           'roll count or density rule was not reported')
    expect('Roll marker velocity 40' in report,
           'Hard roll eligibility velocity was not reported')


def test_hard_progression_and_disco_mix_rules():
    host = FakeHost()
    chunk = midi_chunk([
        (96, 0, 120), (96, 480, 600),
        (84, 0, 120), (84, 480, 600),
    ], [(0, '[mix 2 drums0d]'), (480, '[mix 3 drums0]')])
    status, report = validate_drums(host, chunk, 'H')
    expect('issue' in status and 'unchanged copy of Expert' in report,
           'Hard adjacent-tier reduction rule was not reported')
    expect('Hard has 2 kicks and Expert has 2 kicks' in report,
           'Hard-vs-Expert kick reduction was not reported')
    expect('Hard mix event uses the disco variant' in report,
           'Hard disco unflip rule was not reported')
    expect('Disco flip status' in report and '(Expert)' in report,
           'informational disco scan was not appended')


def test_validate_all_reports_density_hints_and_empty_tiers():
    host = FakeHost(180)
    chunk = midi_chunk([
        (84, 0, 60), (85, 240, 300),
        (86, 480, 540), (87, 720, 780),
    ])
    status, report = validate_all_drums(host, chunk)
    expect('X:empty' in status and 'M:empty' in status and 'E:empty' in status,
           'empty Drums tiers were not summarized')
    expect('4 consecutive 8th notes' in report,
           'Hard timekeeping density run was not reported')
    expect('Try removing kicks from adjacent 8th or 16th notes.' in report,
           'Hard qualitative authoring hints were not included')
    expect('no [mix N drums...] events' in report,
           'empty disco scan result was not included')


def test_ui_auto_detects_drums_and_uses_drums_refresh_wording():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_difficulty import DifficultyView

    class TrackHost(object):
        names = ('OTHER', 'PART DRUMS', 'PART KEYS')

        def track_count(self):
            return len(self.names)

        def get_track(self, index):
            return index

        def track_name(self, track, unused_index):
            return self.names[track]

        def project_info(self):
            return {'identity': 'test-project', 'path': '', 'name': 'Test'}

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for Drums UI test')
        if root is not None:
            root.destroy()
        return
    try:
        shown = []
        view = DifficultyView(
            root, lambda status, result: shown.append((status, result)),
            TrackHost())
        expect(view.drums_pane.selected_track(view.track_records) == 1,
               'PART DRUMS was not auto-detected')
        view.refresh_tracks(focus='drums')
        expect(shown[-1][0] == 'Drums track auto-detected.' and
               'PART DRUMS' in shown[-1][1],
               'Drums refresh used the wrong wording')
    finally:
        root.destroy()


def main():
    tests = [
        test_easy_chord_and_kick_pairing_rules,
        test_medium_tempo_kick_rules_and_optional_measure_fallback,
        test_fill_roll_grid_count_density_and_velocity_rules,
        test_hard_progression_and_disco_mix_rules,
        test_validate_all_reports_density_hints_and_empty_tiers,
        test_ui_auto_detects_drums_and_uses_drums_refresh_wording,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Difficulty Drums tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
