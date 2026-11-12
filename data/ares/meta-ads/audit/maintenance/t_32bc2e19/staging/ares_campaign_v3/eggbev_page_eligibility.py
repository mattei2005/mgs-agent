from __future__ import annotations

import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

OPERATION = "Eggbev-US-CC-EN-BOT"
DEFAULT_DENYLIST_PATH = Path(
    "/root/mgs-agent/data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/restricted-page-denylist.json"
)
ET = dt.timezone(dt.timedelta(hours=-4))
PAGE_TOKEN_RE = re.compile(r"\bpg_(\d+)\b", re.IGNORECASE)


class PageEligibilityError(RuntimeError):
    pass


def _norm(value: Any) -> str:
    return str(value or "").strip()


def normalize_page_token(value: Any) -> str:
    match = PAGE_TOKEN_RE.search(_norm(value))
    if not match:
        raise PageEligibilityError("page token pg_XXXXX ausente ou inválido")
    return f"pg_{match.group(1)}"


def page_token_from_campaign_name(name: Any) -> str:
    return normalize_page_token(name)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def load_denylist(path: Path = DEFAULT_DENYLIST_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise PageEligibilityError("denylist canônica de páginas restritas indisponível") from exc
    if payload.get("operation_id") != OPERATION or payload.get("policy") != "ever_restricted_page_is_permanently_ineligible":
        raise PageEligibilityError("denylist canônica de páginas restritas inválida")
    pages = payload.get("pages")
    if not isinstance(pages, dict):
        raise PageEligibilityError("denylist canônica sem mapa de páginas")
    return payload


def page_eligibility(
    page_token: Any,
    *,
    meta_page_id: Any = None,
    denylist: dict[str, Any] | None = None,
    path: Path = DEFAULT_DENYLIST_PATH,
) -> dict[str, Any]:
    token = normalize_page_token(page_token)
    payload = denylist if denylist is not None else load_denylist(path)
    row = (payload.get("pages") or {}).get(token)
    if not isinstance(row, dict):
        return {
            "eligible": True,
            "page_token": token,
            "reason": "no_restriction_history_in_canonical_denylist",
            "source_updated_at": payload.get("updated_at"),
        }
    expected_meta_page_id = _norm(meta_page_id)
    recorded_meta_page_id = _norm(row.get("fb_page_id"))
    identity_match = not expected_meta_page_id or not recorded_meta_page_id or expected_meta_page_id == recorded_meta_page_id
    return {
        "eligible": False,
        "page_token": token,
        "page_name": row.get("page_name"),
        "fb_page_id": recorded_meta_page_id or None,
        "reason": "restricted_page_history" if identity_match else "restricted_page_identity_mismatch_fail_closed",
        "currently_restricted": bool(row.get("currently_restricted")),
        "current_restricted_until": row.get("current_restricted_until"),
        "first_restriction_seen_at": row.get("first_restriction_seen_at"),
        "last_restriction_seen_at": row.get("last_restriction_seen_at"),
        "source_updated_at": payload.get("updated_at"),
    }


def require_page_eligible(
    page_token: Any,
    *,
    meta_page_id: Any = None,
    denylist: dict[str, Any] | None = None,
    path: Path = DEFAULT_DENYLIST_PATH,
) -> dict[str, Any]:
    result = page_eligibility(page_token, meta_page_id=meta_page_id, denylist=denylist, path=path)
    if not result["eligible"]:
        deadline = result.get("current_restricted_until") or "histórico permanente"
        name = result.get("page_name") or result["page_token"]
        raise PageEligibilityError(
            f"página {name} ({result['page_token']}) inelegível por histórico de restrição; "
            f"restrição atual/última: {deadline}; solicite outra página"
        )
    return result


def _eggbev_scope(row: dict[str, Any]) -> bool:
    sites = _norm(row.get("sites")).lower()
    bot_user = _norm(row.get("bot_user")).lower()
    return "eggbev" in sites or "eggbev" in bot_user


def _merge_page(target: dict[str, dict[str, Any]], row: dict[str, Any], *, active: bool) -> None:
    if not _eggbev_scope(row):
        return
    raw_page_id = _norm(row.get("page_id"))
    raw_token = _norm(row.get("utm_campaign")) or (f"pg_{raw_page_id}" if raw_page_id.isdigit() else "")
    try:
        token = normalize_page_token(raw_token)
    except PageEligibilityError:
        return
    has_history = bool(
        active
        or row.get("currently_restricted")
        or row.get("last_entry_at")
        or row.get("last_known_restricted_until")
        or row.get("restricted_until")
    )
    if not has_history:
        return
    current = target.setdefault(token, {"page_token": token})
    for key in ("page_id", "page_name", "fb_page_id", "profile_name", "sites"):
        if row.get(key) not in (None, ""):
            current[key] = row.get(key)
    entry_at = _norm(row.get("last_entry_at"))
    if entry_at:
        previous = _norm(current.get("first_restriction_seen_at"))
        current["first_restriction_seen_at"] = min(filter(None, [previous, entry_at])) if previous else entry_at
        current["last_restriction_seen_at"] = max(_norm(current.get("last_restriction_seen_at")), entry_at)
    current_until = _norm(row.get("current_restricted_until") or row.get("restricted_until"))
    current["currently_restricted"] = bool(active or row.get("currently_restricted"))
    if current_until:
        current["current_restricted_until"] = current_until
    elif not current.get("currently_restricted"):
        current["current_restricted_until"] = ""
    last_known = _norm(row.get("last_known_restricted_until") or row.get("restricted_until"))
    if last_known:
        current["last_known_restricted_until"] = max(_norm(current.get("last_known_restricted_until")), last_known)
    current["eligibility"] = "INELIGIBLE_PERMANENT_RESTRICTION_HISTORY"


def build_denylist(
    transition_state: dict[str, Any],
    previous: dict[str, Any] | None = None,
    *,
    authorized_at_et: str = "2026-08-31T20:00:00-04:00",
) -> dict[str, Any]:
    pages: dict[str, dict[str, Any]] = {}
    if isinstance(previous, dict):
        for key, value in (previous.get("pages") or {}).items():
            if isinstance(value, dict):
                pages[str(key)] = dict(value)
    history = ((transition_state.get("history") or {}).get("pages") or {})
    for row in history.values():
        if isinstance(row, dict):
            _merge_page(pages, row, active=bool(row.get("currently_restricted")))
    for row in (transition_state.get("active") or {}).values():
        if isinstance(row, dict):
            _merge_page(pages, row, active=True)
    updated_at = _norm(transition_state.get("last_check")) or dt.datetime.now(ET).isoformat()
    return {
        "version": 1,
        "operation_id": OPERATION,
        "policy": "ever_restricted_page_is_permanently_ineligible",
        "authorized_by": "Nicolas Holanda",
        "authorized_by_discord_id": "1055570806945620030",
        "authorized_at_et": authorized_at_et,
        "source": "/root/mgs-agent/data/sb-restricted-transition-state.json history.pages + active",
        "updated_at": updated_at,
        "page_count": len(pages),
        "pages": {key: pages[key] for key in sorted(pages, key=lambda value: int(value.split("_", 1)[1]))},
    }


def sync_denylist(
    transition_state: dict[str, Any],
    *,
    path: Path = DEFAULT_DENYLIST_PATH,
) -> dict[str, Any]:
    previous: dict[str, Any] | None = None
    if path.exists():
        try:
            previous = json.loads(path.read_text())
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            previous = None
    payload = build_denylist(transition_state, previous)
    _atomic_json(path, payload)
    readback = load_denylist(path)
    if readback.get("page_count") != len(readback.get("pages") or {}):
        raise PageEligibilityError("readback da denylist canônica não fechou")
    return readback
