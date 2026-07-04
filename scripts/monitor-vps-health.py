#!/usr/bin/env python3
"""monitor-vps-health.py — VPS resource/service watchdog for MGS.

Silent on OK. Alerts Discord only on anomaly or recovery.
Default target is the channel/thread requested by Rodolfo on 2026-07-02.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import textwrap
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE = Path('/root/mgs-agent')
STATE_PATH = BASE / 'data' / 'vps-health-state.json'
LOG_PREFIX = 'monitor-vps-health'
DEFAULT_TARGET_CHANNEL_ID = os.environ.get('MGS_VPS_HEALTH_CHANNEL_ID', '1522444367292268565')
MENTION_USER_ID = '344196393512075265'
SERVICES = ['zeus-gateway', 'atena-gateway', 'ares-gateway', 'hera-gateway', 'mgs-autocommit']
ANTI_SPAM_SECONDS = int(os.environ.get('MGS_VPS_HEALTH_ANTI_SPAM_SECONDS', str(6 * 3600)))

THRESHOLDS = {
    'disk_warn_pct': float(os.environ.get('MGS_VPS_DISK_WARN_PCT', '75')),
    'disk_crit_pct': float(os.environ.get('MGS_VPS_DISK_CRIT_PCT', '85')),
    'inode_warn_pct': float(os.environ.get('MGS_VPS_INODE_WARN_PCT', '80')),
    'inode_crit_pct': float(os.environ.get('MGS_VPS_INODE_CRIT_PCT', '90')),
    'mem_warn_mb': float(os.environ.get('MGS_VPS_MEM_WARN_MB', '1536')),
    'mem_crit_mb': float(os.environ.get('MGS_VPS_MEM_CRIT_MB', '750')),
    'load15_warn': float(os.environ.get('MGS_VPS_LOAD15_WARN', '2.0')),
    'load15_crit': float(os.environ.get('MGS_VPS_LOAD15_CRIT', '4.0')),
    'uptime_warn_min': float(os.environ.get('MGS_VPS_UPTIME_WARN_MIN', '15')),
    'backup_warn_gb': float(os.environ.get('MGS_VPS_BACKUP_WARN_GB', '25')),
    'backup_crit_gb': float(os.environ.get('MGS_VPS_BACKUP_CRIT_GB', '35')),
}


def log(msg: str) -> None:
    print(f'[{time.strftime("%Y-%m-%dT%H:%M:%S%z")}] {LOG_PREFIX}: {msg}', flush=True)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors='ignore').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val




def read_cpu_times() -> tuple[int, int]:
    parts = Path('/proc/stat').read_text().splitlines()[0].split()[1:]
    vals = [int(x) for x in parts]
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    total = sum(vals)
    return idle, total


def cpu_usage_percent(interval: float = 0.5) -> float:
    idle1, total1 = read_cpu_times()
    time.sleep(interval)
    idle2, total2 = read_cpu_times()
    total_delta = total2 - total1
    idle_delta = idle2 - idle1
    if total_delta <= 0:
        return 0.0
    return max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0))


def apt_upgradable_count() -> int:
    proc = run(['apt', 'list', '--upgradable'])
    if proc.returncode not in (0,):
        return -1
    return max(0, len([line for line in proc.stdout.splitlines()[1:] if line.strip()]))


def cron_summary_chunks(max_chars: int = 950) -> list[str]:
    proc = run([str(BASE / 'scripts' / 'cron-control-plane.py'), '--json'])
    if proc.returncode != 0:
        return ['Não consegui carregar cron-control-plane.py.']
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return ['Não consegui parsear cron-control-plane.py --json.']
    rows = []
    for job in data.get('jobs', []):
        script = job.get('script', '?')
        schedule = job.get('schedule', '?')
        desc = job.get('description') or 'Sem descrição cadastrada.'
        if len(desc) > 92:
            desc = desc[:89] + '...'
        rows.append(f"{schedule:<17} {script:<39} {desc}")
    chunks: list[str] = []
    cur = ''
    for row in rows:
        add = row + '\n'
        if cur and len(cur) + len(add) > max_chars:
            chunks.append(cur.rstrip())
            cur = ''
        cur += add
    if cur:
        chunks.append(cur.rstrip())
    return chunks or ['Nenhum cron ativo encontrado.']

def read_meminfo() -> dict[str, int]:
    data: dict[str, int] = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, rest = line.split(':', 1)
        value = int(rest.strip().split()[0])  # kB
        data[key] = value
    return data


def path_size_gb(path: Path) -> float:
    if not path.exists():
        return 0.0
    proc = run(['du', '-sx', '--block-size=1', str(path)])
    if proc.returncode != 0:
        return 0.0
    try:
        return int(proc.stdout.split()[0]) / (1024 ** 3)
    except Exception:
        return 0.0


def pct(used: int, total: int) -> float:
    return (used / total * 100.0) if total else 0.0


def severity_for(value: float, warn: float, crit: float, *, higher_bad: bool = True) -> str:
    if higher_bad:
        if value >= crit:
            return 'critical'
        if value >= warn:
            return 'warning'
    else:
        if value <= crit:
            return 'critical'
        if value <= warn:
            return 'warning'
    return 'ok'


def service_state(service: str) -> tuple[str, str, str]:
    active = run(['systemctl', 'is-active', f'{service}.service']).stdout.strip() or 'unknown'
    enabled = run(['systemctl', 'is-enabled', f'{service}.service']).stdout.strip() or 'unknown'
    since = run(['systemctl', 'show', f'{service}.service', '-p', 'ActiveEnterTimestamp', '--value']).stdout.strip()
    return active, enabled, since


def collect() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {'thresholds': THRESHOLDS.copy()}

    cpu_pct = cpu_usage_percent()
    metrics['cpu'] = {'used_pct': round(cpu_pct, 1)}

    updates = apt_upgradable_count()
    metrics['updates'] = {'apt_upgradable_count': updates, 'available': updates > 0 if updates >= 0 else None}

    disk = shutil.disk_usage('/')
    disk_pct = pct(disk.used, disk.total)
    metrics['disk_root'] = {'used_pct': round(disk_pct, 1), 'free_gb': round(disk.free / (1024 ** 3), 1), 'total_gb': round(disk.total / (1024 ** 3), 1)}
    sev = severity_for(disk_pct, THRESHOLDS['disk_warn_pct'], THRESHOLDS['disk_crit_pct'])
    if sev != 'ok':
        issues.append({'key': 'disk_root', 'severity': sev, 'title': 'Disco / alto', 'detail': f"/ usado={disk_pct:.1f}% livre={disk.free/(1024**3):.1f}GB"})

    inode_out = run(['df', '-Pi', '/']).stdout.splitlines()
    if len(inode_out) >= 2:
        parts = inode_out[1].split()
        inode_pct = float(parts[4].rstrip('%'))
        metrics['inode_root'] = {'used_pct': inode_pct, 'free': parts[3]}
        sev = severity_for(inode_pct, THRESHOLDS['inode_warn_pct'], THRESHOLDS['inode_crit_pct'])
        if sev != 'ok':
            issues.append({'key': 'inode_root', 'severity': sev, 'title': 'Inodes / alto', 'detail': f"/ inodes usados={inode_pct:.1f}% livres={parts[3]}"})

    mem = read_meminfo()
    avail_mb = mem.get('MemAvailable', 0) / 1024
    total_mb = mem.get('MemTotal', 0) / 1024
    mem_available_pct = pct(mem.get('MemAvailable', 0), mem.get('MemTotal', 1))
    mem_used_pct = 100.0 - mem_available_pct
    metrics['memory'] = {'available_mb': round(avail_mb), 'total_mb': round(total_mb), 'available_pct': round(mem_available_pct, 1), 'used_pct': round(mem_used_pct, 1)}
    sev = severity_for(avail_mb, THRESHOLDS['mem_warn_mb'], THRESHOLDS['mem_crit_mb'], higher_bad=False)
    if sev != 'ok':
        issues.append({'key': 'memory_available', 'severity': sev, 'title': 'Memória disponível baixa', 'detail': f"MemAvailable={avail_mb:.0f}MB total={total_mb:.0f}MB"})

    load1, load5, load15 = os.getloadavg()
    metrics['load'] = {'load1': round(load1, 2), 'load5': round(load5, 2), 'load15': round(load15, 2)}
    sev = severity_for(load15, THRESHOLDS['load15_warn'], THRESHOLDS['load15_crit'])
    if sev != 'ok':
        issues.append({'key': 'load15', 'severity': sev, 'title': 'Load 15min alto', 'detail': f"load15={load15:.2f} em VPS 2 vCPU"})

    uptime_seconds = float(Path('/proc/uptime').read_text().split()[0])
    uptime_min = uptime_seconds / 60
    metrics['uptime'] = {'minutes': round(uptime_min), 'days': round(uptime_seconds / 86400, 2)}
    if uptime_min < THRESHOLDS['uptime_warn_min']:
        issues.append({'key': 'recent_reboot', 'severity': 'warning', 'title': 'Reboot recente detectado', 'detail': f"uptime={uptime_min:.1f}min"})

    backup_gb = path_size_gb(BASE / 'backups')
    metrics['mgs_backups'] = {'gb': round(backup_gb, 1)}
    sev = severity_for(backup_gb, THRESHOLDS['backup_warn_gb'], THRESHOLDS['backup_crit_gb'])
    if sev != 'ok':
        issues.append({'key': 'mgs_backups_size', 'severity': sev, 'title': 'Backups MGS grandes', 'detail': f"/root/mgs-agent/backups={backup_gb:.1f}GB"})

    services: dict[str, Any] = {}
    for svc in SERVICES:
        active, enabled, since = service_state(svc)
        services[svc] = {'active': active, 'enabled': enabled, 'since': since}
        if active != 'active':
            issues.append({'key': f'service_{svc}', 'severity': 'critical', 'title': 'Service MGS inativo', 'detail': f'{svc}: active={active} enabled={enabled}'})
    metrics['services'] = services

    return issues, metrics


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {'alerts': {}, 'last_check': None, 'last_metrics': {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {'alerts': {}, 'last_check': None, 'last_metrics': {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, STATE_PATH)


def get_bot_token() -> str:
    if os.environ.get('DISCORD_BOT_TOKEN'):
        return os.environ['DISCORD_BOT_TOKEN'].strip()
    vault = os.environ.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')
    cmd = ['op', 'item', 'get', 'Discord Bot - Zeus', '--vault', vault, '--fields', 'label=discord_bot_token', '--reveal']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ''


def post_discord(channel_id: str, payload: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        log('DRY_RUN discord payload title=' + payload.get('embeds', [{}])[0].get('title', 'sem título'))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    token = get_bot_token()
    if not token:
        raise RuntimeError('Discord Bot - Zeus token indisponível')
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f'https://discord.com/api/v10/channels/{channel_id}/messages',
        data=data,
        method='POST',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bot {token}', 'User-Agent': 'MGS-Zeus-VPS-Health/1.0'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f'Discord HTTP {resp.status}')


def build_status_embeds(title: str, color: int, metrics: dict[str, Any], issues: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    updates = metrics.get('updates', {})
    updates_value = 'erro ao checar'
    if updates.get('available') is True:
        updates_value = f"sim — {updates.get('apt_upgradable_count')} pacotes"
    elif updates.get('available') is False:
        updates_value = 'não'

    fields: list[dict[str, Any]] = [
        {'name': 'CPU', 'value': f"{metrics['cpu']['used_pct']}% usado", 'inline': True},
        {'name': 'Memória', 'value': f"{metrics['memory']['used_pct']}% usada / {metrics['memory']['available_mb']}MB livre", 'inline': True},
        {'name': 'Disco /', 'value': f"{metrics['disk_root']['used_pct']}% usado / {metrics['disk_root']['free_gb']}GB livre", 'inline': True},
        {'name': 'Load', 'value': f"1m {metrics['load']['load1']} / 5m {metrics['load']['load5']} / 15m {metrics['load']['load15']}", 'inline': True},
        {'name': 'Inodes /', 'value': f"{metrics['inode_root']['used_pct']}% usado", 'inline': True},
        {'name': 'Atualizações', 'value': updates_value, 'inline': True},
        {'name': 'Backups MGS', 'value': f"{metrics['mgs_backups']['gb']}GB", 'inline': True},
        {'name': 'Uptime', 'value': f"{metrics['uptime']['days']} dias", 'inline': True},
        {'name': 'Services', 'value': ' / '.join(f"{k}:{v['active']}" for k, v in metrics['services'].items())[:1024], 'inline': False},
    ]
    if issues:
        rows = [f"{i['severity'].upper():8} | {i['title']} | {i['detail']}" for i in issues]
        detail = '\n'.join(rows)[:950]
        fields.append({'name': 'Anomalias', 'value': f'```\n{detail}\n```', 'inline': False})
    else:
        fields.append({'name': 'Anomalias', 'value': 'Nenhuma no momento.', 'inline': False})

    # Keep Discord alert compact. Full cron inventory stays in docs/CRONS.md.
    return [{'title': title, 'color': color, 'fields': fields}]


def issue_payload(issues: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    critical = any(i['severity'] == 'critical' for i in issues)
    color = 15158332 if critical else 15844367
    content = f'<@{MENTION_USER_ID}> alerta crítico VPS MGS' if critical else ''
    return {
        'content': content,
        'allowed_mentions': {'users': [MENTION_USER_ID]} if critical else {'parse': []},
        'embeds': build_status_embeds('VPS MGS com anomalia', color, metrics, issues),
    }


def status_payload(metrics: dict[str, Any], issues: list[dict[str, Any]], *, mention: bool = True) -> dict[str, Any]:
    color = 15158332 if any(i['severity'] == 'critical' for i in issues) else (15844367 if issues else 3066993)
    return {
        'content': f'<@{MENTION_USER_ID}> relatório VPS MGS' if mention else '',
        'allowed_mentions': {'users': [MENTION_USER_ID]} if mention else {'parse': []},
        'embeds': build_status_embeds('Relatório VPS MGS', color, metrics, issues),
    }


def resolved_payload(resolved_keys: list[str], metrics: dict[str, Any]) -> dict[str, Any]:
    detail = ', '.join(resolved_keys)[:900]
    return {
        'content': '',
        'allowed_mentions': {'parse': []},
        'embeds': [{
            'title': 'VPS MGS recuperada',
            'color': 3066993,
            'fields': [
                {'name': 'Resolvido', 'value': detail or 'anomalias anteriores', 'inline': False},
                {'name': 'Estado atual', 'value': f"Disco {metrics['disk_root']['used_pct']}% usado; memória {metrics['memory']['available_mb']}MB disponível; load15 {metrics['load']['load15']}", 'inline': False},
            ],
        }],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='do not write state or post Discord')
    ap.add_argument('--force-report', action='store_true', help='send a full status report even when there is no anomaly')
    ap.add_argument('--channel-id', default=DEFAULT_TARGET_CHANNEL_ID)
    args = ap.parse_args()

    load_env_file(BASE / '.env')
    now = int(time.time())
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))
    issues, metrics = collect()
    state = load_state()
    state.setdefault('alerts', {})

    current = {i['key']: i for i in issues}
    previous_keys = set(state.get('alerts', {}).keys())
    current_keys = set(current.keys())
    resolved = sorted(previous_keys - current_keys)

    if args.dry_run:
        log(f'DRY_RUN issues={len(issues)} resolved={len(resolved)} target={args.channel_id}')
        for issue in issues:
            print(f"{issue['severity']:8} | {issue['key']:24} | {issue['detail']}")
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        return 0

    alerts_to_send: list[dict[str, Any]] = []
    for key, issue in current.items():
        prev = state['alerts'].get(key, {})
        last_alert = int(prev.get('last_alert', 0) or 0)
        if now - last_alert >= ANTI_SPAM_SECONDS or prev.get('severity') != issue['severity']:
            alerts_to_send.append(issue)
            state['alerts'][key] = {'first_seen': prev.get('first_seen', now), 'last_alert': now, 'severity': issue['severity'], 'detail': issue['detail']}
        else:
            state['alerts'][key] = {**prev, 'severity': issue['severity'], 'detail': issue['detail']}

    for key in resolved:
        state['alerts'].pop(key, None)

    try:
        if args.force_report:
            post_discord(args.channel_id, status_payload(metrics, issues, mention=True), dry_run=False)
            log(f'FORCE_REPORT sent issues={len(issues)} target={args.channel_id}')
        elif alerts_to_send:
            post_discord(args.channel_id, issue_payload(alerts_to_send, metrics), dry_run=False)
            log(f'ALERT sent issues={len(alerts_to_send)} target={args.channel_id}')
        if resolved:
            post_discord(args.channel_id, resolved_payload(resolved, metrics), dry_run=False)
            log(f'RESOLVED sent count={len(resolved)} target={args.channel_id}')
    except Exception as exc:
        # State is still saved below to avoid alert loops when Discord/1P has a temporary issue.
        log(f'ERROR discord_send_failed: {type(exc).__name__}: {exc}')
        state.setdefault('failed_sends', []).append({'ts': now_iso, 'error': f'{type(exc).__name__}: {exc}', 'issues': [i['key'] for i in alerts_to_send], 'resolved': resolved})

    state['last_check'] = now_iso
    state['last_metrics'] = metrics
    save_state(state)
    log(f'DONE status={"alert" if issues else "ok"} issues={len(issues)} resolved={len(resolved)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
