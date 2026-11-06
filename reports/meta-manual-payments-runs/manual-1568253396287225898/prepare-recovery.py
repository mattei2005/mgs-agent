from pathlib import Path
B=Path(__file__).parent
p=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/read_pc1_accounts_list.py')
s=p.read_text()
s=s.replace("created=False;pid=None;wid=None;es=[];text='';last={};results=[]", "created=False;pid=None;wid=None;es=[];text='';last={};results=[];action_log=[]")
s=s.replace("d=call(x)\n if d.get", "d=call(x);action_log.append({'request':x,'result':d});(B/'input-diagnostics.json').write_text(json.dumps(action_log,ensure_ascii=False,indent=2))\n if d.get")
old="t=lookup[aid];cap();gate();ss=search();assert len(ss)==1,'search_not_unique';act({'action':'click','element':ss[0]['index']});act({'action':'key','keys':'ctrl+a'});act({'action':'type','text':t['name']});deadline=time.monotonic()+35;prefix=t['name']+' ID: '+aid+' '"
new="""t=lookup[aid];cap();gate();ss=search();assert len(ss)==1,'search_not_unique'
  # Previous verified-lost element click permits pixel rung on this control.
  scale=last.get('bounds_scale',1);bx,by,bw,bh=ss[0]['bounds'];xy=[round((bx+min(180,bw/2))/scale),round((by+bh/2)/scale)]
  act({'action':'click','coordinate':xy});gate();act({'action':'key','keys':'ctrl+a'});act({'action':'type','text':t['name']});time.sleep(2);cap();gate();prefix=t['name']+' ID: '+aid+' '
  if not any(l.startswith(prefix)for l in text.splitlines()):
   snap(aid+'-after-pixel-input')
   # Do not replay successful input. Only escalate if search remains empty.
   ss=search();assert len(ss)==1,'search_not_unique_after_pixel'
   field=ss[0];assert not field.get('value')and not any(t['name']in str(e.get('value',''))for e in es),'search_nonempty_unmatched_stop'
   scale=last.get('bounds_scale',1);bx,by,bw,bh=field['bounds'];xy=[round((bx+min(180,bw/2))/scale),round((by+bh/2)/scale)]
   act({'action':'click','coordinate':xy,'delivery_mode':'foreground'});gate();act({'action':'key','keys':'ctrl+a','delivery_mode':'foreground'});act({'action':'type','text':t['name'],'delivery_mode':'foreground'});time.sleep(2);cap();gate()
  deadline=time.monotonic()+15"""
assert old in s;s=s.replace(old,new)
(B/'read-accounts-recovery.py').write_text(s);(B/'read-accounts-recovery.py').chmod(0o600)
print(str(B/'read-accounts-recovery.py'))
