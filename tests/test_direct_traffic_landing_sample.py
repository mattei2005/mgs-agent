"""Offline cadence tests: synthetic times are fixtures, never PC1 evidence."""
import importlib.util
import unittest
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
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

    def test_capture_defers_only_renderer_and_restores_it(self):
        original=lambda:True
        tool=SimpleNamespace(_should_route_through_aux_vision=original)
        def handler(args,session_id):
            self.assertFalse(tool._should_route_through_aux_vision())
            self.assertEqual(args,{'action':'capture','mode':'vision','app':'screen'})
            self.assertEqual(session_id,'OFFLINE_SESSION')
            return {'meta':{'screenshot_path':'OFFLINE_ONLY.png'}}
        tool.handle_computer_use=handler
        r=module.capture_screen(tool,'OFFLINE_SESSION')
        self.assertIs(tool._should_route_through_aux_vision,original)
        self.assertTrue(r['analysis_deferred']);self.assertNotIn('ad_visible',r)
        self.assertEqual(r['screenshot_path'],'OFFLINE_ONLY.png')

    def test_renderer_restored_even_on_handler_failure(self):
        original=lambda:True
        def fail(*args,**kwargs):raise ValueError('OFFLINE_FAILURE')
        tool=SimpleNamespace(_should_route_through_aux_vision=original,handle_computer_use=fail)
        with self.assertRaisesRegex(ValueError,'OFFLINE_FAILURE'):module.capture_screen(tool,'OFFLINE_SESSION')
        self.assertIs(tool._should_route_through_aux_vision,original)

    def test_frame_uses_real_file_timestamp_and_never_claims_visual_pass(self):
        with tempfile.TemporaryDirectory() as d:
            image=Path(d)/'OFFLINE_FIXTURE.png';image.write_bytes(b'OFFLINE_FIXTURE_ONLY')
            stamp=image.stat().st_mtime
            r=module.capture_frame(lambda args:{'meta':{'screenshot_path':str(image)},'analysis_deferred':True})
            self.assertEqual(r['captured_at'],stamp);self.assertEqual(image.stat().st_mtime,stamp)
            self.assertTrue(r['analysis_deferred']);self.assertIsNone(r['analysis'])
            self.assertNotIn('ad_visible',r);self.assertNotIn('tab_active',r)

    def test_fast_capture_still_budgets_ten_seconds(self):
        now=[0]
        def capture():return {'monotonic_seconds':now[0],'captured_at':1000+now[0]}
        def pause(seconds):now[0]+=seconds
        r=module.collect(capture,pause=pause)
        self.assertEqual(r['state'],'CAPTURED_NOT_PASS')
        self.assertGreaterEqual(r['samples'][-1]['captured_at']-r['samples'][0]['captured_at'],10)

    def test_capture_error_preserves_partial_real_frame_records(self):
        frame={'monotonic_seconds':1,'captured_at':1001,'screenshot':'OFFLINE_ONLY.png'}
        calls=iter([frame,ValueError('OFFLINE_CAPTURE_FAILURE')])
        def capture():
            result=next(calls)
            if isinstance(result,Exception):raise result
            return result
        r=module.collect(capture,pause=lambda _:None)
        self.assertEqual(r['state'],'CAPTURE_ERROR')
        self.assertEqual(r['samples'],[]);self.assertEqual(r['all_frames'],[frame])
        self.assertEqual(r['error'],'OFFLINE_CAPTURE_FAILURE')

    def test_capture_crossing_deadline_cannot_validate_cadence(self):
        now=[0]
        frames=iter([0,5,10])
        def capture():
            stamp=next(frames)
            now[0]+=20
            return {'monotonic_seconds':stamp,'captured_at':1000+stamp}
        with patch.object(module.time,'monotonic',side_effect=lambda:now[0]):
            r=module.collect(capture,pause=lambda _:None,max_seconds=45)
        self.assertEqual(r['state'],'CADENCE_NOT_VALIDATED')
        self.assertEqual(r['samples'],[]);self.assertEqual(len(r['all_frames']),3)


if __name__=='__main__':unittest.main()
