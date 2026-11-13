"""Lossless native-zstd preservation; no original writes/deletes or SQLite opens."""
import subprocess, hashlib
from pathlib import Path
ZSTD='/usr/bin/zstd'
MAX_PACKED=1024**3

def sha(path):
 return subprocess.check_output(['sha256sum','--',str(path)],text=True).split()[0]

def memory_gate(required):
 free=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 if free<required:raise RuntimeError('RAM_CAPACITY_GATE')

def check_base(path,expected):
 if not expected or sha(path)!=expected:raise ValueError('BASE_HASH_MISMATCH')

def encode(source,base=None):
 size=Path(source).stat().st_size;bs=Path(base).stat().st_size if base else 0
 memory_gate(3*(size+bs)+1024**3)
 cmd=[ZSTD,'-q','-3','--single-thread','-M2048MB','--check','-c']
 if base:cmd+=['--patch-from='+str(base)]
 cmd+=['--',str(source)]
 r=subprocess.run(cmd,capture_output=True,timeout=220)
 if r.returncode:raise RuntimeError('ZSTD_ENCODE_FAILED_RC_'+str(r.returncode)+':'+r.stderr.decode(errors='replace')[:500])
 if len(r.stdout)>MAX_PACKED:raise RuntimeError('PACKED_SIZE_BUDGET_EXCEEDED')
 return r.stdout

def decode(packed,base=None,base_sha=None,expected_size=0):
 bs=Path(base).stat().st_size if base else 0
 memory_gate(3*(expected_size+bs)+1024**3)
 if base:check_base(base,base_sha)
 cmd=[ZSTD,'-q','-d','-c','-M2048MB','--check']
 if base:cmd+=['--patch-from='+str(base)]
 r=subprocess.run(cmd,input=packed,capture_output=True,timeout=220)
 if r.returncode:raise RuntimeError('ZSTD_DECODE_FAILED_RC_'+str(r.returncode))
 if len(r.stdout)!=expected_size:raise RuntimeError('DECODE_SIZE_MISMATCH')
 return r.stdout
