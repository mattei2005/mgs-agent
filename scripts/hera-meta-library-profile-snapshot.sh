#!/usr/bin/env bash
set -euo pipefail
umask 077

PROFILE_DIR="/root/.hermes/profiles/hera/browser-profiles/meta-library-chromium"
LOCK_FILE="/root/.hermes/profiles/hera/browser-profiles/.meta-library-collector.lock"
STATUS_FILE="/root/.hermes/profiles/hera/artifacts/meta-library-login-status.json"
BACKUP_ROOT="/root/.hermes/profiles/hera/browser-profile-backups/meta-library-chromium"

mkdir -p "$(dirname "$LOCK_FILE")" "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"
exec 9>"$LOCK_FILE"
chmod 600 "$LOCK_FILE"
if ! flock -n 9; then
  echo "Perfil Meta Library em uso; snapshot recusado." >&2
  exit 75
fi

shopt -s nullglob
singleton_files=("$PROFILE_DIR"/Singleton*)
if ((${#singleton_files[@]})); then
  echo "Chromium ainda mantém SingletonLock; snapshot recusado." >&2
  exit 76
fi

if [[ ! -f "$STATUS_FILE" ]] || ! python3 - "$STATUS_FILE" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]))
raise SystemExit(0 if s.get('authenticatedLikely') is True else 1)
PY
then
  echo "Sessão autenticada não confirmada; snapshot recusado." >&2
  exit 77
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="$BACKUP_ROOT/.${ts}.tmp"
final="$BACKUP_ROOT/$ts"
mkdir -p "$tmp/profile"

rsync -a \
  --exclude='Singleton*' \
  --exclude='Crashpad/' \
  --exclude='*/Cache/' \
  --exclude='*/Code Cache/' \
  --exclude='*/GPUCache/' \
  --exclude='*/DawnCache/' \
  "$PROFILE_DIR/" "$tmp/profile/"

python3 - "$tmp" "$STATUS_FILE" <<'PY'
import datetime, hashlib, json, os, sys
root,status_path=sys.argv[1:]
profile=os.path.join(root,'profile')
def digest(rel):
    p=os.path.join(profile,rel)
    if not os.path.isfile(p): return None
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
status=json.load(open(status_path))
meta={
  'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'authenticatedLikely':status.get('authenticatedLikely') is True,
  'proxyMode':status.get('proxyMode'),
  'pageTitle':status.get('pageTitle'),
  'criticalHashes':{
    'Default/Cookies':digest('Default/Cookies'),
    'Local State':digest('Local State'),
    'Default/Preferences':digest('Default/Preferences')
  }
}
with open(os.path.join(root,'snapshot-metadata.json'),'w') as f:
    json.dump(meta,f,ensure_ascii=False,indent=2); f.write('\n')
PY

mv "$tmp" "$final"
chmod -R go-rwx "$final"

python3 - "$BACKUP_ROOT" <<'PY'
import os, shutil, sys
root=sys.argv[1]
items=sorted([x for x in os.listdir(root) if x[:8].isdigit() and os.path.isdir(os.path.join(root,x))])
for old in items[:-5]: shutil.rmtree(os.path.join(root,old))
PY

printf '{"success":true,"snapshot":"%s","retention":5}\n' "$final"
