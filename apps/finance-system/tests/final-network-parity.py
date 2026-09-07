"""Independent final Sheet × published financial-engine readback, no writes."""
import pathlib,sys,json,shlex,collections
from decimal import Decimal as D
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/networks-1546579646227943506';sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557');import audit
pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -At -d mgs_finance -c '
sql="SELECT json_build_object('id',id,'domain',result->'domain','revision',revision) FROM scenarios WHERE id IN ('workspace-2026-08','workspace-2026-09') ORDER BY id"
rows=[json.loads(l) for l in ssh(pg+shlex.quote(sql)).splitlines()];(STATE/'final-production-domains.json').write_text(json.dumps(rows,ensure_ascii=False));snap=json.loads((STATE/'sheets-repair-after.json').read_text());grids={s['properties']['title']:audit.cells(s) for s in snap['sheets']};result=[]
num=lambda x:D(str(x)) if x not in ('',None) else D(0)
for row in rows:
 title='Agosto 2026' if row['id'].endswith('08') else 'Setembro 2026';grid=grids[title];bad=[];count=0
 for f in row['domain']['facts']:
  for metric,cell in f['source'].items():
   if metric in ['roi_gross','roi_net']:continue
   value=audit.val(grid.get(cell,{}));amount=f[metric];count+=1
   if isinstance(value,dict) or abs(num(value)-num(amount))>D('.000001'):bad.append({'id':f['id'],'metric':metric,'cell':cell,'sheet':value,'dash':amount})
 personnel=[]
 for e in row['domain']['expenses']:
  if e['category']!='personnel' or not e['label']:continue
  r=e['id'].split('|')[-1]
  if not r.isdigit():continue
  sheet_brl=audit.val(grid.get('P'+r,{}));delta=num(e['brl'])-num(sheet_brl);personnel.append({'id':e['id'],'label':e['label'],'sheet_brl':str(num(sheet_brl)),'dash_brl':str(num(e['brl'])),'delta_brl':str(delta)})
 result.append({'id':row['id'],'daily_checks':count,'daily_mismatches':len(bad),'bad':bad,'personnel':personnel,'network_counts':dict(collections.Counter(s['network'] for s in row['domain']['site_catalog'])),'cash':row['domain']['cash']})
old=next(x for x in json.loads((STATE/'production-before.json').read_text()) if x['id']=='workspace-2026-08')['result']['cash'];new=result[0]['cash'];delta={k:str(num(new[k])-num(old[k])) for k in ['gross','invalid','net','tax','spend','personnel','half_usd','half_brl']}
out={'periods':result,'august_change_vs_task_start':delta,'source_currency_gap':{'site':'WavesBee','period':'2026-09','sheet_input':'GP2 GROSS_CAD_US','sheet_conversion':'GQ5 GP5/H1','dashboard_inherited_input':'GBP','status':'decision_required_outside_invalid_formula_scope'},'pass_daily_values':all(not r['daily_mismatches'] for r in result)}
(STATE/'final-financial-parity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'pass_daily_values':out['pass_daily_values'],'periods':[{'id':r['id'],'daily_checks':r['daily_checks'],'daily_mismatches':r['daily_mismatches'],'first_mismatches':r['bad'][:4],'payroll_deltas':[p for p in r['personnel'] if abs(num(p['delta_brl']))>D('.01')],'network_counts':r['network_counts']} for r in result],'august_delta':delta},ensure_ascii=False))
