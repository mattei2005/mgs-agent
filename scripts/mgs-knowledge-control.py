#!/usr/bin/env python3
"""MGS institutional knowledge capture, registry and continuity checkpoints.

This tool is deliberately narrow: it indexes canonical sources, captures durable
knowledge candidates, and stores resumable initiative checkpoints. It never
promotes chat text into policy or edits a canonical source by itself.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCHEMA_VERSION = 1
VALID_KINDS = {"source", "decision", "policy", "strategy", "capability", "procedure", "preference"}
VALID_STATUSES = {"active", "superseded", "retired", "draft"}
CLOSED_CHECKPOINT_STATES = {"completed", "cancelled", "closed"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
EXTERNAL_SOURCE_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


class ControlError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def paths(root: Path) -> Dict[str, Path]:
    data = root / "data"
    return {
        "data": data,
        "registry": data / "knowledge-registry.json",
        "inbox": data / "knowledge-inbox.jsonl",
        "checkpoints": data / "agent-checkpoints.json",
        "regression": data / "knowledge-regression-cases.json",
        "lock": data / ".knowledge-control.lock",
    }


def initial_registry() -> Dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "updated_at": now_iso(), "entries": []}


def initial_checkpoints() -> Dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "updated_at": now_iso(), "checkpoints": []}


def initial_regression_cases() -> Dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "cases": []}


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = ""
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        readback = json.loads(path.read_text(encoding="utf-8"))
        if readback != payload:
            raise ControlError(f"atomic readback mismatch: {path}")
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


@contextmanager
def locked(root: Path):
    p = paths(root)
    p["data"].mkdir(parents=True, exist_ok=True)
    with p["lock"].open("a+", encoding="utf-8") as handle:
        os.chmod(p["lock"], 0o640)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield p
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControlError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ControlError(f"expected JSON object: {path}")
    return value


def initialize(root: Path) -> Dict[str, Any]:
    with locked(root) as p:
        created: List[str] = []
        if not p["registry"].exists():
            atomic_write_json(p["registry"], initial_registry())
            created.append(str(p["registry"]))
        if not p["checkpoints"].exists():
            atomic_write_json(p["checkpoints"], initial_checkpoints())
            created.append(str(p["checkpoints"]))
        if not p["regression"].exists():
            atomic_write_json(p["regression"], initial_regression_cases())
            created.append(str(p["regression"]))
        if not p["inbox"].exists():
            fd = os.open(p["inbox"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
            os.close(fd)
            created.append(str(p["inbox"]))
        return {"status": "ok", "created": created}


def normalized_candidate(args: argparse.Namespace) -> Dict[str, Any]:
    identity = {
        "domain": args.domain.strip().lower(),
        "kind": args.kind.strip().lower(),
        "summary": args.summary.strip(),
        "owner": args.owner.strip(),
        "source": args.source.strip(),
        "proposed_target": args.proposed_target.strip(),
        "origin_agent": args.origin_agent.strip().lower(),
    }
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    candidate_id = "KCI-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return {
        "candidate_id": candidate_id,
        **identity,
        "status": "pending",
        "created_at": now_iso(),
    }


def read_inbox(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ControlError(f"invalid JSONL {path}:{number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ControlError(f"expected object in {path}:{number}")
        rows.append(row)
    return rows


def capture(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    if args.kind not in VALID_KINDS:
        raise ControlError(f"invalid kind: {args.kind}")
    row = normalized_candidate(args)
    with locked(root) as p:
        existing = read_inbox(p["inbox"])
        if any(item.get("candidate_id") == row["candidate_id"] for item in existing):
            return {"status": "ok", "candidate_id": row["candidate_id"], "deduplicated": True}
        with p["inbox"].open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        readback = read_inbox(p["inbox"])
        if not any(item == row for item in readback):
            raise ControlError("knowledge inbox readback failed")
    return {"status": "ok", "candidate_id": row["candidate_id"], "deduplicated": False}


def validate_id(value: str, label: str = "id") -> None:
    if not ID_RE.fullmatch(value):
        raise ControlError(f"invalid {label}: {value!r}")


def local_source_path(root: Path, source: str) -> Path | None:
    if EXTERNAL_SOURCE_RE.match(source):
        return None
    candidate = Path(source)
    return candidate if candidate.is_absolute() else root / candidate


def validate_registry(root: Path, registry: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append("registry schema_version mismatch")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        return errors + ["registry entries must be a list"]
    ids: Dict[str, int] = {}
    active_keys: Dict[str, str] = {}
    all_ids = {entry.get("id") for entry in entries if isinstance(entry, dict)}
    for index, entry in enumerate(entries):
        prefix = f"registry entry {index}"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not ID_RE.fullmatch(entry_id):
            errors.append(f"{prefix} has invalid id")
        else:
            ids[entry_id] = ids.get(entry_id, 0) + 1
        for field in ("kind", "domain", "title", "owner", "canonical_source", "canonical_key", "status"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix} missing {field}")
        if entry.get("kind") not in VALID_KINDS:
            errors.append(f"{prefix} invalid kind")
        if entry.get("status") not in VALID_STATUSES:
            errors.append(f"{prefix} invalid status")
        source = entry.get("canonical_source")
        if isinstance(source, str) and source.strip():
            local = local_source_path(root, source)
            if local is not None and not local.exists():
                errors.append(f"{prefix} missing local source: {source}")
        key = entry.get("canonical_key")
        if entry.get("status") == "active" and isinstance(key, str):
            if key in active_keys:
                errors.append(f"duplicate active canonical_key: {key}")
            active_keys[key] = str(entry_id)
        if entry.get("status") == "superseded":
            successor = entry.get("superseded_by")
            if successor not in all_ids:
                errors.append(f"{prefix} superseded_by target missing")
    for entry_id, count in ids.items():
        if count > 1:
            errors.append(f"duplicate registry id: {entry_id}")
    return errors


def validate_checkpoints(store: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if store.get("schema_version") != SCHEMA_VERSION:
        errors.append("checkpoint schema_version mismatch")
    rows = store.get("checkpoints")
    if not isinstance(rows, list):
        return errors + ["checkpoints must be a list"]
    seen = set()
    for index, row in enumerate(rows):
        prefix = f"checkpoint {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        record_id = row.get("id")
        if not isinstance(record_id, str) or not ID_RE.fullmatch(record_id):
            errors.append(f"{prefix} invalid id")
        elif record_id in seen:
            errors.append(f"duplicate checkpoint id: {record_id}")
        seen.add(record_id)
        for field in ("agent", "thread_id", "objective", "state", "next_step", "source", "updated_at"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix} missing {field}")
    return errors


def validate_inbox(rows: Iterable[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    seen = set()
    for index, row in enumerate(rows):
        candidate_id = row.get("candidate_id")
        if not isinstance(candidate_id, str) or not ID_RE.fullmatch(candidate_id):
            errors.append(f"inbox row {index} invalid candidate_id")
        elif candidate_id in seen:
            errors.append(f"duplicate inbox candidate_id: {candidate_id}")
        seen.add(candidate_id)
        for field in ("domain", "kind", "summary", "owner", "source", "proposed_target", "origin_agent", "status", "created_at"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"inbox row {index} missing {field}")
    return errors


def validate_regression_cases(root: Path, store: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if store.get("schema_version") != SCHEMA_VERSION:
        errors.append("regression schema_version mismatch")
    cases = store.get("cases")
    if not isinstance(cases, list):
        return errors + ["regression cases must be a list"]
    seen = set()
    for index, case in enumerate(cases):
        prefix = f"regression case {index}"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id):
            errors.append(f"{prefix} invalid id")
        elif case_id in seen:
            errors.append(f"duplicate regression id: {case_id}")
        seen.add(case_id)
        for field in ("question", "source"):
            value = case.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix} missing {field}")
        for field in ("required_all", "forbidden_any"):
            values = case.get(field)
            if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
                errors.append(f"{prefix} invalid {field}")
        source = case.get("source")
        if isinstance(source, str) and source.strip():
            local = local_source_path(root, source)
            if local is None or not local.exists():
                errors.append(f"{prefix} missing local source: {source}")
    return errors


def run_regression(root: Path) -> Dict[str, Any]:
    p = paths(root)
    store = load_json(p["regression"], initial_regression_cases())
    schema_errors = validate_regression_cases(root, store)
    results: List[Dict[str, Any]] = []
    if not schema_errors:
        for case in store.get("cases", []):
            source_path = local_source_path(root, case["source"])
            assert source_path is not None
            text = source_path.read_text(encoding="utf-8", errors="replace").casefold()
            case_errors = []
            for term in case["required_all"]:
                if term.casefold() not in text:
                    case_errors.append(f"missing required term: {term}")
            for term in case["forbidden_any"]:
                if term.casefold() in text:
                    case_errors.append(f"forbidden term present: {term}")
            results.append({
                "id": case["id"],
                "question": case["question"],
                "source": case["source"],
                "status": "ok" if not case_errors else "error",
                "errors": case_errors,
            })
    failed = len(schema_errors) or sum(1 for result in results if result["status"] == "error")
    return {
        "status": "ok" if not schema_errors and failed == 0 else "error",
        "schema_errors": schema_errors,
        "passed": sum(1 for result in results if result["status"] == "ok"),
        "failed": failed,
        "results": results,
    }


def validate_all(root: Path) -> Dict[str, Any]:
    p = paths(root)
    errors: List[str] = []
    try:
        registry = load_json(p["registry"], initial_registry())
        checkpoints = load_json(p["checkpoints"], initial_checkpoints())
        regression = load_json(p["regression"], initial_regression_cases())
        inbox = read_inbox(p["inbox"])
        errors.extend(validate_registry(root, registry))
        errors.extend(validate_checkpoints(checkpoints))
        errors.extend(validate_inbox(inbox))
        errors.extend(validate_regression_cases(root, regression))
    except ControlError as exc:
        errors.append(str(exc))
        registry, checkpoints, regression, inbox = {"entries": []}, {"checkpoints": []}, {"cases": []}, []
    return {
        "status": "ok" if not errors else "error",
        "errors": errors,
        "registry_entries": len(registry.get("entries", [])),
        "inbox_candidates": len(inbox),
        "checkpoints": len(checkpoints.get("checkpoints", [])),
        "regression_cases": len(regression.get("cases", [])),
    }


def register(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    validate_id(args.id)
    if args.kind not in VALID_KINDS:
        raise ControlError(f"invalid kind: {args.kind}")
    if args.status not in VALID_STATUSES:
        raise ControlError(f"invalid status: {args.status}")
    entry = {
        "id": args.id,
        "kind": args.kind,
        "domain": args.domain.strip().lower(),
        "title": args.title.strip(),
        "owner": args.owner.strip(),
        "canonical_source": args.source.strip(),
        "canonical_key": args.canonical_key.strip(),
        "status": args.status,
        "consumers": sorted(set(args.consumer or [])),
        "effective_at": args.effective_at or now_iso(),
        "review_due": args.review_due or None,
        "superseded_by": None,
        "updated_at": now_iso(),
    }
    local = local_source_path(root, entry["canonical_source"])
    if local is not None and not local.exists():
        raise ControlError(f"missing local source: {entry['canonical_source']}")
    with locked(root) as p:
        registry = load_json(p["registry"], initial_registry())
        entries = registry.setdefault("entries", [])
        if any(item.get("id") == entry["id"] for item in entries):
            raise ControlError(f"registry id already exists: {entry['id']}")
        supersedes_id = getattr(args, "supersedes", None)
        superseded = None
        if supersedes_id:
            superseded = next((item for item in entries if item.get("id") == supersedes_id), None)
            if superseded is None:
                raise ControlError(f"superseded registry entry missing: {supersedes_id}")
            if superseded.get("status") != "active":
                raise ControlError(f"entry is not active: {supersedes_id}")
            if entry["status"] != "active":
                raise ControlError("a superseding registry entry must be active")
            if superseded.get("canonical_key") != entry["canonical_key"]:
                raise ControlError("superseding registry entry must preserve canonical_key")
        if entry["status"] == "active" and any(
            item.get("status") == "active"
            and item.get("canonical_key") == entry["canonical_key"]
            and item.get("id") != supersedes_id
            for item in entries
        ):
            raise ControlError(f"active canonical_key already exists: {entry['canonical_key']}")
        entries.append(entry)
        if superseded is not None:
            superseded["status"] = "superseded"
            superseded["superseded_by"] = entry["id"]
            superseded["updated_at"] = now_iso()
        entries.sort(key=lambda item: item.get("id", ""))
        registry["updated_at"] = now_iso()
        errors = validate_registry(root, registry)
        if errors:
            raise ControlError("; ".join(errors))
        atomic_write_json(p["registry"], registry)
    result = "created_and_superseded" if superseded is not None else "created"
    return {"status": "ok", "id": entry["id"], "result": result, "supersedes": supersedes_id}


def supersede(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    validate_id(args.id)
    validate_id(args.by, "successor id")
    with locked(root) as p:
        registry = load_json(p["registry"], initial_registry())
        entries = registry.get("entries", [])
        old = next((item for item in entries if item.get("id") == args.id), None)
        new = next((item for item in entries if item.get("id") == args.by), None)
        if old is None or new is None:
            raise ControlError("both old and successor registry entries must exist")
        if old.get("status") != "active":
            raise ControlError(f"entry is not active: {args.id}")
        if new.get("status") != "active":
            raise ControlError(f"successor is not active: {args.by}")
        old["status"] = "superseded"
        old["superseded_by"] = args.by
        old["updated_at"] = now_iso()
        registry["updated_at"] = now_iso()
        errors = validate_registry(root, registry)
        if errors:
            raise ControlError("; ".join(errors))
        atomic_write_json(p["registry"], registry)
    return {"status": "ok", "id": args.id, "superseded_by": args.by}


def checkpoint_upsert(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    validate_id(args.id)
    row = {
        "id": args.id,
        "agent": args.agent.strip().lower(),
        "thread_id": args.thread_id.strip(),
        "objective": args.objective.strip(),
        "state": args.state.strip().lower(),
        "next_step": args.next_step.strip(),
        "source": args.source.strip(),
        "updated_at": now_iso(),
    }
    with locked(root) as p:
        store = load_json(p["checkpoints"], initial_checkpoints())
        rows = store.setdefault("checkpoints", [])
        existing = next((item for item in rows if item.get("id") == row["id"]), None)
        result = "updated" if existing is not None else "created"
        if existing is None:
            rows.append(row)
        else:
            existing.clear()
            existing.update(row)
        rows.sort(key=lambda item: item.get("id", ""))
        store["updated_at"] = now_iso()
        errors = validate_checkpoints(store)
        if errors:
            raise ControlError("; ".join(errors))
        atomic_write_json(p["checkpoints"], store)
    return {"status": "ok", "id": args.id, "result": result}


def status(root: Path) -> Dict[str, Any]:
    p = paths(root)
    registry = load_json(p["registry"], initial_registry())
    checkpoints = load_json(p["checkpoints"], initial_checkpoints())
    regression = load_json(p["regression"], initial_regression_cases())
    inbox = read_inbox(p["inbox"])
    active = sum(1 for row in checkpoints.get("checkpoints", []) if row.get("state") not in CLOSED_CHECKPOINT_STATES)
    pending = sum(1 for row in inbox if row.get("status") == "pending")
    return {
        "status": "ok",
        "registry_entries": len(registry.get("entries", [])),
        "pending_candidates": pending,
        "active_checkpoints": active,
        "regression_cases": len(regression.get("cases", [])),
    }


def add_common_register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id", required=True)
    parser.add_argument("--kind", required=True, choices=sorted(VALID_KINDS))
    parser.add_argument("--domain", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--canonical-key", required=True)
    parser.add_argument("--status", default="active", choices=sorted(VALID_STATUSES))
    parser.add_argument("--consumer", action="append", default=[])
    parser.add_argument("--effective-at")
    parser.add_argument("--review-due")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/root/mgs-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")

    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--domain", required=True)
    capture_parser.add_argument("--kind", required=True, choices=sorted(VALID_KINDS))
    capture_parser.add_argument("--summary", required=True)
    capture_parser.add_argument("--owner", required=True)
    capture_parser.add_argument("--source", required=True)
    capture_parser.add_argument("--proposed-target", required=True)
    capture_parser.add_argument("--origin-agent", required=True)

    register_parser = sub.add_parser("register")
    add_common_register_args(register_parser)
    register_parser.add_argument("--supersedes")

    supersede_parser = sub.add_parser("supersede")
    supersede_parser.add_argument("--id", required=True)
    supersede_parser.add_argument("--by", required=True)

    checkpoint_parser = sub.add_parser("checkpoint-upsert")
    checkpoint_parser.add_argument("--id", required=True)
    checkpoint_parser.add_argument("--agent", required=True)
    checkpoint_parser.add_argument("--thread-id", required=True)
    checkpoint_parser.add_argument("--objective", required=True)
    checkpoint_parser.add_argument("--state", required=True)
    checkpoint_parser.add_argument("--next-step", required=True)
    checkpoint_parser.add_argument("--source", required=True)

    sub.add_parser("validate")
    sub.add_parser("regression")
    sub.add_parser("status")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        if args.command == "init":
            result = initialize(root)
        elif args.command == "capture":
            initialize(root)
            result = capture(root, args)
        elif args.command == "register":
            initialize(root)
            result = register(root, args)
        elif args.command == "supersede":
            initialize(root)
            result = supersede(root, args)
        elif args.command == "checkpoint-upsert":
            initialize(root)
            result = checkpoint_upsert(root, args)
        elif args.command == "validate":
            initialize(root)
            result = validate_all(root)
            print_json(result)
            return 0 if result["status"] == "ok" else 1
        elif args.command == "regression":
            initialize(root)
            result = run_regression(root)
            print_json(result)
            return 0 if result["status"] == "ok" else 1
        elif args.command == "status":
            initialize(root)
            result = status(root)
        else:  # pragma: no cover
            parser.error("unknown command")
            return 2
        print_json(result)
        return 0
    except ControlError as exc:
        print_json({"status": "error", "error": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
