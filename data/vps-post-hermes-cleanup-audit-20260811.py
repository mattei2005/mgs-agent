#!/usr/bin/env python3
"""Read-only whole-VPS storage inventory after the Hermes 0.20 cutover.

No file is deleted. The report separates measurements from review-only cleanup
candidates and preserves the active and rollback Hermes runtimes.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

EXCLUDED = {"/proc", "/sys", "/dev", "/run"}
ROOT = Path("/")
ACTIVE_LAUNCHER = Path("/root/.local/bin/hermes")
ROLLBACK_RUNTIME = Path("/root/.hermes/hermes-agent-port-v0191-cc4cab2f")


def run(cmd: list[str], timeout: int = 120) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-1000:]}
    except Exception as exc:
        return {"rc": 125, "error": type(exc).__name__}


def tree_size(path: Path, root_dev: int) -> dict[str, int]:
    logical = allocated = files = dirs = errors = 0
    seen: set[tuple[int, int]] = set()
    stack = [path]
    while stack:
        cur = stack.pop()
        try:
            st = cur.lstat()
            if st.st_dev != root_dev:
                continue
            key = (st.st_dev, st.st_ino)
            if key in seen:
                continue
            seen.add(key)
            allocated += st.st_blocks * 512
            if cur.is_symlink():
                logical += st.st_size
                continue
            if cur.is_dir():
                dirs += 1
                with os.scandir(cur) as it:
                    stack.extend(Path(e.path) for e in it)
            else:
                files += 1
                logical += st.st_size
        except (OSError, PermissionError):
            errors += 1
    return {"logical_bytes": logical, "allocated_bytes": allocated, "files": files, "dirs": dirs, "errors": errors}


def full_scan(root_dev: int) -> dict[str, Any]:
    files = dirs = errors = logical = allocated = 0
    top_files: list[tuple[int, int, str]] = []
    by_top: dict[str, list[int]] = {}
    seen: set[tuple[int, int]] = set()
    stack = [ROOT]
    while stack:
        cur = stack.pop()
        s = str(cur)
        if s in EXCLUDED:
            continue
        try:
            st = cur.lstat()
            if st.st_dev != root_dev:
                continue
            key = (st.st_dev, st.st_ino)
            if key in seen:
                continue
            seen.add(key)
            alloc = st.st_blocks * 512
            allocated += alloc
            parts = cur.parts
            top = "/" if len(parts) < 2 else "/" + parts[1]
            bucket = by_top.setdefault(top, [0, 0, 0])
            bucket[1] += alloc
            if cur.is_symlink():
                continue
            if cur.is_dir():
                dirs += 1
                bucket[2] += 1
                with os.scandir(cur) as it:
                    stack.extend(Path(e.path) for e in it)
            else:
                files += 1
                logical += st.st_size
                bucket[0] += st.st_size
                if st.st_size >= 100 * 1024 * 1024:
                    top_files.append((st.st_size, alloc, s))
        except (OSError, PermissionError):
            errors += 1
    top_files.sort(reverse=True)
    return {
        "files": files,
        "dirs": dirs,
        "errors": errors,
        "logical_bytes": logical,
        "allocated_bytes": allocated,
        "by_top_level": {
            k: {"logical_bytes": v[0], "allocated_bytes": v[1], "dirs": v[2]}
            for k, v in sorted(by_top.items(), key=lambda kv: kv[1][1], reverse=True)
        },
        "files_over_100MiB": [
            {"path": p, "logical_bytes": n, "allocated_bytes": a}
            for n, a, p in top_files[:200]
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: vps-post-hermes-cleanup-audit-20260811.py OUTPUT.json", file=sys.stderr)
        return 2
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    root_dev = ROOT.stat().st_dev
    active_bin = Path(os.path.realpath(ACTIVE_LAUNCHER))
    active_runtime = active_bin.parents[2] if len(active_bin.parents) >= 3 else Path("")
    scan = full_scan(root_dev)

    candidates: list[dict[str, Any]] = []
    explicit = [
        (Path("/root/.cache"), "cache", "review"),
        (Path("/root/.npm"), "cache", "review"),
        (Path("/var/cache/apt/archives"), "apt_cache", "usually_safe"),
        (Path("/tmp"), "temporary", "age_review"),
        (Path("/root/mgs-agent/reports/hermes-updates"), "hermes_update_reports", "retain_one_canonical_rollback_set"),
        (Path("/root/.hermes/secure-backups"), "secure_backups", "retention_review"),
    ]
    for path, kind, policy in explicit:
        if path.exists():
            candidates.append({"path": str(path), "kind": kind, "policy": policy, **tree_size(path, root_dev)})

    runtime_candidates = []
    for path in sorted(Path("/root/.hermes").glob("hermes-agent*")):
        if not path.is_dir():
            continue
        preserved = path.resolve() in {active_runtime.resolve(), ROLLBACK_RUNTIME.resolve()}
        entry = {
            "path": str(path),
            "preserved": preserved,
            "reason": "active" if path.resolve() == active_runtime.resolve() else ("rollback" if path.resolve() == ROLLBACK_RUNTIME.resolve() else "old_runtime_review"),
            **tree_size(path, root_dev),
        }
        runtime_candidates.append(entry)

    usage = shutil.disk_usage("/")
    apt_sim = run(["apt-get", "-s", "autoremove"], 180)
    journal = run(["journalctl", "--disk-usage"], 60)
    failed = run(["systemctl", "--failed", "--no-legend", "--plain"], 60)
    report = {
        "schema": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "root filesystem, same-device only; excludes /proc /sys /dev /run and other mounted filesystems",
        "mutation_performed": False,
        "active_launcher": str(ACTIVE_LAUNCHER),
        "active_binary": str(active_bin),
        "active_runtime": str(active_runtime),
        "rollback_runtime": str(ROLLBACK_RUNTIME),
        "disk": {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free},
        "scan": scan,
        "review_roots": candidates,
        "hermes_runtimes": runtime_candidates,
        "apt_autoremove_simulation": apt_sim,
        "journal_disk_usage": journal,
        "failed_units": {"rc": failed.get("rc"), "lines": [x for x in failed.get("stdout", "").splitlines() if x.strip()]},
        "decision": "inventory_only_no_deletion; exact deletion manifest requires Rodolfo confirmation after review",
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "status": "PASS" if scan["errors"] == 0 else "PASS_WITH_SCAN_ERRORS",
        "output": str(output),
        "files": scan["files"],
        "dirs": scan["dirs"],
        "errors": scan["errors"],
        "free_bytes": usage.free,
        "runtime_entries": len(runtime_candidates),
        "review_roots": len(candidates),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
