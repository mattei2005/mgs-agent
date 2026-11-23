#!/usr/bin/env python3
"""Frozen-cohort, thirty-day Cloudflare country monitor. Read-only provider access."""
from __future__ import annotations
import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path('/root/mgs-agent')
STORE = ROOT / 'data/portfolio-country-monitor-20261123'
THREAD = '1574415087257780367'
ITEM = 'Cloudflare MGS Admin Token - mattei20052'
spec = importlib.util.spec_from_file_location('country_transport', ROOT/'scripts/monitor-vagaaqui-country.py')
assert spec is not None and spec.loader is not None
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
setattr(base, 'THREAD', THREAD)  # Private instance; the Vagaaqui process is unchanged.
Error = base.MonitorError
iso, parse, save = base.iso, base.parse, base.save
UTC = dt.timezone.utc


def read_config(store):
    c = json.loads((store/'config.json').read_text())
    selection_bytes = (store/'selection.json').read_bytes()
    selection = json.loads(selection_bytes)
    if hashlib.sha256(selection_bytes).hexdigest() != c['selection_sha256']:
        raise Error('selection_integrity_mismatch', True)
    if c['thread_id'] != THREAD or c['credential_item'] != ITEM or c['days'] != 30:
        raise Error('scope_guard_mismatch', True)
    if parse(c['end']) - parse(c['start']) != dt.timedelta(days=30):
        raise Error('duration_guard_mismatch', True)
    if c['sites'] != selection['sites'] or len(c['sites']) != 38:
        raise Error('cohort_guard_mismatch', True)
    allowed = set(json.loads((ROOT/'data/mgs-domain-scope.json').read_text())['domains'])
    seen = set()
    for site in c['sites']:
        domain = site['domain']
        if domain in seen or domain not in allowed or site['baseline_requests'] <= 1000:
            raise Error('site_scope_mismatch', True)
        seen.add(domain)
        if site['credential_item'] != ITEM or not re.fullmatch('[a-f0-9]{32}', site['zone_id']):
            raise Error('zone_scope_mismatch', True)
        for host in site['hosts']:
            canonical = host.removeprefix('www.')
            if canonical not in allowed or not (canonical == domain or canonical.endswith('.'+domain)):
                raise Error('hostname_scope_mismatch', True)
    return c


def intervals(c):
    start = parse(c['start'])
    return [(str(i+1), iso(start+dt.timedelta(days=i)), iso(start+dt.timedelta(days=i+1))) for i in range(30)]


def credential():
    r = subprocess.run([str(ROOT/'scripts/mgs-op-with-service-account.sh'), 'item', 'get', ITEM,
                        '--vault', 'MGS Conteúdo', '--format', 'json'], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise Error('credential_read_failed', True)
    try:
        return next(f['value'] for f in json.loads(r.stdout)['fields'] if f.get('label') == 'token')
    except (KeyError, ValueError, StopIteration):
        raise Error('credential_field_missing', True)


def query_text(site, a, b):
    return ('query {viewer {zones(filter:{zoneTag:'+json.dumps(site['zone_id'])+'}) {'
            'settings {httpRequestsAdaptiveGroups {enabled maxDuration notOlderThan}} '
            'httpRequestsAdaptiveGroups(limit:1000,orderBy:[count_DESC],filter:{datetime_geq:'+json.dumps(a)+
            ',datetime_lt:'+json.dumps(b)+',requestSource:"eyeball",clientRequestHTTPHost_in:'+json.dumps(site['hosts'])+
            '}) {count dimensions {clientCountryName} avg {sampleInterval}}}}}')


def query(token, site, a, b):
    body = json.dumps({'query': query_text(site, a, b)}).encode()
    req = urllib.request.Request('https://api.cloudflare.com/client/v4/graphql', data=body,
                                headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json',
                                         'User-Agent': 'MGS-Zeus-Portfolio-Country/1.0'})
    reason = 'cloudflare_transport_unconfirmed'
    for attempt in range(3):
        retry_after = None
        try:
            with urllib.request.urlopen(req, timeout=35) as r:
                result = json.load(r)
            if result.get('errors'):
                codes = [str((e.get('extensions') or {}).get('code', 'graphql')) for e in result['errors']]
                raise Error('cloudflare_graphql_'+'_'.join(codes), any('auth' in x.lower() for x in codes))
            zones = result['data']['viewer']['zones']
            if len(zones) != 1:
                raise Error('zone_data_unavailable', True)
            settings = zones[0]['settings']['httpRequestsAdaptiveGroups']
            age = (dt.datetime.now(UTC)-parse(a)).total_seconds()
            if not settings['enabled'] or settings['maxDuration'] < (parse(b)-parse(a)).total_seconds():
                raise Error('dataset_duration_unavailable', True)
            if age >= settings['notOlderThan']:
                raise Error('dataset_retention_gap', True)
            rows = zones[0]['httpRequestsAdaptiveGroups']
            for row in rows:
                for value in [row['count'], row['avg']['sampleInterval']]:
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise Error('country_nonfinite_value')
            data = base.normalize(rows, a, b)
            data['settings'] = settings
            data['hosts'] = site['hosts']
            return data
        except urllib.error.HTTPError as e:
            if e.code not in [429, 500, 502, 503, 504]:
                raise Error('cloudflare_http_'+str(e.code), e.code in [401, 403])
            reason = 'cloudflare_http_'+str(e.code)
            header = e.headers.get('Retry-After')
            if header:
                try:
                    retry_after = max(0, float(header))
                except ValueError:
                    from email.utils import parsedate_to_datetime
                    retry_after = max(0, (parsedate_to_datetime(header)-dt.datetime.now(UTC)).total_seconds())
                if retry_after > 10:
                    raise Error(reason+';retry_at='+iso(dt.datetime.now(UTC)+dt.timedelta(seconds=retry_after)))
        except (TimeoutError, OSError) as e:
            reason = 'cloudflare_transport_'+type(e).__name__
        except (KeyError, ValueError, TypeError):
            raise Error('cloudflare_invalid_response')
        if attempt < 2:
            time.sleep(retry_after if retry_after is not None else 2**(attempt+1))
    raise Error(reason)


