"""EVENTS-track vocabulary for Venue > Events.

Modern counterpart:
rock_band_general_helper_vkr/section_events.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals


def _bases(values):
    return tuple({'base': base, 'caps': caps} for base, caps in values)


SECTION_EVENT_GROUPS = (
    {'key': 'intro', 'label': 'Intro', 'kind': 'prc', 'bases': _bases((
        ('intro', 'e'), ('intro_slow', 'd.'), ('intro_fast', 'd'),
        ('intro_heavy', 'd'), ('quiet_intro', 'd'), ('noise_intro', 'd'),
        ('intro_hook', 'd'), ('intro_riff', 'd'), ('fade_in', 'd'),
        ('drum_intro', 'd'), ('bass_intro', 'd'), ('vocal_intro', 'd'),
        ('gtr_intro', 'e'), ('violin_intro', 'd'), ('strings_intro', 'd'),
        ('orch_intro', 'd'), ('horn_intro', 'd'), ('harmonica_intro', 'd'),
        ('organ_intro', 'd'), ('piano_intro', 'd'), ('keyboard_intro', 'd'),
        ('dj_intro', '.'), ('drums_enter', '.'), ('bass_enters', '.'),
        ('gtr_enters', '.'), ('rhy_enters', '.'), ('band_enters', '.'),
    ))},
    {'key': 'structure', 'label': 'Structure', 'kind': 'prc', 'bases': _bases((
        ('verse', 'ffffdddddd'), ('alt_verse', 'd'), ('quiet_verse', 'd'),
        ('preverse', 'dddddd'), ('postverse', 'dddddd'),
        ('chorus', 'dddddddddd'), ('alt_chorus', 'd'),
        ('chorus_break', 'd'), ('prechorus', 'dddddd'),
        ('postchorus', 'dddddd'), ('bridge', 'dddddddddd'),
        ('breakdown_chorus', 'd'),
    ))},
    {'key': 'solo', 'label': 'Solo', 'kind': 'prc', 'bases': _bases((
        ('gtr_solo', 'snnnnnnnnn'), ('slide_solo', 'ddddd'),
        ('drum_solo', 'ddddd'), ('perc_solo', 'ddddd'),
        ('bass_solo', 'ddddd'), ('organ_solo', 'ddddd'),
        ('piano_solo', 'ddddd'), ('keyboard_solo', 'ddddd'),
        ('synth_solo', 'ddddd'), ('harmonica_solo', 'ddddd'),
        ('sax_solo', 'ddddd'), ('horn_solo', 'ddddd'),
        ('flute_solo', 'ddddd'), ('noise_solo', 'ddddd'),
        ('dj_solo', 'ddddd'),
    ))},
    {'key': 'break', 'label': 'Break', 'kind': 'prc', 'bases': _bases((
        ('break', 'ddddd'), ('gtr_break', 'ddddd'),
        ('bass_break', 'ddddd'), ('drum_break', 'ddddd'),
        ('organ_break', 'ddddd'), ('synth_break', 'ddddd'),
        ('piano_break', 'ddddd'), ('keyboard_break', 'ddddd'),
        ('horn_break', '.'), ('perc_break', '.'), ('dj_break', '.'),
        ('breakdown', 'ddddd'),
    ))},
    {'key': 'energy', 'label': 'Tempo / Energy', 'kind': 'prc',
     'bases': _bases((
         ('slow_part', 'ddddd'), ('fast_part', 'ddddd'),
         ('quiet_part', 'ddddd'), ('loud_part', 'ddddd'),
         ('heavy_part', 'ddddd'), ('spacey', '.'),
         ('trippy_part', 'ddddd'), ('speedup', '.'),
         ('tension', 'ddddd'), ('build_up', 'ddddd'),
     ))},
    {'key': 'interlude', 'label': 'Interlude / Jam', 'kind': 'prc',
     'bases': _bases((
         ('interlude', 'ddddd'), ('soundscape', 'ddddd'),
         ('jam', 'ddddd'), ('space_jam', 'ddddd'), ('vamp', 'ddddd'),
     ))},
    {'key': 'outro', 'label': 'Outro / Ending', 'kind': 'prc',
     'bases': _bases((
         ('outro', 'ddddd'), ('outro_solo', 'd'),
         ('outro_chorus', 'd'), ('ending', 'd'), ('fade_out', 'd'),
     ))},
    {'key': 'misc', 'label': 'Misc', 'kind': 'prc', 'bases': _bases((
        ('main_riff', 'ffffdddddd'), ('bre', '.'), ('melody', 'ddddd'),
        ('lo_melody', 'ddddd'), ('hi_melody', 'ddddd'),
        ('intro_verse', 'd'), ('intro_chorus', 'd'),
    ))},
    {'key': 'generic', 'label': 'Generic', 'kind': 'generic',
     'bases': _bases(tuple((letter, None) for letter in 'abcdefghijk'))},
    {'key': 'crowd', 'label': 'Crowd', 'kind': 'plain', 'events': (
        '[crowd_realtime]', '[crowd_mellow]', '[crowd_normal]',
        '[crowd_intense]', '[crowd_noclap]', '[crowd_clap]',
        '[crowd_fists_on]', '[crowd_fists_off]', '[crowd_horns_on]',
        '[crowd_horns_off]', '[crowd_lighters_on]', '[crowd_lighters_off]',
    )},
    {'key': 'global', 'label': 'Global', 'kind': 'plain', 'events': (
        '[music_start]', '[music_end]', '[end]', '[coda]',
    )},
)

SECTION_EVENT_BASE = {}
for _group in SECTION_EVENT_GROUPS:
    for _base in _group.get('bases', ()):
        SECTION_EVENT_BASE[_base['base']] = _base
