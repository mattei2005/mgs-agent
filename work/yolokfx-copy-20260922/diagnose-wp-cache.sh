#!/usr/bin/env bash
set -Eeuo pipefail
sudo python3 - <<'PY'
import hashlib,json,os
roots=['/home/runcloud/webapps/yolokfx/wp-content/cache','/home/runcloud/webapps/yolokfx/wp-content/uploads/cache','/home/runcloud/webapps/yolokfx/wp-content/litespeed']
needles=[b'Get Free SHEIN Products Delivered to Your Home',b'Would you like to get free SHEIN products?']
hits=[]
for root in roots:
 if not os.path.isdir(root): continue
 for cur,dirs,files in os.walk(root):
  dirs.sort(); files.sort()
  for name in files:
   p=os.path.join(cur,name)
   try:
    if os.path.getsize(p)>5_000_000: continue
    d=open(p,'rb').read()
   except OSError: continue
   if any(n in d for n in needles):
    st=os.stat(p)
    hits.append({'path':p,'bytes':st.st_size,'mtime':st.st_mtime,'sha256':hashlib.sha256(d).hexdigest()})
print(json.dumps({'count':len(hits),'hits':hits},separators=(',',':')))
PY
sudo -u runcloud wp --path=/home/runcloud/webapps/yolokfx plugin list --status=active --format=json --fields=name,version,status --allow-root
