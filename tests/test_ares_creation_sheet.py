import copy,importlib.util,json,unittest
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
P=Path('/root/.hermes/profiles/ares/scripts/campaign-creation-sheet.py');s=importlib.util.spec_from_file_location('tested_creation_sheet',P);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class CreationSheetTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=m.config();cls.accounts=[a for a in m.load(m.BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json')['accounts'] if a['name'].split('-')[0] in cls.p['brands']]
  cls.snapshot=m.load(m.STATE/'runs/manual-20261110T091441/snapshot.json')
 def fixture(self):
  with patch.object(m,'now',return_value=datetime.fromisoformat(self.snapshot['cutoff'])):
   d=m.snapshot_to_days(self.snapshot,self.p,self.accounts)
  return m.preserve_history(self.snapshot,d,self.accounts,{})
 def test_scope_exact_six_sites_thirty_six_accounts(self):
  self.assertEqual(len(self.accounts),36);self.assertEqual({a['name'].split('-')[0] for a in self.accounts},set(self.p['brands']))
  self.assertEqual(len({(a['name'].split('-')[0],a['manager_code']) for a in self.accounts}),36)
 def test_exact_baseline_partition_preserves_existing_history(self):
  days,ledger=self.fixture();baseline=m.load(m.BASE/self.p['historical_baseline'])
  for brand,b in baseline['sites'].items():
   for d,vals in b['daily'].items():
    for code,v in vals.items():
     self.assertGreaterEqual(days[d]['cells'][brand+'|'+code],v)
     if d<'2026-10-28':self.assertEqual(days[d]['cells'][brand+'|'+code],v)
 def test_disappeared_campaign_retained_by_unique_id(self):
  days,ledger=self.fixture();snapshot=copy.deepcopy(self.snapshot)
  for a in snapshot['accounts']:a['campaigns']=[]
  d=m.snapshot_to_days(snapshot,self.p,self.accounts);again,ledger2=m.preserve_history(snapshot,d,self.accounts,ledger)
  self.assertEqual(ledger2,ledger)
  self.assertEqual({k:v['cells'] for k,v in again.items()},{k:v['cells'] for k,v in days.items()})
 def test_duplicate_id_rejected(self):
  v=copy.deepcopy(self.snapshot);a=next(a for a in v['accounts'] if a['campaigns']);a['campaigns'].append(a['campaigns'][0])
  with self.assertRaises(AssertionError):m.snapshot_to_days(v,self.p,self.accounts)
 def test_incomplete_not_zero(self):
  v=copy.deepcopy(self.snapshot);v['accounts'][0]['complete']=False
  with self.assertRaises(AssertionError):m.snapshot_to_days(v,self.p,self.accounts)
 def test_full_month_tabs_summary_consistency_future_blank(self):
  d,_=self.fixture();models=m.models(d,self.p,self.accounts);self.assertEqual(len(models),14)
  self.assertEqual(len({x['title'] for x in models}),14)
  for month in ['2026-10','2026-11']:
   details=[x for x in models if x['month']==month and x['kind']=='detail'];summary=next(x for x in models if x['month']==month and x['kind']=='summary')
   self.assertEqual(len(details),6);self.assertEqual(summary['width'],9)
   self.assertEqual(summary['rows'][12][-2],sum(x['rows'][12][-1] for x in details))
   for i in range(6,12):self.assertEqual(summary['rows'][i][-2],sum(x['rows'][i][-1] for x in details))
   for row in summary['rows'][15:]:
    if row[-1]!='FUTURO — não consolidado':self.assertEqual(row[-2],sum(row[1:-2]))
  for x in models:
   if x['month']=='2026-11' and x['kind']=='detail':self.assertEqual(x['rows'][6][11],'');self.assertIn('PARCIAL',x['rows'][2][1])
 def test_missing_site_or_repeated_account_rejected(self):
  for rows in [self.snapshot['accounts'][:-1],self.snapshot['accounts'][:-1]+[self.snapshot['accounts'][0]]]:
   snap=dict(self.snapshot,accounts=rows)
   with self.assertRaises(AssertionError):m.snapshot_to_days(snap,self.p,self.accounts)
 def test_existing_closed_twelve_cell_history_expands_without_count_loss(self):
  prior=m.load(m.BASE/'data/ares/meta-ads/reports/creation-sheet-1569716229999173673/days.json.before')
  new=m.snapshot_to_days(self.snapshot,self.p,self.accounts);days=m.merge_days(prior,new)
  ledger=m.load(m.BASE/'data/ares/meta-ads/reports/creation-sheet-1569716229999173673/campaign-ledger.json.before')
  days,_=m.preserve_history(self.snapshot,days,self.accounts,ledger)
  for day,row in prior.items():
   self.assertEqual(len(days[day]['cells']),36)
   for key,val in row['cells'].items():self.assertGreaterEqual(days[day]['cells'][key],val)
 def test_historical_ids_union_is_idempotent_and_scoped(self):
  cutoff=datetime.fromisoformat(self.snapshot['cutoff']);out=m.historical_ledger(self.accounts,{},cutoff)
  self.assertEqual(m.historical_ledger(self.accounts,out,cutoff),out)
  self.assertTrue(all(c['account_id'] in {a['account_id'] for a in self.accounts} for c in out.values()))
 def test_existing_sheet_ids_reused_new_ids_collision_free(self):
  from tempfile import TemporaryDirectory
  from unittest.mock import Mock
  d,_=self.fixture();model=m.models(d,self.p,self.accounts)
  before=m.load(m.STATE/'runs/closed-2026-11-09/readback.json')['book']
  g=Mock();g.book.return_value=before;g.fid=self.p['spreadsheet_id'];g.p=self.p;g.batch.side_effect=RuntimeError('STOP_BEFORE_REMOTE_WRITE')
  with TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(RuntimeError,'STOP_BEFORE_REMOTE_WRITE'):m.sync(g,model,Path(tmp))
   mapping=m.load(Path(tmp)/'write-intent.json')['mapping']
  self.assertEqual(len(set(mapping.values())),14)
  for sheet in before['sheets']:self.assertEqual(mapping[sheet['properties']['title']],sheet['properties']['sheetId'])
  requests=g.batch.call_args.args[0]
  self.assertEqual(sum('addSheet' in r for r in requests),8)
  summary_charts=[r['updateChartSpec']['spec'] for r in requests if 'updateChartSpec' in r and r['updateChartSpec']['spec']['basicChart']['series'][0]['series']['sourceRange']['sources'][0]['startColumnIndex']==7]
  self.assertEqual(len(summary_charts),2)
 def test_closed_day_not_downgraded(self):
  prior={'2026-11-08':{'closed':True,'cutoff':'2026-11-08T23:59:59-05:00','cells':{'a':8}}};new={'2026-11-08':{'closed':False,'cutoff':'2026-11-08T18:08:00-05:00','cells':{'a':1}}}
  self.assertEqual(m.merge_days(prior,new),prior)
 def test_preparation_and_publication_gate(self):
  at=datetime.fromisoformat('2026-11-10T00:13:25-05:00');cut,gate=m.close_window(at)
  self.assertEqual(cut.isoformat(),'2026-11-09T23:59:59.999999-05:00');self.assertEqual(gate.hour,0);self.assertEqual(gate.minute,15);self.assertEqual((gate-at).total_seconds(),95)
  with self.assertRaises(AssertionError):m.close_window(at.replace(minute=12))
 def test_dst_closed_civil_day_is_twenty_five_hours(self):
  cut,gate=m.close_window(datetime.fromisoformat('2026-11-02T00:13:25-05:00'))
  start=datetime(2026,11,1,tzinfo=m.NY);end=cut+timedelta(microseconds=1)
  self.assertEqual(end.timestamp()-start.timestamp(),25*3600)
 def test_columns(self):self.assertEqual([m.colname(n) for n in [1,26,27,33]],['A','Z','AA','AG'])
 def test_chart_update_fieldmask_is_relative_to_overlay(self):
  text=P.read_text();self.assertIn("'fields':'anchorCell,widthPixels,heightPixels'",text);self.assertNotIn("'fields':'overlayPosition'",text)
 def test_daily_hook_failure_preserves_daily_report(self):
  d=m.module('test_creation_daily',m.HOME/'scripts/shein-campaign-creation-daily.py')
  with patch.object(d,'module',side_effect=RuntimeError('test')),patch.object(d,'save') as save:
   d.update_creation_sheet({},m.STATE/'unit-test-no-write');self.assertEqual(save.call_args.args[1]['status'],'FAILED_RESUMABLE')
if __name__=='__main__':unittest.main()
