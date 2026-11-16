"""Expired immediate plan + contextual OK, with immutable approved artifacts."""
import copy,json,time,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import Mock,patch
import test_eggbev_cross_account_clone as fixtures
from ares_campaign_v3 import eggbev_cross_account as c,cross_clone_immediate as clock,schema
from ares_campaign_v3.prevalidation import prevalidate_payload,content_digest
from ares_campaign_v3 import eggbev_creation_naming as naming

class ImmediateTests(unittest.TestCase):
 def setUp(self):
  self.b=fixtures.CrossTests('test_01_new_mode_shape_and_five_by_three_order');self.b.setUp();self.addCleanup(self.b.doCleanups)
  raw=self.b.draft();now=datetime.now(timezone.utc);self.old=(now-timedelta(hours=1)).isoformat();raw['created_at']=(now-timedelta(hours=2)).isoformat()
  for row in raw['campaigns']:row['start_time']=self.old
  class Past(datetime):
   @classmethod
   def now(cls,tz=None):return datetime.now(tz)-timedelta(days=2)
  with patch.object(schema,'datetime',Past),patch.object(clock,'datetime',Past):self.raw=prevalidate_payload(raw,self.b.reg)
  self.proof={'request_id':self.b.q['request_id'],'approved_digest':content_digest(self.raw),'approval_message_id':'1571717806532329475','summary_message_id':'1571713566728396904','author_id':c.CEO,'verified_at_monotonic':time.monotonic()}
 def admit(self,**kw):return clock.admission(kw.get('q',self.b.q),kw.get('raw',self.raw),kw.get('cfg',self.b.cfg),kw.get('proof',self.proof))
 def parsed(self):
  with self.admit():return schema.Manifest.from_dict(self.raw)
 def execute(self,fake):
  with self.admit():
   m=schema.Manifest.from_dict(self.raw);marker=c.CURRENT.set({**self.proof,'digest':m.digest})
   try:
    with patch.object(naming,'allocation',return_value=self.b.allocation):return self.b.engine(fake).execute(m)
   finally:c.CURRENT.reset(marker)
 def test_01_elapsed_requires_scoped_live_admission(self):
  with self.assertRaises(ValueError):schema.Manifest.from_dict(self.raw)
  before=copy.deepcopy(self.raw);self.assertEqual(len(self.parsed().campaigns),5);self.assertEqual(before,self.raw)
  with self.assertRaises(ValueError):schema.Manifest.from_dict(self.raw)
 def test_02_old_or_wrong_approval_denied(self):
  for delta in [{'approved_digest':'0'*64},{'verified_at_monotonic':time.monotonic()-200},{'author_id':'other'},{'approval_message_id':'123'}]:
   with self.subTest(delta=delta),self.assertRaises(ValueError):
    with self.admit(proof={**self.proof,**delta}):pass
 def test_03_non_immediate_request_denied(self):
  q=copy.deepcopy(self.b.q);q['start_intent']='SCHEDULED'
  with self.assertRaises(ValueError):
   with self.admit(q=q):pass
 def test_04_missing_allowlist_denied(self):
  cfg=copy.deepcopy(self.b.cfg);cfg['accounts'][c.TARGET]['campaign_policy']['immediate_start_request_ids']=[]
  with self.assertRaises(ValueError):
   with self.admit(cfg=cfg):pass
 def test_05_payload_delta_not_admitted(self):
  with self.admit():
   raw=copy.deepcopy(self.raw);raw['campaigns'][0]['name']+=' changed'
   with self.assertRaises(ValueError):schema.Manifest.from_dict(raw)
 def test_06_actual_five_new_shells_have_safe_starts_original_plan_unchanged(self):
  before=copy.deepcopy(self.raw);fake=self.b.fake();out=self.execute(fake);self.assertEqual(out['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(len(out['campaign_ids']),5)
  adsets=[x for x in fake.objects.values() if x.get('_kind')=='adset'];self.assertEqual(len(adsets),5)
  self.assertTrue(all(datetime.fromisoformat(a['start_time'])>datetime.now(timezone.utc) for a in adsets));self.assertEqual(self.raw,before)
 def test_07_crash_resume_preserves_existing_adset_starts(self):
  fake=self.b.fake(crash_seed=True)
  with self.assertRaises(KeyboardInterrupt):self.execute(fake)
  existing={x['id']:x['start_time'] for x in fake.objects.values() if x.get('_kind')=='adset'}
  out=self.execute(fake);self.assertEqual(len(out['campaign_ids']),5)
  self.assertTrue(all(fake.objects[k]['start_time']==v for k,v in existing.items()))
  self.assertEqual(len([x for x in fake.objects.values() if x.get('_kind')=='campaign']),5)
 def test_08_journal_tamper_denied(self):
  fake=self.b.fake();self.execute(fake)
  cp=json.loads((Path(self.b.cfg['state_root'])/'checkpoints'/(self.b.q['request_id']+'-'+c.TARGET+'.json')).read_text());record=next(r for r in cp['bundles'] if r.get('cross_immediate_starts'));spec=self.parsed().campaigns[0]
  record['cross_immediate_starts']['1']['effective_start_time']=self.old
  with self.assertRaises(ValueError):clock.expected_start(spec,record,1)
 def test_09_future_start_unchanged_without_clock_entry(self):
  spec=self.b.manifest().campaigns[0];record={};self.assertEqual(clock.new_adset_start(Mock(),spec,record,1),spec.start_time);self.assertFalse(record)
 def test_10_missing_engine_authority_denied(self):
  spec=self.parsed().campaigns[0];engine=self.b.engine(self.b.fake())
  with self.assertRaises(ValueError):clock.new_adset_start(engine,spec,{},1)
 def test_11_contextual_OK_is_real_immediate_predecessor_not_fabricated_reply(self):
  summary,sent,ok,common=self.b.approval_fixture();ok['message_reference']=None
  common.discord_request.side_effect=lambda method,path:(200,[copy.deepcopy(sent)] if '?before=' in path else copy.deepcopy(ok if path.endswith(ok['id']) else sent))
  with patch.object(c,'home_for',return_value=self.b.root):payload,proof=c.final_approval(self.b.q,summary,common,ok['id'],summary['digest'],return_proof=True)
  self.assertEqual(proof['context'],'directly_after_exact_summary');self.assertIsNone(ok['message_reference']);self.assertEqual(payload['request_id'],self.b.q['request_id'])
 def test_12_intervening_message_makes_unreferenced_OK_ambiguous(self):
  summary,sent,ok,common=self.b.approval_fixture();ok['message_reference']=None
  common.discord_request.side_effect=lambda method,path:(200,[{'id':'999999999999999999'}] if '?before=' in path else copy.deepcopy(ok if path.endswith(ok['id']) else sent))
  with patch.object(c,'home_for',return_value=self.b.root),self.assertRaises(ValueError):c.final_approval(self.b.q,summary,common,ok['id'],summary['digest'])
 def test_13_wrong_explicit_reply_denied(self):
  summary,sent,ok,common=self.b.approval_fixture();ok['message_reference']={'message_id':'999999999999999999'}
  with patch.object(c,'home_for',return_value=self.b.root),self.assertRaises(ValueError):c.final_approval(self.b.q,summary,common,ok['id'],summary['digest'])
 def test_14_completion_reports_actual_starts_from_live_trees(self):
  fake=self.b.fake();self.execute(fake);cp=json.loads((Path(self.b.cfg['state_root'])/'checkpoints'/(self.b.q['request_id']+'-'+c.TARGET+'.json')).read_text())
  from ares_campaign_v3.eggbev_cross_account_completion import completion_proof
  proof=completion_proof(self.b.q,self.raw,cp,[r for r in cp['bundles'] if r.get('status')=='COMPLETE'],self.b.assets)
  self.assertEqual(len(proof['actual_start_times']),5);self.assertTrue(all(v!=self.old for v in proof['actual_start_times'].values()))

if __name__=='__main__':unittest.main()
