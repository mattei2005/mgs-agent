import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CronSchedulingPolicyTests(unittest.TestCase):
    def test_canonical_policy_covers_all_schedulers_and_minute_allocation(self):
        policy = (ROOT / "context/cron-scheduling-policy.md").read_text(encoding="utf-8")
        required = [
            "todos os agentes, profiles e schedulers MGS",
            "root crontab",
            "/etc/crontab",
            "systemd timers",
            "jobs Hermes de todos os profiles operacionais",
            "minuto de início",
            "oito datas civis",
            "Baselines contínuas",
            "duração",
            "lock",
            "readback exato",
            "nova auditoria global de colisão",
        ]
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, policy)

    def test_global_route_points_every_agent_to_the_policy(self):
        routes = (ROOT / "context/routes.md").read_text(encoding="utf-8")
        self.assertIn("Criar/alterar cron global/operacional", routes)
        self.assertIn("context/cron-scheduling-policy.md", routes)
        self.assertIn("qualquer agente ou scheduler", routes)

    def test_ares_and_zeus_operational_skills_enforce_the_policy(self):
        paths = [
            ROOT / "profiles/ares-skills/growth/meta-ads-intraday-operations/SKILL.md",
            ROOT / "profiles/zeus-skills/ops/hermes-agent-operations/SKILL.md",
            ROOT / "profiles/zeus-skills/ops/log-monitor-discord-alert/SKILL.md",
        ]
        for path in paths:
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertIn("cron-scheduling-policy.md", content)


if __name__ == "__main__":
    unittest.main()
