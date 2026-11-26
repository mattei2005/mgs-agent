"""Seal round121's actual read-only observations after visual inspection.

vision_analyze confirmed Accounts BM155263197283282, six browser tabs,
no visible auth challenge, no historical D, and native Save As still open.
The exact approved AX independently confirmed Rodolfo. No inputs sent.
"""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round119/seal.py'
exec(compile(prior.read_text(), __file__, 'exec'), globals())
