#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
sudo python3 - "$WP" <<'PY'
import hashlib,json,os,stat,sys
root=sys.argv[1]
needle=b'Get Free SHEIN Products Delivered to Your Home'
new=b'Get Free Products Delivered to Your Home'
hits=[]
for cur,dirs,files in os.walk(root):
    dirs[:]=[d for d in dirs if d not in {'.git','node_modules','cache','uploads'}]
    for name in files:
        path=os.path.join(cur,name)
        try:
            if os.path.getsize(path)>5_000_000: continue
            data=open(path,'rb').read()
        except (OSError,PermissionError):
            continue
        if needle in data or new in data:
            st=os.lstat(path)
            hits.append({'path':path,'realpath':os.path.realpath(path),'is_symlink':os.path.islink(path),'bytes':st.st_size,'mtime':st.st_mtime,'old':needle in data,'new':new in data,'sha256':hashlib.sha256(data).hexdigest()})
print(json.dumps({'count':len(hits),'hits':hits},separators=(',',':')))
for slug in ('sh1-g002','sh2-g002','sh1-g001','sh2-g001'):
    p=os.path.join(root,'quiz','us',slug,'index.html')
    st=os.stat(p)
    print(json.dumps({'slug':slug,'path':p,'realpath':os.path.realpath(p),'bytes':st.st_size,'mtime':st.st_mtime,'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()},separators=(',',':')))
PY
sudo -u runcloud wp --path="$WP" option get home --allow-root
sudo -u runcloud wp --path="$WP" option get siteurl --allow-root
