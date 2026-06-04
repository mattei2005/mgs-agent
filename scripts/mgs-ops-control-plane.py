#!/usr/bin/env python3
"""MGS Ops Control Plane v1 — read-only executive collector."""
from __future__ import annotations

import json
import os
import sys
import pathlib
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

BASE = pathlib.Path('/root/mgs-agent')
LOGS = BASE / 'logs'
DATA = BASE / 'data'
PROFILES = pathlib.Path('/root/.hermes/profiles')
EXCLUDED_AGENTS: set[str] = set()
AGENTS = ['zeus', 'atena', 'ares']
SERVICES = ['zeus-gateway.service', 'atena-gateway.service', 'ares-gateway.service', 'mgs-autocommit.service']


def run(cmd: list[str] | str, timeout: int = 20, cwd: str | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {'ok': p.returncode == 0, 'rc': p.returncode, 'out': p.stdout.strip(), 'err': p.stderr.strip()}
    except subprocess.TimeoutExpired as e:
        return {'ok': False, 'rc': 'timeout', 'out': (e.stdout or '').strip() if isinstance(e.stdout, str) else '', 'err': 'timeout'}
    except Exception as e:
        return {'ok': False, 'rc': 'exception', 'out': '', 'err': repr(e)}


def tail(path: pathlib.Path, lines: int = 80) -> list[str]:
    if not path.exists():
        return []
    try:
        data = path.read_text(errors='replace').splitlines()
        return data[-lines:]
    except Exception as e:
        return [f'ERROR reading {path}: {e!r}']


def load_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except Exception as e:
        return {'_error': repr(e)}


def service_status() -> list[dict[str, Any]]:
    rows = []
    for svc in SERVICES:
        active = run(['systemctl', 'is-active', svc])
        show = run(['systemctl', 'show', svc, '--property=ActiveEnterTimestamp,NRestarts,MainPID,MemoryCurrent'])
        props: dict[str, str] = {}
        for line in show['out'].splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                props[k] = v
        rows.append({
            'service': svc.replace('.service', ''),
            'active': active['out'] or active['err'] or str(active['rc']),
            'main_pid': props.get('MainPID', ''),
            'restarts': props.get('NRestarts', ''),
            'since': props.get('ActiveEnterTimestamp', ''),
            'memory': props.get('MemoryCurrent', ''),
        })
    return rows


def failed_units() -> list[str]:
    r = run('systemctl --failed --no-pager --plain | sed -n "2,20p"', timeout=10)
    lines = [x for x in r['out'].splitlines() if x.strip() and not x.startswith('Legend') and 'loaded units listed' not in x]
    return lines[:10]


def disk_status() -> list[str]:
    r = run('df -h / /root | tail -n +2', timeout=10)
    return r['out'].splitlines()


def git_status() -> dict[str, Any]:
    dirty = run(['git', '-C', str(BASE), 'status', '--short'])
    branch = run(['git', '-C', str(BASE), 'rev-parse', '--abbrev-ref', 'HEAD'])
    head = run(['git', '-C', str(BASE), 'rev-parse', '--short', 'HEAD'])
    upstream = run('git -C /root/mgs-agent rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true')
    behind = run('git -C /root/mgs-agent rev-list --left-right --count HEAD...@{u} 2>/dev/null || true')
    recent = run(['git', '-C', str(BASE), 'log', '--oneline', '-5'])
    return {
        'branch': branch['out'],
        'head': head['out'],
        'dirty_lines': dirty['out'].splitlines(),
        'upstream': upstream['out'],
        'ahead_behind': behind['out'],
        'recent': recent['out'].splitlines(),
    }


def cron_status() -> dict[str, Any]:
    crontab = run('crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" || true')
    entries = crontab['out'].splitlines() if crontab['out'] else []
    stale_log = tail(LOGS / 'monitor-cron-stale-logs.log', 80)
    last_stale = next((l for l in reversed(stale_log) if 'cron-stale check:' in l), '')
    m = re.search(r'jobs=(\d+) problems=(\d+) resolved=(\d+) alerts_sent=(\d+)', last_stale)
    return {
        'entries': len(entries),
        'last_stale_check': last_stale,
        'stale_summary': dict(zip(['jobs', 'problems', 'resolved', 'alerts_sent'], m.groups())) if m else {},
    }


def pending_status() -> dict[str, Any]:
    auth = load_json(DATA / 'authorized-users.json') or {}
    pending_approvals = auth.get('pending_approvals', []) if isinstance(auth, dict) else []
    pr_state = load_json(DATA / 'pending-reports-state.json') or {}
    alerted = pr_state.get('alerted', {}) if isinstance(pr_state, dict) else {}
    return {
        'pending_approvals': len(pending_approvals),
        'pending_report_alerted': len(alerted),
    }


def agent_recent_errors(agent: str) -> list[str]:
    if agent in EXCLUDED_AGENTS:
        return []
    lines = tail(PROFILES / agent / 'logs' / 'errors.log', 200)
    patt = re.compile(r'(ERROR|CRITICAL|Traceback|Exception|OperationalError|No space left|failed)', re.I)
    return [l[-240:] for l in lines if patt.search(l)][-8:]


def monitor_summaries() -> dict[str, str]:
    files = [
        'monitor-auto-push.log',
        'monitor-tool-loops.log',
        'monitor-service-restarts.log',
        'check-pending-reports.log',
        'monitor-webshare-status.log',
        'monitor-gpt55-oauth-cost.log',
    ]
    out = {}
    for f in files:
        lines = [l for l in tail(LOGS / f, 50) if l.strip()]
        out[f] = lines[-1] if lines else 'sem log'
    return out


def render(report: dict[str, Any]) -> str:
    def row(a: str, b: str, c: str = '') -> str:
        return f'{a:<28} {b:<18} {c}'

    services = report['services']
    failed = report['failed_units']
    git = report['git']
    cron = report['cron']
    pending = report['pending']

    attention = []
    if failed:
        attention.append(f'{len(failed)} systemd failed unit(s)')
    if git['dirty_lines']:
        attention.append(f'{len(git["dirty_lines"])} arquivo(s) dirty em /root/mgs-agent')
    if int(cron.get('stale_summary', {}).get('problems', 0) or 0) > 0:
        attention.append('cron stale com problema ativo')
    if pending['pending_approvals']:
        attention.append(f'{pending["pending_approvals"]} autorização pendente')
    if pending['pending_report_alerted']:
        attention.append(f'{pending["pending_report_alerted"]} REPORT-INFRA pendente')
    if not attention:
        attention.append('nenhum bloqueio crítico detectado no escopo v1')

    lines: list[str] = []
    lines.append('MGS Ops Control Plane v1')
    lines.append(f'Gerado em: {report["generated_at"]}')
    lines.append('Escopo: Zeus, Atena, Ares, crons, git, infra local.')
    lines.append('')
    lines.append('Atenção executiva')
    lines.append('-' * 72)
    for item in attention:
        lines.append(f'- {item}')
    lines.append('')
    lines.append('Serviços')
    lines.append('-' * 72)
    lines.append(row('Service', 'Estado', 'Restarts / PID'))
    for s in services:
        lines.append(row(s['service'], s['active'], f"restarts={s['restarts']} pid={s['main_pid']}"))
    lines.append('')
    lines.append('Crons')
    lines.append('-' * 72)
    ss = cron.get('stale_summary', {})
    lines.append(row('Entradas root', str(cron['entries']), ''))
    lines.append(row('Stale monitor', f"problems={ss.get('problems','?')}", f"jobs={ss.get('jobs','?')} alerts={ss.get('alerts_sent','?')}"))
    lines.append('')
    lines.append('Pendências')
    lines.append('-' * 72)
    lines.append(row('Autorizações', str(pending['pending_approvals']), 'pending_approvals'))
    lines.append(row('REPORT-INFRA', str(pending['pending_report_alerted']), 'state.alerted'))
    lines.append('')
    lines.append('Git / versionamento')
    lines.append('-' * 72)
    lines.append(row('Branch', git['branch'], f"HEAD={git['head']}"))
    lines.append(row('Upstream', git['upstream'] or 'n/a', git['ahead_behind'] or ''))
    lines.append(row('Dirty tree', str(len(git['dirty_lines'])), 'OK' if not git['dirty_lines'] else 'verificar'))
    lines.append('')
    lines.append('Monitores — último sinal')
    lines.append('-' * 72)
    for name, val in report['monitors'].items():
        lines.append(row(name.replace('.log','')[:27], val[:18], val[18:140]))
    lines.append('')
    lines.append('Erros recentes por agente no escopo')
    lines.append('-' * 72)
    for agent, errs in report['agent_errors'].items():
        lines.append(f'{agent}: {len(errs)} achado(s) relevante(s) no tail de errors.log')
        for e in errs[-3:]:
            lines.append(f'  - {e}')
    lines.append('')
    lines.append('Disco')
    lines.append('-' * 72)
    lines.extend(report['disk'])
    return '\n'.join(lines).rstrip() + '\n'


def build() -> dict[str, Any]:
    return {
        'generated_at': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
        'scope': {'agents': AGENTS, 'excluded_agents': sorted(EXCLUDED_AGENTS)},
        'services': service_status(),
        'failed_units': failed_units(),
        'disk': disk_status(),
        'git': git_status(),
        'cron': cron_status(),
        'pending': pending_status(),
        'monitors': monitor_summaries(),
        'agent_errors': {a: agent_recent_errors(a) for a in AGENTS},
    }


def main() -> int:
    report = build()
    if '--json' in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
