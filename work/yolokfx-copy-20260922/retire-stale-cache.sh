#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
CACHE="$WP/wp-content/cache/all/quiz/us"
BACKUP=/home/runcloud/backups/yolokfx-direct-quiz-copy-recovery-20260923T023052Z
CACHE_BACKUP="$BACKUP/wp-fastest-cache-before"
MOVED=0
rollback() {
  set +e
  if [[ "$MOVED" == 1 ]]; then
    for slug in sh1-g002 sh2-g002; do
      if sudo test -d "$CACHE_BACKUP/$slug" && ! sudo test -e "$CACHE/$slug"; then
        sudo mv "$CACHE_BACKUP/$slug" "$CACHE/$slug"
      fi
    done
  fi
  printf 'CACHE_ROLLBACK=%s\n' "$CACHE_BACKUP" >&2
}
on_error() { rc=$?; trap - ERR; rollback; exit "$rc"; }
trap on_error ERR
sudo test -d "$CACHE/sh1-g002"
sudo test -d "$CACHE/sh2-g002"
sudo test ! -e "$CACHE_BACKUP/sh1-g002"
sudo test ! -e "$CACHE_BACKUP/sh2-g002"
sudo python3 - "$CACHE/sh1-g002" "$CACHE/sh2-g002" <<'PY'
import hashlib,json,os,sys
rows=[]
for root in sys.argv[1:]:
 files=[]
 for cur,dirs,names in os.walk(root):
  dirs.sort(); names.sort()
  for name in names:
   p=os.path.join(cur,name); data=open(p,'rb').read()
   files.append({'path':os.path.relpath(p,root),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'old_title':b'Get Free SHEIN Products Delivered to Your Home' in data})
 assert len(files)==1 and files[0]['path']=='index.html' and files[0]['old_title']
 rows.append({'root':root,'files':files})
print(json.dumps({'stale_cache_confirmed':rows},separators=(',',':')))
PY
sudo mkdir -p "$CACHE_BACKUP"
sudo mv "$CACHE/sh1-g002" "$CACHE_BACKUP/sh1-g002"
MOVED=1
sudo mv "$CACHE/sh2-g002" "$CACHE_BACKUP/sh2-g002"
sudo test ! -e "$CACHE/sh1-g002"
sudo test ! -e "$CACHE/sh2-g002"
sudo test -s "$CACHE_BACKUP/sh1-g002/index.html"
sudo test -s "$CACHE_BACKUP/sh2-g002/index.html"
python3 - <<'PY'
import json,ssl,urllib.request
rows=[]
for slug in ('sh1-g002','sh2-g002'):
 req=urllib.request.Request(f'https://yolokfx.com/quiz/us/{slug}/',headers={'User-Agent':'Mozilla/5.0 MGS-QA/1.0','Cache-Control':'no-cache'})
 with urllib.request.urlopen(req,timeout=30,context=ssl.create_default_context()) as r:
  html=r.read().decode('utf-8','replace')
 assert r.status==200
 assert 'Get Free Products Delivered to Your Home' in html
 assert 'Get Free SHEIN Products Delivered to Your Home' not in html
 assert 'Would you like to get free products?' in html
 assert 'Would you like to get free SHEIN products?' not in html
 rows.append({'slug':slug,'status':r.status,'new_copy':True})
print(json.dumps({'public_recovery':'PASS','routes':rows},separators=(',',':')))
PY
MOVED=0
printf 'CACHE_BACKUP=%s\nSTATUS=PASS\n' "$CACHE_BACKUP"
