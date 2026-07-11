#!/usr/bin/env bash
set -euo pipefail

WP=/home/runcloud2/webapps/creditoparaveiculo
PLUGIN_PARENT="$WP/wp-content/plugins"
LIVE="$PLUGIN_PARENT/mgs-quiz-carro"
PACKAGE=/tmp/mgs-quiz-carro-1.7.0.tar.gz
IMPORT_JSON=/tmp/historical-creditoparaveiculo-import.json
IMPORT_PHP=/tmp/mgs-quiz-sms-revenue-import.php
SMOKE_PHP=/tmp/mgs-quiz-sms-revenue-smoke.php
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/home/runcloud2/backups/creditoparaveiculo/mgs-quiz-carro-1.6.2-$STAMP"
STAGE_PARENT="$WP/wp-content/.mgs-deploy/mgs-quiz-carro-1.7.0-$STAMP"
STAGE="$STAGE_PARENT/mgs-quiz-carro"
OLD_LIVE="$BACKUP/mgs-quiz-carro-live-before-swap"
FAILED="$BACKUP/mgs-quiz-carro-1.7.0-failed"
SWAPPED=0

rollback() {
  rc=$?
  if [ "$rc" -ne 0 ] && [ "$SWAPPED" -eq 1 ]; then
    if [ -d "$LIVE" ]; then mv "$LIVE" "$FAILED" || true; fi
    if [ -d "$OLD_LIVE" ]; then mv "$OLD_LIVE" "$LIVE" || true; fi
    echo "DEPLOY_FAILED_PLUGIN_ROLLED_BACK backup=$BACKUP database_backup=$BACKUP/pre-1.7.0.sql" >&2
  fi
  exit "$rc"
}
trap rollback EXIT

for file in "$PACKAGE" "$IMPORT_JSON" "$IMPORT_PHP" "$SMOKE_PHP"; do [ -f "$file" ]; done
chmod 644 "$IMPORT_JSON" "$IMPORT_PHP" "$SMOKE_PHP"
[ -d "$LIVE" ]
CURRENT_VERSION="$(sudo -u runcloud2 wp --path="$WP" plugin get mgs-quiz-carro --field=version --skip-plugins --skip-themes 2>/dev/null)"
[ "$CURRENT_VERSION" = "1.6.2" ]
[ "$(sudo -u runcloud2 sha256sum "$LIVE/mgs-quiz-carro.php" | cut -d' ' -f1)" = "4af8fd8c4b842bc681ba06dbed65679cdc24f0b426a149880fe80a4f89ba3466" ]
[ "$(sudo -u runcloud2 sha256sum "$LIVE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" = "601310680721d1b903350a121618aee4801802503e477edd1c47e0a38d14d441" ]
[ ! -e "$BACKUP" ]
[ ! -e "$STAGE_PARENT" ]

mkdir -p "$BACKUP" "$STAGE_PARENT"
chown runcloud2:runcloud2 "$BACKUP"
tar -xzf "$PACKAGE" -C "$STAGE_PARENT"
[ -d "$STAGE" ]
OWNER="$(sudo -u runcloud2 stat -c '%U:%G' "$LIVE")"
chown -R "$OWNER" "$STAGE"

python3 - "$STAGE" <<'PY'
from pathlib import Path
import subprocess,sys
root=Path(sys.argv[1]); files=list(root.rglob('*.php')); failed=[]
for path in files:
    result=subprocess.run(['php','-l',str(path)],capture_output=True,text=True)
    if result.returncode: failed.append(result.stdout+result.stderr)
if failed: raise SystemExit('\n'.join(failed))
main=(root/'mgs-quiz-carro.php').read_text()
activator=(root/'includes/class-mgs-quiz-activator.php').read_text()
admin=(root/'includes/class-mgs-quiz-admin.php').read_text()
markers=(
    ('Version:     1.7.0',main),
    ("MGS_QUIZ_DB_VERSION', '1.3.0",main),
    ('mgs_quiz_sms_revenue',activator),
    ('Receita SMS — Smart Bidding',admin),
)
for marker,text in markers:
    if marker not in text: raise SystemExit('Missing marker: '+marker)
print('STAGE_LINT_OK',len(files))
PY

tar -C "$PLUGIN_PARENT" -czf "$BACKUP/mgs-quiz-carro-1.6.2.tgz" mgs-quiz-carro
sha256sum "$BACKUP/mgs-quiz-carro-1.6.2.tgz" > "$BACKUP/SHA256SUMS"
sudo -u runcloud2 wp --path="$WP" db export "$BACKUP/pre-1.7.0.sql" --skip-plugins --skip-themes >/dev/null
[ -s "$BACKUP/pre-1.7.0.sql" ]

mv "$LIVE" "$OLD_LIVE"
mv "$STAGE" "$LIVE"
SWAPPED=1
chown -R "$OWNER" "$LIVE"

find "$LIVE" -type f -name '*.php' -print0 | xargs -0 -n1 php -l >/dev/null
sudo -u runcloud2 wp --path="$WP" plugin is-active mgs-quiz-carro --skip-plugins --skip-themes
NEW_VERSION="$(sudo -u runcloud2 wp --path="$WP" plugin get mgs-quiz-carro --field=version --skip-plugins --skip-themes 2>/dev/null)"
[ "$NEW_VERSION" = "1.7.0" ]
DB_VERSION="$(sudo -u runcloud2 wp --path="$WP" option get mgs_quiz_db_version --skip-themes 2>/dev/null)"
[ "$DB_VERSION" = "1.3.0" ]
TABLE_CHECK="$(sudo -u runcloud2 wp --path="$WP" db query "SELECT CONCAT(ENGINE,'|',TABLE_COLLATION) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='wp_mgs_quiz_sms_revenue';" --skip-column-names --skip-plugins --skip-themes 2>/dev/null)"
echo "$TABLE_CHECK" | grep -q '^InnoDB|'

IMPORT_RESULT="$(sudo -u runcloud2 wp --path="$WP" eval-file "$IMPORT_PHP" --skip-themes 2>/dev/null)"
echo "$IMPORT_RESULT" | grep -q 'BACKFILL_OK'
SMOKE_RESULT="$(sudo -u runcloud2 wp --path="$WP" eval-file "$SMOKE_PHP" --skip-themes 2>/dev/null)"
echo "$SMOKE_RESULT" | grep -q 'REVENUE_REPORT_SMOKE_OK'

for route in /quiz-car-parcelas/ /quiz-car-parcelas-g001/ /quiz-car-parcelas-g002-qm001/ /quiz-car-parcelas-g002-qm002/; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "https://creditoparaveiculo.com$route")"
  [ "$code" = "200" ]
done

LIVE_ADMIN_SHA="$(sha256sum "$LIVE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)"
PACKAGE_SHA="$(sha256sum "$PACKAGE" | cut -d' ' -f1)"
SWAPPED=0
trap - EXIT
printf 'DEPLOY_OK version=%s db_version=%s backup=%s package_sha256=%s admin_sha256=%s import=%s smoke=%s\n' "$NEW_VERSION" "$DB_VERSION" "$BACKUP" "$PACKAGE_SHA" "$LIVE_ADMIN_SHA" "$IMPORT_RESULT" "$SMOKE_RESULT"
