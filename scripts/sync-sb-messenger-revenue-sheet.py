#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Daily Smart Bidding Messenger Daily -> Google Sheet revenue sync.

Reads the live dashboard's default last-seven-days request, aggregates REVENUE by
PROFILE_NAME (Segurador), and replaces column C (RECEITA 7 DIAS) in the
canonical migration tab. Missing names stay blank; present names with zero
revenue are written as numeric zero.

Google access is exclusively the canonical mgs-core-prod Service Account.
Smart Bidding uses the persistent authenticated headed-browser state.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import subprocess
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE = Path("/root/mgs-agent")
SHEET_ID = "1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY"
TAB_NAME = "Migracao 22/06"
TAB_GID = 542936436
DASHBOARD_URL = "https://app.smartbiddingdigital.com/reports/messenger_daily"
REPORT_API = "https://api.jbfdigital.com.br/report/messenger"
SB_STATE = Path("/root/.local/share/mgs/smartbidding_state_headed.json")
GOOGLE_HELPER = BASE / "scripts/mgs_google_workspace_auth.py"
STATE_PATH = BASE / "data/sb-messenger-revenue-sheet-sync-state.json"
BACKUP_DIR = BASE / "backups/sb-messenger-revenue-sheet"
ALERT_CHANNEL_ID = "1498132022634483894"
RODOLFO_ID = "344196393512075265"
NY = ZoneInfo("America/New_York")
CENT = Decimal("0.01")
EXPECTED_HEADERS = ["Removidos acumulado", "User", "RECEITA 7 DIAS", "Segurador"]
SEGURADOR_ALIASES = {
    # The Sheet preserves the operator spelling while Smart Bidding currently
    # exposes this profile with a one-letter correction.
    "ingrid resende": "ingrid rezende",
}


