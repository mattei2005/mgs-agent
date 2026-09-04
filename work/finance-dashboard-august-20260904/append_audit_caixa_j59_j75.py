#!/usr/bin/env python3
import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path

path = Path('/root/mgs-agent/logs/events-audit.jsonl')
record = {
    'ts': datetime.now(timezone.utc).isoformat(),
    'agent': 'zeus',
    'event': 'finance_caixa_august_j59_j75_completed',
    'actor': 'Rodolfo Mattei',
    'authorization_message_id': '1545553235874545664',
    'thread_id': '1545426987756298340',
    'spreadsheet_id': '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak',
    'authorized_range': "CAIXA SINTETICO!J59:J75",
    'written_cells': ['J59', 'J60', 'J61', 'J62', 'J72', 'J73', 'J75'],
    'preserved_summary_formulas': ['J64', 'J67', 'J68', 'J69', 'J70', 'J71'],
    'preserved_spacers': ['J63', 'J65', 'J66', 'J74'],
    'write_http': 200,
    'formula_scope_diff': 'exact_7_cells',
    'validation': 'pass: formula/source parity 7/7; arithmetic J64,J67:J71,J77,J79:J81; zero displayed errors; independent live readback pass',
    'backup_sha256': '4e26e3fca4679a92cc260f1c460866f7e763ce79a6eb34bbbd7cf9ff94828748',
    'verification_sha256': '6db929e79fa559b6785f5c0908411d315a2fb72c9b828f3a015a70e5badaeb98',
    'skill_version': '0.1.7',
    'skill_sha256': 'ea126f007dde21d30e9c9903df30a01f834d2de29c50972166dd7d8ce4608646',
    'ledger_sha256': '4368a6c2f32a80939d825b228bff2c4f54472cae6811fd0e2b7dcf9ae7078e66',
    'checkpoint_id': 'ZEUS-FINANCE-DASH-AUGUST-20260904',
    'checkpoint_sha256': '394ec88ca895fd6d429eb0719d1c2bf8746bc5cdd4926f9bfbe3aff21a5da9ab',
    'inventory_sha256': '4a04f307c725dd3929d1062f0468fdfaa45c366ee2e0cc42a27223637abe6912',
}
line = json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n'
with path.open('a', encoding='utf-8') as handle:
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    handle.write(line)
    handle.flush()
    os.fsync(handle.fileno())
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
print(json.dumps({'status': 'pass', 'event': record['event'], 'authorization_message_id': record['authorization_message_id']}, separators=(',', ':')))
