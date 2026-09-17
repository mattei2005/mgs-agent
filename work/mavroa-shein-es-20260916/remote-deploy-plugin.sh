#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/runcloud/webapps/mavroa
BACK=/home/runcloud/backups/mavroa-direct-quiz-20260917T023143Z
PACKAGE=/tmp/mgs-direct-quiz-1.2.1.tar.gz
FINAL="$ROOT/wp-content/plugins/mgs-direct-quiz"
STAGING="$ROOT/wp-content/plugins/.mgs-direct-quiz-new-20260917T023143Z"
if sudo test -e "$FINAL"; then
  echo 'ABORT: plugin target appeared after preflight' >&2
  exit 20
fi
if sudo test -e "$STAGING"; then
  echo 'ABORT: staging target already exists' >&2
  exit 21
fi
sudo -u runcloud mkdir "$STAGING"
sudo -u runcloud tar -xzf "$PACKAGE" --strip-components=1 -C "$STAGING"
sudo -u runcloud php -l "$STAGING/mgs-direct-quiz.php" >/dev/null
sudo -u runcloud php -l "$STAGING/includes/class-mgs-direct-quiz.php" >/dev/null
sudo -u runcloud php -l "$STAGING/templates/landing.php" >/dev/null
sudo -u runcloud mv "$STAGING" "$FINAL"
if ! sudo -u runcloud wp --path="$ROOT" plugin activate mgs-direct-quiz --allow-root; then
  sudo mv "$FINAL" "$BACK/plugin-failed-activation-20260917T023143Z"
  exit 22
fi
status=$(sudo -u runcloud wp --path="$ROOT" plugin get mgs-direct-quiz --field=status --allow-root)
version=$(sudo -u runcloud wp --path="$ROOT" plugin get mgs-direct-quiz --field=version --allow-root)
count=$(sudo -u runcloud wp --path="$ROOT" eval 'echo count(MGS_Direct_Quiz::items());' --allow-root)
static_version=$(sudo -u runcloud wp --path="$ROOT" option get mgs_direct_quiz_static_version --allow-root)
sudo mv "$PACKAGE" "$BACK/mgs-direct-quiz-1.2.1.tar.gz"
sudo chown runcloud:runcloud "$BACK/mgs-direct-quiz-1.2.1.tar.gz"
printf 'status=%s\nversion=%s\nitems=%s\nstatic_version=%s\n' "$status" "$version" "$count" "$static_version"
