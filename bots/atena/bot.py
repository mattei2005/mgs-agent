"""
Atena — Content Agent for MGS
Discord bot that handles content creation requests (REC articles, etc.)
only from authorized users in atena-content-agent channel.

MVP version: recognizes intents but does not yet execute the pipeline.
Pipeline integration comes in Part 4 after connectivity validation.
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

# Import shared modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from bots.shared.config import (
    ATENA_CHANNEL_ID,
    ATENA_NAME,
    GUILD_ID,
    PROJECT_ROOT,
    log_path,
)
from bots.shared.auth import is_authorized, get_user_details
from bots.shared import events


# ===== Logging setup =====
LOG_FILE = log_path(ATENA_NAME)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("atena")


# ===== Token loading (runtime from 1Password, never persisted) =====
def load_token() -> str:
    """Fetch Discord bot token from 1Password at runtime."""
    vault = os.getenv("OP_DEFAULT_VAULT", "MGS Conteúdo")
    try:
        result = subprocess.run(
            [
                "op", "item", "get",
                "Discord Bot - Atena",
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

bot = commands.Bot(command_prefix="!atena ", intents=intents)


# ===== Event handlers =====
@bot.event
async def on_ready():
    logger.info(f"Atena logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Guild count: {len(bot.guilds)}")
    for guild in bot.guilds:
        logger.info(f"  - {guild.name} ({guild.id})")
    logger.info(f"Listening only on channel {ATENA_CHANNEL_ID}")


@bot.event
async def on_message(message: discord.Message):
    # Ignore own messages
    if message.author == bot.user:
        return

    # Only respond in Atena's designated channel
    if message.channel.id != ATENA_CHANNEL_ID:
        return

    # Ignore bots
    if message.author.bot:
        return

    # Authorization check
    if not is_authorized(message.author.id, "atena"):
        logger.warning(
            f"UNAUTHORIZED message from {message.author} "
            f"(ID: {message.author.id}) in #{message.channel.name}: "
            f"'{message.content[:100]}'"
        )
        await message.channel.send(
            f"🔒 {message.author.mention}, você não está autorizado a usar Atena. "
            f"Solicite autorização ao Zeus admin."
        )
        # Report auth request to Zeus
        try:
            await events.report_auth_request(
                bot, "Atena", message.author.id, message.author.mention,
                message.content[:100]
            )
        except Exception:
            logger.exception("Failed to report auth_request to Zeus")
        return

    # Authorized — route intent
    user = get_user_details(message.author.id, "atena")
    username = user.get("name") if user else str(message.author)
    logger.info(f"Message from {username} ({message.author.id}): '{message.content}'")

    content = message.content.strip().lower()

    try:
        # Intent detection (simple for MVP)
        if any(kw in content for kw in ["status", "tá tudo ok", "health", "tudo certo"]):
            await handle_status(message)
        elif content in ["templates", "lista verticais", "list templates"] or "templates" in content:
            await handle_list_templates(message)
        elif content in ["sites", "lista sites", "list sites"] or content.startswith("sites"):
            await handle_list_sites(message)
        elif content.startswith("rec ") or "faz um rec" in content or "create rec" in content:
            await handle_rec_create(message, content)
        else:
            await message.channel.send(
                f"Olá {username}! Comandos disponíveis:\n"
                f"• `rec [card] no [site]` — criar REC article\n"
                f"• `templates` — listar templates disponíveis\n"
                f"• `sites` — listar sites configurados\n"
                f"• `status` — health check"
            )
    except Exception as e:
        logger.exception("Unhandled error in on_message intent routing")
        try:
            await events.report_error(bot, "Atena", "on_message", str(e), username)
        except Exception:
            logger.exception("Failed to report error to Zeus")


# ===== Intent handlers =====
async def handle_status(message: discord.Message):
    """Report system health."""
    now = datetime.now(timezone.utc).isoformat()
    py_version = sys.version.split()[0]
    dpy_version = discord.__version__

    response = (
        f"📊 **Atena Status**\n"
        f"• Agent: Content Agent\n"
        f"• Channel: <#{ATENA_CHANNEL_ID}>\n"
        f"• Python: `{py_version}`\n"
        f"• discord.py: `{dpy_version}`\n"
        f"• UTC: `{now}`\n"
        f"• Status: ✅ Online (MVP mode, pipeline integration pending)"
    )
    await message.channel.send(response)


async def handle_list_templates(message: discord.Message):
    """List available REC templates."""
    templates_dir = PROJECT_ROOT / "skills" / "content-generate-rec" / "templates"
    if not templates_dir.exists():
        await message.channel.send("❌ Templates directory not found.")
        return

    templates = sorted(templates_dir.glob("rec-*.md"))
    if not templates:
        await message.channel.send("📝 Nenhum template REC encontrado.")
        return

    lines = ["📝 **Templates disponíveis:**"]
    for tpl in templates:
        name = tpl.stem
        lines.append(f"• `{name}`")
    await message.channel.send("\n".join(lines))


async def handle_list_sites(message: discord.Message):
    """List configured sites from data/sites.json."""
    sites_path = PROJECT_ROOT / "data" / "sites.json"
    if not sites_path.exists():
        await message.channel.send("❌ sites.json not found.")
        return

    try:
        with open(sites_path, "r", encoding="utf-8") as f:
            sites = json.load(f)
    except Exception as e:
        await message.channel.send(f"❌ Erro ao ler sites.json: {e}")
        return

    if not sites:
        await message.channel.send("🌐 Nenhum site configurado.")
        return

    lines = ["🌐 **Sites configurados:**"]
    for key, meta in sites.items():
        vertical = meta.get("vertical", "?") if isinstance(meta, dict) else "?"
        lines.append(f"• `{key}` → vertical `{vertical}`")
    await message.channel.send("\n".join(lines))


async def handle_rec_create(message: discord.Message, content: str):
    """
    MVP: detect rec_create intent + parse card/site + confirm detection.
    Does NOT execute pipeline yet — that comes in Part 4.
    """
    original = message.content  # preserve original casing

    # Simple parsing — look for "rec <card> no <site>" or "rec <card> em <site>"
    # Also accept "faz um rec do <card> em <site>"
    import re
    patterns = [
        r"rec\s+(.+?)\s+(?:no|em|on)\s+(\S+)",
        r"faz\s+um\s+rec\s+(?:do|de)\s+(.+?)\s+(?:no|em|on)\s+(\S+)",
        r"create\s+rec\s+(.+?)\s+on\s+(\S+)",
    ]

    card_name = None
    site_key = None
    for pattern in patterns:
        m = re.search(pattern, original, re.IGNORECASE)
        if m:
            card_name = m.group(1).strip().strip('"\'')
            site_key = m.group(2).strip().strip('"\'').strip('.,;:!?')
            break

    if not card_name or not site_key:
        await message.channel.send(
            "🤔 Não consegui identificar o card e o site na sua mensagem.\n"
            "Formato esperado: `rec [card_name] no [site_key]`\n"
            "Exemplo: `rec HSBC Premier no eggbev`"
        )
        return

    # Resolve username for event reporting
    user_details = get_user_details(message.author.id, "atena")
    username = user_details.get("name") if user_details else str(message.author)

    # Report to Zeus BEFORE responding on channel
    try:
        await events.report_pipeline_started(
            bot, "Atena", username,
            f"rec '{card_name}' no {site_key}",
            {"card": card_name, "site": site_key}
        )
    except Exception:
        logger.exception("Failed to report pipeline_started to Zeus")

    # Confirm parsing (MVP — no pipeline execution yet)
    response = (
        f"✅ **Pedido recebido e reconhecido**\n"
        f"• Intent: `rec_create`\n"
        f"• Card: `{card_name}`\n"
        f"• Site: `{site_key}`\n\n"
        f"⚠️ _MVP mode: detecção OK, mas integração com pipeline ainda não implementada (Parte 4).\n"
        f"Quando ativarmos, o pipeline irá:_\n"
        f"1. Validar site em `data/sites.json`\n"
        f"2. Carregar template da vertical\n"
        f"3. Executar 11 steps com 4 paradas obrigatórias\n"
        f"4. Reportar progresso neste canal"
    )
    await message.channel.send(response)
    logger.info(f"rec_create detected: card='{card_name}' site='{site_key}' requester_id={message.author.id}")


# ===== Entry point =====
def main():
    logger.info("=" * 60)
    logger.info("Atena starting up...")
    logger.info(f"Log file: {LOG_FILE}")

    try:
        token = load_token()
        logger.info("Token loaded from 1Password (length: %d)", len(token))
    except Exception:
        logger.exception("Failed to load token — aborting")
        sys.exit(1)

    try:
        bot.run(token, log_handler=None)  # Use our logging, not discord's default
    except discord.LoginFailure:
        logger.error("Invalid token — check 1Password item 'Discord Bot - Atena'")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user — shutting down")
    except Exception:
        logger.exception("Unexpected error in bot.run")
        sys.exit(1)


if __name__ == "__main__":
    main()
