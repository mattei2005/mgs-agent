"""Same occurrence reconciliation and fresh PC1 captures; no UI input."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/probe.py'
original = source.read_text()
code = original.replace("session='recovery-79cd082a-round41'", "session='recovery-79cd082a-round67'")
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
