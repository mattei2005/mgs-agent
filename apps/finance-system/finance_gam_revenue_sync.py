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
if __name__ == "__main__":
    from finance_release_guard import admit_entrypoint
    admit_entrypoint(ROOT)
from finance_release_guard import trigger_time
REPO = pathlib.Path("/root/mgs-agent")
CONTRACT = REPO / "data/finance-gam-revenue-contract.json"
STATE = REPO / "data/finance-gam-revenue-state.json"
MEDIA_SPEND_STATE = REPO / "data/finance-media-spend-state.json"
MEDIA_SPEND_RUNNER = ROOT / "finance_media_spend_sync.py"
SMS_USAGE_STATE = REPO / "data/finance-sms-usage-state.json"
SMS_USAGE_RUNNER = REPO / "scripts/sync-smsfunnel-cost-daily.py"
SMS_USAGE_LOCK = "/var/lock/sync-smsfunnel-cost-daily.lock"
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
from runcloud_ops import secret as runcloud_secret  # type: ignore[import-not-found]

from gam_revenue import REPORTS, build_plan, inspect_workbook
from gam_recovery import guarded_import, retry_read, failure_fields, RecoveryBlocked

_RUN_CLOUD_PASSWORD: str | None = None


def ssh(command: str, input_data: bytes | None = None, timeout: int = 180) -> str:
    """Use one in-memory 1Password resolution for every SSH call in this run."""
    global _RUN_CLOUD_PASSWORD
    if _RUN_CLOUD_PASSWORD is None:
        _RUN_CLOUD_PASSWORD = runcloud_secret("Runcloud Server 01 - 162.55.28.178- zeus Acesso", "password")
    assert _RUN_CLOUD_PASSWORD is not None
    read_fd, write_fd = os.pipe()
    os.write(write_fd, (_RUN_CLOUD_PASSWORD + "\n").encode())
    os.close(write_fd)
    try:
        result = subprocess.run(
            ["sshpass", "-d", str(read_fd), "ssh", "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=/root/.ssh/known_hosts_mgs", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "-o", "ConnectTimeout=20", "zeus@162.55.28.178", command],
            pass_fds=(read_fd,), input=input_data, capture_output=True, timeout=timeout,
        )
    finally:
        os.close(read_fd)
    if result.returncode:
        raise RuntimeError("SSH command failed exit=" + str(result.returncode) + " " + result.stderr.decode(errors="replace")[-1200:] + result.stdout.decode(errors="replace")[-1200:])
    return result.stdout.decode(errors="replace")


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


def healthy_state_fields() -> dict:
    """Clear stale technical-failure flags after a healthy mailbox result."""
    return {
        "failure_streak": 0,
        "blocked_after_five": False,
        "intervention_required": False,
        "last_failure": None,
    }


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


def accepted_senders(contract: dict) -> set[str]:
    """Return the exact mailbox sender allowlist, with legacy fallback."""
    mailbox = contract["mailbox"]
    values = mailbox.get("expected_senders")
    if values is None:
        values = [mailbox.get("expected_sender", "")]
    if not isinstance(values, list) or not values or any(
        not isinstance(value, str) or not re.fullmatch(r"[^@\s]+@[^@\s]+", value.strip())
        for value in values
    ):
        raise RuntimeError("invalid mailbox sender allowlist")
    return {value.strip().lower() for value in values}


def sender_allowed(sender: str, contract: dict) -> bool:
    return sender.strip().lower() in accepted_senders(contract)


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
            if not sender_allowed(sender, contract):
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
    if message.get("embeds", []):
        raise RuntimeError("Discord notice must be a normal message without embeds")
    return {"message_id": message_id, "channel_id": thread, "readback": True}


