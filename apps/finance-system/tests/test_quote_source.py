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
if __name__=='__main__':unittest.main()
