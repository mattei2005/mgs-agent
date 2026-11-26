"""Same authorized occurrence: GET reconciliation, no-input probe only."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round120/probe.py').read_text()
assert code.count('round120') == 2
code = code.replace('round120', 'round122')
exec(compile(code, __file__, 'exec'), globals())
