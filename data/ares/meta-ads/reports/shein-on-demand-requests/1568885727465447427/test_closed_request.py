import importlib.util,json,copy,unittest
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('layout','/root/.hermes/profiles/ares/scripts/shein-report-layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GateTest(unittest.TestCase):
 def test_real_authenticated_request(self):
  req=json.loads((ROOT/'request.json').read_text())
  for b in req['bindings']:
   model={'account':{'id':b['account_id']},'date':req['date'],'closed_day_report':{'kind':'on_demand','source_message_id':req['source_message_id'],'period':{'since':req['date'],'until':req['date']},'day_closed':True},'rows':[]}
   m.validate_on_demand_closed_day(model,datetime.fromisoformat('2026-11-08T02:30:00-05:00'),datetime.fromisoformat('2026-11-08T02:31:00-05:00'))
 def test_invalid_evidence(self):
  req=json.loads((ROOT/'request.json').read_text());aid=req['bindings'][0]['account_id'];base={'account':{'id':aid},'date':req['date'],'closed_day_report':{'kind':'on_demand','source_message_id':req['source_message_id'],'period':{'since':req['date'],'until':req['date']},'day_closed':True},'rows':[]}
  mutations=[lambda x:x['closed_day_report'].update(source_message_id='no'),lambda x:x['account'].update(id='123456789'),lambda x:x.update(date='2026-11-06'),lambda x:x['closed_day_report'].update(day_closed=False),lambda x:x.update(rows=[{'history':[{'partial':True}]}])]
  for fn in mutations:
   x=copy.deepcopy(base);fn(x)
   with self.assertRaises(m.LayoutError):m.validate_on_demand_closed_day(x,datetime.fromisoformat('2026-11-08T02:30:00-05:00'),datetime.fromisoformat('2026-11-08T02:31:00-05:00'))
  with self.assertRaises(m.LayoutError):m.validate_on_demand_closed_day(base,datetime.fromisoformat('2026-11-07T23:30:00-05:00'),datetime.fromisoformat('2026-11-08T02:31:00-05:00'))
  with self.assertRaises(m.LayoutError):m.validate_on_demand_closed_day(base,datetime.fromisoformat('2026-11-08T02:30:00-05:00'),datetime.fromisoformat('2026-11-07T23:30:00-05:00'))
if __name__=='__main__':unittest.main()
