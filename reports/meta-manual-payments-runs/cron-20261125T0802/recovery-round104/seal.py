"""Seal actual round-104 evidence after pixel inspection, no business mutation."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round98/seal.py').read_text()
changes = {
    'Seal actual round-98 reads': 'Seal actual round-104 reads',
    "B.parent/'recovery-round97/approved-retry-elements.json'": "B.parent/'recovery-round103/approved-retry-elements.json'"
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, __file__, 'exec'), globals())
