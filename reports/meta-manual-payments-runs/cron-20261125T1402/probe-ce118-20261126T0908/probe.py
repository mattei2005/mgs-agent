"""Local evidence-only probe for the same authorized occurrence."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round10/probe.py'
code = source.read_text()
old = "assert source['scheduled_at']==j['last_dispatch']['scheduled_at']=='2026-11-25T14:02:00-05:00'"
new = """assert source['scheduled_at']=='2026-11-25T14:02:00-05:00'
assert row['source_key']=='native:zeus:2ee720363d7d:20261125T1402:ui-missing'
later=load(ROOT/'reports/meta-manual-payments-runs/cron-20261126T0802/closure-receipt.json')
assert j['last_dispatch']['scheduled_at']==later['scheduled_at']=='2026-11-26T08:02:00-05:00'
assert later['fresh_metrics_count']==len(c['account_ids'])
save('newer-native-receipt.json',later)"""
assert code.count(old)==1
code=code.replace(old,new)
old_session="or'recovery-ce11800-round10'"
assert code.count(old_session)==1
code=code.replace(old_session,"or'probe-ce11800-20261126T0908'")
print('Read-only predecessor SHA256:',hashlib.sha256(source.read_bytes()).hexdigest(),flush=True)
exec(compile(code,str(Path(__file__)),'exec'),globals())
