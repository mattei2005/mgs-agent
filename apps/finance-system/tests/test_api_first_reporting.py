import unittest,pathlib,sys
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from spend_report import render_report
from finance_spend_sources import missing_spend_account,SourceError
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
if __name__=='__main__':unittest.main()
