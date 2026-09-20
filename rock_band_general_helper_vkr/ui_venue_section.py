"""Tk Venue > Section gen view.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import (
    PALETTE, ResponsiveLabel, make_labeled_spinbox,
)

from .actions_difficulty_shared import format_time
from .actions_venue_section import (
    KEYFRAME_ALIGN_LABELS, default_section_config, generate_venue_section,
    load_venue_sections, section_key,
)
from .ui_venue_themes import PACING_LABELS, SUBDIVISION_LABELS
from .venue import CAMERA_EVENTS, POSTPROC_EVENTS
from .venue_themes import LIGHTING_NAMES, get_section_preset, load_venue_themes


NONE = '(none)'
DIRECTED = tuple(name for name in CAMERA_EVENTS
                 if name.startswith('directed_'))


class VenueSectionView(ttk.Frame):
    def __init__(self, parent, controller, themes_dir=None):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        if themes_dir is None:
            themes_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'resources', 'themes')
        self.themes, self.theme_errors = load_venue_themes(themes_dir)
        self.themes_by_label = dict(
            (theme['label'], theme) for theme in self.themes)
        self.sections = []
        self.section_by_label = {}
        self.configs = {}
        self.loading = False
        self.active_section_key = None
        self.bounded_spins = []

        body = ttk.Frame(self, padding=12)
        body.pack(fill=tk.X)

        self.section_name = tk.StringVar()
        self.mode = tk.StringVar(); self.mode.set('Custom')
        self.theme_name = tk.StringVar()
        if self.themes:
            self.theme_name.set(self.themes[0]['label'])
        self.lighting = tk.StringVar(); self.lighting.set(NONE)
        self.postproc = tk.StringVar(); self.postproc.set(NONE)
        self.keyframe_rate = tk.IntVar(); self.keyframe_rate.set(2)
        self.light_blendin = tk.IntVar(); self.light_blendin.set(0)
        self.pp_blendin = tk.IntVar(); self.pp_blendin.set(0)
        self.directed = tk.StringVar(); self.directed.set(NONE)
        self.bonusfx = tk.BooleanVar()
        self.camera_pacing = tk.StringVar(); self.camera_pacing.set(PACING_LABELS[0])
        self.camera_jitter = tk.BooleanVar(); self.camera_jitter.set(True)
        self.camera_custom = tk.IntVar(); self.camera_custom.set(16)
        self.keyframe_align = tk.StringVar()
        self.keyframe_align.set(KEYFRAME_ALIGN_LABELS[0])
        self.subdivision = tk.StringVar(); self.subdivision.set(SUBDIVISION_LABELS[0])

        ResponsiveLabel(
            body, text=('Generate venue events for one recognized [prc_*] '
                        'section using custom settings or an .rbtheme.'),
            justify=tk.LEFT, wraplength=700).grid(
                row=0, column=0, columnspan=4, sticky='w')
        self._label(body, 1, 'Section')
        self.section_combo = ttk.Combobox(
            body, state='readonly', textvariable=self.section_name, width=38)
        self.section_combo.grid(row=1, column=1, columnspan=2, sticky='ew', pady=3)
        self.section_combo.bind('<<ComboboxSelected>>', self._section_changed)
        ttk.Button(body, text='Refresh', command=self._refresh).grid(
            row=1, column=3, sticky='w', padx=(8, 0))
        self.section_alert = ResponsiveLabel(
            body, foreground=PALETTE['error'], justify=tk.LEFT,
            wraplength=700)
        self.section_alert.grid(row=2, column=0, columnspan=4, sticky='w')

        self._label(body, 3, 'Mode')
        modes = ttk.Frame(body)
        modes.grid(row=3, column=1, columnspan=3, sticky='w', pady=3)
        ttk.Radiobutton(
            modes, text='Custom', value='Custom', variable=self.mode,
            command=self._sync_states).pack(side=tk.LEFT)
        ttk.Radiobutton(
            modes, text='Template', value='Template', variable=self.mode,
            command=self._sync_states).pack(side=tk.LEFT, padx=(12, 0))

        self.custom = ttk.LabelFrame(body, text='Custom section preset', padding=8)
        self.custom.grid(row=4, column=0, columnspan=4, sticky='ew', pady=(6, 4))
        self._label(self.custom, 0, 'Lighting')
        self.lighting_combo = self._combo(
            self.custom, 0, self.lighting, (NONE,) + LIGHTING_NAMES)
        self.lighting_combo.bind('<<ComboboxSelected>>', self._sync_states)
        self._label(self.custom, 3, 'Keyframe rate')
        self.rate_spin = self._spin(
            self.custom, 3, self.keyframe_rate, 1, 8, 'beats')
        self._label(self.custom, 4, 'Light blendin')
        self._spin(self.custom, 4, self.light_blendin, 0, 8, 'beats')
        self._label(self.custom, 5, 'Post-process')
        self._combo(self.custom, 5, self.postproc, (NONE,) + POSTPROC_EVENTS)
        self._label(self.custom, 6, 'PP blendin')
        self._spin(self.custom, 6, self.pp_blendin, 0, 8, 'beats')
        self._label(self.custom, 7, 'Directed cut')
        self._combo(self.custom, 7, self.directed, (NONE,) + DIRECTED)
        self._label(self.custom, 8, 'Bonus FX')
        ttk.Checkbutton(self.custom, variable=self.bonusfx).grid(
            row=8, column=1, sticky='w', pady=3)
        self.custom.columnconfigure(1, weight=1)

        self.template = ttk.LabelFrame(body, text='Theme template', padding=8)
        self.template.grid(row=5, column=0, columnspan=4, sticky='ew', pady=4)
        self._label(self.template, 0, 'Theme')
        self.theme_combo = self._combo(
            self.template, 0, self.theme_name,
            tuple(theme['label'] for theme in self.themes))
        self.theme_combo.bind('<<ComboboxSelected>>', self._sync_states)
        self.template_values = {}
        for row, (key, label) in enumerate((
                ('lighting', 'Lighting'), ('postproc', 'Post-process'),
                ('keyframe_rate', 'Keyframe rate'),
                ('light_blendin', 'Light blendin'),
                ('pp_blendin', 'PP blendin'),
                ('dircut', 'Directed cut'), ('bonusfx', 'Bonus FX')), 1):
            self._label(self.template, row, label)
            value = ResponsiveLabel(
                self.template, foreground=PALETTE['muted'], justify=tk.LEFT,
                wraplength=520, wrap_padding=130)
            value.grid(row=row, column=1, columnspan=2, sticky='w', pady=3)
            self.template_values[key] = value
        self.template.columnconfigure(1, weight=1)

        common = ttk.LabelFrame(body, text='Generation', padding=8)
        common.grid(row=6, column=0, columnspan=4, sticky='ew', pady=4)
        self._label(common, 0, 'Camera pacing')
        pacing = self._combo(common, 0, self.camera_pacing, PACING_LABELS)
        pacing.bind('<<ComboboxSelected>>', self._sync_states)
        self.jitter_check = ttk.Checkbutton(
            common, text='Include jitter', variable=self.camera_jitter)
        self.jitter_check.grid(row=0, column=2, sticky='w', padx=(8, 0))
        self._label(common, 1, 'Custom interval')
        self.custom_spin = self._spin(
            common, 1, self.camera_custom, 2, 128, '16th notes')
        self._label(common, 2, 'Keyframe align')
        self.align_combo = self._combo(
            common, 2, self.keyframe_align, KEYFRAME_ALIGN_LABELS)
        self.align_combo.bind('<<ComboboxSelected>>', self._sync_states)
        self._label(common, 3, 'Subdivision')
        self.subdivision_combo = self._combo(
            common, 3, self.subdivision, SUBDIVISION_LABELS)
        common.columnconfigure(1, weight=1)

        self.generate_button = ttk.Button(
            body, text='Generate section', command=self._generate)
        self.generate_button.grid(
            row=7, column=0, columnspan=4, sticky='w', pady=(10, 0))
        body.columnconfigure(1, weight=1)
        self._sync_states()

    def _label(self, parent, row, text):
        ttk.Label(parent, text=text).grid(
            row=row, column=0, sticky='w', padx=(0, 12), pady=3)

    def _combo(self, parent, row, variable, values):
        combo = ttk.Combobox(
            parent, state='readonly', width=34, textvariable=variable,
            values=values)
        combo.grid(row=row, column=1, sticky='ew', pady=3)
        return combo

    def _spin(self, parent, row, variable, low, high, suffix):
        field, spin = make_labeled_spinbox(
            parent, variable, low, high, suffix)
        field.grid(row=row, column=1, sticky='w', pady=3)
        self.bounded_spins.append((spin, variable, low, high))
        spin.bind('<FocusOut>', self._clamp_controls)
        return spin

    def _clamp_controls(self, unused_event=None):
        for unused_spin, variable, low, high in self.bounded_spins:
            try:
                value = int(variable.get())
            except (tk.TclError, TypeError, ValueError):
                value = low
            variable.set(max(low, min(high, value)))

    def _section_label(self, section):
        name = section['name'][:1].upper() + section['name'][1:]
        if section.get('num') is not None:
            name += ' %s' % section['num']
        return '%s  (%s - %s)' % (
            name, format_time(section['t_start']),
            format_time(section['t_end']))

    def _refresh(self):
        self._save_config()
        previous_label = self.section_name.get()
        try:
            self.sections, unused_guards = load_venue_sections(
                self.controller.host)
        except Exception as exc:
            self.sections = []
            self.section_alert.configure(text=str(exc))
        else:
            self.section_alert.configure(
                text=('' if self.sections else
                      'No [prc_*] sections were found on EVENTS.'))
        labels = tuple(self._section_label(section)
                       for section in self.sections)
        self.section_by_label = dict(zip(labels, self.sections))
        self.section_combo.configure(values=labels)
        self.section_name.set(
            previous_label if previous_label in self.section_by_label else
            labels[0] if labels else '')
        self._load_config()
        self._sync_states()

    def refresh_on_open(self):
        self._refresh()

    def _selected_section(self):
        return self.section_by_label.get(self.section_name.get())

    def _save_config(self, key=None):
        if self.loading:
            return
        self._clamp_controls()
        key = key or self.active_section_key
        if key is None:
            return
        self.configs[key] = {
            'lighting': '' if self.lighting.get() == NONE else self.lighting.get(),
            'postproc': '' if self.postproc.get() == NONE else self.postproc.get(),
            'keyframe_rate': self.keyframe_rate.get(),
            'light_blendin': self.light_blendin.get(),
            'pp_blendin': self.pp_blendin.get(),
            'dircut': '' if self.directed.get() == NONE else self.directed.get(),
            'bonusfx': self.bonusfx.get(),
        }

    def _load_config(self):
        section = self._selected_section()
        config = (self.configs.get(section_key(section), default_section_config())
                  if section is not None else default_section_config())
        self.loading = True
        self.lighting.set(config['lighting'] or NONE)
        self.postproc.set(config['postproc'] or NONE)
        self.keyframe_rate.set(config['keyframe_rate'])
        self.light_blendin.set(config['light_blendin'])
        self.pp_blendin.set(config['pp_blendin'])
        self.directed.set(config['dircut'] or NONE)
        self.bonusfx.set(config['bonusfx'])
        self.active_section_key = (
            section_key(section) if section is not None else None)
        self.loading = False

    def _section_changed(self, unused_event=None):
        self._save_config(self.active_section_key)
        self._load_config()
        self._sync_states()

    def _sync_states(self, unused_event=None):
        template_mode = self.mode.get() == 'Template'
        if template_mode:
            self.custom.grid_remove()
            self.template.grid()
        else:
            self.template.grid_remove()
            self.custom.grid()
        manual = self.lighting.get() in (
            'verse', 'chorus', 'manual_cool', 'manual_warm', 'dischord', 'stomp')
        align_enabled = template_mode or manual
        self.align_combo.configure(
            state=('readonly' if align_enabled else tk.DISABLED))
        self.rate_spin.configure(state=(tk.NORMAL if manual else tk.DISABLED))
        instrument = (align_enabled and
                      self.keyframe_align.get() in KEYFRAME_ALIGN_LABELS[3:])
        self.subdivision_combo.configure(
            state=('readonly' if instrument else tk.DISABLED))
        custom = self.camera_pacing.get() == PACING_LABELS[6]
        self.custom_spin.configure(state=(tk.NORMAL if custom else tk.DISABLED))
        phrase = self.camera_pacing.get() == PACING_LABELS[7]
        self.jitter_check.configure(state=(tk.DISABLED if phrase else tk.NORMAL))
        no_theme = template_mode and not self.themes
        self.generate_button.configure(
            state=(tk.DISABLED if not self.sections or no_theme else tk.NORMAL))
        self._update_template_summary()

    def _update_template_summary(self):
        values = dict((key, '-') for key in self.template_values)
        if not self.themes:
            values['lighting'] = 'No .rbtheme files found; use Custom mode.'
            self._set_template_values(values)
            return
        theme = self.themes_by_label.get(self.theme_name.get())
        section = self._selected_section()
        preset = (get_section_preset(
            theme, section['name'], section.get('num'))
            if theme is not None and section is not None else None)
        if not preset:
            values['lighting'] = 'No matching or default section preset.'
            self._set_template_values(values)
            return
        values.update({
            'lighting': ', '.join(
                preset.get('allowed_lightpresets', ())) or '-',
            'postproc': ', '.join(
                preset.get('allowed_postprocs', ())) or '-',
            'keyframe_rate': preset.get('keyframe_rate', '-'),
            'light_blendin': preset.get('lightpreset_blendin', '-'),
            'pp_blendin': preset.get('postproc_blendin', '-'),
            'dircut': preset.get('dircut_at_start', '-'),
            'bonusfx': 'yes' if preset.get('bonusfx_at_start') else 'no',
        })
        self._set_template_values(values)

    def _set_template_values(self, values):
        for key, widget in self.template_values.items():
            widget.configure(text=str(values.get(key, '-')))

    def _generate(self):
        self._save_config()
        section = self._selected_section()
        if section is None:
            self.controller.show_result(
                'Select a Venue section first.',
                'Press Refresh and choose a detected EVENTS section.')
            return
        theme = (self.themes_by_label.get(self.theme_name.get())
                 if self.mode.get() == 'Template' else None)
        config = self.configs.get(section_key(section), default_section_config())
        options = {
            'camera_pacing': PACING_LABELS.index(self.camera_pacing.get()),
            'camera_jitter': self.camera_jitter.get(),
            'camera_custom': self.camera_custom.get(),
            'keyframe_align': KEYFRAME_ALIGN_LABELS.index(
                self.keyframe_align.get()),
            'keyframe_subdivision': SUBDIVISION_LABELS.index(
                self.subdivision.get()),
        }
        try:
            status, report = generate_venue_section(
                self.controller.host, section, config, options, theme)
            self.controller.show_result(status, report)
        except Exception as exc:
            self.controller.show_result(
                'Venue section generation could not complete',
                'The guarded generator stopped. No unverified project change '
                'was accepted.\n\n%s' % exc)
