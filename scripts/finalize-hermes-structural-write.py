#!/usr/bin/env python3
"""Finalize metadata-only receipts for MGS-synced automatic Hermes skill writes."""

from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

DEFAULT_PROFILES_ROOT = Path("/root/.hermes/profiles")
DEFAULT_REPO_ROOT = Path("/root/mgs-agent")
DEFAULT_AUDIT = DEFAULT_REPO_ROOT / "logs" / "events-audit.jsonl"
DEFAULT_CHANNEL = "1498132022634483894"
DEFAULT_ZEUS_ENV = Path("/root/.hermes/profiles/zeus/.env")
DEFAULT_LOG = DEFAULT_REPO_ROOT / "logs" / "hermes-structural-write-finalizer.log"
DEFAULT_MAX_BLOCKED_ATTEMPTS = 3
DEFAULT_MAX_LOG_BYTES = 50 * 1024 * 1024
DEFAULT_LOG_BACKUPS = 5
PROFILES = ("zeus", "atena", "ares")
ZEUS_SYNCED_GROWTH = {
    "meta-utility-template-approval",
    "meta-app-rate-limit-monitor",
    "segurador-page-health-monitor",
    "meta-ads-api-operations",
}
ARES_SYNCED_OPS = {"discord-ops", "log-monitor-discord-alert"}


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def changed_paths(receipt: Dict[str, Any]) -> set[str]:
    """Return only paths whose before/after state was changed by this receipt."""
    before = receipt.get("before") or {}
    after = receipt.get("after") or {}
    return {
        raw_path
        for raw_path in set(before) | set(after)
        if before.get(raw_path) != after.get(raw_path)
    }


def map_live_to_mirror(
    live_path: Path | str,
    *,
    profiles_root: Path | str = DEFAULT_PROFILES_ROOT,
    repo_root: Path | str = DEFAULT_REPO_ROOT,
) -> Optional[Path]:
    """Map a live profile skill file to its selective versioned MGS mirror."""
    live = Path(live_path)
    profiles = Path(profiles_root)
    repo = Path(repo_root)
    try:
        relative = live.relative_to(profiles)
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) < 5 or parts[1] != "skills":
        return None
    profile, category, skill_name = parts[0], parts[2], parts[3]
    synced = False
    if profile == "zeus":
        synced = category == "ops" or (
            category == "growth" and skill_name in ZEUS_SYNCED_GROWTH
        )
    elif profile == "atena":
        synced = category in {"wordpress", "devops"}
    elif profile == "ares":
        synced = category == "growth" or (
            category == "ops" and skill_name in ARES_SYNCED_OPS
        )
    if not synced:
        return None
    return repo / "profiles" / f"{profile}-skills" / Path(*parts[2:])


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temp_name: Optional[str] = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
        )
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        temp_name = None
        os.chmod(path, 0o600)
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def rotate_log_if_needed(
    path: Path | str = DEFAULT_LOG,
    *,
    max_bytes: int = DEFAULT_MAX_LOG_BYTES,
    backups: int = DEFAULT_LOG_BACKUPS,
) -> bool:
    """Compress and truncate the cron log before it grows without bound.

    The cron shell opens the append target before launching this process. Truncating
    the same inode therefore keeps stdout valid while reclaiming the old contents.
    """
    log_path = Path(path)
    if backups < 1 or not log_path.is_file() or log_path.stat().st_size <= max_bytes:
        return False
    for index in range(backups, 1, -1):
        older = Path(f"{log_path}.{index - 1}.gz")
        newer = Path(f"{log_path}.{index}.gz")
        if older.exists():
            os.replace(older, newer)
    target = Path(f"{log_path}.1.gz")
    temporary = Path(f"{target}.tmp")
    try:
        with log_path.open("rb") as source, gzip.open(temporary, "wb", compresslevel=6) as sink:
            shutil.copyfileobj(source, sink, length=1024 * 1024)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        with log_path.open("wb"):
            pass
        os.chmod(log_path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _run_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command_failed rc={result.returncode} cmd={Path(command[0]).name} "
            f"stderr={result.stderr[:300]}"
        )
    return result.stdout.strip()


def _load_env(path: Path = DEFAULT_ZEUS_ENV) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _discord_request(url: str) -> Any:
    _load_env()
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("discord_bot_token_missing")
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bot " + token,
            "User-Agent": "MGS-Zeus/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"discord_get_http_{response.status}")
        return json.load(response)


def _embed_has_correlation(message: Dict[str, Any], correlation_id: str) -> bool:
    for embed in message.get("embeds") or []:
        for field in embed.get("fields") or []:
            if correlation_id in str(field.get("value") or ""):
                return True
    return False


