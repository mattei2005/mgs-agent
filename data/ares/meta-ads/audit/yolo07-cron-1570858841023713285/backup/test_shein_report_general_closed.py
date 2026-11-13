"""CEO all36 closed-day requests from SHEIN general remain tightly scoped."""
import sys,copy,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_shein_report_on_demand_closed import OnDemandClosedTests,BINDINGS,layout
class GeneralClosedDayTests(OnDemandClosedTests):
 def general(self):
  self.user='344196393512075265';self.day='2026-11-12'
  self.req.update(date=self.day,source_thread_id='1570801075621986305',requester_discord_id=self.user,request_text='vai enviar o report do dia fechado de ontem e depois o intraday de agora em todos os canais',bindings=copy.deepcopy(BINDINGS),operation_id='SHEIN-US-DIRECT',scope='all36_account_threads')
  self.proof['message'].update(channel_id=self.req['source_thread_id'],author={'id':self.user,'bot':False},content=self.req['request_text'],timestamp='2026-11-13T14:47:00+00:00')
  self.proof['origin']={'id':self.req['source_thread_id'],'parent_id':'1549404457157140601','type':11}
  self.model['date']=self.day;self.model['account']['timezone_name']='America/New_York';self.model['closed_day_report']['period']={'since':self.day,'until':self.day}
 def gcheck(self):return self.check(cutoff='2026-11-13T10:00:00-05:00',budget='2026-11-13T10:01:00-05:00')
 def test_general_all36_relative_yesterday_passes(self):
  self.general()
  for b in BINDINGS:
   self.model['account']['id']=b['account_id'];self.gcheck()
 def test_general_wrong_author_blocked(self):
  self.general();self.proof['message']['author']['id']=self.req['requester_discord_id']='1055570806945620030'
  with self.assertRaises(layout.LayoutError):self.gcheck()
 def test_general_wrong_parent_blocked(self):
  self.general();self.proof['origin']['parent_id']='123'
  with self.assertRaises(layout.LayoutError):self.gcheck()
 def test_general_incomplete_and_duplicated_bindings_blocked(self):
  self.general();original=copy.deepcopy(self.req['bindings'])
  for bs in [original[:-1],original[:-1]+[original[0]]]:
   self.req['bindings']=bs
   with self.assertRaises(layout.LayoutError):self.gcheck()
 def test_general_wrong_relative_date_blocked(self):
  self.general();self.proof['message']['timestamp']='2026-11-14T14:47:00+00:00'
  with self.assertRaises(layout.LayoutError):self.gcheck()
 def test_general_missing_scope_or_timestamp_blocked(self):
  self.general();self.req.pop('scope')
  with self.assertRaises(layout.LayoutError):self.gcheck()
  self.general();self.proof['message'].pop('timestamp')
  with self.assertRaises(layout.LayoutError):self.gcheck()
 def test_general_explicit_conflicting_date_blocked(self):
  self.general();self.req['request_text']+=' 11/11/2026';self.proof['message']['content']=self.req['request_text']
  with self.assertRaises(layout.LayoutError):self.gcheck()
if __name__=='__main__':unittest.main()
