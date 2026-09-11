#!/usr/bin/env python3
"""Daily fail-closed GAM mailbox intake and finance-dashboard import."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import email
import fcntl
import hashlib
import imaplib
import json
import os
import pathlib
import re
import shlex
import shutil
import ssl
import subprocess
import sys
from email import policy
from email.utils import parseaddr
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path("/root/mgs-agent")
CONTRACT = REPO / "data/finance-gam-revenue-contract.json"
STATE = REPO / "data/finance-gam-revenue-state.json"
LOCK = ROOT / "private/gam-revenue-sync.lock"
QUOTE_LOCK = ROOT / "private/quote-sync.lock"
RUNS = ROOT / "private/gam-email-runs"
TZ = ZoneInfo("America/New_York")
TARGET = "/home/mgsfinance/releases/pg-auth-1545934831664242748"
NODE = "/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node"
PG_BIN = "/opt/mgs-postgresql18/usr/lib/postgresql/18/bin"
PG_ENV = "env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu "
PG = "sudo -n -u mgs_pg " + PG_ENV + PG_BIN + "/"
SOCKET = "/run/mgs-postgresql18"

sys.path.insert(0, str(REPO / "scripts"))
from mgs_google_workspace_auth import load_env  # type: ignore[import-not-found]

load_env()
sys.path.insert(0, str(ROOT / "deploy"))
from runcloud_ops import ssh  # type: ignore[import-not-found]

from gam_revenue import REPORTS, build_plan, inspect_workbook


def atomic_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def read_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def credential(contract: dict) -> tuple[str, str]:
    ref = contract["mailbox"]["credential_ref"]
    result = subprocess.run(["op", "item", "get", ref["item_id"], "--vault", ref["vault_id"], "--format=json"], text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError("1Password mailbox lookup failed")
    fields = json.loads(result.stdout).get("fields", [])
    get = lambda identity: next(str(field.get("value", "")) for field in fields if field.get("id") == identity)
    username, password = get("username"), get("password")
    if username != contract["mailbox"]["address"] or not password:
        raise RuntimeError("mailbox credential identity mismatch")
    return username, password


def fetch_candidates(contract: dict, run_dir: pathlib.Path) -> list[dict]:
    username, password = credential(contract)
    box = contract["mailbox"]
    client = imaplib.IMAP4_SSL(box["host"], box["port"], ssl_context=ssl.create_default_context(), timeout=30)
    candidates = []
    try:
        client.login(username, password)
        status, _ = client.select(box["folder"], readonly=True)
        if status != "OK":
            raise RuntimeError("IMAP readonly select failed")
        since = (dt.datetime.now(TZ).date() - dt.timedelta(days=7)).strftime("%d-%b-%Y")
        status, data = client.search(None, "SINCE", since)
        if status != "OK":
            raise RuntimeError("IMAP search failed")
        for sequence in data[0].split() if data and data[0] else []:
            status, parts = client.fetch(sequence, "(BODY.PEEK[])")
            if status != "OK":
                raise RuntimeError("IMAP PEEK failed")
            raw = next(item[1] for item in parts if isinstance(item, tuple))
            message = email.message_from_bytes(raw, policy=policy.default)
            sender = parseaddr(str(message.get("from", "")))[1].lower()
            subject = str(message.get("subject", ""))
            if sender != contract["mailbox"]["expected_sender"].lower():
                continue
            report_key = next((key for key, cfg in contract["reports"].items() if re.fullmatch(cfg["subject_regex"], subject, flags=re.IGNORECASE)), None)
            if not report_key:
                continue
            expected_name = contract["reports"][report_key]["attachment"]
            attachments = [part for part in message.walk() if part.get_filename() == expected_name]
            if len(attachments) != 1:
                raise RuntimeError("expected exactly one GAM attachment")
            decoded = attachments[0].get_payload(decode=True)
            blob = decoded if isinstance(decoded, bytes) else b""
            sha = hashlib.sha256(blob).hexdigest()
            candidate_dir = run_dir / "candidates" / f"{report_key}-{sha[:12]}"
            candidate_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = candidate_dir / expected_name
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise RuntimeError("immutable candidate collision")
            if not path.exists():
                path.write_bytes(blob)
                path.chmod(0o600)
            workbook = inspect_workbook(path, report_key)
            candidates.append({"report_key": report_key, "date": workbook["date"], "sha256": sha, "bytes": len(blob), "path": str(path), "message_id": str(message.get("message-id", "")), "subject": subject, "received": str(message.get("date", ""))})
    finally:
        try:
            client.logout()
        except Exception:
            pass
    return candidates


def select_pair(candidates: list[dict], contract: dict, state: dict) -> tuple[str | None, dict[str, pathlib.Path], list[dict]]:
    last = state.get("last_applied_date") or contract["initial_last_reconciled_date"]
    expected = (dt.date.fromisoformat(last) + dt.timedelta(days=1)).isoformat()
    by_key: dict[str, list[dict]] = {key: [] for key in REPORTS}
    for item in candidates:
        if item["date"] == expected:
            by_key[item["report_key"]].append(item)
    blockers = []
    selected = {}
    for key in REPORTS:
        rows = by_key[key]
        hashes = {row["sha256"] for row in rows}
        if len(hashes) > 1:
            blockers.append({"type": "conflicting_report_versions", "report": key, "date": expected, "hash_count": len(hashes)})
        elif rows:
            selected[key] = pathlib.Path(rows[-1]["path"])
    if blockers:
        return expected, {}, blockers
    if len(selected) != len(REPORTS):
        return expected, {}, []
    return expected, selected, []


def save_selected(run_dir: pathlib.Path, paths: dict[str, pathlib.Path], candidates: list[dict], target_date: str) -> dict[str, pathlib.Path]:
    source = run_dir / "source"
    source.mkdir(parents=True, exist_ok=True, mode=0o700)
    final = {}
    metadata = []
    for key, original in paths.items():
        target = source / REPORTS[key]["attachment"]
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != hashlib.sha256(original.read_bytes()).hexdigest():
            raise RuntimeError("immutable selected-source collision")
        if not target.exists():
            shutil.copy2(original, target)
            target.chmod(0o600)
        final[key] = target
        item = next(row for row in candidates if row["report_key"] == key and row["date"] == target_date and row["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest())
        metadata.append({k: item[k] for k in ("report_key", "date", "sha256", "bytes", "message_id", "subject", "received")})
    atomic_json(run_dir / "intake.json", {"schema_version": 1, "readonly": True, "date": target_date, "attachments": metadata})
    return final


def verify_notice(message_id: str, payload: dict, thread: str) -> dict:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        env_path = pathlib.Path("/root/.hermes/profiles/zeus/.env")
        values = {}
        for raw in env_path.read_text(errors="ignore").splitlines():
            if raw.strip() and not raw.lstrip().startswith("#") and "=" in raw:
                key, value = raw.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
        token = values.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Discord bot token missing")
    import urllib.request
    request = urllib.request.Request(f"https://discord.com/api/v10/channels/{thread}/messages/{message_id}", headers={"Authorization": "Bot " + token, "User-Agent": "MGS-Finance-GAM/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        message = json.load(response)
    if message["id"] != message_id or message["channel_id"] != thread or message["author"]["id"] != "1496296175014252634" or message["content"] != payload["content"]:
        raise RuntimeError("Discord notice readback mismatch")
    return {"message_id": message_id, "channel_id": thread, "readback": True}


def notice(contract: dict, title: str, body: str, *, attention: bool, signature: str) -> dict:
    thread = contract["thread_id"]
    payload = {"content": "<@344196393512075265>" if attention else "", "allowed_mentions": {"parse": [], "users": ["344196393512075265"], "roles": [], "replied_user": False}, "embeds": [{"title": title, "description": body[:3900], "color": 15158332 if attention else 3066993}], "nonce": signature[:24], "enforce_nonce": True}
    child_env = {key: value for key, value in os.environ.items() if key not in {"DISCORD_BOT_TOKEN", "MGS_DISCORD_BOT_TOKEN_OVERRIDE", "MGS_DISCORD_API_URL_OVERRIDE", "MGS_DISCORD_BOT_ENV", "MGS_DRY_RUN"}}
    child_env["MGS_DISCORD_BOT_ENV"] = "/root/.hermes/profiles/zeus/.env"
    result = subprocess.run(["python3", str(REPO / "scripts/discord-bot-post.py"), "--channel-id", thread], input=json.dumps(payload), text=True, capture_output=True, timeout=60, env=child_env)
    if result.returncode:
        raise RuntimeError("Discord notice delivery failed")
    match = re.search(r"message_id=(\d+)", result.stdout)
    if not match:
        raise RuntimeError("Discord notice response missing message id")
    return verify_notice(match[1], payload, thread)


def remote_runner_check() -> dict:
    files = ["gam-revenue-core.mjs", "gam-revenue-cli.mjs"]
    result = {}
    for name in files:
        local = ROOT / name
        expected = hashlib.sha256(local.read_bytes()).hexdigest()
        remote = ssh("sudo -n -u mgsfinance sha256sum " + shlex.quote(TARGET + "/" + name)).split()[0]
        if remote != expected:
            raise RuntimeError("remote GAM runner hash mismatch")
        result[name] = expected
    return result


def remote_phase(phase: str, plan: dict) -> dict:
    command = "sudo -n -u mgsfinance " + shlex.quote(NODE) + " " + shlex.quote(TARGET + "/gam-revenue-cli.mjs") + " " + phase + " mgs_finance"
    return json.loads(ssh(command, json.dumps(plan, ensure_ascii=False).encode(), timeout=480))


def backup_before(plan: dict, run_dir: pathlib.Path) -> dict:
    remote = f"/home/zeus/mgs-finance-backups/gam-email/{plan['date']}-{plan['source_bundle_sha256'][:12]}"
    ssh("mkdir -p " + shlex.quote(remote) + " && chmod 700 " + shlex.quote(remote))
    scenario = remote + "/workspace-before.json"
    dump = remote + "/mgs_finance-before.dump"
    query = "SELECT row_to_json(s)::text FROM scenarios s WHERE id=" + "'" + plan["scenario_id"].replace("'", "''") + "'"
    if not ssh("test -f " + shlex.quote(scenario) + " && test -f " + shlex.quote(dump) + " && echo yes").strip():
        ssh(PG + "psql -h " + SOCKET + " -U mgs_pg -d mgs_finance -At -c " + shlex.quote(query) + " > " + shlex.quote(scenario) + " && chmod 600 " + shlex.quote(scenario))
        ssh(PG + "pg_dump -h " + SOCKET + " -U mgs_pg -Fc mgs_finance > " + shlex.quote(dump) + " && chmod 600 " + shlex.quote(dump), timeout=420)
    ssh(PG_ENV + PG_BIN + "/pg_restore --list " + shlex.quote(dump) + " >/dev/null")
    info = {}
    for path in (scenario, dump):
        output = ssh("sha256sum " + shlex.quote(path) + " && stat -c %s " + shlex.quote(path)).splitlines()
        info[path] = {"sha256": output[0].split()[0], "bytes": int(output[1])}
    encoded = ssh("base64 -w0 " + shlex.quote(dump), timeout=420)
    raw = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(raw).hexdigest() != info[dump]["sha256"]:
        raise RuntimeError("backup transfer hash mismatch")
    local = run_dir / "mgs_finance-before.dump"
    local.write_bytes(raw)
    local.chmod(0o600)
    info["local_copy"] = {"path": str(local), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return {"verified": True, "remote_root": remote, "files": info}


def blocker_body(plan: dict) -> str:
    lines = [f"Relatórios de {plan['date']} recebidos e reconciliados por moeda, mas a importação foi bloqueada antes de qualquer escrita:"]
    for item in plan["blockers"]:
        if item["type"] == "new_domain_country":
            lines.append(f"• {item['domain']} · país {item['country'].upper()} · {item['currency']} {float(item['revenue']):,.6f}: confirmar a vertical.")
        elif item["type"] == "missing_manager_after_cutover":
            lines.append(f"• {item['domain']} · {item['currency']} {float(item['revenue']):,.6f}: utm_medium ausente; confirmar o gestor.")
        else:
            lines.append(f"• {item['type']} · {item.get('domain', item.get('report', 'fonte'))}")
    lines.append("Nenhum valor foi aplicado à dashboard; o cutoff permanece no dia anterior.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--source-dir", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()
    contract = json.loads(CONTRACT.read_text())
    now = dt.datetime.now(TZ)
    if args.scheduled and (now.hour != 8 or now.minute not in contract["poll_minutes"]):
        return 0
    run_dir = RUNS / now.strftime("%Y%m%dT%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = read_state()
    with LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        step = "intake"
        try:
            if args.source_dir:
                paths = {key: args.source_dir / cfg["attachment"] for key, cfg in REPORTS.items()}
                for path in paths.values():
                    if not path.is_file():
                        raise FileNotFoundError(path)
                candidates = []
                target_date = inspect_workbook(paths["usd"], "usd")["date"]
            else:
                candidates = fetch_candidates(contract, run_dir)
                atomic_json(run_dir / "mailbox-candidates.json", {"readonly": True, "candidates": candidates})
                target_date, selected, selection_blockers = select_pair(candidates, contract, state)
                if selection_blockers:
                    raise RuntimeError("conflicting report versions for expected date")
                if not selected:
                    waiting = {"pass": True, "status": "waiting_pair", "expected_date": target_date, "candidate_count": len(candidates), "evidence": str(run_dir)}
                    atomic_json(run_dir / "result.json", waiting)
                    if args.scheduled and now.minute == max(contract["poll_minutes"]):
                        signature = digest(waiting)
                        if state.get("last_notice_signature") != signature:
                            proof = notice(contract, "Receita GAM — par não recebido", f"Até 08:{now.minute:02d} Eastern, o par completo referente a {target_date} não estava disponível. A dashboard não foi alterada.", attention=True, signature=signature)
                            state["last_notice_signature"] = signature
                            state["last_notice"] = proof
                    state.update({"last_run_at": now.isoformat(), "last_status": "waiting_pair", "expected_date": target_date})
                    atomic_json(STATE, state)
                    print(json.dumps(waiting, ensure_ascii=False))
                    return 0
                assert target_date is not None
                paths = save_selected(run_dir, selected, candidates, target_date)
            step = "analysis"
            plan = build_plan(paths)
            atomic_json(run_dir / "plan.json", plan)
            if plan["blockers"]:
                result = {"pass": True, "status": "blocked_mapping", "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "blockers": plan["blockers"], "evidence": str(run_dir), "production_financial_writes": 0}
                atomic_json(run_dir / "result.json", result)
                signature = digest(plan["blockers"])
                if (args.scheduled or args.notify) and state.get("last_notice_signature") != signature:
                    proof = notice(contract, "Receita GAM — decisão necessária", blocker_body(plan), attention=True, signature=signature)
                    state["last_notice_signature"] = signature
                    state["last_notice"] = proof
                state.update({"last_run_at": now.isoformat(), "last_status": "blocked_mapping", "expected_date": plan["date"], "last_plan": str(run_dir / "plan.json"), "last_blockers": plan["blockers"]})
                atomic_json(STATE, state)
                print(json.dumps(result, ensure_ascii=False))
                return 2
            if args.dry_run:
                result = {"pass": True, "status": "dry_run", "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "groups": len(plan["entries"]), "evidence": str(run_dir), "production_financial_writes": 0}
                atomic_json(run_dir / "result.json", result)
                print(json.dumps(result, ensure_ascii=False))
                return 0
            step = "remote_preflight"
            with QUOTE_LOCK.open("a") as quote_lock:
                fcntl.flock(quote_lock, fcntl.LOCK_EX)
                hashes = remote_runner_check()
                rehearsal = remote_phase("rehearse", plan)
                if not rehearsal.get("pass"):
                    raise RuntimeError("remote rehearsal failed")
                backup = backup_before(plan, run_dir)
                step = "production_apply"
                applied = remote_phase("apply", plan)
                verified = remote_phase("verify", plan)
            if not applied.get("pass") or not verified.get("pass") or verified.get("cutoff") != plan["date"]:
                raise RuntimeError("production readback failed")
            result = {"pass": True, "status": "already_applied" if applied.get("already_applied") else "applied", "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "groups": len(plan["entries"]), "source_bundle_sha256": plan["source_bundle_sha256"], "rehearsal": rehearsal, "apply": applied, "verify": verified, "backup": backup, "runner_hashes": hashes, "evidence": str(run_dir)}
            atomic_json(run_dir / "result.json", result)
            signature = digest({"date": plan["date"], "bundle": plan["source_bundle_sha256"], "status": result["status"]})
            if (args.scheduled or args.notify) and state.get("last_notice_signature") != signature:
                body = f"Receita de {plan['date']} processada e validada.\n• USD: {float(plan['source_totals']['USD']):,.2f}\n• CAD: {float(plan['source_totals']['CAD']):,.2f}\n• {plan['source_rows']} linhas → {len(plan['entries'])} grupos\n• Cutoff da dashboard: {plan['date']}\n• Repetição idempotente: validada"
                proof = notice(contract, "Receita GAM atualizada", body, attention=False, signature=signature)
                state["last_notice_signature"] = signature
                state["last_notice"] = proof
            state.update({"authority": "1547983130038767755", "last_run_at": now.isoformat(), "last_status": "ok", "last_applied_date": plan["date"], "last_source_bundle_sha256": plan["source_bundle_sha256"], "last_result": str(run_dir / "result.json"), "failure_streak": 0, "blocked_after_five": False})
            atomic_json(STATE, state)
            print(json.dumps({"pass": True, "status": result["status"], "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "groups": len(plan["entries"]), "evidence": str(run_dir)}, ensure_ascii=False))
            return 0
        except Exception as exc:
            failure = {"pass": False, "status": "failed", "step": step, "error": type(exc).__name__, "run_at": now.isoformat(), "evidence": str(run_dir)}
            atomic_json(run_dir / "failure.json", failure)
            previous = read_state() | state
            streak = previous.get("failure_streak", 0) + 1
            previous.update({"last_run_at": now.isoformat(), "last_status": "failed", "failure_streak": streak, "blocked_after_five": streak >= 5, "intervention_required": streak >= 3, "last_failure": failure})
            signature = digest(failure)
            if (args.scheduled or args.notify) and previous.get("last_notice_signature") != signature:
                try:
                    proof = notice(contract, "Receita GAM — falha técnica", f"Etapa: {step}\nErro: {type(exc).__name__}\nA dashboard não foi alterada.", attention=True, signature=signature)
                    previous["last_notice_signature"] = signature
                    previous["last_notice"] = proof
                except Exception:
                    pass
            atomic_json(STATE, previous)
            print(json.dumps(failure, ensure_ascii=False))
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
