from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


RUNTIME = Path("/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py")
ACCOUNT = Path("/root/mgs-agent/data/ares/meta-ads/accounts/1046241194533786.json")
EXPECTED_CACHE = Path(
    "/root/.cache/mgs/ares-meta-token-creditoparaveiculo-roosevelt-minibot-1299247318762949.json"
)


def test_account13_runtime_uses_registry_token_and_isolated_cache(monkeypatch):
    monkeypatch.setenv("ARES_META_TOKEN_CACHE_PATH", "/tmp/incorrect-generic-cache.json")
    monkeypatch.setenv("ARES_META_TOKEN_CACHE_LOCK_PATH", "/tmp/incorrect-generic-cache.lock")

    spec = importlib.util.spec_from_file_location("cpv13_token_routing_test", RUNTIME)
    assert spec and spec.loader
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)

    account = json.loads(ACCOUNT.read_text(encoding="utf-8"))["accounts"][0]
    assert runtime.META_ITEM == account["token_1password_item"]
    assert runtime.META_TOKEN_CACHE_PATH == EXPECTED_CACHE
    assert os.environ["ARES_META_TOKEN_CACHE_PATH"] == str(EXPECTED_CACHE)
    assert os.environ["ARES_META_TOKEN_CACHE_LOCK_PATH"] == f"{EXPECTED_CACHE}.lock"
