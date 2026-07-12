#!/usr/bin/env python3
"""Alert templates/broadcast channel when SB Utility messages stay gray for >=2 days.

Live SB is the source of truth. Local state only remembers first_seen/alerted markers.
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


def clip(value, width):
    value = str(value or '').strip()
    return value if len(value) <= width else value[:width - 1] + '…'


def template_columns(template):
    """Split '<site> - <config> - gNNN-d <manager>' for a compact Discord row."""
    match = re.match(r'^(.*?)\s+-\s+(.*?)\s+-\s+g\d+-d\s+(.+)$', template or '')
    if not match:
        return clip(template, 18), '-', '-'
    site, config, manager = match.groups()
    return clip(site, 18), clip(config, 24), clip(manager, 10)


def render_alert(alerts):
    rows = []
    for age, rec in alerts:
        site, config, manager = template_columns(rec['template'])
        message_id = str(rec.get('message_id') or '-')
        cta = clip(rec.get('cta') or '-', 25)
        rows.append(
            f'{site:<18} | {config:<24} | {manager:<10} | '
            f'{message_id:>4} | {age:>4} | {cta}'
        )

    header = 'Template           | Configuração             | Gestor     | ID   | Dias | CTA'
    divider = '-------------------|--------------------------|------------|------|------|-------------------------'
    lines = [
        'Template/Broadcast — cinza persistente',
        f'Mensagens cinza há >= {ALERT_AFTER_DAYS} dias: {len(alerts)}',
        '',
    ]
    # Independent blocks keep Discord's automatic message splitting readable.
    for start in range(0, len(rows), 11):
        lines.extend(['```', header, divider, *rows[start:start + 11], '```', ''])
    lines.append('Ação: sem troca automática; validar com Ciro ou em teste controlado.')
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
            name = row.get('NAME') or ''
            if not name:
                continue
            for msg in rollout.parse_messages(row):
                if rollout.status_of(msg) != '':
                    continue
                k = key_for(name, msg)
                current_keys.add(k)
                rec = items.setdefault(k, {
                    'template': name,
                    'message_id': int(msg.get('MESSAGE_ID') or 0),
                    'first_seen': today.isoformat(),
                    'text': (msg.get('TEXT') or '')[:160],
                    'cta': msg.get('CTA_1') or msg.get('CTA 1') or '',
                    'alerted': False,
                })
                try:
                    age = (today - dt.date.fromisoformat(rec.get('first_seen', today.isoformat()))).days
                except Exception:
                    rec['first_seen'] = today.isoformat(); age = 0
                if age >= ALERT_AFTER_DAYS and not rec.get('alerted'):
                    alerts.append((age, rec))
                    rec['alerted'] = True
                    rec['last_alerted'] = today.isoformat()
        # purge resolved/non-gray keys
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
