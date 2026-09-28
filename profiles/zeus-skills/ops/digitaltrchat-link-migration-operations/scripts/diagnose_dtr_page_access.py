#!/usr/bin/env python3
"""Sanitized DTR/Graph access gate for a frozen Page manifest.

Tokens and secrets exist only in process memory. The JSON report contains only
app IDs, validity/identity verdicts, Page visibility, tasks-independent counts,
and subscribed-app IDs.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

import requests
from playwright.async_api import async_playwright

VAULT = "MGS Conteúdo"
GRAPH_BASE = "https://graph.facebook.com/v23.0/"


def load_helper(path: Path):
    spec = importlib.util.spec_from_file_location("dtr_operation_helper", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load operation helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = ("resolve_credentials", "login_context", "switch_account", "current_inventory", "AUDIT", "DTR_BASE")
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"operation helper missing required exports: {missing}")
    return module


def resolve_item_id(title: str) -> str:
    rows = json.loads(
        subprocess.check_output(
            ["op", "item", "list", "--vault", VAULT, "--format", "json"],
            text=True,
        )
    )
    matches = [str(row.get("id")) for row in rows if str(row.get("title") or "").strip() == title]
    if len(matches) != 1:
        raise RuntimeError(f"exact app item resolution count={len(matches)}")
    return matches[0]


def item_fields(item_id: str) -> dict[str, str]:
    raw = subprocess.check_output(
        ["op", "item", "get", item_id, "--vault", VAULT, "--format", "json", "--reveal"],
        text=True,
    )
    item = json.loads(raw)
    fields: dict[str, str] = {}
    for field in item.get("fields", []):
        label = str(field.get("label") or "").strip().casefold().replace(" ", "_")
        value = field.get("value")
        if label and isinstance(value, str):
            fields[label] = value.strip()
    return fields


def token_from_html(source: str) -> str | None:
    patterns = (
        r"graph\.facebook\.com/me/picture\?access_token=([^&\"'<>]+)",
        r"access_token=([^&\"'<>]+)&",
    )
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            return unquote(html.unescape(match.group(1)))
    return None


def graph_get(path: str, params: dict) -> tuple[int, dict, bool]:
    response = requests.get(GRAPH_BASE + path.lstrip("/"), params=params, timeout=30)
    try:
        body = response.json()
    except Exception:
        body = {"error": {"message": "non-json response"}}
    return response.status_code, body, bool(response.headers.get("x-app-usage"))


def validate_targets(targets: list[dict]) -> None:
    required = {"bot_user", "account_id", "segurador", "page_name", "fb_page_id"}
    for index, target in enumerate(targets):
        missing = sorted(required - set(target))
        if missing:
            raise RuntimeError(f"target[{index}] missing fields: {missing}")
        if not str(target["fb_page_id"]).isdigit():
            raise RuntimeError(f"target[{index}] has non-numeric fb_page_id")
    ids = [str(target["fb_page_id"]) for target in targets]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate fb_page_id in frozen target manifest")


async def run(args) -> dict:
    helper = load_helper(Path(args.helper))
    targets = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("targets must be a non-empty JSON array")
    validate_targets(targets)
    credentials = helper.resolve_credentials(targets)

    app = item_fields(resolve_item_id(args.app_item_title))
    app_id = app.get("app_id")
    secret = app.get("app_secret") or app.get("secret_key")
    admin_token = app.get("access_token")
    if not app_id or not secret or not admin_token:
        raise RuntimeError("app credential fields incomplete")
    app_access = f"{app_id}|{secret}"

    app_http, app_body, app_usage = graph_get(
        app_id,
        {"fields": "id,name", "access_token": admin_token},
    )
    report = {
        "expected_app_label": args.app,
        "expected_app_id": app_id,
        "app_live": {
            "http": app_http,
            "id": str(app_body.get("id") or ""),
            "name": str(app_body.get("name") or ""),
            "error_code": (app_body.get("error") or {}).get("code"),
            "error_message": (app_body.get("error") or {}).get("message"),
            "x_app_usage_present": app_usage,
        },
        "users": [],
    }

    grouped: dict[str, list[dict]] = {}
    for target in targets:
        grouped.setdefault(str(target["bot_user"]), []).append(target)

    async with async_playwright() as playwright:
        for user, user_targets in sorted(grouped.items()):
            browser, context, page = await helper.login_context(
                playwright,
                user,
                helper.AUDIT.sync.op_password(credentials[user]),
            )
            user_row = {"user": user, "accounts": []}
            try:
                social = helper.DTR_BASE + "/social_accounts/index"
                accounts = []
                seen = set()
                for target in user_targets:
                    account_id = str(target["account_id"])
                    if account_id not in seen:
                        seen.add(account_id)
                        accounts.append({"account_id": account_id, "segurador": target["segurador"]})

                for account in accounts:
                    await helper.switch_account(context, page, account["account_id"], social)
                    await page.goto(social, wait_until="domcontentloaded", timeout=60000)
                    source = await page.content()
                    token = token_from_html(source)
                    inventory = await helper.current_inventory(page)
                    scoped = [
                        target
                        for target in user_targets
                        if str(target["account_id"]) == account["account_id"]
                    ]
                    row = {
                        "account_id": account["account_id"],
                        "segurador": account["segurador"],
                        "dtr_pages": len(inventory),
                        "token_found": bool(token),
                        "scoped_target_count": len(scoped),
                    }
                    if token:
                        debug_http, debug_body, debug_usage = graph_get(
                            "debug_token",
                            {"input_token": token, "access_token": app_access},
                        )
                        debug_data = debug_body.get("data") or {}
                        debug_error = debug_body.get("error") or {}
                        row["debug"] = {
                            "http": debug_http,
                            "is_valid": debug_data.get("is_valid"),
                            "app_id": str(debug_data.get("app_id") or ""),
                            "matches_expected_app": str(debug_data.get("app_id") or "") == str(app_id),
                            "error_code": debug_error.get("code"),
                            "error_subcode": debug_error.get("error_subcode"),
                            "error_message": debug_error.get("message"),
                            "x_app_usage_present": debug_usage,
                        }

                        pages_http, pages_body, _ = graph_get(
                            "me/accounts",
                            {
                                "fields": "id,name,access_token,tasks",
                                "limit": "200",
                                "access_token": token,
                            },
                        )
                        graph_pages = {
                            str(entry.get("id")): entry
                            for entry in (pages_body.get("data") or [])
                            if isinstance(entry, dict)
                        }
                        scoped_rows = []
                        for target in scoped:
                            facebook_id = str(target["fb_page_id"])
                            graph_page = graph_pages.get(facebook_id)
                            page_row = {
                                "page_name": target["page_name"],
                                "fb_page_id": facebook_id,
                                "visible_in_me_accounts": bool(graph_page),
                            }
                            if graph_page and graph_page.get("access_token"):
                                page_http, page_body, _ = graph_get(
                                    "debug_token",
                                    {
                                        "input_token": graph_page["access_token"],
                                        "access_token": app_access,
                                    },
                                )
                                page_data = page_body.get("data") or {}
                                page_error = page_body.get("error") or {}
                                page_row["page_token_debug"] = {
                                    "http": page_http,
                                    "is_valid": page_data.get("is_valid"),
                                    "app_id": str(page_data.get("app_id") or ""),
                                    "matches_expected_app": str(page_data.get("app_id") or "") == str(app_id),
                                    "error_code": page_error.get("code"),
                                    "error_message": page_error.get("message"),
                                }
                                subscribed_http, subscribed_body, _ = graph_get(
                                    facebook_id + "/subscribed_apps",
                                    {
                                        "fields": "id,name",
                                        "access_token": graph_page["access_token"],
                                    },
                                )
                                subscribed_ids = [
                                    str(entry.get("id"))
                                    for entry in (subscribed_body.get("data") or [])
                                    if isinstance(entry, dict)
                                ]
                                page_row["subscribed_apps"] = {
                                    "http": subscribed_http,
                                    "app_ids": subscribed_ids,
                                    "expected_present": str(app_id) in subscribed_ids,
                                    "error_code": (subscribed_body.get("error") or {}).get("code"),
                                    "error_message": (subscribed_body.get("error") or {}).get("message"),
                                }
                            scoped_rows.append(page_row)
                        row["me_accounts"] = {
                            "http": pages_http,
                            "total": len(graph_pages),
                            "error_code": (pages_body.get("error") or {}).get("code"),
                            "error_message": (pages_body.get("error") or {}).get("message"),
                            "targets": scoped_rows,
                        }
                    user_row["accounts"].append(row)
            finally:
                await browser.close()
            report["users"].append(user_row)

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(output, 0o600)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--app-item-title", required=True)
    parser.add_argument("--helper", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
