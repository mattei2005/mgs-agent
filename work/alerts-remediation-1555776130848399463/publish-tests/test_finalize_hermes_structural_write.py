#!/usr/bin/env python3
import importlib.util
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "finalize-hermes-structural-write.py"


def load_module():
    spec = importlib.util.spec_from_file_location("trace_finalizer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_receipt(path: Path, live_file: Path, digest: str):
    record = {
        "id": "corr123",
        "correlation_id": "corr123",
        "subsystem": "skills",
        "action": "patch",
        "target": "demo",
        "origin": "background_review",
        "profile": "zeus",
        "profile_home": str(live_file.parents[3]),
        "created_at": 1.0,
        "status": "pending",
        "before": {str(live_file): "a" * 64},
        "after": {str(live_file): digest},
        "paths": [str(live_file)],
        "session": {"platform": "discord", "thread_id": "thread-1"},
        "persisted": True,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))


def test_live_to_mirror_mapping(tmp_path):
    mod = load_module()
    profiles = tmp_path / "profiles"
    repo = tmp_path / "repo"

    zeus = profiles / "zeus" / "skills" / "ops" / "demo" / "SKILL.md"
    ares = profiles / "ares" / "skills" / "growth" / "demo" / "SKILL.md"
    atena = profiles / "atena" / "skills" / "wordpress" / "demo" / "SKILL.md"
    unsynced = profiles / "zeus" / "skills" / "research" / "demo" / "SKILL.md"

    assert mod.map_live_to_mirror(zeus, profiles_root=profiles, repo_root=repo) == (
        repo / "profiles" / "zeus-skills" / "ops" / "demo" / "SKILL.md"
    )
    assert mod.map_live_to_mirror(ares, profiles_root=profiles, repo_root=repo) == (
        repo / "profiles" / "ares-skills" / "growth" / "demo" / "SKILL.md"
    )
    assert mod.map_live_to_mirror(atena, profiles_root=profiles, repo_root=repo) == (
        repo / "profiles" / "atena-skills" / "wordpress" / "demo" / "SKILL.md"
    )
    assert mod.map_live_to_mirror(unsynced, profiles_root=profiles, repo_root=repo) is None


def test_process_receipt_closes_once_and_is_idempotent(tmp_path):
    mod = load_module()
    profiles = tmp_path / "profiles"
    repo = tmp_path / "repo"
    live = profiles / "zeus" / "skills" / "ops" / "demo" / "SKILL.md"
    live.parent.mkdir(parents=True)
    live.write_text("new body")
    digest = mod.sha256_file(live)
    receipt_path = profiles / "zeus" / "pending" / "trace" / "corr123.json"
    make_receipt(receipt_path, live, digest)
    audit = repo / "logs" / "events-audit.jsonl"
    calls = []
    sends = []

    def run_command(command):
        calls.append(tuple(command))
        if command[0].endswith("sync-souls.sh"):
            mirror = mod.map_live_to_mirror(live, profiles_root=profiles, repo_root=repo)
            mirror.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, mirror)
        return "ok"

    def send_report(receipt, mirror_paths):
        sends.append((receipt["id"], tuple(mirror_paths)))
        return "message-1"

    result = mod.process_receipt(
        receipt_path,
        profiles_root=profiles,
        repo_root=repo,
        audit_path=audit,
        run_command=run_command,
        find_report=lambda correlation_id: None,
        send_report=send_report,
        readback_report=lambda message_id, correlation_id: True,
    )
    repeated = mod.process_receipt(
        receipt_path,
        profiles_root=profiles,
        repo_root=repo,
        audit_path=audit,
        run_command=run_command,
        find_report=lambda correlation_id: None,
        send_report=send_report,
        readback_report=lambda message_id, correlation_id: True,
    )

    closed = json.loads(receipt_path.read_text())
    assert result["status"] == "closed"
    assert repeated["status"] == "already_closed"
    assert closed["status"] == "closed"
    assert closed["report_message_id"] == "message-1"
    assert len(sends) == 1
    events = [json.loads(line) for line in audit.read_text().splitlines()]
    assert [event["correlation_id"] for event in events] == ["corr123"]
    assert any(command[0].endswith("sync-souls.sh") for command in calls)
    assert any(command[0].endswith("infra-discovery.sh") for command in calls)


def test_existing_correlated_report_prevents_duplicate_send(tmp_path):
    mod = load_module()
    profiles = tmp_path / "profiles"
    repo = tmp_path / "repo"
    live = profiles / "ares" / "skills" / "growth" / "demo" / "SKILL.md"
    live.parent.mkdir(parents=True)
    live.write_text("new body")
    receipt_path = profiles / "ares" / "pending" / "trace" / "corr123.json"
    make_receipt(receipt_path, live, mod.sha256_file(live))
    sends = []

    def run_command(command):
        if command[0].endswith("sync-souls.sh"):
            mirror = mod.map_live_to_mirror(live, profiles_root=profiles, repo_root=repo)
            mirror.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, mirror)
        return "ok"

    result = mod.process_receipt(
        receipt_path,
        profiles_root=profiles,
        repo_root=repo,
        audit_path=repo / "logs" / "events-audit.jsonl",
        run_command=run_command,
        find_report=lambda correlation_id: "existing-message",
        send_report=lambda *args: sends.append(args) or "new-message",
        readback_report=lambda message_id, correlation_id: message_id == "existing-message",
    )

    assert result["status"] == "closed"
    assert sends == []
    assert json.loads(receipt_path.read_text())["report_message_id"] == "existing-message"


