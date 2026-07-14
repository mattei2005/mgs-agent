#!/usr/bin/env bash
set -euo pipefail

SITE_ROOT=/home/runcloud2/webapps/creditoparaveiculo
LIVE="$SITE_ROOT/wp-content/plugins/mgs-quiz-carro"
PKG=/var/tmp/mgs-quiz-carro-1.7.6.tar.gz
SMOKE=/var/tmp/mgs-quiz-report-smoke-1.7.6.php
EXPECTED_PKG=8d5b70ca50b326f48c19e34d218c593163cf8c2748c0cf2b119bdd9436268d3b
EXPECTED_BOOT=1074d2e95e1aa88bdc57088827bcaf09f01371aeb0625141108455e56add4c07
EXPECTED_ADMIN=0fa0e69cb5ee7dfb116eea71d260297d42e0808831e4ea8772f6508e6a164148
EXPECTED_SMOKE=0f41cd48fca5765678b481fcf595153fee8addae3de90e9ed8345f7c0628a1bb
EXPECTED_OLD_BOOT=5677764cbb2d1e73ae8830566877dad5fa9bbded0d68672090ff0ea8e388bb15
EXPECTED_OLD_ADMIN=71f6f187e26f7a80ba3d54887104befa3f7ff20684284d2945ccaaf1962f8f1d
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/home/runcloud2/backups/creditoparaveiculo/mgs-quiz-carro-1.7.5-pre-apply-filter-${STAMP}"
STAGE="/var/tmp/mgs-quiz-carro-1.7.6-stage-${STAMP}"
DEPLOYED=0

wp_run(){ wp --allow-root --path="$SITE_ROOT" "$@"; }
rollback(){
  rc=$?
  set +e
  if [[ $DEPLOYED -eq 1 && -d "$BACKUP" ]]; then
    install -o runcloud2 -g runcloud2 -m 0644 "$BACKUP/includes/class-mgs-quiz-admin.php" "$LIVE/includes/class-mgs-quiz-admin.php"
    install -o runcloud2 -g runcloud2 -m 0644 "$BACKUP/mgs-quiz-carro.php" "$LIVE/mgs-quiz-carro.php"
    echo "ROLLBACK_OK backup=$BACKUP stage_retained=$STAGE" >&2
  fi
  exit "$rc"
}
trap rollback ERR

[[ "$(sha256sum "$PKG" | cut -d' ' -f1)" == "$EXPECTED_PKG" ]]
[[ "$(sha256sum "$SMOKE" | cut -d' ' -f1)" == "$EXPECTED_SMOKE" ]]
mkdir -p "$STAGE" "$(dirname "$BACKUP")"
tar -xzf "$PKG" -C "$STAGE"
CAND="$STAGE/mgs-quiz-carro"
[[ "$(sha256sum "$CAND/mgs-quiz-carro.php" | cut -d' ' -f1)" == "$EXPECTED_BOOT" ]]
[[ "$(sha256sum "$CAND/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" == "$EXPECTED_ADMIN" ]]
for file in "$CAND"/*.php "$CAND"/includes/*.php "$CAND"/templates/*.php; do php -l "$file" >/dev/null; done

[[ "$(wp_run plugin get mgs-quiz-carro --field=version --skip-themes 2>/dev/null)" == 1.7.5 ]]
wp_run plugin is-active mgs-quiz-carro --skip-themes --quiet 2>/dev/null
[[ "$(sha256sum "$LIVE/mgs-quiz-carro.php" | cut -d' ' -f1)" == "$EXPECTED_OLD_BOOT" ]]
[[ "$(sha256sum "$LIVE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" == "$EXPECTED_OLD_ADMIN" ]]

cp -a "$LIVE" "$BACKUP"
printf '%s\n' \
  "source_version=1.7.5" \
  "target_version=1.7.6" \
  "candidate_package_sha256=$EXPECTED_PKG" \
  "candidate_boot_sha256=$EXPECTED_BOOT" \
  "candidate_admin_sha256=$EXPECTED_ADMIN" \
  "change=calendar Apply submits the full report filter form; Filtrar relatório preserved" \
  > "$BACKUP/deploy-1.7.6-metadata.txt"
chown runcloud2:runcloud2 "$BACKUP/deploy-1.7.6-metadata.txt"

DEPLOYED=1
install -o runcloud2 -g runcloud2 -m 0644 "$CAND/includes/class-mgs-quiz-admin.php" "$LIVE/includes/class-mgs-quiz-admin.php"
install -o runcloud2 -g runcloud2 -m 0644 "$CAND/mgs-quiz-carro.php" "$LIVE/mgs-quiz-carro.php"

[[ "$(sha256sum "$LIVE/mgs-quiz-carro.php" | cut -d' ' -f1)" == "$EXPECTED_BOOT" ]]
[[ "$(sha256sum "$LIVE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" == "$EXPECTED_ADMIN" ]]
[[ "$(wp_run plugin get mgs-quiz-carro --field=version --skip-themes 2>/dev/null)" == 1.7.6 ]]
wp_run plugin is-active mgs-quiz-carro --skip-themes --quiet 2>/dev/null
wp_run eval-file "$SMOKE" --skip-themes

for route in quiz-car-parcelas quiz-car-parcelas-g001 quiz-car-parcelas-g003 quiz-car-parcelas-g002-qm002 quiz-car-001-cl001; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "https://creditoparaveiculo.com/${route}/")"
  [[ "$code" == 200 ]]
done

DEPLOYED=0
echo "DEPLOY_176_OK backup=$BACKUP stage_retained=$STAGE boot=$EXPECTED_BOOT admin=$EXPECTED_ADMIN"
