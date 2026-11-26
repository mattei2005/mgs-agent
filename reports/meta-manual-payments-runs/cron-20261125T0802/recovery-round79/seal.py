"""Seal this round's actual visual diagnosis; business and queue stay unchanged."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round78/seal.py'
code = source.read_text()
old = 'recovery-round77/approved-elements.json'
assert code.count(old) == 1
code = code.replace(old, 'recovery-round78/approved-elements.json')
exec(compile(code, str(Path(__file__)), 'exec'), globals())
