"""Seal fresh observed resource gate, preserving the existing supervisor owner."""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round41/seal.py'
code = prior.read_text().replace('recovery-round40/approved-elements.json', 'recovery-round42/approved-elements.json')
assert code != prior.read_text()
exec(compile(code, str(Path(__file__)), 'exec'), globals())
