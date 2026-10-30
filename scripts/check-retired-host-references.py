#!/usr/bin/env python3
"""Fail closed when a retired MGS host reappears on operational surfaces."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RETIRED_HOST = "87.99." + "151.107"
REPO = Path("/root/mgs-agent")
MAX_FILE_BYTES = 8_000_000

# Historical evidence is preserved intentionally and must not drive connections.
REPO_ALLOWLIST_PREFIXES = (
    "logs/events-audit.jsonl",
    "data/discord-thread-imports/",
    "data/infra-inventory.json",
    "backups/",
)

# This immutable pre-change inventory records a REMOVED firewall rule, not a
# connection target. Preserve its historical evidence without exempting its
# parent directory or future snapshots. Any byte change revokes the exemption.
HISTORICAL_EVIDENCE_SHA256 = {
    "data/zeus/meta-campaign-rename/1555626535980114000/inventory-before-runtime-entry.json":
        "70d47a6b52bbed213b8558a5fef1b73e294ea896509b7ca0731c24c6e54620d1",
    # Authorized AdsPower delivery amendment: immutable before-image of the
    # canonical inventory; its only retired-host hit is removed_validated
    # firewall history. Audit authority 1559206352956432395. No parent exemption.
    "data/adspower-warming-20261008/delivery-amendment-1559206352956432395/inventory-before.json":
        "aebab065306cc85eac7bab53efdf3eae1c4affac46da2d324b371974e543f437",
    # Audited PHP recheck: the sole hit explicitly says the retired agent was
    # NOT probed. Hash reconciled with infra-inventory record
    # hetzner-php-recheck-1562886130582552618; no reports/ directory exemption.
    "reports/php-security-20261021/hetzner-recheck-1562886130582552618.json":
        "1bd0e08c60977607a2689aaeca409ca1f866a7b18ae50562ae9005df05de2d6d",
    # Authorized schedule pre-change inventory (1563960345826037821): its
    # sole hit is removed_validated firewall history, identical to the live
    # canonical inventory record. Preserve only this exact immutable snapshot.
    "reports/meta-manual-payments-scheduling-1563960345826037821/inventory-pre-update.json":
        "ec73c34f09b9c3a8e80f32246d68242ee6187b1d11b9741c06ffc1e0642e3123",
    # Authorized before-images reconciled with REPORT-INFRA 1563994125924176056,
    # 1564026420827791371 and 1563999971219603627. Each has exactly one hit:
    # the unchanged canonical removed_validated firewall history, not a target.
    # Preserve exact bytes only; changed snapshots and siblings still fail.
    "reports/meta-pay-now-1563981039230255186/inventory-pre-update.json":
        "57d7d665cda7979f29abda806ba70cb245337a13e67ff854c6b75a5a6d1dcbfd",
    "reports/meta-september-invoices-1564022485366734969/inventory-before.json":
        "d7cc803898a2f4d28ceaa39d2d0a24f59c43bf7721add9ca3c6b1b3bacf8cead",
    "reports/meta-sheet-subtitle-1563999324587819020/inventory-before.json":
        "9672a1417db6d00da92f1edd3575aec206415a39b6fc96b07f1043b7d94a6519",
}

# Inventory before-images recur during authorized operations. Recognize only
# the pinned, already-removed firewall record, never a directory or live target.
REMOVED_FIREWALL_RECORD_SHA256 = "5671c8b06110f9417fd6dd7a7cf2a84e9f79d15d7a0a798089495b5efa84bf2a"


def historical_inventory_only(path: Path, relative: str) -> bool:
    parts = Path(relative).parts
    # Kanban rollback before-images use the same canonical inventory schema.
    # Permit their naming/location only; provenance, the pinned removed record
    # and the full-document target scan below remain mandatory for every file.
    if (not parts or parts[0] not in {"data", "reports", "work"}
            or not path.name.startswith(("inventory-before", "inventory-pre-",
                                         "infra-inventory-before"))
            or path.suffix != ".json"):
        return False
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
        content = path.read_text(encoding="utf-8")
        if content.count(RETIRED_HOST) != 1:
            return False
        inventory = json.loads(content)
        if not isinstance(inventory, dict):
            return False
        metadata = inventory.get("_meta")
        if (not isinstance(metadata, dict)
                or metadata.get("generated_by") != "infra-discovery.sh"):
            return False
        records = inventory.get("runtime_artifacts")
        if not isinstance(records, list):
            return False
        hits = [record for record in records if RETIRED_HOST in json.dumps(record)]
        if len(hits) != 1:
            return False
        encoded = json.dumps(hits[0], sort_keys=True, separators=(",", ":")).encode()
        if hashlib.sha256(encoded).hexdigest() != REMOVED_FIREWALL_RECORD_SHA256:
            return False
        # Re-scan the entire parsed document, keys included. JSON-escaped
        # additional connection addresses must also remain blocking.
        inventory["runtime_artifacts"] = [record for record in records if record is not hits[0]]
        return RETIRED_HOST not in json.dumps(inventory)
    except (OSError, UnicodeError, ValueError, TypeError):
        return False


PROFILE_NAMES = ("zeus", "atena", "ares")
PROFILE_OPERATIONAL_NAMES = ("config.yaml", "SOUL.md", "skills", "scripts", "cron")
SYSTEM_PATHS = (
    Path("/etc/systemd/system"),
    Path("/etc/cron.d"),
    Path("/etc/cron.daily"),
    Path("/etc/cron.hourly"),
    Path("/etc/cron.weekly"),
    Path("/etc/cron.monthly"),
    Path("/root/.ssh/config"),
)


def read_contains(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return False
        return RETIRED_HOST in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def scan_tree(path: Path, label: str, failures: list[str]) -> None:
    if path.is_file():
        if read_contains(path):
            failures.append(f"{label}:{path}")
        return
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {".git", "logs", "sessions", "browser-profiles", "home", "cache", "audio_cache", "pending"}]
        for filename in files:
            candidate = Path(root) / filename
            if read_contains(candidate):
                failures.append(f"{label}:{candidate}")


def tracked_repo_failures(failures: list[str]) -> None:
    result = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="surrogateescape")
        if any(relative == prefix or relative.startswith(prefix) for prefix in REPO_ALLOWLIST_PREFIXES):
            continue
        path = REPO / relative
        expected_hash = HISTORICAL_EVIDENCE_SHA256.get(relative)
        if expected_hash is not None:
            try:
                if hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash:
                    continue
            except OSError:
                pass
        if read_contains(path) and not historical_inventory_only(path, relative):
            failures.append(f"repo:{relative}")


def crontab_failure(failures: list[str]) -> None:
    result = subprocess.run(["crontab", "-l"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if RETIRED_HOST in result.stdout:
        failures.append("root-crontab")


def hashed_known_host_failures(failures: list[str]) -> None:
    for path in sorted(Path("/root/.ssh").glob("known_hosts*")):
        if not path.is_file():
            continue
        result = subprocess.run(
            ["ssh-keygen", "-F", RETIRED_HOST, "-f", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            failures.append(f"known-host:{path}")


def main() -> int:
    failures: list[str] = []
    tracked_repo_failures(failures)

    for profile in PROFILE_NAMES:
        root = Path("/root/.hermes/profiles") / profile
        for name in PROFILE_OPERATIONAL_NAMES:
            scan_tree(root / name, f"profile-{profile}", failures)

    for path in SYSTEM_PATHS:
        scan_tree(path, "system", failures)

    crontab_failure(failures)
    hashed_known_host_failures(failures)

    if failures:
        print("FAIL retired-host-reference guard")
        for failure in sorted(set(failures))[:100]:
            print(f"- {failure}")
        return 1

    print("OK retired-host-reference guard: no operational references or hashed known-host entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
