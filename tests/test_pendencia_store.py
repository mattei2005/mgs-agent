#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pendencia_store as store  # noqa: E402


def base_db(open_items=None, resolved=None, root_next=2, meta_next=2):
    return {
        "schema_version": "1.0",
        "metadata": {
            "ultima_atualizacao": "2026-01-01T00:00:00-05:00",
            "total_abertas": len(open_items or []),
            "total_resolvidas": len(resolved or []),
            "proximo_id": meta_next,
        },
        "categorias": {"infra": "Infra"},
        "pendencias": list(open_items or []),
        "resolvidas": list(resolved or []),
        "proximo_id": root_next,
        "ultima_atualizacao": "2026-01-01T00:00:00-05:00",
    }


def open_item(pid, title="Open"):
    return {
        "id": pid,
        "titulo": title,
        "categoria": "infra",
        "prioridade": "baixa",
        "status": "aberta",
        "tempo_estimado": None,
        "bloqueio": None,
        "criada_em": "2026-01-01T00:00:00-05:00",
        "criada_por": "test",
        "tags": [],
        "contexto": None,
    }


def resolved_item(pid, title="Resolved"):
    return {
        "id": pid,
        "titulo": title,
        "categoria": "infra",
        "resolvida_em": "2026-01-01T00:00:00-05:00",
        "resolvida_por": "test",
        "como": "done",
    }


class PendenciaStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mgs-pendencia-test-")
        self.db = Path(self.tmp.name) / "pendencias.db.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_db(self, data):
        self.db.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def read_db(self):
        return json.loads(self.db.read_text())

    def add(self, title="New", **kwargs):
        return store.add_open(
            self.db,
            titulo=title,
            categoria="infra",
            prioridade="baixa",
            criada_por="test",
            timestamp="2026-07-12T21:00:00-04:00",
            **kwargs,
        )

    # 1. Stored counters are never authoritative.
    def test_counter_drift_is_ignored(self):
        self.write_db(base_db([open_item("PEND-010")], [resolved_item("PEND-020")], 2, 999))
        self.assertEqual(self.add()["id"], "PEND-021")
        data = self.read_db()
        self.assertEqual(data["proximo_id"], 22)
        self.assertEqual(data["metadata"]["proximo_id"], 22)

    # 2. Missing counters do not block allocation.
    def test_missing_counters_are_rebuilt(self):
        data = base_db([open_item("PEND-003")])
        data.pop("proximo_id")
        data["metadata"].pop("proximo_id")
        self.write_db(data)
        self.assertEqual(self.add()["id"], "PEND-004")

    # 3. Historical gaps are never reused.
    def test_gaps_are_not_reused(self):
        self.write_db(base_db([open_item("PEND-057"), open_item("PEND-067")]))
        self.assertEqual(self.add()["id"], "PEND-068")

    # 4. Legacy PEND-Rxxx remains a separate namespace.
    def test_legacy_r_namespace_is_preserved(self):
        self.write_db(base_db([open_item("PEND-009")], [resolved_item("PEND-R999")]))
        self.assertEqual(self.add()["id"], "PEND-010")
        self.assertIn("PEND-R999", [x["id"] for x in self.read_db()["resolvidas"]])

    # 5. Existing duplicates fail closed without touching the DB.
    def test_duplicate_preexisting_id_aborts_without_write(self):
        self.write_db(base_db([open_item("PEND-005")], [resolved_item("PEND-005")]))
        before = self.db.read_bytes()
        with self.assertRaises(store.IntegrityError):
            self.add()
        self.assertEqual(self.db.read_bytes(), before)

    # 6. Ten concurrent adds produce ten unique IDs and no lost writes.
    def test_ten_concurrent_adds_are_unique(self):
        self.write_db(base_db([open_item("PEND-100")], root_next=1, meta_next=1))
        def work(i):
            return self.add(title=f"Concurrent {i}")["id"]
        with ThreadPoolExecutor(max_workers=10) as pool:
            ids = list(pool.map(work, range(10)))
        self.assertEqual(len(set(ids)), 10)
        self.assertEqual(set(ids), {f"PEND-{n:03d}" for n in range(101, 111)})
        self.assertEqual(len(self.read_db()["pendencias"]), 11)

    # 7. A concurrent add and done cannot clobber one another.
    def test_add_and_done_concurrency_has_no_lost_update(self):
        self.write_db(base_db([open_item("PEND-001")], [resolved_item("PEND-010")]))
        barrier = __import__("threading").Barrier(2)
        def add_work():
            barrier.wait()
            return self.add(title="Concurrent add")
        def done_work():
            barrier.wait()
            return store.resolve_open(
                self.db,
                pending_id="PEND-001",
                como="resolved concurrently",
                resolvida_por="test",
                timestamp="2026-07-12T21:01:00-04:00",
            )
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(add_work)
            b = pool.submit(done_work)
            a.result(); b.result()
        data = self.read_db()
        self.assertIn("PEND-011", [x["id"] for x in data["pendencias"]])
        self.assertIn("PEND-001", [x["id"] for x in data["resolvidas"]])

    # 8. Atomic replace failure leaves the original file byte-identical.
    def test_atomic_replace_failure_preserves_original(self):
        self.write_db(base_db([open_item("PEND-001")]))
        before = self.db.read_bytes()
        with mock.patch.object(store.os, "replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                self.add()
        self.assertEqual(self.db.read_bytes(), before)

    # 9. Arguments with quotes, dollars, newlines and Unicode survive exactly.
    def test_special_characters_round_trip(self):
        self.write_db(base_db())
        title = "Dólar $HOME, aspas ' \" e linha\nseguinte — ç"
        context = "$(touch /tmp/never)\ntexto literal"
        result = self.add(title=title, contexto=context, tags=["a$b", "ç"])
        item = next(x for x in self.read_db()["pendencias"] if x["id"] == result["id"])
        self.assertEqual(item["titulo"], title)
        self.assertEqual(item["contexto"], context)
        self.assertEqual(item["tags"], ["a$b", "ç"])

    # 10. Historical inserts use max+1 and refresh derived counters.
    def test_historical_add_uses_max_plus_one(self):
        self.write_db(base_db([open_item("PEND-015")], [resolved_item("PEND-040")], 2, 3))
        result = store.add_historical(
            self.db,
            titulo="Historical",
            categoria="infra",
            prioridade="baixa",
            data_resolucao="2026-07-01",
            resolvida_por="test",
            como="already done",
            timestamp="2026-07-12T21:02:00-04:00",
        )
        self.assertEqual(result["id"], "PEND-041")
        data = self.read_db()
        self.assertEqual(data["proximo_id"], 42)
        self.assertEqual(data["metadata"]["proximo_id"], 42)

    # 11. Resolve moves exactly one item and readback counters are correct.
    def test_resolve_moves_exactly_one_and_updates_counts(self):
        self.write_db(base_db([open_item("PEND-001"), open_item("PEND-002")]))
        store.resolve_open(
            self.db,
            pending_id="PEND-001",
            como="fixed",
            resolvida_por="test",
            timestamp="2026-07-12T21:03:00-04:00",
        )
        data = self.read_db()
        self.assertEqual([x["id"] for x in data["pendencias"]], ["PEND-002"])
        self.assertEqual([x["id"] for x in data["resolvidas"]], ["PEND-001"])
        self.assertEqual(data["metadata"]["total_abertas"], 1)
        self.assertEqual(data["metadata"]["total_resolvidas"], 1)
        self.assertEqual(data["proximo_id"], 3)
        self.assertEqual(data["metadata"]["proximo_id"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
