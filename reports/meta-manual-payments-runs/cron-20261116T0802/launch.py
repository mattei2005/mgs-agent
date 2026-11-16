import sys,shutil,runpy
from pathlib import Path
R=Path(shutil.which('hermes')).resolve().parents[2]
sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
target=sys.argv[1];sys.argv=sys.argv[1:]
runpy.run_path(target,run_name='__main__')
