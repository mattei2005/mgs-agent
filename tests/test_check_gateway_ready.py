#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-gateway-ready.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_gateway_ready", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_wait_requires_active_running_and_new_discord_marker(tmp_path):
    mod = load_module()
    log = tmp_path / "agent.log"
    log.write_text("old ✓ discord connected\n", encoding="utf-8")
    offset = log.stat().st_size
    states = iter(
        [
            {"ActiveState": "activating", "SubState": "start", "MainPID": "0", "NRestarts": "0"},
            {"ActiveState": "active", "SubState": "running", "MainPID": "42", "NRestarts": "0"},
            {"ActiveState": "active", "SubState": "running", "MainPID": "42", "NRestarts": "0"},
        ]
    )
    ticks = iter([0.0, 1.0, 2.0, 3.0])

    def sleep(_seconds):
        log.write_text(log.read_text() + "new ✓ discord connected\n", encoding="utf-8")

    result = mod.wait_gateway_ready(
        "zeus-gateway.service",
        log,
        offset,
        timeout=10,
        poll_interval=1,
        status_fn=lambda _svc: next(states),
        monotonic_fn=lambda: next(ticks),
        sleep_fn=sleep,
    )
    assert result["ready"] is True
    assert result["MainPID"] == 42
    assert result["discord_connected"] is True


def test_old_marker_before_offset_does_not_pass(tmp_path):
    mod = load_module()
    log = tmp_path / "agent.log"
    log.write_text("✓ discord connected\n", encoding="utf-8")
    offset = log.stat().st_size
    ticks = iter([0.0, 0.5, 1.1])
    result = mod.wait_gateway_ready(
        "ares-gateway.service",
        log,
        offset,
        timeout=1,
        poll_interval=0,
        status_fn=lambda _svc: {"ActiveState": "active", "SubState": "running", "MainPID": "7", "NRestarts": "0"},
        monotonic_fn=lambda: next(ticks),
        sleep_fn=lambda _seconds: None,
    )
    assert result["ready"] is False
    assert result["reason"] == "timeout_waiting_for_discord"


def test_log_rotation_reads_new_file_from_start(tmp_path):
    mod = load_module()
    log = tmp_path / "agent.log"
    log.write_text("✓ discord connected\n", encoding="utf-8")
    assert mod.has_new_discord_marker(log, offset=9999) is True


def test_cli_json_is_metadata_only(tmp_path, monkeypatch, capsys):
    mod = load_module()
    log = tmp_path / "agent.log"
    log.write_text("✓ discord connected\n", encoding="utf-8")
    monkeypatch.setattr(
        mod,
        "wait_gateway_ready",
        lambda *a, **k: {"ready": True, "service": "zeus-gateway.service", "MainPID": 12, "NRestarts": 0, "discord_connected": True, "elapsed_seconds": 2.0},
    )
    rc = mod.main(["--service", "zeus-gateway.service", "--log", str(log), "--offset", "0", "--timeout", "180"])
    output = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert output["ready"] is True
    assert "payload" not in output


def test_safe_restart_uses_sequential_weighted_discord_gate():
    text = (ROOT / "scripts" / "mgs-gateway-restart-safe.sh").read_text(encoding="utf-8")
    assert 'for wanted in atena ares zeus' in text
    assert 'zeus) readiness_timeout=180' in text
    assert 'atena|ares) readiness_timeout=90' in text
    assert 'check-gateway-ready.py --service' in text
    assert 'gateway_restart_agent_ready' in text
    assert 'sleep 12' not in text
    assert 'systemctl restart --no-block zeus-gateway.service' not in text
