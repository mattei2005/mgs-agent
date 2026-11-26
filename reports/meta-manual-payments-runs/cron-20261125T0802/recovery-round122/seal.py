"""Seal round122 actual read-only evidence after vision inspection.

Both captures inspected with vision_analyze this round: Accounts is BM
155263197283282 with six Chrome tabs and no visible auth challenge;
it is not historical D. Native Save As remains open, not Windows Security.
Approved AX confirms Rodolfo; lease release was read back unlocked.
"""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round119/seal.py'
exec(compile(prior.read_text(), __file__, 'exec'), globals())
