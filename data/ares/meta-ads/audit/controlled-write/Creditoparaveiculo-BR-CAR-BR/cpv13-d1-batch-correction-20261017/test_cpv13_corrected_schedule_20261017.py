import importlib.util
import json
import unittest
from pathlib import Path
from datetime import datetime, timedelta

s=importlib.util.spec_from_file_location('runner','/root/.hermes/profiles/ares/scripts/cpv13-d1-restart-20261018-19.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
config=r.a.load_json(r.CONFIG)
jobs={x['id']:x for x in r.a.load_json(r.PROFILE/'cron/jobs.json')['jobs']}
operation=r.a.load_json(r.OP)

class CorrectedSchedule(unittest.TestCase):
 def test_exact_partition(self):
  self.assertEqual(set(config['batches']['18']['targets']),{'40','41'})
  self.assertEqual(set(config['batches']['19']['targets']),{'42','43'})
 def test_enabled_exact_jobs_and_no_early_activation(self):
  for batch,jid in [('18','b6dbf310a27e'),('19','051eb42132fd')]:
   cfg=config['batches'][batch];job=jobs[jid];st=r.a.load_json(r.paths(cfg)[0])
   self.assertTrue(job['enabled']);self.assertTrue(job['no_agent']);self.assertEqual(job['failure_deliver'],'local')
   target=datetime.fromisoformat(cfg['target_at_sp']);launch=datetime.fromisoformat(job['schedule']['run_at'])
   self.assertEqual((target-launch).total_seconds(),70)
   self.assertEqual(st['status'],'SCHEDULED');self.assertEqual(st['cron_job_id'],jid)
   self.assertTrue(all(r.a.configured(row)=='PAUSED' for row in st['prepared'].values()))
 def test_supersession_and_operational_d1(self):
  for old in config['superseded_batches'].values():
   st=r.a.load_json(r.paths({'request_id':old})[0])
   self.assertEqual(st['status'],'SUPERSEDED_BY_RODOLFO_CORRECTION')
   self.assertEqual(operation['scheduled_operations'][old]['state'],st['status'])
  allowed=operation['management_scope']['autonomous_action_scope']['allowed_campaigns']
  for cfg in config['batches'].values():
   for n in cfg['targets']:
    self.assertEqual(allowed[n]['cycle_start_date'],cfg['target_at_sp'][:10])
    self.assertFalse(allowed[n]['actions_enabled'])
    self.assertEqual(allowed[n]['cycle_restart_request'],cfg['request_id'])
 def test_preserved_budgets_guard_reset_and_frozen_jobs(self):
  guard=r.a.load_json(r.GUARD)['campaigns']
  for cfg in config['batches'].values():
   state=r.a.load_json(r.paths(cfg)[0])
   for n,target in cfg['targets'].items():
    self.assertEqual(int(state['prepared'][n]['daily_budget']),2500 if n=='43' else 3000)
    self.assertFalse(state.get('activation'));g=guard[target['campaign_id']]
    self.assertEqual(g['reset_request_id'],cfg['request_id'])
    self.assertEqual(g['morning_estimated_roi'],{});self.assertEqual(g['morning_actual_roi'],{})
    self.assertEqual(g['consecutive_16h_failures'],0)
  for jid in ['2cf8115a4f8b','9532b8be5aa2','5d0974e97ebd','990b3e644f36']:
   self.assertFalse(jobs[jid]['enabled'])

if __name__=='__main__':unittest.main(verbosity=2)