def now_et() -> str:
    return datetime.now(NY).isoformat(timespec="seconds")


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def decimal_value(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal(0)


def cents(value: object) -> Decimal:
    return decimal_value(value).quantize(CENT, rounding=ROUND_HALF_UP)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def google_module():
    spec = importlib.util.spec_from_file_location("mgs_google_workspace_auth", GOOGLE_HELPER)
    if not spec or not spec.loader:
        raise RuntimeError("canonical Google Service Account helper unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GoogleClient:
    def __init__(self) -> None:
        self.module = google_module()
        self.token = self.module.service_account_access_token()
        self.quota_project = self.module.service_account_project_id()
        if self.quota_project != "mgs-core-prod":
            raise RuntimeError("canonical Google project mismatch")
        service_account = self.module.load_service_account()
        if service_account.get("client_email") != "mgsagent@mgs-core-prod.iam.gserviceaccount.com":
            raise RuntimeError("canonical Google Service Account mismatch")

    def api(self, method: str, url: str, payload: object = None) -> dict:
        status, data = self.module.api_json(
            method,
            url,
            self.token,
            payload,
            quota_project=self.quota_project,
        )
        if status not in (200, 201):
            error = data.get("error") or {}
            raise RuntimeError(f"Google API {method} failed HTTP {status}: {error.get('status')}")
        return data

    def preflight(self) -> dict:
        fields = urllib.parse.quote(
            "id,name,driveId,trashed,capabilities(canEdit,canModifyContent)", safe=",()"
        )
        drive = self.api(
            "GET",
            f"https://www.googleapis.com/drive/v3/files/{SHEET_ID}"
            f"?supportsAllDrives=true&fields={fields}",
        )
        capabilities = drive.get("capabilities") or {}
        if drive.get("trashed") or not capabilities.get("canEdit") or not capabilities.get("canModifyContent"):
            raise RuntimeError("target Sheet is not safely editable through canonical Service Account")
        metadata = self.api(
            "GET",
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
            "?fields=spreadsheetId,properties.title,sheets.properties",
        )
        sheet = next(
            (
                item.get("properties") or {}
                for item in metadata.get("sheets") or []
                if (item.get("properties") or {}).get("sheetId") == TAB_GID
            ),
            None,
        )
        if not sheet or sheet.get("title") != TAB_NAME:
            raise RuntimeError("target Sheet tab/gid mismatch")
        row_count = int((sheet.get("gridProperties") or {}).get("rowCount") or 0)
        if row_count < 220:
            raise RuntimeError(f"target Sheet grid unexpectedly small: {row_count}")
        return {
            "drive_name": drive.get("name"),
            "sheet_title": (metadata.get("properties") or {}).get("title"),
            "row_count": row_count,
        }

    def values(self, a1_range: str, *, formatted: bool = False) -> list[list]:
        encoded = urllib.parse.quote(a1_range, safe="")
        render = "FORMATTED_VALUE" if formatted else "UNFORMATTED_VALUE"
        data = self.api(
            "GET",
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}"
            f"?majorDimension=ROWS&valueRenderOption={render}",
        )
        return data.get("values") or []

    def put_value(self, a1_range: str, value: object) -> None:
        encoded = urllib.parse.quote(a1_range, safe="")
        self.api(
            "PUT",
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}"
            "?valueInputOption=RAW",
            {"range": a1_range, "majorDimension": "ROWS", "values": [[value]]},
        )

    def clear_value(self, a1_range: str) -> None:
        encoded = urllib.parse.quote(a1_range, safe="")
        self.api(
            "POST",
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}:clear",
            {},
        )

    def update_column(self, expected: dict[int, Decimal], row_count: int) -> None:
        rows = []
        for row_number in range(2, row_count + 1):
            if row_number in expected:
                rows.append(
                    {"values": [{"userEnteredValue": {"numberValue": float(expected[row_number])}}]}
                )
            else:
                rows.append({"values": [{}]})
        grid = {
            "sheetId": TAB_GID,
            "startRowIndex": 1,
            "endRowIndex": row_count,
            "startColumnIndex": 2,
            "endColumnIndex": 3,
        }
        payload = {
            "requests": [
                {
                    "updateCells": {
                        "range": grid,
                        "rows": rows,
                        "fields": "userEnteredValue",
                    }
                },
                {
                    "repeatCell": {
                        "range": grid,
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {"type": "CURRENCY", "pattern": "R$ #,##0.00"}
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat",
                    }
                },
            ]
        }
        self.api(
            "POST",
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate",
            payload,
        )


async def fetch_live_report() -> tuple[list[dict], dict]:
    if not SB_STATE.exists() or SB_STATE.stat().st_size < 1000:
        raise RuntimeError("Smart Bidding authenticated state is unavailable")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            context = await browser.new_context(
                storage_state=str(SB_STATE),
                viewport={"width": 1600, "height": 1000},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            future = asyncio.get_running_loop().create_future()
            request_payload: dict = {}

            async def on_response(response) -> None:
                if response.url.split("?")[0] == REPORT_API and not future.done():
                    if response.status not in (200, 201):
                        future.set_exception(RuntimeError(f"Smart Bidding report HTTP {response.status}"))
                        return
                    try:
                        future.set_result(await response.json())
                    except Exception as exc:
                        future.set_exception(exc)

            async def on_request(request) -> None:
                if request.url.split("?")[0] == REPORT_API:
                    try:
                        body = request.post_data_json
                        if isinstance(body, dict):
                            request_payload.update(body)
                    except Exception:
                        pass

            page.on("response", on_response)
            page.on("request", on_request)
            await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=120000)
            data = await asyncio.wait_for(future, timeout=120)
            rows = data if isinstance(data, list) else next(
                (
                    data[key]
                    for key in ("data", "rows", "result", "items")
                    if isinstance(data, dict) and isinstance(data.get(key), list)
                ),
                [],
            )
            return rows, request_payload
        finally:
            await browser.close()


