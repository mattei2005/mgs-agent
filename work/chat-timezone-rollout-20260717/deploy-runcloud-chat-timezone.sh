#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-all}
ARTIFACT=/tmp/mgs-chat-funnels-0.4.2-code-only.tar.gz
SMOKE=/tmp/mgs-chat-timezone-smoke.php
EXPECTED_OLD_MAIN=1bdf3f78698687237b7ee25629c2f5ef959e9662d040593efb78aa60a57cfbcf
EXPECTED_OLD_CLASS=9739f296d88424bc3aa983d9a7be90674f554ad47f2f3100156d8aece9f73f09
EXPECTED_NEW_MAIN=ddd390a604be6df2e295e5d5cd66d2dcbed97fd1af4fb19b094b0cb81cc3268f
EXPECTED_NEW_CLASS=d72ad096a4575674ef74f1b87c1036e2427821bc12b2fe9784514de2c44e9717
TS=$(date -u +%Y%m%dT%H%M%SZ)

test -s "$ARTIFACT"; tar -tzf "$ARTIFACT" >/dev/null; php -l "$SMOKE" >/dev/null
sites=(
  'eggbev.com|/home/runcloud/webapps/eggbev|runcloud|G006'
  'newsoun.com|/home/runcloud/webapps/newsoun|runcloud|G005'
  'finance.topfeed.fun|/home/runcloud/webapps/topfeedfinance|runcloud|G004'
  'wantabrand.com|/home/runcloud2/webapps/wantabrand|runcloud2|G001'
  'zuout.com|/home/runcloud/webapps/zuout|runcloud|G002'
  'zytiva.com|/home/runcloud/webapps/zytiva|runcloud|G003'
)

