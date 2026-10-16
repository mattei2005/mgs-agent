"""Offline probe-base fixtures; never live PC1 evidence."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('landing_repair',ROOT/'scripts/ares-direct-traffic-repair.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ProbeBaseTests(unittest.TestCase):
    def window(self,n):return {'pid':1,'window_id':n,'app_name':'chrome.exe'}

    def test_unique_browser_uses_exact_identity_without_input(self):
        def unexpected(args):self.fail('No call needed for unique base')
        self.assertEqual(module.probe_base_window(unexpected,[self.window(10)]),10)

    def snapshot(self,private=False):
        es=[{'role':'Edit','label':'Address and search bar'}]
        if private:es.append({'role':'Button','label':'Incognito'})
        return {'elements':es}

    def test_multiple_windows_select_unique_normal_read_only(self):
        calls=[]
        def call(args):
            calls.append(args)
            return self.snapshot(private=args['window_id']==20)
        self.assertEqual(module.probe_base_window(call,[self.window(10),self.window(20)]),10)
        self.assertEqual([a['window_id'] for a in calls],[10,20])
        self.assertTrue(all(a['action']=='capture' and a['mode']=='ax' for a in calls))

    def test_two_normal_windows_fail_without_input(self):
        with self.assertRaisesRegex(ValueError,'no opening input'):
            module.probe_base_window(lambda args:self.snapshot(),[self.window(10),self.window(20)])

    def test_unreadable_or_no_browser_fails_closed(self):
        for baseline in ([],[self.window(10),self.window(20)]):
            with self.assertRaises(ValueError):module.probe_base_window(lambda args:{},baseline)

    def test_all_private_windows_fail_closed(self):
        with self.assertRaises(ValueError):
            module.probe_base_window(lambda args:self.snapshot(True),[self.window(10),self.window(20)])


if __name__=='__main__':unittest.main()
