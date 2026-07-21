#!/usr/bin/env python3
"""Read-only DigitalTRChat flow inspector.

Loads a named flow, enforces the yellow Edit / red Delete safety boundary,
and extracts the live graph JSON without saving or mutating the builder.
"""

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict, deque
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE = "https://digitaltrchat.com"
BOT_LIST = f"{BASE}/messenger_bot/bot_list"


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect one DigitalTRChat flow without modifying it")
    parser.add_argument("--vault", required=True, help="1Password vault name")
    parser.add_argument("--item", required=True, help="1Password login item title")
    parser.add_argument("--page-id", required=True, type=int, help="DigitalTRChat page number, e.g. 1084")
    parser.add_argument("--flow", required=True, help="Exact flow reference name")
    parser.add_argument("--output", help="Optional path for full extracted graph JSON")
    parser.add_argument("--screenshot", help="Optional path for a full-page builder screenshot")
    parser.add_argument("--timeout-ms", type=int, default=90000)
    return parser.parse_args()


def resolve_credentials(vault, item):
    try:
        raw = subprocess.check_output(
            ["op", "item", "get", item, "--vault", vault, "--format", "json", "--reveal"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError("Unable to resolve the requested 1Password item") from exc
    record = json.loads(raw)
    fields = {field.get("id"): field.get("value") for field in record.get("fields", [])}
    username = fields.get("username")
    password = fields.get("password") or fields.get("credential")
    if not username or not password:
        raise RuntimeError("The 1Password item lacks username or concealed password/credential")
    return username, password


def normalize_preview(value, limit=180):
    value = value or ""
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Cf")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def graph_summary(graph, account_item, page_id, flow_name, builder_url):
    nodes = {int(node_id): node for node_id, node in graph.get("nodes", {}).items()}
    counts = Counter(node.get("name", "Unknown") for node in nodes.values())
    adjacency = defaultdict(list)
    for node_id, node in nodes.items():
        for output in node.get("outputs", {}).values():
            for connection in output.get("connections", []):
                adjacency[node_id].append(int(connection["node"]))

    start_ids = [node_id for node_id, node in nodes.items() if node.get("name") == "Start Bot Flow"]
    reachable = set()
    queue = deque(start_ids)
    while queue:
        node_id = queue.popleft()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        queue.extend(adjacency[node_id])

    sequence_settings = []
    delays = []
    buttons = []
    image_click_destinations = []
    texts = []
    postbacks = []
    zero_width_text_nodes = []

    for node_id, node in sorted(nodes.items()):
        node_type = node.get("name")
        data = node.get("data", {})
        if node_type == "New Sequence":
            sequence_settings.append({
                "node_id": node_id,
                "name": data.get("name"),
                "starting_time": data.get("startingTime"),
                "closing_time": data.get("closingTime"),
                "timezone": data.get("timezone"),
            })
        elif node_type == "Sequence Single":
            minutes_raw = data.get("promotional") or data.get("nonPromotional") or ""
            try:
                minutes = int(minutes_raw)
            except (TypeError, ValueError):
                minutes = None
            delays.append({
                "node_id": node_id,
                "minutes": minutes,
                "label": data.get("promotionalText") or data.get("nonPromotionalText"),
                "promotional": bool(data.get("isPromotionalChecked")),
                "targets": adjacency[node_id],
            })
        elif node_type == "Button":
            value = data.get("value")
            buttons.append({
                "node_id": node_id,
                "label": data.get("buttonText"),
                "type": data.get("buttonType"),
                "destination": value or data.get("text"),
                "domain": urlparse(value).netloc if value else None,
            })
        elif node_type == "Generic Template":
            image_link = data.get("imageClickDestinationLink")
            if image_link:
                image_click_destinations.append({
                    "node_id": node_id,
                    "destination": image_link,
                    "domain": urlparse(image_link).netloc,
                })
        elif node_type == "Text":
            raw_text = data.get("textMessage") or ""
            has_zero_width = any(unicodedata.category(ch) == "Cf" for ch in raw_text)
            if has_zero_width:
                zero_width_text_nodes.append(node_id)
            texts.append({
                "node_id": node_id,
                "preview": normalize_preview(raw_text),
                "typing_delay_seconds": data.get("delayReplyFor"),
                "typing_display": bool(data.get("IsTypingOnDisplayChecked")),
                "has_zero_width": has_zero_width,
                "targets": adjacency[node_id],
            })
        elif node_type == "New Postback":
            postbacks.append({
                "node_id": node_id,
                "title": data.get("title"),
                "targets": adjacency[node_id],
            })

    delays.sort(key=lambda entry: (entry["minutes"] is None, entry["minutes"] or 0, entry["node_id"]))
    return {
        "status": "ok",
        "mode": "read-only",
        "account_item": account_item,
        "page_id": page_id,
        "flow": flow_name,
        "builder_url": builder_url,
        "graph_id": graph.get("id"),
        "node_count": len(nodes),
        "node_types": dict(sorted(counts.items())),
        "reachable_node_count": len(reachable),
        "disconnected_node_ids": sorted(set(nodes) - reachable),
        "sequence_settings": sequence_settings,
        "sequence_delays": delays,
        "postbacks": postbacks,
        "buttons": buttons,
        "image_click_destinations": image_click_destinations,
        "texts": texts,
        "zero_width_text_node_ids": zero_width_text_nodes,
    }


def run(args):
    username, password = resolve_credentials(args.vault, args.item)
    manager_url = f"{BASE}/visual_flow_builder/flowbuilder_manager/{args.page_id}/1"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            ),
        )
        try:
            page = context.new_page()
            page.goto(BOT_LIST, wait_until="domcontentloaded", timeout=args.timeout_ms)
            if "/home/login" in page.url:
                page.get_by_role("textbox", name="Email Or FB ID").fill(username)
                page.get_by_role("textbox", name="Password").fill(password)
                page.get_by_role("button", name="Login").click()
                page.wait_for_timeout(4000)
                if "/home/login" in page.url:
                    raise RuntimeError("DigitalTRChat login did not leave the login page")

            page.goto(manager_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            exact_flow = page.get_by_text(args.flow, exact=True)
            exact_flow.wait_for(state="visible", timeout=args.timeout_ms)
            row = page.locator("tr").filter(has=exact_flow).first
            if row.count() != 1:
                raise RuntimeError("Unable to isolate exactly one target flow row")

            edit = row.locator('a[title="Edit"]')
            if edit.count() != 1:
                raise RuntimeError("Target row does not contain exactly one Edit action")
            edit_class = edit.get_attribute("class") or ""
            edit_href = edit.get_attribute("href") or ""
            unsafe = row.locator('a[title="Delete"], .delete_data, .btn-outline-danger')
            if (
                "btn-outline-warning" not in edit_class
                or "btn-outline-danger" in edit_class
                or "delete_data" in edit_class
                or "/visual_flow_builder/edit_builder_data/" not in edit_href
                or unsafe.count() < 1
            ):
                raise RuntimeError("Edit/Delete safety predicates did not match the expected UI")

            with page.expect_popup(timeout=30000) as popup_info:
                edit.click()
            builder = popup_info.value
            builder.wait_for_load_state("domcontentloaded", timeout=args.timeout_ms)
            builder.wait_for_function("typeof data !== 'undefined' && data", timeout=args.timeout_ms)
            raw_graph = builder.evaluate("data")
            graph = json.loads(raw_graph)

            if args.output:
                output_path = Path(args.output).expanduser().resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
            if args.screenshot:
                screenshot_path = Path(args.screenshot).expanduser().resolve()
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                builder.screenshot(path=str(screenshot_path), full_page=True)

            return graph_summary(graph, args.item, args.page_id, args.flow, builder.url)
        finally:
            context.close()
            browser.close()


def main():
    args = parse_args()
    try:
        result = run(args)
    except (RuntimeError, PlaywrightTimeoutError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
