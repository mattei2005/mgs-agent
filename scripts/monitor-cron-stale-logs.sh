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
export MGS_MONITOR_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE="${CRON_STALE_STATE:-${BASE}/data/cron-stale-logs-state.json}"
LOG="${BASE}/logs/monitor-cron-stale-logs.log"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

mkdir -p "$(dirname "$STATE")" "$(dirname "$LOG")"

# No credential bootstrap here. Direct bot transport loads only its token on delivery.

python3 - "$STATE" "$DRY_RUN" <<'PY'
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

BASE = Path('/root/mgs-agent')
sys.path.insert(0, os.environ['MGS_MONITOR_SCRIPT_DIR'])
from mgs_alert_transport import post_verified, update_verified
from mgs_scheduler_health import native_rows, timer_rows, producer_health
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
CANONICAL_PRODUCER_STATE = {
    'apps/finance-system/finance_media_spend_sync.py': BASE / 'data/finance-media-spend-state.json',
    'apps/finance-system/finance_gam_revenue_sync.py': BASE / 'data/finance-gam-revenue-state.json',
}

CUSTOM_LOG = {
    # Authorized concurrent performance closure: preserve the internal DTR log.
    'dtr-sb-page-health-sync.sh': str(BASE / 'logs/dtr-sb-page-health-sync.log'),
}

# Erros semânticos: log fresco não significa cron saudável.
# Manter padrões específicos para evitar falso positivo em mensagens tipo "zero falhas".
SEMANTIC_ERROR_RE = re.compile(
    r'(syntax error|traceback|exception|fatal:|critical|erro crítico|(^|\b)(error|erro):|error token|command not found|permission denied|no such file or directory)',
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
    if script == 'monitor-runcloud.py' and minute == '13,28,43,58' and hour == '*':
        # RunCloud: four cycles, with 35s stagger and bounded hourly backup scan.
        return 60 * 60
    if script == 'monitor-hermes-memory-capacity.py':
        # Agenda explícita a cada 10 minutos; quatro ciclos de tolerância.
        return 40 * 60
    if (
        script == 'monitor-honcho-health.sh'
        and minute == '54'
        and hour == '2,8,14,20'
    ):
        # Probe a cada seis horas: um ciclo completo mais três horas de margem.
        return 9 * 3600
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
    if minute == '*' and hour == '*':
        # Jobs por minuto: cinco ciclos sem log são suficientes para STALE.
        return 5 * 60
    if minute.startswith('*/5') or minute.endswith('/5'):
        return 20 * 60
    if minute.startswith('*/15') or minute.endswith('/15'):
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
        if not s or s.startswith('#') or str(BASE) + '/' not in s:
            continue
        parts = s.split()
        if len(parts) < 6:
            continue
        schedule = ' '.join(parts[:5])
        command = ' '.join(parts[5:])
        m = re.search(re.escape(str(BASE)) + r'/((?:scripts/|apps/)[^\s;\"\']+\.(?:py|sh))(?=$|[\s\"\'])', command)
        if not m:
            continue
        script = m.group(1).removeprefix('scripts/')
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
            'description': f'`{script}` voltou a ter o sinal monitorado saudável (log/execução/entrega).',
            'color': 3066993,
        }],
    }

state = load_state()
state.setdefault('alerts', {})
state.setdefault('observed_jobs', [])
state.setdefault('missing_log_first_seen', {})
previously_observed = set(state['observed_jobs'])
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
        if script not in previously_observed:
            state['missing_log_first_seen'].setdefault(log_path, NOW)
        first_seen = state['missing_log_first_seen'].get(log_path)
        if first_seen is not None and NOW - int(first_seen) <= threshold:
            # Observações a cada 15min não provam que um job diário já deveria
            # ter executado. Aguarde a janela de sua cadência desde a descoberta.
            # Jobs legados sem timestamp continuam STALE; não reiniciar sua graça.
            status = 'WARMUP'
            detail = f'log ausente; primeira execução age={(NOW-int(first_seen))//60}min threshold={threshold//60}min path={log_path}'
        else:
            status = 'STALE'
            detail = f'log ausente: {log_path}'
    else:
        state['missing_log_first_seen'].pop(log_path, None)
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
                is_json_success = False
                try:
                    parsed_line = json.loads(tline)
                    is_json_success = isinstance(parsed_line, dict) and (
                        parsed_line.get('ok') is True
                        or (
                            script in CANONICAL_PRODUCER_STATE
                            and parsed_line.get('pass') is True
                            and parsed_line.get('status') in ('applied', 'already_applied')
                        )
                    )
                except (json.JSONDecodeError, TypeError):
                    pass
                if is_start or is_success or is_json_success:
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
    if script in CANONICAL_PRODUCER_STATE:
        heartbeat = producer_health(CANONICAL_PRODUCER_STATE[script], NOW, threshold, p.stat().st_mtime if p.exists() else 0)
        if heartbeat is not None:
            status, detail = heartbeat
    rows.append((script, status, detail))

# Um mesmo script pode ter várias agendas no root crontab apontando para o
# mesmo log. O monitor só consegue provar o estado compartilhado do script,
# não uma falha independente por agenda. Consolidar antes de consultar/mutar
# state evita quatro alertas idênticos e transições ERROR/RESOLVED conflitantes
# dentro da mesma execução.
# Isolated overrides default to no native/timer probes unless explicitly enabled.
if 'CRON_STALE_STATE' not in os.environ or os.environ.get('MGS_MONITOR_NATIVE') == '1':
    rows.extend(native_rows(NOW))
    rows.extend(timer_rows())
