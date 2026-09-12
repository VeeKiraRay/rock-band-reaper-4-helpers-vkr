"""Venue .rbtheme parser and preset helpers.

Modern counterpart: rock_band_general_helper_vkr/venue_themes.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os
import re

from .venue import POSTPROC_EVENTS


LIGHTING_NAMES = (
    'verse', 'chorus', 'manual_cool', 'manual_warm', 'dischord',
    'stomp', 'loop_cool', 'loop_warm', 'harmony', 'frenzy',
    'silhouettes', 'silhouettes_spot', 'searchlights', 'sweep',
    'strobe_slow', 'strobe_fast', 'blackout_slow', 'blackout_fast',
    'blackout_spot', 'flare_slow', 'flare_fast', 'bre',
)
LIGHTING_VALID = frozenset(LIGHTING_NAMES)
POSTPROC_VALID = frozenset(POSTPROC_EVENTS)
CAMERA_PACING = {
    'crazy': 4, 'fast': 8, 'medium': 16, 'slow': 24, 'minimal': 32,
}


class VenueThemeError(Exception):
    pass


def theme_display_label(stem):
    return re.sub(r'(?<!^)([A-Z])', r' \1', stem)


def _tokens(content):
    content = re.sub(r';[^\r\n]*', '', content)
    return re.findall(r'\(|\)|[^\s()]+', content)


def _parse_one(tokens, position):
    if position >= len(tokens):
        raise VenueThemeError('Unexpected end of theme file.')
    token = tokens[position]
    if token == ')':
        raise VenueThemeError('Unexpected closing parenthesis.')
    if token != '(':
        return token, position + 1
    result = []
    position += 1
    while position < len(tokens) and tokens[position] != ')':
        value, position = _parse_one(tokens, position)
        result.append(value)
    if position >= len(tokens):
        raise VenueThemeError('Unclosed parenthesis in theme file.')
    return result, position + 1


def parse_theme_nodes(content):
    tokens = _tokens(content)
    nodes = []
    position = 0
    while position < len(tokens):
        node, position = _parse_one(tokens, position)
        nodes.append(node)
    return nodes


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _section_preset(children):
    preset = {}
    for child in children:
        if not isinstance(child, list) or not child:
            continue
        key = child[0]
        values = child[1:]
        if key == 'allowed_lightpresets':
            preset[key] = [value for value in values
                           if value in LIGHTING_VALID]
        elif key == 'allowed_postprocs':
            preset[key] = [value for value in values
                           if value in POSTPROC_VALID]
        elif key in ('keyframe_rate', 'lightpreset_blendin',
                     'postproc_blendin') and values:
            value = _number(values[0])
            if value is not None:
                preset[key] = value
        elif key in ('camera_pacing', 'dircut_at_start') and values:
            preset[key] = values[0]
        elif key == 'bonusfx_at_start':
            preset[key] = True
    return preset


def parse_theme(content, stem='Theme'):
    theme = {
        'stem': stem,
        'label': theme_display_label(stem),
        'camera_pacing': 'medium',
        'section_presets': {},
    }
    for node in parse_theme_nodes(content):
        if not isinstance(node, list) or not node:
            continue
        if node[0] == 'camera_pacing' and len(node) > 1:
            theme['camera_pacing'] = node[1]
        elif node[0] == 'section_presets':
            for section in node[1:]:
                if isinstance(section, list) and section:
                    theme['section_presets'][section[0]] = (
                        _section_preset(section[1:]))
    return theme


def load_venue_themes(themes_dir):
    themes = []
    errors = []
    if not os.path.isdir(themes_dir):
        return themes, ['Theme directory was not found: %s' % themes_dir]
    for filename in sorted(os.listdir(themes_dir)):
        stem, extension = os.path.splitext(filename)
        if extension.lower() != '.rbtheme':
            continue
        path = os.path.join(themes_dir, filename)
        try:
            with open(path, 'rb') as handle:
                content = handle.read().decode('utf-8')
            themes.append(parse_theme(content, stem))
        except Exception as exc:
            errors.append('%s: %s' % (filename, exc))
    themes.sort(key=lambda theme: theme['label'].lower())
    return themes, errors


def get_section_preset(theme, section_name, section_number=None):
    presets = theme.get('section_presets', {})
    if section_number is not None:
        variants = []
        index = 1
        while section_name + str(index) in presets:
            variants.append(presets[section_name + str(index)])
            index += 1
        if variants:
            return variants[(int(section_number) - 1) % len(variants)]
    if section_name in presets:
        return presets[section_name]
    return presets.get('default')


def get_theme_camera_interval(camera_pacing, bpm):
    base = CAMERA_PACING.get(camera_pacing, CAMERA_PACING['medium'])
    return int(base * 1.5 + 0.5) if float(bpm) >= 150.0 else base


def build_lighting_pool(preset):
    if not preset:
        return []
    return ['[lighting (%s)]' % name
            for name in preset.get('allowed_lightpresets', ())
            if name in LIGHTING_VALID]


def build_postproc_pool(preset):
    if not preset:
        return []
    return ['[%s]' % name
            for name in preset.get('allowed_postprocs', ())
            if name in POSTPROC_VALID]
