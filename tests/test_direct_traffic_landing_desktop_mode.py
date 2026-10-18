"""Offline normal-desktop mode regressions; not production observation evidence."""
import sys,json,os,tempfile,unittest,copy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import landing_desktop_observation as desktop,landing_rewarded as rw,landing_lean as lean
from test_direct_traffic_landing_rewarded import state,TARGET
P={'enabled':True,'device_mode':'DESKTOP','effective_at_epoch':99,'minimum_seconds':20,'maximum_seconds':30,'rewarded_gate':{'enabled':True,'authority_message_id':'1561047502944477287','maximum_wait_seconds':180,'observation_target_seconds':25}}
V={'desktop_view':True,'device_toolbar_visible':False,'viewport_bounds':[0,120,1920,960],'verified':True,'verified_at':90,'device_mode':'DESKTOP'}
class DesktopTests(unittest.TestCase):
 def evidence(self):return dict(device_mode='DESKTOP',desktop_view=dict(V),opened_at=100,article_verified=True,article_ready_at=102,scroll_visual_changed=True,observation_started_at=104,observation_ended_at=129,observation_seconds=25,visual_captured_at=129,closed_at=131)
 def test_valid_desktop(self):desktop.validate(self.evidence(),P)
 def test_invalid_time_and_scroll(self):
  for change in [dict(observation_seconds=10),dict(observation_seconds=float('nan')),dict(scroll_visual_changed=False),dict(article_ready_at=110),dict(visual_captured_at=103)]:
   with self.assertRaises(ValueError):desktop.validate(dict(self.evidence(),**change),P)
 def test_mobile_proof_rejected(self):
  e=self.evidence();e['mobile_emulation']={'verified':True}
  with self.assertRaises(ValueError):desktop.validate(e,P)
 def test_emulation_or_narrow_window_rejected(self):
  for change in [dict(device_toolbar_visible=True),dict(desktop_view=False),dict(viewport_bounds=[0,0,393,852])]:
   e=self.evidence();e['desktop_view'].update(change)
   with self.assertRaises(ValueError):desktop.validate(e,P)
 def test_dispatch_desktop_to_shared_rewarded_not_mobile(self):
  with patch.object(desktop,'policy',return_value=P),patch.object(rw,'observe_rewarded',return_value=('OFFLINE',{})) as fn,patch('ares_campaign_v3.landing_mobile.observe_mobile',side_effect=AssertionError('mobile forbidden')):
   self.assertEqual(lean.observe_prepared(None,None,'url','source')[0],'OFFLINE');self.assertEqual(fn.call_args.kwargs['desktop_config'],P)
 def test_desktop_and_mobile_mutually_exclusive_policy(self):
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   root=Path(tmp);p=root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'active_observation_route':{'desktop_observation':{'enabled':True},'mobile_emulation':{'enabled':True}}}))
   with patch.object(desktop.core,'BASE',root):
    with self.assertRaises(ValueError):desktop.policy()
 def test_shared_desktop_observes25_then_closes_and_reviews(self):
  for ad,initial_ad in [(True,False),(False,False),(False,True)]:
   clock=[100.0];events=[];states=iter([state(article=True,excerpt='before'),state(article=True,excerpt='after')])
   def opening(call,url,persist,configure,verify_url):
    configure(TARGET);p=dict(target=TARGET,new_window_created=True,new_tab_created=True,browser_mode='NORMAL',opened_at=clock[0],state='NAVIGATION_SUBMITTED');persist(p);return p
   def closure(call,proof):events.append('close');clock[0]+=1;return dict(closed_at=clock[0],tab_closed_verified=True,other_tabs_preserved=True)
   with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
    n=[0]
    def capture():
     n[0]+=1;p=Path(tmp)/(str(n[0])+'.png');p.write_bytes(b'OFFLINE');os.utime(p,(clock[0],clock[0]));return {'screenshot_path':str(p)}
    def review(shot,prompt):
     if prompt==rw.STATE_PROMPT.replace('mobile viewport','desktop viewport'):data=next(states)
     else:events.append('review');data=dict(network_ad_visible=(initial_ad if Path(shot['screenshot_path']).stem=='1' else ad),active_normal_chrome=True,unobstructed=True,landing_loaded=True,description='OFFLINE desktop fixture')
     return {'success':True,'analysis':json.dumps(data)}
    with patch.object(desktop,'configure',return_value=V),patch.object(lean,'open_normal',side_effect=opening),patch.object(lean,'close_normal',side_effect=closure):
     result,e=rw.observe_rewarded(lambda a:{'ok':True,'effect':'confirmed'},'https://example.invalid/lp','offline',read_mobile=None,capture_visual=capture,review_visual=review,on_owned=lambda p:None,pause=lambda n:clock.__setitem__(0,clock[0]+n),clock=lambda:clock[0],monotonic=lambda:clock[0],desktop_config=P)
   self.assertEqual(result,'PASS' if ad or initial_ad else 'NO_AD');self.assertEqual(e['device_mode'],'DESKTOP');self.assertNotIn('mobile_emulation',e);self.assertEqual(e['observation_seconds'],25);self.assertEqual(events,['close','review'] if ad else ['close','review','review'])
   if initial_ad:self.assertEqual(e['ad_confirmation_stage'],'ARTICLE_BEFORE_SCROLL');self.assertFalse(e['final_visual']['network_ad_visible'])
if __name__=='__main__':unittest.main()
