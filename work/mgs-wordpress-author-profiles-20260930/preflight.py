#!/usr/bin/env python3
"""Read-only author profile preflight for MGS allowlisted WordPress sites."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path('/root/mgs-agent/work/mgs-wordpress-author-profiles-20260930')
ROOT.mkdir(parents=True, exist_ok=True)
OUT = ROOT / 'preflight.json'
VAULT = 'MGS Conteúdo'
PREFIX = 'Atena WordPress - '


def run(args: list[str], attempts: int = 3) -> bytes:
    last = None
    for attempt in range(1, attempts + 1):
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if p.returncode == 0:
            return p.stdout
        last = p.stderr.decode('utf-8', 'replace')[:500]
        if attempt < attempts:
            time.sleep(attempt * 2)
    raise RuntimeError(f'command failed: {last}')


def op_item(item_id: str) -> dict:
    return json.loads(run(['op', 'item', 'get', item_id, '--vault', VAULT, '--format', 'json', '--reveal']))


def request_json(domain: str, path: str, username: str, password: str) -> tuple[int, object]:
    url = f'https://{domain}{path}'
    token = base64.b64encode(f'{username}:{password}'.encode()).decode()
    req = urllib.request.Request(url, headers={
        'Authorization': f'Basic {token}',
        'Accept': 'application/json',
        'User-Agent': 'MGS-Atena-Author-Preflight/1.0',
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body = json.loads(raw) if raw else None
        except Exception:
            body = {'non_json': raw[:200].decode('utf-8', 'replace')}
        return exc.code, body


def main() -> int:
    allowed = [x.strip() for x in subprocess.check_output(
        ['python3', '/root/mgs-agent/scripts/mgs-domain-scope.py', 'list', '--agent', 'atena'], text=True
    ).splitlines() if x.strip()]
    items = json.loads(run(['op', 'item', 'list', '--vault', VAULT, '--format', 'json']))
    by_title = {x.get('title', '').casefold(): x['id'] for x in items}
    results = []
    failures = []
    for index, domain in enumerate(allowed, 1):
        title = f'{PREFIX}{domain}'
        item_id = by_title.get(title.casefold())
        if not item_id:
            failures.append({'domain': domain, 'stage': 'credential_item', 'error': 'missing'})
            continue
        try:
            raw = op_item(item_id)
            fields = {f.get('id') or f.get('label'): f.get('value', '') for f in raw.get('fields', [])}
            username = fields.get('username', '')
            password = fields.get('wp_app_password', '')
            user_id = int(fields.get('wp_user_id', '0') or 0)
            if username != 'atena' or not password or user_id <= 0 or fields.get('site_domain') != domain:
                raise RuntimeError('credential metadata mismatch')
            own_http, own = request_json(
                domain,
                f'/wp-json/wp/v2/users/{user_id}?context=edit&_fields=id,username,name,description,roles,slug,email,link',
                username,
                password,
            )
            if own_http != 200 or not isinstance(own, dict):
                raise RuntimeError(f'Atena profile HTTP {own_http}')
            query = urllib.parse.urlencode({
                'search': 'Raquel', 'per_page': 100, 'context': 'view',
                '_fields': 'id,slug,name,description,link',
            })
            rq_http, rq_data = request_json(domain, f'/wp-json/wp/v2/users?{query}', username, password)
            candidates = []
            if rq_http == 200 and isinstance(rq_data, list):
                for row in rq_data:
                    searchable = ' '.join(str(row.get(k, '')) for k in ('slug', 'name', 'description')).casefold()
                    if 'raquel' in searchable:
                        candidates.append({
                            'id': row.get('id'), 'slug': row.get('slug'), 'name': row.get('name'),
                            'description': row.get('description'), 'link': row.get('link'),
                        })
            results.append({
                'domain': domain,
                'atena': {
                    'http': own_http, 'id': own.get('id'), 'username': own.get('username'),
                    'name': own.get('name'), 'description': own.get('description'),
                    'roles': own.get('roles'), 'slug': own.get('slug'), 'link': own.get('link'),
                },
                'raquel_public_search': {'http': rq_http, 'candidates': candidates},
            })
            OUT.write_text(json.dumps({'status':'in_progress','expected':len(allowed),'results':results,'failures':failures}, ensure_ascii=False, indent=2)+'\n')
        except Exception as exc:
            failures.append({'domain': domain, 'stage': 'profile_readback', 'error': f'{type(exc).__name__}: {str(exc)[:300]}'})
            OUT.write_text(json.dumps({'status':'in_progress','expected':len(allowed),'results':results,'failures':failures}, ensure_ascii=False, indent=2)+'\n')
        time.sleep(0.15)
    summary = {
        'expected': len(allowed),
        'readback_ok': len(results),
        'failures': len(failures),
        'atena_name_counts': {},
        'atena_empty_bio': sum(not (x['atena'].get('description') or '').strip() for x in results),
        'raquel_candidate_sites': sum(bool(x['raquel_public_search']['candidates']) for x in results),
        'raquel_candidate_records': sum(len(x['raquel_public_search']['candidates']) for x in results),
    }
    for row in results:
        name = row['atena'].get('name') or ''
        summary['atena_name_counts'][name] = summary['atena_name_counts'].get(name, 0) + 1
    payload = {
        'status': 'PASS' if len(results) == len(allowed) and not failures else 'PARTIAL',
        'summary': summary,
        'results': results,
        'failure_details': failures,
        'secret_values_recorded': False,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status':payload['status'],'summary':summary,'failure_details':failures}, ensure_ascii=False, indent=2))
    return 0 if payload['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
