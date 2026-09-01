"""Pure Tab Input parsing and Guitar/Bass guide logic.

Modern counterparts:
rock_band_general_helper_vkr/actions_guitar_guide.lua
rock_band_general_helper_vkr/actions_guitar.lua (gem assignment helpers)
lib/reaper_guitar_theory.lua (chord-width classification)

This module deliberately has no REAPER or Tk dependency.
Python 2.7 compatible.
"""

from __future__ import unicode_literals


# Indexed in standard ASCII-tab row order: high e, B, G, D, A, low E.
GUITAR_TAB_OPEN = (64, 59, 55, 50, 45, 40)
NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B')
GEM_LETTERS = ('G', 'R', 'Y', 'B', 'O')

POOLS = {
    1: ((0,), (1,), (2,), (3,), (4,)),
    2: ((0, 1), (0, 2), (1, 2), (0, 3), (1, 3),
        (2, 3), (1, 4), (2, 4), (3, 4)),
    3: ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3),
        (1, 2, 4), (1, 3, 4), (2, 3, 4)),
}

WIDTH_POOLS = {
    1: ((0, 1), (1, 2), (2, 3), (3, 4)),
    2: ((0, 2), (1, 3), (2, 4)),
    3: ((0, 3), (1, 4)),
    4: ((0, 4),),
}

DYAD_WIDTHS = {3: 1, 4: 1, 7: 2, 9: 2, 12: 3}
DYAD_NAMES = {
    3: 'Minor third',
    4: 'Major third',
    5: 'Perfect fourth',
    7: 'Perfect fifth (power chord)',
    9: 'Sixth dyad',
    12: 'Octave',
}


class TabEvent(object):
    def __init__(self, pitches, phrase_index, tab_text=''):
        self.pitches = list(pitches)
        self.phrase_index = int(phrase_index)
        self.tab_text = tab_text


def _fret(token):
    try:
        return int(token)
    except (TypeError, ValueError):
        return None


def pitch_name(pitch):
    pitch = max(0, min(127, int(round(pitch))))
    octave = pitch // 12 - 2
    return '%s%d' % (NOTE_NAMES[pitch % 12], octave)


def pitch_label(pitches):
    return '+'.join(pitch_name(pitch) for pitch in pitches)


def gem_label(gems):
    return '[' + '+'.join(GEM_LETTERS[gem] for gem in gems) + ']'


def parse_tab_horizontal(text):
    """Parse one low-E-to-high-e event per line."""
    events = []
    phrase_index = 1
    for line in (text or '').splitlines():
        trimmed = line.strip()
        if not trimmed:
            if events:
                phrase_index += 1
            continue
        pitches = []
        for position, token in enumerate(trimmed.split()[:6]):
            fret = _fret(token)
            if fret is not None:
                # Input token 0 is low E; tuning index 5 is low E.
                pitches.append(GUITAR_TAB_OPEN[5 - position] + fret)
        if pitches:
            events.append(TabEvent(pitches, phrase_index, trimmed))
    return events


def parse_tab_vertical(text):
    """Parse six high-e-to-low-E rows whose columns are events."""
    rows = []
    for line in (text or '').splitlines():
        trimmed = line.strip()
        if trimmed and len(rows) < 6:
            rows.append(trimmed.split())
    column_count = max([len(row) for row in rows] or [0])
    events = []
    phrase_index = 1
    for column in range(column_count):
        pitches = []
        for string_index, row in enumerate(rows):
            token = row[column] if column < len(row) else None
            fret = _fret(token)
            if fret is not None:
                pitches.append(GUITAR_TAB_OPEN[string_index] + fret)
        if pitches:
            events.append(TabEvent(pitches, phrase_index))
        elif events:
            phrase_index += 1
    return events


def parse_tab(text, vertical=False):
    if vertical:
        return parse_tab_vertical(text)
    return parse_tab_horizontal(text)


def reformat_vertical_tab(text, add_column=True):
    rows = [[] for unused in range(6)]
    row_index = 0
    for line in (text or '').splitlines():
        trimmed = line.strip()
        if trimmed:
            if row_index < 6:
                rows[row_index] = trimmed.split()
            row_index += 1
    width = max([len(row) for row in rows] or [0])
    for row in rows:
        row.extend(['-'] * (width - len(row)))
        if add_column:
            row.append('-')
    return '\n'.join(' '.join(row) for row in rows)


