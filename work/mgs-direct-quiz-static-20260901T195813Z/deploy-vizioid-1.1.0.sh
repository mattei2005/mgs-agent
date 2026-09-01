#!/usr/bin/env bash
set -Eeuo pipefail
SITE=vizioid
OWNER=runcloud
WP=/home/runcloud/webapps/$SITE
ACTIVE="$WP/wp-content/plugins/mgs-direct-quiz"
ARCHIVE=/tmp/mgs-direct-quiz-1.1.0.tar.gz
EXPECTED=ea5b595e99de0e5d5ca06d238bcf8cc5429ad9e3481f26b588a66b9d08d06cce
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/home/runcloud/backups/${SITE}-mgs-direct-quiz-static-${STAMP}"
STAGE="$BACKUP/stage"
OLD="$BACKUP/plugin-live-before"
SWAPPED=0
rollback() {
  set +e
  if [[ "$SWAPPED" == 1 ]]; then
    sudo mkdir -p "$BACKUP/failed-static"
    for slug in sh1-g002 sh2-g002; do
      dir="$WP/quiz/us/$slug"
      if sudo test -f "$dir/index.html" && sudo grep -q 'MGS Direct Quiz static' "$dir/index.html"; then
        sudo mv "$dir" "$BACKUP/failed-static/$slug"
      fi
    done
    if sudo test -d "$ACTIVE"; then sudo mv "$ACTIVE" "$BACKUP/plugin-failed-1.1.0"; fi
    if sudo test -d "$OLD"; then sudo mv "$OLD" "$ACTIVE"; fi
    sudo -u "$OWNER" wp --path="$WP" option update mgs_direct_quiz_static_version '' --allow-root >/dev/null 2>&1 || true
  fi
  printf 'ROLLBACK_PATH=%s\n' "$BACKUP" >&2
}
on_error() {
  rc=$?
  trap - ERR
  rollback
  exit "$rc"
}
trap on_error ERR

actual=$(sha256sum "$ARCHIVE" | python3 -c "import sys; print(sys.stdin.read().split()[0])")
[[ "$actual" == "$EXPECTED" ]]
sudo mkdir -p "$STAGE"
sudo cp -a "$ACTIVE" "$BACKUP/plugin-copy-before"
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-before.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-before.json"
sudo chmod 600 "$BACKUP/landings-before.json"
sudo test -s "$BACKUP/landings-before.json"
for slug in sh1-g002 sh2-g002; do
  [[ ! -e "$WP/quiz/us/$slug/index.html" ]]
done
sudo tar -xzf "$ARCHIVE" -C "$STAGE"
sudo chown -R "$OWNER:$OWNER" "$STAGE/mgs-direct-quiz"
sudo python3 - "$STAGE/mgs-direct-quiz" <<'PY'
import os,sys
root=sys.argv[1]
for dp,dirs,files in os.walk(root):
    os.chmod(dp,0o755)
    for name in files: os.chmod(os.path.join(dp,name),0o644)
PY
sudo mv "$ACTIVE" "$OLD"
sudo mv "$STAGE/mgs-direct-quiz" "$ACTIVE"
SWAPPED=1

sync_json=$(sudo -u "$OWNER" wp --path="$WP" eval '$r=MGS_Direct_Quiz::sync_static_pages(); if(is_wp_error($r)){throw new Exception($r->get_error_message());} echo wp_json_encode($r,JSON_UNESCAPED_SLASHES);' --allow-root)
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
[[ "$version" == "1.1.0" && "$status" == "active" ]]
for slug in sh1-g002 sh2-g002; do
  file="$WP/quiz/us/$slug/index.html"
  sudo test -f "$file"
  sudo grep -q 'MGS Direct Quiz static; plugin=1.1.0' "$file"
  sudo grep -q 'direct-quiz.js?v=1.1.0' "$file"
  [[ $(sudo grep -c 'data-mgs-dq-cta' "$file") -eq 2 ]]
done
static_version=$(sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_static_version --allow-root)
[[ "$static_version" == "1.1.0" ]]
SWAPPED=0
printf 'SITE=%s\nVERSION=%s\nSTATUS=%s\nSTATIC_VERSION=%s\nPACKAGE_SHA256=%s\nBACKUP=%s\nSYNC=%s\n' "$SITE" "$version" "$status" "$static_version" "$actual" "$BACKUP" "$sync_json"
