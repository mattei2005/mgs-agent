"""RunCloud owner-approved two-hour/daily inspection cadence."""
import importlib.util
import unittest
from pathlib import Path

SPEC=importlib.util.spec_from_file_location('runcloud_cadence','/root/mgs-agent/scripts/monitor-runcloud.py')
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

class FakeAPI:
    calls=0
    failures=0
    def pages(self,path): self.calls+=1;return []

class CadenceTests(unittest.TestCase):
    def setUp(self):
        self.cfg={'servers':[],'webapp_servers':{},'backup_max_age_hours':36,'backup_cadence_seconds':86400}
        self.now=1000000;self.state=M.fresh_state();self.api=FakeAPI()
    def test_daily_backups_not_refetched_at_next_health_cycle(self):
        self.state['last_backup_check']=self.now-7200
        _,summary=M.collect(self.api,self.cfg,self.state,self.now)
        self.assertEqual(self.api.calls,0)
        self.assertIsNone(summary['backups'])
        self.assertEqual(self.state['last_backup_check'],self.now-7200)
    def test_daily_backup_exact_boundary_is_due(self):
        self.state['last_backup_check']=self.now-86400
        _,summary=M.collect(self.api,self.cfg,self.state,self.now)
        self.assertEqual(self.api.calls,1)
        self.assertIsNotNone(summary['backups'])
        self.assertEqual(self.state['last_backup_check'],self.now)
    def test_explicit_force_keeps_on_demand_semantics(self):
        self.state['last_backup_check']=self.now-60
        M.collect(self.api,self.cfg,self.state,self.now,True)
        self.assertEqual(self.api.calls,1)
    def test_invalid_backup_cadence_fails_closed(self):
        for value in [0,-1,True,'86400']:
            with self.subTest(value=value):
                cfg={**self.cfg,'backup_cadence_seconds':value}
                with self.assertRaises(M.APIError):M.collect(self.api,cfg,self.state,self.now)
    def test_watchdog_matches_two_hour_cron(self):
        text=Path('/root/mgs-agent/scripts/monitor-cron-stale-logs.sh').read_text()
        block=text[text.index('def threshold_seconds('):text.index('def parse_crons():')]
        namespace={};exec(compile(block,'watchdog-cadence','exec'),namespace)
        self.assertEqual(namespace['threshold_seconds']('4 0-23/2 * * *','monitor-runcloud.py'),3*3600)

if __name__=='__main__':unittest.main(verbosity=2)
