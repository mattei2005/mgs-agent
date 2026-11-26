"""Read-only same-occurrence probe; preserve completed financial layers."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round75/probe.py'
code = source.read_text()
old = 'recovery-79cd082a-round75'
assert code.count(old) == 1
code = code.replace(old, 'recovery-79cd082a-round76')
exec(compile(code, str(Path(__file__)), 'exec'), globals())
