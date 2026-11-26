"""Same occurrence, probe_only: GET reconciliation and no-input capture."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round41/probe.py').read_text()
changes = {
    "session='recovery-79cd082a-round41'": "session='recovery-79cd082a-round120'",
    'cron-20261125T1402/closure-receipt.json': 'cron-20261125T2102/closure-receipt.json',
    "assert j['last_dispatch']['scheduled_at']==later['scheduled_at']=='2026-11-25T14:02:00-05:00'": "assert j['last_dispatch']['scheduled_at']==later['scheduled_at']=='2026-11-25T21:02:00-05:00'",
    "assert set(later['pending_new_historical_d'])==set(source['pending_account_ids'])": "assert set(source['pending_account_ids']) <= set(later['pending_new_historical_d']); assert set(later['pending_new_historical_d']) - set(source['pending_account_ids']) == {'1770569568407466'}",
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
code = code.split("os.environ['HERMES_CUA_DRIVER_CMD']", 1)[0]
exec(compile(code, __file__, 'exec'), globals())
capture = (base / 'recovery-round97/capture-retry.py').read_text()
old = "session='recovery-79cd082a-round97-capture'"
assert capture.count(old) == 1
capture = capture.replace(old, "session='recovery-79cd082a-round120-capture'")
old = "re.search('Save As|Salvar como',w.get('title',''),re.I)"
assert capture.count(old) == 1
capture = capture.replace(old, "re.search('Save As|Salvar como|Windows Security|Segurança do Windows|passkey',w.get('title',''),re.I)")
exec(compile(capture, __file__, 'exec'), globals())
