# Hermes v2026.5.16 / v0.14.0 MGS relevance notes

Use when Rodolfo asks whether the May 16 2026 Hermes release helps MGS operations before approving an update.

## Release facts to verify live

Check installed version and pending commits:

```bash
hermes --version
# Example observed on MGS: Hermes Agent v0.14.0 (2026.5.16)
# Output may also say: Update available: N commits behind — run 'hermes update'
```

Read release notes via GitHub API if needed:

```bash
python3 - <<'PY'
import json, urllib.request
url='https://api.github.com/repos/NousResearch/hermes-agent/releases/tags/v2026.5.16'
req=urllib.request.Request(url, headers={'Accept':'application/vnd.github+json','User-Agent':'MGS-Zeus'})
data=json.load(urllib.request.urlopen(req, timeout=30))
print(data['name'])
print(data['published_at'])
print(data['body'][:4000])
PY
```

## MGS-relevant improvements

```text
Feature                                  Why it matters for MGS
-----------------------------------------|-----------------------------------------------
Discord channel history backfill          Less “what is this thread about?” context loss
Per-turn file-mutation verifier footer    Better evidence after patches/writes
LSP semantic diagnostics on write         Faster detection of code/config mistakes
Cold-start performance wave               Less downtime/latency after gateway restart
180x faster browser_console               Faster browser-based audits when needed
Tool-error sanitization                    Safer against prompt injection through errors
Native clarify buttons on Discord         Better approval UX on mobile
/handoff live                             Potentially safer model/profile transitions
Codex app-server runtime                  May stabilize long Codex/OAuth runs
```

## Executive framing for Rodolfo

This release helps Hermes stability, UX, diagnostics, and startup latency. It does **not** by itself fix REC production architecture. REC speed still depends on cleaning the Atena/REC layers: runner-first flow, short prompts, `template_key` contract, validators, image gates, and taxonomy/cache telemetry.

Recommended order when REC architecture is actively being fixed:
1. Patch/validate REC architecture first while the current runtime is known-good.
2. Then update Hermes in a separate phase with backup + restart + validation.
3. Then run one controlled REC draft benchmark.

## Safety note

For large deltas (100+ commits behind), treat update as medium-risk infrastructure work: backup profiles, inspect local patches/status, update, verify `HEAD..origin/main == 0`, restart/validate Zeus and Atena, and run targeted smoke tests. Do not combine with publication of a real article in the same unverified step.