def notice_payloads(title: str, body: str, *, attention: bool, signature: str) -> list[dict]:
    """Normal mobile-readable messages; retain all exceptions beyond Discord's limit."""
    text = ("<@344196393512075265>\n" if attention else "") + f"**{title}**\n\n" + body
    chunks = []
    while text:
        end = min(len(text), 1900)
        if end < len(text):
            boundary = text.rfind("\n", 0, end)
            if boundary > 0:
                end = boundary + 1
        chunks.append(text[:end])
        text = text[end:]
    return [{
        "content": chunk, "embeds": [], "flags": 4,
        "allowed_mentions": {"parse": [], "users": ["344196393512075265"] if attention and index == 0 else [], "roles": [], "replied_user": False},
        "nonce": hashlib.sha256(f"normal-v1:{signature}:{index}".encode()).hexdigest()[:24],
        "enforce_nonce": True,
    } for index, chunk in enumerate(chunks)]


def notice(contract: dict, title: str, body: str, *, attention: bool, signature: str) -> dict:
    thread = contract["thread_id"]
    child_env = {key: value for key, value in os.environ.items() if key not in {"DISCORD_BOT_TOKEN", "MGS_DISCORD_BOT_TOKEN_OVERRIDE", "MGS_DISCORD_API_URL_OVERRIDE", "MGS_DISCORD_BOT_ENV", "MGS_DRY_RUN"}}
    child_env["MGS_DISCORD_BOT_ENV"] = "/root/.hermes/profiles/zeus/.env"
    receipts = []
    for payload in notice_payloads(title, body, attention=attention, signature=signature):
        result = subprocess.run(["python3", str(REPO / "scripts/discord-bot-post.py"), "--channel-id", thread], input=json.dumps(payload), text=True, capture_output=True, timeout=60, env=child_env)
        if result.returncode:
            raise RuntimeError("Discord notice delivery failed")
        match = re.search(r"message_id=(\d+)", result.stdout)
        if not match:
            raise RuntimeError("Discord notice response missing message id")
        receipts.append(verify_notice(match[1], payload, thread))
    return {**receipts[0], "messages": receipts}


def completion_notice(contract: dict, state: dict) -> dict | None:
    """A single combined receipt, only after both financial partitions verify.

    Notification failure must not undo a confirmed financial state or cause reimport.
    Later morning slots retry delivery using the same deterministic nonce.
    """
    date = state.get("last_applied_date")
    if state.get("last_status") != "ok" or not date or not state.get("last_result"):
        return None
    result = json.loads(pathlib.Path(state["last_result"]).read_text())
    if not (result.get("pass") and result.get("date") == date and result.get("cutoff") == date
            and result.get("verify", {}).get("pass") and not result.get("blockers")
            and result.get("status") in {"applied", "already_applied"}):
        return None
    signature = digest({"kind": "daily-complete-v1", "date": date, "bundle": result["source_bundle_sha256"]})
    if state.get("last_completion_signature") == signature:
        return state.get("last_completion_notice")
    spend_state = json.loads(MEDIA_SPEND_STATE.read_text())
    if not spend_ready(spend_state, date):
        return None
    spend = json.loads(pathlib.Path(spend_state["last_report_path"]).read_text())
    from spend_report import render_report
    if not (spend.get("pass") and spend.get("readback") and spend.get("until", "") >= date
            and not render_report(spend)["attention"]):
        return None
    plan = json.loads(pathlib.Path(state["last_plan"]).read_text())
    verified = remote_phase("verify", plan)
    if not verified.get("pass") or verified.get("cutoff") != date:
        raise RuntimeError("completion receipt financial verification failed")
    display = dt.date.fromisoformat(date).strftime("%d/%m/%Y")
    proof = notice(contract, "Preenchimento diário concluído",
        f"Tudo preenchido e conferido até {display}: gastos do Facebook e Google Ads e receitas dos relatórios GAM.\n\n"
        f"A dashboard está completa até esse dia, sem pendências de preenchimento. O dia atual entra no próximo ciclo.",
        attention=False, signature=signature)
    state.update(last_completion_signature=signature, last_completion_notice=proof,
                 last_completion_date=date, completion_notice_pending=False, completion_notice_error=None)
    atomic_json(STATE, state)
    return proof