for entry in "${sites[@]}"; do
  IFS='|' read -r domain site user manager <<< "$entry"
  if [ "$TARGET" != "all" ] && [ "$TARGET" != "$domain" ]; then continue; fi
  plugin="$site/wp-content/plugins/mgs-chat-funnels"
  backup_root="/var/tmp/mgs-production-backups"
  if [ "$user" = "runcloud2" ]; then backup_root="/var/tmp/mgs-production-backups-runcloud2"; fi
  backup="$backup_root/$domain/mgs-chat-funnels-timezone/$TS"
  stage="$site/wp-content/plugins/.mgs-chat-funnels-0.4.2-stage-$TS"
  echo "BEGIN|$domain"
  version=$(sudo -n -u "$user" wp --path="$site" plugin get mgs-chat-funnels --field=version --allow-root)
  test "$version" = "0.4.1"
  sudo -n -u "$user" wp --path="$site" plugin is-active mgs-chat-funnels --allow-root
  old_main=$(sudo -n -u "$user" sha256sum "$plugin/mgs-chat-funnels.php" | cut -d' ' -f1)
  old_class=$(sudo -n -u "$user" sha256sum "$plugin/includes/class-mgs-chat-sms.php" | cut -d' ' -f1)
  test "$old_main" = "$EXPECTED_OLD_MAIN"; test "$old_class" = "$EXPECTED_OLD_CLASS"

  sudo -n -u "$user" mkdir -p "$backup" "$stage/includes"
  sudo -n -u "$user" tar -czf "$backup/plugin-before.tar.gz" -C "$site/wp-content/plugins" mgs-chat-funnels
  sudo -n -u "$user" tar -tzf "$backup/plugin-before.tar.gz" >/dev/null
  sudo -n -u "$user" sh -c "wp --path='$site' db export - --allow-root --quiet 2>'$backup/db-export.stderr' | gzip -c > '$backup/database-before.sql.gz'"
  sudo -n -u "$user" gzip -t "$backup/database-before.sql.gz"
  sudo -n -u "$user" tar -xzf "$ARTIFACT" -C "$stage"
  sudo -n -u "$user" php -l "$stage/mgs-chat-funnels.php" >/dev/null
  sudo -n -u "$user" php -l "$stage/includes/class-mgs-chat-sms.php" >/dev/null
  test "$(sudo -n -u "$user" sha256sum "$stage/mgs-chat-funnels.php" | cut -d' ' -f1)" = "$EXPECTED_NEW_MAIN"
  test "$(sudo -n -u "$user" sha256sum "$stage/includes/class-mgs-chat-sms.php" | cut -d' ' -f1)" = "$EXPECTED_NEW_CLASS"

  installed=0
  rollback() {
    rc=$?
    if [ "$installed" = "1" ]; then
      sudo -n -u "$user" cp "$backup/class-mgs-chat-sms.php" "$plugin/includes/class-mgs-chat-sms.php"
      sudo -n -u "$user" cp "$backup/mgs-chat-funnels.php" "$plugin/mgs-chat-funnels.php"
      sudo -n -u "$user" wp --path="$site" cache flush --allow-root >/dev/null 2>&1 || true
    fi
    echo "ROLLBACK|$domain|rc=$rc"
    exit "$rc"
  }
  trap rollback ERR
  sudo -n -u "$user" cp "$plugin/mgs-chat-funnels.php" "$backup/mgs-chat-funnels.php"
  sudo -n -u "$user" cp "$plugin/includes/class-mgs-chat-sms.php" "$backup/class-mgs-chat-sms.php"
  sudo -n -u "$user" cp "$stage/includes/class-mgs-chat-sms.php" "$plugin/includes/.class-mgs-chat-sms.php.new"
  sudo -n -u "$user" mv "$plugin/includes/.class-mgs-chat-sms.php.new" "$plugin/includes/class-mgs-chat-sms.php"
  sudo -n -u "$user" cp "$stage/mgs-chat-funnels.php" "$plugin/.mgs-chat-funnels.php.new"
  sudo -n -u "$user" mv "$plugin/.mgs-chat-funnels.php.new" "$plugin/mgs-chat-funnels.php"
  installed=1
  sudo -n -u "$user" rm -rf "$stage"
  sudo -n -u "$user" wp --path="$site" cache flush --allow-root >/dev/null || true

  version=$(sudo -n -u "$user" wp --path="$site" plugin get mgs-chat-funnels --field=version --allow-root)
  test "$version" = "0.4.2"
  sudo -n -u "$user" wp --path="$site" plugin is-active mgs-chat-funnels --allow-root
  live_main=$(sudo -n -u "$user" sha256sum "$plugin/mgs-chat-funnels.php" | cut -d' ' -f1)
  live_class=$(sudo -n -u "$user" sha256sum "$plugin/includes/class-mgs-chat-sms.php" | cut -d' ' -f1)
  test "$live_main" = "$EXPECTED_NEW_MAIN"; test "$live_class" = "$EXPECTED_NEW_CLASS"

  readback=$(sudo -n -u "$user" wp --path="$site" eval '
  $start=MGS_Chat_SMS::local_date_bound_to_utc("2026-07-15");
  $end=MGS_Chat_SMS::local_date_bound_to_utc("2026-07-15",true);
  $display=MGS_Chat_SMS::format_created_at("2026-07-15 03:00:00");
  echo wp_json_encode(array("timezone"=>MGS_Chat_SMS::BUSINESS_TIMEZONE,"start"=>$start,"end_exclusive"=>$end,"display"=>$display));
  ' --allow-root)
  python3 - "$readback" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); expected={'timezone':'America/Sao_Paulo','start':'2026-07-15 03:00:00','end_exclusive':'2026-07-16 03:00:00','display':'15/07/2026, 00:00'}
if x!=expected: raise SystemExit(f'timezone readback mismatch: {x}')
print('TIMEZONE_READBACK|'+json.dumps(x,separators=(',',':')))
PY
  sudo -n -u "$user" env MGS_EXPECT_MANAGER="$manager" wp --path="$site" eval-file "$SMOKE" --allow-root | sed "s/^/SMOKE|$domain|/"
  for route in /chat/car/br1/ /chat-sms/car/br1/; do
    code=$(curl -L -sS -o /dev/null -w '%{http_code}' "https://$domain$route")
    test "$code" = "200"
    echo "HTTP|$domain|$route|$code"
  done
  trap - ERR
  echo "COMPLETE|$domain|version=$version|manager=$manager|backup=$backup|main=$live_main|class=$live_class"
done
