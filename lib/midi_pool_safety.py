"""Project-wide safety checks for REAPER pooled MIDI source identifiers.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk import MidiChunkError


def verify_unshared_pool_sources(host, contexts):
    """Allow unique pool GUIDs but refuse shared or unverifiable sources."""
    guids = set(context['parsed'].pool_guid for context in contexts
                if context['parsed'].pool_guid)
    if not guids:
        return

    count_items = getattr(host, 'project_item_count', None)
    get_item = getattr(host, 'get_project_item', None)
    if count_items is None or get_item is None:
        raise MidiChunkError(
            'Mutation blocked: pooled MIDI source safety could not be '
            'verified across the project.')

    counts = dict((guid, 0) for guid in guids)
    try:
        item_count = count_items()
        for index in range(item_count):
            chunk = host.read_item_chunk(get_item(index))
            for line in chunk.splitlines():
                stripped = line.strip()
                for guid in guids:
                    if stripped == 'POOLEDEVTS %s' % guid:
                        counts[guid] += 1
    except Exception as exc:
        raise MidiChunkError(
            'Mutation blocked: project-wide pooled MIDI source scan failed '
            '(%s: %s).' % (exc.__class__.__name__, str(exc)))

    shared = [(guid, counts[guid]) for guid in sorted(guids)
              if counts[guid] != 1]
    if shared:
        detail = ', '.join('%s referenced %d times' % value
                           for value in shared)
        raise MidiChunkError(
            'Mutation blocked: pooled/shared MIDI source detected (%s).' %
            detail)
