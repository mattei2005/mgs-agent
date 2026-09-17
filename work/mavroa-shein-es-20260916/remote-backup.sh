#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/runcloud/webapps/mavroa
BACK=/home/runcloud/backups/mavroa-direct-quiz-20260917T023143Z
sudo mkdir -p "$BACK"
sudo chown runcloud:runcloud "$BACK"
if ! sudo test -s "$BACK/database.sql"; then
  sudo -u runcloud wp --path="$ROOT" db export "$BACK/database.sql" --allow-root
fi
sudo -u runcloud bash -c 'wp --path="$1" post get 9001 --format=json --allow-root > "$2"' _ "$ROOT" "$BACK/post-9001.json"
sudo -u runcloud bash -c 'wp --path="$1" post get 9001 --field=post_content --allow-root > "$2"' _ "$ROOT" "$BACK/post-9001-content.html"
if sudo -u runcloud bash -c 'wp --path="$1" option get mgs_direct_quiz_landings --format=json --allow-root > "$2" 2>/dev/null' _ "$ROOT" "$BACK/mgs_direct_quiz_landings.json"; then
  :
else
  printf '[]\n' | sudo -u runcloud tee "$BACK/mgs_direct_quiz_landings.json" >/dev/null
fi
if sudo test -d "$ROOT/wp-content/plugins/mgs-direct-quiz"; then
  sudo cp -a "$ROOT/wp-content/plugins/mgs-direct-quiz" "$BACK/plugin-before"
  printf 'present\n' | sudo -u runcloud tee "$BACK/plugin-before.state" >/dev/null
else
  printf 'absent\n' | sudo -u runcloud tee "$BACK/plugin-before.state" >/dev/null
fi
if sudo test -d "$ROOT/quiz"; then
  sudo cp -a "$ROOT/quiz" "$BACK/quiz-before"
  printf 'present\n' | sudo -u runcloud tee "$BACK/quiz-before.state" >/dev/null
else
  printf 'absent\n' | sudo -u runcloud tee "$BACK/quiz-before.state" >/dev/null
fi
sudo chown -R runcloud:runcloud "$BACK"
sudo -u runcloud sha256sum "$BACK/database.sql" "$BACK/post-9001.json" "$BACK/post-9001-content.html" "$BACK/mgs_direct_quiz_landings.json" | sudo -u runcloud tee "$BACK/SHA256SUMS" >/dev/null
printf 'BACKUP=%s\n' "$BACK"
printf 'PLUGIN_BEFORE=%s\n' "$(sudo cat "$BACK/plugin-before.state")"
printf 'QUIZ_BEFORE=%s\n' "$(sudo cat "$BACK/quiz-before.state")"
printf 'FILES=%s\n' "$(sudo python3 -c 'import os; print(sum(len(f) for _,_,f in os.walk("/home/runcloud/backups/mavroa-direct-quiz-20260917T023143Z")))')"
