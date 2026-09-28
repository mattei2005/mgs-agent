#!/usr/bin/env bash
set -euo pipefail

# Copy this template to a durable root-owned path, replace every __PLACEHOLDER__,
# chmod 700 it, and validate it before setting HERMES_CUA_DRIVER_CMD.
readonly SSH_BIN=/usr/bin/ssh
readonly SSH_KEY='__ABSOLUTE_PRIVATE_KEY_PATH__'
readonly SSH_HOST='__WINDOWS_USER__@__WINDOWS_TAILSCALE_IP__'
readonly REMOTE_DRIVER='"__ABSOLUTE_WINDOWS_CUA_DRIVER_EXE__"'
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

# approvals.mode=off makes Hermes request an unrestricted private daemon. A
# Windows OpenSSH child runs in Session 0 and cannot own the interactive GUI.
# Keep the transport fail-closed: satisfy only the local lifecycle placeholder
# and attach every real operation to the existing standard interactive daemon.
if [[ "${1:-}" == "serve" ]]; then
  for arg in "$@"; do
    [[ "$arg" == "--embedded" ]] && exec /usr/bin/sleep infinity
  done
fi

if [[ "${1:-}" == "mcp" ]]; then
  shift
  forwarded=()
  while (( $# > 0 )); do
    case "$1" in
      --embedded) shift ;;
      --socket)
        (( $# >= 2 )) || { echo "missing value for --socket" >&2; exit 2; }
        shift 2
        ;;
      *) forwarded+=("$1"); shift ;;
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
      *) forwarded+=("$1"); shift ;;
    esac
  done
  exec "$SSH_BIN" "${ssh_args[@]}" "$REMOTE_DRIVER" status --socket "$REMOTE_SOCKET" "${forwarded[@]}"
fi

if [[ "${1:-}" == "stop" && " ${*} " == *" --socket "* ]]; then
  exit 0
fi

exec "$SSH_BIN" "${ssh_args[@]}" "$REMOTE_DRIVER" "$@"
