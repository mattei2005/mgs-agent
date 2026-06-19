#!/usr/bin/env python3
"""Probe Meta asyncbatch adset copy for Elena perfect 7/1 clone.

Creates a PAUSED shallow campaign copy, then tries asyncbatch deep-copy of source adsets
into that campaign. If async copy fails or result is not a complete perfect clone,
cleans up the campaign. Never prints tokens.
"""
from __future__ import annotations

import importlib.util
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ACCOUNT_ID = "1356770869843984"
SOURCE_CAMPAIGN_ID = "120248940367540604"
import os
GRAPH_VERSION = os.environ.get("ARES_META_GRAPH_VERSION", "v25.0")
COMMON_PATH = Path("/root/mgs-agent/scripts/ares-meta-common.py")
AUDIT_DIR = Path("/root/mgs-agent/data/ares/meta-ads/audit/clone")


def load_common():
    spec = importlib.util.spec_from_file_location("common", COMMON_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    mod.GRAPH_VERSION = GRAPH_VERSION
    return mod


def safe_error(common, payload):
    return common.safe_meta_error(payload) if isinstance(payload, dict) else payload


def post_form(common, token, path, params, timeout=90):
    clean = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            clean[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, bool):
            clean[k] = "true" if v else "false"
        else:
            clean[k] = str(v)
    clean["access_token"] = token
    req = urllib.request.Request(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip('/')}",
        data=urllib.parse.urlencode(clean).encode(),
        headers={"User-Agent": "mgs-ares-meta-ads/0.1"},
    )
    try:
        common._throttle_before_request()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(body), dict(resp.headers), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(body)
        except Exception:
            payload = {"raw": body[:2000]}
        return e.code, payload, dict(e.headers), body


def get(common, token, path, params=None):
    st, payload, headers = common.graph_get(path, token, params or {})
    return st, payload, headers


def cleanup(common, token, campaign_id, audit, reason):
    if not campaign_id:
        return
    st, payload, _, _ = post_form(common, token, campaign_id, {"status": "DELETED"})
    vst, verify, _ = get(common, token, campaign_id, {"fields": "id,name,status,effective_status"})
    audit.setdefault("cleanups", []).append({
        "campaign_id": campaign_id,
        "reason": reason,
        "delete_status": st,
        "delete_payload": safe_error(common, payload),
        "verify_status": vst,
        "verify": verify if vst == 200 else safe_error(common, verify),
    })


def list_adsets_ads(common, token, campaign_id):
    st_as, adsets, _ = get(common, token, f"{campaign_id}/adsets", {
        "fields": "id,name,status,effective_status,attribution_spec,dsa_beneficiary,dsa_payor,regional_regulated_categories",
        "limit": 50,
    })
    st_ads, ads, _ = get(common, token, f"{campaign_id}/ads", {"fields": "id,name,status,effective_status,adset_id", "limit": 100})
    return {
        "adsets_status": st_as,
        "adsets": adsets.get("data", []) if st_as == 200 else safe_error(common, adsets),
        "ads_status": st_ads,
        "ads": ads.get("data", []) if st_ads == 200 else safe_error(common, ads),
    }


def extract_async_session_ids(payload):
    if not isinstance(payload, dict):
        return []
    ids = []
    for key in ("async_sessions", "async_session", "data"):
        val = payload.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    sid = item.get("id") or item.get("async_session_id")
                    if sid:
                        ids.append(str(sid))
                elif item:
                    ids.append(str(item))
        elif isinstance(val, dict):
            sid = val.get("id") or val.get("async_session_id")
            if sid:
                ids.append(str(sid))
    for key in ("id", "async_request_id", "report_run_id"):
        val = payload.get(key)
        if isinstance(val, str):
            ids.append(val)
    return list(dict.fromkeys(ids))


def poll_possible(common, token, session_ids, audit):
    # Poll every returned async session. Do not clean up while any job is IN_PROGRESS.
    session_ids = [str(s) for s in (session_ids or [])]
    if not session_ids:
        return []
    polls = []
    terminal = {"COMPLETED", "SUCCESS", "FAILED", "SKIPPED"}
    for i in range(40):  # up to ~6.5 min
        time.sleep(10 if i else 3)
        statuses = []
        for sid in session_ids:
            st, payload, _ = get(common, token, sid, {"fields": "id,status,result,errors,complete_time,created_time"})
            rec = {"i": i, "session_id": sid, "status": st, "payload": payload if st == 200 else safe_error(common, payload)}
            polls.append(rec)
            if st == 200:
                statuses.append(str(payload.get("status") or "").upper())
        if statuses and all(s in terminal for s in statuses):
            return polls
    return polls


