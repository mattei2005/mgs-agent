#!/usr/bin/env bash
set -euo pipefail
SITE_ROOT=/home/runcloud2/webapps/creditoparaveiculo
LIVE="$SITE_ROOT/wp-content/plugins/mgs-quiz-carro"
PKG=/var/tmp/mgs-quiz-carro-1.7.4.tar.gz
SMOKE=/var/tmp/mgs-quiz-report-smoke-1.7.4.php
EXPECTED_PKG=5982835509567016469cad1868750cc2a02e10c8b0edb01134404fc650bf3079
EXPECTED_BOOT=c2e1c39120362a14efb3829f673f8a596d3eb26dd95d83e04bddc25fd8572e28
EXPECTED_ADMIN=71f6f187e26f7a80ba3d54887104befa3f7ff20684284d2945ccaaf1962f8f1d
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/home/runcloud2/backups/creditoparaveiculo/mgs-quiz-carro-1.7.3-${STAMP}"
STAGE="/var/tmp/mgs-quiz-carro-1.7.4-stage-${STAMP}"
DEPLOYED=0
rollback(){
  rc=$?
  if [[ $DEPLOYED -eq 1 && -d "$BACKUP" ]]; then
    cp -a "$BACKUP/includes/class-mgs-quiz-admin.php" "$LIVE/includes/class-mgs-quiz-admin.php"
    cp -a "$BACKUP/mgs-quiz-carro.php" "$LIVE/mgs-quiz-carro.php"
    echo "ROLLBACK_OK backup=$BACKUP" >&2
  fi
  rm -rf "$STAGE"
  exit "$rc"
}
trap rollback ERR
[[ "$(sha256sum "$PKG" | cut -d' ' -f1)" == "$EXPECTED_PKG" ]]
mkdir -p "$STAGE" "$(dirname "$BACKUP")"
tar -xzf "$PKG" -C "$STAGE"
CAND="$STAGE/mgs-quiz-carro"
[[ "$(sha256sum "$CAND/mgs-quiz-carro.php" | cut -d' ' -f1)" == "$EXPECTED_BOOT" ]]
[[ "$(sha256sum "$CAND/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" == "$EXPECTED_ADMIN" ]]
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find "$CAND" -name '*.php' -print0)
cp -a "$LIVE" "$BACKUP"
DEPLOYED=1
install -o runcloud2 -g runcloud2 -m 0644 "$CAND/includes/class-mgs-quiz-admin.php" "$LIVE/includes/class-mgs-quiz-admin.php"
install -o runcloud2 -g runcloud2 -m 0644 "$CAND/mgs-quiz-carro.php" "$LIVE/mgs-quiz-carro.php"
[[ "$(sha256sum "$LIVE/mgs-quiz-carro.php" | cut -d' ' -f1)" == "$EXPECTED_BOOT" ]]
[[ "$(sha256sum "$LIVE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" == "$EXPECTED_ADMIN" ]]
wp --allow-root --path="$SITE_ROOT" plugin status mgs-quiz-carro --skip-plugins --skip-themes | grep -q 'Version: 1.7.4'
wp --allow-root --path="$SITE_ROOT" eval-file "$SMOKE" --skip-themes
for route in quiz-car-parcelas quiz-car-parcelas-g001 quiz-car-parcelas-g003 quiz-car-parcelas-g002-qm002; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "https://creditoparaveiculo.com/${route}/")"
  [[ "$code" == 200 ]]
done
rm -rf "$STAGE"
DEPLOYED=0
echo "DEPLOY_174_OK backup=$BACKUP boot=$EXPECTED_BOOT admin=$EXPECTED_ADMIN"
