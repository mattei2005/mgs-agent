"""Seal the observed resource gate without changing queue or business state."""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round41/seal.py'
code = prior.read_text().replace('recovery-round40/approved-elements.json', 'recovery-round43/approved-elements.json')
assert code != prior.read_text()
exec(compile(code, str(Path(__file__)), 'exec'), globals())
