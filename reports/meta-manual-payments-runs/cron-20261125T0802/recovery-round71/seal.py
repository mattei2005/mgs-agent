"""Seal inspected resource evidence; keep separate later native-tick work."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/seal.py'
code = source.read_text()
changes = {
    'recovery-round40/approved-elements.json': 'recovery-round70/approved-elements.json',
    'New account D and later tick H35/D2 remain separate.': 'New account D and later native-tick pending fields remain separate. Latest 21:02 tick has already published metrics52 and H35; its D9 UI pending belongs to its own occurrence, not this historical D5 recovery.'
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, str(Path(__file__)), 'exec'), globals())
