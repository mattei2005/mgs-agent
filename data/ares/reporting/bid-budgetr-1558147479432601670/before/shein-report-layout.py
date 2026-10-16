#!/usr/bin/env python3
"""Canonical SHEIN report renderer/gate. Offline only; never posts or mutates APIs."""
import argparse
import copy
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shein_report_delivery import discord_length, register_report

CONTRACT = Path('/root/mgs-agent/data/ares/meta-ads/operations/SHEIN-US-DIRECT.json')


class LayoutError(ValueError):
    pass


def policy():
    return json.loads(CONTRACT.read_text())['reporting']['on_demand_default_layout']


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def signal(value, estimated=False):
    v = number(value)
    if v is None:
        return '⚪'
    rule = policy()['roi_direction_signal']
    if estimated:
        bands = rule['estimated_roi']
        return bands['red']['color'] if v < Decimal(bands['red']['value']) else bands['green']['color'] if v > Decimal(bands['green']['value']) else bands['yellow']['color']
    colors = rule['real_roi']
    return colors['positive'] if v > 0 else colors['negative'] if v < 0 else colors['exact_zero']


def mean_roi(values):
    valid = [v for x in values if (v := number(x)) is not None]
    return (sum(valid) / len(valid) if valid else None, len(valid))


def roi(revenue, spend):
    r, s = number(revenue), number(spend)
    return (r - s) * 100 / s if r is not None and s is not None and s > 0 else None


def equal_metric(actual, expected, label):
    a, e = number(actual), number(expected)
    if (a is None) != (e is None) or (a is not None and abs(a - e) > Decimal('1e-18')):
        raise LayoutError('Inconsistent ' + label)


def fmt(value, suffix='', signed=False, places=2):
    v = number(value)
    if v is None:
        return 'n/d'
    v = v.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return format(v, f'+.{places}f' if signed else f'.{places}f').replace('.', ',') + suffix


def visual_width(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in text)


def product_label(value, remove_ellipsis=False, max_characters=None):
    rule = policy().get('product_column') or {}
    limit = rule.get('max_characters', 20)
    visual_limit = rule.get('max_visual_width', limit)
    suffix = rule.get('ellipsis', '')
    if max_characters is not None:
        if not isinstance(max_characters, int) or isinstance(max_characters, bool) or max_characters <= 0 or max_characters > limit:
            raise LayoutError('Preview product cap must be a positive integer no larger than the default')
        limit = max_characters
        visual_limit = min(visual_limit, limit)
    budget_suffix = '' if remove_ellipsis and max_characters is not None else suffix
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < len(budget_suffix) or not isinstance(visual_limit, int) or visual_limit < visual_width(budget_suffix):
        raise LayoutError('Invalid product display limit')
    text = unicodedata.normalize('NFC', str(value) if value is not None else 'n/d')
    text = ' '.join(text.replace('|', ' ').split())
    def fits(candidate):
        return len(candidate) <= limit and visual_width(candidate) <= visual_limit
    if fits(text):
        return text
    prefix = text
    while prefix and not fits(prefix.rstrip() + budget_suffix):
        prefix = prefix[:-1]
    return prefix.rstrip() if remove_ellipsis else prefix.rstrip() + suffix


def bar_positions(text):
    positions, current = [], 0
    for char in text:
        if char == '|':
            positions.append(current)
        current += visual_width(char)
    return positions


