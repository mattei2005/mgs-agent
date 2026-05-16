#!/bin/bash
# sync-codex-oauth.sh
#
# Sincroniza tokens Codex OAuth do /root/.hermes/auth.json (global)
# para os profiles em /root/.hermes/profiles/*/auth.json quando o profile
# está com providers.openai-codex.last_refresh mais antigo que o global.
#
# Direção: SEMPRE global → profiles (unidirectional).
# Comparação: por providers.openai-codex.last_refresh interno (NÃO mtime).
# Safety check: POST https://chatgpt.com/backend-api/codex/responses com body {}.
#   - 200/400/405 → auth_ok → prossegue
#   - 401/403     → token_invalid → ABORTA (cria alert file)
#   - timeout/5xx → ABORTA (cria alert file)
# Logs: zero token leak. Só timestamp, profile names, last_refresh ISO, HTTP status, ação.
# Write: tempfile + os.replace (atômico) + chmod 0600. Demais chaves preservadas.
# Modos:
#   --dry-run: discovery + safety check + plan, sem write nem alert
#   normal:    aplica mudanças necessárias

set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      cat <<EOF
Uso: $0 [--dry-run]

  --dry-run    Não escreve auth.json nem alert file
  (sem flag)   Aplica mudanças atomically quando necessário
EOF
      exit 0
      ;;
    *) echo "ERRO: arg desconhecido: $arg (use --help)" >&2; exit 2 ;;
  esac
done

GLOBAL_AUTH="/root/.hermes/auth.json"
PROFILES_DIR="/root/.hermes/profiles"
ALERT_FILE="/root/mgs-agent/data/sync-codex-oauth.alert"
ENDPOINT="https://chatgpt.com/backend-api/codex/responses"

[[ ! -f "$GLOBAL_AUTH" ]] && { echo "ERRO: $GLOBAL_AUTH não existe" >&2; exit 1; }
[[ ! -d "$PROFILES_DIR" ]] && { echo "ERRO: $PROFILES_DIR não existe" >&2; exit 1; }

python3 - "$GLOBAL_AUTH" "$PROFILES_DIR" "$ALERT_FILE" "$ENDPOINT" "$DRY_RUN" <<'PYEOF'
import json
import os
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

GLOBAL_AUTH, PROFILES_DIR, ALERT_FILE, ENDPOINT, DRY_RUN_STR = sys.argv[1:6]
DRY_RUN = DRY_RUN_STR == "1"

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def now_iso_micro():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")

def log(msg):
    print(f"[{now_iso()}] {msg}", flush=True)

