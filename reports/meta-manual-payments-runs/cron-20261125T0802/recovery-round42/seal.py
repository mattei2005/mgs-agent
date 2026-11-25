"""Seal fresh read-only evidence after actual inspection of both round42 captures."""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round41/seal.py'
code = prior.read_text().replace("recovery-round40/approved-elements.json", "recovery-round41/approved-elements.json")
assert code != prior.read_text()
exec(compile(code, str(Path(__file__)), 'exec'), globals())
