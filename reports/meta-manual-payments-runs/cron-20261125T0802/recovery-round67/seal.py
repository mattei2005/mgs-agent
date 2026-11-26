"""Seal this round's inspected resource evidence; do not close the request."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/seal.py'
original = source.read_text()
code = original.replace('recovery-round40/approved-elements.json', 'recovery-round66/approved-elements.json')
code = code.replace('New account D and later tick H35/D2 remain separate.', 'New account D and all later native-tick pending fields remain separate.')
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
