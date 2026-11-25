"""Seal the actually inspected resource gate; preserve queue and business state."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round41/seal.py'
original = source.read_text()
code = original.replace('recovery-round40/approved-elements.json', 'recovery-round50/approved-elements.json')
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
