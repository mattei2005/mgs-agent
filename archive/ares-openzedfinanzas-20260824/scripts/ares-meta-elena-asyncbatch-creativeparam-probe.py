#!/usr/bin/env python3
"""Bounded probe: asyncbatch adset deep-copy with creative_parameters variants.

Goal: test whether normalizing deprecated standard_enhancements during native copy
unblocks a perfect Elena adset copy while preserving 7/1 attribution.
All campaign shells are PAUSED and deleted unless success criteria pass.
Never prints tokens.
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
SOURCE_ADSET_ID = "120248940367380604"
GRAPH_VERSION = "v25.0"
COMMON_PATH = Path("/root/mgs-agent/scripts/ares-meta-common.py")
AUDIT_DIR = Path("/root/mgs-agent/data/ares/meta-ads/audit/clone")


def load_common():
    spec = importlib.util.spec_from_file_location("common", COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load common")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GRAPH_VERSION = GRAPH_VERSION
    return mod


def encode_val(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def post(common, token, path, params, timeout=45):
    body = {k: encode_val(v) for k, v in params.items() if v is not None}
    body["access_token"] = token
    req = urllib.request.Request(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip('/')}",
        data=urllib.parse.urlencode(body).encode(),
        headers={"User-Agent": "mgs-ares-meta-ads/0.1"},
    )
    try:
        common._throttle_before_request()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:2000]}


def get(common, token, path, params=None):
    st, payload, _ = common.graph_get(path, token, params or {})
    return st, payload


def safe(common, payload):
    return common.safe_meta_error(payload) if isinstance(payload, dict) else payload


def cleanup(common, token, cid, rec):
    if not cid:
        return
    st, payload = post(common, token, cid, {"status": "DELETED"})
    vst, verify = get(common, token, cid, {"fields": "id,name,status,effective_status"})
    rec["cleanup"] = {
        "delete_status": st,
        "delete_payload": safe(common, payload),
        "verify_status": vst,
        "verify": verify if vst == 200 else safe(common, verify),
    }


def parse_result(payload):
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, str) and result:
        try:
            return json.loads(result)
        except Exception:
            return {"raw_result": result[:2000]}
    return result or {}


def poll_session(common, token, sid, max_seconds=90):
    started = time.time()
    polls = []
    while time.time() - started < max_seconds:
        time.sleep(5)
        st, payload = get(common, token, sid, {"fields": "id,status,result,complete_time"})
        rec = {"status": st, "payload": payload if st == 200 else safe(common, payload)}
        polls.append(rec)
        if st == 200 and payload.get("status") != "IN_PROGRESS":
            return polls
    return polls


def verify_clone(common, token, cid):
    st_as, adsets = get(common, token, f"{cid}/adsets", {"fields": "id,name,status,effective_status,attribution_spec", "limit": 20})
    st_ads, ads = get(common, token, f"{cid}/ads", {"fields": "id,name,status,effective_status,creative{id,degrees_of_freedom_spec}", "limit": 50})
    as_data = adsets.get("data", []) if st_as == 200 else []
    ads_data = ads.get("data", []) if st_ads == 200 else []
    attr_ok = bool(as_data) and all(
        any(s.get("event_type") == "CLICK_THROUGH" and str(s.get("window_days")) == "7" for s in (a.get("attribution_spec") or []))
        and any(s.get("event_type") == "VIEW_THROUGH" and str(s.get("window_days")) == "1" for s in (a.get("attribution_spec") or []))
        for a in as_data
    )
    std_present = any("standard_enhancements" in json.dumps(((ad.get("creative") or {}).get("degrees_of_freedom_spec") or {})).lower() for ad in ads_data)
    return {
        "adsets_status": st_as,
        "adsets_count": len(as_data),
        "adsets": as_data,
        "ads_status": st_ads,
        "ads_count": len(ads_data),
        "ads_sample": ads_data[:2],
        "attribution_7_1_ok": attr_ok,
        "standard_enhancements_present": std_present,
    }


def main():
    common = load_common()
    token, field = common.get_token_from_1password()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "elena_asyncbatch_creative_parameters_variants",
        "graph_version": GRAPH_VERSION,
        "source_campaign_id": SOURCE_CAMPAIGN_ID,
        "source_adset_id": SOURCE_ADSET_ID,
        "token_item": "Token Meta API",
        "token_field": field,
        "variants": [],
    }

    st_src, src_adset = get(common, token, SOURCE_ADSET_ID, {"fields": "id,name,dsa_beneficiary,dsa_payor,regional_regulated_categories,attribution_spec"})
    audit["source_adset_read"] = {"status": st_src, "payload": src_adset if st_src == 200 else safe(common, src_adset)}
    if st_src != 200:
        audit["final"] = {"success": False, "blocker": "source_adset_read_failed"}
        return finish(audit, 1)

    variants = [
        ("creative_parameters_singular_granular", "creative_parameters", {
            "degrees_of_freedom_spec": {"creative_features_spec": {
                "text_optimizations": {"enroll_status": "OPT_IN"},
                "image_touchups": {"enroll_status": "OPT_IN"},
            }}
        }),
        ("creative_parameter_singular_granular", "creative_parameter", {
            "degrees_of_freedom_spec": {"creative_features_spec": {
                "text_optimizations": {"enroll_status": "OPT_IN"},
                "image_touchups": {"enroll_status": "OPT_IN"},
            }}
        }),
        ("creative_parameters_disable_all_known", "creative_parameters", {
            "degrees_of_freedom_spec": {"creative_features_spec": {
                "standard_enhancements": {"enroll_status": "OPT_OUT"},
                "text_optimizations": {"enroll_status": "OPT_OUT"},
                "image_touchups": {"enroll_status": "OPT_OUT"},
                "inline_comment": {"enroll_status": "OPT_OUT"},
            }}
        }),
    ]

    for variant_name, param_name, creative_param in variants:
        rec = {"variant": variant_name, "param_name": param_name}
        audit["variants"].append(rec)
        st_c, p_c = post(common, token, f"{SOURCE_CAMPAIGN_ID}/copies", {
            "status_option": "PAUSED",
            "rename_options": {"rename_strategy": "ONLY_TOP_LEVEL_RENAME", "append_text": f" - ARES CPVAR {variant_name} {ts}"},
        })
        cid = p_c.get("copied_campaign_id") if isinstance(p_c, dict) else None
        rec["campaign_copy"] = {"status": st_c, "payload": p_c if st_c == 200 else safe(common, p_c), "campaign_id": cid}
        if st_c != 200 or not cid:
            continue

        body_params = {
            "name": f"{src_adset.get('name', 'adset')} - CPVAR {variant_name}",
            "campaign_id": cid,
            "deep_copy": "true",
            "status_option": "PAUSED",
            "dsa_beneficiary": src_adset.get("dsa_beneficiary"),
            "dsa_payor": src_adset.get("dsa_payor"),
            "regional_regulated_categories": json.dumps(src_adset.get("regional_regulated_categories") or [], ensure_ascii=False),
            param_name: json.dumps(creative_param, ensure_ascii=False),
        }
        req = [{
            "method": "POST",
            "relative_url": f"{SOURCE_ADSET_ID}/copies",
            "name": variant_name,
            "body": urllib.parse.urlencode({k: v for k, v in body_params.items() if v is not None}),
        }]
        st_ab, p_ab = post(common, token, "", {"asyncbatch": json.dumps(req, ensure_ascii=False)}, timeout=90)
        sessions = [x.get("id") for x in p_ab.get("async_sessions", [])] if isinstance(p_ab, dict) else []
        rec["asyncbatch"] = {"status": st_ab, "payload": p_ab if st_ab == 200 else safe(common, p_ab), "sessions": sessions}
        if sessions:
            rec["polls"] = poll_session(common, token, sessions[0], max_seconds=90)
            last = rec["polls"][-1]["payload"] if rec["polls"] else {}
            rec["parsed_result"] = parse_result(last) if isinstance(last, dict) else last
        rec["verification"] = verify_clone(common, token, cid)
        success = rec["verification"].get("adsets_count") == 1 and rec["verification"].get("ads_count") == 3 and rec["verification"].get("attribution_7_1_ok")
        rec["success"] = bool(success)
        if success:
            audit["final"] = {"success": True, "variant": variant_name, "campaign_id": cid}
            return finish(audit, 0)
        cleanup(common, token, cid, rec)

    audit["final"] = {"success": False, "blocker": "all_creative_parameter_variants_failed"}
    return finish(audit, 2)


def finish(audit, code):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIT_DIR / f"elena-asyncbatch-creativeparam-probe-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"success": audit.get("final", {}).get("success"), "final": audit.get("final"), "audit": str(out)}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
