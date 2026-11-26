"""Same authorized occurrence: read-only reconciliation and PC1 inspection."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round90/probe.py'
code = source.read_text()
assert code.count('recovery-79cd082a-round90') == 1
code = code.replace('recovery-79cd082a-round90', 'recovery-79cd082a-round95')
exec(compile(code, str(Path(__file__)), 'exec'), globals())
