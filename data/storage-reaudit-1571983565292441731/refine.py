"""Refine the saved inventory only; no second filesystem crawl."""
from typing import Any
import pathlib,json,gzip,collections
OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-reaudit-1571983565292441731')
AREAS=['/root/mgs-agent/apps/finance-system','/root/mgs-agent/data','/root/mgs-agent/backups','/root/mgs-agent/tmp','/root/mgs-agent/reports','/root/.hermes/profiles/zeus','/root/.hermes/profiles/ares','/root/.hermes/profiles/atena','/root/.hermes/secure-backups/hermes-update/20261103-phase4-1567354570823172209']
inodes={};groups={};cluster_data=json.load(open(OUT/'postgres-clusters.json'));cluster_roots={r['path']for r in cluster_data};backup_controls=[]
for line in gzip.open(PRIVATE/'metadata-root.jsonl.gz','rt'):
 r=json.loads(line);p=r['p'];area=next((a for a in AREAS if p==a or p.startswith(a+'/')),None)
 if not area:continue
 rel=p[len(area):].strip('/').split('/');depth=2 if area.endswith('finance-system')or area.endswith('phase4-1567354570823172209')else 1;group=area+'/'+ '/'.join(rel[:depth])if rel[0]else area+'/[root_metadata]'
 g=groups.setdefault(group,dict(path=group,area=area,file=0,directory=0,link=0,other=0,logical_bytes=0,allocated_bytes_unique=0));g[r['k']]+=1
 if r['k']=='file':g['logical_bytes']+=r['s']
 inode=(r['d'],r['i'])
 if inode not in inodes:inodes[inode]=[r['b'],group,area]
 else:
  x=inodes[inode]
  if x[2]!=area:x[1]='[shared_between_selected_areas]';x[2]='[shared]'
  elif x[1]!=group:x[1]=area+'/[shared_between_subgroups]'
for b,g,area in inodes.values():
 row=groups.setdefault(g,dict(path=g,area=area,file=0,directory=0,link=0,other=0,logical_bytes=0,allocated_bytes_unique=0));row['allocated_bytes_unique']+=b
result: dict[str, Any] = dict(note='Detailed partitions of selected areas, already included in the full ledger. Do not add to parent/category totals. Cross-area and cross-subgroup hardlinks credited once in explicit shared buckets.',groups=sorted(groups.values(),key=lambda x:x['allocated_bytes_unique'],reverse=True))
(OUT/'detailed-areas.json').write_text(json.dumps(result,indent=2)+'\n')
for area in AREAS:
 print('AREA',area)
 for r in [x for x in result['groups']if x['area']==area][:8]:print(json.dumps(dict(path=r['path'],GiB=round(r['allocated_bytes_unique']/1024**3,3),files=r['file'])))
print('DETAILED_UNIQUE_GIB',round(sum(x['allocated_bytes_unique']for x in result['groups'])/1024**3,3))
