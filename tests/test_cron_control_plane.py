#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path('/root/mgs-agent/scripts/cron-control-plane.py')
spec = importlib.util.spec_from_file_location('cron_control_plane', SCRIPT)
assert spec and spec.loader
cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron)


class CronControlPlaneParsingTests(unittest.TestCase):
    def test_profile_script_cron_is_inventoried(self):
        line = (
            '3-58/5 * * * * sleep 30 && flock -n '
            '/root/mgs-agent/data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/roas-cycle.lock '
            '/root/.hermes/profiles/ares/scripts/eggbev-page-restriction-guardrail.sh '
            '>> /root/mgs-agent/logs/ares-eggbev-page-restriction-guardrail.log 2>&1'
        )
        parsed = cron.parse_cron_line(line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['script'], 'eggbev-page-restriction-guardrail.sh')
        self.assertEqual(
            parsed['script_path'],
            '/root/.hermes/profiles/ares/scripts/eggbev-page-restriction-guardrail.sh',
        )
        self.assertEqual(parsed['owner'], 'Ares/Campaign Ops')
        self.assertIn('pausar campanhas', parsed['risk'])

    def test_repo_script_cron_keeps_existing_path(self):
        parsed = cron.parse_cron_line(
            '10 1 * * * /usr/bin/python3 /root/mgs-agent/scripts/cron-control-plane.py --write-doc'
        )
        self.assertEqual(parsed['script'], 'cron-control-plane.py')
        self.assertEqual(parsed['script_path'], '/root/mgs-agent/scripts/cron-control-plane.py')


if __name__ == '__main__':
    unittest.main()
