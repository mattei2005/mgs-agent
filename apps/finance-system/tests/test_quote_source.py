"""Technical quote source never reads monthly settlement cells."""
import importlib.util,json,os,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('independent_quote_sync',ROOT/'sync-quotes.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
BRL='principal|CAIXA SINTETICO|J2';CAD='principal|Agosto 2026|H1';GBP='principal|Agosto 2026|I1'
class SourceIndependenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.config=pathlib.Path(self.tmp.name)/'config.json';self.calls=[]
  self.cfg={'spreadsheet_id':'technical-sheet','drive_id':'0AEwt4Ye690ocUk9PVA','sheet_title':'Sheet1','range':'A1','key':GBP,'formula':'=GOOGLEFINANCE("GBPUSD")','periods':['2026-08'],'automatic_sources':[{'key':BRL,'range':'B1','formula':'=GOOGLEFINANCE("USDBRL")*99%'},{'key':CAD,'range':'C1','formula':'=GOOGLEFINANCE("USDCAD")'}]};self.config.write_text(json.dumps(self.cfg))
  self.cells=[{'userEnteredValue':{'formulaValue':'=GOOGLEFINANCE("GBPUSD")'},'effectiveValue':{'numberValue':1.3}},{'userEnteredValue':{'formulaValue':'=GOOGLEFINANCE("USDBRL")*99%'},'effectiveValue':{'numberValue':5.2}},{'userEnteredValue':{'formulaValue':'=GOOGLEFINANCE("USDCAD")'},'effectiveValue':{'numberValue':1.4}}]
 def api(self,method,url,*args,**kwargs):
  self.calls.append((method,url));self.assertEqual(method,'GET');self.assertNotIn(sync.SHEET,url,'principal settlement workbook must not be accessed')
  if '/drive/' in url:return 200,{'id':'technical-sheet','driveId':'0AEwt4Ye690ocUk9PVA','trashed':False}
  return 200,{'sheets':[{'properties':{'title':'Sheet1'},'data':[{'startRow':0,'startColumn':0,'rowData':[{'values':self.cells}]}]}]}
 def collect(self):
  selectors={k:'service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']}
  with patch.dict(os.environ,selectors),patch.object(sync,'load_env'),patch.object(sync,'load_service_account',return_value={'client_email':'mgsagent@mgs-core-prod.iam.gserviceaccount.com','project_id':'mgs-core-prod'}),patch.object(sync,'service_account_access_token',return_value='test-only-not-a-credential'),patch.object(sync,'api_json',side_effect=self.api):return sync.collect(self.config)
 def test_monthly_fixed_rate_does_not_block_fresh_quotes(self):
  result=self.collect();self.assertEqual(result['values'],{BRL:5.2,CAD:1.4,GBP:1.3});self.assertEqual(result['google_writes'],0);self.assertEqual(result['spreadsheet_id'],'technical-sheet');self.assertEqual(result['extra_sources'][BRL]['range'],'B1')
 def test_manual_number_in_technical_source_is_rejected(self):
  self.cells[1]['userEnteredValue']={'numberValue':5.08}
  with self.assertRaisesRegex(RuntimeError,'quote_formula_changed'):self.collect()
 def test_nonfinite_effective_quote_is_rejected(self):
  self.cells[2]['effectiveValue']={'numberValue':float('nan')}
  with self.assertRaisesRegex(RuntimeError,'invalid_quote'):self.collect()
 def test_google_finance_loading_error_is_rejected(self):
  self.cells[1]['effectiveValue']={'errorValue':{'type':'N_A'}}
  with self.assertRaisesRegex(RuntimeError,'invalid_quote'):self.collect()
 def test_wrong_formula_cannot_change_spread(self):
  self.cells[1]['userEnteredValue']['formulaValue']='=GOOGLEFINANCE("USDBRL")'
  with self.assertRaisesRegex(RuntimeError,'quote_formula_changed'):self.collect()
 def test_missing_config_does_not_fall_back_to_settlement_source(self):
  self.config=pathlib.Path(self.tmp.name)/'missing.json'
  with self.assertRaises((RuntimeError,FileNotFoundError)):self.collect()
  self.assertEqual(self.calls,[])
 def corporate(self):
  # Same native Sheet moved by Rodolfo; this is not an alternate identity.
  sid='1Zk-b8OoaDHrvFtuerf5IuO2jx-phVWXMYi79yqVTZX4'
  self.cfg['spreadsheet_id']=sid;self.config.write_text(json.dumps(self.cfg))
  self.metadata={'id':sid,'trashed':False,'parents':['16fP9b4bp3inB1Gze95znQLYq3rdtTEhp'],'owners':[{'permissionId':'03783617840924670288','emailAddress':'mgsdigitalcorp@gmail.com'}],'capabilities':{'canEdit':True},'permissions':[{'id':'07414359829876449782','type':'user','role':'writer','emailAddress':'mgsagent@mgs-core-prod.iam.gserviceaccount.com'}]}
  old=self.api
  def api(method,url,*args,**kwargs):
   if '/drive/' in url:
    self.calls.append((method,url));self.assertEqual(method,'GET');return 200,self.metadata
   return old(method,url,*args,**kwargs)
  self.api=api
 def test_approved_corporate_same_id_collects_read_only(self):
  self.corporate();r=self.collect();self.assertEqual(r['google_writes'],0);self.assertEqual(len(r['values']),3);self.assertEqual(r['spreadsheet_id'],self.cfg['spreadsheet_id'])
 def reject_corporate(self):
  with self.assertRaisesRegex(RuntimeError,'drive_preflight_'):self.collect()
  self.assertEqual(len(self.calls),1,'Untrusted file must not reach Sheets')
 def test_corporate_wrong_parent_rejected(self):
  self.corporate();self.metadata['parents']=['wrong'];self.reject_corporate()
 def test_corporate_wrong_owner_native_id_rejected(self):
  self.corporate();self.metadata['owners'][0]['permissionId']='wrong';self.reject_corporate()
 def test_corporate_wrong_owner_email_rejected(self):
  self.corporate();self.metadata['owners'][0]['emailAddress']='wrong@example.com';self.reject_corporate()
 def test_corporate_missing_sa_access_rejected(self):
  self.corporate();self.metadata['permissions']=[];self.reject_corporate()
 def test_corporate_wrong_sa_native_id_rejected(self):
  self.corporate();self.metadata['permissions'][0]['id']='wrong';self.reject_corporate()
 def test_corporate_wrong_file_id_rejected(self):
  self.corporate();self.metadata['id']='another-sheet';self.reject_corporate()
 def test_corporate_trashed_rejected(self):
  self.corporate();self.metadata['trashed']=True;self.reject_corporate()
 def test_corporate_readonly_capability_rejected(self):
  self.corporate();self.metadata['capabilities']['canEdit']=False;self.reject_corporate()
 def test_corporate_other_drive_rejected(self):
  self.corporate();self.metadata['driveId']='unapproved-drive';self.reject_corporate()
 def test_unrelated_mydrive_sheet_cannot_use_exception(self):
  self.corporate();self.cfg['spreadsheet_id']='unapproved-sheet';self.config.write_text(json.dumps(self.cfg));self.metadata['id']='unapproved-sheet';self.reject_corporate()
if __name__=='__main__':unittest.main()
