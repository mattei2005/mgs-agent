#!/usr/bin/env bash
set -euo pipefail

SITE_ROOT=/home/runcloud2/webapps/creditoparaveiculo
LIVE="$SITE_ROOT/wp-content/plugins/mgs-quiz-carro"
PKG=/var/tmp/mgs-quiz-carro-1.7.5.tar.gz
EXPECTED_PKG=05e103e7a19dd796b11f706749a503cf6d3cd095bd1fc1b435bddece678fca5e
EXPECTED_BOOT=5677764cbb2d1e73ae8830566877dad5fa9bbded0d68672090ff0ea8e388bb15
EXPECTED_CSS=8f4d70e3044795b6e37abb8250bf8a6e0b5b4aeaecd9bcf44f24dedd4b718115
EXPECTED_IMAGE=491b0eeefa1ed8c776817054fce92937ecc46d85ca1cec3d7b429b99e08863e6
SLUG=quiz-car-001-cl001
OLD_IMAGE='https://cdn.motor1.com/images/mgl/7ZvBzJ/s3/volkswagen-polo-sense-at-2024.jpg'
NEW_IMAGE='https://creditoparaveiculo.com/wp-content/plugins/mgs-quiz-carro/public/images/polo-transparent.webp'
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/home/runcloud2/backups/creditoparaveiculo/mgs-quiz-carro-1.7.4-pre-responsive-${STAMP}"
STAGE="/var/tmp/mgs-quiz-carro-1.7.5-stage-${STAMP}"
DEPLOYED=0
DB_CHANGED=0

wp_run(){ sudo -u runcloud2 wp --path="$SITE_ROOT" "$@"; }
rollback(){
  rc=$?
  set +e
  if [[ $DB_CHANGED -eq 1 ]]; then
    wp_run db query "UPDATE wp_mgs_quiz_config SET car_image_url='${OLD_IMAGE}' WHERE slug='${SLUG}' AND car_image_url='${NEW_IMAGE}';" --allow-root >/dev/null 2>&1
  fi
  if [[ $DEPLOYED -eq 1 && -d "$BACKUP" ]]; then
    install -o runcloud2 -g runcloud2 -m 0644 "$BACKUP/public/css/quiz.css" "$LIVE/public/css/quiz.css"
    install -o runcloud2 -g runcloud2 -m 0644 "$BACKUP/mgs-quiz-carro.php" "$LIVE/mgs-quiz-carro.php"
  fi
  echo "ROLLBACK_EXECUTED backup=$BACKUP orphan_asset_safe=true" >&2
  exit "$rc"
}
trap rollback ERR

[[ "$(sha256sum "$PKG" | cut -d' ' -f1)" == "$EXPECTED_PKG" ]]
mkdir -p "$STAGE" "$(dirname "$BACKUP")"
tar -xzf "$PKG" -C "$STAGE"
CAND="$STAGE/mgs-quiz-carro"
[[ "$(sha256sum "$CAND/mgs-quiz-carro.php" | cut -d' ' -f1)" == "$EXPECTED_BOOT" ]]
[[ "$(sha256sum "$CAND/public/css/quiz.css" | cut -d' ' -f1)" == "$EXPECTED_CSS" ]]
[[ "$(sha256sum "$CAND/public/images/polo-transparent.webp" | cut -d' ' -f1)" == "$EXPECTED_IMAGE" ]]
for file in "$CAND"/*.php "$CAND"/includes/*.php "$CAND"/templates/*.php; do php -l "$file" >/dev/null; done

CURRENT_VERSION="$(wp_run plugin get mgs-quiz-carro --field=version --allow-root 2>/dev/null)"
[[ "$CURRENT_VERSION" == 1.7.4 ]]
CURRENT_IMAGE="$(wp_run db query "SELECT car_image_url FROM wp_mgs_quiz_config WHERE slug='${SLUG}' AND layout_template='fmybc_sms';" --skip-column-names --allow-root 2>/dev/null)"
[[ "$CURRENT_IMAGE" == "$OLD_IMAGE" ]]

cp -a "$LIVE" "$BACKUP"
printf '%s\n' "slug=$SLUG" "old_image=$OLD_IMAGE" "new_image=$NEW_IMAGE" "candidate_package_sha256=$EXPECTED_PKG" > "$BACKUP/deploy-1.7.5-metadata.txt"
chown runcloud2:runcloud2 "$BACKUP/deploy-1.7.5-metadata.txt"

DEPLOYED=1
mkdir -p "$LIVE/public/images"
install -o runcloud2 -g runcloud2 -m 0644 "$CAND/public/css/quiz.css" "$LIVE/public/css/quiz.css"
install -o runcloud2 -g runcloud2 -m 0644 "$CAND/public/images/polo-transparent.webp" "$LIVE/public/images/polo-transparent.webp"
install -o runcloud2 -g runcloud2 -m 0644 "$CAND/mgs-quiz-carro.php" "$LIVE/mgs-quiz-carro.php"

[[ "$(sha256sum "$LIVE/mgs-quiz-carro.php" | cut -d' ' -f1)" == "$EXPECTED_BOOT" ]]
[[ "$(sha256sum "$LIVE/public/css/quiz.css" | cut -d' ' -f1)" == "$EXPECTED_CSS" ]]
[[ "$(sha256sum "$LIVE/public/images/polo-transparent.webp" | cut -d' ' -f1)" == "$EXPECTED_IMAGE" ]]

wp_run db query "UPDATE wp_mgs_quiz_config SET car_image_url='${NEW_IMAGE}' WHERE slug='${SLUG}' AND layout_template='fmybc_sms' AND car_image_url='${OLD_IMAGE}';" --allow-root >/dev/null 2>&1
DB_CHANGED=1
READBACK_IMAGE="$(wp_run db query "SELECT car_image_url FROM wp_mgs_quiz_config WHERE slug='${SLUG}' AND layout_template='fmybc_sms';" --skip-column-names --allow-root 2>/dev/null)"
[[ "$READBACK_IMAGE" == "$NEW_IMAGE" ]]
[[ "$(wp_run plugin get mgs-quiz-carro --field=version --allow-root 2>/dev/null)" == 1.7.5 ]]
wp_run plugin is-active mgs-quiz-carro --allow-root --quiet 2>/dev/null

SMOKE="$(date +%s)"
HTML="$(curl -fsS "https://creditoparaveiculo.com/${SLUG}/?mgs_smoke=${SMOKE}")"
grep -Fq 'quiz.css?v=1.7.5' <<<"$HTML"
grep -Fq 'polo-transparent.webp' <<<"$HTML"
[[ "$(curl -fsS -o /dev/null -w '%{http_code}' "${NEW_IMAGE}?v=1.7.5")" == 200 ]]
CONTENT_TYPE="$(curl -fsSI "${NEW_IMAGE}?v=1.7.5" | tr -d '\r' | sed -n 's/^content-type: //Ip' | tail -1)"
[[ "$CONTENT_TYPE" == image/webp* ]]

DEPLOYED=0
DB_CHANGED=0
echo "DEPLOY_175_OK backup=$BACKUP version=1.7.5 css=$EXPECTED_CSS image=$EXPECTED_IMAGE image_url=$READBACK_IMAGE content_type=$CONTENT_TYPE stage_retained=$STAGE"
