"""
Auth module — validates Discord user IDs against authorized-users.json whitelist.

Each bot (Zeus, Atena) has its own whitelist in agents.<bot>.authorized_user_discord_ids.
Zeus only accepts Super Admin (Rodolfo). Atena only accepts Raquel.
"""
from typing import Optional
from .config import load_authorized_users


def is_authorized(discord_id: int, agent_key: str) -> bool:
    """
    Check if a Discord ID is authorized for a given agent.

    Args:
        discord_id: numeric Discord user ID of the message sender
        agent_key: "zeus" or "atena" (matches keys in authorized-users.json > agents)

    Returns:
        True if discord_id is in the agent's whitelist, False otherwise.
    """
    try:
        data = load_authorized_users()
        agent_config = data.get("agents", {}).get(agent_key, {})
        whitelist = agent_config.get("authorized_user_discord_ids", [])
        # Compare as strings because JSON stores IDs as strings
        return str(discord_id) in [str(x) for x in whitelist]
    except Exception as e:
        # Fail-closed: on any error, deny
        print(f"[auth] ERROR loading authorization: {e}", flush=True)
        return False


def get_user_details(discord_id: int, agent_key: str) -> Optional[dict]:
    """
    Return the _authorized_users_detail dict for a given Discord ID, if authorized.

    Returns None if not authorized or agent_key invalid.
    """
    try:
        data = load_authorized_users()
        agent_config = data.get("agents", {}).get(agent_key, {})
        details = agent_config.get("_authorized_users_detail", [])
        for user in details:
            if str(user.get("discord_id")) == str(discord_id):
                return user
        return None
    except Exception:
        return None
