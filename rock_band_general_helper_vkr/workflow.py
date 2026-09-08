"""Workflow checklist template parsing.

Modern counterpart:
rock_band_general_helper_vkr/workflow.lua

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os


def composite_key(section, label):
    """Return the stable key for an item within a section."""
    return (section or '') + '\x1e' + label


def _brace_groups(line):
    groups = []
    depth = 0
    start = None
    for index, char in enumerate(line):
        if char == '{':
            if depth == 0:
                start = index
            depth += 1
        elif char == '}' and depth:
            depth -= 1
            if depth == 0:
                groups.append((start, index + 1))
    return groups


def _strip_brace_groups(line):
    groups = _brace_groups(line)
    if not groups:
        return line, None, 0
    parts = []
    position = 0
    for start, end in groups:
        parts.append(line[position:start])
        position = end
    parts.append(line[position:])
    label = ''.join(parts).strip()
    tooltip = None
    if len(groups) == 1:
        start, end = groups[0]
        tooltip = line[start + 1:end - 1]
    return label, tooltip, len(groups)


def parse_workflow_content(content):
    """Return ``(entries, warnings)`` for workflow template text."""
    entries = []
    warnings = []
    section = ''
    seen = set()
    last_item = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('[') and line.endswith(']') and len(line) > 2:
            section = line[1:-1]
            entries.append({'kind': 'header', 'label': section})
            last_item = None
            continue

        label, tooltip, group_count = _strip_brace_groups(line)
        if not label:
            if last_item is not None:
                sources = last_item['_tooltip_sources'] + group_count
                last_item['_tooltip_sources'] = sources
                last_item['tooltip'] = tooltip if sources == 1 else None
            continue

        key = composite_key(section, label)
        if key in seen:
            warnings.append(
                'Duplicate item under [%s]: "%s" (appears more than once)' %
                (section or '(no section)', label))
        seen.add(key)
        last_item = {
            'kind': 'item',
            'section': section,
            'label': label,
            'tooltip': tooltip if group_count == 1 else None,
            '_tooltip_sources': group_count,
        }
        entries.append(last_item)

    for entry in entries:
        entry.pop('_tooltip_sources', None)

    if content.count('[') != content.count(']'):
        warnings.append(
            "Uneven [ ] brackets: %d '[' vs %d ']' - check the file for a "
            'missing bracket.' % (content.count('['), content.count(']')))
    if content.count('{') != content.count('}'):
        warnings.append(
            "Uneven { } brackets: %d '{' vs %d '}' - check the file for a "
            'missing bracket.' % (content.count('{'), content.count('}')))
    return entries, warnings


def parse_workflow_file(path):
    try:
        with open(path, 'rb') as handle:
            content = handle.read().decode('utf-8-sig')
    except (IOError, OSError, UnicodeError) as exc:
        return [], ['Could not read file: %s (%s)' % (path, exc)]
    return parse_workflow_content(content)


def load_workflow_files(directory):
    """Load and alphabetize every ``.txt`` workflow in a directory."""
    try:
        filenames = os.listdir(directory)
    except (IOError, OSError):
        return []
    workflows = []
    for filename in filenames:
        stem, extension = os.path.splitext(filename)
        path = os.path.join(directory, filename)
        if extension != '.txt' or not os.path.isfile(path):
            continue
        entries, warnings = parse_workflow_file(path)
        workflows.append({
            'stem': stem,
            'label': stem,
            'entries': entries,
            'errors': warnings,
        })
    workflows.sort(key=lambda workflow: workflow['label'].lower())
    return workflows


def default_workflow_name(workflows):
    for workflow in workflows:
        if workflow['stem'] == 'Default':
            return workflow['stem']
    return workflows[0]['stem'] if workflows else None
