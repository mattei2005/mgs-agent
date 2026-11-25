"""Read-only authority and resource reconciliation for the same operation."""
from pathlib import Path
import os
os.umask(0o077)
os.environ['HERMES_SESSION_ID']='recovery-79cd082a-round38'
source=Path(__file__).parent.parent/'recovery-round31/probe.py'
exec(compile(source.read_bytes(),str(source),'exec'),globals())
