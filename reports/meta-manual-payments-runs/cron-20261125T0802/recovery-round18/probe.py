"""Read-only reconciliation for the same historical-D recovery occurrence.
Reuse the inspected round17 diagnostic, isolating immutable round18 evidence.
No browser input, business writes or queue mutation.
"""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round17' / 'probe.py'
exec(compile(source.read_text(), str(source), 'exec'), globals())