def deliver_completion(contract: dict, state: dict) -> None:
    try:
        completion_notice(contract, state)
    except Exception as exc:
        state.update(completion_notice_pending=True, completion_notice_error=type(exc).__name__)
        atomic_json(STATE, state)
        print(json.dumps({"notification_pending": True, "error": type(exc).__name__, "financial_state_preserved": True}))


def remote_runner_check() -> dict:
    files = ["gam-revenue-core.mjs", "gam-revenue-cli.mjs", "gam-recovery-inspect.mjs"]
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
    stage = "partial" if plan.get("partial") else "complete"
    remote = f"/home/zeus/mgs-finance-backups/gam-email/{plan['date']}-{plan['source_bundle_sha256'][:12]}-{stage}-{plan['mapping_rules_sha256'][:12]}"
    parent = "/home/zeus/mgs-finance-backups/gam-email"
    ssh("sudo -n install -d -o zeus -g zeus -m 700 " + shlex.quote(parent) + " && mkdir -p " + shlex.quote(remote) + " && chmod 700 " + shlex.quote(remote))
    scenario = remote + "/workspace-before.json"
    dump = remote + "/mgs_finance-before.dump"
    query = "SELECT row_to_json(s)::text FROM scenarios s WHERE id=" + "'" + plan["scenario_id"].replace("'", "''") + "'"
    if not ssh("if test -f " + shlex.quote(scenario) + " && test -f " + shlex.quote(dump) + "; then echo yes; fi").strip():
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


def blocker_body(plan: dict, *, confirmed_applied: bool) -> str:
    if confirmed_applied:
        lines = [
            f"Relatórios de {plan['date']} recebidos e reconciliados por moeda.",
            f"As {plan['summary']['mapped_rows']} linhas com classificação comprovada foram aplicadas em {len(plan['entries'])} grupos. Somente as {plan['summary']['blocked_rows']} linha(s) abaixo ficaram pendentes; não foram tratadas como zero.",
            "Preciso confirmar somente estes itens:",
        ]
    else:
        lines = [
            f"Relatórios de {plan['date']} recebidos, mas nenhuma linha pôde ser aplicada com segurança.",
            "Preciso confirmar somente estes itens:",
        ]
    for index, item in enumerate(plan["blockers"], 1):
        placements = ", ".join(item.get("placements", [])) or "não identificado"
        amount = f"{item['currency']} {float(item['revenue']):,.6f}"
        rows = item.get("rows", 0)
        if item["type"] == "new_domain_country":
            lines.append(f"{index}. {item['domain']} / {item['country'].upper()} — {rows} linha(s), {amount}. O domínio e o país foram identificados; falta somente a vertical. Fonte: {placements}.")
        elif item["type"] == "missing_manager_after_cutover":
            lines.append(f"{index}. {item['domain']} — {rows} linha(s), {amount}. A linha chegou sem gestor identificável; falta informar o gestor. Fonte: {placements}.")
        elif item["type"] == "unknown_domain":
            candidates = ", ".join(item.get("candidate_domains", [])) or "nenhum candidato encontrado"
            lines.append(f"{index}. {item['domain']} / {item['country'].upper()} — {rows} linha(s), {amount}. O identificador não está cadastrado; candidato: {candidates}. Faltam o domínio correto e a vertical. Fonte: {placements}.")
        else:
            lines.append(f"{index}. {item.get('domain', item.get('report', 'fonte'))} — {rows} linha(s), {amount}. Falta a classificação operacional exata. Fonte: {placements}.")
    lines.append("Responda com a informação que falta em cada número e diga se a regra deve valer também para os próximos relatórios.")
    lines.extend(
        [
            "O restante já está na dashboard. O Realizado continua até o último dia completo; esta data aparece como parcial.",
            "Após sua confirmação, aplicarei somente o complemento pendente e conferirei se o dia ficou completo.",
        ] if confirmed_applied else [
            "A parcela incerta não foi gravada nem tratada como zero. O Realizado continua até o último dia completo.",
            "Após sua confirmação, aplicarei somente a classificação autorizada e conferirei o resultado.",
        ]
    )
    return "\n\n".join(lines)


