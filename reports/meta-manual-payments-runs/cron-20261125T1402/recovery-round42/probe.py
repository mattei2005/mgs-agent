"""Read-only probe for the same authorized occurrence; no UI inputs."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round40/probe.py'
code = source.read_text()
assert code.count("or'recovery-ce11800-round40'") == 1
code = code.replace("or'recovery-ce11800-round40'", "or'recovery-ce11800-round42'")
print('Read-only predecessor SHA256:', hashlib.sha256(source.read_bytes()).hexdigest(), flush=True)
exec(compile(code, str(Path(__file__)), 'exec'), globals())
