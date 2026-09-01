"""Genre converter lookup and integrity validation.

Modern counterpart:
rock_band_general_helper_vkr/metadata_genres_lookup.lua

Pure module with no REAPER or Tk dependency. Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .metadata_genres import RB3_GENRE_ORDER, RB3_GENRES
from .metadata_genres_ext import (
    EXTENDED_GENRES,
    GENRE_FAMILIES,
    GENRE_FAMILY_ORDER,
)


_family_cache = None
_by_key = None
_reverse = None


def _build_caches():
    global _family_cache, _by_key
    if _family_cache is not None:
        return
    _family_cache = dict((key, []) for key in GENRE_FAMILY_ORDER)
    _by_key = {}
    for entry in EXTENDED_GENRES:
        _by_key[entry['key']] = entry
        bucket = _family_cache.get(entry['family'])
        if bucket is not None:
            bucket.append(entry)


def genres_in_family(family_key):
    _build_caches()
    return _family_cache.get(family_key, [])


def extended_genre_by_key(key):
    _build_caches()
    return _by_key.get(key)


def rb3_subgenre(genre_key, subgenre_key):
    genre = RB3_GENRES.get(genre_key)
    if not genre:
        return None
    for subgenre in genre['subgenres']:
        if subgenre['key'] == subgenre_key:
            return subgenre
    return None


def resolve_extended_genre(key):
    entry = extended_genre_by_key(key)
    if not entry:
        return None
    result = {
        'key': entry['key'],
        'label': entry['label'],
        'family': entry['family'],
        'family_label': GENRE_FAMILIES.get(entry['family']),
        'candidates': [],
        'see_also': [],
    }
    for redirect in entry.get('see_also', []):
        target = extended_genre_by_key(redirect.get('key'))
        if target:
            result['see_also'].append({
                'key': redirect['key'],
                'label': target['label'],
                'when': redirect.get('when', ''),
            })
    for candidate in entry.get('candidates', []):
        genre = RB3_GENRES.get(candidate.get('genre'))
        subgenre = rb3_subgenre(
            candidate.get('genre'), candidate.get('subgenre'))
        if genre and subgenre:
            result['candidates'].append({
                'genre_key': candidate['genre'],
                'genre_label': genre['label'],
                'sub_key': candidate['subgenre'],
                'sub_label': subgenre['label'],
                'why': candidate['why'],
                'sub': subgenre,
            })
    return result


def build_reverse_genre_index():
    global _reverse
    if _reverse is not None:
        return _reverse
    _reverse = {}
    for entry in EXTENDED_GENRES:
        for index, candidate in enumerate(entry.get('candidates', [])):
            pair = '%s/%s' % (
                candidate['genre'], candidate['subgenre'])
            record = _reverse.setdefault(pair, {'first': [], 'lower': []})
            bucket = record['first'] if index == 0 else record['lower']
            bucket.append({
                'key': entry['key'],
                'label': entry['label'],
                'family': entry['family'],
                'why': candidate['why'],
            })
    return _reverse


def extended_genres_for_pair(genre_key, subgenre_key):
    record = build_reverse_genre_index().get(
        '%s/%s' % (genre_key, subgenre_key))
    if not record:
        return [], []
    return record['first'], record['lower']


def format_genre_recommendation(result):
    """Build the plain-text recommendation shown by the Tk view."""
    if not result or not result['candidates']:
        return 'No supported genre is mapped to this entry yet.'
    lines = []
    if len(result['candidates']) > 1:
        lines.extend([
            '%s maps more than one way. The first is the usual pick; the '
            'others reflect genuine catalogue splits.' % result['label'],
            '',
        ])
    for index, candidate in enumerate(result['candidates']):
        lines.append('%d.  %s  /  %s' % (
            index + 1,
            candidate['genre_label'],
            candidate['sub_label']))
        lines.append('    ' + candidate['why'])
        subgenre = candidate['sub']
        optional = (
            ('blurb', 'Described as'),
            ('elements', 'Typical elements'),
            ('artists', 'Example artists'),
            ('albums', 'Example albums'),
        )
        for field, label in optional:
            if subgenre.get(field):
                lines.append('    %s: %s' % (label, subgenre[field]))
        if index + 1 < len(result['candidates']):
            lines.append('')
    if result['see_also']:
        lines.extend(['', '-' * 60])
        for redirect in result['see_also']:
            lines.append('If %s, see "%s" instead.' % (
                redirect['when'], redirect['label']))
    return '\n'.join(lines)


def validate_genre_tables():
    """Return human-readable integrity problems; an empty list is valid."""
    problems = []
    ordered = set()
    for genre_key in RB3_GENRE_ORDER:
        if genre_key in ordered:
            problems.append('RB3_GENRE_ORDER lists %s twice' % genre_key)
        ordered.add(genre_key)
        if genre_key not in RB3_GENRES:
            problems.append('ordered genre is missing: %s' % genre_key)
    for genre_key, genre in RB3_GENRES.items():
        if genre_key not in ordered:
            problems.append('unordered supported genre: %s' % genre_key)
        if not genre.get('label'):
            problems.append('%s has no label' % genre_key)
        if not genre.get('subgenres'):
            problems.append('%s has no subgenres' % genre_key)
        seen_subgenres = set()
        for subgenre in genre.get('subgenres', []):
            key = subgenre.get('key')
            if key in seen_subgenres:
                problems.append('%s lists %s twice' % (genre_key, key))
            seen_subgenres.add(key)
            if not subgenre.get('label'):
                problems.append('%s/%s has no label' % (genre_key, key))

    family_order = set(GENRE_FAMILY_ORDER)
    if family_order != set(GENRE_FAMILIES):
        problems.append('genre family order and labels differ')
    family_usage = set()
    seen_keys = set()
    seen_labels = set()
    reached_genres = set()
    for entry in EXTENDED_GENRES:
        key = entry.get('key')
        label = entry.get('label')
        if key in seen_keys:
            problems.append('duplicate extended key: %s' % key)
        if label in seen_labels:
            problems.append('duplicate extended label: %s' % label)
        seen_keys.add(key)
        seen_labels.add(label)
        family = entry.get('family')
        family_usage.add(family)
        if family not in family_order:
            problems.append('%s has unknown family %s' % (key, family))
        candidates = entry.get('candidates', [])
        if not 1 <= len(candidates) <= 3:
            problems.append('%s has %d candidates' % (key, len(candidates)))
        seen_pairs = set()
        for candidate in candidates:
            pair = (candidate.get('genre'), candidate.get('subgenre'))
            if pair in seen_pairs:
                problems.append('%s repeats %s/%s' % (
                    key, pair[0], pair[1]))
            seen_pairs.add(pair)
            reached_genres.add(pair[0])
            if not rb3_subgenre(pair[0], pair[1]):
                problems.append('%s points at unknown %s/%s' % (
                    key, pair[0], pair[1]))
            if len(candidate.get('why', '')) < 20:
                problems.append('%s has no usable reason' % key)

    for family in GENRE_FAMILY_ORDER:
        if family not in family_usage:
            problems.append('family %s has no entries' % family)
    for genre_key in RB3_GENRE_ORDER:
        if genre_key not in reached_genres:
            problems.append('no extended genre maps to %s' % genre_key)

    for entry in EXTENDED_GENRES:
        for redirect in entry.get('see_also', []):
            if redirect.get('key') not in seen_keys:
                problems.append('%s redirects to unknown %s' % (
                    entry['key'], redirect.get('key')))
            if redirect.get('key') == entry['key']:
                problems.append('%s redirects to itself' % entry['key'])
            if len(redirect.get('when', '')) < 20:
                problems.append('%s has no usable redirect condition' %
                                entry['key'])
    return problems

