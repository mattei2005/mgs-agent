import sys,json,pathlib,subprocess,os
P=pathlib.Path('/root/mgs-agent/work/sb-smart-routing/openzed-cutover-1559931178050527265');plan=json.loads((P/'plan.json').read_text());mode=sys.argv[1]
selected=plan['plans'][:1] if mode=='canary' else plan['plans']
groups={}
for p in selected:
 for r in json.loads(p['after']['ROUTES']):groups.setdefault(p['domain'],{})[r['route']]=r['url']
REMOTE=r'''import json,pathlib,hashlib,os,stat,re,subprocess,shutil
spec=json.loads(SPEC)
backup=pathlib.Path('/root/mgs-route-backups/1559931178050527265');backup.mkdir(parents=True,exist_ok=True,mode=0o700)
results=[]
for domain,mapping in spec.items():
 root=pathlib.Path('/home/runcloud/webapps')/domain;target=root/'.htaccess';st=target.stat();before=target.read_bytes();oldhash=hashlib.sha256(before).hexdigest()
 b=backup/(domain+'.'+oldhash+'.htaccess');
 if not b.exists():b.write_bytes(before);b.chmod(0o600)
 original=backup/(domain+'.original.htaccess')
 if not original.exists():original.write_bytes(before);original.chmod(0o600)
 # Freeze complete file, transform only URL tokens belonging to authorized identities.
 lines=before.decode().splitlines(keepends=True);seen={};changed=0;out=[]
 for line in lines:
  m=re.match(r'^(RewriteRule\s+\^)([^\s]+)(\s+)(https?://[^\s]+)(\s+\[[^\]]+\].*)$',line.rstrip('\r\n'))
  if m:
   raw=m.group(2);route=raw.split('(')[0].rstrip('$')
   if route in mapping:
    assert raw==route+'(/)?$',('unexpected pattern',route)
    assert '$1' in m.group(4) and 'QSA' in m.group(5) and 'R=302' in m.group(5),('redirect flags',route)
    seen[route]=seen.get(route,0)+1;newurl=mapping[route]+'$1'
    if newurl!=m.group(4):
     line=m.group(1)+m.group(2)+m.group(3)+newurl+m.group(5)+('\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else '');changed+=1
  out.append(line)
 assert set(seen)==set(mapping) and all(v==1 for v in seen.values()),('missing/duplicate rule',domain,len(seen),len(mapping))
 after=''.join(out).encode();newhash=hashlib.sha256(after).hexdigest()
 stage=backup/(domain+'.'+newhash+'.candidate.htaccess')
 if not stage.exists():stage.write_bytes(after);stage.chmod(0o600)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==oldhash,'concurrent file write before cutover'
 if changed:
  # Same filesystem atomic replacement; staging stays nonpublic/private until cutover.
  staging=pathlib.Path('/home/runcloud')/('.mgs-route-stage-1559931178050527265-'+domain)
  with staging.open('xb') as f:f.write(after);f.flush();os.fsync(f.fileno())
  os.chown(staging,st.st_uid,st.st_gid);os.chmod(staging,stat.S_IMODE(st.st_mode));os.replace(staging,target)
 assert target.read_bytes()==after and target.stat().st_uid==st.st_uid and stat.S_IMODE(target.stat().st_mode)==stat.S_IMODE(st.st_mode),'file/permission readback failed'
 results.append({'domain':domain,'path':str(target),'routes':len(mapping),'changed':changed,'before_sha256':oldhash,'after_sha256':newhash,'backup':str(b),'original_backup':str(original),'readback':'PASS','owner_mode_preserved':True})
print(json.dumps(results))
'''
code=REMOTE.replace('spec=json.loads(SPEC)','spec=json.loads('+repr(json.dumps(groups))+')')
pw=subprocess.check_output(['op','item','get','Runcloud Server 03 - 46.4.95.117- zeus Acesso','--vault','MGS Conteúdo','--fields','label=password','--reveal'],stderr=subprocess.DEVNULL).strip();rd,wr=os.pipe();os.write(wr,pw+b'\n');os.close(wr)
try:
 rr=subprocess.run(['sshpass','-d',str(rd),'ssh','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','zeus@46.4.95.117','sudo -n python3 -'],input=code,pass_fds=(rd,),capture_output=True,text=True,timeout=150)
 if rr.returncode:
  (P/('origin-'+mode+'-error.txt')).write_text(rr.stderr);print('origin_write_failed',rr.returncode);sys.exit(1)
 data=json.loads(rr.stdout);(P/('origin-'+mode+'-receipt.json')).write_text(json.dumps(data,indent=2));print(json.dumps(data))
finally:os.close(rd)