def write_alert(reason):
    if DRY_RUN:
        log(f"[DRY-RUN] would create alert: {ALERT_FILE} ({reason})")
        return
    try:
        Path(ALERT_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(ALERT_FILE).write_text(f"{now_iso()} {reason}\n")
        log(f"alert: created {ALERT_FILE}")
    except Exception:
        log("WARN: failed to create alert file")

def abort(reason):
    log(f"ABORT: {reason}")
    write_alert(reason)
    sys.exit(1)

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

def get_codex_state(auth):
    """Extract codex state (tokens + last_refresh) without exposing tokens externally."""
    if not isinstance(auth, dict):
        return None
    prov = auth.get("providers")
    if not isinstance(prov, dict):
        return None
    codex = prov.get("openai-codex")
    if not isinstance(codex, dict):
        return None
    tokens = codex.get("tokens")
    if not isinstance(tokens, dict):
        return None
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    last_refresh = codex.get("last_refresh")
    if not (isinstance(access, str) and isinstance(refresh, str) and isinstance(last_refresh, str)):
        return None
    return {"access_token": access, "refresh_token": refresh, "last_refresh": last_refresh}

def parse_iso(s):
    """Parse ISO timestamp robustly (Z suffix or +00:00)."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def safety_check(access_token):
    """POST endpoint with empty JSON body. Returns (http_status_or_None, verdict)."""
    req = urllib.request.Request(
        ENDPOINT,
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, "auth_ok"
    except urllib.error.HTTPError as e:
        if e.code in (200, 400, 405):
            return e.code, "auth_ok"
        if e.code in (401, 403):
            return e.code, "token_invalid"
        if 500 <= e.code <= 599:
            return e.code, "server_error"
        return e.code, "unexpected_status"
    except urllib.error.URLError:
        return None, "network_error"
    except TimeoutError:
        return None, "timeout"
    except Exception:
        return None, "error"

def atomic_write(path, data):
    """Write JSON to a tempfile in same dir, chmod 0600, then os.replace."""
    dirpath = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=".sync-codex.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise

# ============================================================
# DISCOVERY
# ============================================================
mode_tag = "[DRY-RUN]" if DRY_RUN else "[APPLY]"
log(f"{mode_tag} sync-codex-oauth starting")

global_auth = load_json(GLOBAL_AUTH)
if global_auth is None:
    abort(f"failed to read or parse global auth at {GLOBAL_AUTH}")

global_state = get_codex_state(global_auth)
if global_state is None:
    abort("global auth missing providers.openai-codex.tokens or last_refresh")

global_lr_str = global_state["last_refresh"]
try:
    global_lr_dt = parse_iso(global_lr_str)
except ValueError:
    abort(f"global last_refresh not ISO parseable: {global_lr_str}")

log(f"discovery: global last_refresh={global_lr_str}")

# Discover profiles
profile_entries = []
try:
    for entry in sorted(os.listdir(PROFILES_DIR)):
        p_auth = Path(PROFILES_DIR) / entry / "auth.json"
        if p_auth.is_file():
            profile_entries.append((entry, str(p_auth)))
except OSError:
    abort(f"failed to list profiles dir {PROFILES_DIR}")

# Analyze each profile
to_sync = []  # [(name, path, profile_auth_full, profile_state)]
for name, p_path in profile_entries:
    p_auth = load_json(p_path)
    if p_auth is None:
        log(f"discovery: {name} skipped (unreadable or invalid JSON)")
        continue
    p_state = get_codex_state(p_auth)
    if p_state is None:
        log(f"discovery: {name} skipped (no codex state)")
        continue
    p_lr_str = p_state["last_refresh"]
    try:
        p_lr_dt = parse_iso(p_lr_str)
    except ValueError:
        log(f"discovery: {name} skipped (last_refresh not ISO parseable)")
        continue
    if p_lr_dt == global_lr_dt:
        log(f"discovery: {name} last_refresh={p_lr_str} (IN_SYNC)")
    elif p_lr_dt < global_lr_dt:
        log(f"discovery: {name} last_refresh={p_lr_str} (STALE — needs sync)")
        to_sync.append((name, p_path, p_auth, p_state))
    else:
        log(f"discovery: {name} last_refresh={p_lr_str} (NEWER_THAN_GLOBAL, skipping)")

if not to_sync:
    log("done: all profiles in sync, nothing to do")
    sys.exit(0)

# ============================================================
# SAFETY CHECK
# ============================================================
http_code, verdict = safety_check(global_state["access_token"])
code_repr = http_code if http_code is not None else "NONE"
log(f"safety check: POST endpoint → HTTP {code_repr} ({verdict})")

if verdict == "token_invalid":
    abort(f"safety check failed (HTTP {code_repr}): token invalid, no sync performed")
if verdict in ("timeout", "server_error", "network_error", "unexpected_status", "error"):
    abort(f"safety check inconclusive (HTTP {code_repr}, {verdict}): aborting for safety")
# verdict == "auth_ok" → continue

# ============================================================
# APPLY CHANGES (or dry-run plan)
# ============================================================
synced_count = 0
for name, p_path, p_auth, p_state in to_sync:
    # Deep-ish copy: shallow copy top-level + reconstruct nested dicts we touch
    new_auth = dict(p_auth)

    # 1. providers.openai-codex.tokens + last_refresh — MERGE preserves auth_mode + unknown keys
    providers = dict(new_auth.get("providers") or {})
    codex_prov = dict(providers.get("openai-codex") or {})
    tokens = dict(codex_prov.get("tokens") or {})
    tokens["access_token"] = global_state["access_token"]
    tokens["refresh_token"] = global_state["refresh_token"]
    codex_prov["tokens"] = tokens
    codex_prov["last_refresh"] = global_lr_str
    providers["openai-codex"] = codex_prov
    new_auth["providers"] = providers

    # 2. credential_pool.openai-codex[0] (only index 0; preserve other entries + other providers)
    pool = dict(new_auth.get("credential_pool") or {})
    codex_pool = list(pool.get("openai-codex") or [])
    if codex_pool and isinstance(codex_pool[0], dict):
        entry0 = dict(codex_pool[0])
        entry0["access_token"] = global_state["access_token"]
        entry0["refresh_token"] = global_state["refresh_token"]
        entry0["last_refresh"] = global_lr_str
        entry0["last_status"] = "ok"
        entry0["last_status_at"] = None
        entry0["last_error_code"] = None
        entry0["last_error_reason"] = None
        entry0["last_error_message"] = None
        entry0["last_error_reset_at"] = None
        codex_pool[0] = entry0
        pool["openai-codex"] = codex_pool
        new_auth["credential_pool"] = pool

    # 3. updated_at — top-level, reflect sync time
    new_auth["updated_at"] = now_iso_micro()

    if DRY_RUN:
        log(f"[DRY-RUN] would update {name}: last_refresh {p_state['last_refresh']} → {global_lr_str}")
    else:
        atomic_write(p_path, new_auth)
        log(f"sync: {name} updated atomically (last_refresh → {global_lr_str})")
        synced_count += 1

if DRY_RUN:
    names = ", ".join(n for n, _, _, _ in to_sync)
    log(f"[DRY-RUN] would sync {len(to_sync)} profile(s): {names}")
    log("[DRY-RUN] no files modified, no alert created")
else:
    log(f"done: {synced_count} profile(s) synced")
PYEOF