def find_report_by_correlation(correlation_id: str) -> Optional[str]:
    messages = _discord_request(
        f"https://discord.com/api/v10/channels/{DEFAULT_CHANNEL}/messages?limit=100"
    )
    for message in messages:
        if _embed_has_correlation(message, correlation_id):
            return str(message.get("id") or "") or None
    return None


def readback_report(message_id: str, correlation_id: str) -> bool:
    message = _discord_request(
        f"https://discord.com/api/v10/channels/{DEFAULT_CHANNEL}/messages/{message_id}"
    )
    titles = [str(embed.get("title") or "") for embed in message.get("embeds") or []]
    return (
        message.get("content", "") == ""
        and any(title.startswith("REPORT-INFRA") for title in titles)
        and _embed_has_correlation(message, correlation_id)
    )


def send_report(
    receipt: Dict[str, Any],
    mirror_paths: Iterable[str],
    *,
    repo_root: Path | str = DEFAULT_REPO_ROOT,
) -> str:
    repo = Path(repo_root)
    correlation = str(receipt["correlation_id"])
    paths = "; ".join(str(path) for path in mirror_paths)
    evidence = (
        f"correlation={correlation}; profile={receipt.get('profile')}; "
        f"action={receipt.get('action')}; post-write hashes verified; "
        "mirror/inventory finalized"
    )
    output = _run_command([
        str(repo / "scripts" / "send-report-infra-embed.sh"),
        "--action", "modificada",
        "--type", "skill/autowrite",
        "--path", paths,
        "--reason", "Fechar rastreabilidade estrutural de write automático Hermes.",
        "--evidence", evidence,
    ])
    match = re.search(r"message_id=(\d+)", output)
    if not match:
        raise RuntimeError("report_message_id_missing")
    return match.group(1)


def _audit_has_correlation(path: Path, correlation_id: str) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            if json.loads(line).get("correlation_id") == correlation_id:
                return True
        except Exception:
            continue
    return False


