"""
Events module — inter-agent communication via Discord webhook to Zeus channel.

Agents (Atena, future Hermes/Ares) call these functions to report lifecycle
events to Zeus. Zeus receives, displays, and maintains audit log.

All events are posted to ZEUS_CHANNEL_ID as embedded messages.
"""
import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord

logger = logging.getLogger("events")

# Events log — persistent audit trail
EVENTS_LOG_PATH = Path("/root/mgs-agent/logs/events-audit.jsonl")


def _write_audit_log(event: dict):
    """Append event to JSONL audit log."""
    try:
        EVENTS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


async def _post_to_zeus(bot: discord.Client, embed: discord.Embed) -> bool:
    """
    Post an embed to Zeus channel.

    `bot` is the discord.py Client/Bot instance of the agent sending the event.
    It uses bot's channel lookup to find Zeus channel.
    """
    from bots.shared.config import ZEUS_CHANNEL_ID
    try:
        channel = bot.get_channel(ZEUS_CHANNEL_ID)
        if channel is None:
            # fallback: try fetching
            channel = await bot.fetch_channel(ZEUS_CHANNEL_ID)
        if channel is None:
            logger.error(f"Could not resolve Zeus channel ID {ZEUS_CHANNEL_ID}")
            return False
        await channel.send(embed=embed)
        return True
    except discord.Forbidden:
        logger.error("Zeus channel access forbidden (permissions issue)")
        return False
    except Exception as e:
        logger.error(f"Failed to post event to Zeus: {e}")
        return False


async def report_pipeline_started(bot, agent_name: str, user_name: str,
                                    request_summary: str, metadata: Optional[dict] = None):
    """Notify Zeus that a pipeline has started."""
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "type": "pipeline_started",
        "timestamp": now,
        "agent": agent_name,
        "user": user_name,
        "request": request_summary,
        "metadata": metadata or {},
    }
    _write_audit_log(event)

    embed = discord.Embed(
        title="📋 Pipeline Started",
        description=f"**Agent:** {agent_name}\n**User:** {user_name}\n**Request:** `{request_summary}`",
        color=0x3498db,  # blue
        timestamp=datetime.now(timezone.utc),
    )
    if metadata:
        for key, value in metadata.items():
            embed.add_field(name=key, value=str(value), inline=True)
    await _post_to_zeus(bot, embed)


async def report_pipeline_paused(bot, agent_name: str, step: str, awaiting_from: str,
                                   context: Optional[str] = None):
    """Notify Zeus that a pipeline is paused for human review."""
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "type": "pipeline_paused",
        "timestamp": now,
        "agent": agent_name,
        "step": step,
        "awaiting_from": awaiting_from,
        "context": context,
    }
    _write_audit_log(event)

    embed = discord.Embed(
        title="⏸️ Pipeline Paused",
        description=f"**Agent:** {agent_name}\n**Step:** {step}\n**Awaiting:** {awaiting_from}",
        color=0xf39c12,  # orange
        timestamp=datetime.now(timezone.utc),
    )
    if context:
        embed.add_field(name="Context", value=context[:1000], inline=False)
    await _post_to_zeus(bot, embed)


async def report_pipeline_completed(bot, agent_name: str, user_name: str,
                                      duration_seconds: float, output_summary: str,
                                      output_url: Optional[str] = None):
    """Notify Zeus that a pipeline completed successfully."""
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "type": "pipeline_completed",
        "timestamp": now,
        "agent": agent_name,
        "user": user_name,
        "duration_seconds": duration_seconds,
        "output_summary": output_summary,
        "output_url": output_url,
    }
    _write_audit_log(event)

    mins, secs = divmod(int(duration_seconds), 60)
    duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    embed = discord.Embed(
        title="✅ Pipeline Completed",
        description=f"**Agent:** {agent_name}\n**User:** {user_name}\n**Duration:** {duration_str}",
        color=0x2ecc71,  # green
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Output", value=output_summary[:1000], inline=False)
    if output_url:
        embed.add_field(name="URL", value=output_url, inline=False)
    await _post_to_zeus(bot, embed)


async def report_error(bot, agent_name: str, step: str, error_message: str,
                         user_name: Optional[str] = None):
    """Notify Zeus of an error."""
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "type": "error",
        "timestamp": now,
        "agent": agent_name,
        "step": step,
        "user": user_name,
        "error": error_message,
    }
    _write_audit_log(event)

    embed = discord.Embed(
        title="❌ Error",
        description=f"**Agent:** {agent_name}\n**Step:** {step}",
        color=0xe74c3c,  # red
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Error", value=error_message[:1000], inline=False)
    if user_name:
        embed.add_field(name="User", value=user_name, inline=True)
    await _post_to_zeus(bot, embed)


async def report_auth_request(bot, agent_name: str, user_discord_id: int,
                                user_mention: str, request_summary: str):
    """Notify Zeus of a pending authorization request (unauthorized user made request)."""
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "type": "auth_request",
        "timestamp": now,
        "agent": agent_name,
        "user_discord_id": str(user_discord_id),
        "user_mention": user_mention,
        "request": request_summary,
    }
    _write_audit_log(event)

    embed = discord.Embed(
        title="🔐 Authorization Request",
        description=(
            f"**Agent:** {agent_name}\n"
            f"**User:** {user_mention} (`{user_discord_id}`)\n"
            f"**Request:** `{request_summary}`"
        ),
        color=0x9b59b6,  # purple
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="Action Required",
        value=(
            f"Reply in this channel:\n"
            f"• `aprova {user_mention} {agent_name.lower()}` — authorize\n"
            f"• `nega {user_mention}` — deny"
        ),
        inline=False,
    )
    await _post_to_zeus(bot, embed)


async def report_unauthorized_attempt(bot, agent_name: str, user_name: str,
                                         user_discord_id: int, request_summary: str):
    """Notify Zeus of an unauthorized access attempt (sent alongside auth_request,
    but this is purely informational for audit — auth_request is the actionable one)."""
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "type": "unauthorized_attempt",
        "timestamp": now,
        "agent": agent_name,
        "user": user_name,
        "user_discord_id": str(user_discord_id),
        "request": request_summary,
    }
    _write_audit_log(event)
    # no embed — auth_request already notified
