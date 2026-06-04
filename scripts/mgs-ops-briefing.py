#!/usr/bin/env python3
"""Render MGS Ops Control Plane as a compact Discord-safe briefing.

Manual/on-demand only. Does not send to Discord and does not modify services.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from datetime import datetime
from typing import Any

CONTROL_PLANE = pathlib.Path('/root/mgs-agent/scripts/mgs-ops-control-plane.py')
OUT_MD = pathlib.Path('/root/mgs-agent/data/mgs-ops-briefing-latest.md')
OUT_JSON = pathlib.Path('/root/mgs-agent/data/mgs-ops-control-plane-latest.json')


def run_control_plane() -> dict[str, Any]:
    p = subprocess.run([str(CONTROL_PLANE), '--json'], text=True, capture_output=True, timeout=45)
    if p.returncode != 0:
        raise SystemExit(f'control-plane failed rc={p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}')
    data = json.loads(p.stdout)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return data


def status_label(value: str) -> str:
    return 'OK' if value == 'active' else 'ATENÇÃO'


def attention_items(d: dict[str, Any]) -> list[str]:
    items: list[str] = []
    failed = d.get('failed_units') or []
    git = d.get('git') or {}
    cron = d.get('cron') or {}
    pending = d.get('pending') or {}
    stale = (cron.get('stale_summary') or {})

    if failed:
        items.append(f'{len(failed)} unit(s) systemd em failed')
    if git.get('dirty_lines'):
        items.append(f'{len(git["dirty_lines"])} arquivo(s) dirty no repo MGS')
    try:
        if int(stale.get('problems') or 0) > 0:
            items.append(f'{stale.get("problems")} cron(s) com stale problem')
    except Exception:
        pass
    if pending.get('pending_approvals'):
        items.append(f'{pending["pending_approvals"]} autorização pendente')
    if pending.get('pending_report_alerted'):
        items.append(f'{pending["pending_report_alerted"]} REPORT-INFRA pendente')

    # Treat current errors.log tail as observation, not blocker; many entries are historical/tool warnings.
    if not items:
        items.append('nenhum bloqueio crítico detectado')
    return items


def fmt_table(rows: list[tuple[str, str, str]], headers: tuple[str, str, str]) -> str:
    widths = [len(x) for x in headers]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], min(len(str(v)), 42))
    out = []
    out.append(f'{headers[0]:<{widths[0]}}  {headers[1]:<{widths[1]}}  {headers[2]:<{widths[2]}}')
    out.append(f'{"-"*widths[0]}  {"-"*widths[1]}  {"-"*widths[2]}')
    for r in rows:
        vals = [str(v)[:42] for v in r]
        out.append(f'{vals[0]:<{widths[0]}}  {vals[1]:<{widths[1]}}  {vals[2]:<{widths[2]}}')
    return '\n'.join(out)


def render(d: dict[str, Any]) -> str:
    generated = d.get('generated_at') or datetime.now().isoformat(timespec='seconds')
    services = d.get('services') or []
    cron = d.get('cron') or {}
    pending = d.get('pending') or {}
    git = d.get('git') or {}
    disk = d.get('disk') or []
    agent_errors = d.get('agent_errors') or {}

    service_rows = []
    for s in services:
        service_rows.append((
            s.get('service', '?'),
            status_label(s.get('active', '?')),
            f"{s.get('active','?')} | r={s.get('restarts','?')} | pid={s.get('main_pid','?')}",
        ))

    stale = cron.get('stale_summary') or {}
    ops_rows = [
        ('Crons', 'OK' if str(stale.get('problems', '0')) == '0' else 'ATENÇÃO', f"jobs={stale.get('jobs', cron.get('entries','?'))} stale={stale.get('problems','?')}"),
        ('Autorizações', 'OK' if not pending.get('pending_approvals') else 'ATENÇÃO', f"pendentes={pending.get('pending_approvals', '?')}"),
        ('REPORT-INFRA', 'OK' if not pending.get('pending_report_alerted') else 'ATENÇÃO', f"pendentes={pending.get('pending_report_alerted', '?')}"),
        ('Git dirty', 'OK' if not git.get('dirty_lines') else 'ATENÇÃO', f"branch={git.get('branch','?')} head={git.get('head','?')}"),
        ('Disco', 'OK', ' | '.join(disk)[:90] if disk else 'sem dado'),
    ]

    err_rows = []
    for agent in ['zeus', 'atena', 'ares']:
        errs = agent_errors.get(agent) or []
        state = 'OBS' if errs else 'OK'
        err_rows.append((agent, state, f'{len(errs)} achado(s) no tail de errors.log'))

    items = attention_items(d)
    attention = '\n'.join(f'- {x}' for x in items)

    md = f"""**MGS Ops Briefing**
Gerado em: `{generated}`

**Atenção executiva**
{attention}

```text
{fmt_table(service_rows, ('Service', 'Sinal', 'Detalhe'))}
```

```text
{fmt_table(ops_rows, ('Área', 'Sinal', 'Detalhe'))}
```

```text
{fmt_table(err_rows, ('Agente', 'Sinal', 'Observação'))}
```

Arquivos locais:
- `{OUT_MD}`
- `{OUT_JSON}`
""".strip() + '\n'
    return md


def main() -> int:
    d = run_control_plane()
    md = render(d)
    OUT_MD.write_text(md)
    print(md)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
