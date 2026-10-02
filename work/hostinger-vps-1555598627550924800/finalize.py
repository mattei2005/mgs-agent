#!/usr/bin/env python3
"""Idempotent, credential-safe final receipt for the Zeus Hostinger integration."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import yaml

REPO = Path('/root/mgs-agent')
WORK = REPO / 'work/hostinger-vps-1555598627550924800'
IDENTIFIER = 'hostinger-vps-zeus-1555598627550924800'
REPORT_RECEIPT = WORK / 'report-infra-receipt.json'
CLOSURE = WORK / 'closure-result.json'
NOW = datetime.now(timezone.utc).isoformat(timespec='seconds')


def write_json(path, payload):
    with path.open('w') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def digest(path):
    return subprocess.run(['sha256sum', str(path)], capture_output=True, text=True, check=True).stdout.split()[0]


def inventory_update(record):
    p = REPO / 'data/infra-inventory.json'
    with p.open('r+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        data = json.load(handle)
        data['runtime_artifacts'] = [x for x in data.get('runtime_artifacts', []) if x.get('id') != IDENTIFIER] + [record]
        for row in record['files']:
            path = Path(row['path'])
            if path.parent == REPO / 'scripts':
                data['scripts'] = [x for x in data.get('scripts', []) if x.get('path') != str(path)] + [{'path': str(path), 'size_bytes': path.stat().st_size, 'modified_at': NOW, 'sha256': row['sha256']}]
        policy = REPO / 'data/hostinger-vps-zeus.json'
        data['data_files'] = [x for x in data.get('data_files', []) if x.get('path') != str(policy)] + [{'path': str(policy), 'size_bytes': policy.stat().st_size, 'modified_at': NOW}]
        skills = data.setdefault('skills_hermes', {}).setdefault('zeus', [])
        if not any(x.get('name') == 'hostinger-vps-operations' for x in skills):
            skills.append({'name': 'hostinger-vps-operations', 'category': 'ops', 'skill_md': '/root/.hermes/profiles/zeus/skills/ops/hostinger-vps-operations/SKILL.md'})
        data['_meta']['updated_at'] = NOW
        handle.seek(0)
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n'); handle.truncate(); handle.flush(); os.fsync(handle.fileno())
    readback = json.loads(p.read_text())
    assert next(x for x in readback['runtime_artifacts'] if x.get('id') == IDENTIFIER) == record


def main():
    smoke = json.loads((WORK/'smoke-result.json').read_text())
    standalone = json.loads((WORK/'standalone-probe-result.json').read_text())
    assert smoke['pass'] and standalone['pass']
    assert smoke['batch_mutation_denied'] and smoke['other_vm_override_ineffective']
    assert smoke['vps']['id'] == 1767265
    config = Path('/root/.hermes/profiles/zeus/config.yaml')
    mirror = REPO / 'profiles/zeus-config.yaml'
    assert config.read_bytes() == mirror.read_bytes()
    entry = yaml.safe_load(config.read_text())['mcp_servers']['hostinger-vps']
    assert entry['enabled'] and entry['trust'] == 'untrusted' and not entry['env']
    skill = Path('/root/.hermes/profiles/zeus/skills/ops/hostinger-vps-operations/SKILL.md')
    skill_mirror = REPO / 'profiles/zeus-skills/ops/hostinger-vps-operations/SKILL.md'
    assert skill.read_bytes() == skill_mirror.read_bytes()
    expected = "MCP server 'hostinger-vps' (stdio): registered 3 tool(s)"
    logs = Path('/root/.hermes/profiles/zeus/logs/agent.log').read_text().splitlines()
    live_registration = next(x for x in reversed(logs) if expected in x)
    paths = [REPO/'data/hostinger-vps-zeus.json', REPO/'scripts/hostinger-vps-mcp-launch.py', REPO/'scripts/hostinger-vps-mcp-readonly.mjs', REPO/'scripts/mgs-hostinger-vps-probe.py', config, mirror, skill, skill_mirror, WORK/'smoke-result.json', WORK/'standalone-probe-result.json', Path(__file__), REPO/'reports/hostinger-vps-zeus-integration-1555598627550924800.md', Path('/root/.hermes/profiles/zeus/mcp/hostinger-vps/package-lock.json')]
    files = [{'path': str(p), 'sha256': digest(p)} for p in paths]
    receipt = {'id': IDENTIFIER, 'agent': 'zeus', 'type': 'hostinger_vps_readonly_mcp_integration', 'status': 'validated_pending_report', 'updated_at': NOW, 'authority_message_ids': ['1555597320769372342','1555598627550924800'], 'thread_id': '1555572634228490283', 'hostname': 'srv1767265.hstgr.cloud', 'virtual_machine_id': 1767265, 'allowed_operations': json.loads((REPO/'data/hostinger-vps-zeus.json').read_text())['allowed_operations'], 'scheduled_jobs_changed': False, 'secrets_emitted': False, 'mutating_hostinger_api_calls': 0, 'files': files, 'live_registration': live_registration}
    inventory_update(receipt)
    if not REPORT_RECEIPT.exists():
        report = subprocess.run(['bash', str(REPO/'scripts/send-report-infra-embed.sh'), '--action', 'criada', '--type', 'MCP/config/script/skill/data', '--path', 'Zeus mcp_servers.hostinger-vps; data/hostinger-vps-zeus.json; scripts/hostinger-vps-mcp-{launch.py,readonly.mjs}; scripts/mgs-hostinger-vps-probe.py; skill hostinger-vps-operations', '--reason', 'Rodolfo1555597320769372342 autorizou integração VPS;1555598627550924800 confirmou token salvo no1Password. Consultas ao provedor complementam Linux/SSH.', '--evidence', 'hostinger-api-mcp2.7.0; VM1767265running; cinco GET reais aprovados; reboot/stop/restore/firewall/billing e batch negados; alvo fixo; token somente1Password/memória; gateway registrou3 ferramentas; AdsPower/config anterior preservados; mirrors iguais; nenhum cron alterado. work/hostinger-vps-1555598627550924800/smoke-result.json'], capture_output=True, text=True, timeout=90)
        match = re.search(r'message_id=(\d+)', report.stdout)
        if match:
            write_json(REPORT_RECEIPT, {'message_id': match.group(1), 'helper_exit': report.returncode, 'channel_id': '1498132022634483894'})
        assert report.returncode == 0 and match, 'REPORT-INFRA send did not return a verified message handle'
    saved = json.loads(REPORT_RECEIPT.read_text())
    # Read only the exact sent message; never print the bot credential.
    env = Path('/root/.hermes/profiles/zeus/.env').read_text().splitlines()
    token = next(line.split('=',1)[1].strip().strip('"').strip("'") for line in env if line.startswith('DISCORD_BOT_TOKEN='))
    request = urllib.request.Request(f"https://discord.com/api/v10/channels/{saved['channel_id']}/messages/{saved['message_id']}", headers={'Authorization': 'Bot '+token, 'User-Agent': 'MGS/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        message = json.load(response)
    assert not message['content'] and len(message['embeds']) == 1 and not message.get('mentions')
    assert 'hostinger-vps' in json.dumps(message['embeds'])
    receipt.update(status='completed_validated', report_infra_message_id=saved['message_id'], report_infra_channel_id=saved['channel_id'], report_infra_readback=True)
    inventory_update(receipt)
    write_json(CLOSURE, {**receipt, 'smoke': smoke, 'standalone': standalone, 'closed_at': NOW})
    with (REPO/'logs/events-audit.jsonl').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        handle.write(json.dumps({'timestamp': NOW, 'event': 'hostinger_vps_zeus_integration_completed', 'agent': 'zeus', 'authority_message_ids':receipt['authority_message_ids'], 'thread_id':receipt['thread_id'], 'target':receipt['hostname'], 'status':'completed_validated', 'closure':str(CLOSURE), 'closure_sha256':digest(CLOSURE), 'report_infra_message_id':saved['message_id'], 'report_infra_readback':True, 'scheduled_jobs_changed':False, 'secrets_emitted':False},ensure_ascii=False)+'\n');handle.flush();os.fsync(handle.fileno())
    result = subprocess.run(['python3',str(REPO/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','hostinger-vps-zeus-1555597320769372342','--agent','zeus','--thread-id','1555572634228490283','--objective','Configurar integração Hostinger VPS no Zeus com credencial1Password e operações de consulta seguras','--state','completed','--next-step','Integração validada e disponível; cron/monitor existente não alterado. Consultas diretas pelo probe ou MCP do Zeus.','--source',str(CLOSURE)],capture_output=True,text=True,timeout=30)
    assert result.returncode == 0
    print(json.dumps({'status':'completed_validated','report_infra_message_id':saved['message_id'],'report_infra_readback':True,'inventory_readback':True,'closure':str(CLOSURE),'file_hashes_verified':len(files),'checkpoint_completed':True}))


if __name__ == '__main__':
    main()
