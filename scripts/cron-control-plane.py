#!/usr/bin/env python3
"""cron-control-plane.py — Inventário/status dos crons MGS.

Uso:
  /root/mgs-agent/scripts/cron-control-plane.py --markdown > /root/mgs-agent/docs/CRONS.md
  /root/mgs-agent/scripts/cron-control-plane.py --json

Somente leitura. Não modifica crontab, logs ou estado.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path('/root/mgs-agent')
LOGS = BASE / 'logs'
SCRIPTS = BASE / 'scripts'

DESCRIPTIONS = {
    'cron-control-plane.py': 'Regenera docs/CRONS.md com inventário/status dos crons MGS.',
    'monitor-cron-stale-logs.sh': 'Watchdog que alerta quando logs de crons MGS deixam de atualizar dentro da tolerância esperada.',
    'cron-smoke-test.sh': 'Smoke test manual dos crons MGS seguros; usa dry-run em scripts de risco.',
    'sync-souls.sh': 'Sincroniza SOUL.md, config.yaml e skills MGS dos profiles Hermes para versionamento no repo.',
    'monitor-auto-push.sh': 'Monitora falhas no auto-push Git do /root/mgs-agent e alerta em #mgs-alerts.',
    'monitor-yoast-health-eggbev.sh': 'Monitora saúde Yoast do eggbev: SEO + Readability com baseline, semanal e alerta por degradação.',
    'check-pending-reports.sh': 'Detecta skills MGS sem REPORT-INFRA/inventário e cobra correção no canal Zeus.',
    'monitor-service-restarts.sh': 'Detecta restarts inesperados dos services zeus-gateway, atena-gateway e mgs-autocommit.',
    'monitor-anthropic-cost.sh': 'Calcula custo hipotético GPT-5.5/OAuth dos agentes; OAuth não gera custo real por token.',
    'monitor-tool-loops.sh': 'Detecta loops de tool_calls nas sessões Hermes e alerta infra.',
    'infra-discovery.sh': 'Regenera data/infra-inventory.json a partir do estado real do sistema.',
    'monitor-hermes-updates.sh': 'Verifica updates upstream do Hermes Agent e alerta quando há nova versão.',
    'track-article-cost.sh': 'Calcula custo hipotético por artigo publicado e grava data/article-tracker.db.',
    'cleanup-discord-threads.sh': 'Limpa threads Discord arquivadas antigas nos canais da categoria Agents.',
    'cleanup-zombie-sessions.sh': 'Fecha sessões Hermes zumbis/inativas há mais de 30 minutos.',
    'housekeeping-bak-cleanup.sh': 'Remove arquivos .bak antigos com retenção padrão de 15 dias e reporta resumo.',
    'pendencia-render-md.sh': 'Renderiza docs/PENDENCIAS.md a partir de data/pendencias.db.json.',
    'chat-log.sh': 'Mantém índice Markdown de data/chat-logs/INDEX.md.',
    'sync-codex-oauth.sh': 'Sincroniza tokens OAuth Codex do auth global para profiles Hermes com safety check.',
}

RISK = {
    'cron-control-plane.py': 'baixo: re-renderiza docs/CRONS.md',
    'monitor-cron-stale-logs.sh': 'baixo: read-only + alerta Discord',
    'cron-smoke-test.sh': 'baixo/médio: execução manual controlada',
    'sync-souls.sh': 'baixo',
    'monitor-auto-push.sh': 'baixo',
    'monitor-yoast-health-eggbev.sh': 'baixo',
    'check-pending-reports.sh': 'baixo',
    'monitor-service-restarts.sh': 'baixo',
    'monitor-anthropic-cost.sh': 'baixo',
    'monitor-tool-loops.sh': 'baixo',
    'infra-discovery.sh': 'médio: sobrescreve infra-inventory.json',
    'monitor-hermes-updates.sh': 'baixo',
    'track-article-cost.sh': 'baixo/médio: escreve SQLite local',
    'cleanup-discord-threads.sh': 'alto: deleta threads arquivadas antigas',
    'cleanup-zombie-sessions.sh': 'médio: fecha sessões Hermes inativas',
    'housekeeping-bak-cleanup.sh': 'alto: deleta arquivos .bak antigos',
    'pendencia-render-md.sh': 'baixo: re-renderiza docs/PENDENCIAS.md',
    'chat-log.sh': 'baixo: re-renderiza índice',
    'sync-codex-oauth.sh': 'médio: atualiza auth.json dos profiles',
}

OWNER = {
    'cron-control-plane.py': 'Zeus/Ops',
    'monitor-cron-stale-logs.sh': 'Zeus/Infra',
    'cron-smoke-test.sh': 'Zeus/Ops',
    'monitor-yoast-health-eggbev.sh': 'Atena/Conteúdo',
    'track-article-cost.sh': 'Atena/Conteúdo',
    'pendencia-render-md.sh': 'Zeus/Ops',
    'chat-log.sh': 'Zeus/Ops',
}


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout


def cron_lines() -> list[str]:
    out = run(['crontab', '-l'])
    return [line.rstrip() for line in out.splitlines()]


def parse_cron_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        return None
    parts = stripped.split()
    if len(parts) < 6:
        return None
    schedule = ' '.join(parts[:5])
    command = ' '.join(parts[5:])
    if '/root/mgs-agent/scripts/' not in command:
        return None
    m = re.search(r'/root/mgs-agent/scripts/([^\s]+)', command)
    script_name = m.group(1) if m else ''
    log_match = re.search(r'>>\s*([^\s]+)', command)
    log_path = log_match.group(1) if log_match else ''
    return {
        'schedule': schedule,
        'command': command,
        'script': script_name,
        'script_path': f'/root/mgs-agent/scripts/{script_name}' if script_name else '',
        'log_path': log_path,
        'uses_flock': 'flock -n' in command,
        'owner': OWNER.get(script_name, 'Zeus/Infra'),
        'risk': RISK.get(script_name, 'não classificado'),
        'description': DESCRIPTIONS.get(script_name, 'Sem descrição cadastrada.'),
    }


def stat_info(path: str) -> dict[str, Any]:
    if not path:
        return {'exists': False}
    p = Path(path)
    if not p.exists():
        return {'exists': False}
    st = p.stat()
    return {
        'exists': True,
        'size_bytes': st.st_size,
        'mtime': datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec='seconds'),
    }


def tail_summary(path: str, max_lines: int = 8) -> str:
    if not path or not Path(path).exists() or Path(path).stat().st_size == 0:
        return ''
    out = run(['tail', '-n', str(max_lines), path])
    interesting = []
    for line in out.splitlines():
        if re.search(r'ERROR|FATAL|WARN|ALERT|falha|erro|OK|Conclu|done|synced|RESOLVIDO', line, re.I):
            interesting.append(line.strip())
    return (interesting[-1] if interesting else out.splitlines()[-1].strip())[:220]


def collect() -> dict[str, Any]:
    jobs = []
    for line in cron_lines():
        job = parse_cron_line(line)
        if not job:
            continue
        job['script_stat'] = stat_info(job['script_path'])
        job['log_stat'] = stat_info(job['log_path'])
        job['last_log_signal'] = tail_summary(job['log_path'])
        jobs.append(job)
    return {
        'generated_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        'source': 'root crontab + script/log stat, read-only',
        'count': len(jobs),
        'jobs': jobs,
    }


def md_table(rows: list[list[str]]) -> str:
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    out = []
    for idx, row in enumerate(rows):
        out.append(' | '.join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if idx == 0:
            out.append(' | '.join('-' * widths[i] for i in range(len(widths))))
    return '\n'.join(out)


def render_markdown(data: dict[str, Any]) -> str:
    rows = [['Frequência', 'Script', 'Owner', 'Risco', 'Flock', 'Último log']]
    for j in data['jobs']:
        last = j.get('last_log_signal') or '(sem log útil ainda)'
        rows.append([
            j['schedule'],
            j['script'],
            j['owner'],
            j['risk'],
            'sim' if j['uses_flock'] else 'não',
            last.replace('|', '/'),
        ])

    details = []
    for j in data['jobs']:
        details.append(f"### `{j['script']}`")
        details.append(f"- **Frequência:** `{j['schedule']}`")
        details.append(f"- **Owner:** {j['owner']}")
        details.append(f"- **Risco:** {j['risk']}")
        details.append(f"- **Função:** {j['description']}")
        details.append(f"- **Comando:** `{j['command']}`")
        details.append(f"- **Log:** `{j['log_path'] or 'sem redirect explícito'}`")
        if j['log_stat'].get('exists'):
            details.append(f"- **Último log:** {j['log_stat']['mtime']} ({j['log_stat']['size_bytes']} bytes)")
        else:
            details.append("- **Último log:** arquivo ausente")
        details.append('')

    high = [j for j in data['jobs'] if str(j['risk']).startswith('alto')]
    medium = [j for j in data['jobs'] if str(j['risk']).startswith('médio')]

    return f"""# Crons MGS — Control Plane

