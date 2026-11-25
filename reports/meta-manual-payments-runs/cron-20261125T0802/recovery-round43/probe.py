"""Fresh bounded read-only reconciliation of the same authorized occurrence."""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round41/probe.py'
code = prior.read_text().replace("session='recovery-79cd082a-round41'", "session='recovery-79cd082a-round43'")
assert code != prior.read_text()
exec(compile(code, str(Path(__file__)), 'exec'), globals())
