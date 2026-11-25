"""Same-occurrence read-only preflight; no business replay or queue mutation."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/probe.py'
original = source.read_text()
code = original.replace("session='recovery-79cd082a-round41'", "session='recovery-79cd082a-round55'")
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
