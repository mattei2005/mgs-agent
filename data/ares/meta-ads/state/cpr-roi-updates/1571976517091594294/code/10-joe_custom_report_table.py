"""Offline presentation only for authorized Joe G004 custom metric reports."""
import json
from pathlib import Path

POLICY = Path('/root/mgs-agent/data/ares/meta-ads/policies/joe-custom-report-layout.json')


def render(title_lines, groups, footer_lines):
    """Preserve supplied strings and groups; paginate complete fenced tables."""
    policy = json.loads(POLICY.read_text())
    assert policy['status'] == 'active'
    layout = policy['layout']
    heads = layout['column_order']
    widths = list(layout['minimum_widths'])
    sep = layout['separator']
    limit = layout['max_message_chars']
    groups = [(label, [tuple(str(v) for v in row) for row in rows]) for label, rows in groups]
    for _, rows in groups:
        for row in rows:
            assert len(row) == len(heads)
            assert all('\n' not in v and '\r' not in v and '`' not in v for v in row)
            widths = [max(w, len(v)) for w, v in zip(widths, row)]
    widths = [max(w, len(v)) for w, v in zip(widths, heads)]

    def line(row):
        return sep.join(v.ljust(w) if i < 2 else v.rjust(w) for i, (v, w) in enumerate(zip(row, widths)))

    title = '\n'.join(title_lines)
    header = line(heads)
    parts = []
    current = title
    for label, rows in groups:
        group_title = '**' + label + ' (' + str(len(rows)) + ')**'
        if not rows:
            block = group_title + '\nNenhuma encontrada neste corte.'
            if len(current + '\n\n' + block) > limit:
                parts.append(current)
                current = title
            current += '\n\n' + block
            continue
        pos = 0
        while pos < len(rows):
            heading = group_title if pos == 0 else group_title + ' · continuação'
            prefix = '\n\n' + heading + '\n```text\n' + header + '\n'
            lines = []
            while pos < len(rows):
                candidate = line(rows[pos])
                block = prefix + '\n'.join(lines + [candidate]) + '\n```'
                if len(current + block) > limit:
                    break
                lines.append(candidate)
                pos += 1
            if not lines:
                if current != title:
                    parts.append(current)
                    current = title
                    continue
                raise ValueError('A complete table row exceeds Discord capacity')
            current += prefix + '\n'.join(lines) + '\n```'
            if pos < len(rows):
                parts.append(current)
                current = title
    for paragraph in footer_lines:
        if not paragraph:
            continue
        assert len(title + '\n\n' + paragraph) <= limit, 'Footer exceeds Discord capacity'
        if len(current + '\n\n' + paragraph) > limit:
            parts.append(current)
            current = title
        current += '\n\n' + paragraph
    if current:
        parts.append(current)
    assert all(len(p) <= limit and p.count('```') % 2 == 0 for p in parts)
    return parts
