#!/usr/bin/env python3
"""Automatic residual capacity protection for Hermes USER/MEMORY stores.

Discovers immediate active profiles, checks bounded store usage, and invokes the
fail-closed semantic compactor at >=90%. Successful compactions and failures are
reported as metadata-only Discord embeds through a durable outbox. Store content
is never printed, logged, or sent to Discord.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence

import yaml

DEFAULT_PROFILES_ROOT = Path("/root/.hermes/profiles")
DEFAULT_STATE_FILE = Path("/root/mgs-agent/data/hermes-memory-capacity-state.json")
DEFAULT_COMPACTOR = Path("/root/mgs-agent/scripts/hermes-memory-autocompactor.py")
DEFAULT_POSTER = Path("/root/mgs-agent/scripts/discord-bot-post.py")
DEFAULT_BACKUP_ROOT = Path("/root/.hermes/secure-backups/memory-autocompaction")
DEFAULT_CHANNEL_ID = "1527401973698007060"
DEFAULT_THRESHOLD_PERCENT = 90.0
DEFAULT_TARGET_PERCENT = 85.0
DEFAULT_COMPACTOR_TIMEOUT = 900
ALERT_COOLDOWN = timedelta(hours=2)
STATE_SCHEMA_VERSION = 1


class Settings:
    def __init__(
        self,
        *,
        profiles_root: Path = DEFAULT_PROFILES_ROOT,
        state_file: Path = DEFAULT_STATE_FILE,
        compactor: Path = DEFAULT_COMPACTOR,
        poster: Path = DEFAULT_POSTER,
        backup_root: Path = DEFAULT_BACKUP_ROOT,
        threshold_percent: float = DEFAULT_THRESHOLD_PERCENT,
        target_percent: float = DEFAULT_TARGET_PERCENT,
        channel_id: str = DEFAULT_CHANNEL_ID,
        profile_filter: Sequence[str] = (),
        dry_run: bool = False,
        no_post: bool = False,
        compactor_timeout: int = DEFAULT_COMPACTOR_TIMEOUT,
    ) -> None:
        self.profiles_root = Path(profiles_root)
        self.state_file = Path(state_file)
        self.compactor = Path(compactor)
        self.poster = Path(poster)
        self.backup_root = Path(backup_root)
        self.threshold_percent = float(threshold_percent)
        self.target_percent = float(target_percent)
        self.channel_id = str(channel_id)
        self.profile_filter = tuple(profile_filter)
        self.dry_run = bool(dry_run)
        self.no_post = bool(no_post)
        self.compactor_timeout = int(compactor_timeout)


class CompactionRunError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class DeliveryError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _event_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]


def discover_profiles(root: Path, selected: Sequence[str] = ()) -> List[Path]:
    if not root.is_dir():
        return []
    allow = set(selected)
    result = []
    for path in root.iterdir():
        if not path.is_dir() or path.name.startswith("."):
            continue
        if allow and path.name not in allow:
            continue
        if not (path / "config.yaml").is_file():
            continue
        if not (path / "memories").is_dir():
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.name)


def _limits(profile: Path) -> Dict[str, int]:
    try:
        config = yaml.safe_load((profile / "config.yaml").read_text(encoding="utf-8")) or {}
        memory = config.get("memory") or {}
        values = {
            "user": int(memory.get("user_char_limit", 1375)),
            "memory": int(memory.get("memory_char_limit", 2200)),
        }
    except Exception as exc:
        raise CompactionRunError("profile_config_invalid") from exc
    if any(value <= 0 for value in values.values()):
        raise CompactionRunError("profile_limit_invalid")
    return values


def _source(profile: Path, store: str) -> Path:
    return profile / "memories" / ("USER.md" if store == "user" else "MEMORY.md")


def _usage(profile: Path, store: str, limit: int) -> Dict[str, Any]:
    path = _source(profile, store)
    raw = path.read_bytes() if path.exists() else b""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CompactionRunError("store_not_utf8") from exc
    chars = len(text)
    return {
        "path": path,
        "raw": raw,
        "chars": chars,
        "percent": round(chars * 100.0 / limit, 2),
        "sha256": _sha256_bytes(raw),
    }


def _default_state() -> Dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "last_check": None,
        "stores": {},
        "outbox": [],
        "delivered_events": {},
    }


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return _default_state()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("state_file_invalid") from exc
    if not isinstance(value, dict) or not isinstance(value.get("outbox", []), list):
        raise RuntimeError("state_file_invalid")
    base = _default_state()
    base.update(value)
    if not isinstance(base.get("stores"), dict) or not isinstance(base.get("delivered_events"), dict):
        raise RuntimeError("state_file_invalid")
    return base


def _atomic_state_write(path: Path, state: Dict[str, Any]) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".memory-capacity-", suffix=".tmp", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _success_payload(profile: str, store: str, result: Dict[str, Any], after: Dict[str, Any], limit: int) -> Dict[str, Any]:
    return {
        "embeds": [{
            "title": "Memória compactada automaticamente",
            "description": "Proteção residual de capacidade concluída com backup, validação semântica e readback.",
            "color": 0x2ECC71,
            "fields": [
                {"name": "Perfil / store", "value": f"{profile} / {store}", "inline": True},
                {"name": "Antes", "value": f"{result.get('before_chars')} / {limit} chars", "inline": True},
                {"name": "Depois", "value": f"{after['chars']} / {limit} chars ({after['percent']}%)", "inline": True},
                {"name": "Modo", "value": str(result.get("mode", "unknown")), "inline": True},
                {"name": "Readback", "value": "hash, limite, permissões e backup: PASS", "inline": False},
            ],
            "footer": {"text": "MGS · Honcho principal · USER/MEMORY residual"},
        }]
    }


def _failure_payload(profile: str, store: str, before: Dict[str, Any], limit: int, code: str, unchanged: bool) -> Dict[str, Any]:
    return {
        "embeds": [{
            "title": "Falha na compactação automática",
            "description": "A execução falhou fechada; nenhuma validação foi relaxada.",
            "color": 0xE74C3C,
            "fields": [
                {"name": "Perfil / store", "value": f"{profile} / {store}", "inline": True},
                {"name": "Uso", "value": f"{before['chars']} / {limit} chars ({before['percent']}%)", "inline": True},
                {"name": "Código", "value": code[:120], "inline": False},
                {"name": "Fonte preservada", "value": "sim" if unchanged else "não comprovado — requer investigação", "inline": False},
            ],
            "footer": {"text": "MGS · alerta sem conteúdo de memória"},
        }]
    }


def _profile_failure_payload(profile: str, code: str) -> Dict[str, Any]:
    return {
        "embeds": [{
            "title": "Falha no monitor automático de memória",
            "description": "O profile não pôde ser validado; nenhum store foi compactado.",
            "color": 0xE74C3C,
            "fields": [
                {"name": "Perfil", "value": profile, "inline": True},
                {"name": "Código", "value": code[:120], "inline": False},
                {"name": "Ação", "value": "corrigir configuração antes da próxima tentativa", "inline": False},
            ],
            "footer": {"text": "MGS · alerta sem conteúdo de memória"},
        }]
    }


def _queue_event(state: Dict[str, Any], event: Dict[str, Any], now: datetime) -> bool:
    event_id = event["event_id"]
    if any(item.get("event_id") == event_id for item in state["outbox"]):
        return False
    delivered = state["delivered_events"].get(event_id)
    if delivered:
        try:
            delivered_at = datetime.fromisoformat(str(delivered).replace("Z", "+00:00"))
        except ValueError:
            delivered_at = now
        if now - delivered_at < ALERT_COOLDOWN:
            return False
    event = dict(event)
    event.update({"created_at": _iso(now), "attempts": 0, "last_attempt_at": None})
    state["outbox"].append(event)
    return True


def _prune_delivered(state: Dict[str, Any], now: datetime) -> None:
    keep: Dict[str, str] = {}
    for key, value in state["delivered_events"].items():
        try:
            when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            continue
        if now - when < timedelta(days=7):
            keep[key] = value
    state["delivered_events"] = keep


def _default_compactor_runner(settings: Settings) -> Callable[[Path, str, float], Dict[str, Any]]:
    def run(profile: Path, store: str, target_percent: float) -> Dict[str, Any]:
        command = [
            sys.executable,
            str(settings.compactor),
            "--target-profile-root", str(profile),
            "--model-profile-root", str(profile),
            "--store", store,
            "--target-percent", str(target_percent),
            "--backup-root", str(settings.backup_root),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=settings.compactor_timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise CompactionRunError("compactor_timeout") from exc
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        try:
            data = json.loads(lines[-1]) if lines else {}
        except json.JSONDecodeError as exc:
            raise CompactionRunError("compactor_invalid_json") from exc
        if completed.returncode != 0 or data.get("success") is not True or data.get("applied") is not True:
            raise CompactionRunError(str(data.get("error_code") or f"compactor_exit_{completed.returncode}"))
        return data
    return run


def _default_poster(settings: Settings) -> Callable[[Dict[str, Any]], str]:
    def post(payload: Dict[str, Any]) -> str:
        command = [sys.executable, str(settings.poster), "--channel-id", settings.channel_id, "--timeout", "15"]
        completed = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        if completed.returncode != 0:
            raise DeliveryError("discord_delivery_failed")
        match = re.search(r"message_id=([0-9]+)", completed.stdout)
        if not match:
            raise DeliveryError("discord_readback_missing")
        return match.group(1)
    return post


def _deliver_outbox(state: Dict[str, Any], poster: Callable[[Dict[str, Any]], str], now: datetime) -> int:
    failures = 0
    remaining = []
    for event in state["outbox"]:
        event["attempts"] = int(event.get("attempts", 0)) + 1
        event["last_attempt_at"] = _iso(now)
        try:
            message_id = poster(event["payload"])
        except Exception:
            failures += 1
            remaining.append(event)
            continue
        state["delivered_events"][event["event_id"]] = _iso(now)
        state.setdefault("last_deliveries", {})[event["event_id"]] = {
            "message_id": str(message_id),
            "delivered_at": _iso(now),
            "kind": event.get("kind"),
        }
    state["outbox"] = remaining
    return failures


def run_monitor(
    settings: Settings,
    *,
    compactor_runner: Callable[[Path, str, float], Dict[str, Any]] | None = None,
    poster: Callable[[Dict[str, Any]], str] | None = None,
    now: datetime | None = None,
) -> Dict[str, Any]:
    now = now or _utc_now()
    if not (1.0 <= settings.target_percent < settings.threshold_percent <= 100.0):
        raise ValueError("invalid_threshold_configuration")
    profiles = discover_profiles(settings.profiles_root, settings.profile_filter)
    state = _load_state(settings.state_file)
    _prune_delivered(state, now)
    compact = compactor_runner or _default_compactor_runner(settings)
    send = poster or _default_poster(settings)
    summary = {
        "success": True,
        "dry_run": settings.dry_run,
        "profiles": [path.name for path in profiles],
        "stores_checked": 0,
        "threshold_count": 0,
        "compacted_count": 0,
        "failure_count": 0,
        "delivery_failures": 0,
        "outbox_pending": len(state["outbox"]),
    }

    for profile in profiles:
        try:
            limits = _limits(profile)
        except CompactionRunError as exc:
            for store in ("user", "memory"):
                key = f"{profile.name}:{store}"
                state["stores"][key] = {"status": "error", "error_code": exc.code, "checked_at": _iso(now)}
            summary["failure_count"] += 1
            event_id = _event_id("profile_failure", profile.name, exc.code)
            _queue_event(state, {
                "event_id": event_id,
                "kind": "profile_failure",
                "payload": _profile_failure_payload(profile.name, exc.code),
            }, now)
            continue
        for store in ("user", "memory"):
            summary["stores_checked"] += 1
            key = f"{profile.name}:{store}"
            limit = limits[store]
            try:
                before = _usage(profile, store, limit)
            except CompactionRunError as exc:
                state["stores"][key] = {"status": "error", "error_code": exc.code, "checked_at": _iso(now)}
                summary["failure_count"] += 1
                continue
            record = {
                "status": "healthy",
                "chars": before["chars"],
                "limit": limit,
                "percent": before["percent"],
                "sha256": before["sha256"],
                "checked_at": _iso(now),
            }
            if before["chars"] * 100 < limit * settings.threshold_percent:
                state["stores"][key] = record
                continue
            summary["threshold_count"] += 1
            if settings.dry_run:
                record["status"] = "threshold_dry_run"
                state["stores"][key] = record
                continue
            try:
                result = compact(profile, store, settings.target_percent)
                after = _usage(profile, store, limit)
                if after["chars"] >= before["chars"] or after["chars"] * 100 > limit * settings.target_percent:
                    raise CompactionRunError("post_compaction_capacity_invalid")
                if result.get("readback_matches") is not True:
                    raise CompactionRunError("post_compaction_readback_invalid")
                backup = Path(str(result.get("backup_path", "")))
                if not backup.is_file() or (backup.stat().st_mode & 0o777) != 0o600:
                    raise CompactionRunError("post_compaction_backup_invalid")
                record.update({
                    "status": "compacted",
                    "chars": after["chars"],
                    "percent": after["percent"],
                    "sha256": after["sha256"],
                    "mode": result.get("mode"),
                    "compacted_at": _iso(now),
                    "backup_path": str(backup),
                })
                state["stores"][key] = record
                summary["compacted_count"] += 1
                event_id = _event_id("success", profile.name, store, before["sha256"], after["sha256"])
                _queue_event(state, {
                    "event_id": event_id,
                    "kind": "compaction_success",
                    "payload": _success_payload(profile.name, store, result, after, limit),
                }, now)
            except CompactionRunError as exc:
                try:
                    live = _usage(profile, store, limit)
                    unchanged = live["sha256"] == before["sha256"]
                except CompactionRunError:
                    unchanged = False
                    live = before
                state["stores"][key] = {
                    **record,
                    "status": "compaction_failed",
                    "error_code": exc.code,
                    "source_unchanged": unchanged,
                    "last_failure_at": _iso(now),
                }
                summary["failure_count"] += 1
                event_id = _event_id("failure", profile.name, store, before["sha256"], exc.code)
                _queue_event(state, {
                    "event_id": event_id,
                    "kind": "compaction_failure",
                    "payload": _failure_payload(profile.name, store, live, limit, exc.code, unchanged),
                }, now)

    state["last_check"] = _iso(now)
    state["schema_version"] = STATE_SCHEMA_VERSION
    if settings.dry_run:
        summary["outbox_pending"] = len(state["outbox"])
        return summary

    _atomic_state_write(settings.state_file, state)
    if settings.no_post:
        for event in state["outbox"]:
            state["delivered_events"][event["event_id"]] = _iso(now)
        state["outbox"] = []
    else:
        summary["delivery_failures"] = _deliver_outbox(state, send, now)
    _atomic_state_write(settings.state_file, state)
    summary["outbox_pending"] = len(state["outbox"])
    summary["success"] = summary["failure_count"] == 0 and summary["delivery_failures"] == 0
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles-root", type=Path, default=DEFAULT_PROFILES_ROOT)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--compactor", type=Path, default=DEFAULT_COMPACTOR)
    parser.add_argument("--poster", type=Path, default=DEFAULT_POSTER)
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    parser.add_argument("--channel-id", default=DEFAULT_CHANNEL_ID)
    parser.add_argument("--threshold-percent", type=float, default=DEFAULT_THRESHOLD_PERCENT)
    parser.add_argument("--target-percent", type=float, default=DEFAULT_TARGET_PERCENT)
    parser.add_argument("--compactor-timeout", type=int, default=DEFAULT_COMPACTOR_TIMEOUT)
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-post", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    settings = Settings(
        profiles_root=args.profiles_root,
        state_file=args.state_file,
        compactor=args.compactor,
        poster=args.poster,
        backup_root=args.backup_root,
        threshold_percent=args.threshold_percent,
        target_percent=args.target_percent,
        channel_id=args.channel_id,
        profile_filter=args.profile,
        dry_run=args.dry_run,
        no_post=args.no_post,
        compactor_timeout=args.compactor_timeout,
    )
    lock_path = settings.state_file.with_suffix(settings.state_file.suffix + ".lock")
    if not lock_path.parent.exists():
        lock_path.parent.mkdir(parents=True, mode=0o700)
    with open(lock_path, "a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"success": True, "skipped": "lock_busy"}, separators=(",", ":")))
            return 0
        try:
            result = run_monitor(settings)
        except Exception as exc:
            result = {"success": False, "error_code": type(exc).__name__}
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
