#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/runcloud/webapps/boostingecon
BACK=/home/runcloud/backups/boostingecon-direct-quiz-20260921T133820Z
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo -u runcloud wp --path="$ROOT" db import "$BACK/database.sql" --allow-root
if [ "$(cat "$BACK/plugin-before.state")" = present ]; then
  if sudo test -d "$ROOT/wp-content/plugins/mgs-direct-quiz"; then
    sudo mv "$ROOT/wp-content/plugins/mgs-direct-quiz" "$BACK/plugin-rolled-back-$STAMP"
  fi
  sudo cp -a "$BACK/plugin-before" "$ROOT/wp-content/plugins/mgs-direct-quiz"
  sudo chown -R runcloud:runcloud "$ROOT/wp-content/plugins/mgs-direct-quiz"
else
  sudo -u runcloud wp --path="$ROOT" plugin deactivate mgs-direct-quiz --allow-root 2>/dev/null || true
  if sudo test -d "$ROOT/wp-content/plugins/mgs-direct-quiz"; then
    sudo mv "$ROOT/wp-content/plugins/mgs-direct-quiz" "$BACK/plugin-removed-by-rollback-$STAMP"
  fi
fi
if sudo test -d "$ROOT/quiz"; then
  sudo mv "$ROOT/quiz" "$BACK/quiz-rolled-back-$STAMP"
fi
if [ "$(cat "$BACK/quiz-before.state")" = present ]; then
  sudo cp -a "$BACK/quiz-before" "$ROOT/quiz"
  sudo chown -R runcloud:runcloud "$ROOT/quiz"
fi
printf 'Rollback restaurado a partir de %s\n' "$BACK"
