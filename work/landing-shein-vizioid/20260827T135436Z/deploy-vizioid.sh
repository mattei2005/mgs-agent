#!/usr/bin/env bash
set -Eeuo pipefail

WP=/home/runcloud/webapps/vizioid
PLUGIN_SLUG=mgs-direct-quiz
ACTIVE="$WP/wp-content/plugins/$PLUGIN_SLUG"
DEPLOY_ID=20260827T135436Z
INBOX="/home/zeus/mgs-deploy-inbox/$DEPLOY_ID"
BACKUP_ROOT="/home/runcloud/backups/vizioid-mgs-direct-quiz-$DEPLOY_ID"
PACKAGE_INBOX="$INBOX/mgs-direct-quiz-1.0.7.tar.gz"
MIGRATION_INBOX="$INBOX/create-vizioid-g002.php"
PACKAGE="$BACKUP_ROOT/mgs-direct-quiz-1.0.7.tar.gz"
MIGRATION="$BACKUP_ROOT/create-vizioid-g002.php"
DB_BACKUP="$BACKUP_ROOT/vizioid-options-pre-deploy.sql"
STAGE="$BACKUP_ROOT/stage"
FAILED="$BACKUP_ROOT/failed-plugin"
EXPECTED_PACKAGE_SHA="5ae36f8397c10b475b96ee7f62ff94fbbf84a7e9b9d231ebe62b407e49eab62b"
MUTATED=0

rollback() {
  rc=$?
  trap - ERR
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo -u runcloud wp --path="$WP" plugin deactivate "$PLUGIN_SLUG" --quiet --allow-root
    if sudo test -d "$ACTIVE"; then
      sudo mv "$ACTIVE" "$FAILED"
    fi
    sudo -u runcloud wp --path="$WP" option delete mgs_direct_quiz_landings --quiet --allow-root
    sudo -u runcloud wp --path="$WP" rewrite flush --hard --quiet --allow-root
  fi
  printf 'deploy_failed_rc=%s rollback_plugin_path=%s option_restored=absent\n' "$rc" "$FAILED" >&2
  exit "$rc"
}
trap rollback ERR

sudo test -d "$WP"
sudo -u runcloud wp --path="$WP" core is-installed --allow-root
if sudo test -e "$ACTIVE"; then
  echo "unexpected_existing_plugin_path=$ACTIVE" >&2
  exit 20
fi
if sudo -u runcloud wp --path="$WP" plugin is-installed "$PLUGIN_SLUG" --allow-root; then
  echo "unexpected_existing_plugin_registry=$PLUGIN_SLUG" >&2
  exit 21
fi
OPTION_STATE=$(sudo -u runcloud wp --path="$WP" eval '$v=get_option("mgs_direct_quiz_landings",null);echo null===$v?"absent":"present";' --allow-root)
[[ "$OPTION_STATE" == "absent" ]]

sudo mkdir -p "$BACKUP_ROOT" "$STAGE"
if [[ -f "$PACKAGE_INBOX" ]]; then sudo mv "$PACKAGE_INBOX" "$PACKAGE"; fi
if [[ -f "$MIGRATION_INBOX" ]]; then sudo mv "$MIGRATION_INBOX" "$MIGRATION"; fi
sudo test -f "$PACKAGE"
sudo test -f "$MIGRATION"
sudo chown -R runcloud:runcloud "$BACKUP_ROOT"
ACTUAL_PACKAGE_SHA=$(sudo sha256sum "$PACKAGE" | awk '{print $1}')
[[ "$ACTUAL_PACKAGE_SHA" == "$EXPECTED_PACKAGE_SHA" ]]

PREFIX=$(sudo -u runcloud wp --path="$WP" db prefix --allow-root)
sudo -u runcloud wp --path="$WP" db export "$DB_BACKUP" --tables="${PREFIX}options" --allow-root --quiet
sudo test -s "$DB_BACKUP"

sudo -u runcloud tar -xzf "$PACKAGE" -C "$STAGE"
sudo test -f "$STAGE/$PLUGIN_SLUG/mgs-direct-quiz.php"
sudo mv "$STAGE/$PLUGIN_SLUG" "$ACTIVE"
MUTATED=1
sudo chown -R runcloud:runcloud "$ACTIVE"
sudo find "$ACTIVE" -type d -exec chmod 755 {} +
sudo find "$ACTIVE" -type f -exec chmod 644 {} +

sudo -u runcloud wp --path="$WP" plugin activate "$PLUGIN_SLUG" --quiet --allow-root
MIGRATION_READBACK=$(sudo -u runcloud wp --path="$WP" eval-file "$MIGRATION" --allow-root)
sudo -u runcloud wp --path="$WP" rewrite flush --hard --quiet --allow-root
sudo -u runcloud wp --path="$WP" cache flush --quiet --allow-root || true
sudo -u runcloud wp --path="$WP" eval 'if(function_exists("wpfc_clear_all_cache")){wpfc_clear_all_cache(true);}' --allow-root

VERSION=$(sudo -u runcloud wp --path="$WP" plugin get "$PLUGIN_SLUG" --field=version --allow-root)
STATUS=$(sudo -u runcloud wp --path="$WP" plugin get "$PLUGIN_SLUG" --field=status --allow-root)
COUNT=$(sudo -u runcloud wp --path="$WP" eval 'echo count(MGS_Direct_Quiz::items());' --allow-root)
[[ "$VERSION" == "1.0.7" ]]
[[ "$STATUS" == "active" ]]
[[ "$COUNT" == "2" ]]

MUTATED=0
trap - ERR
sudo mv "$INBOX/deploy-vizioid.sh" "$BACKUP_ROOT/deploy-vizioid.sh"
sudo chown runcloud:runcloud "$BACKUP_ROOT/deploy-vizioid.sh"
printf 'deploy=success\nversion=%s\nstatus=%s\nlandings_count=%s\npackage_sha256=%s\nbackup_root=%s\ndb_backup=%s\nlandings=%s\n' \
  "$VERSION" "$STATUS" "$COUNT" "$ACTUAL_PACKAGE_SHA" "$BACKUP_ROOT" "$DB_BACKUP" "$MIGRATION_READBACK"
