#!/usr/bin/env python3
"""Eggbev BOT page-lead guardrail.

Scans every effectively active campaign in one allowlisted Meta account, maps it
to a live Smart Bidding Messenger page by exact UTM_CAMPAIGN plus FB_PAGE_ID,
and pauses the whole campaign when LEADS is strictly greater than the approved
limit. Default mode is dry-run. Controlled writes require the scoped runtime
gate and an existing fixed Discord thread ID.

Never prints credentials. Every write is followed by a GET readback. A failed
POST is reconciled by GET and is never retried blindly.
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
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path("/root/mgs-agent")
OP_PATH = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
ACCOUNT_PATH = BASE / "data/ares/meta-ads/accounts/1034081997659047.json"
META_COMMON_PATH = BASE / "scripts/ares-meta-common.py"
SB_COMMON_PATH = BASE / "scripts/ares-smartbidding-common.py"
DISCORD_POSTER = BASE / "scripts/ares-discord-post-with-thread.py"
AUDIT_DIR = BASE / "data/ares/meta-ads/audit/guardrails/Eggbev-US-CC-EN-BOT/page-leads"
STATE_PATH = BASE / "data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/page-lead-guardrail.json"
LOCK_PATH = BASE / "data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/page-lead-guardrail.lock"
NY = ZoneInfo("America/New_York")
UTM_RE = re.compile(r"\(\s*pg[_-]?(\d+)\s*\)", re.I)
ACTION_MESSAGING = (
    "onsite_conversion.messaging_conversation_started_7d",
    "onsite_conversion.messaging_first_reply",
    "messaging_conversation_started",
)
ACTION_PURCHASE = ("omni_purchase", "purchase")


class GuardrailError(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GuardrailError(f"cannot load module {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def now_et() -> dt.datetime:
    return dt.datetime.now(NY)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
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


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise GuardrailError(f"invalid JSON object: {path.name}")
    return data


def open_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, "r+")


def norm(value: Any) -> str:
    return str(value or "").strip()


def normalize_utm(value: Any) -> str | None:
    raw = norm(value).lower()
    match = re.fullmatch(r"pg[_-]?(\d+)", raw)
    return f"pg_{match.group(1)}" if match else None


def utm_from_campaign_name(name: str) -> str | None:
    match = UTM_RE.search(norm(name))
    return f"pg_{match.group(1)}" if match else None


def utm_from_url_tags(tags: Any) -> set[str]:
    raw = norm(tags)
    if not raw:
        return set()
    parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
    values = parsed.get("utm_campaign") or parsed.get("UTM_CAMPAIGN") or []
    return {value for item in values if (value := normalize_utm(item))}


def finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def strict_over(value: Any, limit: float) -> bool:
    number = finite_float(value)
    return bool(number is not None and number > limit)


def active_restriction(row: dict[str, Any], local_date: dt.date) -> dict[str, Any]:
    raw = norm(row.get("RESTRICTED_UNTIL"))[:10]
    if not raw:
        return {"active": False, "restricted_until": None, "basis": "smart_bidding_restricted_until_empty"}
    try:
        date_value = dt.date.fromisoformat(raw)
    except ValueError:
        return {"active": None, "restricted_until": raw, "basis": "smart_bidding_restricted_until_invalid"}
    return {
        "active": date_value >= local_date,
        "restricted_until": raw,
        "basis": "smart_bidding_restricted_until",
    }


def action_value(rows: Any, preferred: tuple[str, ...]) -> float | None:
    if not isinstance(rows, list):
        return None
    by_type: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        number = finite_float(row.get("value"))
        if number is not None:
            by_type[norm(row.get("action_type"))] = number
    for key in preferred:
        if key in by_type:
            return by_type[key]
    for key, value in by_type.items():
        if any(fragment in key for fragment in preferred):
            return value
    return None


def money_minor_to_usd(value: Any) -> float | None:
    number = finite_float(value)
    return None if number is None else number / 100.0


def fetch_all_meta(common, token: str, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    after: str | None = None
    for _ in range(100):
        request_params = dict(params)
        if after:
            request_params["after"] = after
        status, body, _ = common.graph_get(path, token, request_params)
        if status != 200 or not isinstance(body, dict):
            raise GuardrailError(f"Meta read failed for {path}: HTTP {status}")
        rows.extend(row for row in body.get("data") or [] if isinstance(row, dict))
        paging = body.get("paging") or {}
        cursor = (paging.get("cursors") or {}).get("after")
        if not paging.get("next") or not cursor or cursor == after:
            break
        after = str(cursor)
    else:
        raise GuardrailError(f"Meta pagination exceeded safety limit for {path}")
    return rows


def fetch_sb_pages(sb_common, publisher_name: str, credential_item: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    status, companies, token_report = sb_common.api_request("GET", "/company", item_name=credential_item)
    if status != 200 or not isinstance(companies, list):
        raise GuardrailError(f"Smart Bidding /company failed: HTTP {status}")
    publishers: list[str] = []
    for company in companies:
        if not isinstance(company, dict):
            continue
        for publisher in company.get("publishers") or []:
            if norm(publisher.get("name")).lower() != publisher_name.lower() or not publisher.get("active", True):
                continue
            publisher_id = norm(publisher.get("publisherId"))
            if publisher_id and "_" not in publisher_id:
                publisher_id = f"{company.get('companyId')}_{publisher_id}"
            if publisher_id:
                publishers.append(publisher_id)
    publishers = sorted(set(publishers))
    if not publishers:
        raise GuardrailError("approved Smart Bidding publisher was not found")
    query = "&".join("companies[]=" + urllib.parse.quote(value) for value in publishers) + "&source=Messenger"
    status, rows, token_report = sb_common.api_request(
        "GET", "/campaigns/Messenger?" + query, item_name=credential_item
    )
    if status != 200 or not isinstance(rows, list):
        raise GuardrailError(f"Smart Bidding Messenger pages failed: HTTP {status}")
    clean_rows = [row for row in rows if isinstance(row, dict)]
    return clean_rows, {
        "publisher_name": publisher_name,
        "publisher_count": len(publishers),
        "row_count": len(clean_rows),
        "token_report": {
            "credential_item": token_report.get("credential_item"),
            "token_len": token_report.get("token_len"),
        },
    }


def index_sb_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        utm = normalize_utm(row.get("UTM_CAMPAIGN"))
        if utm:
            grouped[utm].append(row)
    duplicates = {key: len(value) for key, value in grouped.items() if len(value) != 1}
    unique = {key: value[0] for key, value in grouped.items() if len(value) == 1}
    return unique, duplicates


def campaign_page_evidence(campaign: dict[str, Any], ads: list[dict[str, Any]]) -> dict[str, Any]:
    name_utm = utm_from_campaign_name(norm(campaign.get("name")))
    tag_utms: set[str] = set()
    page_ids: set[str] = set()
    for ad in ads:
        creative = ad.get("creative") or {}
        tag_utms |= utm_from_url_tags(creative.get("url_tags"))
        object_story_spec = creative.get("object_story_spec") or {}
        page_id = norm(object_story_spec.get("page_id"))
        if page_id:
            page_ids.add(page_id)
    issues: list[str] = []
    if not name_utm:
        issues.append("campaign_name_missing_pg_utm")
    if len(tag_utms) > 1:
        issues.append("multiple_creative_utm_campaign_values")
    if tag_utms and name_utm and tag_utms != {name_utm}:
        issues.append("campaign_name_and_creative_utm_mismatch")
    if len(page_ids) != 1:
        issues.append("meta_page_id_missing_or_ambiguous")
    return {
        "utm_campaign": name_utm,
        "creative_utm_campaigns": sorted(tag_utms),
        "meta_page_id": next(iter(page_ids)) if len(page_ids) == 1 else None,
        "active_ad_count": len(ads),
        "issues": issues,
    }


def evaluate_campaigns(
    campaigns: list[dict[str, Any]],
    ads: list[dict[str, Any]],
    sb_rows: list[dict[str, Any]],
    lead_limit: float,
    local_date: dt.date,
) -> dict[str, Any]:
    ads_by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ad in ads:
        campaign_id = norm((ad.get("campaign") or {}).get("id"))
        if campaign_id:
            ads_by_campaign[campaign_id].append(ad)
    sb_index, sb_duplicates = index_sb_rows(sb_rows)
    eligible: list[dict[str, Any]] = []
    safe: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for campaign in campaigns:
        campaign_id = norm(campaign.get("id"))
        campaign_ads = ads_by_campaign.get(campaign_id, [])
        if not campaign_ads:
            safe.append({"campaign_id": campaign_id, "campaign_name": campaign.get("name"), "reason": "no_effectively_active_ads"})
            continue
        evidence = campaign_page_evidence(campaign, campaign_ads)
        if evidence["issues"]:
            issues.append({"campaign_id": campaign_id, "campaign_name": campaign.get("name"), **evidence})
            continue
        utm = evidence["utm_campaign"]
        if utm in sb_duplicates:
            issues.append({"campaign_id": campaign_id, "campaign_name": campaign.get("name"), **evidence, "issue": "duplicate_smart_bidding_utm", "matches": sb_duplicates[utm]})
            continue
        sb_row = sb_index.get(utm)
        if not sb_row:
            issues.append({"campaign_id": campaign_id, "campaign_name": campaign.get("name"), **evidence, "issue": "smart_bidding_utm_not_found"})
            continue
        sb_page_id = norm(sb_row.get("FB_PAGE_ID"))
        if not sb_page_id or sb_page_id != evidence["meta_page_id"]:
            issues.append({
                "campaign_id": campaign_id,
                "campaign_name": campaign.get("name"),
                **evidence,
                "issue": "meta_and_smart_bidding_page_id_mismatch",
                "smart_bidding_page_id_present": bool(sb_page_id),
            })
            continue
        leads = finite_float(sb_row.get("LEADS"))
        base = {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name"),
            "campaign_status": campaign.get("status"),
            "campaign_effective_status": campaign.get("effective_status"),
            "daily_budget_usd": money_minor_to_usd(campaign.get("daily_budget")),
            **evidence,
            "page_name": sb_row.get("PAGE_NAME"),
            "smart_bidding_page_id": sb_page_id,
            "leads": leads,
            "leads_total": finite_float(sb_row.get("LEADS_TOTAL")),
            "smart_bidding_status": sb_row.get("STATUS"),
            "restriction": active_restriction(sb_row, local_date),
        }
        if leads is None:
            issues.append({**base, "issue": "smart_bidding_leads_not_numeric"})
        elif strict_over(leads, lead_limit):
            eligible.append(base)
        else:
            safe.append({**base, "reason": "leads_not_strictly_over_limit"})
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        grouped[str(row["utm_campaign"])].append(row)
    return {
        "eligible_groups": [
            {"utm_campaign": key, "page_name": rows[0].get("page_name"), "leads": rows[0].get("leads"), "leads_total": rows[0].get("leads_total"), "restriction": rows[0].get("restriction"), "smart_bidding_status": rows[0].get("smart_bidding_status"), "campaigns": rows}
            for key, rows in sorted(grouped.items())
        ],
        "issues": issues,
        "safe": safe,
        "sb_utm_duplicates": sb_duplicates,
    }


def fetch_today_insights(common, token: str, campaign_ids: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for start in range(0, len(campaign_ids), 50):
        batch = []
        for campaign_id in campaign_ids[start:start + 50]:
            batch.append({
                "name": campaign_id,
                "path": f"{campaign_id}/insights",
                "params": {
                    "date_preset": "today",
                    "level": "campaign",
                    "fields": "campaign_id,campaign_name,spend,impressions,cpm,ctr,actions,action_values,cost_per_action_type,purchase_roas",
                    "limit": 10,
                },
            })
        status, payload, _ = common.graph_batch_get(token, batch)
        if status != 200 or not isinstance(payload, list):
            for campaign_id in campaign_ids[start:start + 50]:
                result[campaign_id] = {"status": "unavailable", "reason": f"batch_http_{status}"}
            continue
        for child in payload:
            campaign_id = norm(child.get("name"))
            body = child.get("body") if isinstance(child, dict) else None
            rows = body.get("data") if isinstance(body, dict) else None
            row = rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}
            spend = finite_float(row.get("spend"))
            purchase_value = action_value(row.get("action_values"), ACTION_PURCHASE)
            result[campaign_id] = {
                "status": "ok" if row else "no_data_today",
                "spend": spend,
                "impressions": finite_float(row.get("impressions")),
                "cpm": finite_float(row.get("cpm")),
                "ctr": finite_float(row.get("ctr")),
                "messaging_results": action_value(row.get("actions"), ACTION_MESSAGING),
                "cost_per_messaging_result": action_value(row.get("cost_per_action_type"), ACTION_MESSAGING),
                "purchase_roas": action_value(row.get("purchase_roas"), ACTION_PURCHASE),
                "purchase_value": purchase_value,
            }
    return result


def reconcile_pause(common, token: str, campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = norm(campaign.get("campaign_id"))
    fields = "id,name,status,effective_status,configured_status,updated_time"
    pre_status, before, _ = common.graph_get(campaign_id, token, {"fields": fields})
    if pre_status != 200 or not isinstance(before, dict):
        return {"campaign_id": campaign_id, "campaign_name": campaign.get("campaign_name"), "ok": False, "stage": "pre_readback", "http_status": pre_status}
    if norm(before.get("status")) == "PAUSED" or norm(before.get("configured_status")) == "PAUSED":
        return {"campaign_id": campaign_id, "campaign_name": campaign.get("campaign_name"), "ok": True, "stage": "already_paused", "before": {"status": before.get("status"), "effective_status": before.get("effective_status")}, "after": {"status": before.get("status"), "effective_status": before.get("effective_status")}}
    post_status, post_body, _ = common.graph_post_once(campaign_id, token, {"status": "PAUSED"})
    read_status, after, _ = common.graph_get(campaign_id, token, {"fields": fields})
    confirmed = bool(read_status == 200 and isinstance(after, dict) and (norm(after.get("status")) == "PAUSED" or norm(after.get("configured_status")) == "PAUSED"))
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("campaign_name"),
        "ok": confirmed,
        "stage": "paused_confirmed" if confirmed else "pause_not_confirmed",
        "post_http_status": post_status,
        "post_response_success": bool(isinstance(post_body, dict) and post_body.get("success") is True),
        "readback_http_status": read_status,
        "before": {"status": before.get("status"), "effective_status": before.get("effective_status")},
        "after": {"status": after.get("status") if isinstance(after, dict) else None, "effective_status": after.get("effective_status") if isinstance(after, dict) else None},
    }


def fmt_number(value: Any, decimals: int = 2) -> str:
    number = finite_float(value)
    if number is None:
        return "N/D"
    return f"{number:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_money(value: Any) -> str:
    number = finite_float(value)
    return "N/D" if number is None else f"${number:,.2f}"


def build_alert(group: dict[str, Any], actions: list[dict[str, Any]], insights: dict[str, dict[str, Any]], run_at: dt.datetime, lead_limit: float) -> str:
    confirmed = [row for row in actions if row.get("ok")]
    failed = [row for row in actions if not row.get("ok")]
    restriction = group.get("restriction") or {}
    if restriction.get("active") is True:
        restriction_text = f"Sim, até {restriction.get('restricted_until')} (Smart Bidding)"
    elif restriction.get("active") is False:
        restriction_text = "Não indicada como ativa na Smart Bidding"
    else:
        restriction_text = "Não confirmada"
    lines = [
        "```text",
        "⛔ LIMITE DE LEADS — PÁGINA DESATIVADA",
        "",
        f"Página: {group.get('page_name') or 'N/D'}",
        f"UTM Campaign: {group.get('utm_campaign')}",
        f"Leads: {fmt_number(group.get('leads'), 0)}",
        f"Limite: > {fmt_number(lead_limit, 0)}",
        f"Status Smart Bidding: {group.get('smart_bidding_status') or 'N/D'}",
        f"Restrição: {restriction_text}",
        f"Horário: {run_at.strftime('%d/%m/%Y %H:%M')} America/New_York",
        "",
        f"Campanhas encontradas: {len(actions)}",
        f"Campanhas confirmadas PAUSED: {len(confirmed)}",
        f"Falhas/pendências: {len(failed)}",
        "",
        "Campanha                                              Spend    ROAS   Res.   CPM    CTR    Estado",
        "----------------------------------------------------  -------  -----  -----  -----  -----  --------",
    ]
    for campaign in group.get("campaigns") or []:
        campaign_id = norm(campaign.get("campaign_id"))
        metric = insights.get(campaign_id) or {}
        action = next((row for row in actions if row.get("campaign_id") == campaign_id), {})
        name = norm(campaign.get("campaign_name"))
        if len(name) > 52:
            name = name[:49] + "..."
        state = "PAUSED" if action.get("ok") else "PENDENTE"
        lines.append(
            f"{name:<52}  {fmt_money(metric.get('spend')):>7}  {fmt_number(metric.get('purchase_roas')):>5}  {fmt_number(metric.get('messaging_results'),0):>5}  {fmt_money(metric.get('cpm')):>5}  {fmt_number(metric.get('ctr')):>5}  {state:>8}"
        )
    lines += ["", f"Readback Meta: {len(confirmed)}/{len(actions)} campanhas confirmadas como PAUSED"]
    if failed:
        lines.append("⚠️ Estado parcial: há campanha ainda não confirmada; reconciliação necessária.")
    else:
        lines.append("✅ Nenhuma campanha mapeada desta página permanece ativa neste ciclo.")
    lines += ["Reativação automática: não", "```"]
    return "\n".join(lines)


def post_to_thread(thread_id: str, message: str) -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(DISCORD_POSTER), "--thread-id", thread_id, "--fallback-title", "Limite de Leads — Eggbev"],
        input=message,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    return {
        "ok": process.returncode == 0,
        "returncode": process.returncode,
        "stderr": process.stderr[-1000:] if process.returncode else "",
    }


def event_id(group: dict[str, Any], actions: list[dict[str, Any]]) -> str:
    material = json.dumps({
        "utm_campaign": group.get("utm_campaign"),
        "campaigns": sorted(norm(row.get("campaign_id")) for row in actions if row.get("ok")),
    }, sort_keys=True).encode()
    return hashlib.sha256(material).hexdigest()[:24]


def sanitized_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": run.get("ok"),
        "mode": run.get("mode"),
        "account_alias": run.get("account_alias"),
        "active_campaigns": run.get("active_campaigns"),
        "active_ads": run.get("active_ads"),
        "eligible_pages": run.get("eligible_pages"),
        "campaigns_planned": run.get("campaigns_planned"),
        "campaigns_paused_confirmed": run.get("campaigns_paused_confirmed"),
        "mapping_issues": run.get("mapping_issues"),
        "alerts_delivered": run.get("alerts_delivered"),
        "blocked_reason": run.get("blocked_reason"),
        "audit_path": run.get("audit_path"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the approved scoped campaign pauses")
    parser.add_argument("--post-alerts", action="store_true", help="post action reports to the approved fixed thread")
    parser.add_argument("--quiet", action="store_true", help="stay silent on successful no-action runs")
    args = parser.parse_args()

    with open_lock() as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        started = now_et()
        run_id = started.strftime("%Y%m%dT%H%M%S%z")
        audit_path = AUDIT_DIR / f"run-{run_id}.json"
        operation = load_json(OP_PATH)
        account_file = load_json(ACCOUNT_PATH)
        account = (account_file.get("accounts") or [{}])[0]
        policy = operation.get("page_lead_guardrail") or {}
        source = policy.get("source") or {}
        discord = policy.get("discord") or {}
        runtime = policy.get("runtime") or {}
        account_id = norm((operation.get("account") or {}).get("account_id"))
        account_alias = norm((operation.get("account") or {}).get("account_alias"))
        lead_limit = finite_float(source.get("threshold")) or 5000.0
        thread_id = norm(discord.get("thread_id"))
        mode = "controlled_write" if args.apply else "dry_run"
        run: dict[str, Any] = {
            "ok": False,
            "run_id": run_id,
            "started_at_et": started.isoformat(),
            "mode": mode,
            "operation_id": operation.get("operation_id"),
            "account_id": account_id,
            "account_alias": account_alias,
            "policy": {
                "metric": source.get("metric"),
                "operator": source.get("operator"),
                "threshold": lead_limit,
                "join_keys": source.get("join_keys"),
                "auto_reactivate": policy.get("auto_reactivate"),
            },
            "audit_path": str(audit_path),
            "writes": [],
            "alerts": [],
        }
        atomic_json(audit_path, run)
        try:
            if source.get("metric") != "LEADS" or source.get("operator") != ">":
                raise GuardrailError("guardrail source contract is not strict LEADS > threshold")
            if args.apply:
                if not policy.get("policy_approved"):
                    raise GuardrailError("guardrail policy is not approved")
                if not runtime.get("write_enabled"):
                    run["blocked_reason"] = runtime.get("blocked_reason") or "guardrail_runtime_write_disabled"
                    raise GuardrailError(run["blocked_reason"])
                if not thread_id:
                    run["blocked_reason"] = "missing_fixed_discord_thread_id"
                    raise GuardrailError(run["blocked_reason"])
                if not args.post_alerts:
                    run["blocked_reason"] = "controlled_write_requires_post_alerts"
                    raise GuardrailError(run["blocked_reason"])
            os.environ.setdefault("ARES_META_TOKEN_CACHE_PATH", "/root/.cache/mgs/ares-meta-token-eggbev-us-cc-en-01-g006.json")
            meta_common = load_module("ares_meta_common_eggbev_guardrail", META_COMMON_PATH)
            sb_common = load_module("ares_sb_common_eggbev_guardrail", SB_COMMON_PATH)
            token, token_field = meta_common.get_token_from_1password(account.get("token_1password_item"))
            run["credential_readback"] = {"item": account.get("token_1password_item"), "field": token_field, "token_len": len(token)}
            status, live_account, _ = meta_common.graph_get("act_" + account_id, token, {"fields": "id,name,account_status,currency,timezone_name,disable_reason"})
            if status != 200 or not isinstance(live_account, dict):
                raise GuardrailError(f"Meta account preflight failed: HTTP {status}")
            if live_account.get("currency") != "USD" or live_account.get("timezone_name") != "America/New_York" or int(live_account.get("account_status") or 0) != 1:
                raise GuardrailError("Meta account identity/currency/timezone/status preflight failed")
            campaigns = fetch_all_meta(meta_common, token, "act_" + account_id + "/campaigns", {
                "fields": "id,name,status,effective_status,configured_status,daily_budget,updated_time",
                "effective_status": ["ACTIVE"],
                "limit": 200,
            })
            ads = fetch_all_meta(meta_common, token, "act_" + account_id + "/ads", {
                "fields": "id,name,status,effective_status,configured_status,campaign{id,name,status,effective_status},creative{id,name,object_story_spec,url_tags,effective_object_story_id}",
                "effective_status": ["ACTIVE"],
                "limit": 200,
            })
            sb_rows, sb_readback = fetch_sb_pages(
                sb_common,
                publisher_name=norm(source.get("publisher_name") or "Eggbev"),
                credential_item=norm(source.get("credential_item") or "Ares - Smartbidding Dashboard"),
            )
            evaluated = evaluate_campaigns(campaigns, ads, sb_rows, lead_limit, started.date())
            groups = evaluated["eligible_groups"]
            run.update({
                "meta_account_readback": {"name": live_account.get("name"), "currency": live_account.get("currency"), "timezone_name": live_account.get("timezone_name"), "account_status": live_account.get("account_status")},
                "smart_bidding_readback": sb_readback,
                "active_campaigns": len(campaigns),
                "active_ads": len(ads),
                "eligible_pages": len(groups),
                "campaigns_planned": sum(len(group.get("campaigns") or []) for group in groups),
                "mapping_issues": len(evaluated["issues"]),
                "evaluation": evaluated,
            })
            campaign_ids = [norm(campaign.get("campaign_id")) for group in groups for campaign in group.get("campaigns") or []]
            insights = fetch_today_insights(meta_common, token, campaign_ids) if campaign_ids else {}
            run["latest_intraday_snapshot"] = insights
            alerts_delivered = 0
            paused_confirmed = 0
            if args.apply:
                for group in groups:
                    actions: list[dict[str, Any]] = []
                    for campaign in group.get("campaigns") or []:
                        action = reconcile_pause(meta_common, token, campaign)
                        actions.append(action)
                        run["writes"].append(action)
                        if action.get("ok"):
                            paused_confirmed += 1
                        run["campaigns_paused_confirmed"] = paused_confirmed
                        atomic_json(audit_path, run)
                    message = build_alert(group, actions, insights, started, lead_limit)
                    delivery = post_to_thread(thread_id, message)
                    alert = {"event_id": event_id(group, actions), "utm_campaign": group.get("utm_campaign"), "delivery": delivery, "confirmed_pauses": sum(1 for action in actions if action.get("ok")), "total_campaigns": len(actions)}
                    run["alerts"].append(alert)
                    if delivery.get("ok"):
                        alerts_delivered += 1
                    atomic_json(audit_path, run)
            run["campaigns_paused_confirmed"] = paused_confirmed
            run["alerts_delivered"] = alerts_delivered
            run["ok"] = True
            run["finished_at_et"] = now_et().isoformat()
            atomic_json(audit_path, run)
            atomic_json(STATE_PATH, {
                "operation_id": operation.get("operation_id"),
                "last_run_id": run_id,
                "last_run_at_et": run["finished_at_et"],
                "last_mode": mode,
                "last_ok": True,
                "active_campaigns": len(campaigns),
                "eligible_pages": len(groups),
                "campaigns_paused_confirmed": paused_confirmed,
                "mapping_issues": len(evaluated["issues"]),
                "audit_path": str(audit_path),
            })
            summary = sanitized_summary(run)
            if not args.quiet or groups or evaluated["issues"]:
                print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            run["ok"] = False
            run["error"] = {"type": type(exc).__name__, "message": str(exc)}
            run["finished_at_et"] = now_et().isoformat()
            atomic_json(audit_path, run)
            atomic_json(STATE_PATH, {
                "operation_id": operation.get("operation_id"),
                "last_run_id": run_id,
                "last_run_at_et": run["finished_at_et"],
                "last_mode": mode,
                "last_ok": False,
                "error": run["error"],
                "audit_path": str(audit_path),
            })
            print(json.dumps(sanitized_summary(run) | {"error": run["error"]}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
