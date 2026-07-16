#!/usr/bin/env python3
import csv,json
from pathlib import Path
RUN=Path('/root/mgs-agent/work/sb-broadcast-23-30-20260716');PLAN=json.loads((RUN/'plan.json').read_text(encoding='utf-8'))['templates'];OUT=RUN/'rollback-csv';OUT.mkdir(exist_ok=True)
fields=['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2','APPROVAL']
for x in PLAN:
 r=json.loads(Path(x['backup']).read_text(encoding='utf-8'));m=r.get('MESSAGES') or [];m=json.loads(m) if isinstance(m,str) else m
 dst=OUT/(Path(x['csv']).name)
 with dst.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\r\n',quoting=csv.QUOTE_ALL);w.writeheader()
  for q in sorted(m,key=lambda z:int(z.get('MESSAGE_ID') or 0)):
   w.writerow({'MESSAGE ID':q.get('MESSAGE_ID'),'TEXT':q.get('TEXT',''),'DESCRIPTION':q.get('DESCRIPTION',''),'IMAGE':q.get('IMAGE',''),'CTA 1':q.get('CTA_1') or q.get('CTA 1') or '','LINK 1':q.get('LINK_1') or q.get('LINK 1') or '','CTA 2':q.get('CTA_2') or q.get('CTA 2') or '','LINK 2':q.get('LINK_2') or q.get('LINK 2') or '','TEXT 2':q.get('TEXT_2') or q.get('TEXT 2') or '','APPROVAL':''})
print(json.dumps({'rollback_csvs':len(list(OUT.glob('*.csv'))),'path':str(OUT)}))
