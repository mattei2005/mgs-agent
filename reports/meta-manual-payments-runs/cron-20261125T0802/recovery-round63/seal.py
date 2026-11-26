"""Seal independently inspected resource evidence; never complete business."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/seal.py'
original = source.read_text()
code = original.replace('recovery-round40/approved-elements.json', 'recovery-round62/approved-elements.json')
code = code.replace('New account D and later tick H35/D2 remain separate.', 'New account D and all later native-tick pending fields remain separate.')
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
