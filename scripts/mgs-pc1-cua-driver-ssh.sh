#!/usr/bin/env bash
set -euo pipefail

readonly SSH_BIN=/usr/bin/ssh
readonly SSH_KEY=/root/.ssh/mgs-pc1-zeus_ed25519
readonly SSH_HOST=matte@100.85.69.58
readonly REMOTE_DRIVER='"C:\Users\matte\AppData\Local\hermes\tools\cua-driver-0.21.0-win32-x64\cua-driver.exe"'
readonly REMOTE_SOCKET='\\.\pipe\cua-driver'

ssh_args=(
  -T
  -i "$SSH_KEY"
  -o BatchMode=yes
  -o StrictHostKeyChecking=yes
  -o ConnectTimeout=10
  -o ConnectionAttempts=2
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=2
  -o ClearAllForwardings=yes
  -o ExitOnForwardFailure=yes
  -o LogLevel=ERROR
  "$SSH_HOST"
)

# Hermes maps approvals.mode=off to an unrestricted private daemon. A private
# daemon cannot be launched from Windows OpenSSH Session 0 because it would not
# see the interactive desktop. Keep the remote boundary fail-closed: satisfy the
# local embedded-daemon lifecycle while every real MCP/CLI call is attached to
# the existing standard-mode daemon in the logged-in Windows session.
if [[ "${1:-}" == "serve" ]]; then
  for arg in "$@"; do
    if [[ "$arg" == "--embedded" ]]; then
      exec /usr/bin/sleep infinity
    fi
  done
fi

if [[ "${1:-}" == "mcp" ]]; then
  shift
  forwarded=()
  while (( $# > 0 )); do
    case "$1" in
      --embedded)
        shift
        ;;
      --socket)
        (( $# >= 2 )) || { echo "missing value for --socket" >&2; exit 2; }
        shift 2
        ;;
      *)
        printf "unsupported transport argument\n" >&2; exit 2
        shift
        ;;
    esac
  done
  exec "$SSH_BIN" "${ssh_args[@]}" "$REMOTE_DRIVER" mcp --socket "$REMOTE_SOCKET" "${forwarded[@]}"
fi

if [[ "${1:-}" == "status" ]]; then
  shift
  forwarded=()
  while (( $# > 0 )); do
    case "$1" in
      --socket)
        (( $# >= 2 )) || { echo "missing value for --socket" >&2; exit 2; }
        shift 2
        ;;
      *)
        printf "unsupported transport argument\n" >&2; exit 2
        shift
        ;;
    esac
  done
  exec "$SSH_BIN" "${ssh_args[@]}" "$REMOTE_DRIVER" status --socket "$REMOTE_SOCKET" "${forwarded[@]}"
fi

if [[ "${1:-}" == "stop" && " ${*} " == *" --socket "* ]]; then
  # The local placeholder process is terminated by Hermes itself. Never stop
  # the shared interactive Windows daemon while tearing down one Hermes session.
  exit 0
fi

case "${1:-}" in
  manifest|doctor|version|--version)
    [[ $# == 1 ]] || { printf 'read-only command takes no remote argv\n' >&2; exit 2; }
    exec "$SSH_BIN" "${ssh_args[@]}" "$REMOTE_DRIVER" "$1"
    ;;
  call)
    [[ $# == 2 ]] || { printf 'pass structured call data on stdin\n' >&2; exit 2; }
    case "$2" in list_apps|list_windows|get_window_state) exec "$SSH_BIN" "${ssh_args[@]}" "$REMOTE_DRIVER" call "$2" --socket "$REMOTE_SOCKET" ;; esac
    ;;
esac
printf 'unsupported remote command; use structured MCP\n' >&2
exit 2
