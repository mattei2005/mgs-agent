#!/usr/bin/env bash
set -euo pipefail

section() {
  printf '\n%s\n' "$1"
  printf '%s\n' "$(printf '─%.0s' $(seq 1 ${#1}))"
}

safe_run() {
  local label="$1"; shift
  if ! "$@"; then
    printf 'WARN: %s failed\n' "$label"
  fi
}

section "MGS update status"
printf 'Time:   %s\n' "$(date)"
printf 'Host:   %s\n' "$(hostname)"
printf 'OS:     '
if [ -r /etc/os-release ]; then . /etc/os-release; printf '%s\n' "${PRETTY_NAME:-unknown}"; else printf 'unknown\n'; fi
printf 'Kernel: %s\n' "$(uname -r)"
printf 'Uptime: %s\n' "$(uptime -p 2>/dev/null || true)"

section "APT packages"
apt_pending="$(apt list --upgradable 2>/dev/null | tail -n +2 || true)"
if [ -n "$apt_pending" ]; then
  printf '%s\n' "$apt_pending"
else
  printf 'OK: no APT packages pending\n'
fi

section "Reboot / kernel"
if [ -f /var/run/reboot-required ]; then
  printf 'REBOOT REQUIRED: '
  cat /var/run/reboot-required
else
  printf 'OK: no reboot-required flag\n'
fi
if command -v needrestart >/dev/null 2>&1; then
  needrestart -b 2>/dev/null | awk '/^NEEDRESTART-(KCUR|KEXP|KSTA|SVC):/ {print}' || true
else
  printf 'needrestart not installed\n'
fi

section "Hermes Agent"
if command -v hermes >/dev/null 2>&1; then
  hermes --version 2>&1 | sed -n '1,8p'
  repo=/root/.hermes/hermes-agent
  if [ -d "$repo/.git" ]; then
    git -C "$repo" fetch --quiet origin main 2>/dev/null || true
    head="$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    origin="$(git -C "$repo" rev-parse --short origin/main 2>/dev/null || echo unknown)"
    behind="$(git -C "$repo" rev-list --count HEAD..origin/main 2>/dev/null || echo unknown)"
    printf 'Git:    HEAD=%s origin/main=%s behind=%s\n' "$head" "$origin" "$behind"
    status="$(git -C "$repo" status --short 2>/dev/null || true)"
    if [ -n "$status" ]; then
      printf 'Local changes:\n%s\n' "$status"
    else
      printf 'Local changes: none\n'
    fi
  fi
else
  printf 'hermes not found\n'
fi

section "NPM global"
if command -v npm >/dev/null 2>&1; then
  printf 'Node: %s\n' "$(node -v 2>/dev/null || echo unknown)"
  printf 'npm:  %s\n' "$(npm -v 2>/dev/null || echo unknown)"
  npm_outdated="$(npm outdated -g --depth=0 2>/dev/null || true)"
  if [ -n "$npm_outdated" ]; then
    printf '%s\n' "$npm_outdated"
  else
    printf 'OK: no global npm packages pending\n'
  fi
else
  printf 'npm not installed\n'
fi

section "MGS services"
for svc in zeus-gateway.service atena-gateway.service; do
  if systemctl list-unit-files "$svc" >/dev/null 2>&1; then
    printf '%-24s %s\n' "$svc" "$(systemctl is-active "$svc" 2>/dev/null || true)"
  else
    printf '%-24s not-found\n' "$svc"
  fi
done

section "Disk / memory"
df -h / | awk 'NR==1 || NR==2 {print}'
free -h | awk 'NR==1 || /^Mem:/ {print}'