def aggregate_report(rows: list[dict], request_payload: dict) -> tuple[dict[str, Decimal], dict[str, str], Decimal, dict]:
    publishers = request_payload.get("publishers") or []
    start = str(request_payload.get("initialDate") or "")[:10]
    end = str(request_payload.get("finalDate") or "")[:10]
    if len(rows) < 1000 or len(publishers) < 30:
        raise RuntimeError(
            f"Smart Bidding scope unexpectedly small: rows={len(rows)} publishers={len(publishers)}"
        )
    try:
        start_date = datetime.fromisoformat(start).date()
        end_date = datetime.fromisoformat(end).date()
    except ValueError as exc:
        raise RuntimeError("Smart Bidding last-seven-days window is invalid") from exc
    if (end_date - start_date).days != 6:
        raise RuntimeError(f"Smart Bidding window is not seven inclusive days: {start}..{end}")

    aggregate: dict[str, Decimal] = defaultdict(Decimal)
    labels: dict[str, str] = {}
    blank_revenue = Decimal(0)
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Smart Bidding report row is not an object")
        name = str(row.get("PROFILE_NAME") or "").strip()
        revenue = decimal_value(row.get("REVENUE"))
        key = norm(name)
        if not key:
            blank_revenue += revenue
            continue
        aggregate[key] += revenue
        labels.setdefault(key, name)
    rounded = {key: cents(value) for key, value in aggregate.items()}
    if not 100 <= len(rounded) <= 300:
        raise RuntimeError(f"Smart Bidding named-profile count outside safety bounds: {len(rounded)}")
    summary = {
        "period_start": start,
        "period_end": end,
        "publishers": len(publishers),
        "api_rows": len(rows),
        "named_profiles": len(rounded),
        "dashboard_groups": len(rounded) + (1 if cents(blank_revenue) else 0),
        "blank_profile_revenue": str(cents(blank_revenue)),
        "dashboard_total": str(cents(sum(rounded.values(), cents(blank_revenue)))),
    }
    return rounded, labels, cents(blank_revenue), summary


def aggregate_invest_3d(rows: list[dict], request_payload: dict) -> dict:
    """Separate today's partial spend from the prior three closed dates."""
    publishers = request_payload.get("publishers") or []
    end_text = str(request_payload.get("finalDate") or "")[:10]
    if len(rows) < 1000 or len(publishers) < 30:
        raise RuntimeError(
            f"Smart Bidding scope unexpectedly small: rows={len(rows)} publishers={len(publishers)}"
        )
    try:
        end_date = datetime.fromisoformat(end_text).date()
    except ValueError as exc:
        raise RuntimeError("Smart Bidding Invest 3D final date is invalid") from exc
    current_date = end_date.isoformat()
    period_dates = [(end_date - timedelta(days=offset)).isoformat() for offset in (3, 2, 1)]
    required_dates = set(period_dates + [current_date])
    observed_dates = {
        str(row.get("DATE") or "")[:10]
        for row in rows
        if isinstance(row, dict) and str(row.get("DATE") or "")[:10] in required_dates
    }
    missing_dates = sorted(required_dates - observed_dates)
    if missing_dates:
        raise RuntimeError(f"Smart Bidding Invest dates missing: {missing_dates}")

    aggregate_3d: dict[str, Decimal] = defaultdict(Decimal)
    aggregate_today: dict[str, Decimal] = defaultdict(Decimal)
    labels: dict[str, str] = {}
    source_rows_3d = 0
    source_rows_today = 0
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Smart Bidding report row is not an object")
        row_date = str(row.get("DATE") or "")[:10]
        if row_date not in required_dates:
            continue
        name = str(row.get("PROFILE_NAME") or "").strip()
        key = norm(name)
        if not key:
            continue
        labels.setdefault(key, name)
        if row_date == current_date:
            source_rows_today += 1
            aggregate_today[key] += decimal_value(row.get("INVESTIMENT"))
        else:
            source_rows_3d += 1
            aggregate_3d[key] += decimal_value(row.get("INVESTIMENT"))
    if not 100 <= len(labels) <= 300:
        raise RuntimeError(
            f"Smart Bidding Invest named-profile count outside safety bounds: {len(labels)}"
        )
    rounded_3d = {key: cents(aggregate_3d[key]) for key in labels}
    rounded_today = {key: cents(aggregate_today[key]) for key in labels}
    return {
        "status": "INVEST_3D_OK",
        "source": "Smart Bidding /report/messenger",
        "metric": "INVESTIMENT",
        "period_start": period_dates[0],
        "period_end": period_dates[-1],
        "days": 3,
        "includes_current_day": False,
        "current_date": current_date,
        "current_day_partial": True,
        "source_currency": request_payload.get("currency"),
        "publishers": len(publishers),
        "source_rows": source_rows_3d,
        "source_rows_today": source_rows_today,
        "named_profiles": len(labels),
        "total": str(cents(sum(rounded_3d.values(), Decimal(0)))),
        "today_total": str(cents(sum(rounded_today.values(), Decimal(0)))),
        "by_profile": {key: str(value) for key, value in sorted(rounded_3d.items())},
        "by_profile_today": {key: str(value) for key, value in sorted(rounded_today.items())},
        "labels": {key: labels[key] for key in sorted(labels)},
    }


