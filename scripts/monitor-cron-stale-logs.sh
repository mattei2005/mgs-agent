#!/usr/bin/env bash
# monitor-cron-stale-logs.sh — Watchdog para detectar crons MGS silenciosos/stale.
#
# Roda via cron a cada 15min. Lê o root crontab, identifica jobs MGS e compara
# mtime do log esperado com uma tolerância por frequência. Alerta no Discord
# (#alerts-infra) quando um job fica velho demais ou sem log.
#
# Modos:
#   --dry-run   imprime avaliação e não grava state nem envia Discord

set -euo pipefail

BASE="/root/mgs-agent"
STATE="${BASE}/data/cron-stale-logs-state.json"
LOG="${BASE}/logs/monitor-cron-stale-logs.log"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

mkdir -p "$(dirname "$STATE")" "$(dirname "$LOG")"

set -a
# shellcheck source=/dev/null
source "${BASE}/.env" 2>/dev/null || true
set +a

python3 - "$STATE" "$DRY_RUN" <<'PY'
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

BASE = Path('/root/mgs-agent')
STATE = Path(sys.argv[1])
DRY_RUN = sys.argv[2] == '1'
NOW = int(time.time())
ANTI_SPAM = 6 * 3600
MENTION = '<@344196393512075265>'

# Jobs intencionalmente silenciosos ou que já têm monitor próprio de semântica.
# Ainda aparecem no CRONS.md; aqui evitamos falso positivo por log vazio/sem output.
SKIP = {
    'monitor-cron-stale-logs.sh',
}

# Logs custom quando o crontab não tem redirect explícito.
CUSTOM_LOG = {}

# Erros semânticos: log fresco não significa cron saudável.
# Manter padrões específicos para evitar falso positivo em mensagens tipo "zero falhas".
SEMANTIC_ERROR_RE = re.compile(
    r'(syntax error|traceback|exception|fatal:|critical|erro crítico|(^|\\b)(error|erro):|error token|command not found|permission denied|no such file or directory)',
    re.I,
)

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False).stdout


def threshold_seconds(schedule: str, script: str = '') -> int:
    minute, hour, dom, mon, dow = schedule.split()
    # Este relatório diário teve a agenda movida entre horários distantes no
    # mesmo ciclo. Preserve dois ciclos completos antes de classificar STALE;
    # o monitor alvo continua validado separadamente por dry-run.
    if script == 'monitor-gpt55-oauth-cost.sh':
        return 48 * 3600
    if script == 'monitor-hermes-memory-capacity.py':
        # Agenda explícita a cada 10 minutos; quatro ciclos de tolerância.
        return 40 * 60
    if (
        script == 'monitor-sb-messenger-token-invalid.py'
        and minute == '12,27,42,57'
        and hour == '*'
    ):
        # Agenda principal explícita 12,27,42,57: tolerância de 75 minutos.
        # O mesmo script também executa retenção diária às 00:05; essa entrada
        # deve seguir a janela diária genérica, não a cadência do monitor.
        return 75 * 60
    if script == 'hermes-news-explainer-watchdog.py':
        # Watchdog por minuto: cinco ciclos sem sinal já indicam perda de proteção.
        return 5 * 60
    # Jobs restritos por dia da semana podem ficar vários dias sem executar.
    # O fallback diário de 30h gerava falso STALE (ex.: terça/sexta). Uma
    # janela semanal completa também cobre a primeira execução após mudança
    # de agenda feita depois do horário daquele dia.
    if dow != '*':
        return 8 * 24 * 3600
    # Mesma proteção para jobs mensais/restritos por dia do mês.
    if dom != '*':
        return 32 * 24 * 3600
    if minute.startswith('*/5'):
        return 20 * 60
    if minute.startswith('*/15'):
        return 60 * 60
    if minute == '0' and hour == '*':
        return 150 * 60
    # Jobs diários podem ter a agenda movida para mais tarde no mesmo dia.
    # 30h gerava falso STALE antes da primeira execução na nova agenda
    # (ex.: 12:47 -> 22:44). 36h mantém uma margem de 12h após o horário
    # diário esperado sem mascarar uma execução perdida por mais de um ciclo.
    return 36 * 3600


def parse_crons():
    out = run(['crontab', '-l'])
    jobs = []
    for line in out.splitlines():
        s = line.strip()
        if not s or s.startswith('#') or '/root/mgs-agent/scripts/' not in s:
            continue
        parts = s.split()
        if len(parts) < 6:
            continue
        schedule = ' '.join(parts[:5])
        command = ' '.join(parts[5:])
        m = re.search(r'/root/mgs-agent/scripts/([^\s]+)', command)
        if not m:
            continue
        script = m.group(1)
        log_m = re.search(r'>>\s*([^\s]+)', command)
        log_path = log_m.group(1) if log_m else CUSTOM_LOG.get(script, '')
        jobs.append({'schedule': schedule, 'script': script, 'command': command, 'log_path': log_path})
    return jobs


def load_state():
    if not STATE.exists():
        return {'alerts': {}, 'last_check': None}
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'alerts': {}, 'last_check': None}


def save_state(state):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, STATE)


def get_webhook():
    cmd = ['op', 'item', 'get', 'Discord Webhook - Alerts Infra Channel', '--vault', 'MGS Conteúdo', '--fields', 'label=webhook_url', '--reveal']
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False).stdout.strip()
    return out if out.startswith('https://') else ''


def post_discord(webhook, payload):
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(webhook, data=data, method='POST', headers={'Content-Type': 'application/json', 'User-Agent': 'Hermes-Agent (MGS cron stale monitor)'})
    urllib.request.urlopen(req, timeout=10).read()


