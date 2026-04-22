"""
Config module — loads environment variables and constants for MGS Agent bots.

Called by zeus/bot.py and atena/bot.py to get tokens, channel IDs, and paths.
Uses python-dotenv to source /root/mgs-agent/.env.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Project root
PROJECT_ROOT = Path("/root/mgs-agent")
ENV_PATH = PROJECT_ROOT / ".env"
AUTH_PATH = PROJECT_ROOT / "data" / "authorized-users.json"
LOGS_DIR = PROJECT_ROOT / "logs"

# Load .env
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Discord server
GUILD_ID = 1185714635991679006  # MGS Digital Corp

# Roles (for future mention/permission use)
ROLE_SUPER_ADMIN = 1185978575782936586
ROLE_ADMIN = 1496260941787168848
ROLE_CONTEUDO = 1496254887883702323
ROLE_ZEUS = 1496306777933877369
ROLE_ATENA = 1496308166466600963

# Bot-specific config (loaded from .env)
ZEUS_TOKEN = os.getenv("DISCORD_BOT_TOKEN_ZEUS", "")
ZEUS_CHANNEL_ID = 1496267442899521627  # zeus-admin-agent
ZEUS_NAME = "Zeus"

ATENA_TOKEN = os.getenv("DISCORD_BOT_TOKEN_ATENA", "")
ATENA_CHANNEL_ID = 1496267571543019653  # atena-content-agent
ATENA_NAME = "Atena"


def load_authorized_users():
    """Load authorization data from data/authorized-users.json."""
    if not AUTH_PATH.exists():
        raise FileNotFoundError(f"Authorization config not found: {AUTH_PATH}")
    with open(AUTH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def log_path(bot_name: str) -> Path:
    """Return path to bot-specific log file."""
    LOGS_DIR.mkdir(exist_ok=True, parents=True)
    return LOGS_DIR / f"bot-{bot_name.lower()}.log"