def family_groups(rows):
    ids = {r['id']: r for r in rows}
    if len(ids) != len(rows):
        raise LayoutError('Duplicate campaign ID')
    by_number, children, parents, notes = defaultdict(list), defaultdict(list), {}, []
    for r in rows:
        # Match numeric identity, preserving literal padding in all labels.
        by_number[(r['product'], int(r['number']))].append(r['id'])
    for r in rows:
        source = r.get('copy_source_literal')
        if source is None:
            continue
        matches = by_number[(r['product'], int(source))]
        if len(matches) != 1:
            notes.append('Origem COPY fora do recorte ou ambígua: ' + r['number'])
            continue
        parents[r['id']] = matches[0]
        children[matches[0]].append(r['id'])
    colors = {}
    def check(cid):
        if colors.get(cid) == 1:
            raise LayoutError('COPY cycle')
        if colors.get(cid) == 2:
            return
        colors[cid] = 1
        for child in children[cid]:
            check(child)
        colors[cid] = 2
    for cid in ids:
        check(cid)
    key = lambda cid: (ids[cid].get('first_delivery') or '9999-12-31', int(ids[cid]['number']), cid)
    def tree(cid):
        group = [ids[cid]]
        for child in sorted(children[cid], key=key):
            group.extend(tree(child))
        return group
    roots = sorted((cid for cid in ids if cid not in parents), key=lambda cid: (unicodedata.normalize('NFKD', ids[cid]['product']).casefold(), *key(cid)))
    groups = [tree(cid) for cid in roots]
    if len([r for g in groups for r in g]) != len(rows):
        raise LayoutError('Family coverage mismatch')
    return groups, notes


def pack_complete_parts(parts):
    """Combine complete blocks where possible; never split a row or fence."""
    packed = []
    for part in parts:
        if packed and discord_length(packed[-1] + '\n\n' + part) <= 2000:
            packed[-1] += '\n\n' + part
        else:
            packed.append(part)
    return packed


def table_parts(title, headers, groups, left_columns, join, prefix=''):
    flat = [r for group in groups for r in group]
    widths = [max(visual_width(v) for v in [headers[i]] + [row[i] for row in flat]) for i in range(len(headers))]
    def cell(value, width, left):
        spaces = width - visual_width(value)
        if left:
            return value + ' ' * spaces
        n = spaces // 2
        return ' ' * n + value + ' ' * (spaces - n)
    def line(row):
        return join.join(cell(v, w, i in left_columns) for i, (v, w) in enumerate(zip(row, widths))).rstrip()
    header = line(headers)
    lines = [line(row) for row in flat]
    def message(chunk, i, total):
        lead = prefix.strip() + '\n\n' if prefix and i == 1 else ''
        return lead + f'**{title} · {i}/{total}**\n```text\n' + header + '\n' + '\n'.join(chunk) + ('\n' if chunk else '') + '```'
    if prefix and lines and discord_length(message([lines[0]], 1, 1)) > 2000:
        return pack_complete_parts([prefix.strip(), *table_parts(title, headers, groups, left_columns, join)])
    # Fixed point includes the real page numbers rather than an arbitrary reserve.
    # The new capacity-first policy permits a family boundary only when needed;
    # adjacency and exact parent/child order remain unchanged.
    total = 1
    while True:
        chunks, current = [], []
        if discord_length(message([], 1, total)) > 2000:
            raise LayoutError('Table header exceeds Discord capacity')
        for item in lines:
            i = len(chunks) + 1
            if discord_length(message(current + [item], i, total)) <= 2000:
                current.append(item)
            else:
                if not current:
                    raise LayoutError('One row exceeds Discord capacity')
                chunks.append(current)
                current = [item]
                if discord_length(message(current, len(chunks) + 1, total)) > 2000:
                    raise LayoutError('One row exceeds Discord capacity')
        if current or not chunks:
            chunks.append(current)
        if len(chunks) == total:
            break
        total = len(chunks)
    parts = []
    for i, chunk in enumerate(chunks, 1):
        if any(bar_positions(row) != bar_positions(header) for row in chunk):
            raise LayoutError('Visual separators misaligned')
        text = message(chunk, i, total)
        if discord_length(text) > 2000:
            raise LayoutError('Discord part too large')
        parts.append(text)
    return parts


