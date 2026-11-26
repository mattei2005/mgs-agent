import hashlib,json,re,shutil
from pathlib import Path
from datetime import datetime
from decimal import Decimal
R=Path(__file__).parent
DEST=Path('/root/mgs-agent/data/ares/meta-ads/reports/shein-on-demand-requests/1575567382112510074')
load=lambda p:json.loads(p.read_text())
q=load(R/'request.json');fin=load(R/'final-reconciliation.json')
tests=load(R/'test-results.json')
required={'test_shein_report_financial_source.py','test_shein_report_layout.py','test_shein_report_intraday.py','test_shein_report_daily_d1.py'}
assert {s['suite'] for s in tests['suites']}==required
assert all(s['returncode']==0 for s in tests['suites'])
f=tests['summary_fixtures'];assert f['passed'] and f['tests_run']==5 and f['failures']==f['errors']==0
canonical=load(Path(q['selection_source']))
pairs={(b['account_id'],b['thread_id']) for b in q['bindings']}
assert pairs=={(b['account_id'],b['thread_id']) for b in canonical['bindings']}
assert len(pairs)==fin['accounts']==fin['summaries']==7
assert fin['meta_writes']==0 and fin['status']=='COMPLETE_GET_VERIFIED_AND_RECONCILED'
capture=load(R/'sb-visible-rps-capture.json')
assert capture['complete'] and capture['identity_Ares_visible'] and capture['currency']=='USD'
assert capture['data_date']==q['date'] and capture['pages'][-1]['end']==capture['pages'][-1]['total']
ui={(r['ACCOUNT_ID'].removeprefix('act_'),r['CAMPAIGN_ID']) for r in capture['rows']}
qa=[];all_ids=[]
for b in q['bindings']:
 p=R/b['account_id'];m=load(p/'model.json');rows=m['rows'];selected=load(p/'selected.json')
 assert set(selected)=={r['id'] for r in rows} and len(selected)==len(rows)
 assert m['account']['name']==b['account_name'] and m['date']==q['date'] and m['account']['currency']=='USD'
 assert m['source_timestamps']['financial']==m['source_timestamps']['sb']
 assert datetime.fromisoformat(m['source_timestamps']['financial'])>=datetime.fromisoformat(q['started_at'])
 assert len(m['history_dates'])==7 and 'closed_day_report' not in m
 sb=load(p/'sb.json');must={str(s['CAMPAIGN_ID']) for s in sb if str(s['DATE'])[:10]==q['date']} & set(selected)
 assert all((b['account_id'],cid) in ui for cid in must)
 for row in rows:
  assert [h['partial'] for h in row['history']]==[False]*6+[True]
  assert row['roi']==row['history'][-1]['roi']
  assert row['spend']==row['history'][-1]['spend']
 parts=load(p/'report.parts.json');assert all(len(s.encode('utf-16-le'))//2<=2000 for s in parts)
 text=(p/'summary.txt').read_text()
 assert all(a in text for a in ['Gasto:','Receita líquida:','Saldo:','ROI real:','ROI estimado:'])
 if not rows:assert 'Receita líquida: **n/d**' in text and 'Saldo: **n/d**' in text and 'ROI real: **n/d**' in text
 all_ids.extend(selected)
 qa.append({'account_id':b['account_id'],'thread_id':b['thread_id'],'campaigns':len(rows),'ui_covered':len(must),'parts':len(parts),'financial_cutoff':m['source_timestamps']['financial']})
assert len(all_ids)==len(set(all_ids))==fin['campaigns']
(R/'qa.json').write_text(json.dumps({'status':'PASS','accounts':qa,'campaigns':len(all_ids),'source_window_and_financial_checks':True,'tests':load(R/'test-results.json')},ensure_ascii=False,indent=2))
root_names={'acceptance.json','authorization.json','collection-progress.json','completion.json','delivery-progress.json','destinations-readback.json','final-reconciliation.json','intraday.py','launch.py','archive.py','qa.json','preflight.json','publishers.json','request.json','sb-visible-rps-capture.json','summary-deliveries.json','validated-summary.json','test-results.json','test_summary.py','run_tests.py','review.py','prepublication-qa.json','approved-review.json','gate-test-results.json','test_gate.py','materialize_from_refresh.py','diagnose_refresh.py','archive-test-results.json'}
# Diagnostic refresh artifacts exist only when recovery was needed.
# Keep mandatory request evidence required, but do not invent recovery files.
root_names.update(name for n in range(0,len(all_ids),50)
                  if (R/(name := 'refresh-diagnostic-'+str(n)+'.json')).exists())
root_names.update({'test_archive.py','scoped-tests/test_shein_report_financial_source.py'})
root_names.update('rps-page-'+str(p['number'])+'.json' for p in capture['pages'])
files=[R/n for n in sorted(root_names)]
account_names={'account.json','ads.json','adsets.json','campaigns.json','daily.json','delay.json','insights.json','model.json','receipt.json','delivery.json','report.md','report.parts.json','sb.json','selected.json','summary-intent.json','summary.txt','refresh-observed-at.json'}
account_names.update(n+'-observed-at.json' for n in ['account','ads','adsets','campaigns','daily','delay','insights','sb'])
def account_archive_files(p,required,conditional):
 missing=[n for n in sorted(required) if not (p/n).exists()]
 assert not missing,'Missing mandatory account evidence: '+','.join(missing)
 return [p/n for n in sorted(required)]+[p/n for n in sorted(conditional) if (p/n).exists()]
for b in q['bindings']:
 p=R/b['account_id'];names=set(account_names)
 names.update('delivery-intent-'+str(i)+'.json' for i in range(len(load(p/'report.parts.json'))))
 files.extend(account_archive_files(p,names,{'ads-pagination.json','ads-archived-recovery.json','adsets-archived-recovery.json'}))
DEST.mkdir(parents=True,exist_ok=True,mode=0o700);manifest=[]
for src in files:
 assert src.name!='session.json'
 rel=src.relative_to(R);dst=DEST/rel;dst.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 data=src.read_bytes();shutil.copyfile(src,dst);dst.chmod(0o600);assert dst.read_bytes()==data
 manifest.append({'path':str(rel),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'role':'reusable_code' if src.suffix=='.py' else 'request_evidence'})
mp=DEST/'artifact-manifest.json';mp.write_text(json.dumps({'request_id':q['source_message_id'],'status':'ARCHIVED_BYTES_VERIFIED','files':manifest,'excluded':['session.json']},ensure_ascii=False,indent=2));mp.chmod(0o600)
assert all(hashlib.sha256((DEST/e['path']).read_bytes()).hexdigest()==e['sha256'] for e in load(mp)['files'])
print(json.dumps({'status':'ARCHIVED_AND_QA_VERIFIED','accounts':len(pairs),'campaigns':len(all_ids),'files':len(manifest),'source':str(DEST/'final-reconciliation.json')}))
