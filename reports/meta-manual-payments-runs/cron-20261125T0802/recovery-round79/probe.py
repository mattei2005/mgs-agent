"""Same-occurrence read-only gate reconciliation; preserve business and queue."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round78/probe.py'
code = source.read_text()
old = 'recovery-79cd082a-round78'
assert code.count(old) == 1
code = code.replace(old, 'recovery-79cd082a-round79')
exec(compile(code, str(Path(__file__)), 'exec'), globals())
