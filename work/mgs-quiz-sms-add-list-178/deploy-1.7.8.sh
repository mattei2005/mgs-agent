#!/usr/bin/env bash
set -euo pipefail

SITE=/home/runcloud2/webapps/creditoparaveiculo
PLUGIN="$SITE/wp-content/plugins/mgs-quiz-carro"
OWNER=runcloud2
PACKAGE=/var/tmp/mgs-quiz-carro-1.7.8.tar.gz
EXPECTED_BOOTSTRAP=12fa21fad01e0d7fa7a71a42ae95154c47fa5e31729a4bb31275edf2dd28a0f9
EXPECTED_ADMIN=3682eca5155181832ecbc5e63da1c50c0827212e35151bfa411869f4e5a3d988
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/var/tmp/mgs-production-backups/creditoparaveiculo.com/mgs-quiz-carro-sms-add-list/$STAMP"
STAGE="/var/tmp/mgs-quiz-carro-1.7.8-stage-$STAMP"
BACKUP_READY=0

rollback() {
  if [[ "$BACKUP_READY" == 1 ]]; then
    sudo -u "$OWNER" tar -xzf "$BACKUP/mgs-quiz-carro-1.7.7.tar.gz" -C "$SITE/wp-content/plugins"
    sudo -u "$OWNER" php -l "$PLUGIN/includes/class-mgs-quiz-admin.php" >/dev/null
    echo "ROLLBACK_OK version=$(sudo -u "$OWNER" wp --path="$SITE" plugin get mgs-quiz-carro --field=version --allow-root)"
  fi
}
trap 'rc=$?; if [[ $rc -ne 0 ]]; then rollback; fi; exit $rc' EXIT

home=$(sudo -u "$OWNER" wp --path="$SITE" option get home --allow-root)
version=$(sudo -u "$OWNER" wp --path="$SITE" plugin get mgs-quiz-carro --field=version --allow-root)
read -r bootstrap_hash _ < <(sudo -u "$OWNER" sha256sum "$PLUGIN/mgs-quiz-carro.php")
read -r admin_hash _ < <(sudo -u "$OWNER" sha256sum "$PLUGIN/includes/class-mgs-quiz-admin.php")
[[ "$home" == "https://creditoparaveiculo.com" ]]
[[ "$version" == "1.7.7" ]]
[[ "$bootstrap_hash" == "$EXPECTED_BOOTSTRAP" ]]
[[ "$admin_hash" == "$EXPECTED_ADMIN" ]]
option_hash_before=$(sudo -u "$OWNER" wp --path="$SITE" eval 'echo hash("sha256", serialize(get_option("mgs_quiz_sms_presets", array())));' --allow-root)
quiz_count_before=$(sudo -u "$OWNER" wp --path="$SITE" db query 'SELECT COUNT(*) FROM wp_mgs_quiz_config;' --skip-column-names --allow-root)
echo "PREFLIGHT_OK version=$version option_hash=$option_hash_before quiz_count=$quiz_count_before"

sudo -u "$OWNER" mkdir -p "$BACKUP" "$STAGE"
sudo -u "$OWNER" tar -C "$SITE/wp-content/plugins" -czf "$BACKUP/mgs-quiz-carro-1.7.7.tar.gz" mgs-quiz-carro
BACKUP_READY=1
sudo -u "$OWNER" tar -xzf "$PACKAGE" -C "$STAGE"
sudo -u "$OWNER" php -l "$STAGE/mgs-quiz-carro/includes/class-mgs-quiz-admin.php" >/dev/null
sudo -u "$OWNER" php -l "$STAGE/mgs-quiz-carro/mgs-quiz-carro.php" >/dev/null

sudo -u "$OWNER" install -m 0644 "$STAGE/mgs-quiz-carro/includes/class-mgs-quiz-admin.php" "$PLUGIN/includes/class-mgs-quiz-admin.php"
sudo -u "$OWNER" php -l "$PLUGIN/includes/class-mgs-quiz-admin.php" >/dev/null
sudo -u "$OWNER" install -m 0644 "$STAGE/mgs-quiz-carro/mgs-quiz-carro.php" "$PLUGIN/mgs-quiz-carro.php"
sudo -u "$OWNER" php -l "$PLUGIN/mgs-quiz-carro.php" >/dev/null

version_after=$(sudo -u "$OWNER" wp --path="$SITE" plugin get mgs-quiz-carro --field=version --allow-root)
status_after=$(sudo -u "$OWNER" wp --path="$SITE" plugin get mgs-quiz-carro --field=status --allow-root)
option_hash_after=$(sudo -u "$OWNER" wp --path="$SITE" eval 'echo hash("sha256", serialize(get_option("mgs_quiz_sms_presets", array())));' --allow-root)
quiz_count_after=$(sudo -u "$OWNER" wp --path="$SITE" db query 'SELECT COUNT(*) FROM wp_mgs_quiz_config;' --skip-column-names --allow-root)
[[ "$version_after" == "1.7.8" ]]
[[ "$status_after" == "active" ]]
[[ "$option_hash_after" == "$option_hash_before" ]]
[[ "$quiz_count_after" == "$quiz_count_before" ]]

admin_probe=$(sudo -u "$OWNER" wp --path="$SITE" eval 'ob_start(); MGS_Quiz_Admin::render_sms_settings(); $h=ob_get_clean(); echo wp_json_encode(array("title"=>false!==strpos($h,"<h1>SMS Funnel</h1>"),"add_button"=>false!==strpos($h,"id=\"mgsqAddSmsList\""),"code_fields"=>substr_count($h,"name=\"sms_codes[]\""),"save_button"=>false!==strpos($h,"Salvar configurações SMS"),"next_code_js"=>false!==strpos($h,"padStart(3")));' --allow-root)
helper_probe=$(sudo -u "$OWNER" wp --path="$SITE" eval '$m=new ReflectionMethod("MGS_Quiz_Admin","build_sms_presets_from_input");$m->setAccessible(true);$u="https://v2.smsfunnel.com.br/integrations/lists/00000000-0000-0000-0000-000000000000/add-lead";$r=$m->invoke(null,array("G001","g007"),array("Atual","Nova"),array($u,$u),array("G001"));echo wp_json_encode(array("valid"=>is_array($r)&&isset($r["G007"]),"new_code"=>is_array($r)?$r["G007"]["gestor_code"]:""));' --allow-root)

public_status=$(curl -sS -o /dev/null -w '%{http_code}' 'https://creditoparaveiculo.com/quiz-car-parcelas/')
rest_status=$(curl -sS -o /dev/null -w '%{http_code}' 'https://creditoparaveiculo.com/wp-json/mgs-quiz/v1/config?slug=quiz-car-parcelas')
[[ "$public_status" == 200 ]]
[[ "$rest_status" == 200 ]]

read -r bootstrap_hash_after _ < <(sudo -u "$OWNER" sha256sum "$PLUGIN/mgs-quiz-carro.php")
read -r admin_hash_after _ < <(sudo -u "$OWNER" sha256sum "$PLUGIN/includes/class-mgs-quiz-admin.php")
echo "DEPLOY_OK version=$version_after status=$status_after bootstrap_hash=$bootstrap_hash_after admin_hash=$admin_hash_after"
echo "ADMIN_PROBE=$admin_probe"
echo "HELPER_PROBE=$helper_probe"
echo "RUNTIME_OK public=$public_status rest=$rest_status option_hash_unchanged=yes quiz_count=$quiz_count_after"
echo "BACKUP=$BACKUP/mgs-quiz-carro-1.7.7.tar.gz"
