#!/usr/bin/env python3
"""Fifteen-calendar-day RunCloud agent review; no production install/restart."""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent')
STATE = BASE / 'data/runcloud-agent-review-state.json'
ZONE = ZoneInfo('America/New_York')
TARGETS = [
    ('Inc01', '162.55.28.178', '290075', 'vgor2cjdz5lvrkfulf26qmkoya'),
    ('Inc02', '162.55.28.179', '288158', 'zjpjux5pfhq7q2m744wwcokg3e'),
    ('Inc03JBF', '46.4.95.117', '310255', 'syrdb4hzyloo3ue3hcrofbcpcy'),
]
PAYLOAD = r'''import datetime,json,os,pathlib,subprocess

def run(args,timeout=30):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('probe_failed:'+args[0]+':rc='+str(p.returncode))
 return p.stdout.strip()
run(['apt-get','-o','APT::Update::Error-Mode=any','update','-qq'],180)
policy=run(['apt-cache','policy','runcloud-agent'])
fields={}
for line in policy.splitlines():
 if line.strip().startswith(('Installed:','Candidate:')):
  k,v=line.strip().split(':',1);fields[k.lower()]=v.strip()
assert fields.get('installed') not in (None,'(none)') and fields.get('candidate') not in (None,'(none)')
services={}
php_units=[line.split()[0] for line in run(['systemctl','list-units','--type=service','--state=running','--no-legend','--no-pager']).splitlines() if line.split() and line.split()[0].startswith('php') and line.split()[0].endswith('rc-fpm.service')]
assert php_units, 'no_running_runcloud_php_fpm'
for unit in ['runcloud-agent','nginx-rc','mariadb','apache2-rc',*php_units]:
 p=subprocess.run(['systemctl','show',unit,'-p','ActiveState'],capture_output=True,text=True,timeout=10)
 services[unit]=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x).get('ActiveState','unknown')
units={u:run(['systemctl','show',u,'-p','ActiveState','-p','UnitFileState','-p','NextElapseUSecRealtime']) for u in ['runcloud-upgrade.timer','runcloud-upgrade.service']}
print(json.dumps({'host':os.uname().nodename,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),**fields,'services':services,'native_updater':units,'native_definition':run(['systemctl','cat','runcloud-upgrade.timer','runcloud-upgrade.service']),'vendor_repository': 'https://release.runcloud.io' in policy}))
'''


