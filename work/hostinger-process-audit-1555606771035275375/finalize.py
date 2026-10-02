#!/usr/bin/env python3
"""Finalize the MCP adoption audit, not the pending native-runtime correction."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path('/root/mgs-agent')
WORK = ROOT/'work/hostinger-process-audit-1555606771035275375'
IDENTIFIER = 'hostinger-process-audit-1555606771035275375'
NOW = datetime.now(timezone.utc).isoformat(timespec='seconds')


def save(path, data):
    with path.open('w') as handle:
        json.dump(data,handle,ensure_ascii=False,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())


def sha(path):
    return subprocess.run(['sha256sum',str(path)],capture_output=True,text=True,check=True).stdout.split()[0]


def main():
    coverage=json.loads((WORK/'coverage-summary.json').read_text())
    classification=json.loads((WORK/'all-scheduled-source-audit.json').read_text())
    assert len(classification)==coverage['unique_scheduled_source_files_inspected']
    assert len({x['path'] for x in classification})==len(classification)
    assert all(x['exists'] for x in classification)
    proof=json.loads((WORK/'native-readonly-compatibility-blocker.json').read_text())
    assert proof['native_execute_request_not_run'] and proof['no_denied_call_retry']
    changed=json.loads((WORK/'skill-readback.json').read_text())
    assert len(changed)==5 and len({x['skill'] for x in changed})==4
    files=[]
    for item in changed:
        src=Path(item['runtime']);mirror=Path(item['mirror']);assert src.read_bytes()==mirror.read_bytes()
        files.extend([{'path':str(src),'sha256':sha(src)},{'path':str(mirror),'sha256':sha(mirror)}])
    report=ROOT/'reports/hostinger-process-audit-1555606771035275375.md'
    for p in [report,WORK/'coverage-summary.json',WORK/'all-scheduled-source-audit.json',WORK/'native-readonly-compatibility-blocker.json',WORK/'safety-invariants.json',Path(__file__)]:files.append({'path':str(p),'sha256':sha(p)})
    marker=WORK/'report-infra-receipt.json'
    if not marker.exists():
        r=subprocess.run(['bash',str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','skill/reference/audit','--path','Zeus skills:hostinger-vps-operations,vps-maintenance-and-backup-governance,log-monitor-discord-alert,hermes-agent-operations(web-tooling); reports/hostinger-process-audit-1555606771035275375.md','--reason','Rodolfo1555606771035275375 pediu auditoria de processos versus MCP e skills. Provider consultas preferir MCP; Linux/DR/apps/schedulers mantidos.','--evidence','51root cron;36Hermes jobs13enabled;10system cron;11periodic;18timers;63sources;vendor64ops21GET;5GET guardados.5files/4skills mirrored. Native execute recusado como write:SDKread_only_hint vs leitorreadOnlyHint;isolatedproof confirmado;sem retry/bypass. Runtime fix aguarda autorização;trust untrusted/config/crons inalterados.'],capture_output=True,text=True,timeout=90)
        match=re.search(r'message_id=(\d+)',r.stdout)
        if match:save(marker,{'message_id':match.group(1),'channel_id':'1498132022634483894','helper_exit':r.returncode})
        assert r.returncode==0 and match,'REPORT send did not return a message handle'
    msg=json.loads(marker.read_text())
    env=Path('/root/.hermes/profiles/zeus/.env').read_text().splitlines()
    token=next(line.split('=',1)[1].strip().strip('"').strip("'") for line in env if line.startswith('DISCORD_BOT_TOKEN='))
    request=urllib.request.Request(f"https://discord.com/api/v10/channels/{msg['channel_id']}/messages/{msg['message_id']}",headers={'Authorization':'Bot '+token,'User-Agent':'MGS/1.0'})
    with urllib.request.urlopen(request,timeout=30) as resp:readback=json.load(resp)
    assert not readback['content'] and len(readback['embeds'])==1 and not readback.get('mentions')
    assert '1555606771035275375' in json.dumps(readback['embeds'])
    receipt={'id':IDENTIFIER,'agent':'zeus','type':'hostinger_mcp_process_routing_audit','status':'audit_skills_completed_native_runtime_blocked','updated_at':NOW,'authority_message_id':'1555606771035275375','thread_id':'1555572634228490283','report_path':str(report),'coverage':coverage,'files':files,'native_call_not_executed':True,'native_fix_authorized':False,'runtime_code_changed':False,'live_config_changed':False,'scheduled_jobs_changed':False,'secrets_emitted':False,'skill_mirrors_equal':True,'report_infra_message_id':msg['message_id'],'report_infra_channel_id':msg['channel_id'],'report_infra_readback':True}
    inventory=ROOT/'data/infra-inventory.json'
    with inventory.open('r+') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX);data=json.load(handle)
        data['runtime_artifacts']=[x for x in data.get('runtime_artifacts',[]) if x.get('id')!=IDENTIFIER]+[receipt]
        data['profile_skill_references']=[x for x in data.get('profile_skill_references',[]) if x.get('id')!=IDENTIFIER]+[{'id':IDENTIFIER,'agent':'zeus','type':'skill_route_update','updated_at':NOW,'files':files[:10],'runtime_versioned_sha_match':True,'report_infra_message_id':msg['message_id'],'report_infra_readback':True}]
        data['_meta']['updated_at']=NOW
        handle.seek(0);json.dump(data,handle,ensure_ascii=False,indent=2);handle.write('\n');handle.truncate();handle.flush();os.fsync(handle.fileno())
    data=json.loads(inventory.read_text());assert next(x for x in data['runtime_artifacts'] if x.get('id')==IDENTIFIER)==receipt
    save(WORK/'closure-result.json',receipt)
    event={'timestamp':NOW,'event':'hostinger_process_routing_audit_completed','agent':'zeus','source_message_id':'1555606771035275375','thread_id':'1555572634228490283','status':receipt['status'],'native_readonly_classification_blocker':True,'native_request_not_run':True,'runtime_fix_authorized':False,'skills_changed':sorted({x['skill'] for x in changed}),'closure':str(WORK/'closure-result.json'),'closure_sha256':sha(WORK/'closure-result.json'),'report_infra_message_id':msg['message_id'],'report_infra_readback':True}
    with (ROOT/'logs/events-audit.jsonl').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX);handle.write(json.dumps(event,ensure_ascii=False)+'\n');handle.flush();os.fsync(handle.fileno())
    cmd=['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id',IDENTIFIER,'--agent','zeus','--thread-id','1555572634228490283','--objective','Auditar processos VPS versus MCP Hostinger e atualizar skills correspondentes sem ampliar poderes críticos','--state','completed','--next-step','Auditoria e4skills concluídas. Correção nativa separada em hostinger-native-sdk-1555606771035275375 aguardando autorização Rodolfo.','--source',str(WORK/'closure-result.json')]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=30);assert r.returncode==0
    print(json.dumps({'status':receipt['status'],'unique_sources':len(classification),'skills':len({x['skill'] for x in changed}),'files_changed':len(changed),'mirror_readback':True,'inventory_readback':True,'report_infra_message_id':msg['message_id'],'report_infra_readback':True,'runtime_fix_pending_authorization':True}))


if __name__=='__main__':
    main()
