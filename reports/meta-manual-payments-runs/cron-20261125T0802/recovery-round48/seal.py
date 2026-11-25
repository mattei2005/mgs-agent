"""Seal the actual visual resource gate; no business or queue mutation."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/seal.py'
original = source.read_text()
code = original.replace('recovery-round40/approved-elements.json', 'recovery-round47/approved-elements.json')
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
