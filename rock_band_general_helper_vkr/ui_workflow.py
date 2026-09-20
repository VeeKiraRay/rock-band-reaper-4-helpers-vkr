"""Tk rendering for General Helper General > Workflow.

Modern counterpart:
rock_band_general_helper_vkr/ui_workflow.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os
import time

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk

from lib.reaper420 import Reaper420Host
from lib.tk_common import PALETTE, ResponsiveLabel, Tooltip
from .actions_workflow import (
    WorkflowPersistenceError,
    WorkflowSidecarStore,
    prune_to_workflow,
    toggle_workflow_item,
    workflow_stats,
)
from .workflow import composite_key, default_workflow_name, load_workflow_files


def workflow_resource_directory():
    package_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(package_dir), 'resources', 'workflow')


def project_session_key(project):
    if not project:
        return '(unknown project)'
    return project.get('identity') or project.get('path') or '(unknown project)'


class WorkflowView(ttk.Frame):
    def __init__(self, parent, show_result, host=None, store=None,
                 resource_directory=None):
        ttk.Frame.__init__(self, parent, padding=10)
        self.show_result = show_result
        self.host = host or Reaper420Host()
        self.store = store or WorkflowSidecarStore()
        self.workflows = load_workflow_files(
            resource_directory or workflow_resource_directory())
        self.workflow_by_name = dict(
            (workflow['stem'], workflow) for workflow in self.workflows)
        self.sessions = {}
        self.project = None
        self.session_key = None
        self.state = {}
        self.variables = []

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X)
        ttk.Label(controls, text='Workflow').pack(side=tk.LEFT)
        self.workflow_var = tk.StringVar()
        self.workflow_combo = ttk.Combobox(
            controls, state='readonly', width=30,
            textvariable=self.workflow_var,
            values=[workflow['label'] for workflow in self.workflows])
        self.workflow_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.workflow_combo.bind('<<ComboboxSelected>>', self._select_workflow)

        self.show_timestamps_var = tk.BooleanVar()
        self.show_timestamps_var.set(False)
        timestamp_check = ttk.Checkbutton(
            self, text='Show completion timestamp',
            variable=self.show_timestamps_var, command=self._render)
        timestamp_check.pack(anchor='w', pady=(10, 0))

        self.hide_done_var = tk.BooleanVar()
        self.hide_done_var.set(False)
        hide_check = ttk.Checkbutton(
            self, text='Show only unfinished', variable=self.hide_done_var,
            command=self._render)
        hide_check.pack(anchor='w')

        self.project_var = tk.StringVar()
        self.project_var.set('Project: unavailable')
        ttk.Label(self, textvariable=self.project_var).pack(
            anchor='w', pady=(8, 0))
        self.persistence_var = tk.StringVar()
        ttk.Label(self, textvariable=self.persistence_var).pack(anchor='w')

        self.progress_var = tk.StringVar()
        ttk.Label(self, textvariable=self.progress_var).pack(
            anchor='w', pady=(8, 4))

        self.checklist = ttk.Frame(self)
        self.checklist.pack(fill=tk.X)

        if not self.workflows:
            self.workflow_combo.configure(state=tk.DISABLED)
            self.persistence_var.set(
                'No workflow templates found in resources/workflow.')
            self._render()
        else:
            self._activate_project(self._read_project())
        self.after(1000, self._poll_project)

    def refresh_current(self):
        self._check_project_change()

    def _read_project(self):
        try:
            return self.host.project_info()
        except Exception:
            return {'identity': None, 'path': '', 'name': 'Unknown project'}

    def _poll_project(self):
        try:
            self._check_project_change()
        finally:
            try:
                self.after(1000, self._poll_project)
            except Exception:
                pass

    def _check_project_change(self):
        project = self._read_project()
        old_path = self.project.get('path', '') if self.project else ''
        if (project_session_key(project) != self.session_key or
                project.get('path', '') != old_path):
            self._activate_project(project)

    def _activate_project(self, project):
        if self.session_key is not None:
            self.sessions[self.session_key] = {
                'template': self.workflow_var.get(),
                'state': self.state,
            }
        self.project = project
        self.session_key = project_session_key(project)
        saved = self.sessions.get(self.session_key)
        load_error = None
        if saved is None:
            try:
                template, state = self.store.load(project.get('path', ''))
            except WorkflowPersistenceError as exc:
                template, state = None, {}
                load_error = str(exc)
            saved = {'template': template, 'state': state}
            self.sessions[self.session_key] = saved

        template = saved.get('template')
        if template not in self.workflow_by_name:
            template = default_workflow_name(self.workflows)
        self.workflow_var.set(template or '')
        workflow = self.workflow_by_name.get(template)
        self.state = prune_to_workflow(
            workflow['entries'] if workflow else {}, saved.get('state', {}))
        saved['template'] = template
        saved['state'] = self.state

        name = project.get('name') or 'Unknown project'
        path = project.get('path') or ''
        self.project_var.set('Project: %s' % name)
        if path:
            self.persistence_var.set(
                'Progress autosaves beside this project as a workflow sidecar.')
        else:
            self.persistence_var.set(
                'Unsaved project: progress lasts only while this helper is open.')
        self._render()
        if load_error:
            # GeneralHelperApp builds the shared result area after its views.
            # Deferring also keeps a bad sidecar from breaking app startup.
            self.after_idle(
                lambda error=load_error: self.show_result(
                    'Workflow sidecar could not be loaded.', error))

    def _select_workflow(self, unused_event=None):
        name = self.workflow_var.get()
        workflow = self.workflow_by_name.get(name)
        if workflow is None:
            return
        self.state = prune_to_workflow(workflow['entries'], self.state)
        self._remember_and_save()
        self._render()

    def _toggle(self, section, label, variable):
        self.state = toggle_workflow_item(
            self.state, section, label, bool(variable.get()))
        self._remember_and_save()
        self._render()

    def _remember_and_save(self):
        self.sessions[self.session_key] = {
            'template': self.workflow_var.get(),
            'state': self.state,
        }
        try:
            persisted = self.store.save(
                self.project.get('path', ''), self.workflow_var.get(),
                self.state)
        except WorkflowPersistenceError as exc:
            self.show_result('Workflow progress could not be saved.', str(exc))
            return
        status = ('Workflow progress saved.' if persisted else
                  'Workflow progress retained for this helper session.')
        self.show_result(status, self._format_report())

    def _format_report(self):
        workflow = self.workflow_by_name.get(self.workflow_var.get())
        entries = workflow['entries'] if workflow else []
        done, total = workflow_stats(entries, self.state)
        lines = [
            'Workflow - %s' % (self.workflow_var.get() or '(none)'),
            'Project - %s' % (self.project.get('name') or 'Unknown project'),
            'Completed - %d / %d' % (done, total),
        ]
        remaining = []
        for entry in entries:
            if entry['kind'] != 'item':
                continue
            saved = self.state.get(composite_key(
                entry.get('section'), entry['label']))
            if not saved or not saved.get('checked'):
                remaining.append('%s: %s' % (
                    entry.get('section') or '(no section)', entry['label']))
        if remaining:
            lines.append('')
            lines.append('Remaining:')
            lines.extend('- ' + item for item in remaining)
        else:
            lines.extend(['', 'Everything checked off!'])
        return '\n'.join(lines)

    def _render(self):
        for child in self.checklist.winfo_children():
            child.destroy()
        self.variables = []
        workflow = self.workflow_by_name.get(self.workflow_var.get())
        if workflow is None:
            self.progress_var.set('0 / 0 completed - 0%')
            ttk.Label(
                self.checklist, text='No workflow template is available.').pack(
                anchor='w', padx=4, pady=4)
            return

        done, total = workflow_stats(workflow['entries'], self.state)
        percent = int(float(done) / total * 100.0 + 0.5) if total else 0
        self.progress_var.set(
            '%d / %d completed - %d%%' % (done, total, percent))

        for warning in workflow['errors']:
            ResponsiveLabel(
                self.checklist, text='! ' + warning,
                foreground=PALETTE['warning'], wraplength=650,
                justify=tk.LEFT).pack(anchor='w', fill=tk.X, padx=4, pady=2)

        pending_header = None
        rendered = False
        for entry in workflow['entries']:
            if entry['kind'] == 'header':
                pending_header = entry['label']
                continue
            saved = self.state.get(composite_key(
                entry.get('section'), entry['label']))
            checked = bool(saved and saved.get('checked'))
            if self.hide_done_var.get() and checked:
                continue
            if pending_header is not None:
                ttk.Separator(self.checklist).pack(
                    fill=tk.X, padx=4, pady=(10 if rendered else 2, 4))
                ttk.Label(
                    self.checklist, text=pending_header,
                    font=('TkDefaultFont', 9, 'bold')).pack(
                    anchor='w', padx=4, pady=(0, 2))
                pending_header = None
            rendered = True
            variable = tk.BooleanVar()
            variable.set(checked)
            self.variables.append(variable)
            check = ttk.Checkbutton(
                self.checklist, text=entry['label'], variable=variable,
                command=lambda section=entry.get('section', ''),
                label=entry['label'], var=variable:
                self._toggle(section, label, var))
            check.pack(anchor='w', fill=tk.X, padx=12, pady=1)
            if entry.get('tooltip'):
                Tooltip(check, entry['tooltip'])
            if self.show_timestamps_var.get() and checked and saved.get('ts'):
                timestamp = time.strftime(
                    '%d.%m.%Y at %H:%M', time.localtime(saved['ts']))
                ttk.Label(
                    self.checklist, text='    Completed on ' + timestamp,
                    foreground=PALETTE['muted']).pack(anchor='w', padx=30)

        if self.hide_done_var.get() and not rendered:
            ttk.Label(
                self.checklist, text='Everything checked off!').pack(
                    anchor='w', padx=4, pady=8)