def add_empty_note(text, vertical=False):
    if vertical:
        if not (text or '').strip():
            return '-\n-\n-\n-\n-\n-'
        return reformat_vertical_tab(text, True)
    value = text or ''
    if value and not value.endswith('\n'):
        value += '\n'
    return value + '- - - - - -\n'


def _distinct_sorted(pitches):
    return sorted(set(pitches))


def _shape_key(pitches):
    return tuple(_distinct_sorted(pitches))


def _width_for_shape(pitches):
    distinct = _distinct_sorted(pitches)
    if len(distinct) < 2:
        return None
    if len(distinct) == 2:
        interval = distinct[1] - distinct[0]
        if interval > 12:
            return 4
        return DYAD_WIDTHS.get(interval)
    pitch_classes = sorted(set((pitch - distinct[0]) % 12
                               for pitch in distinct))
    if len(pitch_classes) == 2:
        return DYAD_WIDTHS.get(pitch_classes[1])
    return None


def _chord_quality(pitches):
    distinct = _distinct_sorted(pitches)
    if len(distinct) <= 1:
        return ''
    interval = distinct[1] - distinct[0] if len(distinct) == 2 else None
    if interval in DYAD_NAMES:
        return DYAD_NAMES[interval]
    pitch_classes = sorted(set((pitch - distinct[0]) % 12
                               for pitch in distinct))
    templates = {
        (0, 7): 'Power chord',
        (0, 4, 7): 'Major triad',
        (0, 3, 7): 'Minor triad',
        (0, 2, 7): 'Sus2',
        (0, 5, 7): 'Sus4',
        (0, 4, 7, 10): 'Dominant 7',
        (0, 3, 7, 10): 'Minor 7',
        (0, 4, 7, 11): 'Major 7',
        (0, 3, 6): 'Diminished',
        (0, 4, 8): 'Augmented',
    }
    return templates.get(tuple(pitch_classes), '')


def _assign_shape_gems(events):
    shapes = {}
    for event in events:
        key = _shape_key(event.pitches)
        if key not in shapes:
            shapes[key] = {
                'pitches': key,
                'maximum': max(key),
                'average': float(sum(key)) / len(key),
            }

    ordered = sorted(shapes, key=lambda key: (
        shapes[key]['maximum'], shapes[key]['average']))
    singles = [key for key in ordered if len(key) == 1]
    assigned = {}
    count = len(singles)
    for rank, key in enumerate(singles):
        gem = 0 if count == 1 else min(
            4, int(float(rank) * 4 / (count - 1) + 0.5))
        assigned[key] = (gem,)

    buckets = {}
    for key in ordered:
        if len(key) == 1:
            continue
        width = _width_for_shape(key)
        if width:
            bucket = ('width', width)
            pool = WIDTH_POOLS[width]
        else:
            size = min(len(key), 3)
            bucket = ('size', size)
            pool = POOLS[size]
        values = buckets.setdefault(bucket, [])
        assigned[key] = pool[len(values) % len(pool)]
        values.append(key)
    return shapes, assigned


def guitar_tab_guide(text, vertical=False):
    events = parse_tab(text, vertical)
    if not events:
        return ('Tab guide: no notes found',
                'No notes found. Use fret numbers for played strings and '
                'dashes or x for unplayed strings.')

    shapes, assigned = _assign_shape_gems(events)
    lines = []
    previous_phrase = None
    for event in events:
        key = _shape_key(event.pitches)
        if event.phrase_index != previous_phrase:
            phrase_shapes = []
            seen = set()
            for candidate in events:
                candidate_key = _shape_key(candidate.pitches)
                if (candidate.phrase_index == event.phrase_index and
                        candidate_key not in seen):
                    seen.add(candidate_key)
                    phrase_shapes.append(candidate_key)
            phrase_shapes.sort(key=lambda item: (
                shapes[item]['maximum'], shapes[item]['average']))
            header = '  '.join('%s -> %s' % (
                pitch_label(shapes[item]['pitches']),
                gem_label(assigned[item])) for item in phrase_shapes)
            if lines:
                lines.append('')
            lines.append('  *** Phrase start  ' + header)
            previous_phrase = event.phrase_index

        gems = assigned[key]
        source = event.tab_text or gem_label(gems)
        chord_type = ('single' if len(gems) == 1 else
                      ('%d-note chord' % len(gems)))
        detail = _chord_quality(key)
        suffix = '  [%s]' % detail if detail else ''
        lines.append('  %-15s  %s  %s -> %s%s' % (
            source, chord_type, pitch_label(event.pitches),
            gem_label(gems), suffix))

    return ('Tab guide: %d note event(s)' % len(events), '\n'.join(lines))

