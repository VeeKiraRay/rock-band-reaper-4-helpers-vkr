"""Desktop tests for General > Workflow."""

from __future__ import print_function

import json
import os
import shutil
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rock_band_general_helper_vkr.actions_workflow import (
    SIDECAR_SUFFIX,
    WorkflowPersistenceError,
    WorkflowSidecarStore,
    prune_to_workflow,
    sidecar_path,
    toggle_workflow_item,
    workflow_stats,
)
from rock_band_general_helper_vkr.workflow import (
    composite_key,
    default_workflow_name,
    load_workflow_files,
    parse_workflow_content,
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def items_only(entries):
    return [entry for entry in entries if entry['kind'] == 'item']


def test_parser_headers_items_and_tooltips():
    entries, warnings = parse_workflow_content(
        '[First]\nPlain\nInline {one tip}\nOwn line\n{second tip}\n')
    items = items_only(entries)
    expect(not warnings, 'valid workflow produced warnings')
    expect(entries[0] == {'kind': 'header', 'label': 'First'},
           'header differs')
    expect(items[0]['section'] == 'First' and items[0]['label'] == 'Plain',
           'plain item differs')
    expect(items[1]['label'] == 'Inline' and items[1]['tooltip'] == 'one tip',
           'inline tooltip differs')
    expect(items[2]['tooltip'] == 'second tip', 'own-line tooltip differs')


def test_parser_ambiguity_duplicates_and_brackets():
    entries, warnings = parse_workflow_content(
        '[First]\nSame {one} {two}\nSame\nBroken {\n')
    items = items_only(entries)
    expect(items[0]['label'] == 'Same' and items[0]['tooltip'] is None,
           'ambiguous tooltip was not dropped')
    expect(any('Duplicate item' in warning for warning in warnings),
           'duplicate warning missing')
    expect(any('Uneven { }' in warning for warning in warnings),
           'brace warning missing')


def test_state_pruning_toggling_and_stats():
    entries, unused = parse_workflow_content('[One]\nSame\n[Two]\nSame\n')
    state = toggle_workflow_item({}, 'One', 'Same', True, 123)
    state = toggle_workflow_item(state, 'Two', 'Same', False, 456)
    expect(state[composite_key('One', 'Same')]['ts'] == 123,
           'checked timestamp differs')
    expect(state[composite_key('Two', 'Same')]['ts'] is None,
           'unchecked timestamp was retained')
    expect(workflow_stats(entries, state) == (1, 2), 'stats differ')
    pruned = prune_to_workflow(entries[:2], state)
    expect(list(pruned) == [composite_key('One', 'Same')],
           'template pruning differs')


def test_sidecar_roundtrip_and_invalid_file():
    directory = tempfile.mkdtemp(prefix='rbhelper_workflow_test_')
    try:
        project = os.path.join(directory, 'song.rpp')
        store = WorkflowSidecarStore()
        state = toggle_workflow_item({}, 'First', 'Done', True, 123456)
        expect(store.save(project, 'Default', state), 'saved project not saved')
        expect(sidecar_path(project) == project + SIDECAR_SUFFIX,
               'sidecar naming differs')
        template, loaded = store.load(project)
        expect(template == 'Default', 'template did not round-trip')
        expect(loaded == state, 'workflow state did not round-trip')
        with open(sidecar_path(project), 'wb') as handle:
            handle.write(b'{not json')
        try:
            store.load(project)
        except WorkflowPersistenceError:
            pass
        else:
            raise AssertionError('invalid sidecar was accepted')
    finally:
        shutil.rmtree(directory)


def test_unsaved_project_does_not_write():
    store = WorkflowSidecarStore()
    expect(store.load('') == (None, {}), 'unsaved load differs')
    expect(not store.save('', 'Default', {}), 'unsaved state wrote a sidecar')


def test_bundled_default_and_ui_import():
    directory = os.path.join(ROOT, 'resources', 'workflow')
    workflows = load_workflow_files(directory)
    expect(default_workflow_name(workflows) == 'Default',
           'bundled Default workflow missing')
    default = [item for item in workflows if item['stem'] == 'Default'][0]
    done, total = workflow_stats(default['entries'], {})
    expect(done == 0 and total > 40, 'bundled workflow content is incomplete')
    from rock_band_general_helper_vkr import ui_workflow
    expect(hasattr(ui_workflow, 'WorkflowView'), 'Workflow view is missing')


def test_ui_constructs_and_keeps_unsaved_project_sessions_separate():
    try:
        import Tkinter as tk
    except ImportError:
        import tkinter as tk
    from rock_band_general_helper_vkr.ui_workflow import WorkflowView

    class SwitchingHost(object):
        def __init__(self):
            self.current = {
                'identity': 'project-a', 'path': '', 'name': 'Project A'}

        def project_info(self):
            return dict(self.current)

    class MemoryStore(object):
        def __init__(self):
            self.saved_paths = []

        def load(self, unused_path):
            return None, {}

        def save(self, path, unused_template, unused_state):
            self.saved_paths.append(path)
            return bool(path)

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        print('SKIP: Tk display unavailable for Workflow construction test')
        if root is not None:
            root.destroy()
        return
    try:
        shown = []
        host = SwitchingHost()
        store = MemoryStore()
        view = WorkflowView(
            root, lambda status, result: shown.append((status, result)),
            host=host, store=store)
        workflow = view.workflow_by_name['Default']
        first = [entry for entry in workflow['entries']
                 if entry['kind'] == 'item'][0]
        variable = tk.BooleanVar()
        variable.set(True)
        view._toggle(first['section'], first['label'], variable)
        expect(workflow_stats(workflow['entries'], view.state)[0] == 1,
               'Project A toggle was not retained')

        host.current = {
            'identity': 'project-b', 'path': '', 'name': 'Project B'}
        view.refresh_current()
        expect(workflow_stats(workflow['entries'], view.state)[0] == 0,
               'Project A state leaked into Project B')
        host.current = {
            'identity': 'project-a', 'path': '', 'name': 'Project A'}
        view.refresh_current()
        expect(workflow_stats(workflow['entries'], view.state)[0] == 1,
               'Project A session state was not restored')
        expect(shown and 'session' in shown[0][0],
               'unsaved-project status did not explain session persistence')

        host.current = {
            'identity': 'project-a', 'path': r'C:\Songs\project-a.rpp',
            'name': 'project-a'}
        view.refresh_current()
        variable.set(False)
        view._toggle(first['section'], first['label'], variable)
        expect(store.saved_paths[-1] == host.current['path'],
               'Save As path change kept writing to the old project path')
    finally:
        root.destroy()


def main():
    tests = [
        test_parser_headers_items_and_tooltips,
        test_parser_ambiguity_duplicates_and_brackets,
        test_state_pruning_toggling_and_stats,
        test_sidecar_roundtrip_and_invalid_file,
        test_unsaved_project_does_not_write,
        test_bundled_default_and_ui_import,
        test_ui_constructs_and_keeps_unsaved_project_sessions_separate,
    ]
    for test in tests:
        test()
        print('PASS: %s' % test.__name__)
    print('Workflow production tests: PASS (%d tests)' % len(tests))


if __name__ == '__main__':
    main()
