import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
REPORT = BASE / "manual_briefing_report.json"
OUT = BASE / "manual_briefing_discord.md"

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

def rows_table(title, headers, rows):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    lines = [title, ""]
    lines.append("  ".join(str(headers[i]).ljust(widths[i]) for i in range(len(headers))))
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        lines.append("  ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))))
    return "```text\n" + "\n".join(lines) + "\n```"

if not REPORT.exists():
    print(f"BLOCKED: missing {REPORT}", file=sys.stderr)
    sys.exit(2)

obj = json.loads(REPORT.read_text())
signals = obj["deterministic_signals"]
content_rows = [[k, str(v)] for k, v in signals["content_top_counts"]]
agent_rows = []
for agent in sorted(signals["gateway_tool_errors_by_agent"]):
    agent_rows.append([
        agent,
        str(signals["gateway_tool_errors_by_agent"].get(agent, 0)),
        str(signals["gateway_provider_ttfb_by_agent"].get(agent, 0)),
        str(signals["gateway_credential_safety_blocks_by_agent"].get(agent, 0)),
    ])

created = obj.get("created_at", datetime.now(timezone.utc).isoformat())
assessment = obj.get("zeus_assessment", {})

md = []
md.append("Honcho briefing experimental — MGS")
md.append("")
md.append(f"Status: `{obj.get('status')}`")
md.append(f"Workspace: `{obj.get('workspace')}`")
md.append(f"Gerado: `{created}`")
md.append("")
md.append(rows_table("Sinais de conteúdo", ["Categoria", "Ocorrências"], content_rows))
md.append("")
md.append(rows_table("Gateway por agente", ["Agente", "Tool errors", "Provider TTFB", "Credential blocks"], agent_rows))
md.append("")
md.append("Veredito Zeus:")
md.append("")
md.append(f"- Conteúdo: {assessment.get('content', 'n/a')}")
md.append(f"- Autorização: {assessment.get('authorization', 'n/a')}")
md.append(f"- Gateway: {assessment.get('gateway', 'n/a')}")
md.append(f"- Produção: {assessment.get('production_recommendation', 'n/a')}")
md.append("")
md.append("Próximo passo pendente: usar manualmente sob demanda; não ativar cron até o sumarizador ficar mais determinístico por domínio.")
text = "\n".join(md).strip() + "\n"

hits = scan(text)
if hits:
    print(f"BLOCKED: secret pattern in rendered briefing: {hits}", file=sys.stderr)
    sys.exit(3)

OUT.write_text(text)
print(text)
