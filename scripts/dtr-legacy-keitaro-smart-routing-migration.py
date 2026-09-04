#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Authorized DTR migration from legacy Keitaro URLs to Openzed Smart Routing.

Scope authority: Discord message 1545266004492427325.
Surfaces: existing Auto Principal Drip URLs, Get Started, and No Match only.
Persistent Menu remains out of scope and untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

BASE = "https://digitaltrchat.com"
BOT_LIST = BASE + "/messenger_bot/bot_list"
FLOW_NAME = "Auto Principal Drip"
VAULT = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
REPO = Path("/root/mgs-agent")
REPORT_DIR = REPO / "reports/dtr-url-variance-20260903T172333-0400"
BACKUP_BASE = REPO / "backups"
STATE_PATH = REPO / "data/dtr-legacy-keitaro-smart-routing-migration-state.json"
RESOLVER_PATH = REPO / "scripts/mgs-op-item-resolver.py"
CATALOG_PATH = Path("/root/.hermes/profiles/zeus/skills/ops/digitaltrchat-link-migration-operations/scripts/openzed_link_catalog.py")
AUTH_MESSAGE_ID = "1545266004492427325"
THREAD_ID = "1545131821245669407"

LOGINS = [
    "disparosvizioidmxcces@gmail.com",
    "disparosvizioid@gmail.com",
    "disparosvizioides@gmail.com",
    "disparoswavesbeeen@gmail.com",
    "disparoswavesbeees@gmail.com",
]
LEGACY_CLASSIFICATION = {
    "card.openzed.com": "US-CC-EN",
    "card.wavesbee.com": "US-CC-EN",
    "tarjeta.openzed.com": "US-CC-ES",
    "tarjeta.wavesbee.com": "US-CC-ES",
}
EXPECTED = {
    "pages": 116,
    "US-CC-EN": 67,
    "US-CC-ES": 49,
    "with_flow": 110,
    "actions_only": 6,
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


resolver = load_module(RESOLVER_PATH, "mgs_op_resolver")
catalog_mod = load_module(CATALOG_PATH, "openzed_catalog")


def now_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def atomic_json(path: Path, payload: Any, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if mode is not None:
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def host(url: str) -> str:
    try:
        safe = url.replace("#PAGE_ID#", "PAGE_ID_PLACEHOLDER")
        return (urlparse(safe).hostname or "").lower()
    except Exception:
        return ""


def graph_nodes(graph: dict) -> dict:
    return graph.get("nodes") or {}


def node_lookup(graph: dict, node_id: str) -> dict:
    nodes = graph_nodes(graph)
    node = nodes.get(str(node_id))
    if node is None:
        try:
            node = nodes.get(int(node_id))
        except (TypeError, ValueError):
            node = None
    if node is None:
        raise RuntimeError(f"graph node missing: {node_id}")
    return node


def topology(graph: dict) -> dict:
    nodes = graph_nodes(graph)
    adjacency: dict[str, list[str]] = defaultdict(list)
    edges = 0
    for node_id, node in nodes.items():
        for output in (node.get("outputs") or {}).values():
            for connection in output.get("connections") or []:
                adjacency[str(node_id)].append(str(connection.get("node")))
                edges += 1
    starts = [str(node_id) for node_id, node in nodes.items() if node.get("name") == "Start Bot Flow"]
    seen: set[str] = set()
    queue = deque(starts)
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(adjacency.get(current, []))
    return {
        "nodes": len(nodes),
        "edges": edges,
        "starts": len(starts),
        "reachable": len(seen),
        "disconnected": len(set(map(str, nodes)) - seen),
    }


def business_links(graph: dict) -> list[dict]:
    links: list[dict] = []
    for node_id, node in graph_nodes(graph).items():
        data = node.get("data") or {}
        if node.get("name") == "Button":
            for field in ("value", "text"):
                value = data.get(field)
                if isinstance(value, str) and value.startswith(("http://", "https://")):
                    links.append(
                        {
                            "node_id": str(node_id),
                            "node_type": "Button",
                            "field": field,
                            "url": value,
                            "host": host(value),
                        }
                    )
        elif node.get("name") == "Generic Template":
            value = data.get("imageClickDestinationLink")
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                links.append(
                    {
                        "node_id": str(node_id),
                        "node_type": "Generic Template",
                        "field": "imageClickDestinationLink",
                        "url": value,
                        "host": host(value),
                    }
                )
    return links


def numbered_label(url: str) -> int | None:
    safe = url.replace("#PAGE_ID#", "PAGE_ID_PLACEHOLDER")
    query_match = re.search(r"utm_content=[^&#]*?(?:^|[_-])m?(\d{1,2})-1(?:&|$)", safe, re.I)
    path_match = re.search(r"/[^?#]*?-m(\d{1,2})-1/", safe, re.I)
    numbers = {int(match.group(1)) for match in (query_match, path_match) if match}
    if len(numbers) > 1:
        raise RuntimeError(f"URL semantic number conflict: {url}")
    return next(iter(numbers)) if numbers else None


def pre_sequence_reachable(graph: dict) -> set[str]:
    """Nodes reachable from Start without traversing a sequence node."""
    nodes = graph_nodes(graph)
    adjacency: dict[str, list[str]] = defaultdict(list)
    for node_id, node in nodes.items():
        for output in (node.get("outputs") or {}).values():
            for connection in output.get("connections") or []:
                adjacency[str(node_id)].append(str(connection.get("node")))
    starts = [str(node_id) for node_id, node in nodes.items() if node.get("name") == "Start Bot Flow"]
    seen: set[str] = set()
    queue = deque(starts)
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        node = node_lookup(graph, current)
        if node.get("name") in {"New Sequence", "Sequence Single"}:
            continue
        queue.extend(adjacency.get(current, []))
    return seen


def semantic_flow_links(graph: dict) -> list[dict]:
    links = business_links(graph)
    before_sequence = pre_sequence_reachable(graph)
    initial = [link for link in links if link["node_id"] in before_sequence]
    if len(initial) != 1:
        raise RuntimeError(f"structural M0 inference count={len(initial)}")
    initial_id = initial[0]["node_id"]
    result: list[dict] = []
    for link in links:
        if link["node_id"] == initial_id:
            semantic = 0
            authority = "structural_start_path_before_sequence"
        else:
            semantic = numbered_label(link["url"])
            if semantic is None or semantic == 0:
                raise RuntimeError(f"timed URL semantic label missing/conflicting node={link['node_id']}")
            authority = "matching_path_and_or_utm_content"
        result.append({**link, "semantic": semantic, "semantic_authority": authority})
    semantics = [item["semantic"] for item in result]
    if len(result) != 16 or set(semantics) != set(range(16)) or len(set(semantics)) != 16:
        raise RuntimeError(
            f"legacy flow semantic coverage invalid fields={len(result)} labels={sorted(semantics)}"
        )
    return result


def graph_core(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: graph_core(val) for key, val in value.items() if key != "labelIdTexts"}
    if isinstance(value, list):
        return [graph_core(item) for item in value]
    return value


def scrub_graph_urls(graph: dict, mods: list[dict]) -> dict:
    result = copy.deepcopy(graph)
    for mod in mods:
        node_lookup(result, mod["node_id"])["data"][mod["field"]] = "<SCOPED_URL>"
    return graph_core(result)


def changed_paths(before: Any, after: Any, path: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    if type(before) is not type(after):
        return [path]
    result: list[tuple[str, ...]] = []
    if isinstance(before, dict):
        for key in sorted(set(before) | set(after)):
            if key == "labelIdTexts":
                continue
            if key not in before or key not in after:
                result.append(path + (str(key),))
            else:
                result.extend(changed_paths(before[key], after[key], path + (str(key),)))
    elif isinstance(before, list):
        if len(before) != len(after):
            result.append(path + ("length",))
        else:
            for index, (left, right) in enumerate(zip(before, after)):
                result.extend(changed_paths(left, right, path + (str(index),)))
    elif before != after:
        result.append(path)
    return result


def action_target_variants(base_url: str) -> set[str]:
    suffix = "&subscriber_id=#SUBSCRIBER_ID_REPLACE#"
    return {base_url, base_url + suffix}


def action_target_ok(actual_url: str, base_url: str) -> bool:
    return actual_url in action_target_variants(base_url)


def stable_action(state: dict, baseline: dict | None = None) -> dict:
    reference = baseline or state
    wanted = {
        (field.get("id") or "", field.get("name") or "")
        for field in reference.get("stable_fields", [])
        if field.get("id") or field.get("name")
    }
    output: dict[str, dict] = {}
    for field in state.get("stable_fields", []):
        key_pair = (field.get("id") or "", field.get("name") or "")
        if key_pair not in wanted:
            continue
        identity = field.get("id") or ("name:" + field.get("name", ""))
        lowered = (field.get("id", "") + " " + field.get("name", "")).lower()
        if "ajax-upload-id-" in lowered:
            continue
        normalized = {k: v for k, v in field.items() if k != "visible"}
        value = normalized.get("value")
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            normalized["value"] = "<SCOPED_URL>"
        # Inactive post selectors hydrate in nondeterministic option order.
        if "post_id_" in lowered:
            normalized["value"] = "<INACTIVE_POST_SELECTOR>"
        output[identity] = normalized
    return output


def catalogs() -> dict[str, dict[str, str]]:
    all_catalogs = {
        key: catalog_mod.build_catalog(key, "g003-d") for key in catalog_mod.SCHEMAS
    }
    validation = catalog_mod.validate_catalogs(all_catalogs, expected_medium="g003-d")
    if validation.get("status") != "ok":
        raise RuntimeError(f"canonical catalog validation failed: {validation}")
    return {key: all_catalogs[key] for key in ("US-CC-EN", "US-CC-ES")}


def target_for(catalog: dict[str, str], semantic: int) -> str:
    return catalog["m0-1" if semantic == 0 else f"m{semantic}-1"]


def audit_file(login: str) -> Path:
    return REPORT_DIR / (login.replace("@", "_at_") + ".json")


def page_hosts(item: dict) -> set[str]:
    result: set[str] = set()
    for surface in ("get_started", "no_match"):
        hosts = ((item.get("action") or {}).get(surface) or {}).get("hosts") or {}
        result.update(hosts.keys() if isinstance(hosts, dict) else hosts)
    for link in (item.get("auto_principal_drip") or {}).get("links") or []:
        if link.get("host"):
            result.add(link["host"])
    return result


def build_scope() -> list[dict]:
    rows: list[dict] = []
    for login in LOGINS:
        source = audit_file(login)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if payload.get("login") != login:
            raise RuntimeError(f"audit login mismatch: {source}")
        for account in payload.get("accounts", []):
            for item in account.get("pages", []):
                legacy_hosts = sorted(page_hosts(item) & set(LEGACY_CLASSIFICATION))
                if not legacy_hosts:
                    continue
                classifications = {LEGACY_CLASSIFICATION[value] for value in legacy_hosts}
                if len(classifications) != 1:
                    raise RuntimeError(
                        f"conflicting classification page={item.get('page')} hosts={legacy_hosts}"
                    )
                classification = next(iter(classifications))
                action = item.get("action") or {}
                gs_urls = (action.get("get_started") or {}).get("urls") or []
                nm_urls = (action.get("no_match") or {}).get("urls") or []
                if len(gs_urls) != 1 or len(nm_urls) != 1:
                    raise RuntimeError(
                        f"audit action cardinality page={item.get('page')} gs={len(gs_urls)} nm={len(nm_urls)}"
                    )
                flow_links = (item.get("auto_principal_drip") or {}).get("links") or []
                rows.append(
                    {
                        "login": login,
                        "account_id": str(account.get("account_id")),
                        "account_name": account.get("account_name"),
                        "page": item.get("page"),
                        "classification": classification,
                        "legacy_hosts": legacy_hosts,
                        "report_status": item.get("status"),
                        "action_routes": item.get("action_routes"),
                        "report_get_started_url": gs_urls[0],
                        "report_no_match_url": nm_urls[0],
                        "flow_expected": bool(flow_links),
                        "report_flow_urls": sorted(link["url"] for link in flow_links),
                        "report_topology": (item.get("auto_principal_drip") or {}).get("topology"),
                        "report_flow_href": (item.get("auto_principal_drip") or {}).get("edit_href"),
                        "source_file": str(source),
                    }
                )
    page_ids = [row["page"]["page_id"] for row in rows]
    counts = Counter(row["classification"] for row in rows)
    flow_count = sum(row["flow_expected"] for row in rows)
    if len(rows) != EXPECTED["pages"] or len(set(page_ids)) != EXPECTED["pages"]:
        raise RuntimeError(f"scope cardinality mismatch rows={len(rows)} unique={len(set(page_ids))}")
    if counts != Counter({"US-CC-EN": EXPECTED["US-CC-EN"], "US-CC-ES": EXPECTED["US-CC-ES"]}):
        raise RuntimeError(f"classification counts mismatch: {dict(counts)}")
    if flow_count != EXPECTED["with_flow"] or len(rows) - flow_count != EXPECTED["actions_only"]:
        raise RuntimeError(f"flow counts mismatch with={flow_count} actions_only={len(rows)-flow_count}")
    return rows


def load_state() -> dict:
    if not STATE_PATH.exists():
        raise RuntimeError(f"state missing; run init first: {STATE_PATH}")
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    run_dir = Path(state["run_dir"])
    if not run_dir.is_dir():
        raise RuntimeError(f"run dir missing: {run_dir}")
    return state


def run_dir() -> Path:
    return Path(load_state()["run_dir"])


def manifest_path(page_id: str) -> Path:
    return run_dir() / "pages" / str(page_id) / "manifest.json"


def credentials(login: str) -> tuple[str, str | None]:
    mapped, missing, errors, _ = resolver.resolve_dtr_items([login], VAULT)
    if missing or errors or login not in mapped:
        raise RuntimeError(f"credential resolution failed login={login} missing={missing} errors={errors}")
    item = resolver.get_item_json(mapped[login]["id"], VAULT)
    secret = resolver.field_value(item, "credential", "password", required=True)
    return secret, mapped[login].get("title")


async def login_context(browser, login: str, password: str):
    context = await browser.new_context(viewport={"width": 1920, "height": 1200})
    page = await context.new_page()
    await page.goto(BOT_LIST, wait_until="domcontentloaded", timeout=90000)
    if "/home/login" in page.url:
        inputs = page.locator("input:visible")
        await inputs.nth(0).fill(login)
        await inputs.nth(1).fill(password)
        await page.locator("button:visible,input[type=submit]:visible").last.click()
        await page.wait_for_timeout(2800)
    if "/home/login" in page.url:
        await context.close()
        raise RuntimeError(f"DTR login failed: {login}")
    return context, page


async def account_inventory(page) -> list[dict]:
    raw = await page.evaluate(
        r"""()=>Array.from(document.querySelectorAll('a.account_switch[data-id],.account_switch[data-id]'))
        .map(e=>({account_id:e.getAttribute('data-id')||'',account_name:(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim()}))
        .filter(x=>x.account_id)"""
    )
    result: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in raw:
        key = (str(item["account_id"]), clean(item["account_name"]))
        if key not in seen:
            seen.add(key)
            result.append({"account_id": key[0], "account_name": key[1]})
    return result


async def switch_account(page, account_id: str, account_name: str) -> None:
    await page.goto(BOT_LIST, wait_until="domcontentloaded", timeout=90000)
    inventory = await account_inventory(page)
    hits = [
        item
        for item in inventory
        if item["account_id"] == str(account_id) and item["account_name"] == clean(account_name)
    ]
    if len(hits) != 1:
        raise RuntimeError(
            f"account identity mismatch id={account_id} name={account_name!r} hits={hits}"
        )
    await page.evaluate(
        """id=>new Promise((resolve,reject)=>{$.post(
        'https://digitaltrchat.com/social_accounts/fb_rx_account_switch',
        {id:String(id)}).done(resolve).fail((xhr,status,error)=>reject(new Error('switch '+xhr.status+' '+status+' '+error)))})""",
        str(account_id),
    )
    await page.goto(BOT_LIST, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(1000)


async def page_inventory(page) -> list[dict]:
    raw = await page.evaluate(
        r"""()=>Array.from(document.querySelectorAll('li.page_list_item'))
        .map((li,index)=>({ui_order:index+1,text:(li.innerText||li.textContent||'').replace(/\s+/g,' ').trim()}))"""
    )
    result = []
    for item in raw:
        match = re.search(r"^(.*?)\s+#(\d+)\s+-\s+(\d+)\s*$", item["text"])
        if match:
            result.append(
                {
                    "ui_order": item["ui_order"],
                    "page_name": clean(match.group(1)),
                    "page_id": match.group(2),
                    "fb_page_id": match.group(3),
                }
            )
    return result


async def discover_action_hrefs(nav, row: dict) -> dict:
    last = "not attempted"
    for attempt in range(1, 4):
        selector_text = f"#{row['page_id']} - {row['fb_page_id']}"
        target = nav.locator("li.page_list_item").filter(has_text=selector_text)
        if await target.count() != 1:
            return {"error": f"page_list_count={await target.count()}"}
        try:
            async with nav.expect_response(lambda response: "get_page_details" in response.url, timeout=15000):
                await target.first.click()
        except PlaywrightTimeoutError:
            await target.first.click()
        await nav.wait_for_timeout(2200 * attempt)
        hrefs = await nav.evaluate(
            """()=>Array.from(document.querySelectorAll('a[href*="/messenger_bot/edit_bot/"]')).map(a=>a.href||'')"""
        )
        get_started = list(dict.fromkeys(value for value in hrefs if value.endswith("/getstart")))
        no_match = list(dict.fromkeys(value for value in hrefs if value.endswith("/nomatch")))
        if len(get_started) == 1 and len(no_match) == 1:
            return {
                "get_started_href": get_started[0],
                "no_match_href": no_match[0],
                "attempt": attempt,
            }
        last = f"action_links gs={len(get_started)} nm={len(no_match)}"
        await nav.reload(wait_until="domcontentloaded", timeout=90000)
        await nav.wait_for_timeout(700)
    return {"error": last}


async def extract_action_page(page, href: str, row: dict) -> dict:
    await page.goto(href, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(1300)
    identity = await page.evaluate(
        """()=>Object.fromEntries(['id','page_id','page_table_id','keyword_type','bot_name']
        .map(id=>[id,document.getElementById(id)?.value||'']))"""
    )
    fields = await page.evaluate(
        """()=>Array.from(document.querySelectorAll('input,textarea,select')).map(e=>({
        tag:e.tagName,id:e.id||'',name:e.name||'',type:e.type||'',
        value:e.type==='password'?'[REDACTED]':e.value||'',checked:!!e.checked,
        disabled:!!e.disabled,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}))"""
    )
    http_fields = [
        field
        for field in fields
        if field["visible"]
        and isinstance(field.get("value"), str)
        and field["value"].startswith(("http://", "https://"))
    ]
    return {
        "href": href,
        "identity": identity,
        "identity_ok": identity.get("page_table_id") == row["page_id"]
        and identity.get("page_id") == row["fb_page_id"],
        "http_fields": http_fields,
        "actual_url": http_fields[0]["value"] if len(http_fields) == 1 else "",
        "stable_fields": [field for field in fields if not field.get("id", "").startswith("ajax-upload-id-")],
    }


async def action_read(context, href: str, row: dict) -> dict:
    page = await context.new_page()
    try:
        return await extract_action_page(page, href, row)
    finally:
        await page.close()


async def resolve_actions(nav, context, scope_row: dict) -> tuple[dict, dict, dict]:
    row = scope_row["page"]
    routes = scope_row.get("action_routes") or {}
    if routes.get("get_started_href") and routes.get("no_match_href"):
        gs, nm = await asyncio.gather(
            action_read(context, routes["get_started_href"], row),
            action_read(context, routes["no_match_href"], row),
        )
        if gs["identity_ok"] and nm["identity_ok"]:
            return gs, nm, routes
    discovered = await discover_action_hrefs(nav, row)
    if "error" in discovered:
        raise RuntimeError(discovered["error"])
    gs, nm = await asyncio.gather(
        action_read(context, discovered["get_started_href"], row),
        action_read(context, discovered["no_match_href"], row),
    )
    if not gs["identity_ok"] or not nm["identity_ok"]:
        raise RuntimeError("action editor identity mismatch after discovery")
    return gs, nm, discovered


async def discover_flow_href(nav, row: dict, require_present: bool) -> str | None:
    manager = BASE + f"/visual_flow_builder/flowbuilder_manager/{row['page_id']}/1"
    await nav.goto(manager, wait_until="domcontentloaded", timeout=90000)
    exact = nav.get_by_text(FLOW_NAME, exact=True)
    try:
        await exact.wait_for(state="visible", timeout=12000)
    except Exception:
        await nav.wait_for_timeout(1200)
    count = await exact.count()
    if not require_present:
        if count == 0:
            return None
        raise RuntimeError(f"flow appeared since audit count={count}")
    if count != 1:
        raise RuntimeError(f"flow count={count}")
    row_locator = nav.locator("tr").filter(has=exact).first
    edit = row_locator.locator('a[title="Edit"]')
    if await edit.count() != 1:
        raise RuntimeError(f"flow edit count={await edit.count()}")
    href = await edit.get_attribute("href")
    classes = await edit.get_attribute("class") or ""
    if (
        "/visual_flow_builder/edit_builder_data/" not in (href or "")
        or "btn-outline-warning" not in classes
        or "btn-outline-danger" in classes
        or "delete_data" in classes
    ):
        raise RuntimeError("unsafe flow edit selector")
    return href


async def flow_read(context, href: str, row: dict) -> dict:
    page = await context.new_page()
    try:
        await page.goto(href, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_function("typeof window.data==='string' && window.data.length>2", timeout=90000)
        meta = await page.evaluate(
            """()=>{const x=window.xitFlowBuilderData||{};return {
            page_table_id:String(x.page_table_id||''),builder_table_id:String(x.builder_table_id||'')}}"""
        )
        if meta["page_table_id"] != str(row["page_id"]):
            raise RuntimeError(
                f"flow page identity mismatch expected={row['page_id']} actual={meta['page_table_id']}"
            )
        return {
            "href": href,
            "meta": meta,
            "graph": json.loads(await page.evaluate("window.data")),
        }
    finally:
        await page.close()


def build_graph_plan(graph: dict, catalog: dict[str, str]) -> tuple[list[dict], dict]:
    topo = topology(graph)
    if topo["starts"] != 1 or topo["disconnected"] != 0 or topo["reachable"] != topo["nodes"]:
        raise RuntimeError(f"graph topology invalid: {topo}")
    links = semantic_flow_links(graph)
    mods = []
    prepared = copy.deepcopy(graph)
    for link in links:
        target = target_for(catalog, link["semantic"])
        mod = {
            "node_id": link["node_id"],
            "node_type": link["node_type"],
            "field": link["field"],
            "semantic": link["semantic"],
            "semantic_authority": link["semantic_authority"],
            "before": link["url"],
            "target": target,
        }
        mods.append(mod)
        node_lookup(prepared, link["node_id"])["data"][link["field"]] = target
    if topology(prepared) != topo:
        raise RuntimeError("prepared graph topology changed")
    expected_paths = {
        ("nodes", str(mod["node_id"]), "data", mod["field"])
        for mod in mods
        if mod["before"] != mod["target"]
    }
    actual_paths = set(changed_paths(graph, prepared))
    if actual_paths != expected_paths:
        raise RuntimeError(
            f"prepared graph diff mismatch expected={len(expected_paths)} actual={len(actual_paths)}"
        )
    return mods, prepared


def flow_state(graph: dict, manifest: dict) -> str:
    mods = manifest.get("mods") or []
    if not mods:
        return "absent"
    if sha(scrub_graph_urls(graph, mods)) != manifest["normalized_non_url_hash"]:
        return "third_non_url_drift"
    current = []
    for mod in mods:
        value = node_lookup(graph, mod["node_id"])["data"].get(mod["field"])
        if value == mod["before"]:
            current.append("before")
        elif value == mod["target"]:
            current.append("target")
        else:
            current.append("third")
    states = set(current)
    if states == {"before"}:
        return "before"
    if states == {"target"}:
        return "target"
    if "third" in states:
        return "third_url_drift"
    return "mixed_before_target"


def build_manifest(scope_row: dict, gs: dict, nm: dict, routes: dict, flow: dict | None) -> tuple[dict, dict | None]:
    catalog = catalogs()[scope_row["classification"]]
    gs_target = catalog["m0-1"]
    nm_target = catalog["nm"]
    if len(gs["http_fields"]) != 1 or len(nm["http_fields"]) != 1:
        raise RuntimeError(
            f"action HTTP cardinality gs={len(gs['http_fields'])} nm={len(nm['http_fields'])}"
        )
    if gs["actual_url"] != scope_row["report_get_started_url"] and not action_target_ok(
        gs["actual_url"], gs_target
    ):
        raise RuntimeError("Get Started drift from audit/target")
    if nm["actual_url"] != scope_row["report_no_match_url"] and not action_target_ok(
        nm["actual_url"], nm_target
    ):
        raise RuntimeError("No Match drift from audit/target")

    manifest = {
        "status": "qualified",
        "qualified_at_et": now_et(),
        "authorization_message_id": AUTH_MESSAGE_ID,
        "thread_id": THREAD_ID,
        "login": scope_row["login"],
        "account_id": scope_row["account_id"],
        "account_name": scope_row["account_name"],
        "page": scope_row["page"],
        "classification": scope_row["classification"],
        "classification_authority": "Rodolfo explicit legacy card/tarjeta mapping message 1545261608769687562",
        "legacy_hosts": scope_row["legacy_hosts"],
        "surfaces": ["get_started", "no_match"]
        + (["auto_principal_drip_existing_urls"] if scope_row["flow_expected"] else []),
        "out_of_scope_unchanged": ["persistent_menu", "messages", "timing", "topology", "buttons", "media"],
        "action_routes": routes,
        "get_started": gs,
        "no_match": nm,
        "targets": {"get_started": gs_target, "no_match": nm_target},
        "flow_expected": scope_row["flow_expected"],
        "mods": [],
        "topology": None,
        "flow_href": None,
        "before_graph_hash": None,
        "prepared_graph_hash": None,
        "normalized_non_url_hash": None,
        "planned_action_changes": int(not action_target_ok(gs["actual_url"], gs_target))
        + int(not action_target_ok(nm["actual_url"], nm_target)),
        "planned_flow_changes": 0,
        "source_audit": scope_row["source_file"],
    }
    prepared = None
    if scope_row["flow_expected"]:
        if flow is None:
            raise RuntimeError("expected flow missing")
        graph = flow["graph"]
        current_urls = sorted(link["url"] for link in business_links(graph))
        report_urls = scope_row["report_flow_urls"]
        mods, prepared = build_graph_plan(graph, catalog)
        all_target = all(mod["before"] == mod["target"] for mod in mods)
        if current_urls != report_urls and not all_target:
            raise RuntimeError("flow URLs drift from audit and are not fully target")
        topo = topology(graph)
        if scope_row.get("report_topology") and current_urls == report_urls and topo != scope_row["report_topology"]:
            raise RuntimeError(f"flow topology drift audit={scope_row['report_topology']} live={topo}")
        manifest.update(
            {
                "flow_href": flow["href"],
                "flow_meta": flow["meta"],
                "topology": topo,
                "mods": mods,
                "before_graph_hash": sha(graph_core(graph)),
                "prepared_graph_hash": sha(graph_core(prepared)),
                "normalized_non_url_hash": sha(scrub_graph_urls(graph, mods)),
                "planned_flow_changes": sum(mod["before"] != mod["target"] for mod in mods),
            }
        )
    return manifest, prepared


async def init_run() -> None:
    scope = build_scope()
    catalogs_payload = catalogs()
    stamp = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%dT%H%M%S%z")
    target_dir = BACKUP_BASE / f"dtr-legacy-keitaro-smart-routing-{stamp}"
    target_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(target_dir, 0o700)
    source_hashes = {str(audit_file(login)): sha(json.loads(audit_file(login).read_text(encoding="utf-8"))) for login in LOGINS}
    scope_payload = {
        "created_at_et": now_et(),
        "authorization_message_id": AUTH_MESSAGE_ID,
        "thread_id": THREAD_ID,
        "requested_pages": len(scope),
        "source_hashes": source_hashes,
        "rows": scope,
    }
    atomic_json(target_dir / "scope.json", scope_payload, mode=0o600)
    atomic_json(target_dir / "catalogs.json", catalogs_payload, mode=0o600)
    state = {
        "status": "initialized",
        "created_at_et": now_et(),
        "updated_at_et": now_et(),
        "authorization_message_id": AUTH_MESSAGE_ID,
        "thread_id": THREAD_ID,
        "run_dir": str(target_dir),
        "requested_pages": len(scope),
        "qualified_pages": 0,
        "applied_pages": 0,
        "verified_pages": 0,
    }
    atomic_json(STATE_PATH, state, mode=0o600)
    print(json.dumps({"status": "initialized", "run_dir": str(target_dir), "pages": len(scope)}, ensure_ascii=False))


def scope_rows() -> list[dict]:
    return json.loads((run_dir() / "scope.json").read_text(encoding="utf-8"))["rows"]


async def qualify_login(login: str) -> None:
    if login not in LOGINS:
        raise RuntimeError(f"login outside authorized scope: {login}")
    rows = [row for row in scope_rows() if row["login"] == login]
    password, item_title = credentials(login)
    results: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context, nav = await login_context(browser, login, password)
        try:
            inventory = await account_inventory(nav)
            expected_accounts = {(row["account_id"], clean(row["account_name"])) for row in rows}
            actual_accounts = {(row["account_id"], clean(row["account_name"])) for row in inventory}
            missing_accounts = sorted(expected_accounts - actual_accounts)
            if missing_accounts:
                raise RuntimeError(f"missing authorized accounts: {missing_accounts}")
            grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
            for row in rows:
                grouped[(row["account_id"], row["account_name"])].append(row)
            position = 0
            for (account_id, account_name), account_rows in grouped.items():
                await switch_account(nav, account_id, account_name)
                live_pages = await page_inventory(nav)
                by_id = {page["page_id"]: page for page in live_pages}
                for scope_row in account_rows:
                    position += 1
                    page_id = scope_row["page"]["page_id"]
                    page_dir = run_dir() / "pages" / page_id
                    page_dir.mkdir(parents=True, exist_ok=True)
                    os.chmod(page_dir, 0o700)
                    try:
                        live_identity = by_id.get(page_id)
                        if live_identity != scope_row["page"]:
                            raise RuntimeError(
                                f"Page identity drift expected={scope_row['page']} live={live_identity}"
                            )
                        gs, nm, routes = await resolve_actions(nav, context, scope_row)
                        flow = None
                        if scope_row["flow_expected"]:
                            href = scope_row.get("report_flow_href")
                            if href:
                                try:
                                    flow = await flow_read(context, href, scope_row["page"])
                                except Exception:
                                    href = await discover_flow_href(nav, scope_row["page"], True)
                                    if not href:
                                        raise RuntimeError("expected flow href missing after discovery")
                                    flow = await flow_read(context, href, scope_row["page"])
                            else:
                                href = await discover_flow_href(nav, scope_row["page"], True)
                                if not href:
                                    raise RuntimeError("expected flow href missing after discovery")
                                flow = await flow_read(context, href, scope_row["page"])
                        else:
                            await discover_flow_href(nav, scope_row["page"], False)
                        manifest, prepared = build_manifest(scope_row, gs, nm, routes, flow)
                        atomic_json(page_dir / "actions-before.json", {"get_started": gs, "no_match": nm}, mode=0o600)
                        if flow is not None:
                            atomic_json(page_dir / "flow-before.json", flow["graph"], mode=0o600)
                            atomic_json(page_dir / "flow-prepared.json", prepared, mode=0o600)
                        atomic_json(page_dir / "manifest.json", manifest, mode=0o600)
                        result = {
                            "page_id": page_id,
                            "status": "qualified",
                            "classification": manifest["classification"],
                            "flow_expected": manifest["flow_expected"],
                            "planned_flow_changes": manifest["planned_flow_changes"],
                            "planned_action_changes": manifest["planned_action_changes"],
                        }
                    except Exception as error:
                        result = {
                            "page_id": page_id,
                            "status": "failed",
                            "error": f"{type(error).__name__}:{str(error)[:600]}",
                        }
                        atomic_json(page_dir / "qualification-error.json", result, mode=0o600)
                    results.append(result)
                    print(
                        json.dumps(
                            {
                                "stage": "qualify",
                                "login": login,
                                "progress": f"{position}/{len(rows)}",
                                **result,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
        finally:
            await context.close()
            await browser.close()
    summary = {
        "login": login,
        "credential_item_title": item_title,
        "requested": len(rows),
        "qualified": sum(row["status"] == "qualified" for row in results),
        "failed": sum(row["status"] != "qualified" for row in results),
        "results": results,
        "finished_at_et": now_et(),
    }
    atomic_json(run_dir() / f"qualification-{login.replace('@', '_at_')}.json", summary, mode=0o600)
    print(json.dumps({"stage": "qualify_login_done", **{k: summary[k] for k in ("login", "requested", "qualified", "failed")}}, ensure_ascii=False))


def finalize_qualification() -> None:
    rows = scope_rows()
    results = []
    for row in rows:
        path = manifest_path(row["page"]["page_id"])
        if path.exists():
            manifest = json.loads(path.read_text(encoding="utf-8"))
            status = "qualified" if manifest.get("status") == "qualified" else "failed"
            results.append({"page_id": row["page"]["page_id"], "status": status})
        else:
            error_path = path.parent / "qualification-error.json"
            error = json.loads(error_path.read_text(encoding="utf-8")) if error_path.exists() else None
            results.append(
                {
                    "page_id": row["page"]["page_id"],
                    "status": "failed",
                    "error": (error or {}).get("error", "manifest missing"),
                }
            )
    summary = {
        "requested": len(rows),
        "qualified": sum(row["status"] == "qualified" for row in results),
        "failed": sum(row["status"] != "qualified" for row in results),
        "classification": dict(Counter(row["classification"] for row in rows)),
        "with_flow": sum(row["flow_expected"] for row in rows),
        "actions_only": sum(not row["flow_expected"] for row in rows),
    }
    payload = {"created_at_et": now_et(), "summary": summary, "results": results}
    atomic_json(run_dir() / "qualification.json", payload, mode=0o600)
    if summary != {
        "requested": 116,
        "qualified": 116,
        "failed": 0,
        "classification": {"US-CC-EN": 67, "US-CC-ES": 49},
        "with_flow": 110,
        "actions_only": 6,
    }:
        raise RuntimeError(f"qualification incomplete: {summary}")
    state = load_state()
    state.update({"status": "qualified", "updated_at_et": now_et(), "qualified_pages": 116})
    atomic_json(STATE_PATH, state, mode=0o600)
    print(json.dumps({"stage": "qualification_complete", "summary": summary}, ensure_ascii=False))


async def graph_write(context, manifest: dict, current_graph: dict, reverse: bool = False) -> dict:
    mods = copy.deepcopy(manifest["mods"])
    if reverse:
        mods = [{**mod, "before": mod["target"], "target": mod["before"]} for mod in mods]
    expected_before = current_graph
    prepared = copy.deepcopy(current_graph)
    active_mods = []
    for mod in mods:
        node = node_lookup(prepared, mod["node_id"])
        actual = node["data"].get(mod["field"])
        if actual != mod["before"]:
            raise RuntimeError(f"graph write drift node={mod['node_id']} field={mod['field']}")
        if actual != mod["target"]:
            node["data"][mod["field"]] = mod["target"]
            active_mods.append(mod)
    if not active_mods:
        return {"method": "zero_diff", "changed": [], "after_hash": sha(graph_core(current_graph))}
    if sha(scrub_graph_urls(prepared, manifest["mods"])) != manifest["normalized_non_url_hash"]:
        raise RuntimeError("graph prepared non-URL invariant mismatch")

    page = await context.new_page()
    responses: list[dict] = []
    page.on(
        "response",
        lambda response: responses.append(
            {"method": response.request.method, "url": response.url, "status": response.status}
        )
        if response.request.method == "POST" and "visual_flow_builder" in response.url
        else None,
    )
    try:
        await page.goto(manifest["flow_href"], wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_function(
            "typeof window.data==='string' && document.querySelector('.node')", timeout=90000
        )
        browser_before = json.loads(await page.evaluate("window.data"))
        if sha(graph_core(browser_before)) != sha(graph_core(expected_before)):
            raise RuntimeError("flow editor changed between prewrite read and editor")
        output = await page.evaluate(
            """mods=>{const el=document.querySelector('.node');const editor=el&&el.__vue__&&el.__vue__.editor;
            if(!editor)throw new Error('editor unavailable');const changed=[];
            for(const m of mods){const n=editor.nodes.find(x=>String(x.id)===String(m.node_id));
            if(!n)throw new Error('node missing '+m.node_id);if(!(m.field in n.data))throw new Error('field missing '+m.field);
            if(n.data[m.field]!==m.before)throw new Error('live drift '+m.node_id+' '+m.field);
            changed.push({node_id:String(n.id),field:m.field,before:n.data[m.field],after:m.target});n.data[m.field]=m.target;}
            return {graph:editor.toJSON(),changed};}""",
            active_mods,
        )
        if sha(graph_core(output["graph"])) != sha(graph_core(prepared)):
            raise RuntimeError("browser unsaved graph differs from prepared graph")
        save = page.locator(".action-button-save")
        if await save.count() != 1 or await page.locator(
            ".action-button-save.btn-outline-danger,.action-button-save.delete_data"
        ).count():
            raise RuntimeError("unsafe Save selector")
        await save.click()
        await page.wait_for_timeout(5000)
        await page.reload(wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_function("typeof window.data==='string' && window.data.length>2", timeout=90000)
        live = json.loads(await page.evaluate("window.data"))
        target_ok = sha(graph_core(live)) == sha(graph_core(prepared))
        before_ok = sha(graph_core(live)) == sha(graph_core(expected_before))
        method = "ui_save"
        direct_response = None
        if not target_ok:
            if not before_ok:
                raise RuntimeError("graph Save produced mixed/unknown state")
            meta = await page.evaluate(
                """()=>{const x=window.xitFlowBuilderData;if(!x)throw new Error('xitFlowBuilderData missing');
                return {page_table_id:String(x.page_table_id||''),builder_table_id:String(x.builder_table_id||''),
                instagram_addon:x.instagram_addon,base_url:x.base_url||''}}"""
            )
            if meta["page_table_id"] != str(manifest["page"]["page_id"]):
                raise RuntimeError("direct Save page identity mismatch")
            direct_response = await page.evaluate(
                """graph=>new Promise((resolve,reject)=>{const x=window.xitFlowBuilderData;
                $.ajax({method:'POST',dataType:'JSON',url:x.base_url+'visual_flow_builder/flowbuilder_submit',
                data:{page_table_id:x.page_table_id,builder_table_id:x.builder_table_id,
                instagram_bot_addon:x.instagram_addon,flow_data:JSON.stringify(graph)},success:resolve,
                error:(xhr,status,error)=>reject(new Error('http '+xhr.status+' '+status+' '+error))})})""",
                output["graph"],
            )
            if isinstance(direct_response, dict) and str(direct_response.get("status", "1")) == "0":
                raise RuntimeError(f"direct Save rejected: {direct_response}")
            await page.reload(wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_function("typeof window.data==='string' && window.data.length>2", timeout=90000)
            live = json.loads(await page.evaluate("window.data"))
            if sha(graph_core(live)) != sha(graph_core(prepared)):
                raise RuntimeError("direct Save readback mismatch")
            method = "canonical_flowbuilder_submit_fallback"
        return {
            "method": method,
            "changed": output["changed"],
            "responses": responses,
            "direct_response": direct_response,
            "after_hash": sha(graph_core(live)),
        }
    finally:
        await page.close()


async def action_write(context, state: dict, row: dict, target_base: str, expected_values: set[str]) -> dict:
    page = await context.new_page()
    responses: list[dict] = []
    page.on(
        "response",
        lambda response: responses.append(
            {"method": response.request.method, "url": response.url, "status": response.status}
        )
        if response.request.method == "POST" and "messenger_bot" in response.url
        else None,
    )
    try:
        live = await extract_action_page(page, state["href"], row)
        if not live["identity_ok"]:
            raise RuntimeError("action write identity mismatch")
        if live["actual_url"] not in expected_values:
            raise RuntimeError("action write URL drift")
        candidates = []
        for index in range(await page.locator("input:visible").count()):
            element = page.locator("input:visible").nth(index)
            value = await element.input_value()
            if value.startswith(("http://", "https://")):
                candidates.append(element)
        if len(candidates) != 1:
            raise RuntimeError(f"action write URL field count={len(candidates)}")
        before = live["actual_url"]
        await candidates[0].fill(target_base)
        submit = page.locator("#submit:visible")
        if await submit.count() != 1:
            raise RuntimeError(f"action Update selector count={await submit.count()}")
        await submit.click()
        await page.wait_for_timeout(4500)
        readback = await extract_action_page(page, state["href"], row)
        if not readback["identity_ok"] or not action_target_ok(readback["actual_url"], target_base):
            raise RuntimeError("action immediate readback mismatch")
        return {
            "before": before,
            "input_target": target_base,
            "persisted": readback["actual_url"],
            "responses": responses,
        }
    finally:
        await page.close()


async def verify_manifest(browser, password: str, manifest: dict) -> dict:
    context, nav = await login_context(browser, manifest["login"], password)
    try:
        await switch_account(nav, manifest["account_id"], manifest["account_name"])
        gs, nm = await asyncio.gather(
            action_read(context, manifest["get_started"]["href"], manifest["page"]),
            action_read(context, manifest["no_match"]["href"], manifest["page"]),
        )
        actions_ok = (
            gs["identity_ok"]
            and nm["identity_ok"]
            and action_target_ok(gs["actual_url"], manifest["targets"]["get_started"])
            and action_target_ok(nm["actual_url"], manifest["targets"]["no_match"])
            and stable_action(gs, manifest["get_started"])
            == stable_action(manifest["get_started"], manifest["get_started"])
            and stable_action(nm, manifest["no_match"])
            == stable_action(manifest["no_match"], manifest["no_match"])
        )
        if manifest["flow_expected"]:
            flow = await flow_read(context, manifest["flow_href"], manifest["page"])
            graph = flow["graph"]
            flow_result = {
                "present": True,
                "state": flow_state(graph, manifest),
                "topology": topology(graph),
                "graph_hash": sha(graph_core(graph)),
                "target_fields": sum(
                    node_lookup(graph, mod["node_id"])["data"].get(mod["field"])
                    == mod["target"]
                    for mod in manifest["mods"]
                ),
                "fields": len(manifest["mods"]),
            }
            flow_ok = flow_result["state"] == "target" and flow_result["topology"] == manifest["topology"]
        else:
            absent = await discover_flow_href(nav, manifest["page"], False)
            flow_result = {"present": absent is not None, "state": "absent" if absent is None else "appeared"}
            flow_ok = absent is None
        status = "verified" if actions_ok and flow_ok else "failed"
        return {
            "status": status,
            "actions_ok": actions_ok,
            "get_started_url": gs["actual_url"],
            "no_match_url": nm["actual_url"],
            "flow_ok": flow_ok,
            "flow": flow_result,
            "verified_at_et": now_et(),
        }
    finally:
        await context.close()


async def rollback_page(context, manifest: dict, written: list[str]) -> dict:
    result = {"attempted": bool(written), "steps": []}
    for surface in reversed(written):
        try:
            if surface == "no_match":
                current = await action_read(context, manifest["no_match"]["href"], manifest["page"])
                step = await action_write(
                    context,
                    current,
                    manifest["page"],
                    manifest["no_match"]["actual_url"],
                    action_target_variants(manifest["targets"]["no_match"]),
                )
            elif surface == "get_started":
                current = await action_read(context, manifest["get_started"]["href"], manifest["page"])
                step = await action_write(
                    context,
                    current,
                    manifest["page"],
                    manifest["get_started"]["actual_url"],
                    action_target_variants(manifest["targets"]["get_started"]),
                )
            elif surface == "flow":
                current = await flow_read(context, manifest["flow_href"], manifest["page"])
                step = await graph_write(context, manifest, current["graph"], reverse=True)
            else:
                raise RuntimeError(f"unknown rollback surface {surface}")
            result["steps"].append({"surface": surface, "status": "restored", "result": step})
        except Exception as error:
            result["steps"].append(
                {"surface": surface, "status": "failed", "error": f"{type(error).__name__}:{error}"}
            )
    result["status"] = "completed" if all(step["status"] == "restored" for step in result["steps"]) else "failed"
    return result


async def apply_pages(page_ids: list[str]) -> None:
    qualification = json.loads((run_dir() / "qualification.json").read_text(encoding="utf-8"))
    if qualification.get("summary", {}).get("qualified") != 116 or qualification.get("summary", {}).get("failed") != 0:
        raise RuntimeError("complete 116/116 qualification required before writes")
    if len(page_ids) != len(set(page_ids)):
        raise RuntimeError("duplicate Page IDs in apply request")
    manifests = {row["page"]["page_id"]: json.loads(manifest_path(row["page"]["page_id"]).read_text(encoding="utf-8")) for row in scope_rows()}
    missing = sorted(set(page_ids) - set(manifests))
    if missing:
        raise RuntimeError(f"Page IDs outside qualified scope: {missing}")

    grouped_credentials: dict[str, tuple[str, str | None]] = {}
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        for index, page_id in enumerate(page_ids, 1):
            manifest = manifests[page_id]
            page_dir = manifest_path(page_id).parent
            result_path = page_dir / "apply-result.json"
            if result_path.exists():
                prior = json.loads(result_path.read_text(encoding="utf-8"))
                if prior.get("status") == "success":
                    results.append(prior)
                    print(json.dumps({"stage": "apply", "progress": f"{index}/{len(page_ids)}", "page_id": page_id, "status": "resumed-success"}), flush=True)
                    continue
            if manifest["login"] not in grouped_credentials:
                grouped_credentials[manifest["login"]] = credentials(manifest["login"])
            password = grouped_credentials[manifest["login"]][0]
            result = {
                "page": manifest["page"],
                "login": manifest["login"],
                "account_id": manifest["account_id"],
                "classification": manifest["classification"],
                "started_at_et": now_et(),
                "status": "started",
                "writes": {},
                "written_surfaces": [],
                "rollback": {"attempted": False, "steps": []},
            }
            context = None
            try:
                context, nav = await login_context(browser, manifest["login"], password)
                await switch_account(nav, manifest["account_id"], manifest["account_name"])
                gs, nm = await asyncio.gather(
                    action_read(context, manifest["get_started"]["href"], manifest["page"]),
                    action_read(context, manifest["no_match"]["href"], manifest["page"]),
                )
                if not gs["identity_ok"] or not nm["identity_ok"]:
                    raise RuntimeError("prewrite action identity mismatch")
                if stable_action(gs, manifest["get_started"]) != stable_action(
                    manifest["get_started"], manifest["get_started"]
                ) or stable_action(nm, manifest["no_match"]) != stable_action(
                    manifest["no_match"], manifest["no_match"]
                ):
                    raise RuntimeError("prewrite action non-URL drift")
                if gs["actual_url"] not in {manifest["get_started"]["actual_url"]} | action_target_variants(
                    manifest["targets"]["get_started"]
                ):
                    raise RuntimeError("prewrite Get Started third value")
                if nm["actual_url"] not in {manifest["no_match"]["actual_url"]} | action_target_variants(
                    manifest["targets"]["no_match"]
                ):
                    raise RuntimeError("prewrite No Match third value")

                if manifest["flow_expected"]:
                    flow = await flow_read(context, manifest["flow_href"], manifest["page"])
                    state = flow_state(flow["graph"], manifest)
                    if state not in {"before", "target"}:
                        raise RuntimeError(f"prewrite flow state={state}")
                    if state == "before" and manifest["planned_flow_changes"]:
                        result["writes"]["flow"] = await graph_write(context, manifest, flow["graph"])
                        result["written_surfaces"].append("flow")
                else:
                    await discover_flow_href(nav, manifest["page"], False)

                if not action_target_ok(gs["actual_url"], manifest["targets"]["get_started"]):
                    result["writes"]["get_started"] = await action_write(
                        context,
                        gs,
                        manifest["page"],
                        manifest["targets"]["get_started"],
                        {manifest["get_started"]["actual_url"]},
                    )
                    result["written_surfaces"].append("get_started")
                if not action_target_ok(nm["actual_url"], manifest["targets"]["no_match"]):
                    result["writes"]["no_match"] = await action_write(
                        context,
                        nm,
                        manifest["page"],
                        manifest["targets"]["no_match"],
                        {manifest["no_match"]["actual_url"]},
                    )
                    result["written_surfaces"].append("no_match")
                await context.close()
                context = None

                verification = await verify_manifest(browser, password, manifest)
                result["independent_readback"] = verification
                if verification["status"] != "verified":
                    raise RuntimeError("independent readback mismatch")
                result["status"] = "success"
                result["finished_at_et"] = now_et()
                atomic_json(result_path, result, mode=0o600)
                results.append(result)
                print(
                    json.dumps(
                        {
                            "stage": "apply",
                            "progress": f"{index}/{len(page_ids)}",
                            "page_id": page_id,
                            "classification": manifest["classification"],
                            "status": "success",
                            "flow_fields_changed": len(result["writes"].get("flow", {}).get("changed", [])),
                            "actions_changed": sum(key in result["writes"] for key in ("get_started", "no_match")),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            except Exception as error:
                result["status"] = "failed"
                result["error"] = f"{type(error).__name__}:{str(error)[:1000]}"
                if result["written_surfaces"]:
                    try:
                        if context is None:
                            context, nav = await login_context(browser, manifest["login"], password)
                            await switch_account(nav, manifest["account_id"], manifest["account_name"])
                        result["rollback"] = await rollback_page(
                            context, manifest, result["written_surfaces"]
                        )
                    except Exception as rollback_error:
                        result["rollback"] = {
                            "attempted": True,
                            "status": "failed",
                            "steps": [],
                            "error": f"{type(rollback_error).__name__}:{rollback_error}",
                        }
                if context is not None:
                    await context.close()
                result["finished_at_et"] = now_et()
                atomic_json(result_path, result, mode=0o600)
                results.append(result)
                print(
                    json.dumps(
                        {
                            "stage": "apply",
                            "progress": f"{index}/{len(page_ids)}",
                            "page_id": page_id,
                            "status": "failed",
                            "error": result["error"],
                            "rollback": result["rollback"].get("status"),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                break
        await browser.close()
    batch = {
        "created_at_et": now_et(),
        "requested": page_ids,
        "results": [
            {
                "page_id": row["page"]["page_id"],
                "status": row["status"],
                "error": row.get("error"),
                "written_surfaces": row.get("written_surfaces"),
            }
            for row in results
        ],
        "summary": {
            "requested": len(page_ids),
            "processed": len(results),
            "success": sum(row["status"] == "success" for row in results),
            "failed": sum(row["status"] != "success" for row in results),
        },
    }
    atomic_json(
        run_dir() / f"apply-batch-{page_ids[0]}-{page_ids[-1]}.json", batch, mode=0o600
    )
    print(json.dumps({"stage": "apply_batch_done", "summary": batch["summary"]}, ensure_ascii=False))


async def verify_pages(page_ids: list[str]) -> None:
    manifests = {row["page"]["page_id"]: json.loads(manifest_path(row["page"]["page_id"]).read_text(encoding="utf-8")) for row in scope_rows()}
    if len(page_ids) != len(set(page_ids)) or not set(page_ids) <= set(manifests):
        raise RuntimeError("verify Page IDs invalid/outside scope")
    creds: dict[str, tuple[str, str | None]] = {}
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        for index, page_id in enumerate(page_ids, 1):
            manifest = manifests[page_id]
            if manifest["login"] not in creds:
                creds[manifest["login"]] = credentials(manifest["login"])
            try:
                result = await verify_manifest(browser, creds[manifest["login"]][0], manifest)
            except Exception as error:
                result = {"status": "failed", "error": f"{type(error).__name__}:{str(error)[:1000]}"}
            result["page_id"] = page_id
            atomic_json(manifest_path(page_id).parent / "final-readback.json", result, mode=0o600)
            results.append(result)
            print(
                json.dumps(
                    {
                        "stage": "verify",
                        "progress": f"{index}/{len(page_ids)}",
                        "page_id": page_id,
                        "status": result["status"],
                        "error": result.get("error"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        await browser.close()
    payload = {
        "created_at_et": now_et(),
        "requested": page_ids,
        "summary": {
            "requested": len(page_ids),
            "verified": sum(row["status"] == "verified" for row in results),
            "failed": sum(row["status"] != "verified" for row in results),
        },
        "results": results,
    }
    atomic_json(
        run_dir() / f"verify-batch-{page_ids[0]}-{page_ids[-1]}.json", payload, mode=0o600
    )
    print(json.dumps({"stage": "verify_batch_done", "summary": payload["summary"]}, ensure_ascii=False))


def final_summary() -> None:
    rows = scope_rows()
    manifests = []
    applications = []
    readbacks = []
    for row in rows:
        page_id = row["page"]["page_id"]
        page_dir = manifest_path(page_id).parent
        manifests.append(json.loads((page_dir / "manifest.json").read_text(encoding="utf-8")))
        apply_path = page_dir / "apply-result.json"
        readback_path = page_dir / "final-readback.json"
        applications.append(json.loads(apply_path.read_text(encoding="utf-8")) if apply_path.exists() else {"page": row["page"], "status": "missing"})
        readbacks.append(json.loads(readback_path.read_text(encoding="utf-8")) if readback_path.exists() else {"page_id": page_id, "status": "missing"})
    recorded_flow_occurrences = sum(
        len((item.get("writes") or {}).get("flow", {}).get("changed", []))
        for item in applications
    )
    recorded_action_occurrences = sum(
        sum(key in (item.get("writes") or {}) for key in ("get_started", "no_match"))
        for item in applications
    )
    verified_flow_occurrences = sum(
        manifest["planned_flow_changes"]
        for manifest, readback in zip(manifests, readbacks)
        if readback.get("status") == "verified"
    )
    verified_action_occurrences = sum(
        manifest["planned_action_changes"]
        for manifest, readback in zip(manifests, readbacks)
        if readback.get("status") == "verified"
    )
    recovered_pre_result_flow_pages = [
        manifest["page"]["page_id"]
        for manifest, application, readback in zip(manifests, applications, readbacks)
        if readback.get("status") == "verified"
        and manifest["planned_flow_changes"]
        > len((application.get("writes") or {}).get("flow", {}).get("changed", []))
    ]
    summary = {
        "requested_pages": len(rows),
        "qualified_pages": len(manifests),
        "apply_success_pages": sum(item.get("status") == "success" for item in applications),
        "apply_failed_or_missing_pages": sum(item.get("status") != "success" for item in applications),
        "final_verified_pages": sum(item.get("status") == "verified" for item in readbacks),
        "final_failed_or_missing_pages": sum(item.get("status") != "verified" for item in readbacks),
        "classification": dict(Counter(item["classification"] for item in manifests)),
        "flow_pages": sum(item["flow_expected"] for item in manifests),
        "actions_only_pages": sum(not item["flow_expected"] for item in manifests),
        "planned_flow_occurrences": sum(item["planned_flow_changes"] for item in manifests),
        "planned_action_occurrences": sum(item["planned_action_changes"] for item in manifests),
        "actual_flow_occurrences_changed_and_verified": verified_flow_occurrences,
        "actual_action_occurrences_changed_and_verified": verified_action_occurrences,
        "recorded_flow_write_occurrences": recorded_flow_occurrences,
        "recorded_action_write_occurrences": recorded_action_occurrences,
        "recovered_pre_result_flow_pages": recovered_pre_result_flow_pages,
        "rollback_pages": sum(bool((item.get("rollback") or {}).get("attempted")) for item in applications),
        "persistent_menu_changed": 0,
    }
    payload = {
        "created_at_et": now_et(),
        "authorization_message_id": AUTH_MESSAGE_ID,
        "thread_id": THREAD_ID,
        "summary": summary,
        "failed_apply": [item for item in applications if item.get("status") != "success"],
        "failed_readback": [item for item in readbacks if item.get("status") != "verified"],
    }
    atomic_json(run_dir() / "final-summary.json", payload, mode=0o600)
    if summary["apply_success_pages"] == 116 and summary["final_verified_pages"] == 116:
        state = load_state()
        state.update(
            {
                "status": "completed",
                "updated_at_et": now_et(),
                "applied_pages": 116,
                "verified_pages": 116,
                "final_summary": str(run_dir() / "final-summary.json"),
            }
        )
        atomic_json(STATE_PATH, state, mode=0o600)
    print(json.dumps({"stage": "final_summary", "run_dir": str(run_dir()), "summary": summary}, ensure_ascii=False, indent=2))


def list_ids(classification: str | None, pending_only: bool, limit: int | None) -> None:
    rows = scope_rows()
    result = []
    for row in rows:
        if classification and row["classification"] != classification:
            continue
        page_id = row["page"]["page_id"]
        if pending_only:
            path = manifest_path(page_id).parent / "apply-result.json"
            if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "success":
                continue
        result.append(page_id)
    if limit is not None:
        result = result[:limit]
    print("\n".join(result))


def offline_self_test() -> None:
    scope = build_scope()
    cats = catalogs()
    sample = REPO / "backups/dtr-semakin-openzed-links-20260903T161108-0400/3051/flow-before.json"
    graph = json.loads(sample.read_text(encoding="utf-8"))
    mods, prepared = build_graph_plan(graph, cats["US-CC-EN"])
    checks = {
        "scope_pages": len(scope) == 116,
        "classification_counts": Counter(row["classification"] for row in scope) == Counter({"US-CC-EN": 67, "US-CC-ES": 49}),
        "sample_topology_preserved": topology(graph) == topology(prepared),
        "sample_semantics": {mod["semantic"] for mod in mods} == set(range(16)),
        "sample_initial_structural_m0": sum(mod["semantic"] == 0 and mod["semantic_authority"] == "structural_start_path_before_sequence" for mod in mods) == 1,
        "sample_all_target_sr": all(host(mod["target"]) == "sr.openzed.com" for mod in mods),
        "catalogs_30_each": all(len(value) == 30 for value in cats.values()),
    }
    if not all(checks.values()):
        raise RuntimeError(f"self-test failed: {checks}")
    print(json.dumps({"status": "ok", "checks": checks}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    sub.add_parser("init")
    qualify = sub.add_parser("qualify-login")
    qualify.add_argument("--login", required=True, choices=LOGINS)
    sub.add_parser("finalize-qualification")
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--page-id", action="append", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--page-id", action="append", required=True)
    summary_parser = sub.add_parser("list-ids")
    summary_parser.add_argument("--classification", choices=("US-CC-EN", "US-CC-ES"))
    summary_parser.add_argument("--pending-only", action="store_true")
    summary_parser.add_argument("--limit", type=int)
    sub.add_parser("final-summary")
    args = parser.parse_args()

    if args.command == "self-test":
        offline_self_test()
    elif args.command == "init":
        asyncio.run(init_run())
    elif args.command == "qualify-login":
        asyncio.run(qualify_login(args.login))
    elif args.command == "finalize-qualification":
        finalize_qualification()
    elif args.command == "apply":
        asyncio.run(apply_pages(args.page_id))
    elif args.command == "verify":
        asyncio.run(verify_pages(args.page_id))
    elif args.command == "list-ids":
        list_ids(args.classification, args.pending_only, args.limit)
    elif args.command == "final-summary":
        final_summary()


if __name__ == "__main__":
    main()