def sheet_snapshot(client: GoogleClient, row_count: int) -> tuple[list[list], list[tuple[int, str, str]]]:
    values = client.values(f"'{TAB_NAME}'!A1:F{row_count}")
    if not values or values[0][:4] != EXPECTED_HEADERS:
        raise RuntimeError("target Sheet headers changed")
    named_rows = []
    for row_number in range(2, row_count + 1):
        row = values[row_number - 1] if row_number - 1 < len(values) else []
        name = str(row[3] if len(row) > 3 else "").strip()
        if name:
            named_rows.append((row_number, name, norm(name)))
    if not 150 <= len(named_rows) <= 400:
        raise RuntimeError(f"target Sheet named-row count outside safety bounds: {len(named_rows)}")
    duplicates = Counter(key for _, _, key in named_rows)
    if any(count > 1 for count in duplicates.values()):
        raise RuntimeError("duplicate normalized Segurador names in target Sheet")
    return values, named_rows


def match_sheet_rows(
    named_rows: list[tuple[int, str, str]], aggregate: dict[str, Decimal]
) -> tuple[dict[int, Decimal], set[str]]:
    """Resolve one Sheet row to one or more unique Smart Bidding profile names.

    Slash-separated Segurador cells represent retained old/current operator
    names. A full-cell exact match wins; otherwise each slash component may
    contribute revenue. An aggregate profile may never feed two Sheet rows.
    """
    expected: dict[int, Decimal] = {}
    mapped_keys: set[str] = set()
    key_owner: dict[str, tuple[int, str]] = {}
    for row_number, name, full_key in named_rows:
        if full_key in aggregate:
            row_keys = [full_key]
        else:
            row_keys = []
            for part in name.split("/"):
                part_key = norm(part)
                if not part_key:
                    continue
                resolved = part_key if part_key in aggregate else SEGURADOR_ALIASES.get(part_key)
                if resolved in aggregate and resolved not in row_keys:
                    row_keys.append(resolved)
        for key in row_keys:
            if key in key_owner:
                owner_row, owner_name = key_owner[key]
                raise RuntimeError(
                    f"Smart Bidding Segurador maps to multiple Sheet rows: "
                    f"{key!r} -> {owner_row} {owner_name!r}, {row_number} {name!r}"
                )
            key_owner[key] = (row_number, name)
        if row_keys:
            expected[row_number] = cents(sum((aggregate[key] for key in row_keys), Decimal(0)))
            mapped_keys.update(row_keys)
    return expected, mapped_keys


def old_column(values: list[list], row_count: int) -> dict[int, object]:
    previous: dict[int, object] = {}
    for row_number in range(2, row_count + 1):
        row = values[row_number - 1] if row_number - 1 < len(values) else []
        if len(row) > 2 and str(row[2]).strip() != "":
            previous[row_number] = row[2]
    return previous