def scheduled_slot(now: dt.datetime, contract: dict, *, intake: bool, finalize: bool) -> bool:
    if intake and finalize:
        raise ValueError("scheduled modes are mutually exclusive")
    if intake:
        return now.hour == 8 and now.minute in contract["poll_minutes"]
    if finalize:
        return now.hour == 9 and now.minute in contract["finalize_minutes"]
    return True


def should_skip_scheduled_run(state: dict, yesterday: str, *, scheduled_intake: bool, finalize: bool) -> bool:
    """Stop later cron slots after the prior financial day is complete."""
    return (scheduled_intake or finalize) and state.get("last_applied_date", "") >= yesterday


def missing_pair_is_overdue(target_date: str | None, yesterday: str) -> bool:
    """A same-day pair is not due and must never create an alert."""
    return bool(target_date and target_date <= yesterday)


def spend_ready(state: dict, source_date: str) -> bool:
    return state.get("last_status") == "ok" and state.get("last_until", "") >= source_date


def run_spend_step(source_date: str, *, state_path: pathlib.Path = MEDIA_SPEND_STATE) -> dict:
    before = json.loads(state_path.read_text()) if state_path.exists() else {}
    if spend_ready(before, source_date):
        return {"pass": True, "status": "already_ready", "state": before, "runner": None}
    command = ["/usr/bin/python3", str(MEDIA_SPEND_RUNNER), "--pipeline-date", source_date]
    process = subprocess.run(command, text=True, capture_output=True, timeout=1200)
    after = json.loads(state_path.read_text()) if state_path.exists() else {}
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    runner = json.loads(lines[-1]) if lines else None
    if process.returncode or not spend_ready(after, source_date):
        detail = process.stderr[-600:] if process.stderr else "media-spend state did not reach the revenue date"
        raise RuntimeError(f"sequential media-spend step failed exit={process.returncode}: {detail}")
    return {"pass": True, "status": "completed", "state": after, "runner": runner}


def sms_ready(state: dict, source_date: str) -> bool:
    day = (state.get("days") or {}).get(source_date) or {}
    return state.get("last_success_date", "") >= source_date and bool(day.get("source_bundle_sha256")) and day.get("audit_id") is not None


