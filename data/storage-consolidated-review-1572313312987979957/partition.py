"""Partition the complete fresh metadata observation into non-additive operational review units."""
import pathlib,json,gzip,collections,re,os
from typing import Any
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent;P=pathlib.Path('/root/.hermes/secure-backups/storage-consolidated-review-1572313312987979957');assert not(O/'review-units.json').exists()
cp=json.loads((R/'data/agent-checkpoints.json').read_text())['checkpoints'];roots=[]
def add(root,family,depth=1):roots.append((str(root),family,depth))
add(R/'apps/finance-system/private','finance',1);add(R/'apps/finance-system','finance_sources',1)
for profile in pathlib.Path('/root/.hermes/profiles').iterdir():
 if profile.is_dir():
  for name in ['workspace','workspaces','work','codex-pilots']:add(profile/name,'agent_work',1)
  for name in ['artifacts','reports']:add(profile/name,'media_evidence',1)
  add(profile/'state-snapshots','snapshots',1)
add(R/'work','agent_work',1);add(R/'backups','backups',1);add(pathlib.Path('/root/.hermes/secure-backups'),'backups',2);add(R/'reports','reports',1);add(R/'data','operational_data',1);add(R/'tmp','temporary',1);add(pathlib.Path('/tmp'),'temporary',1);add(pathlib.Path('/var/tmp'),'temporary',1)
roots.sort(key=lambda x:-len(x[0]));inodes:dict[tuple[int,int],list[Any]]={};units:dict[str,dict[str,Any]]={};total=0;counts=collections.Counter()
def classify(row):
 p=row['p']
 if row['c']=='cache_paused_owner_choice':return(row['unit'],'cache_paused')
 if re.search(r'^/root/\.hermes/hermes-agent[^/]*(?:/|$)',p):return('/'.join(p.split('/')[:4]),'runtime_code')
 for root,family,depth in roots:
  if p==root:return(root+'::direct',family)
  if p.startswith(root+'/'):
   parts=p[len(root)+1:].split('/')
   if len(parts)==1 and row['k']!='directory':return(root+'::direct',family)
   return(root+'/'+ '/'.join(parts[:depth]),family)
 return(row['unit'],row['c'])
for fs in json.loads((O/'metadata-summary.json').read_text())['filesystems']:
 for line in gzip.open(fs['ledger'],'rt'):
  row=json.loads(line);unit,family=classify(row);u=units.setdefault(unit,dict(unit=unit,family=family,file=0,directory=0,link=0,other=0,logical_bytes=0,unique_allocated_bytes=0,newest_mtime_ns=0,oldest_mtime_ns=row['t']));u[row['k']]+=1;u['logical_bytes']+=row['s']if row['k']=='file'else 0;u['newest_mtime_ns']=max(u['newest_mtime_ns'],row['t']);u['oldest_mtime_ns']=min(u['oldest_mtime_ns'],row['t']);key=(row['d'],row['i']);old=inodes.get(key)
  if old is None:inodes[key]=[row['b'],unit]
  elif old[1]!=unit:old[1]='[shared_between_review_units]'
  counts[row['k']]+=1
for size,unit in inodes.values():
 if unit=='[shared_between_review_units]':continue
 units[unit]['unique_allocated_bytes']+=size
shared=sum(size for size,unit in inodes.values()if unit=='[shared_between_review_units]');observed=sum(x['unique_allocated_bytes']for x in units.values())+shared;expected=sum(f['unique_allocated_bytes']for f in json.loads((O/'metadata-summary.json').read_text())['filesystems']);assert observed==expected
for u in units.values():
 ids=re.findall(r'(?<!\d)\d{17,20}(?!\d)',u['unit']);u['checkpoint_matches']=[{k:c.get(k)for k in ['id','state','next_step','source']}for c in cp if any(i in c.get('id','')for i in ids)];u['GiB']=round(u['unique_allocated_bytes']/1024**3,4)
result=dict(units=sorted(units.values(),key=lambda x:-x['unique_allocated_bytes']),shared_between_units_bytes=shared,all_bytes_occupied_not_deletion_eligibility=True,total_allocated_bytes=observed,counts=dict(counts));(O/'review-units.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');reviewfamilies={'finance','finance_sources','agent_work','media_evidence','reports','operational_data','backups','snapshots','runtime_code','temporary'};selected=[u for u in result['units']if u['family']in reviewfamilies and u['unique_allocated_bytes']>=32*1024**2];(O/'material-review-units.json').write_text(json.dumps(selected,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'all_units':len(units),'material_units':len(selected),'partition_reconciled':True,'top_material':[{'unit':u['unit'],'family':u['family'],'GiB':u['GiB'],'files':u['file'],'checkpoint_states':[c['state'][:110]for c in u['checkpoint_matches']]}for u in selected[:35]]},ensure_ascii=False))