def _append_audit_once(
    path: Path,
    receipt: Dict[str, Any],
    mirror_paths: list[str],
    report_message_id: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    correlation = str(receipt["correlation_id"])
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        found = False
        for line in stream:
            try:
                if json.loads(line).get("correlation_id") == correlation:
                    found = True
                    break
            except Exception:
                continue
        if not found:
            event = {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event": "hermes_structural_autowrite_finalized",
                "actor": "hermes-trace-finalizer",
                "correlation_id": correlation,
                "profile": receipt.get("profile"),
                "subsystem": receipt.get("subsystem"),
                "action": receipt.get("action"),
                "target": receipt.get("target"),
                "origin": receipt.get("origin"),
                "session": receipt.get("session") or {},
                "before": receipt.get("before") or {},
                "after": receipt.get("after") or {},
                "mirror_paths": mirror_paths,
                "report_message_id": report_message_id,
                "inventory_updated": True,
            }
            stream.seek(0, os.SEEK_END)
            stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _validate_live(receipt: Dict[str, Any]) -> bool:
    after = receipt.get("after") or {}
    for raw_path in changed_paths(receipt):
        path = Path(raw_path)
        if raw_path in after:
            if not path.is_file() or sha256_file(path) != after[raw_path]:
                return False
        elif path.exists():
            return False
    return True


def _validate_mirrors(
    receipt: Dict[str, Any],
    *,
    profiles_root: Path,
    repo_root: Path,
) -> tuple[bool, list[str]]:
    after = receipt.get("after") or {}
    mirror_paths: list[str] = []
    for raw_path in sorted(changed_paths(receipt)):
        mirror = map_live_to_mirror(
            raw_path, profiles_root=profiles_root, repo_root=repo_root
        )
        if mirror is None:
            continue
        mirror_paths.append(str(mirror))
        if raw_path in after:
            if not mirror.is_file() or sha256_file(mirror) != after[raw_path]:
                return False, mirror_paths
        elif mirror.exists():
            return False, mirror_paths
    return True, mirror_paths


def process_receipt(
    receipt_path: Path | str,
    *,
    profiles_root: Path | str = DEFAULT_PROFILES_ROOT,
    repo_root: Path | str = DEFAULT_REPO_ROOT,
    audit_path: Path | str = DEFAULT_AUDIT,
    run_command: Callable[[list[str]], str] = _run_command,
    find_report: Callable[[str], Optional[str]] = find_report_by_correlation,
    send_report: Optional[Callable[[Dict[str, Any], list[str]], str]] = None,
    readback_report: Callable[[str, str], bool] = readback_report,
    max_blocked_attempts: int = DEFAULT_MAX_BLOCKED_ATTEMPTS,
) -> Dict[str, Any]:
    path = Path(receipt_path)
    profiles = Path(profiles_root)
    repo = Path(repo_root)
    audit = Path(audit_path)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("status") == "closed":
        return {"status": "already_closed", "id": receipt.get("id")}
    if receipt.get("status") == "quarantined":
        return {"status": "already_quarantined", "id": receipt.get("id")}

    attempts = int(receipt.get("attempts") or 0)
    if (
        receipt.get("status") == "blocked"
        and receipt.get("last_error") == "live_hash_drift"
        and attempts >= max_blocked_attempts
    ):
        receipt.update({
            "status": "quarantined",
            "quarantine_reason": "live_hash_drift_retry_exhausted",
            "quarantined_at": time.time(),
        })
        _atomic_write_json(path, receipt)
        return {
            "status": "quarantined",
            "reason": receipt["quarantine_reason"],
            "id": receipt.get("correlation_id") or receipt.get("id") or path.stem,
        }

    correlation = str(receipt.get("correlation_id") or receipt.get("id") or path.stem)
    receipt["correlation_id"] = correlation
    receipt["attempts"] = attempts + 1

    mapped = [
        map_live_to_mirror(raw, profiles_root=profiles, repo_root=repo)
        for raw in changed_paths(receipt)
    ]
    if not any(mapped):
        receipt.update({
            "status": "closed",
            "closure": "not_mgs_synced",
            "closed_at": time.time(),
        })
        _atomic_write_json(path, receipt)
        return {"status": "closed", "reason": "not_mgs_synced", "id": correlation}

    if not _validate_live(receipt):
        receipt.update({"status": "blocked", "last_error": "live_hash_drift"})
        _atomic_write_json(path, receipt)
        return {"status": "blocked", "reason": "live_hash_drift", "id": correlation}

    try:
        run_command([str(repo / "scripts" / "sync-souls.sh")])
        mirrors_ok, mirror_paths = _validate_mirrors(
            receipt, profiles_root=profiles, repo_root=repo
        )
        if not mirrors_ok:
            raise RuntimeError("mirror_hash_mismatch")
        run_command([str(repo / "scripts" / "infra-discovery.sh")])

        message_id = str(receipt.get("report_message_id") or "") or find_report(correlation)
        if not message_id:
            sender = send_report or (
                lambda current, paths: globals()["send_report"](
                    current, paths, repo_root=repo
                )
            )
            message_id = sender(receipt, mirror_paths)
        receipt.update({"status": "report_sent", "report_message_id": message_id})
        _atomic_write_json(path, receipt)

        if not readback_report(message_id, correlation):
            raise RuntimeError("report_readback_failed")
        _append_audit_once(audit, receipt, mirror_paths, message_id)
        receipt.update({
            "status": "closed",
            "closed_at": time.time(),
            "last_error": "",
            "report_message_id": message_id,
            "mirror_paths": mirror_paths,
            "inventory_updated": True,
            "audit_updated": True,
            "report_readback": True,
        })
        _atomic_write_json(path, receipt)
        return {"status": "closed", "id": correlation, "report_message_id": message_id}
    except Exception as exc:
        receipt.update({
            "status": "blocked",
            "last_error": f"{type(exc).__name__}: {exc}",
        })
        _atomic_write_json(path, receipt)
        return {"status": "blocked", "reason": receipt["last_error"], "id": correlation}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles-root", type=Path, default=DEFAULT_PROFILES_ROOT)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--max-blocked-attempts", type=int, default=DEFAULT_MAX_BLOCKED_ATTEMPTS)
    parser.add_argument("--max-log-bytes", type=int, default=DEFAULT_MAX_LOG_BYTES)
    parser.add_argument("--log-backups", type=int, default=DEFAULT_LOG_BACKUPS)
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    rotated = rotate_log_if_needed(
        args.log_path,
        max_bytes=args.max_log_bytes,
        backups=args.log_backups,
    )
    if args.receipt:
        paths = [args.receipt]
    else:
        paths = []
        for profile in PROFILES:
            directory = args.profiles_root / profile / "pending" / "trace"
            if directory.exists():
                paths.extend(sorted(directory.glob("*.json")))
    results = [
        process_receipt(
            path,
            profiles_root=args.profiles_root,
            repo_root=args.repo_root,
            audit_path=args.audit_path,
            max_blocked_attempts=args.max_blocked_attempts,
        )
        for path in paths
    ]
    status_counts: Dict[str, int] = {}
    for item in results:
        status = str(item.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    summary: Dict[str, Any] = {
        "scanned": len(paths),
        "processed": sum(
            count
            for status, count in status_counts.items()
            if status not in {"already_closed", "already_quarantined"}
        ),
        "status_counts": status_counts,
        "log_rotated": rotated,
    }
    if args.verbose or args.receipt:
        summary["results"] = results
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if any(item.get("status") == "blocked" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
