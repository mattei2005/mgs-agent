import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

P=Path('/root/.hermes/profiles/ares/scripts/cpv13-d1-restart-20261018-19.py')
s=importlib.util.spec_from_file_location('runner',P);r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
CFG=r.a.load_json(r.CONFIG)['batches']
LIVE={n:row for cfg in CFG.values() for n,row in r.a.load_json(r.paths(cfg)[0])['prepared'].items()}
LIVE['32']={'configured_status':'DELETED'}
spec=importlib.util.spec_from_file_location('reports','/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py')
reports=importlib.util.module_from_spec(spec);spec.loader.exec_module(reports)

class Tests(unittest.TestCase):
 def test_before_time(self):
  for cfg in CFG.values():
   with self.assertRaisesRegex(r.a.ActionError,'before_activation'):
    r.time_gate(cfg,datetime.fromisoformat(cfg['target_at_sp'])-timedelta(seconds=1))
 def test_late_time(self):
  with self.assertRaisesRegex(r.a.ActionError,'late_activation'):
   r.time_gate(CFG['18'],datetime.fromisoformat(CFG['18']['target_at_sp'])+timedelta(minutes=11))
 def test_on_time(self):
  r.time_gate(CFG['18'],datetime.fromisoformat(CFG['18']['target_at_sp']))
 def test_replay_no_meta(self):
  with patch.object(r,'live',side_effect=AssertionError('must not call Meta')):
   r.activate(CFG['18'],None,None,{'status':'COMPLETE_ACTIVATED'})
 def test_early_no_meta(self):
  with patch.object(r,'live',side_effect=AssertionError('must not call Meta')):
   with self.assertRaisesRegex(r.a.ActionError,'before_activation'):
    r.activate(CFG['18'],None,None,{'status':'SCHEDULED','prepared':{}})
 def test_live_ready(self):
  for cfg in CFG.values():r.validate(cfg,{n:LIVE[n] for n in cfg['targets']})
 def test_budget_drift(self):
  cfg=CFG['18'];rows={n:copy.deepcopy(LIVE[n]) for n in cfg['targets']};base=copy.deepcopy(rows)
  rows['41']['daily_budget']='3100'
  with self.assertRaisesRegex(r.a.ActionError,'material_drift'):r.validate(cfg,rows,base)
 def test_hierarchy_drift(self):
  cfg=CFG['18'];rows={n:copy.deepcopy(LIVE[n]) for n in cfg['targets']}
  rows['41']['ads']['data'][0]['configured_status']='PAUSED'
  with self.assertRaisesRegex(r.a.ActionError,'hierarchy_not_ready'):r.validate(cfg,rows)
 def test_deleted_c32_excluded(self):
  self.assertEqual(LIVE['32']['configured_status'],'DELETED')
  self.assertTrue(all('32' not in cfg['targets'] for cfg in CFG.values()))
 def test_date_preserves_wrapper_copy(self):
  for cfg in CFG.values():
   for n in cfg['targets']:
    name=r.desired_name(LIVE[n]['name'],datetime.fromisoformat(cfg['target_at_sp']))
    self.assertIn('(b01fb13c'+n+')',name)
    if n=='40':self.assertTrue(name.endswith('COPY C12'))
 def test_real_creation_audits(self):
  for cfg in CFG.values():
   for t in cfg['targets'].values():self.assertTrue(Path(r.creation_proof(t)).exists())
 def test_cycle_commit_preserves_history_and_provenance(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'state').mkdir()
   op=root/'op.json';guard=root/'guard.json';audit=root/'audit'
   initial=r.a.load_json(r.OP)
   r.a.atomic_json(op,initial)
   r.a.atomic_json(guard,{'campaigns':{LIVE['41']['id']:{'morning_estimated_roi':{'D1':-50},'pending_reactivation':{'due_date':'2026-10-17'},'consecutive_16h_failures':2}}})
   cfg=CFG['18'];prepared={n:copy.deepcopy(LIVE[n]) for n in cfg['targets']}
   state={'prepared':prepared,'status':'SCHEDULE_PENDING'}
   with patch.object(r,'PROFILE',root),patch.object(r,'OP',op),patch.object(r,'GUARD',guard),patch.object(r,'paths',return_value=(root/'request.json',audit)):
    r.commit(cfg,state);first=r.a.load_json(op)
    r.commit(cfg,state);second=r.a.load_json(op)
    self.assertEqual(first,second)
    self.assertEqual(first['management_scope']['autonomous_action_scope']['allowed_campaigns']['41']['cycle_start_date'],'2026-10-18')
    g=r.a.load_json(guard)['campaigns'][LIVE['41']['id']]
    self.assertEqual(g['morning_estimated_roi'],{});self.assertEqual(g['consecutive_16h_failures'],0)
    self.assertNotIn('pending_reactivation',g)
    self.assertEqual(r.a.load_json(audit/'previous-guard-C41.json')['consecutive_16h_failures'],2)
    reports.validated_allowed_campaigns(first)
    final=copy.deepcopy(prepared)
    for row in final.values():row['configured_status']=row['status']='ACTIVE'
    state['activation_final_readback']=final
    r.commit(cfg,state,activated=True)
    active=r.a.load_json(op);allowed=reports.validated_allowed_campaigns(active)
    for n in cfg['targets']:
     self.assertTrue(reports._operational_d1_restart_audits_prove_campaign(n,allowed[n]))
     broken=copy.deepcopy(allowed[n]);broken['cycle_start_date']='2026-10-19'
     self.assertFalse(reports._operational_d1_restart_audits_prove_campaign(n,broken))
    self.assertEqual(len(allowed['41']['cycle_history']),len(first['management_scope']['autonomous_action_scope']['allowed_campaigns']['41']['cycle_history']))

if __name__=='__main__':unittest.main(verbosity=2)
