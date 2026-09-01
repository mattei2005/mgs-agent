import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CronSchedulingPolicyTests(unittest.TestCase):
    def test_eggbev_physical_ticks_are_staggered_and_contractual(self):
        operation = json.loads(
            (ROOT / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json").read_text(encoding="utf-8")
        )
        jobs = operation["scheduler_jobs"]
        self.assertEqual(jobs["roas_cycle"]["schedule"], "10 0,5,6,8,10,12,13,14,16,18,20,22,23 * * *")
        self.assertEqual(jobs["roas_cycle"]["physical_offset_minute"], 10)
        self.assertEqual(jobs["page_lead_guardrail"]["schedule"], "16 8,20 * * *")
        self.assertEqual(jobs["page_lead_guardrail"]["physical_offset_minute"], 16)
        restriction = jobs["page_restriction_guardrail"]
        self.assertEqual(restriction["schedule"], "3-58/5 * * * *")
        self.assertEqual(restriction["stagger_seconds"], 30)
        self.assertEqual(restriction["maximum_detection_delay_seconds"], 330)

        roas_prompt = (ROOT / "data/ares/discord/thread-prompts/1541578606076231750.txt").read_text()
        page_prompt = (ROOT / "data/ares/discord/thread-prompts/1543312825890381865.txt").read_text()
        self.assertIn("minuto `:10`", roas_prompt)
        self.assertIn("`08:16` e `20:16`", page_prompt)
        self.assertIn("stagger determinístico de 30 segundos", page_prompt)

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
            "Baselines contínuas e densas",
            "todos os 60 resíduos de minuto",
            "menor contenção de baseline",
            "stagger determinístico em segundos",
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
