import unittest,pathlib,sys
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from spend_report import render_report
from finance_spend_sources import missing_spend_account,collect_account_with_retry,SourceError
class ApiFirstReportingTests(unittest.TestCase):
 def report(self):return {'pass':True,'period':'2026-09','since':'2026-09-01','until':'2026-09-07','totals':{'USD':'111206.16'},'api_totals':{'meta':{'accounts':34,'by_currency':{'USD':'114831.22'}}},'auto_registration':{'created':[{'id':'123','name':'Demo-US-01','site':'demo'}],'bound':[]},'exceptions':[],'missing_accounts':[]}
 def test_failure_is_actionable_not_green_success(self):
  r=render_report({'pass':False,'step':'source_collection','since':'2026-09-01','until':'2026-09-07'});self.assertTrue(r['attention']);self.assertTrue(r['actionable']);self.assertIn('não foi concluída',r['body'])
 def test_total_is_api_not_registered_ledger(self):
  r=render_report(self.report());self.assertIn('34',r['body']);self.assertIn('114.831,22',r['body']);self.assertNotIn('111.206,16',r['body']);self.assertNotIn('Gastos importados',r['body'])
 def test_same_pending_does_not_change_signature_on_amount(self):
  p=self.report();p['auto_registration']['created']=[];p['exceptions']=[{'id':'456','name':'Demo','reason':'multiple_spend_fields','currency':'USD','amount':'1.00'}];a=render_report(p);p['exceptions'][0]['amount']='2.00';b=render_report(p);self.assertEqual(a['signature'],b['signature']);self.assertTrue(a['attention'])
 def test_missing_zero_is_not_a_registration_alert(self):
  p=self.report();p['auto_registration']['created']=[];p['missing_accounts']=[{'account_id':'456','spend_status':'ok','spend_amount':'0','name':'Reserve'}];r=render_report(p);self.assertFalse(r['actionable']);self.assertNotIn('Reserve',r['body'])
 def test_canceled_google_is_unknown_not_zero(self):
  for status in ('CANCELED','CLOSED'):
   a={'platform':'google','account_id':'1234567890','status':status};r=missing_spend_account(a,'2026-09-01','2026-09-07',None,None,None);self.assertEqual(r['spend_status'],'unavailable_status');self.assertNotIn('spend_amount',r)
 def test_meta_read_error_is_not_zero(self):
  def denied(*args):raise SourceError('read_denied')
  r=missing_spend_account({'platform':'meta','account_id':'123'},'2026-09-01','2026-09-07',SimpleNamespace(graph_get=denied),None,None);self.assertEqual(r['spend_status'],'error');self.assertNotIn('spend_amount',r)
 def test_detailed_account_transient_failure_is_retried_once(self):
  with patch('finance_spend_sources.collect_account',side_effect=[{'status':'error','error':'AssertionError'},{'status':'ok','currency':'USD'}]) as collect,patch('finance_spend_sources.time.sleep') as pause:
   row,history=collect_account_with_retry({'id':'123'},'2026-09-01','2026-09-07',None,None,None)
  self.assertEqual(row['status'],'ok');self.assertEqual(row['automatic_recovery']['attempts'],2);self.assertEqual(len(history),2);self.assertEqual(collect.call_count,2);pause.assert_called_once_with(300)
