#!/usr/bin/env bash
set -euo pipefail
set -a
source /root/mgs-agent/.env 2>/dev/null || true
set +a
PW=''
for attempt in 1 2; do
  if PW="$(op item get 'Runcloud Server 02 - 162.55.28.179- zeus Acesso' --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields label=password --reveal 2>/tmp/mgs-quiz-170-op.err)" && [ -n "$PW" ]; then
    break
  fi
  PW=''
  if [ "$attempt" -lt 2 ]; then sleep 180; fi
done
if [ -z "$PW" ]; then
  printf 'DEPLOY_BLOCKED_1PASSWORD_RATE_LIMIT: '
  tr '\n' ' ' </tmp/mgs-quiz-170-op.err | cut -c1-220
  printf '\n'
  exit 75
fi
export SSHPASS="$PW"
SSH_OPTS=(-o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/root/.ssh/known_hosts_mgs)
sshpass -e scp "${SSH_OPTS[@]}" \
  /tmp/mgs-quiz-carro-1.7.0.tar.gz \
  /root/mgs-agent/work/sb-sms-backfill/historical-creditoparaveiculo-import.json \
  /root/mgs-agent/work/sb-sms-backfill/import_backfill.php \
  /root/mgs-agent/work/sb-sms-backfill/report_smoke.php \
  /root/mgs-agent/work/sb-sms-backfill/deploy_170.sh \
  zeus@runcloud-inc02.162-55-28-179.sslip.io:/tmp/
sshpass -e ssh "${SSH_OPTS[@]}" zeus@runcloud-inc02.162-55-28-179.sslip.io \
  'mv /tmp/import_backfill.php /tmp/mgs-quiz-sms-revenue-import.php; mv /tmp/report_smoke.php /tmp/mgs-quiz-sms-revenue-smoke.php; mv /tmp/deploy_170.sh /tmp/deploy-mgs-quiz-carro-170.sh; chmod 700 /tmp/deploy-mgs-quiz-carro-170.sh; sudo /tmp/deploy-mgs-quiz-carro-170.sh'
unset PW SSHPASS
