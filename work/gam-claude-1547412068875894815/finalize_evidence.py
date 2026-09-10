import json,os,fcntl,hashlib
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).parent; root=Path('/root/mgs-agent'); ident='zeus-gam-claude-yolo-1547412068875894815'
paths=[root/'docs/gam-revenue-claude-yolo-september-2026.md',root/'data/knowledge-registry.json',root/'data/agent-checkpoints.json',Path('/root/.hermes/profiles/zeus/skills/ops/revenue-spend-reporting-pipeline/SKILL.md'),Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/SKILL.md'),Path('/root/.hermes/profiles/zeus/skills/ops/smartbidding-dashboard-map/references/route-pack-02.md'),Path('/root/.hermes/profiles/zeus/skills/ops/smartbidding-dashboard-map/references/adgroup-gam-revenue-reconciliation.md')]+sorted(p for p in P.iterdir() if p.suffix in ('.py','.json'))
manifest=json.loads((P/'manifest.json').read_text());cache=Path('/root/.hermes/profiles/zeus/cache/documents')
assert len(manifest)==5 and all(hashlib.sha256((cache/m['file']).read_bytes()).hexdigest()==m['sha256'] for m in manifest)
rec=json.loads((P/'reconciliation.json').read_text());assert rec['all_102_rounded_match']
now=datetime.now(timezone.utc).isoformat()
entry={'id':ident,'agent':'zeus','type':'read_only_finance_analysis_and_knowledge','authorization_message_id':'1547412068875894815','source_thread_id':'1545426987756298340','updated_at':now,'paths':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size} for p in paths],'evidence_directory':str(P),'summary':{'original_files':4,'consolidated_files':1,'raw_rows':rec['raw_rows'],'all_102_groups_reproduced':True,'sb_100_rows_daily_requery_equal':True,'financial_writes':False,'email_connector_deployed':False,'yolo_source_difference_unresolved':True,'knowledge_validator':'PASS'},'report_infra_pending':True}
p=root/'data/infra-inventory.json';lock=root/'data/.infra-inventory.lock'
with lock.open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=json.loads(p.read_text());rows=d.setdefault('runtime_artifacts',[]);rows[:]=[x for x in rows if x.get('id')!=ident];rows.append(entry);tmp=p.with_name(p.name+'.gam-'+str(os.getpid()));tmp.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');tmp.chmod(p.stat().st_mode & 0o777);os.replace(tmp,p);check=json.loads(p.read_text());assert next(x for x in check['runtime_artifacts'] if x.get('id')==ident)==entry
with (root/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'gam_claude_yolo_reconciliation','authorization_message_id':'1547412068875894815','artifact_id':ident,'source':str(paths[0]),'evidence':entry['summary'],'scope':'4 originais GAM + Claude7/8 setembro; SB read-only; persistencia documental somente'},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps({'status':'PASS','inventory_entry':ident,'inventoried_paths':len(paths),'source_hashes_unchanged':5,'financial_writes':False,'evidence':entry['summary']},ensure_ascii=False))
