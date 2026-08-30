#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml

BASE = Path("/root/mgs-agent")
THREAD_ID = "1541578556037927053"
source = (BASE / f"data/ares/discord/thread-prompts/{THREAD_ID}.txt").read_text().strip()
versioned = yaml.safe_load((BASE / "profiles/ares-config.yaml").read_text())["discord"]["channel_prompts"][THREAD_ID].strip()
resolved = subprocess.run(
    ["hermes", "config", "get", f"discord.channel_prompts.{THREAD_ID}"],
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
result = {
    "thread_id": THREAD_ID,
    "all_strings": all(isinstance(value, str) for value in (source, versioned, resolved)),
    "source_equals_versioned": source == versioned,
    "source_equals_resolved": source == resolved,
    "bytes": len(source.encode()),
    "sha256": hashlib.sha256(source.encode()).hexdigest(),
}
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if all((result["all_strings"], result["source_equals_versioned"], result["source_equals_resolved"])) else 2)
