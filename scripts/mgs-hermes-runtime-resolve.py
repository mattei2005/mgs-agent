#!/usr/bin/env python3
"""Read-only MGS runtime identity for legacy and native PM launchers."""
import argparse,ast,json,os,pathlib,subprocess,sys

def resolve(launcher):
 p=pathlib.Path(launcher).resolve(strict=True)
 first=p.open().readline().strip()
 if first.startswith('#!'):
  python=pathlib.Path(first[2:])
  if python.is_absolute() and python.name.startswith('python'):
   repo=python.parent.parent.parent
   if (repo/'gateway/run.py').is_file() and python.is_file():return {'repo':str(repo),'python':str(python),'test_python':str(python),'launcher':str(p),'kind':'legacy-venv'}
 # Hermes' native machine-readable boundary; never infer a source tree from a shell shebang.
 result=subprocess.run([str(p),'--print-runtime-command'],capture_output=True,text=True,timeout=25,check=True)
 command=json.loads(result.stdout)
 if not isinstance(command,list) or len(command)<4 or command[1:3]!=['-I','-c']:raise ValueError('Unsupported native runtime command')
 roots=[]
 for node in ast.walk(ast.parse(command[3])):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='insert' and isinstance(node.func.value,ast.Attribute) and node.func.value.attr=='path' and isinstance(node.func.value.value,ast.Name) and node.func.value.value.id=='sys' and len(node.args)==2 and isinstance(node.args[0],ast.Constant) and node.args[0].value==0 and isinstance(node.args[1],ast.Constant) and isinstance(node.args[1].value,str):roots.append(node.args[1].value)
 if len(set(roots))!=1:raise ValueError('Ambiguous native source root')
 repo=pathlib.Path(roots[0]).resolve(strict=True)
 if not (repo/'gateway/run.py').is_file():raise ValueError('Native source root lacks gateway')
 # This native reader does not initialize or repair an environment.
 code='import sys;from pathlib import Path;sys.path.insert(0,'+repr(str(repo))+');from pm.environments import selected_venv,venv_python;print(venv_python(selected_venv(Path('+repr(str(repo))+'))))'
 q=subprocess.run([command[0],'-I','-c',code],capture_output=True,text=True,timeout=20,check=True)
 python=pathlib.Path(q.stdout.strip()).absolute()
 if not python.is_file():raise ValueError('Selected native Python is missing')
 if not os.access(python,os.X_OK):raise ValueError('Selected native Python is not executable')
 testcode='import sys;from pathlib import Path;sys.path.insert(0,'+repr(str(repo))+');from pm.testenv import testenv_python;p=testenv_python(Path('+repr(str(repo))+'));print(str(p) if p else "")'
 t=subprocess.run([command[0],'-I','-c',testcode],capture_output=True,text=True,timeout=20,check=True)
 return {'repo':str(repo),'python':str(python),'test_python':t.stdout.strip() or None,'bootstrap_python':command[0],'launcher':str(p),'kind':'native-pm'}

def main():
 a=argparse.ArgumentParser();a.add_argument('--launcher',default='/root/.local/bin/hermes');a.add_argument('--field',choices=['repo','python','test_python','launcher','kind']);o=a.parse_args()
 try:
  d=resolve(o.launcher);print(d[o.field] if o.field else json.dumps(d))
 except Exception as e:print('runtime-resolution refused: '+str(e),file=sys.stderr);return 1
 return 0
if __name__=='__main__':sys.exit(main())
