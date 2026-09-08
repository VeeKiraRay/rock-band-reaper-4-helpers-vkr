"""Guarded, verified transactions for legacy MIDI item chunks.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

from lib.midi_chunk import first_difference, sha256_text


class MidiChunkTransactionError(Exception):
    pass


def apply_verified_item_chunks(host, plans, undo_description,
                               guard_plans=None):
    """Apply prebuilt chunk plans with stale-state and read-back checks."""
    changed = [plan for plan in plans
               if plan['expected'] != plan['original']]
    if not changed:
        return 0

    checked = list(changed)
    checked_items = set(plan['item'] for plan in changed)
    for plan in guard_plans or ():
        if plan['item'] not in checked_items:
            checked.append(plan)
            checked_items.add(plan['item'])
    for plan in checked:
        current = host.read_item_chunk(plan['item'])
        if (current != plan['original'] or
                sha256_text(current) != plan['fingerprint']):
            raise MidiChunkTransactionError(
                'A MIDI item changed after analysis; no project changes were made.')

    began = False
    written = []
    try:
        host.begin_undo()
        began = True
        for plan in changed:
            # Treat the item as potentially changed once the setter is called,
            # even if the host reports a failure afterward.
            written.append(plan)
            host.write_item_chunk(plan['item'], plan['expected'])
            actual = host.read_item_chunk(plan['item'])
            if actual != plan['expected']:
                difference = first_difference(plan['expected'], actual)
                raise MidiChunkTransactionError(
                    'MIDI write verification differed at byte %s.' % difference)
        host.update_arrange()
        host.end_undo(undo_description)
        began = False
        return len(changed)
    except Exception as exc:
        rollback_ok = True
        for plan in reversed(written):
            try:
                host.write_item_chunk(plan['item'], plan['original'])
                if host.read_item_chunk(plan['item']) != plan['original']:
                    rollback_ok = False
            except Exception:
                rollback_ok = False
        try:
            host.update_arrange()
        except Exception:
            pass
        if began:
            try:
                host.end_undo(undo_description + ' FAILED; rollback attempted')
            except Exception:
                pass
        if isinstance(exc, MidiChunkTransactionError):
            detail = str(exc)
        else:
            detail = '%s: %s' % (exc.__class__.__name__, str(exc))
        raise MidiChunkTransactionError(
            '%s Rollback exact: %s.' %
            (detail, 'yes' if rollback_ok else 'NO'))