def state_read(store):
    p = store/'state.json'
    return json.loads(p.read_text()) if p.exists() else {
        'schema': 1, 'status': 'active', 'outbox': {}, 'delivered_days': [], 'failure_streak': 0}


def country_field(site, data):
    rows = sorted(data['countries'].items(), key=lambda x: (-x[1], x[0]))
    lines = []
    for code, count in rows[:10]:
        name = base.NAMES.get(code, code)
        lines.append(f'{name} ({code})' if name != code else code)
        lines[-1] += f": {base.number(count)} · {100*count/data['total'] if data['total'] else 0:.1f}%"
    if len(rows) > 10:
        count = sum(n for _, n in rows[10:])
        lines.append(f'Outros ({len(rows)-10} países/categorias): {base.number(count)} · {100*count/data["total"] if data["total"] else 0:.1f}%')
    if not rows:
        lines = ['Sem requisições retornadas.']
    return {'name': site['domain']+' · '+base.number(data['total'])+' req.', 'value': '\n'.join(lines), 'inline': False}


def payloads(c, kind, key, results, detail):
    titles = {'initial': 'Cloudflare — referência inicial por país',
              'daily': 'Cloudflare — tráfego diário por país', 'final': 'Cloudflare — fechamento dos 30 dias'}
    chunks = [c['sites'][i:i+8] for i in range(0, len(c['sites']), 8)]
    out = []
    total = sum(results[x['domain']]['total'] for x in c['sites'])
    for i, chunk in enumerate(chunks, 1):
        marker = f'CF-PORTFOLIO-20261123:{key}:{i}'
        p = {'content': '', 'allowed_mentions': {'parse': []}, 'embeds': [{
            'title': f'{titles[kind]} · {i}/{len(chunks)}', 'color': 3447003,
            'description': detail+f'\nCobertura: {len(results)}/{len(c["sites"])} domínios. Total: {base.number(total)} requisições estimadas.',
            'fields': [country_field(x, results[x['domain']]) for x in chunk],
            'footer': {'text': marker+' | País pelo IP; inclui bots/arquivos. Não são visitantes. Analytics adaptativo; top10 + outros.'}}],
            'nonce': str(int(hashlib.sha256(marker.encode()).hexdigest()[:15], 16)), 'enforce_nonce': True}
        validate_payload(p)
        out.append((f'{key}:{i}', p))
    return out


def validate_payload(p):
    e = p['embeds'][0]
    assert p['content'] == '' and p['allowed_mentions'] == {'parse': []}
    assert len(e['fields']) <= 25 and all(len(f['value']) <= 1024 and len(f['name']) <= 256 for f in e['fields'])
    assert sum(len(e.get(k, '')) for k in ['title', 'description'])+len(e['footer']['text'])+sum(len(f['name'])+len(f['value']) for f in e['fields']) < 6000


