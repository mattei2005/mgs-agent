"""Read-only reconciliation of the same occurrence and live PC1."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/probe.py'
original = source.read_text()
code = original.replace("session='recovery-79cd082a-round41'", "session='recovery-79cd082a-round50'")
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
