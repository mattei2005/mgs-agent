"""Reconcile the same occurrence and capture its live resource gate only."""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round41/probe.py'
original = prior.read_text()
code = original.replace("session='recovery-79cd082a-round41'", "session='recovery-79cd082a-round47'")
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