def canary(client: GoogleClient, values_before: list[list], row_count: int) -> str:
    canary_range = f"'{TAB_NAME}'!C{row_count}"
    row = values_before[row_count - 1] if row_count - 1 < len(values_before) else []
    original = row[2] if len(row) > 2 and str(row[2]).strip() != "" else None
    sentinel = f"MGS_CANARY_{int(time.time())}"
    client.put_value(canary_range, sentinel)
    readback = client.values(canary_range)
    if not readback or readback[0][0] != sentinel:
        raise RuntimeError("Google Sheets canary readback mismatch")
    if original is None:
        client.clear_value(canary_range)
        restored = client.values(canary_range)
        if restored:
            raise RuntimeError("Google Sheets canary clear/restore mismatch")
    else:
        client.put_value(canary_range, original)
        restored = client.values(canary_range)
        if not restored or restored[0][0] != original:
            raise RuntimeError("Google Sheets canary value restore mismatch")
    return "write_readback_restore_ok"


def verify_column(client: GoogleClient, expected: dict[int, Decimal], row_count: int) -> dict:
    values = client.values(f"'{TAB_NAME}'!C2:C{row_count}")
    actual: dict[int, Decimal] = {}
    for offset in range(row_count - 1):
        row = values[offset] if offset < len(values) else []
        if row and str(row[0]).strip() != "":
            actual[offset + 2] = cents(row[0])
    wrong = [
        (row, str(value), str(actual.get(row)))
        for row, value in expected.items()
        if actual.get(row) != value
    ]
    unexpected = [row for row in actual if row not in expected]
    if wrong or unexpected or len(actual) != len(expected):
        raise RuntimeError(
            f"Sheet readback mismatch: wrong={wrong[:5]} unexpected={unexpected[:5]} "
            f"actual={len(actual)} expected={len(expected)}"
        )
    return {
        "written_rows": len(actual),
        "positive_rows": sum(1 for value in actual.values() if value > 0),
        "zero_rows": sum(1 for value in actual.values() if value == 0),
        "written_total": str(cents(sum(actual.values(), Decimal(0)))),
    }


def backup_snapshot(values: list[list], named_rows: list[tuple[int, str, str]], row_count: int) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(NY).strftime("%Y%m%dT%H%M%S%z")
    path = BACKUP_DIR / f"before-{stamp}.json"
    previous = old_column(values, row_count)
    payload = {
        "created_at": now_et(),
        "sheet_id": SHEET_ID,
        "tab": TAB_NAME,
        "gid": TAB_GID,
        "column": "C",
        "rows": [
            {
                "row": row_number,
                "segurador": name,
                "previous_value": previous.get(row_number),
            }
            for row_number, name, _ in named_rows
        ],
    }
    atomic_json(path, payload)
    return str(path)


