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
    'check-pending-reports.sh': 'Detecta skills MGS sem REPORT-INFRA/inventário e cobra correção no #alerts-infra.',
    'monitor-service-restarts.sh': 'Detecta restarts inesperados dos services zeus-gateway, atena-gateway, ares-gateway e mgs-autocommit.',
    'monitor-gpt55-oauth-cost.sh': 'Calcula uso hipotético GPT-5.5/OAuth dos agentes; OAuth não gera custo real por token.',
    'monitor-tool-loops.sh': 'Detecta loops de tool_calls nas sessões Hermes e alerta infra.',
    'infra-discovery.sh': 'Regenera data/infra-inventory.json a partir do estado real do sistema.',
    'monitor-hermes-updates.sh': 'Verifica updates upstream do Hermes Agent e alerta quando há nova versão.',
    'track-article-cost.sh': 'Calcula custo hipotético por artigo publicado e grava data/article-tracker.db.',
    'cleanup-discord-threads.sh': 'Limpa threads Discord arquivadas antigas nos canais da categoria Agents.',
    'cleanup-zombie-sessions.sh': 'Fecha sessões Hermes zumbis/inativas usando última atividade real, com grace padrão de 180 minutos.',
    'housekeeping-bak-cleanup.sh': 'Remove backups antigos (.bak/.backup/.old/.orig/~) com retenção padrão de 15 dias, preservando sempre o último por família.',
    'mgs-safety-backup.sh': 'Cria snapshot operacional seguro no máximo a cada 3 dias, exclui segredos conhecidos e mantém somente o snapshot validado mais recente.',
    'hermes-context-cost-audit.py': 'Audita diariamente o orçamento fixo, contexto estimado e uso/custo cumulativo recente dos profiles Zeus, Atena e Ares, sem chamada de modelo.',
    'pendencia-render-md.sh': 'Renderiza docs/PENDENCIAS.md a partir de data/pendencias.db.json.',
    'chat-log.sh': 'Mantém índice Markdown de data/chat-logs/INDEX.md.',
    'sync-codex-oauth.sh': 'Sincroniza tokens OAuth Codex do auth global para profiles Hermes com safety check.',
    'hermes-news-explainer.py': 'Lê anúncios no canal Hermes News e posta explicação executiva do Zeus em PT-BR, com estado anti-duplicata.',
    'hermes-news-explainer-watchdog.py': 'Confere diretamente no Discord se cada anúncio recebeu explicação; reconcilia state inconsistente e recupera órfãos com readback e fallback antes do SLA de 10 minutos.',
    'monitor-webshare-status.sh': 'Monitora status.webshare.io e alerta infra quando detectar manutenção/incidente relevante.',
    'monitor-discord-thread-archive-warnings.py': 'Monitora threads Discord ativas com auto-archive de 1 semana em Zeus/Atena/Ares e posta keepalive quando faltam até 24h para ficarem ocultas.',
    'monitor-vps-health.py': 'Monitora saúde bruta da VPS: disco, inodes, memória disponível, load, reboot recente, tamanho de backups e services MGS ativos.',
    'monitor-op-rate-limit.py': 'Monitora limites horário e diário do 1Password Business e alerta o canal dedicado em 50%/90%.',
    'monitor-hermes-memory-capacity.py': 'Compacta USER/MEMORY automaticamente de >=90% para <=85% com backup, validação semântica, rollback/readback e alerta metadata-only em #limites-90.',
    'sync-sb-sms-revenue-daily.sh': 'Às 08:00 ET, importa no WordPress a receita líquida SMS do dia anterior fechado na Smart Bidding, com upsert/readback e uma retentativa automática após 5 minutos para falhas transitórias.',
    'sync-sb-messenger-revenue-sheet.py': 'Atualiza diariamente a coluna RECEITA 7 DIAS da aba Migracao 22/06 com o Messenger Daily ao vivo, por Segurador, usando a Service Account canônica e readback exato.',
    'monitor-sb-messenger-token-invalid.py': 'Espelha alertas de token Messenger inválido da API Smart Bidding para o canal dedicado, com filtro MGS, dedupe, contagem de páginas e readback Discord sem menções.',
    'ares-meta-account-activity-monitor.py': 'Monitora alterações materiais na conta Meta Creditoparaveiculo 13 e alerta somente ações de outra pessoa ou ferramenta externa; automações da Meta e writes do Ares identificados por audit ou fonte allowlisted ficam silenciosos.',
    'eggbev-page-restriction-guardrail.sh': 'Executa o guardrail Eggbev de restrição DTR a cada cinco minutos. A antiga etapa de campanha com gasto acima de US$2 e zero resultado de pixel está suspensa, removida do wrapper e sem write.',
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
    'monitor-gpt55-oauth-cost.sh': 'baixo',
    'monitor-tool-loops.sh': 'baixo',
    'infra-discovery.sh': 'médio: sobrescreve infra-inventory.json',
    'monitor-hermes-updates.sh': 'baixo',
    'track-article-cost.sh': 'baixo/médio: escreve SQLite local',
    'cleanup-discord-threads.sh': 'alto: deleta threads arquivadas antigas',
    'cleanup-zombie-sessions.sh': 'médio: fecha sessões Hermes inativas',
    'housekeeping-bak-cleanup.sh': 'alto: deleta backups antigos, preservando último por família',
    'mgs-safety-backup.sh': 'alto: cria snapshot e remove automaticamente safety backups além do mais recente',
    'hermes-context-cost-audit.py': 'baixo: leitura local + escrita atômica de estado agregado sem conteúdo das conversas',
    'pendencia-render-md.sh': 'baixo: re-renderiza docs/PENDENCIAS.md',
    'chat-log.sh': 'baixo: re-renderiza índice',
    'sync-codex-oauth.sh': 'médio: atualiza auth.json dos profiles',
    'hermes-news-explainer.py': 'baixo/médio: consulta Discord e pode postar explicação automática',
    'hermes-news-explainer-watchdog.py': 'baixo/médio: consulta Discord a cada minuto e só posta ao recuperar explicação órfã',
    'monitor-webshare-status.sh': 'baixo: consulta status público + alerta Discord se anomalia',
    'monitor-discord-thread-archive-warnings.py': 'baixo: consulta Discord + keepalive automático antes de auto-archive',
    'monitor-vps-health.py': 'baixo: read-only + alerta Discord em anomalia da VPS',
    'monitor-op-rate-limit.py': 'baixo: consulta read-only + alerta Discord por transição',
    'monitor-hermes-memory-capacity.py': 'médio: reescreve USER/MEMORY somente após gates fail-closed e backup protegido',
    'sync-sb-sms-revenue-daily.sh': 'médio/alto: lê SB autenticada e escreve receita diária no WordPress com transação/readback',
    'sync-sb-messenger-revenue-sheet.py': 'médio: lê SB autenticada e substitui a coluna C da planilha com backup, canário, rollback e readback',
    'monitor-sb-messenger-token-invalid.py': 'baixo/médio: lê SB autenticada ao vivo; estado local só faz cursor/dedupe, sem replay; envia apenas notificações novas/reabertas',
    'ares-meta-account-activity-monitor.py': 'baixo: leitura Meta account-wide + estado local; Discord somente quando detectar alteração material de outra pessoa ou ferramenta externa',
    'eggbev-page-restriction-guardrail.sh': 'alto controlado: pode pausar campanhas após pre-read, política e GET/readback',
}

