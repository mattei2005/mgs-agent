import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import re
import subprocess
import urllib.request

REPO = pathlib.Path('/root/mgs-agent')
WORK = REPO / 'work/finance-cleanup-audit-1555576722907201710'
RESULT = json.loads((WORK / 'deletion-result.json').read_text())
SMOKE = json.loads((WORK / 'smoke-result.json').read_text())
REPORT = REPO / 'reports/finance-cleanup-executed-1555579701227946015.md'
CLOSURE = WORK / 'closure-result.json'
CHECKSUM = WORK / 'closure-result.sha256'
IDENTIFIER = 'finance-cleanup-executed-1555579701227946015'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

assert RESULT['status'] == 'filesystem_completed_validated'
assert RESULT['deleted_count'] == 28 and len(RESULT['deleted']) == 28
assert all(not os.path.lexists(path) for path in RESULT['deleted'])
assert SMOKE['pass'] and SMOKE['authenticated_health'] and SMOKE['financial_writes'] == 0
assert not CLOSURE.exists()
assert REPORT.is_file()

report = subprocess.run(
    [
        'bash',
        str(REPO / 'scripts/send-report-infra-embed.sh'),
        '--action',
        'removida',
        '--type',
        'cleanup/finance-test-staging',
        '--path',
        'apps/finance-system/private:28 candidate/stage do manifesto c9056f83c9571ad5e9f741093e8588d9cd501881fac56c24fe5ef1f86bf19993',
        '--reason',
        'Confirmação crítica Rodolfo1555579701227946015 após alerta de disco.',
        '--evidence',
        '196416 arquivos; 52.91GB efetivos liberados; disco 82.85% para 57.27%; alvo ativo preservado; PostgreSQL/dash/socket ativos com PIDs e controles iguais; browser desktop/mobile OK; zero escrita financeira.',
    ],
    capture_output=True,
    text=True,
    timeout=60,
)
assert report.returncode == 0, report.stderr
match = re.search(r'message_id=(\d+)', report.stdout)
assert match is not None, report.stdout
message_id = match.group(1)

token = next(
    line.split('=', 1)[1].strip().strip('"').strip("'")
    for line in pathlib.Path('/root/.hermes/profiles/zeus/.env').read_text().splitlines()
    if line.startswith('DISCORD_BOT_TOKEN=')
)
request = urllib.request.Request(
    f'https://discord.com/api/v10/channels/1498132022634483894/messages/{message_id}',
    headers={'Authorization': 'Bot ' + token, 'User-Agent': 'MGS/1.0'},
)
with urllib.request.urlopen(request, timeout=20) as response:
    discord_message = json.load(response)
assert not discord_message['content']
assert len(discord_message['embeds']) == 1
assert not discord_message.get('mentions')

closure = {
    **RESULT,
    'status': 'completed_validated',
    'smoke': SMOKE,
    'report_path': str(REPORT),
    'report_infra_message_id': message_id,
    'report_infra_readback': True,
    'governance_errors': [],
    'closed_at': NOW,
}
with CLOSURE.open('w') as handle:
    json.dump(closure, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
    handle.flush()
    os.fsync(handle.fileno())
checksum_output = subprocess.run(['sha256sum', str(CLOSURE)], capture_output=True, text=True, check=True).stdout
closure_sha256 = checksum_output.split()[0]
CHECKSUM.write_text(f'{closure_sha256}  {CLOSURE.name}\n')
subprocess.run(['sha256sum', '-c', CHECKSUM.name], cwd=WORK, check=True)

receipt = {
    'id': IDENTIFIER,
    'type': 'finance-cleanup-execution',
    'authority': '1555579701227946015',
    'status': 'completed_validated',
    'updated_at': NOW,
    'manifest_sha256': RESULT['manifest_sha256'],
    'path': str(CLOSURE),
    'sha256': closure_sha256,
    'report_path': str(REPORT.relative_to(REPO)),
    'report_infra_message_id': message_id,
    'deleted_count': RESULT['deleted_count'],
    'files_removed': RESULT['files_removed'],
    'observed_reclaimed_bytes': RESULT['observed_reclaimed_bytes'],
    'financial_writes': 0,
    'active_candidate_retained': True,
    'production_services_active': True,
}
inventory_path = REPO / 'data/infra-inventory.json'
with inventory_path.open('r+') as handle:
    fcntl.flock(handle, fcntl.LOCK_EX)
    inventory = json.load(handle)
    inventory['runtime_artifacts'] = [
        item for item in inventory['runtime_artifacts'] if item.get('id') != IDENTIFIER
    ] + [receipt]
    inventory['_meta']['updated_at'] = NOW
    handle.seek(0)
    json.dump(inventory, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
    handle.truncate()
    handle.flush()
    os.fsync(handle.fileno())

event = {
    'timestamp': NOW,
    'agent': 'zeus',
    'action': 'finance_cleanup_final_receipt',
    'confirmation_message_id': '1555579701227946015',
    'artifact_id': IDENTIFIER,
    'result_sha256': closure_sha256,
    'report_infra_message_id': message_id,
    'status': 'completed_validated',
}
audit_path = REPO / 'logs/events-audit.jsonl'
with audit_path.open('a') as handle:
    fcntl.flock(handle, fcntl.LOCK_EX)
    handle.write(json.dumps(event, ensure_ascii=False) + '\n')
    handle.flush()
    os.fsync(handle.fileno())

inventory_readback = json.loads(inventory_path.read_text())
assert next(item for item in inventory_readback['runtime_artifacts'] if item.get('id') == IDENTIFIER) == receipt
assert event in [json.loads(line) for line in audit_path.read_text().splitlines()[-20:]]
assert subprocess.run(['sha256sum', '-c', CHECKSUM.name], cwd=WORK, capture_output=True).returncode == 0
assert json.loads(CLOSURE.read_text())['report_infra_readback'] is True
print(json.dumps({
    'closure': 'completed_validated',
    'inventory_audit_readback': True,
    'report_infra_readback': True,
    'message_id': message_id,
    'result_sha256': closure_sha256,
}))
