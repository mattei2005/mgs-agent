#!/usr/bin/env python3
"""Alert actionable SB Utility message states in the templates/broadcast channel.

Live SB is the source of truth. Red and purple are reported immediately; gray is
reported after >=2 days. Local state preserves first_seen markers between runs.
Cron delivery target is Discord channel 1522487422510694450; stdout is the alert.
"""
import asyncio, datetime as dt, importlib.util, json, pathlib, re
from zoneinfo import ZoneInfo

BASE = pathlib.Path('/root/mgs-agent')
STATE = BASE / 'data/sb-utility-gray-alert-state.json'
TZ = ZoneInfo('America/New_York')
ALERT_AFTER_DAYS = 2

spec = importlib.util.spec_from_file_location('rollout', BASE / 'scripts/sb-utility-rollout-manager.py')
assert spec and spec.loader
rollout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollout)

def now_et():
    return dt.datetime.now(TZ)

def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {'version': 1, 'items': {}}

def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def key_for(template, msg):
    return json.dumps({'template': template, 'key': rollout.msg_key(msg)}, ensure_ascii=False, separators=(',', ':'))


def template_columns(template):
    """Split '<site> - <config> - gNNN-d <manager>' without dropping source data."""
    match = re.match(r'^(.*?)\s+-\s+(.*?)\s+-\s+g\d+-d\s+(.+)$', template or '')
    if not match:
        return str(template or '').strip(), '-', '-'
    return tuple(part.strip() for part in match.groups())


def is_active_production_row(row):
    name = str(row.get('NAME') or '').strip()
    lowered = name.lower()
    if not name or lowered.startswith('teste-') or 'nao usar' in lowered or 'não usar' in lowered:
        return False
    try:
        pages = int(float(row.get('PAGES') or 0))
    except (TypeError, ValueError):
        pages = 0
    return pages > 0


def should_report(color, age):
    return color in {'roxo', 'vermelho'} or (color == 'cinza' and age >= ALERT_AFTER_DAYS)


def render_alert(alerts):
    priority = {'vermelho': 0, 'roxo': 1, 'cinza': 2}
    alerts = sorted(
        alerts,
        key=lambda item: (
            priority.get(item[1].get('color'), 9),
            item[1].get('template') or '',
            int(item[1].get('message_id') or 0),
        ),
    )
    rows = []
    counts = {'cinza': 0, 'roxo': 0, 'vermelho': 0}
    for age, rec in alerts:
        site, config, manager = template_columns(rec['template'])
        message_id = str(rec.get('message_id') or '-')
        color = str(rec.get('color') or '-').upper()
        status = str(rec.get('status') or 'GRAY')
        cta = str(rec.get('cta') or '-').strip()
        counts[rec.get('color')] = counts.get(rec.get('color'), 0) + 1
        rows.append(
            f'{site:<18} | {config:<24} | {manager:<10} | '
            f'{message_id:>4} | {color:<8} | {age:>4} | {status:<14} | {cta}'
        )

    header = 'Template           | Configuração             | Gestor     | ID   | Cor      | Dias | Status         | CTA'
    divider = '-------------------|--------------------------|------------|------|----------|------|----------------|-------------------------'
    lines = [
        'Template/Broadcast — estados acionáveis',
        (
            f'Cinza >= {ALERT_AFTER_DAYS} dias: {counts["cinza"]} | '
            f'Roxo: {counts["roxo"]} | Vermelho: {counts["vermelho"]}'
        ),
        '',
    ]
    # Independent blocks keep Discord's automatic message splitting readable.
    for start in range(0, len(rows), 9):
        lines.extend(['```', header, divider, *rows[start:start + 9], '```', ''])
    lines.append('Política: roxo = diagnóstico; vermelho = elegível à troca red-only; cinza = sem troca automática.')
    return '\n'.join(lines)


async def main():
    state = load_state()
    items = state.setdefault('items', {})
    today = now_et().date()
    p, browser, ctx, page, rows, headers, post_url = await rollout.capture_rows_headers()
    try:
        current_keys = set()
        alerts = []
        for row in rows:
            if not is_active_production_row(row):
                continue
            name = row.get('NAME') or ''
            for msg in rollout.parse_messages(row):
                status = rollout.status_of(msg)
                color = rollout.status_color(status)
                if color not in {'cinza', 'roxo', 'vermelho'}:
                    continue
                k = key_for(name, msg)
                current_keys.add(k)
                rec = items.setdefault(k, {
                    'template': name,
                    'message_id': int(msg.get('MESSAGE_ID') or 0),
                    'first_seen': today.isoformat(),
                    'text': (msg.get('TEXT') or '')[:160],
                    'cta': msg.get('CTA_1') or msg.get('CTA 1') or '',
                    'status': status,
                    'color': color,
                    'alerted': False,
                })
                previous_status = rec.get('status', status)
                if previous_status != status:
                    rec['first_seen'] = today.isoformat()
                    rec['alerted'] = False
                rec.update({
                    'template': name,
                    'message_id': int(msg.get('MESSAGE_ID') or 0),
                    'text': (msg.get('TEXT') or '')[:160],
                    'cta': msg.get('CTA_1') or msg.get('CTA 1') or '',
                    'status': status,
                    'color': color,
                })
                try:
                    age = (today - dt.date.fromisoformat(rec.get('first_seen', today.isoformat()))).days
                except Exception:
                    rec['first_seen'] = today.isoformat(); age = 0
                if should_report(color, age):
                    alerts.append((age, rec))
                    rec['alerted'] = True
                    rec['last_alerted'] = today.isoformat()
        # purge resolved/green keys
        for k in list(items):
            if k not in current_keys:
                items.pop(k, None)
        state['updated_at_et'] = now_et().isoformat(timespec='seconds')
        save_state(state)
        if not alerts:
            return
        print(render_alert(alerts))
    finally:
        try: await browser.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass

if __name__ == '__main__':
    asyncio.run(main())
