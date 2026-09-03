#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
BACKUP=Path('/root/mgs-agent/backups/meta-app-b0072-to-b0073-cutover-20260903-115111'); BACKUP.mkdir(parents=True,exist_ok=False)
files={
'meta-app-registry.json.before':Path('/root/mgs-agent/data/meta-app-registry.json'),
'meta-app-role-monitor-state.json.before':Path('/root/mgs-agent/data/meta-app-role-monitor-state.json'),
'meta-app-role-identity-baseline.json.before':Path('/root/mgs-agent/data/meta-app-role-identity-baseline.json'),
'meta-app-role-alert-pause.json.before':Path('/root/mgs-agent/data/meta-app-role-alert-pause.json'),
'agent-checkpoints.json.before':Path('/root/mgs-agent/data/agent-checkpoints.json'),
'knowledge-registry.json.before':Path('/root/mgs-agent/data/knowledge-registry.json'),
'infra-inventory.json.before':Path('/root/mgs-agent/data/infra-inventory.json'),
'route-pack-05.runtime.before':Path('/root/.hermes/profiles/zeus/skills/growth/meta-app-rate-limit-monitor/references/route-pack-05.md'),
'route-pack-05.mirror.before':Path('/root/mgs-agent/profiles/zeus-skills/growth/meta-app-rate-limit-monitor/references/route-pack-05.md'),
'meta-app-roles-watch.sh.before':Path('/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh')}
for dst,src in files.items(): assert src.exists(); shutil.copy2(src,BACKUP/dst)
reg=json.loads(files['meta-app-registry.json.before'].read_text(encoding='utf-8')); hits=[x for x in reg['apps'] if x.get('app')=='B007-2']; assert len(hits)==1; assert not any(x.get('app')=='B007-3' for x in reg['apps'])
hits[0].update({'app':'B007-3','channel_id':'1520510823426949313','channel_name':'b007-app-status','admin':'Max Tin Masela','onepassword_item_title':'BOT B007-3 Token - Max Tin Masela','expected_sheet_roles':20})
reg.update({'updated_by':'zeus','authorized_by':'Rodolfo Mattei','source_message_id':'OOB-B0073-after-1545088764530008135'})
(BACKUP/'meta-app-registry.canary.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
script=files['meta-app-roles-watch.sh.before'].read_text(encoding='utf-8'); old="REGISTRY_PATH = Path('/root/mgs-agent/data/meta-app-registry.json')"; assert script.count(old)==1; script=script.replace(old,f"REGISTRY_PATH = Path('{BACKUP}/meta-app-registry.canary.json')",1)
lock='LOCK_FILE="/var/lock/meta-app-roles-watch.lock"'; assert script.count(lock)==1; script=script.replace(lock,'LOCK_FILE="/var/lock/meta-app-roles-watch-b0073-canary.lock"',1); (BACKUP/'meta-app-roles-watch.canary.sh').write_text(script,encoding='utf-8')
(BACKUP/'meta-app-role-monitor-state.canary.json').write_text('{"apps": {}}\n',encoding='utf-8')
pause={'version':4,'mode':'manual','apps':['B007-3'],'monitor_apps':[],'timezone':'America/New_York','requested_by':'Rodolfo Mattei','source_message_id':'OOB-B0073-after-1545088764530008135','reason':'isolated B007-3 cutover canary alert containment'}
(BACKUP/'meta-app-role-alert-pause.canary.json').write_text(json.dumps(pause,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=[]
for p in sorted(BACKUP.iterdir(),key=lambda x:x.name):
 if p.is_file() and p.name!='SHA256SUMS': manifest.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}')
(BACKUP/'SHA256SUMS').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
print(json.dumps({'status':'prepared','backup':str(BACKUP),'files':len(files),'canary_app':'B007-3'},ensure_ascii=False))
