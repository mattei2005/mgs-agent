"""Same authorized occurrence: read-only reconciliation and capture."""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round41/probe.py'
original = prior.read_text()
code = original.replace("session='recovery-79cd082a-round41'", "session='recovery-79cd082a-round45'")
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
