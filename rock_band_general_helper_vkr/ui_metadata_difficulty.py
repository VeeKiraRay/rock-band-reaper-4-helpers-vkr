"""Tk rendering for Metadata > Difficulty.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import datetime

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.tk_common import PALETTE, Tooltip
from .metadata_difficulty import (
    CHART_SPECS,
    analyse_project,
    card_summary,
    current_project_info,
    project_identity_changed,
)
from .difficulty_explain import dot_count
from .difficulty_report import format_suggestion_report


DIFFICULTY_INTRODUCTION = (
    'Estimates a rank and tier for each finished Expert chart in this '
    'project, from measurements of the charts themselves. Advisory only, '
    'treat with a grain of salt. The whole chart is scored - a time '
    'selection does not change the result.')


class MetadataDifficultyView(ttk.Frame):
    def __init__(self, parent, show_result, analyser=None,
                 project_provider=None):
        ttk.Frame.__init__(self, parent, padding=12)
        self.show_result = show_result
        self.analyser = analyser or analyse_project
        self.project_provider = project_provider or current_project_info
        self.project = (self._read_project() or
                        {'identity': None, 'path': '',
                         'name': 'Unknown project'})
        self.last_results = None
        self.last_report = None
        self.refreshed_at = None
        self.empty_reason = 'No suggestions yet.'
        self.results_by_key = {}
        self.show_observations_var = tk.BooleanVar()
        self.show_observations_var.set(False)
        self.status_vars = {}
        self.status_labels = {}
        self.rank_vars = {}
        self.summary_vars = {}
        self.detail_vars = {}
        self.content_frames = {}
        self.summary_labels = {}
        self.detail_labels = {}
        self.dot_canvases = {}
        self.ruler_canvases = {}
        self.ruler_left_vars = {}
        self.ruler_right_vars = {}
        self.ruler_data = {}
        self.layout_after_id = None

        heading = ttk.Frame(self)
        heading.pack(fill=tk.X)
        ttk.Label(
            heading,
            text='Suggested difficulty',
            font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        refresh = ttk.Button(
            heading, text='Refresh suggestions', command=self.refresh)
        refresh.pack(side=tk.RIGHT)
        observations = ttk.Checkbutton(
            heading, text='Show observations',
            variable=self.show_observations_var,
            command=self._observations_changed)
        observations.pack(side=tk.RIGHT, padx=(0, 10))
        Tooltip(
            observations,
            'Show up to three plain-language observations about what makes '
            'each chart unusual. Warnings remain visible either way.')
        Tooltip(
            refresh,
            'Read and score the six chart tracks. This does not modify the '
            'project or create an undo point.')

        self.intro_label = ttk.Label(
            self,
            text=DIFFICULTY_INTRODUCTION,
            justify=tk.LEFT,
            wraplength=680)
        self.intro_label.pack(anchor='w', fill=tk.X, pady=(8, 4))

        self.project_var = tk.StringVar()
        self.project_var.set('Project: %s' % self.project['name'])
        ttk.Label(
            self, textvariable=self.project_var,
            foreground=PALETTE['muted']).pack(anchor='w', pady=(0, 10))

        cards = ttk.Frame(self)
        cards.pack(fill=tk.X)
        for column in range(2):
            # ``uniform`` matters in addition to equal weights: without it,
            # Tk adds each column's requested width before sharing surplus,
            # so one long observation can make that side permanently wider.
            cards.columnconfigure(
                column, weight=1, uniform='difficulty_card_column')
        for row in range(3):
            cards.rowconfigure(row, weight=1)

        style = ttk.Style()
        style.configure(
            'Difficulty.TLabelframe.Label',
            font=('TkDefaultFont', 9, 'bold'))

        for index, spec in enumerate(CHART_SPECS):
            card = ttk.LabelFrame(
                cards, text=spec['label'].upper(), padding=9,
                style='Difficulty.TLabelframe')
            card.grid(
                row=index // 2, column=index % 2,
                sticky='nsew', padx=4, pady=4)
            status_var = tk.StringVar()
            status_var.set('Not analysed')
            rank_var = tk.StringVar()
            rank_var.set('')
            summary_var = tk.StringVar()
            summary_var.set(spec['track'])
            detail_var = tk.StringVar()
            detail_var.set('Press Refresh suggestions to score this chart.')
            status_label = ttk.Label(
                card, textvariable=status_var,
                font=('TkDefaultFont', 9, 'bold'))
            status_label.pack(anchor='w')

            content = ttk.Frame(card)
            content.pack(anchor='w', fill=tk.BOTH, expand=True)
            rank_row = ttk.Frame(content)
            rank_row.pack(anchor='w', fill=tk.X, pady=(4, 0))
            dot_canvas = tk.Canvas(
                rank_row, width=92, height=18, background='#303030',
                highlightthickness=0)
            dot_canvas.pack(side=tk.LEFT)
            ttk.Label(
                rank_row, textvariable=rank_var,
                font=('TkDefaultFont', 9, 'bold')).pack(
                    side=tk.LEFT, padx=(7, 0))
            summary_label = ttk.Label(
                content, textvariable=summary_var,
                justify=tk.LEFT, wraplength=300)
            summary_label.pack(anchor='w', fill=tk.X, pady=(3, 0))
            ruler_row = ttk.Frame(content)
            ruler_row.pack(anchor='w', fill=tk.X)
            ruler_labels = ttk.Frame(ruler_row)
            ruler_labels.pack(fill=tk.X)
            ruler_labels.columnconfigure(0, weight=1)
            ruler_labels.columnconfigure(1, weight=1)
            ruler_left = tk.StringVar()
            ruler_right = tk.StringVar()
            left_label = ttk.Label(
                ruler_labels, textvariable=ruler_left, anchor='w')
            left_label.grid(row=0, column=0, sticky='w')
            right_label = ttk.Label(
                ruler_labels, textvariable=ruler_right, anchor='e')
            right_label.grid(row=0, column=1, sticky='e')
            ruler_canvas = tk.Canvas(
                ruler_row, width=100, height=24, background='#303030',
                highlightthickness=0)
            ruler_canvas.pack(fill=tk.X, expand=True, pady=(2, 0))
            ruler_canvas.bind('<Configure>', self._ruler_resized)
            detail_label = ttk.Label(
                content, textvariable=detail_var,
                justify=tk.LEFT, wraplength=300)
            detail_label.pack(anchor='w', fill=tk.X, pady=(4, 0))
            self.status_vars[spec['key']] = status_var
            self.status_labels[spec['key']] = status_label
            self.rank_vars[spec['key']] = rank_var
            self.summary_vars[spec['key']] = summary_var
            self.detail_vars[spec['key']] = detail_var
            self.content_frames[spec['key']] = content
            self.summary_labels[spec['key']] = summary_label
            self.detail_labels[spec['key']] = detail_label
            self.dot_canvases[spec['key']] = dot_canvas
            self.ruler_canvases[spec['key']] = ruler_canvas
            self.ruler_left_vars[spec['key']] = ruler_left
            self.ruler_right_vars[spec['key']] = ruler_right
            content.pack_forget()

        self._clear_scales()
        self.bind('<Configure>', self._view_resized)
        self.after(1000, self._poll_project)

    def refresh_current(self):
        self._check_project_change(show=True)
        if self.last_report:
            self.show_result(
                'Difficulty suggestions: %s at %s' %
                (self.project['name'], self.refreshed_at),
                self.last_report)
        else:
            self._show_empty_result()

    def refresh(self):
        self.project = self._read_project() or self.project
        self.project_var.set('Project: %s' % self.project['name'])
        try:
            results = self.analyser()
        except Exception as exc:
            self.show_result(
                'Difficulty inventory could not run',
                'Metadata Difficulty could not read the project.\n\n%s' % exc)
            return

        self.last_results = results
        self.results_by_key = dict(
            (result['key'], result) for result in results)
        self.empty_reason = 'No suggestions yet.'
        self.refreshed_at = datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S')
        self.last_report = format_suggestion_report(
            results, self.project['name'], self.refreshed_at)
        for result in results:
            self.status_vars[result['key']].set(result['status'])
            self.summary_vars[result['key']].set(card_summary(result))
            self._render_card(result)

        found = sum(1 for result in results if result['present'])
        readable = sum(1 for result in results
                       if result['parsed_items'] and not result['failed_items'])
        self.show_result(
            'Difficulty suggestions: %d/6 tracks found, %d cleanly read' %
            (found, readable),
            self.last_report)

    def _read_project(self):
        try:
            info = self.project_provider()
            if info and 'identity' in info:
                return info
        except Exception:
            pass
        return None

    def _poll_project(self):
        try:
            self._check_project_change(show=bool(self.winfo_ismapped()))
            self.after(1000, self._poll_project)
        except tk.TclError:
            pass

    def _check_project_change(self, show=False):
        current = self._read_project()
        if current is None:
            return False
        changed = project_identity_changed(self.project, current)
        self.project = current
        self.project_var.set('Project: %s' % current['name'])
        if changed:
            self._clear_results(
                'Project changed; previous suggestions were cleared.')
            if show:
                self._show_empty_result()
        return changed

    def _clear_results(self, reason=None):
        self.last_results = None
        self.last_report = None
        self.refreshed_at = None
        self.results_by_key = {}
        self.empty_reason = reason or 'No suggestions yet.'
        for spec in CHART_SPECS:
            key = spec['key']
            self.status_vars[key].set('Not analysed')
            self._show_status(key)
            self.rank_vars[key].set('')
            self.summary_vars[key].set(spec['track'])
            self.detail_vars[key].set(
                'Press Refresh suggestions to score this chart.')
            self.content_frames[key].pack_forget()
        self._clear_scales()

    def _show_empty_result(self, reason=None):
        message = reason or self.empty_reason
        self.show_result(
            'Difficulty suggestions: waiting for refresh',
            '%s\n\nProject: %s\nPress Refresh suggestions to score this project.' %
            (message, self.project['name']))

    def _clear_scales(self):
        for key in self.dot_canvases:
            self._draw_dots(self.dot_canvases[key], None)
            self.ruler_canvases[key].delete('all')
            self.ruler_left_vars[key].set('')
            self.ruler_right_vars[key].set('')

    def _render_card(self, result):
        key = result['key']
        suggestion = result.get('suggestion')
        if result['status'] == 'Muted':
            self.status_vars[key].set('Muted')
            self._show_status(key)
            self.content_frames[key].pack_forget()
            return
        self._show_card_content(key)
        if not suggestion:
            self._show_status(key)
            self.rank_vars[key].set('')
            self._draw_dots(self.dot_canvases[key], None)
            self.ruler_canvases[key].delete('all')
            self.ruler_left_vars[key].set('')
            self.ruler_right_vars[key].set('')
            self.detail_vars[key].set(
                result['errors'][0] if result.get('errors') else result['status'])
            return
        self.status_vars[key].set('')
        self.status_labels[key].pack_forget()
        self.rank_vars[key].set('Rank %d - %s' % (
            suggestion['rank_shown'], suggestion['tier_name']))
        self._draw_dots(self.dot_canvases[key], suggestion['tier'])
        self._draw_ruler(key, suggestion.get('ruler'))
        self._update_card_details(result)

    @staticmethod
    def _draw_dots(canvas, tier):
        canvas.delete('all')
        filled = dot_count(tier)
        maximum = tier == 6
        for index in range(5):
            x = 11 + index * 17
            colour = ('#d94444' if maximum else
                      '#ffffff' if index < filled else '#777777')
            canvas.create_oval(x - 5, 4, x + 5, 14,
                               fill=colour, outline=colour)

    def _draw_ruler(self, key, ruler):
        canvas = self.ruler_canvases[key]
        self.ruler_data[key] = ruler
        canvas.delete('all')
        if not ruler:
            self.ruler_left_vars[key].set('')
            self.ruler_right_vars[key].set('')
            return
        self.ruler_left_vars[key].set(ruler['lo_label'])
        self.ruler_right_vars[key].set(ruler['hi_label'])
        width = max(30, canvas.winfo_width())
        right = width - 7
        span = right - 7
        middle = 12
        canvas.create_line(7, middle, right, middle, fill='#777777')
        for index in range(7):
            x = 7 + (float(span) * index / 6)
            height = 7 if index in (0, 6) else 5
            canvas.create_line(
                x, middle - height, x, middle + height, fill='#777777')
        position = ruler['pos']
        if ruler['pinned'] == 'lo':
            position = 0
        elif ruler['pinned'] == 'hi':
            position = 1
        x = 7 + span * position
        colour = '#d94444'
        canvas.create_line(x, 3, x, 21, fill=colour, width=3)

    def _show_card_content(self, key):
        content = self.content_frames[key]
        if not content.winfo_manager():
            content.pack(anchor='w', fill=tk.BOTH, expand=True)

    def _show_status(self, key):
        label = self.status_labels[key]
        if not label.winfo_manager():
            label.pack(anchor='w', before=self.content_frames[key])

    def _ruler_resized(self, unused_event=None):
        self._queue_layout()

    def _view_resized(self, unused_event=None):
        self._queue_layout()

    def _observations_changed(self):
        for result in self.results_by_key.values():
            if result.get('suggestion') and result['status'] != 'Muted':
                self._update_card_details(result)
        self._queue_layout()

    def _update_card_details(self, result):
        key = result['key']
        suggestion = result['suggestion']
        details = ['! %s' % warning
                   for warning in suggestion.get('warnings') or []]
        if self.show_observations_var.get():
            details.extend('- %s' % explanation['text']
                           for explanation in
                           suggestion.get('explanations') or [])
            if not details:
                details.append(
                    'Nothing stands out from the reference songs.')
        label = self.detail_labels[key]
        if details:
            self.detail_vars[key].set('\n'.join(details))
            if not label.winfo_manager():
                label.pack(anchor='w', fill=tk.X, pady=(4, 0))
        else:
            self.detail_vars[key].set('')
            label.pack_forget()

    def _queue_layout(self):
        if self.layout_after_id is not None:
            try:
                self.after_cancel(self.layout_after_id)
            except Exception:
                pass
        self.layout_after_id = self.after(80, self._apply_layout)

    def _apply_layout(self):
        self.layout_after_id = None
        self.intro_label.configure(
            wraplength=max(260, self.winfo_width() - 24))
        for key in self.detail_labels:
            width = max(180, self.content_frames[key].winfo_width() - 12)
            self.summary_labels[key].configure(wraplength=width)
            self.detail_labels[key].configure(wraplength=width)
            self._draw_ruler(key, self.ruler_data.get(key))
