#!/usr/bin/env bash
set -Eeuo pipefail
printf 'UTC='; date -u +%Y-%m-%dT%H:%M:%SZ
sudo /usr/sbin/nginx -T 2>&1 | python3 -c 'import sys; lines=sys.stdin.read().splitlines(); keys=("open_file_cache","fastcgi_cache","proxy_cache","yolokfx","sh1-g002","sh2-g002"); print("\n".join(f"{i+1}:{line}" for i,line in enumerate(lines) if any(k in line.lower() for k in keys)))'
sudo python3 - <<'PY'
import json,os
paths=['/home/runcloud/webapps/yolokfx/quiz/us/sh1-g002/index.html','/home/runcloud/webapps/yolokfx/quiz/us/sh2-g002/index.html','/home/runcloud/webapps/yolokfx/quiz/us/sh1-g001/index.html']
for p in paths:
 st=os.stat(p)
 print(json.dumps({'path':p,'inode':st.st_ino,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'size':st.st_size},separators=(',',':')))
PY
