#!/usr/bin/env bash
set -euo pipefail

SITE=/home/runcloud2/webapps/creditoparaveiculo
PLUGIN="$SITE/wp-content/plugins/mgs-quiz-carro"
OWNER=runcloud2
PACKAGE=/var/tmp/mgs-quiz-carro-1.7.9.tar.gz
EXPECTED_BOOTSTRAP=956d71dd7c7b533365373a5b8f5fe5fc0fa63e061794aed2903fa6ddc6056b87
EXPECTED_ADMIN=7e8b5c94910613f4a9050b0492a639f94cf4f6db090a7b8253b0ae3829fcd8a2
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/var/tmp/mgs-production-backups/creditoparaveiculo.com/mgs-quiz-carro-sms-duplicate-gestor/$STAMP"
STAGE="/var/tmp/mgs-quiz-carro-1.7.9-stage-$STAMP"
BACKUP_READY=0

rollback() {
  if [[ "$BACKUP_READY" == 1 ]]; then
    sudo -u "$OWNER" tar -xzf "$BACKUP/mgs-quiz-carro-1.7.8.tar.gz" -C "$SITE/wp-content/plugins"
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
[[ "$version" == "1.7.8" ]]
[[ "$bootstrap_hash" == "$EXPECTED_BOOTSTRAP" ]]
[[ "$admin_hash" == "$EXPECTED_ADMIN" ]]
option_hash_before=$(sudo -u "$OWNER" wp --path="$SITE" eval 'echo hash("sha256", serialize(get_option("mgs_quiz_sms_presets", array())));' --allow-root)
quiz_hash_before=$(sudo -u "$OWNER" wp --path="$SITE" eval 'global $wpdb;$r=$wpdb->get_results("SELECT id,sms_funnel_urls FROM {$wpdb->prefix}mgs_quiz_config ORDER BY id",ARRAY_A);echo hash("sha256",wp_json_encode($r));' --allow-root)
quiz_count_before=$(sudo -u "$OWNER" wp --path="$SITE" db query 'SELECT COUNT(*) FROM wp_mgs_quiz_config;' --skip-column-names --allow-root)
echo "PREFLIGHT_OK version=$version option_hash=$option_hash_before quiz_hash=$quiz_hash_before quiz_count=$quiz_count_before"

sudo -u "$OWNER" mkdir -p "$BACKUP" "$STAGE"
sudo -u "$OWNER" tar -C "$SITE/wp-content/plugins" -czf "$BACKUP/mgs-quiz-carro-1.7.8.tar.gz" mgs-quiz-carro
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
quiz_hash_after=$(sudo -u "$OWNER" wp --path="$SITE" eval 'global $wpdb;$r=$wpdb->get_results("SELECT id,sms_funnel_urls FROM {$wpdb->prefix}mgs_quiz_config ORDER BY id",ARRAY_A);echo hash("sha256",wp_json_encode($r));' --allow-root)
quiz_count_after=$(sudo -u "$OWNER" wp --path="$SITE" db query 'SELECT COUNT(*) FROM wp_mgs_quiz_config;' --skip-column-names --allow-root)
[[ "$version_after" == "1.7.9" ]]
[[ "$status_after" == "active" ]]
[[ "$option_hash_after" == "$option_hash_before" ]]
[[ "$quiz_hash_after" == "$quiz_hash_before" ]]
[[ "$quiz_count_after" == "$quiz_count_before" ]]

admin_probe=$(sudo -u "$OWNER" wp --path="$SITE" eval 'ob_start();MGS_Quiz_Admin::render_sms_settings();$h=ob_get_clean();echo wp_json_encode(array("add_button"=>false!==strpos($h,"id=\"mgsqAddSmsList\""),"blank_gestor"=>false!==strpos($h,"name=\"sms_codes[]\" required pattern=\"G[0-9]{3,}\" maxlength=\"12\" value=\"\""),"no_auto_g007"=>false===strpos($h,"padStart(3"),"preset_ids"=>false!==strpos($h,"name=\"sms_preset_ids[]\""),"duplicate_gestor_copy"=>false!==strpos($h,"O mesmo gestor pode ter mais de uma lista.")));' --allow-root)
helper_probe=$(sudo -u "$OWNER" wp --path="$SITE" eval '$m=new ReflectionMethod("MGS_Quiz_Admin","build_sms_presets_from_input");$m->setAccessible(true);$a="https://v2.smsfunnel.com.br/integrations/lists/00000000-0000-0000-0000-000000000001/add-lead";$b="https://v2.smsfunnel.com.br/integrations/lists/00000000-0000-0000-0000-000000000002/add-lead";$r=$m->invoke(null,array("G004",""),array("G004","G004"),array("Atual","Moto"),array($a,$b),array("G004"));$codes=is_array($r)?array_column($r,"gestor_code"):array();echo wp_json_encode(array("valid"=>is_array($r)&&2===count($r),"same_gestor_count"=>count(array_filter($codes,function($c){return "G004"===$c;})),"custom_internal_id"=>is_array($r)&&2===count($r)&&2===count(array_unique(array_keys($r)))));' --allow-root)
editor_probe=$(sudo -u "$OWNER" wp --path="$SITE" eval 'ob_start();MGS_Quiz_Admin::render_edit();$h=ob_get_clean();echo wp_json_encode(array("selector_uses_preset_id"=>false!==strpos($h,"name=\"sms_preset_id\""),"options_have_data_code"=>false!==strpos($h,"data-code=\"G004\""),"js_uses_data_code"=>false!==strpos($h,"opt.dataset.code")));' --allow-root)

public_status=$(curl -sS -o /dev/null -w '%{http_code}' 'https://creditoparaveiculo.com/quiz-car-parcelas/')
rest_status=$(curl -sS -o /dev/null -w '%{http_code}' 'https://creditoparaveiculo.com/wp-json/mgs-quiz/v1/config?slug=quiz-car-parcelas')
[[ "$public_status" == 200 ]]
[[ "$rest_status" == 200 ]]

read -r bootstrap_hash_after _ < <(sudo -u "$OWNER" sha256sum "$PLUGIN/mgs-quiz-carro.php")
read -r admin_hash_after _ < <(sudo -u "$OWNER" sha256sum "$PLUGIN/includes/class-mgs-quiz-admin.php")
echo "DEPLOY_OK version=$version_after status=$status_after bootstrap_hash=$bootstrap_hash_after admin_hash=$admin_hash_after"
echo "ADMIN_PROBE=$admin_probe"
echo "HELPER_PROBE=$helper_probe"
echo "EDITOR_PROBE=$editor_probe"
echo "RUNTIME_OK public=$public_status rest=$rest_status option_hash_unchanged=yes quiz_hash_unchanged=yes quiz_count=$quiz_count_after"
echo "BACKUP=$BACKUP/mgs-quiz-carro-1.7.8.tar.gz"
