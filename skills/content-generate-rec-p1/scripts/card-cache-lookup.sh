#!/bin/bash
# Preserve card_cache contract: hit0/miss1/error2, full existing fields, TTL and usage.
set -euo pipefail
if [ $# -lt 1 ]; then
  printf '%s\n' '{"error":"usage: card-cache-lookup.sh <card_slug>"}' >&2
  exit 2
fi
python3 - "$1" <<'PY'
import datetime,json,os,sqlite3,sys
from pathlib import Path
slug=sys.argv[1];site=os.environ.get('SITE','unknown')
now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
db=Path('/root/mgs-agent/data/card-cache.db');log=Path('/root/mgs-agent/logs/card-cache.log')
fields='card_slug,card_name,card_official_url,country,vertical,language,annual_fee,apr,benefits_json,tag10,tag2,descriptor,competitors_json,raw_extracted_json,card_image_local_path,card_image_url_orig,card_image_uploaded_id,card_image_uploaded_url,researched_at,last_used_at,usage_count,expires_at'
try:
    if not db.is_file():
        row=None
    else:
        con=sqlite3.connect('file:'+str(db)+'?mode=rw',uri=True,timeout=20);con.row_factory=sqlite3.Row
        try:
            with con:
                con.execute('BEGIN IMMEDIATE')
                row=con.execute('SELECT '+fields+' FROM card_cache WHERE card_slug=? AND (expires_at IS NULL OR expires_at>?)',(slug,now)).fetchone()
                if row:
                    con.execute('UPDATE card_cache SET usage_count=usage_count+1,last_used_at=? WHERE card_slug=?',(now,slug))
                con.execute('INSERT INTO cache_access_log (card_slug,accessed_at,hit,site,notes) VALUES (?,?,?,?,?)',(slug,now,int(row is not None),site,'lookup HIT' if row else 'lookup MISS'))
        finally:con.close()
    out=dict(row) if row else {'card_slug':slug};out['hit']=row is not None
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('a') as f:f.write(json.dumps({'time':now,'hit':out['hit'],'card_slug':slug,'site':site},ensure_ascii=False)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if row else 1)
except (sqlite3.Error,OSError):
    print(json.dumps({'error':'cache_lookup_failed','card_slug':slug}),file=sys.stderr)
    raise SystemExit(2)
PY