OWNER = {
    'cron-control-plane.py': 'Zeus/Ops',
    'monitor-cron-stale-logs.sh': 'Zeus/Infra',
    'cron-smoke-test.sh': 'Zeus/Ops',
    'monitor-yoast-health-eggbev.sh': 'Atena/Conteúdo',
    'track-article-cost.sh': 'Atena/Conteúdo',
    'pendencia-render-md.sh': 'Zeus/Ops',
    'chat-log.sh': 'Zeus/Ops',
    'monitor-op-rate-limit.py': 'Zeus/Infra',
    'monitor-hermes-memory-capacity.py': 'Zeus/Infra',
    'hermes-context-cost-audit.py': 'Zeus/Infra',
    'sync-sb-sms-revenue-daily.sh': 'Zeus/Revenue Tech',
    'sync-sb-messenger-revenue-sheet.py': 'Zeus/Revenue Tech',
    'monitor-sb-messenger-token-invalid.py': 'Zeus/Revenue Tech',
    'ares-meta-account-activity-monitor.py': 'Ares/Campaign Ops',
    'eggbev-page-restriction-guardrail.sh': 'Ares/Campaign Ops',
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
    mgs_match = re.search(r'(/root/mgs-agent/scripts/([^\s]+))', command)
    profile_match = re.search(r'(/root/\.hermes/profiles/[^/]+/scripts/([^\s]+))', command)
    match = mgs_match or profile_match
    if not match:
        return None
    script_path = match.group(1)
    script_name = match.group(2)
    log_match = re.search(r'>>\s*([^\s]+)', command)
    log_path = log_match.group(1) if log_match else ''
    retention_mode = '--cleanup-old-messages' in command
    owner = OWNER.get(script_name, 'Zeus/Infra')
    risk = RISK.get(script_name, 'não classificado')
    description = DESCRIPTIONS.get(script_name, 'Sem descrição cadastrada.')
    if retention_mode:
        risk = 'médio: exclusão limitada de mensagens Discord anteriores ao dia anterior, com readback'
        description = 'Executa retenção diária dos alertas Token Messenger inválido; preserva o dia atual, o dia anterior e mensagens não relacionadas.'
    elif script_name == 'monitor-sb-messenger-token-invalid.py':
        description = 'Consulta a API SB ao vivo e envia somente notificações novas ou reabertas; estado local nunca origina republicação.'
    return {
        'schedule': schedule,
        'command': command,
        'script': script_name,
        'script_path': script_path,
        'log_path': log_path,
        'uses_flock': 'flock -n' in command,
        'owner': owner,
        'risk': risk,
        'description': description,
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


def collect_external_system_crons() -> list[dict[str, Any]]:
    """Known non-root-crontab system cron jobs relevant to MGS operations."""
    jobs: list[dict[str, Any]] = []
    monarx = Path('/etc/cron.d/monarx-update')
    if monarx.exists():
        for line in monarx.read_text(errors='replace').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            parts = stripped.split()
            if len(parts) >= 7 and 'monarx' in stripped:
                jobs.append({
                    'source_file': str(monarx),
                    'schedule': ' '.join(parts[:5]),
                    'user': parts[5],
                    'command': ' '.join(parts[6:]),
                    'owner': 'Host/security infra',
                    'risk': 'médio: apt update/install externo pode acionar needrestart/systemd',
                    'description': 'Atualiza Monarx security scanner/protect; janela conhecida terça 04:20 EDT.',
                    'guardrail': '/etc/needrestart/conf.d/mgs-hermes-gateways.conf exclui Zeus/Atena/Ares de auto-restart por needrestart.',
                })
    return jobs


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
        'external_system_crons': collect_external_system_crons(),
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

    external_details = []
    for j in data.get('external_system_crons', []):
        external_details.append(f"### `{j['source_file']}`")
        external_details.append(f"- **Frequência:** `{j['schedule']}`")
        external_details.append(f"- **Usuário:** `{j['user']}`")
        external_details.append(f"- **Owner:** {j['owner']}")
        external_details.append(f"- **Risco:** {j['risk']}")
        external_details.append(f"- **Função:** {j['description']}")
        external_details.append(f"- **Comando:** `{j['command']}`")
        external_details.append(f"- **Guardrail:** {j['guardrail']}")
        external_details.append('')
    external_section = ''
    if external_details:
        external_section = f"""
## Crons externos / sistema

{chr(10).join(external_details)}"""

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
{external_section}
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
