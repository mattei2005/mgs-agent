"""
Zeus — Admin Agent / General Manager for MGS Digital Corp

Receives events from all other agents via discord.shared.events module.
Responds to commands from Super Admin (Rodolfo) in zeus-admin-agent channel.

MVP commands:
- status — dashboard with agents state + recent activity
- list users — show whitelists per agent
- pending — list pending authorization requests
- last N — show last N pipeline events from audit log
- aprova @user [agent] — authorize user for agent (updates authorized-users.json)
- nega @user — deny pending authorization request

Future (Phase 2+):
- restart <agent>, pause <agent>, logs <agent> last N
- Inter-agent orchestration
"""
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks

# Import shared modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from bots.shared.config import (
    ZEUS_CHANNEL_ID,
    ZEUS_NAME,
    ATENA_CHANNEL_ID,
    GUILD_ID,
    PROJECT_ROOT,
    AUTH_PATH,
    load_authorized_users,
    log_path,
)
from bots.shared.auth import is_authorized, get_user_details


# ===== Logging setup =====
LOG_FILE = log_path(ZEUS_NAME)
EVENTS_AUDIT_PATH = Path("/root/mgs-agent/logs/events-audit.jsonl")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("zeus")


# ===== Token loading (runtime from 1Password, never persisted) =====
def load_token() -> str:
    """Fetch Discord bot token from 1Password at runtime."""
    vault = os.getenv("OP_DEFAULT_VAULT", "MGS Conteúdo")
    try:
        result = subprocess.run(
            [
                "op", "item", "get",
                "Discord Bot - Zeus",
                "--vault", vault,
                "--fields", "discord_bot_token",
                "--reveal",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        token = result.stdout.strip()
        if not token:
            raise ValueError("Token from 1Password is empty")
        return token
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to load token from 1Password: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading token: {e}")
        raise


# ===== Discord bot setup =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!zeus ", intents=intents)


# ===== Helpers =====
def load_recent_events(n: int = 5) -> list:
    """Load last N events from audit log."""
    if not EVENTS_AUDIT_PATH.exists():
        return []
    try:
        with open(EVENTS_AUDIT_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        events = []
        for line in lines[-n*3:]:  # read extra in case of malformed lines
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events[-n:]
    except Exception as e:
        logger.error(f"Failed to load events: {e}")
        return []


def get_pending_approvals() -> list:
    """Get pending authorization requests from authorized-users.json."""
    try:
        data = load_authorized_users()
        return data.get("pending_approvals", [])
    except Exception:
        return []


def format_event_summary(event: dict) -> str:
    """One-line summary of an event."""
    ev_type = event.get("type", "unknown")
    agent = event.get("agent", "?")
    ts = event.get("timestamp", "?")
    # trim ts to HH:MM:SS
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ts_short = dt.strftime("%H:%M:%S UTC")
    except Exception:
        ts_short = ts[:19]

    if ev_type == "pipeline_started":
        return f"`{ts_short}` 📋 {agent} started: {event.get('request', '?')[:50]}"
    elif ev_type == "pipeline_paused":
        return f"`{ts_short}` ⏸️ {agent} paused at {event.get('step', '?')}"
    elif ev_type == "pipeline_completed":
        dur = event.get('duration_seconds', 0)
        return f"`{ts_short}` ✅ {agent} done ({int(dur)}s)"
    elif ev_type == "error":
        return f"`{ts_short}` ❌ {agent} error at {event.get('step', '?')}"
    elif ev_type == "auth_request":
        return f"`{ts_short}` 🔐 {agent} auth request from {event.get('user_mention', '?')}"
    elif ev_type == "unauthorized_attempt":
        return f"`{ts_short}` 🚫 {agent} blocked {event.get('user', '?')}"
    else:
        return f"`{ts_short}` ❓ {agent} {ev_type}"


# ===== Event handlers =====
@bot.event
async def on_ready():
    logger.info(f"Zeus logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Guild count: {len(bot.guilds)}")
    for guild in bot.guilds:
        logger.info(f"  - {guild.name} ({guild.id})")
    logger.info(f"Listening only on channel {ZEUS_CHANNEL_ID}")

    # Send startup heartbeat to channel
    try:
        channel = bot.get_channel(ZEUS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="⚡ Zeus Online",
                description="Admin Agent ready. Type `status` or `help` for commands.",
                color=0xf1c40f,  # gold
                timestamp=datetime.now(timezone.utc),
            )
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send startup message: {e}")


@bot.event
async def on_message(message: discord.Message):
    # Ignore own messages
    if message.author == bot.user:
        return

    # Only respond in Zeus's designated channel
    if message.channel.id != ZEUS_CHANNEL_ID:
        return

    # Allow other bots (Atena) to post events via embeds — don't process as commands
    if message.author.bot:
        return

    # Authorization check (Super Admin only)
    if not is_authorized(message.author.id, "zeus"):
        logger.warning(
            f"UNAUTHORIZED message in Zeus channel from {message.author} "
            f"(ID: {message.author.id}): '{message.content[:100]}'"
        )
        await message.channel.send(
            f"🔒 {message.author.mention}, Zeus é restrito ao Super Admin. Acesso negado."
        )
        return

    # Authorized — route intent
    user = get_user_details(message.author.id, "zeus")
    username = user.get("name") if user else str(message.author)
    logger.info(f"Message from {username}: '{message.content}'")

    content = message.content.strip()
    content_lower = content.lower()

    # Intent detection
    if content_lower in ["help", "comandos", "?"]:
        await handle_help(message, username)
    elif any(kw in content_lower for kw in ["status", "tá tudo ok", "health", "tudo certo"]):
        await handle_status(message)
    elif any(kw in content_lower for kw in ["list users", "lista usuarios", "lista usuários", "users"]):
        await handle_list_users(message)
    elif content_lower.startswith("pending") or "pendências" in content_lower or "pendencias" in content_lower:
        await handle_pending(message)
    elif re.match(r"^last\s+\d+", content_lower) or re.match(r"^últimas?\s+\d+", content_lower):
        await handle_last_events(message, content_lower)
    elif content_lower.startswith("aprova "):
        await handle_approve(message, content)
    elif content_lower.startswith("nega "):
        await handle_deny(message, content)
    else:
        await handle_help(message, username)


# ===== Intent handlers =====
async def handle_help(message: discord.Message, username: str):
    embed = discord.Embed(
        title="⚡ Zeus — Comandos disponíveis",
        description=f"Olá {username}. Zeus é o General Manager.",
        color=0xf1c40f,
    )
    embed.add_field(
        name="📊 Dashboard",
        value="• `status` — estado dos agentes + atividade recente\n"
              "• `list users` — whitelists dos agentes\n"
              "• `pending` — pedidos de autorização pendentes\n"
              "• `last 5` — últimos 5 eventos registrados",
        inline=False,
    )
    embed.add_field(
        name="🔐 Autorização",
        value="• `aprova @user atena` — autorizar user para Atena\n"
              "• `aprova @user zeus` — autorizar user para Zeus\n"
              "• `nega @user` — negar pedido pendente",
        inline=False,
    )
    embed.add_field(
        name="📚 Info",
        value="• `help` — este menu",
        inline=False,
    )
    await message.channel.send(embed=embed)


async def handle_status(message: discord.Message):
    """Admin-level dashboard: agents state + recent activity."""
    now = datetime.now(timezone.utc).isoformat()
    py_version = sys.version.split()[0]
    dpy_version = discord.__version__

    try:
        auth_data = load_authorized_users()
        n_agents = len(auth_data.get("agents", {}))
        pending = len(auth_data.get("pending_approvals", []))
        blocklist = len(auth_data.get("blocklist", []))
    except Exception as e:
        n_agents = pending = blocklist = "?"
        logger.error(f"Failed to load auth data: {e}")

    try:
        git_result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "-1", "--pretty=%h %s"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        last_commit = git_result.stdout.strip()
    except Exception:
        last_commit = "unavailable"

    recent = load_recent_events(5)
    recent_str = "\n".join(format_event_summary(e) for e in recent) if recent else "_Nenhum evento ainda_"

    embed = discord.Embed(
        title="⚡ Zeus Dashboard",
        color=0xf1c40f,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="🤖 Agents",
        value=f"• Active: `{n_agents}`\n• Pending approvals: `{pending}`\n• Blocklist: `{blocklist}`",
        inline=True,
    )
    embed.add_field(
        name="⚙️ System",
        value=f"• Python: `{py_version}`\n• discord.py: `{dpy_version}`\n• Last commit: `{last_commit}`",
        inline=True,
    )
    embed.add_field(
        name="📋 Últimos eventos (5)",
        value=recent_str[:1024],
        inline=False,
    )
    await message.channel.send(embed=embed)


async def handle_list_users(message: discord.Message):
    try:
        data = load_authorized_users()
    except Exception as e:
        await message.channel.send(f"❌ Erro ao carregar auth data: {e}")
        return

    embed = discord.Embed(
        title="👥 Authorized users per agent",
        color=0xf1c40f,
    )
    agents = data.get("agents", {})
    for agent_key, agent_cfg in agents.items():
        name = agent_cfg.get("name", agent_key)
        agent_type = agent_cfg.get("type", "?")
        users = agent_cfg.get("_authorized_users_detail", [])
        if not users:
            value = "_(no users)_"
        else:
            lines = []
            for u in users:
                uname = u.get("discord_username", "?")
                name_str = u.get("name", "?")
                did = u.get("discord_id", "?")
                lines.append(f"• {name_str} (@{uname}) — `{did}`")
            value = "\n".join(lines)
        embed.add_field(name=f"{name} ({agent_type})", value=value[:1024], inline=False)

    blocklist = data.get("blocklist", [])
    pending = data.get("pending_approvals", [])
    footer = f"Blocklist: {len(blocklist)} entries • Pending: {len(pending)}"
    embed.set_footer(text=footer)
    await message.channel.send(embed=embed)


async def handle_pending(message: discord.Message):
    pending = get_pending_approvals()
    if not pending:
        await message.channel.send("✅ Nenhum pedido pendente.")
        return

    embed = discord.Embed(
        title=f"🔐 Pedidos pendentes ({len(pending)})",
        color=0x9b59b6,
    )
    for i, req in enumerate(pending[:10], 1):
        user_mention = req.get("user_mention", "?")
        agent = req.get("agent", "?")
        request_text = req.get("request", "?")[:100]
        ts = req.get("timestamp", "?")
        embed.add_field(
            name=f"{i}. {user_mention} → {agent}",
            value=f"`{request_text}`\n_{ts}_",
            inline=False,
        )
    embed.set_footer(text="Responda: 'aprova @user <agent>' ou 'nega @user'")
    await message.channel.send(embed=embed)


async def handle_last_events(message: discord.Message, content_lower: str):
    m = re.search(r"(\d+)", content_lower)
    n = int(m.group(1)) if m else 5
    n = min(n, 50)  # cap at 50
    events = load_recent_events(n)
    if not events:
        await message.channel.send("_Nenhum evento registrado ainda._")
        return

    lines = [format_event_summary(e) for e in events]
    text = "\n".join(lines)
    if len(text) > 1900:
        text = text[:1900] + "\n_(truncated)_"
    embed = discord.Embed(
        title=f"📋 Últimos {len(events)} eventos",
        description=text,
        color=0x3498db,
    )
    await message.channel.send(embed=embed)


async def handle_approve(message: discord.Message, content: str):
    """
    Parse: 'aprova @user agent_key'
    Extracts discord mention (or ID) and agent_key (zeus/atena).
    """
    # Try to extract mention and agent
    m = re.match(r"aprova\s+<@!?(\d+)>\s+(\w+)", content, re.IGNORECASE)
    if not m:
        # Try plain discord_id
        m = re.match(r"aprova\s+(\d+)\s+(\w+)", content, re.IGNORECASE)
    if not m:
        await message.channel.send(
            "❓ Formato esperado: `aprova @user atena` ou `aprova 123456789 zeus`"
        )
        return

    user_id = m.group(1)
    agent_key = m.group(2).lower()

    if agent_key not in ["zeus", "atena"]:
        await message.channel.send(
            f"❌ Agent `{agent_key}` não existe. Use: zeus, atena."
        )
        return

    # Load, update, save
    try:
        data = load_authorized_users()
        agent_cfg = data.get("agents", {}).get(agent_key)
        if not agent_cfg:
            await message.channel.send(f"❌ Agent `{agent_key}` não configurado.")
            return

        whitelist = agent_cfg.get("authorized_user_discord_ids", [])
        if user_id in whitelist:
            await message.channel.send(f"ℹ️ User `{user_id}` já autorizado para `{agent_key}`.")
            return

        whitelist.append(user_id)
        agent_cfg["authorized_user_discord_ids"] = whitelist

        # Also add to details if possible (lookup user info best-effort)
        details = agent_cfg.setdefault("_authorized_users_detail", [])
        details.append({
            "discord_id": user_id,
            "discord_username": "unknown",
            "name": "unknown",
            "discord_role": "approved_by_zeus",
            "added": datetime.now(timezone.utc).date().isoformat(),
            "added_by": "zeus_admin",
        })

        # Remove from pending if present
        pending = data.get("pending_approvals", [])
        data["pending_approvals"] = [p for p in pending if str(p.get("user_discord_id")) != user_id]

        # Save
        with open(AUTH_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        await message.channel.send(
            f"✅ User `{user_id}` autorizado para `{agent_key}`. "
            f"`authorized-users.json` atualizado."
        )
        logger.info(f"Approved user {user_id} for agent {agent_key}")

    except Exception as e:
        logger.exception("approve failed")
        await message.channel.send(f"❌ Erro ao processar: {e}")


async def handle_deny(message: discord.Message, content: str):
    """Parse: 'nega @user' — removes from pending_approvals."""
    m = re.match(r"nega\s+<@!?(\d+)>", content, re.IGNORECASE)
    if not m:
        m = re.match(r"nega\s+(\d+)", content, re.IGNORECASE)
    if not m:
        await message.channel.send("❓ Formato: `nega @user` ou `nega 123456789`")
        return

    user_id = m.group(1)
    try:
        data = load_authorized_users()
        pending = data.get("pending_approvals", [])
        before = len(pending)
        data["pending_approvals"] = [p for p in pending if str(p.get("user_discord_id")) != user_id]
        after = len(data["pending_approvals"])

        with open(AUTH_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if before > after:
            await message.channel.send(f"❌ User `{user_id}` negado. {before - after} pedido(s) removido(s).")
        else:
            await message.channel.send(f"ℹ️ Nenhum pedido pendente encontrado para `{user_id}`.")
        logger.info(f"Denied user {user_id}")
    except Exception as e:
        logger.exception("deny failed")
        await message.channel.send(f"❌ Erro ao processar: {e}")


# ===== Entry point =====
def main():
    logger.info("=" * 60)
    logger.info("Zeus starting up...")
    logger.info(f"Log file: {LOG_FILE}")

    try:
        token = load_token()
        logger.info("Token loaded from 1Password (length: %d)", len(token))
    except Exception:
        logger.exception("Failed to load token — aborting")
        sys.exit(1)

    try:
        bot.run(token, log_handler=None)
    except discord.LoginFailure:
        logger.error("Invalid token — check 1Password item 'Discord Bot - Zeus'")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user — shutting down")
    except Exception:
        logger.exception("Unexpected error in bot.run")
        sys.exit(1)


if __name__ == "__main__":
    main()
