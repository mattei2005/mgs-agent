#!/usr/bin/env bash
# Reversível: sem rm e sem restauração global do banco.
set -euo pipefail
site=${1:?growpowerhub ou escalatepower}
case "$site" in growpowerhub|escalatepower) ;; *) exit 10;; esac
ROOT=/home/runcloud/webapps/$site
BACK=/home/runcloud/backups/$site-shein-v2v3-1556503439406534777
ARCHIVE="$BACK/rollback-$(date -u +%Y%m%dT%H%M%SZ)"
sudo -u runcloud mkdir "$ARCHIVE"
sudo -u runcloud wp --path="$ROOT" plugin deactivate mgs-direct-quiz --allow-root
# O hook de desativação arquiva rotas físicas sem apagar.
sudo -u runcloud wp --path="$ROOT" eval '$x=json_decode(file_get_contents("/home/runcloud/backups/'"$site"'-shein-v2v3-1556503439406534777/runtime.json"),true);if(!is_array($x)){exit(11);}if($x["option_exists"]){update_option("mgs_direct_quiz_landings",$x["items"],false);}else{delete_option("mgs_direct_quiz_landings");}if(false!==$x["static_version"]){update_option("mgs_direct_quiz_static_version",$x["static_version"],false);}else{delete_option("mgs_direct_quiz_static_version");}if(get_option("mgs_direct_quiz_landings",array())!==$x["items"]){exit(12);}echo "option_restored";' --allow-root
sudo -u runcloud mv "$ROOT/wp-content/plugins/mgs-direct-quiz" "$ARCHIVE/plugin-deployed"
# Novos attachments permanecem preservados; não remover mídias ou backups.
printf '\nRollback de %s concluído; validar HTTP/REC/admin depois.\n' "$site"
