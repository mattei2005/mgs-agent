"""Reconcile this same request and capture PC1 without input."""
from pathlib import Path
import os
os.umask(0o077)
source = Path(__file__).parent.parent / 'recovery-round21/probe.py'
exec(compile(source.read_text(), str(source), 'exec'), globals())
