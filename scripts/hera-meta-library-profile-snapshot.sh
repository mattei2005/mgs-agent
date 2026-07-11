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
  if ! python3 - "$PROFILE_DIR" <<'PY'
import os, sys
profile=sys.argv[1].encode()
live=[]
for name in os.listdir('/proc'):
    if not name.isdigit() or int(name) in {os.getpid(), os.getppid()}:
        continue
    try:
        cmd=open(f'/proc/{name}/cmdline','rb').read()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if profile in cmd:
        live.append((name, cmd.replace(b'\0',b' ')[:240].decode(errors='replace')))
if live:
    for pid,cmd in live:
        print(f'Chromium ativo no perfil: pid={pid} cmd={cmd}', file=sys.stderr)
    raise SystemExit(1)
PY
  then
    echo "Singleton ativo confirmado; snapshot recusado." >&2
    exit 76
  fi
  # Symlinks Singleton órfãos podem permanecer após shutdown. Não removê-los;
  # o rsync os exclui e o snapshot segue apenas após confirmar zero processo vivo.
fi

REPORT_ROOT="/root/.hermes/profiles/hera/artifacts/meta-library"
AUTH_EVIDENCE="$(python3 - "$STATUS_FILE" "$REPORT_ROOT" <<'PY'
import glob, json, os, sys, time
status_path, report_root=sys.argv[1:]
try:
    s=json.load(open(status_path))
    if s.get('authenticatedLikely') is True:
        print(status_path); raise SystemExit(0)
except (OSError, ValueError):
    pass
for p in sorted(glob.glob(os.path.join(report_root,'*','report.json')), key=os.path.getmtime, reverse=True):
    if time.time()-os.path.getmtime(p) > 3600:
        break
    try: r=json.load(open(p))
    except (OSError, ValueError): continue
    if r.get('success') is True and r.get('proxyMode')=='windows-home-socks' and r.get('session',{}).get('authenticatedLikely') is True:
        print(p); raise SystemExit(0)
raise SystemExit(1)
PY
)" || {
  echo "Sessão autenticada não confirmada por status nem report recente; snapshot recusado." >&2
  exit 77
}

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

python3 - "$tmp" "$AUTH_EVIDENCE" <<'PY'
import datetime, hashlib, json, os, sys
root,evidence_path=sys.argv[1:]
profile=os.path.join(root,'profile')
def digest(rel):
    p=os.path.join(profile,rel)
    if not os.path.isfile(p): return None
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
evidence=json.load(open(evidence_path))
if 'session' in evidence:
    authenticated=evidence.get('session',{}).get('authenticatedLikely') is True
    proxy_mode=evidence.get('proxyMode')
    page_title=evidence.get('page',{}).get('title')
else:
    authenticated=evidence.get('authenticatedLikely') is True
    proxy_mode=evidence.get('proxyMode')
    page_title=evidence.get('pageTitle')
meta={
  'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'authenticatedLikely':authenticated,
  'proxyMode':proxy_mode,
  'pageTitle':page_title,
  'authEvidence':evidence_path,
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
