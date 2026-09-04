#!/usr/bin/env python3
import fcntl, json, os
from datetime import datetime, timezone
from pathlib import Path
path=Path('/root/mgs-agent/logs/events-audit.jsonl')
record={
 'ts':datetime.now(timezone.utc).isoformat(),'agent':'zeus','event':'finance_dashboard_august_created_validated',
 'actor':'Rodolfo Mattei','thread_id':'1545426987756298340',
 'authorization_message_ids':['1545428410765942796','1545428672423534713','1545553235874545664'],
 'spreadsheet_id':'16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak',
 'dashboard':{'title':'DASH EXECUTIVO','sheet_id':292770908,'url':'https://docs.google.com/spreadsheets/d/16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak/edit#gid=292770908','kpis':8,'filters':5,'charts':4},
 'base':{'title':'BASE_DASH','sheet_id':1621008526,'rows':154,'columns':22,'site_segments':43,'country_rows':78,'daily_rows':31,'monthly_rows':1},
 'first_attempt':{'status':'failed','error':'INVALID_ARGUMENT: BAR chart series may only target BOTTOM_AXIS','rollback':'pass; both newly created sheets deleted; next preflight confirmed original 15 sheets and target tabs absent'},
 'second_attempt':{'status':'pass','chart_axis_fix':'BAR series target BOTTOM_AXIS'},
 'validation':{'source_formula_hashes_unchanged':True,'displayed_errors':0,'independent_checks':'22/22','filter_probe':'ActiveView reacted and restored to TODOS','charts':'4/4','data_validations':'5/5'},
 'metrics_at_validation':{'gross_usd':413637.2595039202,'revenue_after_invalid_usd':411375.58783002436,'media_spend_usd':300125.3211399784,'net_profit_usd':35883.70445677731,'net_roi':0.11956240253397732,'active_sites':28,'profitable_active_sites':14,'status':'PROVISORIO'},
 'backup_sha256':'1f19828e89cd14f81f413fd6c5f65a65e00866f6eeca81502b4d31adb899d846',
 'candidate_sha256':'ca1f97c416b7e17e4fb7ef7785160e1cc492e91765a7843c2f5832976ebe8a61',
 'verification_sha256':'57f1133708a71120a6f333f4dc9295898a351e591975c05ef549afba0942d87c',
 'independent_verification_sha256':'752a626d4a372657b62f086301476dccea7eb616e8542ae6460f5194bdb820cb',
 'skill_version':'0.1.8','skill_sha256':'2f7f6c6778e6c09a48b5994dac9cc08ccd04af27239a23f82a1cc18e9afa62ad',
 'ledger_sha256':'b5cd7046269d234387be57524d2e525c6cd8275e56da68a019beec121b3261d6',
 'checkpoint_sha256':'3f89564a84ff872c33a54b6a2bf300f483fe77de491ec0998c8c10e82aea2a0d',
 'inventory_sha256':'38972bf7cd0388b2f9166df2e4c5a97362c3be2c965bc537b20f774506bf6221'
}
with path.open('a',encoding='utf-8') as h:
 fcntl.flock(h.fileno(),fcntl.LOCK_EX);h.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n');h.flush();os.fsync(h.fileno());fcntl.flock(h.fileno(),fcntl.LOCK_UN)
print(json.dumps({'status':'pass','event':record['event'],'dashboard_sheet_id':292770908},separators=(',',':')))
