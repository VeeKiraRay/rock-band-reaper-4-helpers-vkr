"""Workflow checklist state and REAPER 4.20 sidecar persistence.

Modern counterpart:
rock_band_general_helper_vkr/actions_workflow.lua

REAPER 4.20 has no project ExtState, so saved projects use a JSON sidecar
beside the RPP file. Python 2.7 compatible.
"""

from __future__ import unicode_literals

import json
import os
import tempfile
import time

from .workflow import composite_key


SIDECAR_SUFFIX = '.rbhelper-workflow.json'
SIDECAR_VERSION = 1
MAX_SIDECAR_BYTES = 1024 * 1024
try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)


class WorkflowPersistenceError(Exception):
    pass


def workflow_stats(entries, state):
    total = 0
    done = 0
    for entry in entries:
        if entry['kind'] != 'item':
            continue
        total += 1
        saved = state.get(composite_key(entry.get('section'), entry['label']))
        if saved and saved.get('checked'):
            done += 1
    return done, total


def prune_to_workflow(entries, state):
    live = set(composite_key(entry.get('section'), entry['label'])
               for entry in entries if entry['kind'] == 'item')
    return dict((key, value) for key, value in state.items() if key in live)


def toggle_workflow_item(state, section, label, checked, completed_at=None):
    new_state = dict(state)
    new_state[composite_key(section, label)] = {
        'section': section or '',
        'label': label,
        'checked': bool(checked),
        'ts': int(completed_at if completed_at is not None else time.time())
              if checked else None,
    }
    return new_state


def sidecar_path(project_path):
    return (project_path + SIDECAR_SUFFIX) if project_path else None


def _replace_file(source, target):
    replace = getattr(os, 'replace', None)
    if replace is not None:
        replace(source, target)
        return
    if os.name == 'nt':
        import ctypes
        move_file = ctypes.windll.kernel32.MoveFileExW
        move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p,
                              ctypes.c_ulong]
        move_file.restype = ctypes.c_int
        # MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH
        if not move_file(source, target, 0x1 | 0x8):
            raise ctypes.WinError()
        return
    os.rename(source, target)


def _atomic_write(path, payload):
    directory = os.path.dirname(path) or '.'
    prefix = os.path.basename(path) + '.'
    descriptor, temporary = tempfile.mkstemp(
        prefix=prefix, suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            encoded = payload.encode('utf-8')
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_file(temporary, path)
        temporary = None
    finally:
        if temporary:
            try:
                os.remove(temporary)
            except (IOError, OSError):
                pass


class WorkflowSidecarStore(object):
    def load(self, project_path):
        path = sidecar_path(project_path)
        if not path or not os.path.exists(path):
            return None, {}
        try:
            if os.path.getsize(path) > MAX_SIDECAR_BYTES:
                raise WorkflowPersistenceError(
                    'Workflow sidecar is unexpectedly large: %s' % path)
            with open(path, 'rb') as handle:
                data = json.loads(handle.read().decode('utf-8'))
        except WorkflowPersistenceError:
            raise
        except (IOError, OSError, UnicodeError, ValueError) as exc:
            raise WorkflowPersistenceError(
                'Could not load workflow sidecar %s (%s)' % (path, exc))
        if not isinstance(data, dict) or data.get('version') != SIDECAR_VERSION:
            raise WorkflowPersistenceError(
                'Unsupported workflow sidecar format: %s' % path)

        template = data.get('template')
        template = template if isinstance(template, STRING_TYPES) else None
        state = {}
        items = data.get('items', [])
        if not isinstance(items, list):
            raise WorkflowPersistenceError(
                'Invalid workflow item list: %s' % path)
        for item in items:
            if not isinstance(item, dict):
                continue
            section = item.get('section', '')
            label = item.get('label')
            if (not isinstance(section, STRING_TYPES) or
                    not isinstance(label, STRING_TYPES)):
                continue
            checked = bool(item.get('checked'))
            timestamp = item.get('completed_at')
            if not isinstance(timestamp, (int, float)):
                timestamp = None
            state[composite_key(section, label)] = {
                'section': section,
                'label': label,
                'checked': checked,
                'ts': int(timestamp) if checked and timestamp is not None
                      else None,
            }
        return template, state

    def save(self, project_path, template, state):
        path = sidecar_path(project_path)
        if not path:
            return False
        items = []
        for key in sorted(state):
            item = state[key]
            items.append({
                'section': item.get('section', ''),
                'label': item.get('label', ''),
                'checked': bool(item.get('checked')),
                'completed_at': item.get('ts'),
            })
        document = {
            'version': SIDECAR_VERSION,
            'template': template,
            'items': items,
        }
        try:
            payload = json.dumps(document, ensure_ascii=True, indent=2,
                                 sort_keys=True) + '\n'
            _atomic_write(path, payload)
        except (IOError, OSError, UnicodeError, ValueError) as exc:
            raise WorkflowPersistenceError(
                'Could not save workflow sidecar %s (%s)' % (path, exc))
        return True
