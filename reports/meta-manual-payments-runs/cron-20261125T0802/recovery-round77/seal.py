"""Seal only the pixel-inspected resource gate; no business or queue mutation."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/seal.py'
code = source.read_text()
changes = {
    'recovery-round40/approved-elements.json': 'recovery-round76/approved-elements.json',
    'New account D and later tick H35/D2 remain separate.': 'New account D and later native-tick pending fields remain separate. Latest 21:02 tick has published metrics52 and H35; its D9 UI pending belongs to its own occurrence, not this historical D5 recovery. Related occurrence 6373afb33275674610c06b6a is waiting_human: preserve that gate and do not reactivate it.'
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, str(Path(__file__)), 'exec'), globals())
