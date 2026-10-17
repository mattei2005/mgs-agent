"""Offline shared mechanical-core and normal-probe tests; no real browser."""
import importlib.util,json,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
import test_direct_traffic_landing_followup as fixtures
from test_direct_traffic_landing_lean import Fake
from ares_campaign_v3 import landing_lean as lean

class NativeFake(Fake):
    def __call__(self,args):
        out=super().__call__(args)
        if args['action']=='capture':out['elements'].append({'index':40,'role':'Document','label':'Rendered page','bounds':[0,121,2560,1271]})
        return out

class SharedMechanicalTests(unittest.TestCase):
    def setUp(self):self.clock=fixtures.Clock();self.native=NativeFake();self.pauses=[]
    def pause(self,s):self.pauses.append(s);self.clock.value+=s
    def visual(self,found=True,loaded=True):return {'success':True,'analysis':json.dumps(dict(network_ad_visible=found,active_normal_chrome=True,unobstructed=True,landing_loaded=loaded,description='Offline rendered-ad fixture' if found else 'Offline loaded page without advertising'))}
    def observe(self,reader):
        timer=types.SimpleNamespace(time=self.clock,monotonic=self.clock,sleep=self.pause)
        with patch.object(lean,'time',timer):return lean.observe_prepared(self.native,reader,'https://example.invalid/landing?utm_campaign=b01fb02c151&utm_adgroup=b01fb02c151g01','offline fixture',pause=self.pause,clock=self.clock,monotonic=self.clock)
    def test_pass_one_visual_read_normal_scroll10_and_close(self):
        reads=[];r,e=self.observe(lambda:reads.append(1) or self.visual());self.assertEqual(r,'PASS');self.assertEqual(reads,[1]);self.assertEqual(e['visible_seconds'],10);self.assertTrue(e['tab_closed_verified']);self.assertTrue(e['other_tabs_preserved']);self.assertEqual(self.pauses,[10]);self.assertNotIn('samples',e)
        self.assertFalse(any(a.get('keys')=='ctrl+shift+n' for a in self.native.calls));self.assertTrue(any(a['action']=='scroll' and a.get('element')==40 for a in self.native.calls))
    def test_noad_not_wait10_or_fake_pass(self):
        r,e=self.observe(lambda:self.visual(False));self.assertEqual(r,'NO_AD');self.assertEqual(self.pauses,[]);self.assertTrue(e['tab_closed_verified']);self.assertFalse(e['network_ad_confirmed'])
    def test_loading_re_read_same_tab(self):
        reads=iter([self.visual(False,False),self.visual(True,True)]);r,e=self.observe(lambda:next(reads));self.assertEqual(r,'PASS');self.assertEqual(self.pauses,[1,10]);self.assertEqual(sum(a['action']=='type' for a in self.native.calls),1)
    def test_unloaded_not_noad(self):
        r,e=self.observe(lambda:self.visual(False,False));self.assertEqual(r,'ERROR');self.assertTrue(e['tab_closed_verified']);self.assertIn('never NO_AD',e['diagnosis'])
    def test_uncertain_close_never_pass(self):
        with patch.object(lean,'close_normal',side_effect=ValueError('offline closure unknown')):r,e=self.observe(lambda:self.visual())
        self.assertEqual(r,'ERROR');self.assertNotIn('tab_closed_verified',e)

class NormalProbeTests(unittest.TestCase):
    setUp=fixtures.FollowupTests.setUp
    tearDown=fixtures.FollowupTests.tearDown
    def load(self):
        path=Path('/root/mgs-agent/scripts/ares-direct-traffic-repair.py');spec=importlib.util.spec_from_file_location('offline_normal_probe',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_actual_probe_main_uses_normal_no_sampler_no_url(self):
        m=self.load();native=NativeFake();released=[]
        tool=types.SimpleNamespace(handle_computer_use=lambda a,**kw:json.dumps(native(a)),release_computer_use_session=lambda sid:released.append(sid))
        pkg=types.ModuleType('tools');pkg.__path__=[];cu=types.ModuleType('tools.computer_use');cu.tool=tool
        def load(name,path):
            if name!='probe_control':raise AssertionError('Lean probe must not load screenshot sampler')
            return types.SimpleNamespace(require_pc1_lease=lambda sid:None)
        args=['probe','--pc1-session-id','offline-session','--repair-note','offline tested normal route','--standalone-probe-id','offline-normal']
        with patch.object(m,'load',side_effect=load),patch.object(m,'lean_enabled',return_value=True),patch.object(m.core,'Queue',return_value=self.q),patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='offline tests',stderr='')),patch.object(m.shutil,'which',return_value='/offline/runtime/bin/hermes'),patch.object(sys,'argv',args),patch.dict(sys.modules,{'tools':pkg,'tools.computer_use':cu}):
            self.assertEqual(m.main(),0)
        proof=json.loads((self.q.root/'probes/offline-normal/technical-probe.json').read_text());self.assertEqual(proof['state'],'TECHNICAL_PROBE_VERIFIED');self.assertEqual(proof['mode'],'LEAN_NORMAL_NEW_TAB');self.assertNotIn('series',proof);self.assertFalse(any(a['action']=='type' for a in native.calls));self.assertFalse(any(a.get('keys')=='ctrl+shift+n' for a in native.calls));self.assertTrue(proof['closure']['tab_closed_verified']);self.assertEqual(released,['offline-session'])
    def test_missing_normal_policy_fails_closed_before_queue_or_input(self):
        m=self.load();args=['probe','--pc1-session-id','offline','--repair-note','offline note','--standalone-probe-id','missing-policy']
        with patch.object(m,'load',return_value=types.SimpleNamespace(require_pc1_lease=lambda sid:None)),patch.object(m,'lean_enabled',return_value=False),patch.object(m.core,'Queue',side_effect=AssertionError('No queue or browser without policy')),patch.object(sys,'argv',args):
            with self.assertRaisesRegex(ValueError,'normal-only repair'):m.main()

    def test_standalone_probe_cannot_bypass_uncertain_observer(self):
        m=self.load()
        with self.q.tx():self.q.db.execute("update jobs set state='NEEDS_RECONCILIATION' where key=?",(self.key,))
        with self.assertRaises(ValueError):m.require_desktop_available(self.q,None)

if __name__=='__main__':unittest.main()
