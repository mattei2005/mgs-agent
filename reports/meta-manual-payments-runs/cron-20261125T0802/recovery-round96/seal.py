"""Seal this round's actual pixel inspection; preserve supervisor ownership."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round90/seal.py'
code = source.read_text()
assert code.count('recovery-round89/approved-elements.json') == 1
code = code.replace('recovery-round89/approved-elements.json', 'recovery-round95/approved-elements.json')
exec(compile(code, str(Path(__file__)), 'exec'), globals())
