#!/usr/bin/env python3
"""Pause Eggbev campaigns after DTR #2022 restriction alerts.

The source of confirmed events is the canonical DTR -> Smart Bidding sync state.
The runner never parses Discord messages. It only acts when the DTR monitor has
recorded a new restriction and the same page is currently restricted in the
Smart Bidding transition state. Matching to Meta is exact by UTM_CAMPAIGN and
creative page_id. Writes are campaign PAUSED only, one POST followed by GET.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path("/root/mgs-agent")
OP_PATH = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
ACCOUNT_PATH = BASE / "data/ares/meta-ads/accounts/1034081997659047.json"
DTR_STATE_PATH = BASE / "data/dtr-sb-page-health-sync-state.json"
SB_TRANSITION_STATE_PATH = BASE / "data/sb-restricted-transition-state.json"
STATE_PATH = BASE / "data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/page-restriction-guardrail.json"
LOCK_PATH = BASE / "data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/page-restriction-guardrail.lock"
AUDIT_DIR = BASE / "data/ares/meta-ads/audit/guardrails/Eggbev-US-CC-EN-BOT/page-restrictions"
LEAD_GUARDRAIL_PATH = BASE / "scripts/ares-eggbev-page-lead-guardrail.py"
META_COMMON_PATH = BASE / "scripts/ares-meta-common.py"
DISCORD_POSTER = BASE / "scripts/ares-discord-post-with-thread.py"
NY = ZoneInfo("America/New_York")


class RestrictionGuardrailError(RuntimeError):
    pass


def now_et() -> dt.datetime:
    return dt.datetime.now(NY)


def norm(value: Any) -> str:
    return str(value or "").strip()


def normalize_utm(value: Any) -> str | None:
    match = re.fullmatch(r"pg[_-]?(\d+)", norm(value).lower())
    return f"pg_{match.group(1)}" if match else None


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RestrictionGuardrailError(f"invalid JSON object: {path.name}")
    return data


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def open_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, "r+")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RestrictionGuardrailError(f"cannot load module {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_iso(value: Any) -> dt.datetime | None:
    raw = norm(value)
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(NY)


def page_id_from_key(key: str) -> str:
    return norm(key.rsplit("|", 1)[-1])


def event_id(key: str, row: dict[str, Any]) -> str:
    material = "|".join([
        norm(row.get("bot_user")),
        page_id_from_key(key),
        norm(row.get("restricted_until")),
        norm(row.get("last_seen")),
    ])
    return hashlib.sha256(material.encode()).hexdigest()[:24]


def transition_index(state: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for key, row in (state.get("active") or {}).items():
        if not isinstance(row, dict):
            continue
        bot_user = norm(row.get("bot_user")).lower()
        page_id = norm(row.get("page_id")) or page_id_from_key(str(key))
        if bot_user and page_id:
            index[(bot_user, page_id)] = row
    return index


def is_eggbev_scope(row: dict[str, Any], transition: dict[str, Any]) -> bool:
    values = " ".join([
        norm(row.get("bot_user")),
        norm(row.get("sites")),
        norm(transition.get("bot_user")),
        norm(transition.get("sites")),
    ]).lower()
    return "eggbev" in values


def collect_confirmed_events(
    dtr_state: dict[str, Any],
    transition_state: dict[str, Any],
    state: dict[str, Any],
    run_at: dt.datetime,
) -> list[dict[str, Any]]:
    cursor = parse_iso(state.get("cursor_last_seen_at"))
    cursor_ids = set(state.get("cursor_event_ids") or [])
    transitions = transition_index(transition_state)
    events: list[dict[str, Any]] = []
    for key, row in (dtr_state.get("alerted_restricted_pages") or {}).items():
        if not isinstance(row, dict):
            continue
        seen = parse_iso(row.get("last_seen"))
        if seen is None:
            continue
        eid = event_id(str(key), row)
        if cursor is not None and (seen < cursor or (seen == cursor and eid in cursor_ids)):
            continue
        page_id = page_id_from_key(str(key))
        bot_user = norm(row.get("bot_user")).lower()
        transition = transitions.get((bot_user, page_id)) or {}
        if not transition or not is_eggbev_scope(row, transition):
            continue
        restricted_until = norm(transition.get("restricted_until") or row.get("restricted_until"))[:10]
        try:
            restriction_date = dt.date.fromisoformat(restricted_until)
        except ValueError:
            continue
        if restriction_date < run_at.astimezone(NY).date():
            continue
        utm = normalize_utm(transition.get("utm_campaign") or transition.get("utm") or f"pg_{page_id}")
        fb_page_id = norm(transition.get("fb_page_id") or row.get("fb_page_id"))
        if not utm or not fb_page_id:
            continue
        events.append({
            "event_id": eid,
            "source_key": str(key),
            "source_seen_at": seen.isoformat(),
            "bot_user": bot_user,
            "page_id": page_id,
            "page_name": transition.get("page_name") or row.get("page_name"),
            "profile_name": transition.get("profile_name") or row.get("segurador"),
            "utm_campaign": utm,
            "fb_page_id": fb_page_id,
            "restricted_until": restricted_until,
            "source": "DTR #2022 + Smart Bidding readback",
        })
    return sorted(events, key=lambda row: (row["source_seen_at"], row["event_id"]))


def advance_cursor(state: dict[str, Any], dtr_state: dict[str, Any]) -> None:
    candidates: list[tuple[dt.datetime, str]] = []
    for key, row in (dtr_state.get("alerted_restricted_pages") or {}).items():
        if not isinstance(row, dict):
            continue
        seen = parse_iso(row.get("last_seen"))
        if seen is not None:
            candidates.append((seen, event_id(str(key), row)))
    if not candidates:
        return
    latest = max(seen for seen, _ in candidates)
    state["cursor_last_seen_at"] = latest.isoformat()
    state["cursor_event_ids"] = sorted(eid for seen, eid in candidates if seen == latest)


def exact_meta_matches(
    event: dict[str, Any],
    campaigns: list[dict[str, Any]],
    ads: list[dict[str, Any]],
    lead_module,
) -> dict[str, Any]:
    ads_by_campaign: dict[str, list[dict[str, Any]]] = {}
    for ad in ads:
        campaign_id = norm((ad.get("campaign") or {}).get("id"))
        if campaign_id:
            ads_by_campaign.setdefault(campaign_id, []).append(ad)
    exact: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for campaign in campaigns:
        campaign_id = norm(campaign.get("id"))
        campaign_ads = ads_by_campaign.get(campaign_id, [])
        if not campaign_ads:
            continue
        evidence = lead_module.campaign_page_evidence(campaign, campaign_ads)
        candidate = {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name"),
            "campaign_status": campaign.get("status"),
            "campaign_effective_status": campaign.get("effective_status"),
            **evidence,
        }
        if evidence.get("issues"):
            issues.append(candidate)
            continue
        same_utm = evidence.get("utm_campaign") == event.get("utm_campaign")
        same_page = evidence.get("meta_page_id") == event.get("fb_page_id")
        if same_utm and same_page:
            exact.append(candidate)
        elif same_utm or same_page:
            partial.append(candidate)
    return {"exact": exact, "partial": partial, "issues": issues}


def fmt_date(value: Any) -> str:
    raw = norm(value)[:10]
    try:
        parsed = dt.date.fromisoformat(raw)
    except ValueError:
        return raw or "N/D"
    return parsed.strftime("%d/%m")


def build_action_alert(
    event: dict[str, Any],
    actions: list[dict[str, Any]],
    run_at: dt.datetime,
    *,
    partial_matches: int = 0,
) -> str:
    confirmed = sum(1 for row in actions if row.get("ok"))
    failed = len(actions) - confirmed
    if failed or partial_matches:
        icon, title = "⚠️", "PÁGINA RESTRITA — PENDÊNCIA"
    elif actions:
        icon, title = "⛔", "PÁGINA RESTRITA — CAMPANHAS PAUSADAS"
    else:
        icon, title = "🟡", "PÁGINA RESTRITA — SEM CAMPANHA ATIVA"
    lines = [
        f"{icon} **{title}**",
        f"**{event.get('page_name') or 'N/D'}** · `{event.get('utm_campaign')}` · até `{fmt_date(event.get('restricted_until'))}`",
        f"Campanhas ativas: **{len(actions)}** · pausadas: **{confirmed}**" + (f" · pendentes: **{failed + partial_matches}**" if failed or partial_matches else " ✅"),
        f"Fonte: `DTR #2022 + SB` · `{run_at.strftime('%H:%M ET')}` · reativação automática: **não**",
    ]
    return "\n".join(lines)


def build_runtime_alert(event: dict[str, Any], run_at: dt.datetime, reason: str) -> str:
    return "\n".join([
        "⚠️ **PÁGINA RESTRITA — AÇÃO BLOQUEADA**",
        f"**{event.get('page_name') or 'N/D'}** · `{event.get('utm_campaign')}`",
        "Campanhas pausadas: **0** · ação: **fail-closed**",
        f"Motivo: `{reason}` · `{run_at.strftime('%H:%M ET')}`",
    ])


def build_test_alert(run_at: dt.datetime) -> str:
    return "\n".join([
        "🧪 **TESTE — PÁGINA E LIMITES**",
        "🟡 Página de teste · `pg_teste`",
        "Campanhas ativas: **0** · ação Meta: **nenhuma**",
        f"Objetivo: validar alerta curto · `{run_at.strftime('%H:%M ET')}`",
    ])


def post_to_thread(thread_id: str, message: str) -> dict[str, Any]:
    process = subprocess.run(
        [
            sys.executable,
            str(DISCORD_POSTER),
            "--thread-id",
            thread_id,
            "--fallback-title",
            "Página e Limites",
            "--verify-readback",
        ],
        input=message,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    payload: dict[str, Any] = {}
    if process.stdout.strip():
        try:
            parsed = json.loads(process.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            pass
    return {
        "ok": process.returncode == 0,
        "returncode": process.returncode,
        "message_ids": payload.get("message_ids") or [],
        "readbacks_confirmed": payload.get("readbacks_confirmed", 0),
        "chunks": payload.get("chunks", 0),
        "stderr": process.stderr[-1000:] if process.returncode else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="pause exact matched active campaigns")
    parser.add_argument("--post-alerts", action="store_true", help="post short alerts to the fixed route")
    parser.add_argument("--initialize", action="store_true", help="baseline existing events without replay")
    parser.add_argument("--test-alert", action="store_true", help="post a no-write synthetic layout test")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    with open_lock() as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        run_at = now_et()
        operation = load_json(OP_PATH)
        account_file = load_json(ACCOUNT_PATH)
        account = (account_file.get("accounts") or [{}])[0]
        policy = operation.get("page_restriction_guardrail") or {}
        discord = policy.get("discord") or {}
        thread_id = norm(discord.get("thread_id") or (((operation.get("discord") or {}).get("fixed_threads") or {}).get("page_lead_guardrail")))
        fallback_thread_id = norm((((operation.get("discord") or {}).get("fixed_threads") or {}).get("rules")))
        state: dict[str, Any] = load_json(STATE_PATH) if STATE_PATH.exists() else {"version": 1}
        run_id = run_at.strftime("%Y%m%dT%H%M%S%z")
        audit_path = AUDIT_DIR / f"run-{run_id}.json"
        run: dict[str, Any] = {
            "run_id": run_id,
            "started_at_et": run_at.isoformat(),
            "mode": "controlled_write" if args.apply else "read_only",
            "events": [],
            "writes": [],
            "deliveries": [],
            "ok": False,
        }
        atomic_json(audit_path, run)

        if args.test_alert:
            if not args.post_alerts or not thread_id:
                raise SystemExit("--test-alert requires --post-alerts and a fixed thread")
            delivery = post_to_thread(thread_id, build_test_alert(run_at))
            run.update({"ok": bool(delivery.get("ok")), "test_alert": True, "deliveries": [delivery], "finished_at_et": now_et().isoformat()})
            atomic_json(audit_path, run)
            print(json.dumps({"ok": run["ok"], "test_alert": True, "delivery": delivery, "audit_path": str(audit_path)}, ensure_ascii=False))
            return 0 if run["ok"] else 2

        dtr_state = load_json(DTR_STATE_PATH)
        transition_state = load_json(SB_TRANSITION_STATE_PATH)
        if args.initialize or not state.get("initialized_at_et"):
            advance_cursor(state, dtr_state)
            state.update({
                "initialized_at_et": run_at.isoformat(),
                "last_run_at_et": run_at.isoformat(),
                "last_ok": True,
                "source": str(DTR_STATE_PATH),
                "meta_writes": 0,
            })
            atomic_json(STATE_PATH, state)
            run.update({"ok": True, "initialized": True, "events_seen": 0, "finished_at_et": now_et().isoformat()})
            atomic_json(audit_path, run)
            if not args.quiet:
                print(json.dumps({"ok": True, "initialized": True, "audit_path": str(audit_path)}, ensure_ascii=False))
            return 0

        events = collect_confirmed_events(dtr_state, transition_state, state, run_at)
        if args.apply and (not policy.get("policy_approved") or not (policy.get("runtime") or {}).get("write_enabled")):
            raise RestrictionGuardrailError("page restriction controlled-write is not enabled")
        if args.apply and not args.post_alerts:
            raise RestrictionGuardrailError("controlled-write requires --post-alerts")
        if events and not thread_id:
            raise RestrictionGuardrailError("missing fixed Discord thread ID")

        meta_common: Any = None
        lead_module: Any = None
        token: Any = None
        campaigns: list[dict[str, Any]] = []
        ads: list[dict[str, Any]] = []
        account_id = norm((operation.get("account") or {}).get("account_id"))
        if events:
            os.environ.setdefault("ARES_META_TOKEN_CACHE_PATH", "/root/.cache/mgs/ares-meta-token-eggbev-us-cc-en-01-g006.json")
            lead_module = load_module("ares_eggbev_lead_guardrail_for_restrictions", LEAD_GUARDRAIL_PATH)
            meta_common = load_module("ares_meta_common_eggbev_restrictions", META_COMMON_PATH)
            token, token_field = meta_common.get_token_from_1password(account.get("token_1password_item"))
            run["credential_readback"] = {"item": account.get("token_1password_item"), "field": token_field, "token_len": len(token)}
            status, live_account, _ = meta_common.graph_get("act_" + account_id, token, {"fields": "id,name,account_status,currency,timezone_name,disable_reason"})
            if status != 200 or not isinstance(live_account, dict):
                raise RestrictionGuardrailError(f"Meta account preflight failed: HTTP {status}")
            if live_account.get("currency") != "USD" or live_account.get("timezone_name") != "America/New_York" or int(live_account.get("account_status") or 0) != 1:
                raise RestrictionGuardrailError("Meta account identity/currency/timezone/status preflight failed")
            campaigns = lead_module.fetch_all_meta(meta_common, token, "act_" + account_id + "/campaigns", {
                "fields": "id,name,status,effective_status,configured_status,daily_budget,updated_time",
                "effective_status": ["ACTIVE"],
                "limit": 200,
            })
            ads = lead_module.fetch_all_meta(meta_common, token, "act_" + account_id + "/ads", {
                "fields": "id,name,status,effective_status,configured_status,campaign{id,name,status,effective_status},creative{id,name,object_story_spec,url_tags,effective_object_story_id}",
                "effective_status": ["ACTIVE"],
                "limit": 200,
            })
            run["meta_readback"] = {"active_campaigns": len(campaigns), "active_ads": len(ads)}

        overall_ok = True
        for event in events:
            match = exact_meta_matches(event, campaigns, ads, lead_module)
            actions: list[dict[str, Any]] = []
            try:
                if match["partial"]:
                    overall_ok = False
                    raise RestrictionGuardrailError("partial_page_or_utm_match")
                if args.apply:
                    for campaign in match["exact"]:
                        action = lead_module.reconcile_pause(meta_common, token, campaign)
                        actions.append(action)
                        run["writes"].append(action)
                        atomic_json(audit_path, run)
                if args.post_alerts:
                    delivery = post_to_thread(thread_id, build_action_alert(event, actions if args.apply else match["exact"], run_at, partial_matches=len(match["partial"])))
                    run["deliveries"].append(delivery)
                    if not delivery.get("ok"):
                        overall_ok = False
                        raise RestrictionGuardrailError("primary_alert_delivery_failed")
                event_result = {**event, "exact_campaigns": len(match["exact"]), "partial_matches": len(match["partial"]), "actions": actions, "ok": all(row.get("ok") for row in actions)}
                if actions and not event_result["ok"]:
                    overall_ok = False
                run["events"].append(event_result)
            except Exception as exc:
                overall_ok = False
                error_delivery = None
                if args.post_alerts:
                    error_delivery = post_to_thread(thread_id, build_runtime_alert(event, run_at, str(exc)))
                    if not error_delivery.get("ok") and fallback_thread_id:
                        error_delivery = post_to_thread(fallback_thread_id, build_runtime_alert(event, run_at, str(exc)))
                    run["deliveries"].append(error_delivery)
                run["events"].append({**event, "ok": False, "error": str(exc), "delivery": error_delivery})
            atomic_json(audit_path, run)

        advance_cursor(state, dtr_state)
        state.update({
            "last_run_at_et": now_et().isoformat(),
            "last_ok": overall_ok,
            "last_events_seen": len(events),
            "last_meta_writes": len(run["writes"]),
            "last_audit_path": str(audit_path),
        })
        atomic_json(STATE_PATH, state)
        run.update({"ok": overall_ok, "events_seen": len(events), "finished_at_et": now_et().isoformat()})
        atomic_json(audit_path, run)
        if not args.quiet or events:
            print(json.dumps({
                "ok": overall_ok,
                "events_seen": len(events),
                "campaigns_paused_confirmed": sum(1 for row in run["writes"] if row.get("ok")),
                "alerts_delivered": sum(1 for row in run["deliveries"] if row and row.get("ok")),
                "audit_path": str(audit_path),
            }, ensure_ascii=False))
        return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
