"""Read-only reconciliation and PC1 surface probe for same occurrence."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/probe.py'
code = source.read_text()
changes = {
    "session='recovery-79cd082a-round41'": "session='recovery-79cd082a-round74'",
    "cron-20261125T1402/closure-receipt.json": "cron-20261125T2102/closure-receipt.json",
    "assert j['last_dispatch']['scheduled_at']==later['scheduled_at']=='2026-11-25T14:02:00-05:00'": "assert j['last_dispatch']['scheduled_at']==later['scheduled_at']=='2026-11-25T21:02:00-05:00'",
    "assert set(later['pending_new_historical_d'])==set(source['pending_account_ids'])": "assert set(source['pending_account_ids']) <= set(later['pending_new_historical_d']); assert set(later['pending_new_historical_d']) - set(source['pending_account_ids']) == {'1770569568407466'}"
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, str(Path(__file__)), 'exec'), globals())