priority = {'OK': 0, 'WARMUP': 0, 'STALE': 1, 'ERROR': 2}
evaluations = {}
for script, status, detail in rows:
    if status in ('SKIP', 'UNKNOWN'):
        continue
    current = evaluations.get(script)
    if current is None or priority.get(status, -1) > priority.get(current[0], -1):
        evaluations[script] = (status, detail)

for script, (status, detail) in evaluations.items():
    key = script
    if status in ('STALE', 'ERROR'):
        last = int(state['alerts'].get(key, {}).get('last_alert', 0) or 0)
        problems.append((script, status, detail, last))
    elif status == 'OK' and key in state['alerts']:
        resolved.append((script, state['alerts'][key].get('detail', '')))
        # Keep the open alert until recovery delivery is read back.

state['observed_jobs'] = sorted(evaluations)

if DRY_RUN:
    for script, status, detail in rows:
        print(f'{script:32} | {status:6} | {detail}')
    print(f'problems={len(problems)} resolved={len(resolved)} dry_run=1')
    raise SystemExit(0)

alerts_sent = 0
send_errors = []
now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(NOW))
state.setdefault('outbox', {})

# Collapse an undelivered failure that recovered before notification: there is
# no public incident to close. Keep evidence locally without posting a fake green.
healthy = {script for script, (status, _) in evaluations.items() if status == 'OK'}
for key in list(state['outbox']):
    pending = state['outbox'][key]
    if pending.get('kind') == 'problem' and key in healthy and not pending.get('message_id') and not state['alerts'].get(key, {}).get('last_alert'):
        state.setdefault('suppressed_transients', {})[key] = {'recovered_at': now_iso, 'first_seen': pending.get('first_seen')}
        state['outbox'].pop(key)
        state['alerts'].pop(key, None)
        resolved = [(s, d) for s, d in resolved if s != key]
    elif pending.get('kind') == 'problem' and key in healthy and not pending.get('message_id'):
        # Supersede a reminder that was never sent; an earlier public incident
        # still needs its recovery. No stale reminder should reopen it.
        state['outbox'][key] = {'kind': 'resolved', 'first_seen': NOW}

for script, status, detail, last in problems:
    if NOW - last < ANTI_SPAM:
        continue
    state['alerts'].setdefault(script, {'last_alert': 0, 'first_seen': NOW})
    state['alerts'][script].update({'status': status, 'detail': detail})
    state['outbox'].setdefault(script, {'kind': 'problem', 'first_seen': NOW})
for script, prev in resolved:
    state['outbox'].setdefault(script, {'kind': 'resolved', 'first_seen': NOW})

# Recovery cannot overtake a POST whose ID was persisted but GET failed. First
# confirm that delivery, then publish the silent recovery on the next cycle.
for script, pending in list(state['outbox'].items()):
    if pending.get('kind') == 'resolved' and script not in healthy:
        state['outbox'].pop(script)
        continue
    if pending.get('kind') == 'problem':
        current = state['alerts'].get(script, {})
        payload = pending.get('payload') or cron_problem_payload(script, current.get('status', 'ERROR'), current.get('detail', ''))
    else:
        payload = pending.get('payload') or cron_resolved_payload(script)
    # An unchanged existing incident gets a silent status update, not another
    # source message and another model-driven resolver invocation.
    update_id = state['alerts'].get(script, {}).get('message_id') if pending['kind'] == 'problem' and not pending.get('message_id') else None
    if update_id:
        payload['content'] = ''
    payload['allowed_mentions'] = {'parse': [], 'users': ['344196393512075265'] if payload.get('content') else [], 'roles': [], 'replied_user': False}
    if not pending.get('payload'):
        state['delivery_sequence'] = int(state.get('delivery_sequence', 0)) + 1
        payload.update({'nonce': str(pending['first_seen']) + 'cr' + str(state['delivery_sequence']), 'enforce_nonce': True})
        pending['payload'] = payload
    state['last_check'] = now_iso
    save_state(state)
    def created(mid):
        pending['message_id'] = mid
        save_state(state)
    try:
        mid = update_verified(payload, message_id=update_id) if update_id else post_verified(payload, prior_id=pending.get('message_id'), on_created=created)
        if pending['kind'] == 'problem':
            state['alerts'][script].update({'last_alert': NOW, 'message_id': mid})
        else:
            state['alerts'].pop(script, None)
        state['outbox'].pop(script, None)
        alerts_sent += 1
    except Exception as exc:
        pending['last_error'] = type(exc).__name__ + ': ' + str(exc)[:200]
        pending['attempts'] = int(pending.get('attempts', 0)) + 1
        send_errors.append({'script': script, 'error': pending['last_error']})
    save_state(state)
state['last_check'] = now_iso
state['send_errors'] = send_errors
save_state(state)
print(f'[{now_iso}] cron-stale check: jobs={len(rows)} problems={len(problems)} resolved={len(resolved)} alerts_sent={alerts_sent} pending={len(state["outbox"])} delivery_errors={len(send_errors)}')
raise SystemExit(1 if send_errors else 0)
PY