Gerado em: `{data['generated_at']}`  
Fonte: `{data['source']}`  
Total MGS ativo no root crontab: **{data['count']}**

## Resumo executivo

```text
{md_table(rows)}
```

## Pontos de atenção

- Alto risco: {', '.join('`'+j['script']+'`' for j in high) if high else 'nenhum'}
- Médio risco: {', '.join('`'+j['script']+'`' for j in medium) if medium else 'nenhum'}
- Crons sem `flock`: {', '.join('`'+j['script']+'`' for j in data['jobs'] if not j['uses_flock']) or 'nenhum'}

## Detalhes por cron

{chr(10).join(details)}
## Comandos úteis

```bash
# Regenerar este documento
/root/mgs-agent/scripts/cron-control-plane.py --markdown > /root/mgs-agent/docs/CRONS.md

# Ver JSON bruto
/root/mgs-agent/scripts/cron-control-plane.py --json | jq .

# Ver root crontab atual
crontab -l
```
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--markdown', action='store_true')
    ap.add_argument('--write-doc', action='store_true', help='Escreve docs/CRONS.md atomicamente')
    args = ap.parse_args()
    data = collect()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.write_doc:
        out = BASE / 'docs' / 'CRONS.md'
        tmp = out.with_suffix('.md.tmp')
        tmp.write_text(render_markdown(data), encoding='utf-8')
        os.replace(tmp, out)
        print(f"OK wrote {out} jobs={data['count']} generated_at={data['generated_at']}")
    else:
        print(render_markdown(data))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
