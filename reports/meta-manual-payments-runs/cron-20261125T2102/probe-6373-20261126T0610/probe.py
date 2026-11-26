"""Repeat the inspected read-only probe for the same supervised occurrence.
No business writes, navigation, inputs, cron changes or messages.
Evidence goes to this round's immutable directory, never the prior round.
"""
from pathlib import Path
source = Path('/root/mgs-agent/reports/meta-manual-payments-runs/cron-20261125T2102/probe-6373-20261126T0552/probe.py')
code = source.read_text()
exec(compile(code, str(source), 'exec'), globals())
