"""Desktop tests for Metadata Genre data, lookup, and formatting."""

from __future__ import print_function

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.metadata_genres import (
    RB3_GENRE_ORDER,
    RB3_GENRES,
)
from rock_band_general_helper_vkr.metadata_genres_ext import (
    EXTENDED_GENRES,
    GENRE_FAMILIES,
    GENRE_FAMILY_ORDER,
)
from rock_band_general_helper_vkr.metadata_genres_lookup import (
    extended_genre_by_key,
    extended_genres_for_pair,
    format_genre_recommendation,
    genres_in_family,
    rb3_subgenre,
    resolve_extended_genre,
    validate_genre_tables,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def test_documented_counts_and_families():
    expect(len(RB3_GENRE_ORDER) == 29, 'supported genre count differs')
    subgenre_count = sum(len(RB3_GENRES[key]['subgenres'])
                         for key in RB3_GENRE_ORDER)
    expect(subgenre_count == 126, 'supported subgenre count differs')
    expect(len(EXTENDED_GENRES) == 227, 'extended genre count differs')
    expect(set(GENRE_FAMILY_ORDER) == set(GENRE_FAMILIES),
           'family order and labels differ')
    expect(sum(len(genres_in_family(key)) for key in GENRE_FAMILY_ORDER) ==
           len(EXTENDED_GENRES), 'family buckets do not cover every entry')


def test_integrity_validation():
    problems = validate_genre_tables()
    expect(problems == [], 'genre validation failed: %s' % problems)
    for entry in EXTENDED_GENRES:
        resolved = resolve_extended_genre(entry['key'])
        expect(resolved is not None, 'entry did not resolve: %s' % entry['key'])
        expect(len(resolved['candidates']) == len(entry['candidates']),
               'candidate resolution differs: %s' % entry['key'])


def test_scoped_subgenres_and_unknowns():
    rock_garage = rb3_subgenre('rock', 'garage')
    punk_garage = rb3_subgenre('punk', 'garage')
    expect(rock_garage and punk_garage,
           'expected Garage under Rock and Punk')
    expect(rock_garage is not punk_garage,
           'scoped Garage records should be distinct')
    expect(resolve_extended_genre('no_such_genre') is None,
           'unknown extended key should not resolve')
    expect(genres_in_family('no_such_family') == [],
           'unknown family should be empty')


def test_reverse_index_roundtrip():
    for entry in EXTENDED_GENRES:
        for index, candidate in enumerate(entry['candidates']):
            first, lower = extended_genres_for_pair(
                candidate['genre'], candidate['subgenre'])
            expected_bucket = first if index == 0 else lower
            other_bucket = lower if index == 0 else first
            expect(any(item['key'] == entry['key']
                       for item in expected_bucket),
                   'reverse mapping missing: %s' % entry['key'])
            expect(not any(item['key'] == entry['key']
                           for item in other_bucket),
                   'entry appeared in both reverse buckets: %s' % entry['key'])


def test_calibrated_mappings_and_redirects():
    expected = {
        'post_grunge': ('rock', 'hard_rock'),
        'deathcore': ('metal', 'metalcore'),
        'djent': ('metal', 'progressive'),
    }
    for key, pair in expected.items():
        result = resolve_extended_genre(key)
        candidate = result['candidates'][0]
        expect((candidate['genre_key'], candidate['sub_key']) == pair,
               'calibrated mapping differs: %s' % key)
    post_grunge = resolve_extended_genre('post_grunge')
    expect(len(post_grunge['see_also']) == 1 and
           post_grunge['see_also'][0]['label'] == 'Grunge',
           'post-grunge redirect differs')


def test_plain_ascii_and_formatted_details():
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(key)
                walk(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            try:
                value.encode('ascii')
            except UnicodeEncodeError:
                raise AssertionError('non-ASCII genre text: %r' % value)

    walk(RB3_GENRES)
    walk(EXTENDED_GENRES)
    result = resolve_extended_genre('grunge')
    formatted = format_genre_recommendation(result)
    expect('Grunge  /  Grunge' in formatted,
           'formatted supported pair is missing')
    expect('Described as:' in formatted and 'Example artists:' in formatted,
           'formatted optional documentation is missing')


def test_ui_modules_import_without_starting_tk():
    from rock_band_general_helper_vkr import ui_metadata, ui_metadata_genre
    expect(hasattr(ui_metadata, 'MetadataView'), 'Metadata view is missing')
    expect(hasattr(ui_metadata_genre, 'MetadataGenreView'),
           'Genre view is missing')


def test_hidden_metadata_notebook_does_not_publish_startup_result():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_metadata import MetadataView

    root = tk.Tk()
    root.withdraw()
    results = []
    view = MetadataView(
        root, lambda status, result: results.append((status, result)))
    view.pack(fill=tk.BOTH, expand=True)
    try:
        root.update()
        view._tab_changed()
        expect(results == [],
               'hidden Metadata initialization populated shared Result')

        root.deiconify()
        root.update()
        results[:] = []
        view._tab_changed()
        expect(len(results) == 1 and results[0][0].startswith(
            'Genre converter:'),
            'visible Metadata tab did not publish its current selection')
    finally:
        root.destroy()


def main():
    tests = [
        test_documented_counts_and_families,
        test_integrity_validation,
        test_scoped_subgenres_and_unknowns,
        test_reverse_index_roundtrip,
        test_calibrated_mappings_and_redirects,
        test_plain_ascii_and_formatted_details,
        test_ui_modules_import_without_starting_tk,
        test_hidden_metadata_notebook_does_not_publish_startup_result,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Metadata Genre production tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
