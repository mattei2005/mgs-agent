"""Probe-only same occurrence, latest native tick reconciled; no UI input."""
from pathlib import Path
base = Path(__file__).parent.parent
preamble = (base / 'recovery-round41/probe.py').read_text().split("os.environ['HERMES_CUA_DRIVER_CMD']", 1)[0]
changes = {
    "session='recovery-79cd082a-round41'": "session='recovery-79cd082a-round123'",
    'cron-20261125T1402/closure-receipt.json': 'cron-20261126T0802/closure-receipt.json',
    "assert j['last_dispatch']['scheduled_at']==later['scheduled_at']=='2026-11-25T14:02:00-05:00'": "assert j['last_dispatch']['scheduled_at']==later['scheduled_at']=='2026-11-26T08:02:00-05:00'",
    "assert set(later['pending_new_historical_d'])==set(source['pending_account_ids'])": "assert set(source['pending_account_ids']) <= set(later['pending_new_historical_d']); assert set(later['pending_new_historical_d']) - set(source['pending_account_ids']) == {'1770569568407466'}",
}
for old, new in changes.items():
    assert preamble.count(old) == 1, old
    preamble = preamble.replace(old, new)
exec(compile(preamble, __file__, 'exec'), globals())
capture = (base / 'recovery-round97/capture-retry.py').read_text()
changes = {
    "session='recovery-79cd082a-round97-capture'": "session='recovery-79cd082a-round123-capture'",
    "re.search('Save As|Salvar como',w.get('title',''),re.I)": "re.search('Save As|Salvar como|Windows Security|Segurança do Windows|passkey',w.get('title',''),re.I)",
}
for old, new in changes.items():
    assert capture.count(old) == 1, old
    capture = capture.replace(old, new)
exec(compile(capture, __file__, 'exec'), globals())
