"""Desktop tests for the first production Tab Input slice."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_guitar_guide import (
    add_empty_note,
    guitar_tab_guide,
    parse_tab_horizontal,
    parse_tab_vertical,
)
from rock_band_general_helper_vkr.actions_keys_guides import (
    pro_keys_tab_guide,
    vocal_tab_guide,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def test_horizontal_and_vertical_match():
    horizontal = parse_tab_horizontal('x 3 2 0 1 0')
    vertical = parse_tab_vertical('0\n1\n0\n2\n3\nx')
    expect(len(horizontal) == 1 and len(vertical) == 1,
           'expected one event in each format')
    expect(sorted(horizontal[0].pitches) == sorted(vertical[0].pitches),
           'equivalent C-major tabs produced different pitches')
    expect(sorted(horizontal[0].pitches) == [48, 52, 55, 60, 64],
           'C-major pitches differ')


def test_phrase_breaks():
    horizontal = parse_tab_horizontal('0 - - - - -\n\n3 - - - - -')
    expect([event.phrase_index for event in horizontal] == [1, 2],
           'horizontal blank-line phrase break failed')
    vertical = parse_tab_vertical(
        '0 - 3\n- - -\n- - -\n- - -\n- - -\n- - -')
    expect([event.phrase_index for event in vertical] == [1, 2],
           'vertical all-dash phrase break failed')


def test_add_note():
    expect(add_empty_note('', False) == '- - - - - -\n',
           'horizontal empty note differs')
    expect(add_empty_note('', True) == '-\n-\n-\n-\n-\n-',
           'vertical first column differs')
    expanded = add_empty_note('0\n1\n0\n2\n3\nx', True)
    expect(expanded.splitlines()[0] == '0 -' and
           expanded.splitlines()[-1] == 'x -',
           'vertical column append differs')


def test_guitar_guide_common_shapes():
    status, result = guitar_tab_guide('3 3 2 0 1 0')
    expect('1 note event' in status, 'guitar status differs')
    expect('3-note chord' in result, 'open C/G was compressed incorrectly')
    status, result = guitar_tab_guide('5 7 7 - - -')
    expect('Power chord' in result, 'power-chord classification missing')
    expect('[G+Y]' in result, 'power chord did not receive 1-3 gems')


def test_keys_and_vocal_guides():
    status, result = pro_keys_tab_guide('x 3 2 0 1 0')
    expect('suggested C2-E3' in status, 'Pro Keys range suggestion differs')
    expect('All 1 events fit within C2-E3.' in result,
           'Pro Keys fit report differs')
    status, result = pro_keys_tab_guide(
        'x 3 2 0 1 0', animation=True)
    expect('(animation)' in status and 'full C2-C4 range' in result,
           'Pro Keys animation report differs')
    status, result = vocal_tab_guide('x 3 2 0 1 0')
    expect('all fit C1-C5' in status, 'Vocal fit report differs')


def test_ui_modules_import_without_starting_tk():
    from rock_band_general_helper_vkr import ui, ui_midi
    expect(hasattr(ui, 'GeneralHelperApp'), 'main UI class is missing')
    expect(hasattr(ui_midi, 'TabInputView'), 'Tab Input UI class is missing')


def main():
    tests = [
        test_horizontal_and_vertical_match,
        test_phrase_breaks,
        test_add_note,
        test_guitar_guide_common_shapes,
        test_keys_and_vocal_guides,
        test_ui_modules_import_without_starting_tk,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Tab Input production tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()