def credential(item_id):
    p = subprocess.run([str(BASE / 'scripts/mgs-op-with-service-account.sh'), 'item', 'get', item_id, '--vault', 'MGS Conteúdo', '--format=json'], capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise RuntimeError('credential_source_unavailable')
    obj = json.loads(p.stdout)
    return {f.get('label', f['id']): f.get('value', '') for f in obj['fields']}


def guest(target):
    name, host, sid, item_id = target
    values = credential(item_id)
    rd, wr = os.pipe()
    try:
        os.write(wr, (values['password'] + '\n').encode())
    finally:
        os.close(wr)
    try:
        p = subprocess.run(['sshpass', '-d', str(rd), 'ssh', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts_mgs', '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no', '-o', 'ConnectTimeout=20', values.get('username', 'zeus') + '@' + host, 'sudo -n python3 -I -'], pass_fds=(rd,), input=PAYLOAD, capture_output=True, text=True, timeout=260)
    finally:
        os.close(rd)
    if p.returncode:
        raise RuntimeError('guest_collection_failed_rc_' + str(p.returncode))
    data = json.loads(p.stdout)
    expected = {'Inc01': 'MatteiInc01', 'Inc02': 'MatteiInc02', 'Inc03JBF': 'MatteiInc03'}[name]
    if data['host'] != expected:
        raise RuntimeError('guest_host_binding_mismatch')
    return data


def provider(targets):
    cooldown = json.loads((BASE / 'data/runcloud-alert-state.json').read_text()).get('api_control', {})
    if cooldown.get('retry_at', 0) > time.time():
        raise RuntimeError('provider_cooldown_preserved')
    token = credential('j6nrnpsscbgcbwla7posxw47jy')['runcloud_api_key_token']
    rows = {}
    for name, host, sid, _ in targets:
        req = urllib.request.Request('https://manage.runcloud.io/api/v3/servers/' + sid, headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'User-Agent': 'MGS-RunCloud-Monitor/1.0'})
        # First 429 terminates the whole provider collection; no per-host retry.
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
        if str(data.get('id')) != sid or data.get('ipAddress') != host:
            raise RuntimeError('provider_host_binding_mismatch')
        rows[name] = {k: data.get(k) for k in ['online', 'connected', 'agentVersion']}
        time.sleep(1.3)
    return rows


def classify(guest_data, api_data):
    if guest_data['installed'] != guest_data['candidate']:
        return 'update_pending_critical_confirmation'
    if not guest_data.get('vendor_repository'):
        return 'vendor_repository_unverified'
    if any(v != 'active' for v in guest_data['services'].values()):
        return 'service_health_failure'
    if not api_data or api_data.get('online') is not True or api_data.get('connected') is not True or api_data.get('agentVersion') != guest_data['installed']:
        return 'provider_integration_unverified'
    return 'current_validated'


def due(state, today):
    return today >= dt.date.fromisoformat(state['next_review_date'])


def collect():
    result = {'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'targets': {}, 'installs': False, 'restarts': False}
    for target in TARGETS:
        name = target[0]
        for attempt in range(2):
            try:
                result['targets'][name] = {'guest': guest(target)}
                break
            except Exception as exc:
                result['targets'][name] = {'status': 'collection_unavailable', 'error_class': type(exc).__name__}
                if attempt == 0:
                    time.sleep(15)
    try:
        api = provider(TARGETS)
    except Exception as exc:
        api = {}
        result['provider_error_class'] = type(exc).__name__
    for name, row in result['targets'].items():
        if 'guest' in row:
            row['provider'] = api.get(name)
            row['status'] = classify(row['guest'], row['provider'])
    result['overall'] = len(result['targets']) == len(TARGETS) and all(x['status'] == 'current_validated' for x in result['targets'].values())
    return result


def atomic(path, data):
    stage = path.with_suffix(path.suffix + '.stage')
    with stage.open('w') as handle:
        os.chmod(stage, 0o600)
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(stage, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check-now', action='store_true', help='Collect without advancing scheduled state')
    args = ap.parse_args()
    lock = Path('/root/.hermes/profiles/zeus/runcloud-agent-review.lock')
    with lock.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        state = json.loads(STATE.read_text())
        today = dt.datetime.now(ZONE).date()
        if state.get('manual_recovery_required') and not args.check_now:
            return 0
        if not args.check_now and not due(state, today):
            return 0
        time.sleep(25 if not args.check_now else 0)
        result = collect()
        folder = Path('/root/.hermes/profiles/zeus/reports/runcloud-agent-reviews')
        folder.mkdir(mode=0o700, exist_ok=True)
        receipt = folder / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
        atomic(receipt, result)
        if not args.check_now:
            if result['overall']:
                next_day = dt.date.fromisoformat(state['next_review_date'])
                while next_day <= today:
                    next_day += dt.timedelta(days=15)
                state['next_review_date'] = next_day.isoformat()
                state['consecutive_failures'] = 0
            else:
                state['consecutive_failures'] = state.get('consecutive_failures', 0) + 1
                # Keep original 15-day cadence; bounded daily recovery probes.
                if state['consecutive_failures'] >= 5:
                    state['manual_recovery_required'] = True
                    state['next_review_date'] = (today + dt.timedelta(days=15)).isoformat()
            state['last_receipt'] = str(receipt)
            state['last_status'] = 'current_validated' if result['overall'] else 'pending_recovery_or_critical_decision'
            atomic(STATE, state)
        print('**Revisão do agente RunCloud**')
        for name, row in result['targets'].items():
            data = row.get('guest', {})
            print('- ' + name + ': ' + data.get('installed', 'versão indisponível') + ' — ' + row['status'])
        if not result['overall']:
            print('Nenhuma instalação/reinício executado. Atualização de /etc ou /usr exige confirmação crítica de Rodolfo; falha de leitura não comprova indisponibilidade do servidor. Evidência: ' + str(receipt))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
