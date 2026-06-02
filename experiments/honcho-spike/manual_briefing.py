import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from honcho import Honcho

WORKSPACE = os.getenv("HONCHO_WORKSPACE", "mgs-agents")
API_KEY = os.getenv("HONCHO_API_KEY")
if not API_KEY:
    print("BLOCKED: HONCHO_API_KEY missing")
    sys.exit(2)

BASE = Path(__file__).resolve().parent
REPORT_PATH = BASE / "targeted_rounds_report.json"
if not REPORT_PATH.exists():
    print(f"BLOCKED: missing {REPORT_PATH}; run run_targeted_rounds.py first")
    sys.exit(2)

SECRET_PATTERNS = [
    r'hch-v3-[A-Za-z0-9]+',
    r'sk-[A-Za-z0-9_\-]+',
    r'github_pat_[A-Za-z0-9_]+',
    r'ghp_[A-Za-z0-9_]+',
    r'xox[baprs]-[A-Za-z0-9_\-]+',
    r'AKIA[A-Za-z0-9]{16}',
    r'(?i)(password|token|secret|api[_-]?key|authorization)[=:]\s*\S+',
]

def scan(text: str):
    return [p for p in SECRET_PATTERNS if re.search(p, text, re.I)]

def one_line(s: str, n=900):
    s = " ".join(str(s).split())
    return s[:n] + ("..." if len(s) > n else "")

report = json.loads(REPORT_PATH.read_text())
content_events = json.loads((BASE / "sanitized_content_events.json").read_text()).get("items", [])
gateway_events = json.loads((BASE / "sanitized_gateway_events.json").read_text()).get("items", [])
auth_events = json.loads((BASE / "sanitized_auth_events.json").read_text()).get("items", [])

# Deterministic validation layer: summarize aggregates from canonical sanitized files.
content_counts = {}
for it in content_events:
    if it.get("source") == "content-aggregate":
        d = it.get("data", {})
        content_counts[d.get("category", "unknown")] = d.get("count_in_tail", 0)

gateway_counts = {}
for it in gateway_events:
    if str(it.get("source", "")).endswith("/aggregate"):
        gateway_counts[it.get("agent", "unknown")] = it.get("data", {}).get("counts_in_tail", {})

auth_summary = {
    "events": len(auth_events),
    "honcho_status": report.get("rounds", {}).get("auth", {}).get("status"),
}

honcho = Honcho(workspace_id=WORKSPACE, api_key=API_KEY, environment="production")
zeus = honcho.peer("zeus")
system = honcho.peer("mgs-system")
session = honcho.session("mgs-manual-briefing-experimental-001")

briefing_input = {
    "policy": "Sanitized aggregates only. Honcho suggests hypotheses; Zeus validates against deterministic counts and canonical logs before reporting.",
    "content_counts": content_counts,
    "gateway_counts": gateway_counts,
    "auth_summary": auth_summary,
    "honcho_round_statuses": {k: v.get("status") for k, v in report.get("rounds", {}).items()},
    "latest_honcho_responses": {
        k: [one_line(r.get("response", ""), 500) for r in v.get("responses", [])]
        for k, v in report.get("rounds", {}).items()
    },
}

payload = json.dumps(briefing_input, ensure_ascii=False, indent=2)
hits = scan(payload)
if hits:
    print("BLOCKED: secret pattern in briefing payload", hits)
    sys.exit(3)

session.add_messages([
    system.message("Manual experimental MGS briefing input. Use only as hypothesis layer; canonical validation remains with Zeus."),
    zeus.message(payload),
])

question = (
    "Create a concise executive operations briefing for Rodolfo from this sanitized input. "
    "Separate: confirmed deterministic signals, Honcho hypotheses, and recommended next validation. "
    "Do not claim incidents are confirmed unless deterministic counts support it."
)
try:
    resp = zeus.chat(question, target=system, session=session.id)
except TypeError:
    try:
        resp = zeus.chat(question, session=session.id)
    except TypeError:
        resp = zeus.chat(question)

honcho_text = str(getattr(resp, "content", resp))

# Zeus deterministic executive layer: use counts directly, not Honcho text, for final decision.
content_top = sorted(content_counts.items(), key=lambda kv: kv[1], reverse=True)
gateway_tool_errors = {a: c.get("tool_errors", 0) for a, c in gateway_counts.items()}
gateway_ttfb = {a: c.get("provider_ttfb_or_retry", 0) for a, c in gateway_counts.items()}
gateway_cred = {a: c.get("credential_safety_blocks", 0) for a, c in gateway_counts.items()}

zeus_brief = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "workspace": WORKSPACE,
    "status": "experimental_manual_briefing_complete",
    "deterministic_signals": {
        "content_top_counts": content_top[:8],
        "gateway_tool_errors_by_agent": gateway_tool_errors,
        "gateway_provider_ttfb_by_agent": gateway_ttfb,
        "gateway_credential_safety_blocks_by_agent": gateway_cred,
        "auth_events_sanitized_count": len(auth_events),
    },
    "zeus_assessment": {
        "content": "Strongest signal. Image lookup/quality, runner failures, WordPress/REST, provider TTFB, and tooling dependencies are the recurring investigation lanes.",
        "authorization": "No current pending approvals indicated by this sanitized run; Honcho mixed credential safety/config with authorization, so keep auth briefing deterministic.",
        "gateway": "Aggregates are useful, but Honcho did not reason well over this domain. Zeus should use deterministic counters first.",
        "production_recommendation": "Use as manual experimental briefing only. Do not schedule cron until summarizer is more deterministic and domain-specific.",
    },
    "honcho_briefing_raw": honcho_text,
}

out = BASE / "manual_briefing_report.json"
out.write_text(json.dumps(zeus_brief, ensure_ascii=False, indent=2))
brief_text = json.dumps(zeus_brief, ensure_ascii=False)
hits = scan(brief_text)
print(f"briefing_report={out}")
print(f"secret_scan={'PASS' if not hits else 'FAIL'}")
if hits:
    print("hits=", hits)
    sys.exit(4)
print(json.dumps(zeus_brief, ensure_ascii=False, indent=2)[:7000])