def deliver(s, key, payload, store):
    entry = s['outbox'].get(key)
    if entry and entry.get('verified'):
        return
    if not entry:
        entry = {'payload': payload, 'prepared_at': iso(dt.datetime.now(UTC))}
        s['outbox'][key] = entry
        save(store/'state.json', s)
    p = entry['payload']
    if not entry.get('message_id'):
        marker = p['embeds'][0]['footer']['text']
        before = ''
        matches = []
        # Exhaust the ambiguous POST window, never rely on only the latest 100 messages.
        for _ in range(50):
            messages = base.discord_get('channels/'+THREAD+'/messages?limit=100'+before)
            matches += [m for m in messages if str(m.get('author', {}).get('id')) == '1496296175014252634'
                        and any(e.get('footer', {}).get('text') == marker for e in m.get('embeds', []))]
            if len(messages) < 100 or parse(messages[-1]['timestamp']) < parse(entry['prepared_at'])-dt.timedelta(minutes=1):
                break
            before = '&before='+messages[-1]['id']
        else:
            raise Error('discord_reconciliation_window_not_exhausted', True)
        if len(matches) > 1:
            raise Error('discord_duplicate_marker', True)
        if matches:
            entry['message_id'] = matches[0]['id']
        else:
            r = subprocess.run([sys.executable, str(ROOT/'scripts/discord-bot-post.py'), '--channel-id', THREAD],
                               input=json.dumps(p), capture_output=True, text=True, timeout=45)
            match = re.search(r'message_id=(\d+)', r.stdout)
            if r.returncode or not match:
                raise Error('discord_post_unconfirmed')
            entry['message_id'] = match.group(1)
        save(store/'state.json', s)
    message = base.discord_get('channels/'+THREAD+'/messages/'+entry['message_id'])
    base.verify_message(message, p)
    entry['verified'] = True
    entry['verified_at'] = iso(dt.datetime.now(UTC))
    save(store/'state.json', s)


def collect(c, store, filename, a, b, deadline):
    path = store/filename
    packet = json.loads(path.read_text()) if path.exists() else {'start': a, 'end': b, 'sites': {}}
    if packet['start'] != a or packet['end'] != b:
        raise Error('saved_period_mismatch', True)
    missing = [x for x in c['sites'] if x['domain'] not in packet['sites']]
    token = credential() if missing else None
    for site in missing:
        if time.monotonic() >= deadline:
            return packet, False
        try:
            packet['sites'][site['domain']] = query(token, site, a, b)
        except Error as e:
            raise Error(site['domain']+':'+str(e), e.permanent)
        save(path, packet)
    return packet, True


def aggregate_days(c, store):
    packets = [json.loads((store/f'day-{i:02}.json').read_text()) for i in range(1, 31)]
    return {site['domain']: base.aggregate([p['sites'][site['domain']] for p in packets]) for site in c['sites']}


