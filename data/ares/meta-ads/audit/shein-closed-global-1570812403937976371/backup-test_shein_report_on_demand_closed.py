"""Authenticated on-demand closed dates remain separate from recurring D-1."""
import unittest,importlib.util,json,copy
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
HOME=Path('/root/.hermes/profiles/ares')
spec=importlib.util.spec_from_file_location('on_demand_layout_test',HOME/'scripts/shein-report-layout.py');layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
BINDINGS=json.loads(Path('/root/mgs-agent/data/ares/discord/shein-intraday-report-bindings.json').read_text())['bindings']
class OnDemandClosedTests(unittest.TestCase):
 def setUp(self):
  self.mid='1999999999999999999';self.user='1055570806945620030';self.day='2026-10-19'
  self.binding=next(b for b in BINDINGS if b['account_id']=='787796726891306')
  self.req={'date':self.day,'source_message_id':self.mid,'source_thread_id':self.binding['thread_id'],'requester_discord_id':self.user,'request_text':'Gere intraday dia 19/10/26','bindings':[self.binding],'mode':'on_demand_read_only','meta_writes':0}
  self.proof={'message':{'id':self.mid,'channel_id':self.binding['thread_id'],'author':{'id':self.user,'bot':False},'content':self.req['request_text']},'origin':{'id':self.binding['thread_id'],'parent_id':self.binding['channel_id']}}
  self.closed={'kind':'on_demand','source_message_id':self.mid,'period':{'since':self.day,'until':self.day},'day_closed':True}
  self.model={'account':{'id':self.binding['account_id']},'date':self.day,'closed_day_report':self.closed,'rows':[]}
  real=Path.read_text
  def reader(path,*a,**kw):
   if str(path).endswith('/shein-on-demand-requests/'+self.mid+'/request.json'):return json.dumps(self.req)
   if str(path).endswith('/shein-on-demand-requests/'+self.mid+'/authorization-readback.json'):return json.dumps(self.proof)
   return real(path,*a,**kw)
  self.mock=patch.object(Path,'read_text',reader);self.mock.start();self.addCleanup(self.mock.stop)
 def check(self,model=None,cutoff='2026-10-20T02:00:00-04:00',budget='2026-10-20T02:01:00-04:00'):
  return layout.validate_on_demand_closed_day(model or self.model,datetime.fromisoformat(cutoff),datetime.fromisoformat(budget))
 def test_explicit_request_passes_without_recurring_policy(self):self.check()
 def test_older_explicit_date_not_forced_to_yesterday(self):self.check(cutoff='2026-10-22T02:00:00-04:00',budget='2026-10-22T02:01:00-04:00')
 def test_current_date_and_stale_budget_rejected(self):
  for kwargs in [{'cutoff':'2026-10-19T23:59:00-04:00'},{'budget':'2026-10-19T23:59:00-04:00'}]:
   with self.assertRaises(layout.LayoutError):self.check(**kwargs)
 def test_wrong_origin_parent_author_bot_and_date_rejected(self):
  baseline=copy.deepcopy(self.proof)
  mutations=[lambda p:p['message']['author'].update(id='123'),lambda p:p['message']['author'].update(bot=True),lambda p:p['origin'].update(parent_id='123'),lambda p:p['origin'].update(id='123'),lambda p:p['message'].update(content='Gere agora'),lambda p:p['message'].update(content='Gere dia 18/10/26')]
  for fn in mutations:
   self.proof=copy.deepcopy(baseline);fn(self.proof)
   with self.assertRaises(layout.LayoutError):self.check()
 def test_wrong_account_partial_and_false_closed_rejected(self):
  for mutation in [lambda x:x['account'].update(id='123'),lambda x:x.update(rows=[{'history':[{'partial':True}]}]),lambda x:x['closed_day_report'].update(day_closed=False),lambda x:x['closed_day_report']['period'].update(until='2026-10-18')]:
   model=copy.deepcopy(self.model);mutation(model)
   with self.assertRaises(layout.LayoutError):self.check(model)
 def test_g006_multicount_and_excluded_schedule_accounts(self):
  for b in [b for b in BINDINGS if b['manager_code']=='g006']:
   self.req.update(bindings=[b],source_thread_id='1567162580273729629')
   self.proof['message']['channel_id']='1567162580273729629';self.proof['origin']={'id':'1567162580273729629','parent_id':b['channel_id']}
   model=copy.deepcopy(self.model);model['account']['id']=b['account_id'];self.check(model)
 def test_full_renderer_preserves_finance_and_labels_current_reads(self):
  model=json.loads(Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/g001-status-blocks-1561918043305803869/787796726891306/model.json').read_text());model['rows']=model['rows'][:1]
  for key in ['insights','configuration','status','budget']:model['source_timestamps'][key]='2026-10-20T02:00:00-04:00'
  for row in model['rows']:
   for h in row['history']:h['partial']=False
  model['closed_day_report']=self.closed
  before=copy.deepcopy(model);result=layout.render_model(model);layout.validate_report(model,result['text'],self.binding['thread_id'])
  self.assertEqual(before,model);self.assertIn('Relatório pontual: 19/10/2026',result['text']);self.assertIn('coleta em 20/10 02:00 EDT',result['text']);self.assertIn('ATRASO GAM/SB ATUAL',result['text']);self.assertNotIn('Diário D-1:',result['text'])
if __name__=='__main__':unittest.main()
