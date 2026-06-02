import json
import os
import sys
from pathlib import Path
from honcho import Honcho

WORKSPACE = os.getenv("HONCHO_WORKSPACE", "mgs-agents")
API_KEY = os.getenv("HONCHO_API_KEY")
if not API_KEY:
    print("BLOCKED: HONCHO_API_KEY missing")
    sys.exit(2)

path = Path(__file__).with_name("sanitized_mgs_events.json")
payload = json.loads(path.read_text())
items = payload.get("items", [])

honcho = Honcho(workspace_id=WORKSPACE, api_key=API_KEY, environment="production")
zeus = honcho.peer("zeus")
atena = honcho.peer("atena")
system = honcho.peer("mgs-system")

session = honcho.session("mgs-sanitized-ops-spike-001")

messages = [
    system.message("Dataset policy: sanitized MGS operational events only. No credentials. Honcho conclusions are hypotheses; Zeus must validate against canonical logs before reporting or acting."),
]

for i, item in enumerate(items[-80:], 1):
    source = item.get("source", "unknown")
    if "line" in item:
        content = f"Sanitized log event {i} from {source}: {item['line']}"
    else:
        content = f"Sanitized audit event {i} from {source}: {json.dumps(item.get('data', {}), ensure_ascii=False)}"
    # Route Atena-related logs to Atena, Zeus logs to Zeus, generic to system.
    if "atena" in source.lower() or "atena" in content.lower():
        messages.append(atena.message(content))
    elif "zeus" in source.lower() or "zeus" in content.lower():
        messages.append(zeus.message(content))
    else:
        messages.append(system.message(content))

session.add_messages(messages)

queries = [
    "What operational risks or recurring patterns should Zeus investigate from these sanitized MGS events? Return concise bullets and mark uncertainty.",
    "Based only on the sanitized events, is there evidence of a confirmed incident, or only hypotheses that require canonical log validation?",
    "What should Zeus do next operationally before alerting Rodolfo?",
]

print(f"workspace={WORKSPACE}")
print(f"session={session.id}")
print(f"messages_ingested={len(messages)}")
for q in queries:
    print("\nQUERY:", q)
    try:
        resp = zeus.chat(q, target=atena)
    except TypeError:
        resp = zeus.chat(q)
    print("RESPONSE:", getattr(resp, "content", resp))
