"""Seal this round's inspected resource gate; no queue/business mutation."""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round41/seal.py'
original = prior.read_text()
code = original.replace('recovery-round40/approved-elements.json', 'recovery-round44/approved-elements.json')
assert code != original
exec(compile(code, str(Path(__file__)), 'exec'), globals())
