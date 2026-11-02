import sys,json,subprocess,time
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b
E=b.BASE/'data/ares/creative-ops/executions/intake-1566594718320693251';jobs=b.read_json(E/'archive-jobs.json');wanted={j['job_id'] for j in jobs}
for cycle in range(40):
 index=b.read_json(b.DATA/'archive-index.json',{});verified=wanted.intersection(index.get('verified_jobs',{}));entries=[e for e in index.get('mappings',{}).values() if e.get('jobId') in wanted];transferred=sum(e.get('stockTransferredToArchive') is True for e in entries)
 print('archive progress',len(verified),'of',len(wanted),'stock',transferred,'of',2*len(wanted),flush=True)
 if len(verified)==len(wanted) and transferred==2*len(wanted):
  b.atomic_json(E/'transport.json',{'status':'complete','jobs':sorted(wanted),'verified':len(verified),'transferred':transferred,'at':b.now_iso()});break
 if len(verified)<len(wanted):
  command=[sys.executable,'-c',"import sys,json;sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_archive_owner_transport as t;print(json.dumps(t.run_tick(max_jobs=4,max_seconds=210,origin='foreground',produce=False)))"]
  p=subprocess.run(command,capture_output=True,text=True,timeout=900);(E/f'owner-cycle-{cycle:02}.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError('Owner transport failed; inspect local phase log')
  result=json.loads(p.stdout.strip().splitlines()[-1]);print('owner cycle',cycle,result.get('status'),'verified',len(result.get('verified_jobs',[])),flush=True)
  if result.get('blocked'):raise RuntimeError('Owner blocked: '+json.dumps(result['blocked']))
 for lane in range(2):
  p=subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs_private_stock_transport.py','--apply','--max-files','4'],capture_output=True,text=True,timeout=900);(E/f'stock-cycle-{cycle:02}-{lane}.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError('Stock transfer failed; inspect local phase log')
  result=json.loads(p.stdout.strip().splitlines()[-1]);print('stock cycle',cycle,lane,'transferred',len(result.get('transferred',[])),flush=True)
else:raise RuntimeError('Scoped completion not reached; preserve checkpoints')
