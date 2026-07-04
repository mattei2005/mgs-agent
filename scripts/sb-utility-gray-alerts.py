#!/usr/bin/env python3
"""Alert templates/broadcast channel when SB Utility messages stay gray for >=2 days.

Live SB is the source of truth. Local state only remembers first_seen/alerted markers.
Cron delivery target is Discord channel 1522487422510694450; stdout is the alert.
"""
import asyncio, datetime as dt, importlib.util, json, pathlib
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
        lines = ['Template/Broadcast — cinza persistente', '', f'Mensagens cinza há >= {ALERT_AFTER_DAYS} dias: {len(alerts)}']
        by_template = {}
        for age, rec in alerts:
            by_template.setdefault(rec['template'], []).append((age, rec))
        for template, vals in list(by_template.items())[:12]:
            lines.append(f'- {template}: {len(vals)} mensagem(ns) cinza')
            for age, rec in vals[:3]:
                lines.append(f'  · #{rec.get("message_id")} há {age} dias — {rec.get("cta","")}')
            if len(vals) > 3:
                lines.append(f'  · +{len(vals)-3} no estado local')
        if len(by_template) > 12:
            lines.append(f'- +{len(by_template)-12} templates no estado local')
        lines.append('')
        lines.append('Ação: não troquei automaticamente. Estado cinza precisa validação/Ciro ou teste controlado.')
        print('\n'.join(lines))
    finally:
        try: await browser.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass

if __name__ == '__main__':
    asyncio.run(main())