def run(c, s, store, now, mode='scheduled', deadline=None):
    if s['status'] in ['completed', 'blocked']:
        return {'status': s['status']+'_noop', 'external_requests': 0}
    deadline = deadline if deadline is not None else time.monotonic()+420
    # Resume saved messages before any new collection or publication.
    for key, entry in list(s['outbox'].items()):
        if not entry.get('verified'):
            deliver(s, key, entry['payload'], store)
    if mode in ['preflight', 'activate']:
        a, b = iso(parse(c['start'])-dt.timedelta(days=1)), c['start']
        packet, complete = collect(c, store, 'initial-reference.json', a, b, deadline)
        if not complete:
            return {'status': 'preparation_pending', 'collected_sites': len(packet['sites'])}
        if mode == 'activate':
            detail = f"Referência: {a} → {b} UTC (fora do acumulado).\nMonitor: {c['start']} → {c['end']} UTC; 30 períodos de 24h; grupo fixo do ranking >1.000 req/dia."
            for key, p in payloads(c, 'initial', 'initial', packet['sites'], detail):
                deliver(s, key, p, store)
            s['activation_verified'] = True
            save(store/'state.json', s)
        return {'status': 'activation_verified' if mode == 'activate' else 'preflight_ok', 'sites': len(packet['sites']),
                'countries': len(set(k for data in packet['sites'].values() for k in data['countries']))}
    if not s.get('activation_verified'):
        return {'status': 'activation_required', 'external_requests': 0}
    for day, a, b in intervals(c):
        if day in s['delivered_days'] or parse(b)+dt.timedelta(hours=3) > now:
            continue
        packet, complete = collect(c, store, f'day-{int(day):02}.json', a, b, deadline)
        if not complete:
            return {'status': 'collection_pending', 'day': day, 'collected_sites': len(packet['sites'])}
        detail = f'Dia {day}/30 · {a} → {b} UTC.\nMesmo grupo de 38 domínios e subdomínios do ranking; países por IP, não pessoas.'
        for key, p in payloads(c, 'daily', 'day-'+day, packet['sites'], detail):
            deliver(s, key, p, store)
        s['delivered_days'].append(day)
        save(store/'state.json', s)
        if time.monotonic() >= deadline:
            return {'status': 'catchup_pending', 'delivered_days': len(s['delivered_days'])}
    if len(s['delivered_days']) == 30 and now >= parse(c['end'])+dt.timedelta(hours=3):
        results = aggregate_days(c, store)
        detail = f"{c['start']} → {c['end']} UTC.\nCobertura completa: 30/30 períodos de 24h × 38 domínios, coletados e entregues. Referência inicial excluída. Monitor encerrado."
        for key, p in payloads(c, 'final', 'final', results, detail):
            deliver(s, key, p, store)
        s['status'] = 'completed'
        s['completed_at'] = iso(now)
        save(store/'state.json', s)
    return {'status': s['status'], 'delivered_days': len(s['delivered_days']),
            'verified_messages': sum(bool(e.get('verified')) for e in s['outbox'].values())}


def notice(s, store, key, title, detail, color):
    marker = 'CF-PORTFOLIO-20261123:'+key
    p = {'content': '', 'allowed_mentions': {'parse': []}, 'embeds': [{'title': title, 'description': detail,
         'color': color, 'footer': {'text': marker}}],
         'nonce': str(int(hashlib.sha256(marker.encode()).hexdigest()[:15], 16)), 'enforce_nonce': True}
    deliver(s, key, p, store)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    with (STORE/'writer.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('SKIP writer_busy')
            return 0
        c = read_config(STORE)
        s = state_read(STORE)
        now = dt.datetime.now(UTC)
        # Provider Retry-After is durable and respected by every later consumer.
        if s.get('retry_at') and now < parse(s['retry_at']):
            print(json.dumps({'status': 'cooldown', 'retry_at': s['retry_at']}))
            return 0
        try:
            prior = s.get('failure_streak', 0)
            result = run(c, s, STORE, now, 'preflight' if args.preflight else 'activate' if args.activate else 'scheduled')
            recovered = result['status'] in ['active', 'completed', 'activation_verified', 'preflight_ok']
            if prior and s['status'] != 'blocked' and recovered:
                notice(s, STORE, 'recovery:'+s['incident_id'], 'Cloudflare — monitor recuperado',
                       'Coleta e entregas faltantes retomadas com GET exato, sem repetir períodos já concluídos.', 3066993)
            if s['status'] != 'blocked' and (not prior or recovered):
                s['failure_streak'] = 0
                for k in ['last_error', 'retry_at', 'incident_id']:
                    s.pop(k, None)
            s['last_check'] = iso(now)
            save(STORE/'state.json', s)
            print(json.dumps(result))
            return 0
        except Exception as exc:
            reason = str(exc) if isinstance(exc, Error) else type(exc).__name__
            s['failure_streak'] += 1
            s['last_error'] = reason
            s['last_check'] = iso(now)
            s.setdefault('incident_id', iso(now))
            if ';retry_at=' in reason:
                s['retry_at'] = reason.split(';retry_at=', 1)[1]
            if getattr(exc, 'permanent', False) or s['failure_streak'] >= 5:
                s['status'] = 'blocked'
            s['next_action'] = ('Decisão humana necessária; Zeus mantém a pendência. Sem consultas cegas.' if s['status'] == 'blocked'
                                else 'Consumidor horário retoma apenas coleta/outbox faltante, preservando todos os recibos.')
            save(STORE/'state.json', s)
            try:
                notice(s, STORE, ('blocked:' if s['status'] == 'blocked' else 'failure:')+s['incident_id'],
                       'Cloudflare — monitor com pendência', reason+'\n'+s['next_action']+' Lacunas nunca contam como zero.', 15844367)
            except Exception:
                pass
            print(json.dumps({'status': s['status'], 'error': reason, 'failure_streak': s['failure_streak']}))
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
