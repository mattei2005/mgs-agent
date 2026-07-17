#!/usr/bin/env bash
set -euo pipefail

ARTIFACT=/tmp/mgs-quiz-carro-1.7.7-code-only.tar.gz
SITE=/home/runcloud2/webapps/creditoparaveiculo
USER=runcloud2
PLUGIN="$SITE/wp-content/plugins/mgs-quiz-carro"
TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/var/tmp/mgs-production-backups/creditoparaveiculo.com/mgs-quiz-carro-timezone/$TS"
STAGE="$SITE/wp-content/plugins/.mgs-quiz-carro-1.7.7-stage-$TS"
EXPECTED_OLD_MAIN=1074d2e95e1aa88bdc57088827bcaf09f01371aeb0625141108455e56add4c07
EXPECTED_OLD_ADMIN=0fa0e69cb5ee7dfb116eea71d260297d42e0808831e4ea8772f6508e6a164148
EXPECTED_OLD_CSV=931520e579ae55d61530964ee83bad212ef2fdf4005ea8b95cac6abbc696420d
EXPECTED_NEW_MAIN=12fa21fad01e0d7fa7a71a42ae95154c47fa5e31729a4bb31275edf2dd28a0f9
EXPECTED_NEW_ADMIN=3682eca5155181832ecbc5e63da1c50c0827212e35151bfa411869f4e5a3d988
EXPECTED_NEW_CSV=e9e9a34546303b14f27d51c435012a749ae937056acf05599466b4951ed79fa4

test -s "$ARTIFACT"; tar -tzf "$ARTIFACT" >/dev/null
version=$(sudo -n -u "$USER" wp --path="$SITE" plugin get mgs-quiz-carro --field=version --allow-root)
test "$version" = "1.7.6"
sudo -n -u "$USER" wp --path="$SITE" plugin is-active mgs-quiz-carro --allow-root
old_main=$(sudo -n -u "$USER" sha256sum "$PLUGIN/mgs-quiz-carro.php" | cut -d' ' -f1)
old_admin=$(sudo -n -u "$USER" sha256sum "$PLUGIN/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)
old_csv=$(sudo -n -u "$USER" sha256sum "$PLUGIN/includes/class-mgs-quiz-csv.php" | cut -d' ' -f1)
test "$old_main" = "$EXPECTED_OLD_MAIN"; test "$old_admin" = "$EXPECTED_OLD_ADMIN"; test "$old_csv" = "$EXPECTED_OLD_CSV"

sudo -n -u "$USER" mkdir -p "$BACKUP" "$STAGE/includes"
sudo -n -u "$USER" cp "$PLUGIN/mgs-quiz-carro.php" "$BACKUP/mgs-quiz-carro.php"
sudo -n -u "$USER" cp "$PLUGIN/includes/class-mgs-quiz-admin.php" "$BACKUP/class-mgs-quiz-admin.php"
sudo -n -u "$USER" cp "$PLUGIN/includes/class-mgs-quiz-csv.php" "$BACKUP/class-mgs-quiz-csv.php"
sudo -n -u "$USER" sh -c "wp --path='$SITE' db export - --allow-root --quiet 2>'$BACKUP/db-export.stderr' | gzip -c > '$BACKUP/database-before.sql.gz'"
sudo -n -u "$USER" gzip -t "$BACKUP/database-before.sql.gz"
sudo -n -u "$USER" tar -xzf "$ARTIFACT" -C "$STAGE"
sudo -n -u "$USER" php -l "$STAGE/mgs-quiz-carro.php" >/dev/null
sudo -n -u "$USER" php -l "$STAGE/includes/class-mgs-quiz-admin.php" >/dev/null
sudo -n -u "$USER" php -l "$STAGE/includes/class-mgs-quiz-csv.php" >/dev/null
test "$(sudo -n -u "$USER" sha256sum "$STAGE/mgs-quiz-carro.php" | cut -d' ' -f1)" = "$EXPECTED_NEW_MAIN"
test "$(sudo -n -u "$USER" sha256sum "$STAGE/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)" = "$EXPECTED_NEW_ADMIN"
test "$(sudo -n -u "$USER" sha256sum "$STAGE/includes/class-mgs-quiz-csv.php" | cut -d' ' -f1)" = "$EXPECTED_NEW_CSV"

