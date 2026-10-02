import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

BASE = Path('/root/mgs-agent')
WORK = Path(__file__).parent
SOURCE = '1555602779563753665'
TARGET = 'finance-month-rollover.py'
INCIDENT = 'cron-stale-first-run-' + SOURCE
STATE = BASE / 'data/cron-stale-logs-state.json'
INVENTORY = BASE / 'data/infra-inventory.json'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic(path, data):
    tmp = path.with_name(path.name + '.recovery-' + SOURCE)
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)


def audit(event, **extra):
    with (BASE / 'logs/events-audit.jsonl').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps({'timestamp': NOW, 'agent': 'zeus', 'event': event,
                                 'source_message_id': SOURCE, **extra}, ensure_ascii=False) + '\n')


tests = subprocess.run(['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p',
                        'test_monitor_cron_stale_logs.py', '-v'], cwd=BASE, capture_output=True, text=True, timeout=90)
(WORK / 'tests.txt').write_text(tests.stdout + tests.stderr)
assert tests.returncode == 0 and 'Ran 9 tests' in tests.stderr
assert json.loads((BASE / 'logs/finance-month-rollover.log').read_text().splitlines()[-1]) == {
    'pass': True, 'status': 'not_last_day', 'writes': 0}
cron = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=True).stdout
assert sum(TARGET in line for line in cron.splitlines() if not line.startswith('#')) == 1
assert subprocess.run(['systemctl', 'is-active', 'cron'], capture_output=True, text=True).stdout.strip() == 'active'
with Path('/var/lock/monitor_cron_stale_logs.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    probe = subprocess.run(['bash', str(BASE / 'scripts/monitor-cron-stale-logs.sh'), '--dry-run'],
                           capture_output=True, text=True, timeout=60, check=True)
    (WORK / 'watchdog.txt').write_text(probe.stdout)
    assert any(TARGET in line and '| OK ' in line for line in probe.stdout.splitlines())
    state = json.loads(STATE.read_text())
    old = state['alerts'].get(TARGET)
    if old:
        assert old['status'] == 'STALE' and old['detail'] == 'log ausente: /root/mgs-agent/logs/finance-month-rollover.log'
        state['alerts'].pop(TARGET)
    state['last_manual_resolution'] = {
        'ts': NOW, 'source_message_id': SOURCE, 'script': TARGET, 'removed_alert': bool(old),
        'reason': 'Premature missing-log alert before first daily execution; real scheduled noop writes=0 and watchdog OK verified; no direct Discord resolution post.'}
    atomic(STATE, state)
    assert TARGET not in json.loads(STATE.read_text())['alerts']

record = {'id': INCIDENT, 'type': 'cron_first_execution_false_positive_recovery',
          'status': 'recovered_verified', 'agent': 'zeus', 'updated_at': NOW,
          'source_message_id': SOURCE, 'authority': 'Rodolfo authorized safe failed-alert recovery',
          'root_cause': 'New daily job missing log; two watchdog observations before first scheduled execution classified STALE.',
          'correction': 'Persist new missing-log first-seen and wait existing cadence tolerance; preserve legacy failures and expired grace.',
          'target': TARGET, 'evidence': str(WORK), 'tests_passed': 9,
          'runner_result': {'pass': True, 'status': 'not_last_day', 'writes': 0},
          'financial_writes': 0, 'cron_changed': False, 'credentials_changed': False,
          'report_infra_status': 'pending',
          'rollback': '/root/.hermes/profiles/zeus/cache/scratch/cron-stale-' + SOURCE,
          'hashes': {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (BASE / 'scripts/monitor-cron-stale-logs.sh', BASE / 'tests/test_monitor_cron_stale_logs.py')}}


def inventory_update():
    with Path('/var/lock/infra_discovery.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw = INVENTORY.read_bytes()
        data = json.loads(raw)
        data['runtime_artifacts'] = [record] + [x for x in data['runtime_artifacts'] if x.get('id') != INCIDENT]
        for section in ('scripts', 'data_files'):
            for item in data[section]:
                if item.get('path') in (str(BASE / 'scripts/monitor-cron-stale-logs.sh'), str(STATE)):
                    p = Path(item['path'])
                    item.update(size_bytes=p.stat().st_size,
                                modified_at=datetime.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat())
                    if 'md5' in item:
                        item['md5'] = hashlib.md5(p.read_bytes()).hexdigest()
        data['_meta']['updated_at'] = NOW
        assert INVENTORY.read_bytes() == raw, 'Concurrent inventory write; no overwrite'
        atomic(INVENTORY, data)
        assert next(x for x in json.loads(INVENTORY.read_text())['runtime_artifacts'] if x['id'] == INCIDENT) == record


inventory_update()
audit('CRON_STALE_FIRST_RUN_RECOVERED', **{k: v for k, v in record.items() if k != 'agent'})
args = [str(BASE / 'scripts/send-report-infra-embed.sh'), '--action', 'modificada', '--type', 'script/test/data',
        '--path', 'scripts/monitor-cron-stale-logs.sh; tests/test_monitor_cron_stale_logs.py; data/cron-stale-logs-state.json; data/infra-inventory.json',
        '--reason', 'Falso STALE da virada financeira antes da primeira execução diária; tolerância inicial agora segue a cadência, sem ocultar falhas legadas.',
        '--evidence', 'Cron ativo e stanza única23:04:25ET; runner scheduled not_last_day writes=0; watchdog OK;9testes PASS; state readback sem alerta; origem autorizada1555579357651537931. Sem alterações financeiras/cron/credenciais. Alerta1555602779563753665.']
report = subprocess.run(args, capture_output=True, text=True, timeout=90)
(WORK / 'report-infra-receipt.txt').write_text(report.stdout + report.stderr)
match = re.search(r'message_id=(\d+)', report.stdout)
if report.returncode == 0 and match:
    mid = match.group(1)
    record.update(report_infra_status='posted_readback_pending', report_infra_message_id=mid)
    spec = importlib.util.spec_from_file_location('poster', BASE / 'scripts/discord-bot-post.py')
    assert spec is not None and spec.loader is not None
    poster = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(poster)
    poster.load_env(poster.DEFAULT_ENV)
    try:
        req = urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/' + mid,
              headers={'Authorization': 'Bot ' + os.environ['DISCORD_BOT_TOKEN'], 'User-Agent': 'MGS-Zeus/1.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            message = json.load(response)
        assert message['id'] == mid and message['channel_id'] == '1498132022634483894'
        assert not message['content'] and not message['mentions'] and len(message['embeds']) == 1
        assert message['embeds'][0]['title'] == 'REPORT-INFRA — modificada'
        assert {x['name'] for x in message['embeds'][0]['fields']} >= {'Ação', 'Tipo', 'Path', 'Motivo', 'Evidência'}
        record['report_infra_status'] = 'posted_readback_verified'
    except Exception as exc:
        record['report_infra_readback_error'] = type(exc).__name__
else:
    record.update(report_infra_status='pending_delivery_failed', report_returncode=report.returncode)
inventory_update()
audit('CRON_STALE_FIRST_RUN_REPORT', status=record['report_infra_status'], message_id=record.get('report_infra_message_id'))
atomic(WORK / 'result.json', record)
print(json.dumps({'incident': INCIDENT, 'recovered': True, 'state_alert_absent': TARGET not in json.loads(STATE.read_text())['alerts'],
                  'tests': 9, 'financial_writes': 0, 'report': record['report_infra_status'],
                  'report_message_id': record.get('report_infra_message_id')}, ensure_ascii=False))
