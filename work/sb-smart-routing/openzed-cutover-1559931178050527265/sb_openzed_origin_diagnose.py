import os,subprocess,json,sys
from pathlib import Path
code='''import pathlib,re,json,subprocess
root=pathlib.Path('/home/runcloud/webapps/boostingecon')
print('root_files', [f.name for f in root.iterdir()])
for base in [pathlib.Path('/etc/nginx-rc'),root]:
 for f in base.rglob('*'):
  if not f.is_file():continue
  if base==root and (len(f.relative_to(root).parts)>2 or f.name=='wp-config.php'):continue
  if f.suffix not in ['.php','.conf','.json'] or f.stat().st_size>300000:continue
  try:s=f.read_text(errors='replace')
  except OSError:continue
  if (base==root and f.name in ['index.php','routing.php']) or re.search(r'boostingecon|smart.?routing|jbfdigital',s,re.I):
   hits=[]
   for n,l in enumerate(s.splitlines(),1):
    if re.search(r'boostingecon|routing|jbfdigital|redirect|include|location|try_files|root |fastcgi|require',l,re.I) and not re.search(r'password|authorization|token|secret|api_key',l,re.I):hits.append([n,l[:600]])
   print(json.dumps({'file':str(f),'hits':hits[:25]}))
'''
password=subprocess.check_output(['op','item','get','Runcloud Server 03 - 46.4.95.117- zeus Acesso','--vault','MGS Conteúdo','--fields','label=password','--reveal'],stderr=subprocess.DEVNULL).strip()
r,w=os.pipe();os.write(w,password+b'\n');os.close(w)
try:
 cmd=['sshpass','-d',str(r),'ssh','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','ConnectTimeout=15','zeus@46.4.95.117','sudo -n python3 -']
 result=subprocess.run(cmd,input=code,pass_fds=(r,),capture_output=True,text=True,timeout=150)
 print('exit',result.returncode);print(result.stdout[:20000])
finally:os.close(r)
