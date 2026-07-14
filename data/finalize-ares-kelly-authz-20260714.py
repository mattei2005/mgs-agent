#!/usr/bin/env python3
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FINALIZER = "/root/mgs-agent/data/mgs-gateway-restart-finalizer-20260714T184505Z-3042593.sh"
AUDIT = Path("/root/mgs-agent/logs/events-audit.jsonl")
LOG = Path("/root/mgs-agent/logs/finalize-ares-kelly-authz-20260714.log")
THREAD_ID = "1526658144183517204"
ARES_BOT_ID = "1508864261504630925"
EXPECTED_USERS = {
    "344196393512075265",
    "321263240782807040",
    "409878085807112207",
    "432898782188011543",
    "1214246869484576890",
    "1291113428982693940",
    "1055570806945620030",
}
HANDOFF = (
    f"<@{ARES_BOT_ID}> Pedido da Kelly recuperado após correção da autorização do gateway. "
    "Execute o pedido original desta thread: País BRASIL; vertical CAR; língua PORTUGUÊS; "
    "processe os criativos em UPLOAD MANUAL, aplique as regras vigentes e mova para a pasta correta. "
    "Responda e valide o resultado aqui."
)


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record(event, **extra):
    payload = {"ts": now(), "event": event, "actor": "zeus-detached-ares-authz-finalizer", **extra}
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def proc_env(service):
    pid = subprocess.check_output(
        ["systemctl", "show", service, "-p", "MainPID", "--value"], text=True
    ).strip()
    raw = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    env = {}
    for item in raw:
        if b"=" in item:
            key, value = item.split(b"=", 1)
            env[key.decode(errors="replace")] = value.decode(errors="replace")
    return pid, env


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as log:
        run = subprocess.run([FINALIZER], text=True)
        if run.returncode != 0:
            record("ares_authz_activation_failed", stage="gateway_finalizer", returncode=run.returncode)
            return run.returncode

        ares_pid, ares_env = proc_env("ares-gateway.service")
        effective = {x.strip() for x in ares_env.get("DISCORD_ALLOWED_USERS", "").split(",") if x.strip()}
        if effective != EXPECTED_USERS:
            record(
                "ares_authz_activation_failed",
                stage="effective_env_readback",
                expected_count=len(EXPECTED_USERS),
                actual_count=len(effective),
                ares_pid=ares_pid,
            )
            return 81

        zeus_pid, zeus_env = proc_env("zeus-gateway.service")
        token = zeus_env.get("DISCORD_BOT_TOKEN") or zeus_env.get("DISCORD_TOKEN")
        if not token:
            record("ares_authz_activation_failed", stage="zeus_token_lookup", zeus_pid=zeus_pid)
            return 82

        body = json.dumps({"content": HANDOFF, "allowed_mentions": {"users": [ARES_BOT_ID]}}).encode()
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{THREAD_ID}/messages",
            data=body,
            headers={
                "Authorization": "Bot " + token,
                "Content-Type": "application/json",
                "User-Agent": "MGS-Zeus-Ares-Handoff/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            posted = json.load(response)
        message_id = str(posted.get("id", ""))
        if not message_id or f"<@{ARES_BOT_ID}>" not in posted.get("content", ""):
            record("ares_authz_activation_failed", stage="handoff_post_readback", ares_pid=ares_pid)
            return 83

        record(
            "ares_authz_activation_completed",
            ares_pid=ares_pid,
            effective_allowed_users_count=len(effective),
            target_thread_id=THREAD_ID,
            handoff_message_id=message_id,
            source_message_id="1526658144183517204",
        )
        log.write(
            f"{now()} completed ares_pid={ares_pid} allowed_users={len(effective)} "
            f"thread={THREAD_ID} handoff_message_id={message_id}\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