class FiveMinuteRetryTests(unittest.TestCase):
 def test_transient_allowlist_and_permanent_exclusions(self):
  from finance_spend_sources import retryable_read_error
  for error in ['AssertionError','TimeoutError','URLError','Meta HTTP 503 code 2','Meta HTTP 400 code 4','Google HTTP 429 []']:
   self.assertTrue(retryable_read_error(error),error)
  for error in ['Meta HTTP 400 code 190 subcode 463','Meta HTTP 403 code 10','Meta HTTP 400 code 200','Meta HTTP 400 code 100','Meta HTTP 400 code 368','Google HTTP 400 AUTHENTICATION_ERROR','billing','unknown','KeyError','']:
   self.assertFalse(retryable_read_error(error),error)
 def test_success_has_no_delay_or_second_read(self):
  with patch('finance_spend_sources.collect_account',return_value={'status':'ok'}) as read,patch('finance_spend_sources.time.sleep') as pause:
   row,h=collect_account_with_retry({'id':'123'},'2026-09-01','2026-09-07',None,None,None)
  self.assertEqual(read.call_count,1);pause.assert_not_called();self.assertEqual(len(h),1)
 def test_persistent_failure_stays_unknown_and_stops(self):
  with patch('finance_spend_sources.collect_account',return_value={'status':'error','error':'AssertionError'}) as read,patch('finance_spend_sources.time.sleep') as pause:
   row,h=collect_account_with_retry({'id':'123'},'2026-09-01','2026-09-07',None,None,None)
  self.assertEqual(read.call_count,2);pause.assert_called_once_with(300);self.assertEqual(row['status'],'error');self.assertNotIn('daily',row);self.assertNotIn('aggregate_total',row);self.assertEqual(len(h),2)
 def test_auth_failure_is_not_delayed(self):
  with patch('finance_spend_sources.collect_account',return_value={'status':'error','error':'Meta HTTP 400 code 190 subcode 463'}) as read,patch('finance_spend_sources.time.sleep') as pause:
   row,h=collect_account_with_retry({'id':'123'},'2026-09-01','2026-09-07',None,None,None)
  self.assertEqual(read.call_count,1);pause.assert_not_called();self.assertEqual(row['status'],'error')
 def test_batch_wait_shared_only_failed_rows_reread(self):
  from finance_spend_sources import retry_failed_batch
  rows=[{'id':'a','status':'error','error':'AssertionError'},{'id':'b','status':'ok','amount':'10'},{'id':'c','status':'error','error':'TimeoutError'},{'id':'d','status':'unavailable_status'}];seen=[]
  def read(row):seen.append(row['id']);return {'id':row['id'],'status':'ok','amount':'20'}
  with patch('finance_spend_sources.time.sleep') as pause:out=retry_failed_batch(rows,read)
  pause.assert_called_once_with(300);self.assertEqual(set(seen),{'a','c'});self.assertEqual([r['id'] for r in out],['a','b','c','d']);self.assertEqual(out[1]['amount'],'10');self.assertEqual(out[3]['status'],'unavailable_status');self.assertEqual(rows[0]['status'],'error')
 def test_scan_retry_preserves_failed_not_zero_and_journal(self):
  import tempfile,json
  from finance_spend_sources import retry_failed_batch
  row={'account_id':'123','spend_status':'error','spend_error':'TimeoutError'}
  with tempfile.TemporaryDirectory() as folder,patch('finance_spend_sources.time.sleep') as pause:
   path=pathlib.Path(folder)/'retry.json'
   def read(prior):
    self.assertEqual(json.loads(path.read_text())['status'],'retrying');return row
   out=retry_failed_batch([row],read,status_key='spend_status',error_key='spend_error',history_key='scan_attempts',evidence_path=path)
   proof=json.loads(path.read_text())
  pause.assert_called_once_with(300);self.assertEqual(proof['remaining'],1);self.assertEqual(proof['recovered'],0);self.assertNotIn('spend_amount',out[0]);self.assertEqual(len(out[0]['scan_attempts']),2)
 def test_five_failures_or_stopped_scan_never_loop(self):
  from finance_spend_sources import retry_failed_batch
  for rows in [[{'id':str(i),'status':'error','error':'TimeoutError'} for i in range(5)],[{'status':'error','error':'TimeoutError'},{'status':'not_checked'}]]:
   with patch('finance_spend_sources.time.sleep') as pause:
    def read(row):self.fail('five-failure stop bypassed')
    out=retry_failed_batch(rows,read)
   pause.assert_not_called();self.assertEqual(len(out),len(rows))
 def test_retry_validates_source_not_only_http(self):
  from finance_spend_sources import collect_account
  a={'id':'123456','name':'test','platform':'meta','currency':'USD','timezone':'America/New_York'}
  def graph(edge,token,params):
   if '/insights' not in edge:return 200,{'account_id':'123456','currency':'USD','timezone_name':'America/New_York'},{}
   return 200,{'data':[{'account_id':'123456','account_currency':'USD','date_start':'2026-09-01','date_stop':'2026-09-01','spend':'10' if params['time_increment']==1 else '11'}]},{}
  with patch('finance_spend_sources.time.sleep') as pause:
   row,h=collect_account_with_retry(a,'2026-09-01','2026-09-01',SimpleNamespace(graph_get=graph),None,None)
  self.assertEqual(row['status'],'error');self.assertEqual(row['error'],'AssertionError');pause.assert_called_once_with(300);self.assertNotIn('daily',row)
 def test_active_api_first_recovers_scan_and_detail_without_revisiting_success(self):
  import tempfile,collections
  import finance_spend_sources as s
  identities={v:{'account_id':v,'name':v,'currency':'USD','timezone':'America/New_York','business_id':'bm'} for v in ['11111','22222']}
  worker=SimpleNamespace(meta=SimpleNamespace(get_token_from_1password=lambda _:('secret',None)),inventory=lambda:(identities,1))
  google=SimpleNamespace(inventory=lambda:({},0));counts=collections.Counter()
  def scan(a,*args):
   counts['scan'+a['account_id']]+=1
   if a['account_id']=='11111' and counts['scan11111']==1:return {**a,'spend_status':'error','spend_error':'TimeoutError'}
   return {**a,'spend_status':'ok','spend_amount':'10'}
  def detail(a,*args):
   counts['detail'+a['id']]+=1
   if a['id']=='22222' and counts['detail22222']==1:return {'id':a['id'],'name':a['name'],'platform':a['platform'],'status':'error','error':'AssertionError'}
   return {'id':a['id'],'name':a['name'],'platform':a['platform'],'status':'ok','currency':a['currency'],'daily':[{'date':'2026-09-01','amount':'10'}]}
  spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _:None))
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'load_env'),patch.object(s,'google_headers',return_value={}),patch.object(s.importlib.util,'spec_from_file_location',return_value=spec),patch.object(s.importlib.util,'module_from_spec',return_value=worker),patch.dict(sys.modules,{'google_ads_inventory':google}),patch.object(s,'missing_spend_account',side_effect=scan),patch.object(s,'collect_account',side_effect=detail),patch.object(s.time,'sleep') as pause:
   result=s.collect_api_first('2026-09-01','2026-09-01',pathlib.Path(folder))
  self.assertEqual(pause.call_count,1);self.assertTrue(all(call.args==(300,) for call in pause.call_args_list));self.assertEqual(counts,{'scan11111':2,'scan22222':1,'detail11111':1,'detail22222':2});self.assertEqual(result['expected_accounts'],2);self.assertTrue(all(a['status']=='ok' for a in result['accounts']));self.assertEqual(result['ad_writes'],0);self.assertEqual(result['sheet_writes'],0)
if __name__=='__main__':unittest.main()
