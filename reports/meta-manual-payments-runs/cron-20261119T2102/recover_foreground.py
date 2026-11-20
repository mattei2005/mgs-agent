import os,sys,shutil,runpy
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
import tools.computer_use_tool as cu
original=cu.handle_computer_use
def foreground_inputs(args,*a,**kw):
    if args.get('action') in ('click','type','key'):
        args={**args,'delivery_mode':'foreground'}
    return original(args,*a,**kw)
cu.handle_computer_use=foreground_inputs
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/read_pc1_accounts_list.py')
sys.argv=[str(S),*sys.argv[1:]]
runpy.run_path(str(S),run_name='__main__')
