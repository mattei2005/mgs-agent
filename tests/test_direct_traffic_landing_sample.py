"""Offline cadence tests: synthetic times are fixtures, never PC1 evidence."""
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('landing_sample',Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-sample.py')
assert spec and spec.loader
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class SampleTests(unittest.TestCase):
    def capture(self,times):
        iterator=iter(times)
        def fn():
            t=next(iterator)
            return {'monotonic_seconds':t,'captured_at':t+1000,'screenshot':'OFFLINE_FIXTURE_ONLY-'+str(t)}
        return fn

    def test_ten_seconds_three_fresh_frames(self):
        r=module.collect(self.capture([0,5,10]),pause=lambda _:None,max_frames=3)
        self.assertEqual(r['state'],'CAPTURED_NOT_PASS');self.assertEqual(len(r['samples']),3)
        self.assertNotIn('ad_visible',r['samples'][0])

    def test_gap_is_not_covered_by_total_duration(self):
        r=module.collect(self.capture([0,11,22]),pause=lambda _:None,max_frames=3)
        self.assertEqual(r['state'],'CADENCE_NOT_VALIDATED');self.assertEqual(r['samples'],[])

    def test_recover_cadence_without_new_page_visit(self):
        r=module.collect(self.capture([0,11,16,21]),pause=lambda _:None,max_frames=4)
        self.assertEqual(r['state'],'CAPTURED_NOT_PASS')
        self.assertEqual([x['monotonic_seconds'] for x in r['samples']],[11,16,21])
        self.assertEqual(len(r['all_frames']),4)

    def test_short_observation_never_passes(self):
        r=module.collect(self.capture([0,4,9]),pause=lambda _:None,max_frames=3)
        self.assertEqual(r['state'],'CADENCE_NOT_VALIDATED')


if __name__=='__main__':unittest.main()
