"""Read-only gate probe for the same occurrence, preserving later human gates."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round78/probe.py'
code = source.read_text()
old = 'recovery-79cd082a-round78'
assert code.count(old) == 1
code = code.replace(old, 'recovery-79cd082a-round80')
exec(compile(code, str(Path(__file__)), 'exec'), globals())
