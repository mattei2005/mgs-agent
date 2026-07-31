#!/usr/bin/env bash
set -euo pipefail
SITE="${1:?site required}"
MIGRATE_LAYOUT="${MIGRATE_LAYOUT:-1}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
ZIP="${ZIP:-/tmp/mgs-chat-funnels-0.4.5-code-only.zip}"
MIGRATOR="${MIGRATOR:-/tmp/migrate-sms-layout.py}"
EXPECTED_ZIP_SHA="${EXPECTED_ZIP_SHA:-c1ef64a12bf906478fb0711746038ad62fad0d81166dfd5115a38c89c1b0fa6e}"
case "$SITE" in
  zuout.com) OWNER=runcloud; APP=/home/runcloud/webapps/zuout ;;
  zytiva.com) OWNER=runcloud; APP=/home/runcloud/webapps/zytiva ;;
  finance.topfeed.fun) OWNER=runcloud; APP=/home/runcloud/webapps/topfeedfinance ;;
  newsoun.com) OWNER=runcloud; APP=/home/runcloud/webapps/newsoun ;;
  eggbev.com) OWNER=runcloud; APP=/home/runcloud/webapps/eggbev ;;
  wantabrand.com) OWNER=runcloud2; APP=/home/runcloud2/webapps/wantabrand ;;
  *) echo "unsupported site: $SITE" >&2; exit 2 ;;
esac
PLUGIN="$APP/wp-content/plugins/mgs-chat-funnels"
SMS="$PLUGIN/configs/car-br-01-sms.json"
LEGACY="$PLUGIN/configs/car-br-01.json"
BACKUP_ROOT="/var/backups/mgs-chat-funnels-sms-layout/$RUN_ID/$SITE"
STAGE="/tmp/mgs-chat-045-$SITE-$RUN_ID"
DB_TMP="/tmp/mgs-chat-$SITE-$RUN_ID.sql"
DEPLOY_STARTED=0
cleanup(){ sudo rm -rf "$STAGE" "$DB_TMP"; }
rollback_on_error(){
  local rc=$?
  if [ "$DEPLOY_STARTED" = "1" ] && [ -d "$BACKUP_ROOT/mgs-chat-funnels.pre" ]; then
    sudo rm -rf "$PLUGIN"
    sudo cp -a "$BACKUP_ROOT/mgs-chat-funnels.pre" "$PLUGIN"
    sudo chown -R "$OWNER:$OWNER" "$PLUGIN"
    echo "ROLLBACK|$SITE|plugin_and_configs=restored" >&2
  fi
  exit "$rc"
}
trap rollback_on_error ERR
trap cleanup EXIT
[ -d "$PLUGIN" ] && [ -f "$SMS" ] && [ -f "$LEGACY" ]
[ -f "$ZIP" ] && [ -f "$MIGRATOR" ]
ACTUAL_ZIP_SHA=$(sha256sum "$ZIP" | cut -d' ' -f1)
[ "$ACTUAL_ZIP_SHA" = "$EXPECTED_ZIP_SHA" ]
python3 - <<PY
import zipfile
z=zipfile.ZipFile('$ZIP');names=z.namelist()
assert names and not any('/configs/' in n for n in names)
assert 'mgs-chat-funnels/mgs-chat-funnels.php' in names
PY
sudo mkdir -p "$BACKUP_ROOT"
[ ! -e "$BACKUP_ROOT/mgs-chat-funnels.pre" ]
sudo cp -a "$PLUGIN" "$BACKUP_ROOT/mgs-chat-funnels.pre"
sudo -u "$OWNER" wp --path="$APP" db export "$DB_TMP" --quiet
sudo mv "$DB_TMP" "$BACKUP_ROOT/database.pre.sql"
sudo chmod 600 "$BACKUP_ROOT/database.pre.sql"
PRE_SMS_SHA=$(sha256sum "$SMS" | cut -d' ' -f1)
PRE_LEGACY_SHA=$(sha256sum "$LEGACY" | cut -d' ' -f1)
PRE_MAIN_SHA=$(sha256sum "$PLUGIN/mgs-chat-funnels.php" | cut -d' ' -f1)
sudo rm -rf "$STAGE" && sudo mkdir -p "$STAGE"
sudo unzip -q "$ZIP" -d "$STAGE"
sudo cp -a "$STAGE/mgs-chat-funnels/." "$PLUGIN/"
sudo chown -R "$OWNER:$OWNER" "$PLUGIN"
DEPLOY_STARTED=1
if [ "$MIGRATE_LAYOUT" = "1" ]; then
  sudo -u "$OWNER" python3 "$MIGRATOR" "$SMS" "$SITE" > "$BACKUP_ROOT/migration.json"
else
  [ "$(sha256sum "$SMS" | cut -d' ' -f1)" = "$PRE_SMS_SHA" ]
fi
sudo -u "$OWNER" php -l "$PLUGIN/mgs-chat-funnels.php" >/dev/null
sudo -u "$OWNER" php -l "$PLUGIN/includes/class-mgs-chat-sms.php" >/dev/null
python3 -m json.tool "$SMS" >/dev/null
python3 -m json.tool "$LEGACY" >/dev/null
python3 - <<PY
from pathlib import Path
p=Path('$PLUGIN/mgs-chat-funnels.php').read_text()
assert 'Version: 0.4.5' in p and "const VERSION = '0.4.5';" in p
assert Path('$PLUGIN/assets/car-financing-hero.png').stat().st_size > 10000
PY
POST_SMS_SHA=$(sha256sum "$SMS" | cut -d' ' -f1)
POST_LEGACY_SHA=$(sha256sum "$LEGACY" | cut -d' ' -f1)
POST_MAIN_SHA=$(sha256sum "$PLUGIN/mgs-chat-funnels.php" | cut -d' ' -f1)
[ "$PRE_LEGACY_SHA" = "$POST_LEGACY_SHA" ]
if [ "$MIGRATE_LAYOUT" = "1" ]; then [ "$PRE_SMS_SHA" != "$POST_SMS_SHA" ]; else [ "$PRE_SMS_SHA" = "$POST_SMS_SHA" ]; fi
python3 - <<PY
import json
from pathlib import Path
out={'site':'$SITE','run_id':'$RUN_ID','backup_root':'$BACKUP_ROOT','migrate_layout':'$MIGRATE_LAYOUT'=='1','pre':{'main':'$PRE_MAIN_SHA','sms':'$PRE_SMS_SHA','legacy':'$PRE_LEGACY_SHA'},'post':{'main':'$POST_MAIN_SHA','sms':'$POST_SMS_SHA','legacy':'$POST_LEGACY_SHA'},'db_backup_bytes':Path('$BACKUP_ROOT/database.pre.sql').stat().st_size,'status':'success'}
Path('$BACKUP_ROOT/result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,separators=(',',':')))
PY
