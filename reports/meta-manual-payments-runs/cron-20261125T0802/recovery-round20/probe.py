"""Same-operation round20: reconcile authority and read PC1 only."""
from pathlib import Path
source20 = Path(__file__).parent.parent / 'recovery-round19' / 'probe.py'
exec(compile(source20.read_text(), str(source20), 'exec'), globals())