def run_sms_step(source_date: str, *, state_path: pathlib.Path = SMS_USAGE_STATE) -> dict:
    before = json.loads(state_path.read_text()) if state_path.exists() else {}
    if sms_ready(before, source_date):
        return {"pass": True, "status": "already_ready", "state": before, "runner": None}
    command = ["/usr/bin/flock", "-w", "900", SMS_USAGE_LOCK, "/usr/bin/python3", str(SMS_USAGE_RUNNER), "--date", source_date, "--dash-only", "--no-alert"]
    process = subprocess.run(command, text=True, capture_output=True, timeout=1800)
    after = json.loads(state_path.read_text()) if state_path.exists() else {}
    lines = [line for line in process.stdout.splitlines() if line.strip().startswith("{")]
    runner = json.loads(lines[-1]) if lines else None
    if process.returncode or not sms_ready(after, source_date):
        detail = (process.stderr or process.stdout or "SMS usage state did not reach the revenue date")[-800:]
        raise RuntimeError(f"sequential SMS usage step failed exit={process.returncode}: {detail}")
    return {"pass": True, "status": "completed", "state": after, "runner": runner}


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--scheduled", action="store_true")
    mode.add_argument("--scheduled-intake", action="store_true")
    mode.add_argument("--scheduled-finalize", action="store_true")
    mode.add_argument("--manual-intake", action="store_true")
    parser.add_argument("--source-dir", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()
    contract = json.loads(CONTRACT.read_text())
    now = trigger_time(dt.datetime.now(TZ))
    scheduled_intake = args.scheduled or args.scheduled_intake
    intake = scheduled_intake or args.manual_intake
    finalize = args.scheduled_finalize
    if not args.manual_intake and not scheduled_slot(now, contract, intake=intake, finalize=finalize):
        return 0
    state = read_state()
    yesterday = (now.date() - dt.timedelta(days=1)).isoformat()
    run_dir = RUNS / now.strftime("%Y%m%dT%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        state = read_state()
        if should_skip_scheduled_run(state, yesterday, scheduled_intake=scheduled_intake, finalize=finalize):
            if not args.dry_run:
                deliver_completion(contract, state)
            return 0
        if state.get("blocked_after_five") or state.get("failure_streak", 0) >= 5:
            print(json.dumps({"pass": False, "status": "blocked_after_five", "intervention_required": True, "production_financial_writes": 0}))
            return 2
        recovery_events = []
        def journal(event):
            recovery_events.append({**event, "observed_at": dt.datetime.now(TZ).isoformat()})
            atomic_json(run_dir / "recovery.json", {"events": recovery_events})
            if not args.dry_run:
                state.update({"intervention_required": True, "last_recovery": str(run_dir / "recovery.json")})
                atomic_json(STATE, state)
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
                candidates = retry_read(lambda: fetch_candidates(contract, run_dir), "intake", journal)
                atomic_json(run_dir / "mailbox-candidates.json", {"readonly": True, "candidates": candidates})
                target_date, selected, selection_blockers = select_pair(candidates, contract, state)
                if selection_blockers:
                    raise RuntimeError("conflicting report versions for expected date")
                if not selected:
                    waiting = {"pass": True, "status": "waiting_pair", "expected_date": target_date, "candidate_count": len(candidates), "evidence": str(run_dir)}
                    atomic_json(run_dir / "result.json", waiting)
                    if not args.dry_run:
                        if intake and now.minute == max(contract["poll_minutes"]) and missing_pair_is_overdue(target_date, yesterday):
                            signature = digest(waiting)
                            if state.get("last_notice_signature") != signature:
                                proof = notice(contract, "Receita GAM — par não recebido", f"Até 08:{now.minute:02d} Eastern, o par completo referente a {target_date} não estava disponível. A dashboard não foi alterada.", attention=True, signature=signature)
                                state["last_notice_signature"] = signature
                                state["last_notice"] = proof
                        state.update({"last_run_at": now.isoformat(), "last_status": "waiting_pair", "expected_date": target_date, **healthy_state_fields()})
                        atomic_json(STATE, state)
                    print(json.dumps(waiting, ensure_ascii=False))
                    return 0
                assert target_date is not None
                paths = save_selected(run_dir, selected, candidates, target_date)
            step = "analysis"
            plan = build_plan(paths)
            atomic_json(run_dir / "plan.json", plan)
            partial = bool(plan["blockers"])
            if partial and not plan["entries"]:
                result = {"pass": True, "status": "blocked_mapping", "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "blockers": plan["blockers"], "evidence": str(run_dir), "production_financial_writes": 0}
                atomic_json(run_dir / "result.json", result)
                if not args.dry_run:
                    signature = digest({"policy": plan["processing_policy_authority_message_id"], "status": "no_confirmed_rows", "blockers": plan["blockers"]})
                    if (intake or finalize or args.notify) and state.get("last_notice_signature") != signature:
                        proof = notice(contract, "Receita GAM — confirmação necessária", blocker_body(plan, confirmed_applied=False), attention=True, signature=signature)
                        state["last_notice_signature"] = signature
                        state["last_notice"] = proof
                    state.update({"last_run_at": now.isoformat(), "last_status": "blocked_mapping", "expected_date": plan["date"], "last_plan": str(run_dir / "plan.json"), "last_blockers": plan["blockers"], **healthy_state_fields()})
                    atomic_json(STATE, state)
                print(json.dumps(result, ensure_ascii=False))
                return 2
            if args.dry_run:
                result = {"pass": True, "status": "partial_dry_run" if partial else "dry_run", "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "mapped_totals": plan["mapped_totals"], "blocked_totals": plan["blocked_totals"], "groups": len(plan["entries"]), "blockers": plan["blockers"], "evidence": str(run_dir), "production_financial_writes": 0}
                atomic_json(run_dir / "result.json", result)
                print(json.dumps(result, ensure_ascii=False))
                return 0
            if intake:
                step = "sequential_spend"
                spend = run_spend_step(plan["date"])
                atomic_json(run_dir / "spend-step.json", spend)
                if plan["date"] >= "2026-10-01":
                    step = "sequential_sms_usage"
                    sms = run_sms_step(plan["date"])
                    atomic_json(run_dir / "sms-step.json", sms)
            if finalize:
                spend_state = json.loads(MEDIA_SPEND_STATE.read_text()) if MEDIA_SPEND_STATE.exists() else {}
                if not spend_ready(spend_state, plan["date"]):
                    result = {"pass": True, "status": "waiting_spend", "date": plan["date"], "spend_until": spend_state.get("last_until"), "evidence": str(run_dir), "production_financial_writes": 0}
                    atomic_json(run_dir / "result.json", result)
                    if now.minute == max(contract["finalize_minutes"]):
                        signature = digest(result)
                        if state.get("last_notice_signature") != signature:
                            proof = notice(contract, "Receita GAM — gastos ainda incompletos", f"A receita de {plan['date']} está validada, mas os gastos automáticos ainda não fecharam o mesmo dia. O cutoff não avançou.", attention=True, signature=signature)
                            state["last_notice_signature"] = signature
                            state["last_notice"] = proof
                    state.update({"last_run_at": now.isoformat(), "last_status": "waiting_spend", "expected_date": plan["date"], "last_plan": str(run_dir / "plan.json")})
                    atomic_json(STATE, state)
                    print(json.dumps(result, ensure_ascii=False))
                    return 0
                if plan["date"] >= "2026-10-01":
                    step = "finalize_sms_usage"
                    sms = run_sms_step(plan["date"])
                    atomic_json(run_dir / "sms-step.json", sms)
            step = "remote_preflight"
            with QUOTE_LOCK.open("a") as quote_lock:
                fcntl.flock(quote_lock, fcntl.LOCK_EX)
                hashes = retry_read(remote_runner_check, "remote_preflight", journal)
                rehearsal = retry_read(lambda: remote_phase("rehearse", plan), "rehearsal", journal)
                if not rehearsal.get("pass"):
                    raise RuntimeError("remote rehearsal failed")
                backup = backup_before(plan, run_dir)
                step = "production_apply"
                outcome = guarded_import(remote_phase, plan, journal)
                applied, verified = outcome["apply"], outcome["verify"]
                step = "production_verify"
            expected_cutoff = (dt.date.fromisoformat(plan["date"]) - dt.timedelta(days=1)).isoformat() if partial else plan["date"]
            if not applied.get("pass") or not verified.get("pass") or verified.get("cutoff") != expected_cutoff:
                raise RuntimeError("production readback failed")
            if partial:
                status = "partial_already_applied" if applied.get("already_applied") else "partial_applied"
            else:
                status = "already_applied" if applied.get("already_applied") else "applied"
            result = {"pass": True, "status": status, "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "mapped_totals": plan["mapped_totals"], "blocked_totals": plan["blocked_totals"], "blockers": plan["blockers"], "groups": len(plan["entries"]), "source_bundle_sha256": plan["source_bundle_sha256"], "cutoff": expected_cutoff, "rehearsal": rehearsal, "apply": applied, "verify": verified, "backup": backup, "runner_hashes": hashes, "evidence": str(run_dir)}
            atomic_json(run_dir / "result.json", result)
            if partial:
                signature = digest({"policy": plan["processing_policy_authority_message_id"], "status": "partial_applied", "bundle": plan["source_bundle_sha256"], "blockers": plan["blockers"]})
                if (intake or finalize or args.notify) and state.get("last_notice_signature") != signature:
                    proof = notice(contract, "Receita GAM — confirmar somente a exceção", blocker_body(plan, confirmed_applied=True), attention=True, signature=signature)
                    state["last_notice_signature"] = signature
                    state["last_notice"] = proof
            next_expected = (dt.date.fromisoformat(plan["date"]) + dt.timedelta(days=1)).isoformat()
            if partial:
                state.update({"authority": "1547983130038767755", "processing_policy_authority": plan["processing_policy_authority_message_id"], "last_run_at": now.isoformat(), "last_status": "partial_mapping", "expected_date": plan["date"], "last_plan": str(run_dir / "plan.json"), "last_blockers": plan["blockers"], "last_partial_date": plan["date"], "last_partial_mapped_totals": plan["mapped_totals"], "last_partial_blocked_totals": plan["blocked_totals"], "last_source_bundle_sha256": plan["source_bundle_sha256"], "last_result": str(run_dir / "result.json"), **healthy_state_fields()})
            else:
                for key in ("last_partial_date", "last_partial_mapped_totals", "last_partial_blocked_totals"):
                    state.pop(key, None)
                state.update({"authority": "1547983130038767755", "processing_policy_authority": plan["processing_policy_authority_message_id"], "last_run_at": now.isoformat(), "last_status": "ok", "last_applied_date": plan["date"], "expected_date": next_expected, "last_plan": str(run_dir / "plan.json"), "last_blockers": [], "last_source_bundle_sha256": plan["source_bundle_sha256"], "last_result": str(run_dir / "result.json"), **healthy_state_fields()})
            atomic_json(STATE, state)
            if not partial and (intake or finalize or args.notify):
                deliver_completion(contract, state)
            print(json.dumps({"pass": True, "status": result["status"], "date": plan["date"], "source_rows": plan["source_rows"], "source_totals": plan["source_totals"], "mapped_totals": plan["mapped_totals"], "blocked_totals": plan["blocked_totals"], "groups": len(plan["entries"]), "cutoff": expected_cutoff, "evidence": str(run_dir)}, ensure_ascii=False))
            return 0
        except Exception as exc:
            failure = {"pass": False, "status": "failed", "step": step, "error": type(exc).__name__, "detail": str(exc)[:500], "run_at": now.isoformat(), "evidence": str(run_dir)}
            atomic_json(run_dir / "failure.json", failure)
            if args.dry_run:
                print(json.dumps(failure, ensure_ascii=False))
                return 1
            previous = read_state() | state
            streak = previous.get("failure_streak", 0) + 1
            disposition = exc.disposition if isinstance(exc, RecoveryBlocked) else "unconfirmed"
            failure["write_outcome"] = disposition
            atomic_json(run_dir / "failure.json", failure)
            previous.update({"last_run_at": now.isoformat(), "last_status": "failed", **failure_fields(streak), "last_failure": failure})
            signature = digest(failure)
            if (intake or finalize or args.notify) and previous.get("last_notice_signature") != signature:
                try:
                    effect = "O lote de receita não foi aplicado, conforme readback; gastos são verificados separadamente." if disposition == "not_applied" else "O resultado da gravação não foi confirmado integralmente. Não repetir a importação sem conferir lote, cenário e auditoria."
                    proof = notice(contract, "Receita GAM — recuperação bloqueada", f"Etapa: {step}\nErro: {type(exc).__name__}\n{effect}\nIntervenção iniciada na primeira falha; recuperação segura esgotada ou bloqueada. Evidência preservada. Recomendo resolver a etapa indicada antes de retomar o mesmo lote, sem duplicar lançamentos.", attention=True, signature=signature)
                    previous["last_notice_signature"] = signature
                    previous["last_notice"] = proof
                except Exception:
                    pass
            atomic_json(STATE, previous)
            print(json.dumps(failure, ensure_ascii=False))
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