def send_failure_alert(message: str) -> bool:
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        return False
    safe = message.replace("\n", " ")[-900:]
    payload = json.dumps(
        {
            "content": f"<@{RODOLFO_ID}>",
            "allowed_mentions": {"users": [RODOLFO_ID]},
            "embeds": [
                {
                    "title": "Falha — Receita Messenger 7 dias",
                    "color": 15158332,
                    "description": "O cron não atualizou a coluna C da planilha.",
                    "fields": [
                        {"name": "Erro", "value": safe, "inline": False},
                        {"name": "Alvo", "value": f"{TAB_NAME} / RECEITA 7 DIAS", "inline": False},
                        {"name": "Horário", "value": now_et(), "inline": True},
                    ],
                }
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{ALERT_CHANNEL_ID}/messages",
        data=payload,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "MGS-SB-Messenger-Revenue-Sheet/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status in (200, 201)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="read and validate without Sheet writes")
    mode.add_argument("--apply", action="store_true", help="update column C with live last-seven-days totals")
    mode.add_argument(
        "--invest-3d-json",
        action="store_true",
        help="print today's partial INVESTIMENT and the prior three closed-date totals",
    )
    parser.add_argument("--no-alert", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env(BASE / ".env")
    load_env(Path("/root/.hermes/profiles/zeus/.env"))
    started = now_et()
    try:
        if args.invest_3d_json:
            report_rows, request_payload = asyncio.run(
                asyncio.wait_for(fetch_live_report(), timeout=45)
            )
            print(json.dumps(aggregate_invest_3d(report_rows, request_payload), ensure_ascii=False, separators=(",", ":")))
            return 0
        client = GoogleClient()
        preflight = client.preflight()
        report_rows, request_payload = asyncio.run(fetch_live_report())
        aggregate, labels, blank_revenue, report_summary = aggregate_report(report_rows, request_payload)
        values, named_rows = sheet_snapshot(client, preflight["row_count"])
        expected, mapped_keys = match_sheet_rows(named_rows, aggregate)
        ratio = len(expected) / len(named_rows)
        if ratio < 0.65:
            raise RuntimeError(
                f"Segurador match ratio below safety gate: {len(expected)}/{len(named_rows)}"
            )
        unused_keys = sorted(key for key in aggregate if key not in mapped_keys)
        unused_names = [labels[key] for key in unused_keys]
        matched_sheet_rows = set(expected)
        unmatched_names = [name for row_number, name, _ in named_rows if row_number not in matched_sheet_rows]
        base_summary = {
            "status": "DRY_RUN_OK" if args.dry_run else "SYNC_OK",
            "started_at_et": started,
            "completed_at_et": now_et(),
            **report_summary,
            "sheet_named_rows": len(named_rows),
            "matched_rows": len(expected),
            "unmatched_sheet_rows": len(unmatched_names),
            "sb_named_not_in_sheet": unused_names,
            "unassigned_revenue": str(
                cents(blank_revenue + sum((aggregate[key] for key in unused_keys), Decimal(0)))
            ),
            "auth": "mgs-core-prod Service Account",
        }
        if args.dry_run:
            print(json.dumps(base_summary, ensure_ascii=False, separators=(",", ":")))
            return 0

        canary_result = canary(client, values, preflight["row_count"])
        values_after_canary, named_rows_after = sheet_snapshot(client, preflight["row_count"])
        if named_rows_after != named_rows:
            raise RuntimeError("target Sheet Segurador rows changed during sync")
        if old_column(values_after_canary, preflight["row_count"]) != old_column(
            values, preflight["row_count"]
        ):
            raise RuntimeError("target Sheet revenue column changed concurrently during sync")

        backup_path = backup_snapshot(values, named_rows, preflight["row_count"])
        client.update_column(expected, preflight["row_count"])
        try:
            verified = verify_column(client, expected, preflight["row_count"])
        except Exception as validation_error:
            previous = {row: cents(value) for row, value in old_column(values, preflight["row_count"]).items()}
            try:
                client.update_column(previous, preflight["row_count"])
                verify_column(client, previous, preflight["row_count"])
            except Exception as rollback_error:
                raise RuntimeError(
                    f"post-write validation failed and rollback failed: "
                    f"validation={validation_error}; rollback={rollback_error}"
                ) from rollback_error
            raise RuntimeError(
                f"post-write validation failed; previous values restored: {validation_error}"
            ) from validation_error

        final = {
            **base_summary,
            **verified,
            "canary": canary_result,
            "readback": "exact_cents_ok",
            "backup": backup_path,
        }
        atomic_json(STATE_PATH, final)
        print(json.dumps(final, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc).replace(chr(10), ' ')[-1000:]}"
        failed: dict[str, object] = {
            "status": "SYNC_FAILED",
            "started_at_et": started,
            "completed_at_et": now_et(),
            "error": error,
        }
        try:
            atomic_json(STATE_PATH, failed)
        except Exception:
            pass
        alerted = False
        if args.apply and not args.no_alert:
            try:
                alerted = send_failure_alert(error)
            except Exception:
                alerted = False
        failed["alerted"] = alerted
        print(json.dumps(failed, ensure_ascii=False, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
