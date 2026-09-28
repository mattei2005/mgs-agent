#!/usr/bin/env python3
"""Provision dedicated Atena WordPress credentials without exposing secrets."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORK = Path("/root/mgs-agent/work/atena-wordpress-access-20260920")
RUNCLOUD_MANIFEST = WORK / "runcloud-preflight.json"
EXTERNAL_MANIFEST = WORK / "external-preflight.json"
STATE_PATH = WORK / "provision-state.json"
VAULT = "MGS Conteúdo"
USERNAME = "atena"
EMAIL = "atena@matteiservicesinc.com"
DISPLAY_NAME = "Atena MGS"
ROLE = "editor"
APP_NAME = "Atena API - MGS"
ITEM_PREFIX = "Atena WordPress - "
AUTHORIZATION_MESSAGE_ID = "1551314627374219305"
SERVER_ITEMS = {
    "162.55.28.178": "Runcloud Server 01 - 162.55.28.178- zeus Acesso",
    "162.55.28.179": "Runcloud Server 02 - 162.55.28.179- zeus Acesso",
    "46.4.95.117": "Runcloud Server 03 - 46.4.95.117- zeus Acesso",
}


class ProvisionError(RuntimeError):
    pass


def run(
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = True,
    timeout: int = 180,
) -> subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(
        args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        raise ProvisionError(f"command failed rc={proc.returncode}: {stderr[:500]}")
    return proc


def op(args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    return run(["op", *args], input_bytes=input_bytes, timeout=180).stdout


def op_secret(item_id: str, field_label: str) -> str:
    value = op(
        [
            "item",
            "get",
            item_id,
            "--vault",
            VAULT,
            "--fields",
            f"label={field_label}",
            "--reveal",
        ]
    ).decode().rstrip("\r\n")
    if not value:
        raise ProvisionError(f"empty 1Password field: {field_label}")
    return value


def list_items() -> list[dict[str, Any]]:
    return json.loads(op(["item", "list", "--vault", VAULT, "--format", "json"]))


def item_id_for_domain(domain: str) -> str | None:
    title = f"{ITEM_PREFIX}{domain}".casefold()
    matches = [x["id"] for x in list_items() if x.get("title", "").casefold() == title]
    if len(matches) > 1:
        raise ProvisionError(f"duplicate 1Password items for {domain}")
    return matches[0] if matches else None


def curl_config_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def curl_json(
    url: str,
    username: str,
    password: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    expected: set[int] | None = None,
) -> tuple[int, Any]:
    expected = expected or {200}
    with tempfile.TemporaryDirectory(prefix="atena-wp-curl-") as td:
        td_path = Path(td)
        cfg = td_path / "curl.cfg"
        body = td_path / "body.json"
        payload_path = td_path / "payload.json"
        cfg.write_text(
            f'user = "{curl_config_value(username)}:{curl_config_value(password)}"\n'
            "silent\nshow-error\nconnect-timeout = 20\nmax-time = 90\n",
            encoding="utf-8",
        )
        os.chmod(cfg, 0o600)
        args = [
            "curl",
            "--config",
            str(cfg),
            "--request",
            method,
            "--output",
            str(body),
            "--write-out",
            "%{http_code}",
            url,
        ]
        if payload is not None:
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            os.chmod(payload_path, 0o600)
            args[1:1] = [
                "--header",
                "Content-Type: application/json",
                "--data-binary",
                f"@{payload_path}",
            ]
        proc = run(args, check=False, timeout=120)
        try:
            http = int(proc.stdout.decode().strip() or "0")
        except ValueError as exc:
            raise ProvisionError("curl returned an invalid HTTP status") from exc
        raw = body.read_text(encoding="utf-8", errors="replace") if body.exists() else ""
        try:
            parsed: Any = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"non_json_body": raw[:300]}
        if http not in expected:
            code = parsed.get("code") if isinstance(parsed, dict) else None
            message = parsed.get("message") if isinstance(parsed, dict) else None
            raise ProvisionError(f"HTTP {http} code={code!r} message={message!r}")
        return http, parsed


def make_login_template(
    domain: str,
    login_password: str,
    app_password: str,
    user_id: int,
) -> dict[str, Any]:
    template = json.loads(op(["item", "template", "get", "Login", "--format", "json"]))
    template["title"] = f"{ITEM_PREFIX}{domain}"
    template["tags"] = ["atena", "wordpress", "mgs-agent"]
    template["urls"] = [
        {"label": "WordPress Admin", "primary": True, "href": f"https://{domain}/wp-admin/"},
        {"label": "WordPress REST API", "href": f"https://{domain}/wp-json/wp/v2/"},
    ]
    by_id = {field.get("id"): field for field in template.get("fields", [])}
    by_id["username"]["value"] = USERNAME
    by_id["password"]["value"] = login_password
    by_id["notesPlain"]["value"] = (
        "Credencial dedicada da Atena para operação editorial WordPress. "
        "Função: Editor. A senha de aplicativo deve ser usada somente na REST API; "
        "a senha normal é reservada para recuperação/login autorizado. "
        f"Autorização Discord: {AUTHORIZATION_MESSAGE_ID}."
    )
    section_id = "wordpress_api"
    template["sections"] = [{"id": section_id, "label": "WordPress API"}]
    template["fields"].extend(
        [
            {
                "id": "wp_app_password",
                "label": "wp_app_password",
                "type": "CONCEALED",
                "value": app_password,
                "section": {"id": section_id},
            },
            {
                "id": "wp_user_id",
                "label": "wp_user_id",
                "type": "STRING",
                "value": str(user_id),
                "section": {"id": section_id},
            },
            {
                "id": "wp_role",
                "label": "wp_role",
                "type": "STRING",
                "value": ROLE,
                "section": {"id": section_id},
            },
            {
                "id": "site_domain",
                "label": "site_domain",
                "type": "STRING",
                "value": domain,
                "section": {"id": section_id},
            },
        ]
    )
    return template


def write_or_update_item(
    domain: str,
    login_password: str,
    app_password: str,
    user_id: int,
) -> tuple[str, str]:
    existing_id = item_id_for_domain(domain)
    template = make_login_template(domain, login_password, app_password, user_id)
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="atena-1p-template-", suffix=".json", delete=False
    ) as fh:
        template_path = Path(fh.name)
        json.dump(template, fh)
        fh.flush()
        os.fchmod(fh.fileno(), 0o600)
    try:
        if existing_id:
            raw = op(
                [
                    "item",
                    "edit",
                    existing_id,
                    "--vault",
                    VAULT,
                    "--template",
                    str(template_path),
                    "--format",
                    "json",
                ]
            )
            action = "updated"
        else:
            raw = op(
                [
                    "item",
                    "create",
                    "--vault",
                    VAULT,
                    "--template",
                    str(template_path),
                    "--format",
                    "json",
                ]
            )
            action = "created"
        item_id = json.loads(raw)["id"]
    finally:
        template_path.unlink(missing_ok=True)

    readback = json.loads(
        op(["item", "get", item_id, "--vault", VAULT, "--format", "json", "--reveal"])
    )
    fields = {field.get("id"): field.get("value", "") for field in readback.get("fields", [])}
    checks = {
        "title": readback.get("title") == f"{ITEM_PREFIX}{domain}",
        "username": fields.get("username") == USERNAME,
        "password": fields.get("password") == login_password,
        "wp_app_password": fields.get("wp_app_password") == app_password,
        "wp_user_id": str(fields.get("wp_user_id")) == str(user_id),
        "wp_role": fields.get("wp_role") == ROLE,
        "site_domain": fields.get("site_domain") == domain,
    }
    if not all(checks.values()):
        failed = [name for name, ok in checks.items() if not ok]
        raise ProvisionError(f"1Password readback mismatch: {failed}")
    return item_id, action


def validate_atena_api(domain: str, app_password: str) -> int:
    http, payload = curl_json(
        f"https://{domain}/wp-json/wp/v2/posts?context=edit&per_page=1&_fields=id,status",
        USERNAME,
        app_password,
        expected={200},
    )
    if not isinstance(payload, list):
        raise ProvisionError("authenticated posts endpoint did not return a list")
    return http


def provision_runcloud(target: dict[str, Any]) -> dict[str, Any]:
    domain = target["domain"]
    host = target["host"]
    server_item = SERVER_ITEMS[host]
    ssh_password = op_secret(
        next(
            x["id"]
            for x in list_items()
            if x.get("title", "").casefold() == server_item.casefold()
        ),
        "password",
    )
    with tempfile.NamedTemporaryFile(mode="w", prefix="atena-sshpass-", delete=False) as fh:
        pw_path = Path(fh.name)
        fh.write(ssh_password)
        fh.flush()
        os.fchmod(fh.fileno(), 0o600)
    remote_script = r'''set -euo pipefail
path=$1
owner=$2
username=atena
email=atena@matteiservicesinc.com
wordfence_app_passwords=unchanged
if runuser -u "$owner" -- wp --path="$path" plugin is-active wordfence --skip-themes >/dev/null 2>&1; then
  disabled=$(runuser -u "$owner" -- wp --path="$path" eval 'echo class_exists("wfConfig") && wfConfig::get("loginSec_disableApplicationPasswords") ? "1" : "0";' --skip-themes 2>/dev/null || printf 'unknown')
  if [ "$disabled" = 1 ]; then
    runuser -u "$owner" -- wp --path="$path" eval 'wfConfig::set("loginSec_disableApplicationPasswords", false);' --skip-themes >/dev/null 2>&1
    readback=$(runuser -u "$owner" -- wp --path="$path" eval 'echo class_exists("wfConfig") && wfConfig::get("loginSec_disableApplicationPasswords") ? "1" : "0";' --skip-themes 2>/dev/null || printf 'unknown')
    [ "$readback" = 0 ]
    wordfence_app_passwords=enabled
  fi
fi
created=0
uid=''
secret_dir=''
rollback() {
  rc=$?
  if [ -n "$secret_dir" ]; then
    rm -rf "$secret_dir" >/dev/null 2>&1 || true
  fi
  if [ "$rc" -ne 0 ] && [ "$created" = 1 ] && [ -n "$uid" ]; then
    runuser -u "$owner" -- wp --path="$path" user delete "$uid" --yes --skip-plugins --skip-themes >/dev/null 2>&1 || true
  fi
  exit "$rc"
}
trap rollback EXIT
existing_uid=$(runuser -u "$owner" -- wp --path="$path" user get "$username" --field=ID --skip-plugins --skip-themes 2>/dev/null || true)
login_password=$(openssl rand -hex 32)
secret_dir=$(mktemp -d /tmp/atena-wp-user.XXXXXX)
chown "$owner":"$owner" "$secret_dir"
chmod 700 "$secret_dir"
printf '%s' "$login_password" > "$secret_dir/login-password"
cat > "$secret_dir/provision-user.php" <<'PHP'
<?php
$password_file = getenv('ATENA_PASSWORD_FILE');
$password = is_string($password_file) ? trim((string) file_get_contents($password_file)) : '';
if ($password === '') {
    fwrite(STDERR, "missing password input\n");
    exit(2);
}
$login = 'atena';
$email = 'atena@matteiservicesinc.com';
$user = get_user_by('login', $login);
if ($user) {
    if (strtolower((string) $user->user_email) !== $email) {
        fwrite(STDERR, "existing user email mismatch\n");
        exit(3);
    }
    wp_set_password($password, $user->ID);
    $updated = wp_update_user([
        'ID' => $user->ID,
        'display_name' => 'Atena MGS',
        'role' => 'editor',
    ]);
    if (is_wp_error($updated)) {
        fwrite(STDERR, $updated->get_error_code() . "\n");
        exit(4);
    }
    $uid = (int) $user->ID;
} else {
    $uid = wp_insert_user([
        'user_login' => $login,
        'user_email' => $email,
        'user_pass' => $password,
        'display_name' => 'Atena MGS',
        'role' => 'editor',
    ]);
    if (is_wp_error($uid)) {
        fwrite(STDERR, $uid->get_error_code() . "\n");
        exit(5);
    }
    $uid = (int) $uid;
}
echo $uid;
PHP
chown "$owner":"$owner" "$secret_dir/login-password" "$secret_dir/provision-user.php"
chmod 600 "$secret_dir/login-password" "$secret_dir/provision-user.php"
uid=$(runuser -u "$owner" -- env ATENA_PASSWORD_FILE="$secret_dir/login-password" wp --path="$path" eval-file "$secret_dir/provision-user.php" --skip-plugins --skip-themes)
rm -rf "$secret_dir"
if [ -n "$existing_uid" ]; then
  [ "$uid" = "$existing_uid" ]
  while IFS= read -r uuid; do
    [ -n "$uuid" ] || continue
    runuser -u "$owner" -- wp --path="$path" user application-password delete "$uid" "$uuid" --skip-plugins --skip-themes >/dev/null
  done < <(runuser -u "$owner" -- wp --path="$path" user application-password list "$uid" --format=json --skip-plugins --skip-themes 2>/dev/null | python3 -c 'import json,sys; [print(x["uuid"]) for x in json.load(sys.stdin) if x.get("name")=="Atena API - MGS"]')
  recovery=rotated
else
  created=1
  recovery=created
fi
app_password=$(runuser -u "$owner" -- wp --path="$path" user application-password create "$uid" 'Atena API - MGS' --porcelain --skip-plugins --skip-themes)
role=$(runuser -u "$owner" -- wp --path="$path" user get "$uid" --field=roles --skip-plugins --skip-themes)
[ "$role" = editor ]
count=$(runuser -u "$owner" -- wp --path="$path" user application-password list "$uid" --format=count --skip-plugins --skip-themes)
printf '%s\0%s\0%s\0%s\0%s\0%s\0' "$uid" "$login_password" "$app_password" "$count" "$recovery" "$wordfence_app_passwords"
created=0
trap - EXIT
'''
    try:
        proc = run(
            [
                "sshpass",
                "-f",
                str(pw_path),
                "ssh",
                "-o",
                "PreferredAuthentications=password",
                "-o",
                "PubkeyAuthentication=no",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "UserKnownHostsFile=/root/.ssh/known_hosts_mgs",
                f"zeus@{host}",
                "sudo",
                "-n",
                "bash",
                "-s",
                "--",
                target["path"],
                target["owner"],
            ],
            input_bytes=remote_script.encode(),
            timeout=180,
        )
    finally:
        pw_path.unlink(missing_ok=True)
    parts = proc.stdout.split(b"\0")
    if len(parts) < 7:
        raise ProvisionError("invalid secret bundle returned by RunCloud provisioner")
    user_id = int(parts[0].decode())
    login_password = parts[1].decode()
    app_password = parts[2].decode()
    app_count = int(parts[3].decode())
    recovery = parts[4].decode()
    wordfence_app_passwords = parts[5].decode()
    if not login_password or not app_password or app_count < 1:
        raise ProvisionError("invalid generated credential state")
    item_id, item_action = write_or_update_item(
        domain, login_password, app_password, user_id
    )
    api_http = validate_atena_api(domain, app_password)
    return {
        "domain": domain,
        "route": "runcloud_wpcli",
        "host": host,
        "path": target["path"],
        "user_id": user_id,
        "username": USERNAME,
        "email": EMAIL,
        "role": ROLE,
        "application_password_count": app_count,
        "onepassword_item_id": item_id,
        "onepassword_item_title": f"{ITEM_PREFIX}{domain}",
        "onepassword_action": item_action,
        "wordpress_action": recovery,
        "wordfence_application_passwords": wordfence_app_passwords,
        "api_validation_http": api_http,
        "status": "validated",
    }


def external_admin_credentials(target: dict[str, Any]) -> tuple[str, str]:
    return (
        op_secret(target["admin_item_id"], target["username_field"]),
        op_secret(target["admin_item_id"], target["application_password_field"]),
    )


def provision_external(target: dict[str, Any]) -> dict[str, Any]:
    domain = target["domain"]
    admin_user, admin_app_password = external_admin_credentials(target)
    _, users = curl_json(
        f"https://{domain}/wp-json/wp/v2/users?search=atena&context=edit&per_page=100&_fields=id,slug,email,roles",
        admin_user,
        admin_app_password,
    )
    exact = [u for u in users if str(u.get("slug", "")).casefold() == USERNAME]
    if len(exact) > 1:
        raise ProvisionError("multiple exact Atena users returned")
    login_password = run(["openssl", "rand", "-base64", "48"]).stdout.decode().strip()
    if not login_password:
        raise ProvisionError("failed to generate login password")
    if exact:
        user_id = int(exact[0]["id"])
        if str(exact[0].get("email", "")).casefold() != EMAIL:
            raise ProvisionError("existing Atena user has a different email")
        curl_json(
            f"https://{domain}/wp-json/wp/v2/users/{user_id}",
            admin_user,
            admin_app_password,
            method="POST",
            payload={
                "password": login_password,
                "roles": [ROLE],
                "name": DISPLAY_NAME,
            },
            expected={200},
        )
        wordpress_action = "rotated"
    else:
        _, created = curl_json(
            f"https://{domain}/wp-json/wp/v2/users",
            admin_user,
            admin_app_password,
            method="POST",
            payload={
                "username": USERNAME,
                "email": EMAIL,
                "password": login_password,
                "name": DISPLAY_NAME,
                "roles": [ROLE],
            },
            expected={201},
        )
        user_id = int(created["id"])
        wordpress_action = "created"

    _, existing_apps = curl_json(
        f"https://{domain}/wp-json/wp/v2/users/{user_id}/application-passwords?context=edit",
        admin_user,
        admin_app_password,
    )
    for app in existing_apps:
        if app.get("name") == APP_NAME and app.get("uuid"):
            curl_json(
                f"https://{domain}/wp-json/wp/v2/users/{user_id}/application-passwords/{app['uuid']}",
                admin_user,
                admin_app_password,
                method="DELETE",
                expected={200},
            )
    _, app_created = curl_json(
        f"https://{domain}/wp-json/wp/v2/users/{user_id}/application-passwords",
        admin_user,
        admin_app_password,
        method="POST",
        payload={"name": APP_NAME},
        expected={201},
    )
    app_password = app_created.get("password", "")
    if not app_password:
        raise ProvisionError("WordPress did not return the new application password")
    _, apps_after = curl_json(
        f"https://{domain}/wp-json/wp/v2/users/{user_id}/application-passwords?context=edit",
        admin_user,
        admin_app_password,
    )
    app_count = len(apps_after)
    item_id, item_action = write_or_update_item(
        domain, login_password, app_password, user_id
    )
    api_http = validate_atena_api(domain, app_password)
    _, user_readback = curl_json(
        f"https://{domain}/wp-json/wp/v2/users/{user_id}?context=edit&_fields=id,slug,email,roles,name",
        admin_user,
        admin_app_password,
    )
    if (
        int(user_readback.get("id", 0)) != user_id
        or user_readback.get("slug") != USERNAME
        or str(user_readback.get("email", "")).casefold() != EMAIL
        or ROLE not in user_readback.get("roles", [])
    ):
        raise ProvisionError("external WordPress user readback mismatch")
    return {
        "domain": domain,
        "route": "external_rest",
        "user_id": user_id,
        "username": USERNAME,
        "email": EMAIL,
        "role": ROLE,
        "application_password_count": app_count,
        "onepassword_item_id": item_id,
        "onepassword_item_title": f"{ITEM_PREFIX}{domain}",
        "onepassword_action": item_action,
        "wordpress_action": wordpress_action,
        "api_validation_http": api_http,
        "status": "validated",
    }


def load_targets() -> dict[str, dict[str, Any]]:
    runcloud = json.loads(RUNCLOUD_MANIFEST.read_text())["targets"]
    external = json.loads(EXTERNAL_MANIFEST.read_text())["targets"]
    targets = {row["domain"]: {**row, "route": "runcloud"} for row in runcloud}
    targets.update({row["domain"]: {**row, "route": "external"} for row in external})
    if len(targets) != 45:
        raise ProvisionError(f"expected 45 targets, got {len(targets)}")
    return targets


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "operation": "atena-wordpress-access-20260920",
        "authorization_message_id": AUTHORIZATION_MESSAGE_ID,
        "targets_expected": 45,
        "results": {},
        "failures": {},
    }


def save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, STATE_PATH)


def provision_domain(domain: str) -> dict[str, Any]:
    targets = load_targets()
    if domain not in targets:
        raise ProvisionError(f"domain is not in the approved 45-site scope: {domain}")
    target = targets[domain]
    if target["route"] == "runcloud":
        return provision_runcloud(target)
    return provision_external(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("domains", nargs="+", help="Approved domains to provision")
    args = parser.parse_args()
    state = load_state()
    for domain in args.domains:
        try:
            result = provision_domain(domain)
            state["results"][domain] = result
            state["failures"].pop(domain, None)
            save_state(state)
            print(
                f"PASS {domain} route={result['route']} user_id={result['user_id']} "
                f"role={result['role']} api_http={result['api_validation_http']} "
                f"onepassword={result['onepassword_action']}"
            )
        except Exception as exc:  # bounded per-domain failure capture
            state["failures"][domain] = {
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
                "at": datetime.now(timezone.utc).isoformat(),
            }
            save_state(state)
            print(f"FAIL {domain} error={type(exc).__name__}: {str(exc)[:500]}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
