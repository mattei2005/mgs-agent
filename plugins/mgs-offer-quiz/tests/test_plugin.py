#!/usr/bin/env python3
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]


class OfferQuizPluginTests(unittest.TestCase):
    def test_required_files_exist(self):
        for relative in (
            "mgs-offer-quiz.php",
            "includes/class-mgs-offer-quiz.php",
            "templates/landing.php",
            "README.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_php_lint(self):
        php_files = sorted(ROOT.rglob("*.php"))
        self.assertGreaterEqual(len(php_files), 3)
        for path in php_files:
            result = subprocess.run(
                ["php", "-l", str(path)], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_template_contract(self):
        item = {
            "id": "fixture-g001",
            "name": "Superdigital BR — G001 — V1",
            "manager": "G001",
            "slug": "quiz-v1-g001",
            "active": 1,
            "logo_url": "https://dicasfinancas.info/wp-content/uploads/2025/05/dicas-logo-1536x508.png",
            "eyebrow": "OFERTAS DE HOJE",
            "headline": "Conheça uma opção digital para cuidar do seu dinheiro",
            "highlight": "SUPERDIGITAL",
            "subheadline": "Veja os detalhes antes de decidir",
            "benefits": [
                "Sem consulta SPC/Serasa",
                "Sem anuidade",
                "Sem taxa escondida",
            ],
            "button_label": "VER OFERTA AGORA",
            "target_url": "https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/",
            "microcopy": "Acesse o conteúdo completo em poucos segundos",
            "disclaimer": "Conteúdo informativo. A disponibilidade e as condições dependem da instituição responsável.",
            "privacy_url": "https://dicasfinancas.info/politica-de-privacidade/",
        }
        with tempfile.TemporaryDirectory(prefix="mgs-offer-quiz-test-") as td:
            fixture = Path(td) / "render.php"
            fixture.write_text(
                "<?php\n"
                + "$mgs_oq_item = json_decode('"
                + json.dumps(item, ensure_ascii=False).replace("\\", "\\\\").replace("'", "\\'")
                + "', true);\n"
                + "$mgs_oq_static_render = true;\n"
                + "include "
                + repr(str(ROOT / "templates" / "landing.php"))
                + ";\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                ["php", str(fixture)], capture_output=True, text=True, check=True
            )
        html = result.stdout
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn('lang="pt-BR"', html)
        self.assertIn("MGS Offer Quiz", html)
        self.assertIn("quiz-v1-g001", html)
        self.assertIn("G001", html)
        self.assertIn(item["target_url"], html)
        self.assertIn("Ofertas de hoje", html)
        self.assertIn("até", html)
        self.assertIn("R$5.000", html)
        self.assertIn("aprovados na hora", html)
        self.assertIn("Sem consulta SPC/Serasa", html)
        self.assertIn("Sem anuidade", html)
        self.assertIn("Sem taxa escondida", html)
        self.assertIn("Ver ofertas agora", html)
        for visual_class in (
            "card-header",
            "header-timer",
            "hero-block",
            "hero-valor",
            "num-list",
            "btn-primary",
            "social-proof",
            "trust-row",
            "aviso-legal",
            "card-footer",
        ):
            self.assertIn(visual_class, html)
        self.assertEqual(html.lower().count("<form"), 0)
        self.assertEqual(html.lower().count("<input"), 0)
        self.assertNotIn("Ofertas extras no meu e-mail", html)
        self.assertIn("1.892", html)
        self.assertIn('id="socialCount"', html)
        self.assertIn("/wp-json/mgs-offer-quiz/v1/daily-view", html)
        self.assertIn("window.fetch", html)
        self.assertIn("registerPageView", html)
        self.assertNotIn("Math.random", html)
        self.assertNotIn("window.setTimeout", html)
        self.assertIn("URLSearchParams", html)
        self.assertIn("window.location.href", html)
        self.assertIn("noindex,follow", html)
        self.assertNotIn("aprovação garantida", html.lower())

    def test_target_path_is_exact(self):
        target = "https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/"
        parsed = urlparse(target)
        self.assertEqual(parsed.netloc, "dicasfinancas.info")
        self.assertEqual(
            parsed.path, "/rec-br-cc-cartao-de-credito-nubank/"
        )
        self.assertEqual(parse_qs(parsed.query), {})

    def test_daily_counter_contract(self):
        source = (ROOT / "includes" / "class-mgs-offer-quiz.php").read_text(
            encoding="utf-8"
        )
        for marker in (
            "COUNTER_BASELINE = 1892",
            "COUNTER_TIMEZONE = 'America/Sao_Paulo'",
            "mgs_offer_quiz_daily_views",
            "dbDelta( $sql )",
            "LAST_INSERT_ID(view_count + 1)",
            "self::COUNTER_BASELINE + $views_today - 1",
            "register_rest_route",
            "mgs-offer-quiz/v1",
            "'/daily-view'",
            "no-store, no-cache, must-revalidate, max-age=0",
        ):
            self.assertIn(marker, source)

    def test_source_contains_safety_and_static_guards(self):
        source = (ROOT / "includes" / "class-mgs-offer-quiz.php").read_text(
            encoding="utf-8"
        )
        for marker in (
            "MGS Offer Quiz static",
            "wp_generate_uuid4",
            "LOCK_EX",
            "rename(",
            "current_user_can( 'manage_options' )",
            "check_admin_referer",
            "sanitize_key",
            "esc_url_raw",
        ):
            self.assertIn(marker, source)
        self.assertRegex(source, re.compile(r"quiz-v1-g00[1-6]"))
        target = "https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/"
        self.assertEqual(source.count(target), 2)
        self.assertNotIn("rec-br-cc-br-cartao-de-credito-superdigital", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