def cron_problem_payload(script, status, detail):
    # Idade do log, thresholds e erro bruto permanecem no state/log local.
    # O alerta público informa somente a falha operacional acionável.
    title = 'Cron com erro no log' if status == 'ERROR' else 'Cron sem log recente'
    return {
        'content': f'{MENTION} alerta de cron {status.lower()}',
        'embeds': [{
            'title': title,
            'color': 15158332,
            'fields': [
                {'name': 'Script', 'value': f'`{script}`', 'inline': True},
                {'name': 'Estado', 'value': status, 'inline': True},
                {'name': 'Ação', 'value': 'Verificar cron, script e log.', 'inline': False},
            ],
        }],
    }


def cron_resolved_payload(script):
    return {
        'content': '',
        'embeds': [{
            'title': 'Cron recuperado',
            'description': f'`{script}` voltou a atualizar log.',
            'color': 3066993,
        }],
    }

state = load_state()
state.setdefault('alerts', {})
problems = []
resolved = []
rows = []

for job in parse_crons():
    script = job['script']
    if script in SKIP:
        rows.append((script, 'SKIP', 'watchdog self-skip'))
        continue
    log_path = job['log_path']
    threshold = threshold_seconds(job['schedule'], script)
    status = 'OK'
    detail = ''
    age = None
    if not log_path:
        # Sem log observável não é falha do cron em si; classifica como skip técnico.
        rows.append((script, 'SKIP', 'sem log observável'))
        continue
    p = Path(log_path)
    if not p.exists():
        status = 'STALE'
        detail = f'log ausente: {log_path}'
    else:
        age = NOW - int(p.stat().st_mtime)
        if age > threshold:
            status = 'STALE'
            detail = f'log age={age//60}min threshold={threshold//60}min path={log_path}'
        else:
            detail = f'age={age//60}min threshold={threshold//60}min'
            try:
                tail_lines = p.read_text(errors='ignore').splitlines()[-120:]
            except Exception as exc:
                tail_lines = [f'WARN: não consegui ler log para scan semântico: {exc}']
            # Avaliar só o trecho posterior ao marcador operacional mais recente.
            # Além de START, aceitar um término saudável explícito: logs extensos podem
            # empurrar o START para fora da janela, deixando um traceback antigo antes
            # de um "OK" final ser classificado incorretamente como erro atual. Monitores
            # de uma linha por execução também usam "status=ok" como fronteira saudável.
            last_boundary = None
            for idx, tline in enumerate(tail_lines):
                is_start = re.search(r'(start|iniciando|===)', tline, re.I)
                is_success = re.search(
                    r'(?:^\[[^\]]+\]\s+(?:OK\b|END\b.*\brc=0\b|[^:]+:\s+DONE\b)|\bstatus=ok\b|["\']status["\']\s*:\s*["\']PASS["\'])',
                    tline,
                    re.I,
                )
                if is_start or is_success:
                    last_boundary = idx
            if last_boundary is not None:
                tail_lines = tail_lines[last_boundary:]
            for line in reversed(tail_lines):
                if SEMANTIC_ERROR_RE.search(line):
                    clean = line.strip()
                    if len(clean) > 700:
                        clean = clean[:697] + '...'
                    status = 'ERROR'
                    detail = f'erro semântico no log: {clean} | age={age//60}min path={log_path}'
                    break
    rows.append((script, status, detail))

# Um mesmo script pode ter várias agendas no root crontab apontando para o
# mesmo log. O monitor só consegue provar o estado compartilhado do script,
# não uma falha independente por agenda. Consolidar antes de consultar/mutar
# state evita quatro alertas idênticos e transições ERROR/RESOLVED conflitantes
# dentro da mesma execução.
priority = {'OK': 0, 'STALE': 1, 'ERROR': 2}
evaluations = {}
for script, status, detail in rows:
    if status == 'SKIP':
        continue
    current = evaluations.get(script)
    if current is None or priority.get(status, -1) > priority.get(current[0], -1):
        evaluations[script] = (status, detail)

for script, (status, detail) in evaluations.items():
    key = script
    if status in ('STALE', 'ERROR'):
        last = int(state['alerts'].get(key, {}).get('last_alert', 0) or 0)
        problems.append((script, status, detail, last))
    elif key in state['alerts']:
        resolved.append((script, state['alerts'][key].get('detail', '')))
        state['alerts'].pop(key, None)

if DRY_RUN:
    for script, status, detail in rows:
        print(f'{script:32} | {status:6} | {detail}')
    print(f'problems={len(problems)} resolved={len(resolved)} dry_run=1')
    raise SystemExit(0)

webhook = ''
alerts_sent = 0
now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(NOW))

for script, status, detail, last in problems:
    if NOW - last < ANTI_SPAM:
        continue
    state['alerts'][script] = {
        'last_alert': NOW,
        'status': status,
        'detail': detail,
        'first_seen': state['alerts'].get(script, {}).get('first_seen', NOW),
    }
    if not webhook:
        webhook = get_webhook()
    if webhook:
        post_discord(webhook, cron_problem_payload(script, status, detail))
        alerts_sent += 1

for script, prev in resolved:
    if not webhook:
        webhook = get_webhook()
    if webhook:
        post_discord(webhook, cron_resolved_payload(script))
        alerts_sent += 1

state['last_check'] = now_iso
save_state(state)
print(f'[{now_iso}] cron-stale check: jobs={len(rows)} problems={len(problems)} resolved={len(resolved)} alerts_sent={alerts_sent}')
PY
