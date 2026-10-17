"""OFFLINE rewarded QA fixtures; never evidence of live ad delivery."""
import sys,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import landing_rewarded as rw,landing_mobile as mobile,landing_lean as lean
M=dict(device_toolbar_enabled=True,device_name='iPhone 16',viewport_width=393,viewport_height=852,viewport_bounds=[806,188,393,852],verified=True,verified_at=90)
P=dict(device_name='iPhone 16',viewport_width=393,viewport_height=852,minimum_seconds=20,maximum_seconds=30,target_seconds=22,effective_at_epoch=99,rewarded_gate=dict(enabled=True,authority_message_id='1561047502944477287',effective_at_epoch=99,maximum_wait_seconds=180,observation_target_seconds=25))
TARGET=dict(pid=1,window_id=2,app_name='chrome.exe')

def state(gate=False,reward=False,article=False,excerpt=''):
    return dict(active_normal_chrome=True,site_gate_visible=gate,rewarded_visible=reward,article_visible=article,network_ad_visible=reward,cta_label='CLAIM MY FREE PRODUCTS' if gate else '',cta_bounds=[850,600,300,44] if gate else [0,0,0,0],article_excerpt=excerpt,description='OFFLINE fixture')

class RewardedTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(rw,'coordinate_scale',return_value=1);p.start();self.addCleanup(p.stop)
    def call(self,a):return {'ok':True,'effect':'confirmed','elements':[]}
    def test_only_exact_site_cta_not_ad_buttons(self):
        good=state(gate=True);a=rw.gate_click_args(self.call,TARGET,good,M);self.assertEqual(a['action'],'click')
        for label in ['Learn more','Shop now','Claim reward','']:
            bad=dict(good,cta_label=label)
            with self.assertRaises(ValueError):rw.gate_click_args(self.call,TARGET,bad,M)
    def test_refuses_button_outside_mobile_viewport(self):
        bad=state(gate=True);bad['cta_bounds']=[1300,600,300,44]
        with self.assertRaises(ValueError):rw.gate_click_args(self.call,TARGET,bad,M)
    def test_coordinates_are_image_relative_not_native_pixels(self):
        with patch.object(rw,'coordinate_scale',return_value=.56875):
            args=rw.gate_click_args(self.call,TARGET,state(gate=True),M)
        self.assertEqual(args['coordinate'],[568,353])
        point=rw.delivered_point({'message':'Posted click to Chromium pid1 at (1763,1130) (background)'})
        self.assertFalse(rw.point_inside(point,M['viewport_bounds']))
    def test_clock_starts_after_article_and_scroll_not_rewarded(self):
        e=dict(mobile_emulation=M,opened_at=100,closed_at=190,tab_open_seconds=90,article_verified=True,article_ready_at=160,scroll_visual_changed=True,observation_started_at=162,observation_ended_at=187,observation_seconds=25,visual_captured_at=187)
        mobile.validate_mobile(e,P)
        for change in [dict(observation_started_at=150),dict(scroll_visual_changed=False),dict(article_verified=False),dict(observation_seconds=10)]:
            with self.assertRaises(ValueError):mobile.validate_mobile(dict(e,**change),P)
    def test_wait_then_scroll_and_single_site_click(self):
        for ad in [True,False]:
            clock=[100.0];calls=[];states=iter([state(gate=True),state(reward=True),state(article=True,excerpt='before'),state(article=True,excerpt='after')])
            def call(a):calls.append(a);return self.call(a)
            def pause(n):clock[0]+=n
            def opening(call,url,persist,configure,verify_url):
                configure(TARGET);proof=dict(target=TARGET,new_window_created=True,new_tab_created=True,browser_mode='NORMAL',opened_at=clock[0],state='NAVIGATION_SUBMITTED');persist(proof);return proof
            def closure(call,proof):clock[0]+=2;return dict(closed_at=clock[0],tab_closed_verified=True,other_tabs_preserved=True)
            with tempfile.TemporaryDirectory() as tmp:
                number=[0]
                def capture():
                    number[0]+=1;p=Path(tmp)/(str(number[0])+'.png');p.write_bytes(b'OFFLINE fixture');os.utime(p,(clock[0],clock[0]));return {'screenshot_path':str(p)}
                def review(shot,prompt):
                    data=next(states) if prompt==rw.STATE_PROMPT else dict(network_ad_visible=ad,active_normal_chrome=True,unobstructed=True,landing_loaded=True,description='OFFLINE final ad fixture')
                    return dict(success=True,analysis=json.dumps(data))
                with patch.object(rw,'policy',return_value=P),patch.object(mobile,'policy',return_value=P),patch.object(rw,'configure_mobile',return_value=M),patch.object(lean,'open_normal',side_effect=opening),patch.object(lean,'close_normal',side_effect=closure):
                    result,e=rw.observe_rewarded(call,'https://example.invalid/lp','offline',read_mobile=lambda:None,capture_visual=capture,review_visual=review,on_owned=lambda p:None,pause=pause,clock=lambda:clock[0],monotonic=lambda:clock[0])
            self.assertEqual(result,'PASS' if ad else 'NO_AD');self.assertEqual(e['observation_seconds'],25);self.assertTrue(e['scroll_visual_changed']);self.assertEqual(sum(a['action']=='click' for a in calls),1);self.assertEqual(sum(a.get('keys')=='pagedown' for a in calls),1);self.assertTrue(e['tab_closed_verified'])
    def test_rewarded_route_is_shared_by_normal_observer(self):
        with patch.object(mobile,'policy',return_value=P),patch.object(rw,'observe_rewarded',return_value=('OFFLINE',{})) as fn:
            mobile.observe_mobile(None,'url','source',read_mobile=None,capture_visual=None,review_visual=None,on_owned=lambda v:None);fn.assert_called_once()

if __name__=='__main__':unittest.main()