def main():
    common = load_common()
    token, field = common.get_token_from_1password()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "elena_asyncbatch_adset_deep_copy_probe",
        "graph_version": GRAPH_VERSION,
        "token_item": "Token Meta API",
        "token_field": field,
        "source_campaign_id": SOURCE_CAMPAIGN_ID,
        "steps": [],
        "cleanups": [],
    }

    st_me, me, _ = get(common, token, "me", {"fields": "id,name"})
    audit["steps"].append({"step": "token_me", "status": st_me, "payload": {"id": me.get("id"), "name_present": bool(me.get("name"))} if st_me == 200 else safe_error(common, me)})
    if st_me != 200:
        audit["final"] = {"success": False, "blocker": "token_invalid"}
        return finish(audit, 1)

    st_src, src, _ = get(common, token, SOURCE_CAMPAIGN_ID, {"fields": "id,name,status,effective_status,objective,buying_type,bid_strategy,daily_budget,special_ad_categories,special_ad_category_country"})
    audit["steps"].append({"step": "source_campaign_get", "status": st_src, "payload": src if st_src == 200 else safe_error(common, src)})
    st_src_as, src_as, _ = get(common, token, f"{SOURCE_CAMPAIGN_ID}/adsets", {"fields": "id,name,attribution_spec,dsa_beneficiary,dsa_payor,regional_regulated_categories", "limit": 10})
    source_adsets = src_as.get("data", []) if st_src_as == 200 else []
    audit["steps"].append({"step": "source_adsets_get", "status": st_src_as, "count": len(source_adsets), "payload": source_adsets if st_src_as == 200 else safe_error(common, src_as)})
    if st_src != 200 or len(source_adsets) != 2:
        audit["final"] = {"success": False, "blocker": "source_read_or_unexpected_adset_count"}
        return finish(audit, 1)

    # Step 1: create campaign shell via native shallow copy. This preserves campaign-level lineage better than manual create.
    rename = {"rename_strategy": "ONLY_TOP_LEVEL_RENAME", "append_text": f" - ARES ASYNCBATCH TEST {ts}"}
    st_copy, p_copy, h_copy, raw_copy = post_form(common, token, f"{SOURCE_CAMPAIGN_ID}/copies", {
        "status_option": "PAUSED",
        "rename_options": rename,
    })
    copied_campaign_id = p_copy.get("copied_campaign_id") if isinstance(p_copy, dict) else None
    audit["steps"].append({"step": "campaign_shallow_copy", "status": st_copy, "payload": p_copy if st_copy == 200 else safe_error(common, p_copy), "created_campaign_id": copied_campaign_id})
    if st_copy != 200 or not copied_campaign_id:
        audit["final"] = {"success": False, "blocker": "campaign_shallow_copy_failed"}
        return finish(audit, 1)

    # Step 2: asyncbatch adset deep copy into copied campaign. Key route from Meta docs.
    async_reqs = []
    for idx, aset in enumerate(source_adsets, 1):
        body_params = {
            "name": f"{aset.get('name') or 'adset'} - ARESCOPY {idx}",
            "campaign_id": copied_campaign_id,
            "deep_copy": "true",
            "status_option": "PAUSED",
            "dsa_beneficiary": aset.get("dsa_beneficiary"),
            "dsa_payor": aset.get("dsa_payor"),
            "regional_regulated_categories": json.dumps(aset.get("regional_regulated_categories") or [], ensure_ascii=False),
            "rename_options": json.dumps({"rename_strategy": "DEEP_RENAME", "append_text": f" - ARESCOPY {ts}"}, ensure_ascii=False),
        }
        body = urllib.parse.urlencode({k: v for k, v in body_params.items() if v not in (None, "")})
        async_reqs.append({
            "method": "POST",
            "relative_url": f"{aset['id']}/copies",
            "name": f"copy_adset_{idx}",
            "body": body,
        })
    st_ab, p_ab, h_ab, raw_ab = post_form(common, token, "", {"asyncbatch": json.dumps(async_reqs, ensure_ascii=False)}, timeout=120)
    audit["steps"].append({"step": "root_asyncbatch_adset_copies", "status": st_ab, "request_shape": async_reqs, "payload": p_ab if st_ab == 200 else safe_error(common, p_ab)})
    session_ids = extract_async_session_ids(p_ab)
    if session_ids:
        audit["steps"].append({"step": "asyncbatch_poll", "session_ids": session_ids, "polls": poll_possible(common, token, session_ids, audit)})
    else:
        # Even without a session id, wait briefly and inspect target campaign; some asyncbatch responses are opaque.
        time.sleep(60)

    verification = list_adsets_ads(common, token, copied_campaign_id)
    audit["steps"].append({"step": "verify_copied_campaign_after_asyncbatch", **verification})
    adsets = verification.get("adsets") if isinstance(verification.get("adsets"), list) else []
    ads = verification.get("ads") if isinstance(verification.get("ads"), list) else []
    attr_ok = len(adsets) == 2 and all(any(spec.get("event_type") == "CLICK_THROUGH" and str(spec.get("window_days")) == "7" for spec in (a.get("attribution_spec") or [])) and any(spec.get("event_type") == "VIEW_THROUGH" and str(spec.get("window_days")) == "1" for spec in (a.get("attribution_spec") or [])) for a in adsets)
    success = len(adsets) == 2 and len(ads) == 6 and attr_ok
    if not success:
        cleanup(common, token, copied_campaign_id, audit, "asyncbatch_copy_not_complete_or_not_7_1")
    audit["final"] = {
        "success": success,
        "campaign_id": copied_campaign_id if success else None,
        "created_campaign_id": copied_campaign_id,
        "adsets_count": len(adsets),
        "ads_count": len(ads),
        "attribution_7_1_ok": attr_ok,
        "blocker": None if success else "asyncbatch did not create complete 2x6 clone preserving 7/1",
    }
    return finish(audit, 0 if success else 2)


def finish(audit, code):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIT_DIR / f"elena-asyncbatch-adset-copy-probe-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"success": audit.get("final", {}).get("success"), "final": audit.get("final"), "audit": str(out)}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
