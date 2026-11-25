"""Read-only reconciliation of operation 79cd082a20c22a736307765f."""
from pathlib import Path
import os
os.umask(0o077)
source = Path(__file__).parent.parent / 'recovery-round21/probe.py'
exec(compile(source.read_text(), str(source), 'exec'), globals())