def test_hash_drift_fails_closed_before_side_effects(tmp_path):
    mod = load_module()
    profiles = tmp_path / "profiles"
    repo = tmp_path / "repo"
    live = profiles / "zeus" / "skills" / "ops" / "demo" / "SKILL.md"
    live.parent.mkdir(parents=True)
    live.write_text("drifted")
    receipt_path = profiles / "zeus" / "pending" / "trace" / "corr123.json"
    make_receipt(receipt_path, live, "f" * 64)
    commands = []

    result = mod.process_receipt(
        receipt_path,
        profiles_root=profiles,
        repo_root=repo,
        audit_path=repo / "logs" / "events-audit.jsonl",
        run_command=lambda command: commands.append(command) or "ok",
        find_report=lambda correlation_id: None,
        send_report=lambda *args: "should-not-send",
        readback_report=lambda *args: True,
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "live_hash_drift"
    assert commands == []
    persisted = json.loads(receipt_path.read_text())
    assert persisted["status"] == "blocked"
    assert persisted["last_error"] == "live_hash_drift"


def test_repeated_hash_drift_is_quarantined_and_stops_retrying(tmp_path):
    mod = load_module()
    profiles = tmp_path / "profiles"
    repo = tmp_path / "repo"
    live = profiles / "zeus" / "skills" / "ops" / "demo" / "SKILL.md"
    live.parent.mkdir(parents=True)
    live.write_text("drifted")
    receipt_path = profiles / "zeus" / "pending" / "trace" / "corr123.json"
    make_receipt(receipt_path, live, "f" * 64)
    receipt = json.loads(receipt_path.read_text())
    receipt.update({"status": "blocked", "last_error": "live_hash_drift", "attempts": 3})
    receipt_path.write_text(json.dumps(receipt))

    result = mod.process_receipt(
        receipt_path,
        profiles_root=profiles,
        repo_root=repo,
        audit_path=repo / "logs" / "events-audit.jsonl",
        max_blocked_attempts=3,
    )
    repeated = mod.process_receipt(
        receipt_path,
        profiles_root=profiles,
        repo_root=repo,
        audit_path=repo / "logs" / "events-audit.jsonl",
        max_blocked_attempts=3,
    )

    persisted = json.loads(receipt_path.read_text())
    assert result["status"] == "quarantined"
    assert repeated["status"] == "already_quarantined"
    assert persisted["status"] == "quarantined"
    assert persisted["attempts"] == 3
    assert persisted["quarantine_reason"] == "live_hash_drift_retry_exhausted"


def test_rotates_large_log_and_keeps_bounded_compressed_history(tmp_path):
    mod = load_module()
    log = tmp_path / "finalizer.log"
    log.write_bytes(b"a" * 2048)

    assert mod.rotate_log_if_needed(log, max_bytes=1024, backups=2) is True
    assert log.read_bytes() == b""
    assert (tmp_path / "finalizer.log.1.gz").is_file()
    assert mod.rotate_log_if_needed(log, max_bytes=1024, backups=2) is False


def test_unrelated_later_drift_does_not_block_receipt(tmp_path):
    mod = load_module()
    profiles = tmp_path / "profiles"
    repo = tmp_path / "repo"
    skill_dir = profiles / "zeus" / "skills" / "ops" / "demo"
    live = skill_dir / "SKILL.md"
    unrelated = skill_dir / "references" / "later.md"
    unrelated.parent.mkdir(parents=True)
    live.write_text("new body")
    unrelated.write_text("state captured by receipt")

    receipt_path = profiles / "zeus" / "pending" / "trace" / "corr123.json"
    make_receipt(receipt_path, live, mod.sha256_file(live))
    receipt = json.loads(receipt_path.read_text())
    unrelated_digest = mod.sha256_file(unrelated)
    receipt["before"][str(unrelated)] = unrelated_digest
    receipt["after"][str(unrelated)] = unrelated_digest
    receipt["paths"].append(str(unrelated))
    receipt_path.write_text(json.dumps(receipt))

    unrelated.write_text("legitimate later write")

    def run_command(command):
        if command[0].endswith("sync-souls.sh"):
            mirror = mod.map_live_to_mirror(live, profiles_root=profiles, repo_root=repo)
            mirror.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, mirror)
        return "ok"

    result = mod.process_receipt(
        receipt_path,
        profiles_root=profiles,
        repo_root=repo,
        audit_path=repo / "logs" / "events-audit.jsonl",
        run_command=run_command,
        find_report=lambda correlation_id: None,
        send_report=lambda *args: "message-1",
        readback_report=lambda *args: True,
    )

    assert result["status"] == "closed"
    assert json.loads(receipt_path.read_text())["status"] == "closed"
