"""OFFLINE fixtures: native mobile setup and bounded residence; no ad evidence."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from ares_campaign_v3 import landing_mobile as mobile
from ares_campaign_v3 import landing_lean as lean

P=dict(device_name='iPhone 16',viewport_width=393,viewport_height=852,minimum_seconds=20,maximum_seconds=30,target_seconds=22,effective_at_epoch=99)
M=dict(device_toolbar_enabled=True,device_name='iPhone 16',viewport_width=393,viewport_height=852,viewport_bounds=[600,200,393,852],verified=True,verified_at=90,source='offline_fixture')
TARGET=dict(pid=1,window_id=2,app_name='chrome.exe')

class MobileTests(unittest.TestCase):
    def evidence(self):return dict(mobile_emulation=dict(M),opened_at=100,closed_at=125,tab_open_seconds=25,visual_captured_at=122)
    def test_valid_mobile_and_residence(self):mobile.validate_mobile(self.evidence(),P)
    def test_reject_short_long_nan(self):
        for dwell in [10,19.99,30.01,float('nan')]:
            e=self.evidence();e.update(tab_open_seconds=dwell,closed_at=100+dwell)
            with self.assertRaises(ValueError):mobile.validate_mobile(e,P)
    def test_reject_frame_from_other_attempt(self):
        for t in [90,110,126]:
            e=self.evidence();e['visual_captured_at']=t
            with self.assertRaises(ValueError):mobile.validate_mobile(e,P)
    def test_reject_desktop_or_wrong_dimensions(self):
        for change in [dict(device_toolbar_enabled=False),dict(device_name='Responsive'),dict(viewport_width=1920),dict(verified=False)]:
            e=self.evidence();e['mobile_emulation'].update(change)
            with self.assertRaises(ValueError):mobile.validate_mobile(e,P)
    def test_mobile_must_precede_navigation(self):
        e=self.evidence();e['mobile_emulation']['verified_at']=101
        with self.assertRaises(ValueError):mobile.validate_mobile(e,P)
    def test_same_residence_for_no_ad_and_pass_and_review_after_close(self):
        for ad in [False,True]:
            clock=[100.0];events=[]
            def pause(n):clock[0]+=n
            def opening(call,url,persist,configure,verify_url):
                configure(TARGET);p=dict(target=TARGET,new_window_created=True,new_tab_created=True,browser_mode='NORMAL',opened_at=clock[0],state='NAVIGATION_SUBMITTED');persist(p);return p
            def closure(call,proof):events.append('close');clock[0]+=2;return dict(closed_at=clock[0],tab_closed_verified=True,other_tabs_preserved=True)
            with tempfile.TemporaryDirectory() as tmp:
                frame=Path(tmp)/'frame.png';frame.write_bytes(b'offline fixture, not an actual ad')
                def capture():events.append('capture');os.utime(frame,(clock[0],clock[0]));return {'screenshot_path':str(frame)}
                def review(shot):events.append('review');return dict(success=True,analysis=json.dumps(dict(network_ad_visible=ad,active_normal_chrome=True,unobstructed=True,landing_loaded=True,description='offline fixture only')))
                with patch.object(mobile,'policy',return_value=P),patch.object(mobile,'configure_mobile',return_value=dict(M)),patch.object(mobile,'scroll_mobile',return_value={'offline':True}),patch.object(lean,'open_normal',side_effect=opening),patch.object(lean,'close_normal',side_effect=closure):
                    result,e=mobile.observe_mobile(lambda a:None,'https://example.invalid/lp','offline',read_mobile=lambda:None,capture_visual=capture,review_visual=review,on_owned=lambda p:None,pause=pause,clock=lambda:clock[0],monotonic=lambda:clock[0])
                self.assertEqual(result,'PASS' if ad else 'NO_AD');self.assertEqual(events,['capture','close','review']);self.assertEqual(e['tab_open_seconds'],24);self.assertNotIn('visible_seconds',e)
    def test_missing_verification_callback_fails_closed(self):
        with self.assertRaises(ValueError):mobile.configure_mobile(lambda a:None,TARGET,None,P)
    def test_scroll_mobile_uses_verified_page_not_devtools(self):
        calls=[]
        def call(a):
            calls.append(a)
            return {'ok':True,'effect':'confirmed','elements':[{'role':'Document','label':'DevTools','index':5,'bounds':[0,100,2560,1200]}]}
        mobile.scroll_mobile(call,TARGET,M)
        self.assertEqual(calls[-1]['coordinate'],[796,626]);self.assertNotIn('element',calls[-1])
    def test_dispatch_requires_new_mobile_path(self):
        with patch('ares_campaign_v3.landing_desktop_observation.policy',return_value={}),patch.object(mobile,'policy',return_value=P),patch.object(mobile,'observe_mobile',return_value=('OFFLINE',{})) as runner:
            self.assertEqual(lean.observe_prepared(None,None,'url','source')[0],'OFFLINE');runner.assert_called_once()
    def test_mobile_url_uses_native_value_not_swallowed_typing(self):
        calls=[]
        def call(a):
            calls.append(a);return {'ok':True,'effect':'confirmed','elements':[{'role':'Edit','label':'Address and search bar','index':5,'bounds':[100,50,1800,24]}]}
        proof=dict(target=TARGET,new_window_created=True,new_tab_created=True,browser_mode='NORMAL')
        with patch.object(lean,'open_blank_normal',return_value=proof):
            out=lean.open_normal(call,'https://example.invalid/lp',configure=lambda t:dict(M),verify_url=lambda u,t:True)
        self.assertEqual(sum(a['action']=='set_value' for a in calls),1);self.assertFalse(any(a['action']=='type' for a in calls));self.assertTrue(out['url_submission_attempted'])
    def test_unverified_native_value_never_submits(self):
        calls=[]
        def call(a):
            calls.append(a);return {'elements':[{'role':'Edit','label':'Address and search bar','index':5,'bounds':[100,50,1800,24]}]}
        proof=dict(target=TARGET,new_window_created=True,new_tab_created=True,browser_mode='NORMAL')
        with patch.object(lean,'open_blank_normal',return_value=proof):
            with self.assertRaises(ValueError):lean.open_normal(call,'https://example.invalid/lp',configure=lambda t:dict(M),verify_url=lambda u,t:False)
        self.assertFalse(any(a.get('keys')=='return' for a in calls))
    def test_omnibox_comparison_rejects_difference_and_uncertainty(self):
        from PIL import Image
        es=[dict(role='Edit',label='Address and search bar',index=5,bounds=[170,51,1800,24]),dict(label='Close',bounds=[2514,0,46,40])]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'offline.png';Image.new('RGB',(2560,1440),color='white').save(path)
            for match,uncertain,expected in [(True,False,True),(False,False,False),(True,True,False)]:
                def review(shot,prompt):
                    with Image.open(shot['screenshot_path']) as image:self.assertLessEqual(image.width,1100)
                    return dict(success=True,analysis=json.dumps(dict(exact_match=match,uncertain=uncertain,observed_difference='offline fixture')))
                with patch.object(mobile,'_capture',return_value=es):
                    self.assertEqual(mobile.verify_omnibox(None,TARGET,'https://example.invalid/lp',lambda:{'screenshot_path':str(path)},review),expected)
    def test_rewarded_gate_is_negative_not_pass_or_loading_error(self):
        from ares_campaign_v3 import landing_followup as core
        base=dict(pid=1,window_id=1,app_name='chrome.exe');url='https://example.invalid/lp?utm_campaign=c1'
        e=self.evidence();e.update(observation_mode='LEAN_NORMAL_NEW_TAB',normal_opening=dict(browser_mode='NORMAL',new_tab_created=True,target=TARGET,baseline=[base],state='OPENED_NORMAL',url_submission_attempted=True,url=url),new_tab_identity=TARGET,before_windows=[base,TARGET],after_windows=[base],tab_closed_verified=True,other_tabs_preserved=True,observed_url=url,resolved_landing_url=url,mapping_source='offline',network_ad_confirmed=False,site_gate_visible=True,visual=dict(network_ad_visible=False,active_normal_chrome=True,unobstructed=False,landing_loaded=True,site_gate_visible=True,description='offline site gate'))
        with patch.object(lean,'lean_enabled',return_value=True),patch.object(core,'scope',return_value=True),patch.object(mobile,'policy',return_value=P):
            lean.validate_lean_observation(e,dict(effective_campaign_url=url),negative=True)
            with self.assertRaises(ValueError):lean.validate_lean_observation(e,dict(effective_campaign_url=url),negative=False)

if __name__=='__main__':unittest.main()
