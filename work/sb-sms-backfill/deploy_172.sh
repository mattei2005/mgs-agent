#!/usr/bin/env bash
set -euo pipefail
WP=/home/runcloud2/webapps/creditoparaveiculo
PLUGIN_PARENT="$WP/wp-content/plugins"
LIVE="$PLUGIN_PARENT/mgs-quiz-carro"
PACKAGE=/tmp/mgs-quiz-carro-1.7.2.tar.gz
SMOKE=/tmp/mgs-quiz-default-date-smoke.php
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/home/runcloud2/backups/creditoparaveiculo/mgs-quiz-carro-1.7.1-$STAMP
STAGE_PARENT=/tmp/mgs-quiz-1.7.2-stage-$STAMP
STAGE="$STAGE_PARENT/mgs-quiz-carro"
FAILED="$BACKUP/mgs-quiz-carro-1.7.2-failed"
SWAPPED=0
rollback(){
  rc=$?
  if [ "$SWAPPED" -eq 1 ]; then
    [ -d "$LIVE" ] && mv "$LIVE" "$FAILED" || true
    [ -d "$BACKUP/mgs-quiz-carro" ] && mv "$BACKUP/mgs-quiz-carro" "$LIVE" || true
    chown -R runcloud2:runcloud2 "$LIVE" 2>/dev/null || true
    echo "DEPLOY_FAILED_PLUGIN_ROLLED_BACK backup=$BACKUP"
  fi
  exit "$rc"
}
trap rollback ERR
[ -f "$PACKAGE" ]
[ -f "$SMOKE" ]
CURRENT_VERSION="$(sudo -u runcloud2 wp --path="$WP" plugin get mgs-quiz-carro --field=version --skip-plugins --skip-themes 2>/dev/null)"
[ "$CURRENT_VERSION" = "1.7.1" ]
[ "$(sudo -u runcloud2 sha256sum "$LIVE/mgs-quiz-carro.php" | cut -d' ' -f1)" = "f5248be2b3229fd7066f5cb6e363db45b4d40754bcb625552db53bfd44e502ed" ]
[ "$(sudo -u runcloud2 sha256sum "$LIVE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" = "e4d20094020724758b0822ff7491402e5acb82b3669ca5711fa53aa6fabb536d" ]
[ ! -e "$BACKUP" ]
mkdir -p "$BACKUP" "$STAGE_PARENT"
tar -C "$STAGE_PARENT" -xzf "$PACKAGE"
[ -f "$STAGE/mgs-quiz-carro.php" ]
LINT_COUNT=0
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; LINT_COUNT=$((LINT_COUNT+1)); done < <(find "$STAGE" -type f -name '*.php' -print0)
[ "$LINT_COUNT" -ge 11 ]
php -l "$SMOKE" >/dev/null
chown -R runcloud2:runcloud2 "$STAGE"
chmod 644 "$SMOKE"
mv "$LIVE" "$BACKUP/mgs-quiz-carro"
mv "$STAGE" "$LIVE"
SWAPPED=1
sudo -u runcloud2 wp --path="$WP" plugin is-active mgs-quiz-carro --skip-plugins --skip-themes >/dev/null
NEW_VERSION="$(sudo -u runcloud2 wp --path="$WP" plugin get mgs-quiz-carro --field=version --skip-plugins --skip-themes 2>/dev/null)"
[ "$NEW_VERSION" = "1.7.2" ]
DB_VERSION="$(sudo -u runcloud2 wp --path="$WP" option get mgs_quiz_db_version --skip-plugins --skip-themes 2>/dev/null)"
[ "$DB_VERSION" = "1.3.0" ]
SMOKE_RESULT="$(sudo -u runcloud2 wp --path="$WP" eval-file "$SMOKE" --skip-themes 2>/dev/null)"
printf '%s' "$SMOKE_RESULT" | grep -q 'REVENUE_REPORT_SMOKE_OK'
printf '%s' "$SMOKE_RESULT" | grep -q '"default_from_to":"'
for path in quiz-car-parcelas/ quiz-car-valor/ quiz-car-gestor/ quiz-car-quiz/; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "https://creditoparaveiculo.com/$path")"
  [ "$code" = "200" ]
done
ADMIN_SHA="$(sha256sum "$LIVE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)"
PACKAGE_SHA="$(sha256sum "$PACKAGE" | cut -d' ' -f1)"
SWAPPED=0
trap - ERR
echo "DEPLOY_OK version=$NEW_VERSION db_version=$DB_VERSION backup=$BACKUP package_sha256=$PACKAGE_SHA admin_sha256=$ADMIN_SHA smoke=$SMOKE_RESULT"