def render_model(model, preview_remove_product_ellipsis=False, preview_product_max_characters=None):
    cfg = policy()
    if preview_product_max_characters is not None:
        product_label('', remove_ellipsis=preview_remove_product_ellipsis, max_characters=preview_product_max_characters)
    if cfg.get('column_separators', {}).get('join') != ' | ':
        raise LayoutError('Unsupported separator contract')
    account = model.get('account') or {}
    if not all(account.get(k) for k in ('id', 'name', 'currency', 'timezone_name')):
        raise LayoutError('Missing account evidence')
    target = date.fromisoformat(model['date'])
    dates = [(target - timedelta(days=n)).isoformat() for n in range(cfg['campaign_roi_history']['days'] - 1, -1, -1)]
    if model.get('history_dates') != dates:
        raise LayoutError('History must contain the exact seven civil dates')
    stamps = model.get('source_timestamps') or {}
    stamp = stamps.get('insights') or model.get('snapshot_at')
    if not stamp:
        raise LayoutError('Missing financial snapshot timestamp')
    cutoff = datetime.fromisoformat(stamp).astimezone(ZoneInfo(account['timezone_name']))
    rows = copy.deepcopy(model.get('rows', []))
    required = ('id', 'name', 'number', 'product', 'quiz', 'bid', 'spend', 'net_revenue', 'estimated_revenue', 'roi', 'estimated_roi', 'health', 'roas', 'first_delivery', 'history')
    for r in rows:
        missing = [key for key in required if key not in r]
        if missing:
            raise LayoutError('Missing evidence fields: ' + ','.join(missing))
        if not re.fullmatch(r'\d+', r['number']):
            raise LayoutError('Campaign number must be literal digits')
        if not isinstance(r['product'], str):
            raise LayoutError('Product label must be text')
        if number(r['spend']) is None or number(r['spend']) < 0:
            raise LayoutError('Invalid Meta spend')
        equal_metric(r['roi'], roi(r['net_revenue'], r['spend']), 'current ROI')
        equal_metric(r['estimated_roi'], roi(r['estimated_revenue'], r['spend']), 'estimated ROI')
        markers = re.findall(r'\bCOPY\s+C(\d+)\b', r['name'], re.I)
        if len(set(markers)) > 1:
            raise LayoutError('Ambiguous COPY marker')
        r['copy_source_literal'] = markers[0] if markers else None
        r['display'] = r['number'] + (' COPY C' + markers[0] if markers else '')
        if [h.get('date') for h in r['history']] != dates:
            raise LayoutError('Daily campaign coverage mismatch')
        for h in r['history']:
            if not all(k in h for k in ('spend', 'net_revenue', 'roi', 'partial')):
                raise LayoutError('Missing daily source evidence')
            equal_metric(h['roi'], roi(h['net_revenue'], h['spend']), 'daily ROI')
            if h['date'] != dates[-1] and h['partial']:
                raise LayoutError('Past civil date cannot be current partial')
        equal_metric(r['history'][-1]['roi'], r['roi'], 'current history/main snapshot')
    groups, notes = family_groups(rows)
    main_groups, history_groups = [], []
    for group in groups:
        main, history = [], []
        for r in group:
            start = date.fromisoformat(r['first_delivery']).strftime('%d/%m') if r['first_delivery'] else 'n/d'
            age = 'D' + str((target - date.fromisoformat(r['first_delivery'])).days + 1) if r['first_delivery'] else 'n/d'
            balance = number(r['net_revenue']) - number(r['spend']) if number(r['net_revenue']) is not None else None
            values = {'R/E': signal(r['roi']) + signal(r['estimated_roi'], True), 'Início': start, 'Nº': r['display'], 'Produto': product_label(r['product'], remove_ellipsis=preview_remove_product_ellipsis, max_characters=preview_product_max_characters), 'Quiz': r['quiz'], 'Gasto': fmt(r['spend']), 'Receita': fmt(r['net_revenue']), 'Saldo': fmt(balance, signed=True), 'Est.Health': fmt(r['health'], '%'), 'ROI': fmt(r['roi'], '%', True), 'ROI est.': fmt(r['estimated_roi'], '%', True), 'ROAS': fmt(r['roas'], 'x'), 'Lance': r['bid']}
            try:
                main.append([values[k] for k in cfg['columns']])
            except KeyError as exc:
                raise LayoutError('Renderer requires update for new column') from exc
            average, n = mean_roi([h['roi'] for h in r['history']])
            partial = any(h['partial'] and number(h['roi']) is not None for h in r['history'])
            avg = fmt(average, '%', True, 1) + ('*' if partial else '') + (f' ({n}/7)' if 0 < n < 7 else '')
            history.append([start, r['display'], age] + [fmt(h['roi'], '%', True, 1) + ('*' if h['partial'] and h['roi'] is not None else '') for h in r['history']] + [avg])
        main_groups.append(main)
        history_groups.append(history)
    has_partial = any(h['partial'] for r in rows for h in r['history'])
    history_headers = ['Início', 'Nº', 'Dia'] + [date.fromisoformat(dt).strftime('%d/%m') + ('*' if i == len(dates) - 1 and has_partial else '') for i, dt in enumerate(dates)] + ['Média 7d']
    left = {i for i, name in enumerate(cfg['columns']) if name in cfg['alignment']['main']['left_aligned_exceptions']}
    main_parts = table_parts('SHEIN — principal', cfg['columns'], main_groups, left, ' | ')
    history_parts = table_parts('Histórico ROI real — 7 dias', history_headers, history_groups, set(), ' | ')
    delay = number((model.get('delay') or {}).get('totalMinutes'))
    if delay is None or delay < 0:
        delay_label = 'n/d — fonte indisponível ou inválida'
    else:
        hh, mm = divmod(int(delay), 60)
        delay_label = f'{hh}h {mm:02d}min' if hh else f'{mm}min'
    spend = sum(number(r['spend']) for r in rows)
    revenue = sum(number(r['net_revenue']) for r in rows) if rows and all(number(r['net_revenue']) is not None for r in rows) else None
    estimated = sum(number(r['estimated_revenue']) for r in rows) if rows and all(number(r['estimated_revenue']) is not None for r in rows) else None
    balance = revenue - spend if revenue is not None else None
    header = f"## SHEIN · {account['name']}\n**{target.strftime('%d/%m/%Y')} · até {cutoff.strftime('%H:%M %Z')} · {account['currency']}**\n**⏱️ ATRASO GAM/SB: {delay_label}**\n"
    if preview_product_max_characters is not None:
        qualifier = ', sem reticências' if preview_remove_product_ellipsis else ''
        header = f'**Prévia visual: Produto até {preview_product_max_characters} caracteres{qualifier}; mesmo snapshot financeiro.**\n' + header
    elif preview_remove_product_ellipsis:
        header = '**Prévia visual: Produto sem reticências; mesmo snapshot financeiro.**\n' + header
    header += f"Gasto **{fmt(spend)}** · Receita **{fmt(revenue)}** · Saldo **{fmt(balance, signed=True)}** · ROI **{fmt(roi(revenue, spend), '%', True)}** · ROI est. **{fmt(roi(estimated, spend), '%', True)}**.\n"
    if not rows:
        header += 'Sem campanhas com entrega no recorte; nenhuma linha financeira foi inventada.\n'
    footer = f"{'* ' + target.strftime('%d/%m') + ' parcial até ' + cutoff.strftime('%H:%M %Z') + '.\n' if has_partial else ''}"
    footer += 'Fontes: Meta Insights × Smart Bidding/Adgroup. ROI = receita líquida/gasto Meta − 1; ROI est. = receita estimada/gasto Meta − 1; ROAS = valor de compras Meta/gasto.\nReceita/ROI sujeitos ao atraso GAM/SB.\n'
    if cfg.get('legend', {}).get('enabled', False):
        footer += 'Média 7d = média aritmética dos ROIs reais diários válidos; n/d não vira zero; (n/7) indica cobertura incompleta. Produto é rótulo do nome; COPY é origem direta explícita.\n'
    if notes:
        footer += '\n'.join(notes) + '\n'
    footer += f'**Fim do relatório — {len(rows)} campanhas e histórico de 7 dias.**'
    main_delivery = table_parts('SHEIN — principal', cfg['columns'], main_groups, left, ' | ', prefix=header.strip())
    parts = pack_complete_parts([*main_delivery, *history_parts, footer.strip()])
    result = {'text': '\n\n'.join(parts), 'parts': parts, 'main_parts': main_parts, 'history_parts': history_parts, 'campaign_order': [r['display'] for g in groups for r in g], 'campaign_ids': [r['id'] for g in groups for r in g], 'main_rows': len(rows), 'history_rows': len(rows), 'history_cells': len(rows) * len(dates), 'contract_sha256': hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
    if any(discord_length(p) > 2000 for p in parts):
        raise LayoutError('Header or footer exceeds Discord capacity')
    return result


def validate_report(model, text, thread_id=None, preview_remove_product_ellipsis=False, preview_product_max_characters=None):
    if thread_id is not None:
        check_thread_binding(model, thread_id)
    result = render_model(model, preview_remove_product_ellipsis=preview_remove_product_ellipsis, preview_product_max_characters=preview_product_max_characters)
    if text != result['text']:
        raise LayoutError('Report differs from canonical rendering; do not publish')
    return {'status': 'validated', 'contract_sha256': result['contract_sha256'], 'report_sha256': hashlib.sha256(text.encode()).hexdigest(), 'model_sha256': hashlib.sha256(json.dumps(model, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), 'account_id': model['account']['id'], 'account_name': model['account']['name'], 'thread_id': thread_id, 'report_date': model['date'], 'main_rows': result['main_rows'], 'history_rows': result['history_rows'], 'parts': len(result['parts']), 'max_part_chars': max(map(len, result['parts'])), 'max_part_utf16_units': max(map(discord_length, result['parts'])), 'pagination_policy': 'capacity_first_exact_2000_no_secondary_split', 'preview_remove_product_ellipsis': bool(preview_remove_product_ellipsis), 'preview_product_max_characters': preview_product_max_characters}


def check_thread_binding(model, thread_id):
    index = Path('/root/mgs-agent/data/ares/discord/shein-intraday-report-bindings.json')
    bindings = json.loads(index.read_text())['bindings']
    matches = [b for b in bindings if b['thread_id'] == str(thread_id)]
    if len(matches) != 1:
        raise LayoutError('Thread is not uniquely bound to a SHEIN account')
    account = model.get('account') or {}
    binding = matches[0]
    if str(account.get('id', '')).removeprefix('act_') != binding['account_id'] or account.get('name') != binding['account_name']:
        raise LayoutError('Thread/account identity mismatch')
    return binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    render = sub.add_parser('render')
    render.add_argument('--input', required=True)
    render.add_argument('--output', required=True)
    render.add_argument('--thread-id')
    render.add_argument('--preview-remove-product-ellipsis', action='store_true')
    render.add_argument('--preview-product-max-characters', type=int)
    validate = sub.add_parser('validate')
    validate.add_argument('--input', required=True)
    validate.add_argument('--report', required=True)
    validate.add_argument('--receipt')
    validate.add_argument('--thread-id')
    validate.add_argument('--preview-remove-product-ellipsis', action='store_true')
    validate.add_argument('--preview-product-max-characters', type=int)
    args = parser.parse_args()
    try:
        model = json.loads(Path(args.input).read_text())
        if args.thread_id:
            check_thread_binding(model, args.thread_id)
        if args.command == 'render':
            result = render_model(model, preview_remove_product_ellipsis=args.preview_remove_product_ellipsis, preview_product_max_characters=args.preview_product_max_characters)
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result['text'])
            path.with_suffix('.parts.json').write_text(json.dumps(result['parts'], ensure_ascii=False, indent=2))
            receipt = validate_report(model, result['text'], args.thread_id, args.preview_remove_product_ellipsis, args.preview_product_max_characters)
            receipt['delivery_receipt'] = str(register_report(result))
            print(json.dumps(receipt, ensure_ascii=False))
        else:
            receipt = validate_report(model, Path(args.report).read_text(), args.thread_id, args.preview_remove_product_ellipsis, args.preview_product_max_characters)
            result = render_model(model, args.preview_remove_product_ellipsis, args.preview_product_max_characters)
            receipt['delivery_receipt'] = str(register_report(result))
            if args.receipt:
                Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
            print(json.dumps(receipt, ensure_ascii=False))
    except (LayoutError, KeyError, ValueError, TypeError) as exc:
        print(json.dumps({'status': 'invalid', 'reason': str(exc)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
