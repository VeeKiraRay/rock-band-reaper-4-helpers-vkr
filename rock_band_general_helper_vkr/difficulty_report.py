"""Concise, copyable difficulty report for authors.

Unlike the modern helper's WIP diagnostic export, this intentionally omits
raw factors and calibration internals. Python 2.7 compatible.
"""

from __future__ import unicode_literals

from .difficulty_explain import dot_count, song_notes


def format_suggestion_report(results, project_name=None, refreshed_at=None):
    title = 'Rock Band difficulty suggestions'
    if project_name:
        title += ' - %s' % project_name
    lines = [title]
    if refreshed_at:
        lines.append('Refreshed: %s' % refreshed_at)
    lines.extend([
        'Advisory only. Estimated from the complete Expert charts; official',
        'and player judgments can differ.',
    ])
    for note in song_notes(results):
        lines.extend(('', note))
    for result in results:
        lines.append('')
        suggestion = result.get('suggestion')
        if not suggestion:
            lines.append('%s - not scored' % result['label'])
            reason = result['status']
            if result.get('errors'):
                reason += ': %s' % result['errors'][0]
            lines.append('  %s' % reason)
            continue
        lines.append('%s - %s (rank %d)' % (
            result['label'], suggestion['tier_name'],
            suggestion['rank_shown']))
        lines.append('  Dots: %d/5%s' % (
            dot_count(suggestion['tier']),
            ' - red maximum' if suggestion['tier'] == 6 else ''))
        ruler_data = suggestion.get('ruler')
        if ruler_data:
            lines.append('  Tier band: %s to %s' % (
                ruler_data['lo_label'], ruler_data['hi_label']))
        for warning in suggestion.get('warnings') or []:
            lines.append('  ! %s' % warning)
        explanations = suggestion.get('explanations') or []
        if explanations:
            for explanation in explanations:
                lines.append('  - %s' % explanation['text'])
        else:
            lines.append(
                '  Nothing about this chart stands out from the reference songs.')
    return '\n'.join(lines)
