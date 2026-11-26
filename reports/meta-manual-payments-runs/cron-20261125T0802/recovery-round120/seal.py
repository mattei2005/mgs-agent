"""Seal only observed round120 evidence; no business/queue mutations.

Actual approved and Save As captures were inspected with vision_analyze in
this round: Accounts BM155263197283282, six tabs, no visible auth challenge,
Save As still open, no historical D proof. AX independently shows Rodolfo.
"""
from pathlib import Path
prior = Path(__file__).parent.parent / 'recovery-round119/seal.py'
exec(compile(prior.read_text(), __file__, 'exec'), globals())