installed=0
rollback() {
  rc=$?
  if [ "$installed" = "1" ]; then
    sudo -n -u "$USER" cp "$BACKUP/class-mgs-quiz-admin.php" "$PLUGIN/includes/class-mgs-quiz-admin.php"
    sudo -n -u "$USER" cp "$BACKUP/class-mgs-quiz-csv.php" "$PLUGIN/includes/class-mgs-quiz-csv.php"
    sudo -n -u "$USER" cp "$BACKUP/mgs-quiz-carro.php" "$PLUGIN/mgs-quiz-carro.php"
    sudo -n -u "$USER" wp --path="$SITE" cache flush --allow-root >/dev/null 2>&1 || true
  fi
  echo "ROLLBACK|creditoparaveiculo.com|rc=$rc"
  exit "$rc"
}
trap rollback ERR
sudo -n -u "$USER" cp "$STAGE/includes/class-mgs-quiz-admin.php" "$PLUGIN/includes/.class-mgs-quiz-admin.php.new"
sudo -n -u "$USER" mv "$PLUGIN/includes/.class-mgs-quiz-admin.php.new" "$PLUGIN/includes/class-mgs-quiz-admin.php"
sudo -n -u "$USER" cp "$STAGE/includes/class-mgs-quiz-csv.php" "$PLUGIN/includes/.class-mgs-quiz-csv.php.new"
sudo -n -u "$USER" mv "$PLUGIN/includes/.class-mgs-quiz-csv.php.new" "$PLUGIN/includes/class-mgs-quiz-csv.php"
sudo -n -u "$USER" cp "$STAGE/mgs-quiz-carro.php" "$PLUGIN/.mgs-quiz-carro.php.new"
sudo -n -u "$USER" mv "$PLUGIN/.mgs-quiz-carro.php.new" "$PLUGIN/mgs-quiz-carro.php"
installed=1
sudo -n -u "$USER" rm -rf "$STAGE"
sudo -n -u "$USER" wp --path="$SITE" cache flush --allow-root >/dev/null || true

version=$(sudo -n -u "$USER" wp --path="$SITE" plugin get mgs-quiz-carro --field=version --allow-root)
test "$version" = "1.7.7"
sudo -n -u "$USER" wp --path="$SITE" plugin is-active mgs-quiz-carro --allow-root
live_main=$(sudo -n -u "$USER" sha256sum "$PLUGIN/mgs-quiz-carro.php" | cut -d' ' -f1)
live_admin=$(sudo -n -u "$USER" sha256sum "$PLUGIN/includes/class-mgs-quiz-admin.php" | cut -d' ' -f1)
live_csv=$(sudo -n -u "$USER" sha256sum "$PLUGIN/includes/class-mgs-quiz-csv.php" | cut -d' ' -f1)
test "$live_main" = "$EXPECTED_NEW_MAIN"; test "$live_admin" = "$EXPECTED_NEW_ADMIN"; test "$live_csv" = "$EXPECTED_NEW_CSV"

readback=$(sudo -n -u "$USER" wp --path="$SITE" eval '
global $wpdb;
$start=MGS_Quiz_Admin::local_date_bound_to_utc("2026-07-15");
$end=MGS_Quiz_Admin::local_date_bound_to_utc("2026-07-15",true);
$display=MGS_Quiz_Admin::format_created_at("2026-07-15 03:00:00");
$table=$wpdb->prefix."mgs_quiz_leads";
$count=(int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE created_at >= %s AND created_at < %s",$start,$end));
echo wp_json_encode(array("timezone"=>MGS_Quiz_Admin::BUSINESS_TIMEZONE,"start"=>$start,"end_exclusive"=>$end,"display"=>$display,"count_2026_07_15"=>$count));
' --allow-root)
python3 - "$readback" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); expected={'timezone':'America/Sao_Paulo','start':'2026-07-15 03:00:00','end_exclusive':'2026-07-16 03:00:00','display':'15/07/2026, 00:00','count_2026_07_15':6813}
if x!=expected: raise SystemExit(f'timezone readback mismatch: {x}')
print('TIMEZONE_READBACK|'+json.dumps(x,separators=(',',':')))
PY
for url in 'https://creditoparaveiculo.com/quiz-car-parcelas/' 'https://creditoparaveiculo.com/quiz-car-001-cl001/' 'https://creditoparaveiculo.com/wp-json/mgs-quiz/v1/config?slug=quiz-car-parcelas'; do
  code=$(curl -L -sS -o /dev/null -w '%{http_code}' "$url"); test "$code" = "200"; echo "HTTP|$code|$url"
done
trap - ERR
echo "COMPLETE|creditoparaveiculo.com|version=$version|backup=$BACKUP|main=$live_main|admin=$live_admin|csv=$live_csv"
