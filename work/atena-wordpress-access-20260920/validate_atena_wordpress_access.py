#!/usr/bin/env python3
"""Independent readback for the 45-site Atena WordPress rollout."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORK = Path("/root/mgs-agent/work/atena-wordpress-access-20260920")
sys.path.insert(0, str(WORK))
import provision_atena_wordpress_access as provision  # noqa: E402

SUMMARY_PATH = WORK / "validation-summary.json"


def remote_runcloud_readback(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target in targets:
        grouped[target["host"]].append(target)
    results: dict[str, dict[str, Any]] = {}
    items = provision.list_items()
    by_title = {x.get("title", "").casefold(): x["id"] for x in items}
    for host, rows in grouped.items():
        server_title = provision.SERVER_ITEMS[host]
        server_id = by_title[server_title.casefold()]
        ssh_password = provision.op_secret(server_id, "password")
        with tempfile.NamedTemporaryFile(mode="w", prefix="atena-validate-ssh-", delete=False) as fh:
            pw_path = Path(fh.name)
            fh.write(ssh_password)
            fh.flush()
            os.fchmod(fh.fileno(), 0o600)
        target_lines = "\n".join(
            f"{row['domain']}\t{row['path']}\t{row['owner']}" for row in rows
        )
        script = r'''set -euo pipefail
while IFS=$'\t' read -r domain path owner; do
  [ -n "$domain" ] || continue
  uid=$(runuser -u "$owner" -- wp --path="$path" user get atena --field=ID --skip-plugins --skip-themes)
  email=$(runuser -u "$owner" -- wp --path="$path" user get "$uid" --field=user_email --skip-plugins --skip-themes)
  role=$(runuser -u "$owner" -- wp --path="$path" user get "$uid" --field=roles --skip-plugins --skip-themes)
  apps=$(runuser -u "$owner" -- wp --path="$path" user application-password list "$uid" --format=json --skip-plugins --skip-themes)
  facts=$(runuser -u "$owner" -- wp --path="$path" eval "\$u=$uid; echo json_encode(['edit_posts'=>user_can(\$u,'edit_posts'),'publish_posts'=>user_can(\$u,'publish_posts'),'upload_files'=>user_can(\$u,'upload_files'),'edit_others_posts'=>user_can(\$u,'edit_others_posts')]);" 2>/dev/null)
  wf=not_active
  if runuser -u "$owner" -- wp --path="$path" plugin is-active wordfence --skip-themes >/dev/null 2>&1; then
    disabled=$(runuser -u "$owner" -- wp --path="$path" eval 'echo class_exists("wfConfig") && wfConfig::get("loginSec_disableApplicationPasswords") ? "1" : "0";' --skip-themes 2>/dev/null || printf unknown)
    wf="disabled_option_${disabled}"
  fi
  python3 - "$domain" "$uid" "$email" "$role" "$apps" "$facts" "$wf" <<'PY'
import json,sys
apps=json.loads(sys.argv[5]); facts=json.loads(sys.argv[6])
print(json.dumps({
  'domain':sys.argv[1], 'user_id':int(sys.argv[2]), 'email':sys.argv[3], 'role':sys.argv[4],
  'application_password_count':len(apps),
  'atena_application_password_count':sum(1 for x in apps if x.get('name')=='Atena API - MGS'),
  'capabilities':facts, 'wordfence':sys.argv[7]
},separators=(',',':')))
PY
done
'''
        try:
            proc = provision.run(
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
                ],
                input_bytes=(script + "\n" + target_lines + "\n").encode(),
                timeout=300,
            )
        finally:
            pw_path.unlink(missing_ok=True)
        # The target data appended after the script cannot be consumed because bash -s parses all stdin.
        # This branch is retained only for a defensive empty-output check below.
        for line in proc.stdout.decode().splitlines():
            if line.startswith("{"):
                row = json.loads(line)
                results[row["domain"]] = row
    return results


def remote_runcloud_readback_v2(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Batch each host by embedding only non-secret target metadata in the script."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target in targets:
        grouped[target["host"]].append(target)
    results: dict[str, dict[str, Any]] = {}
    items = provision.list_items()
    by_title = {x.get("title", "").casefold(): x["id"] for x in items}
    for host, rows in grouped.items():
        server_title = provision.SERVER_ITEMS[host]
        ssh_password = provision.op_secret(by_title[server_title.casefold()], "password")
        with tempfile.NamedTemporaryFile(mode="w", prefix="atena-validate-ssh-", delete=False) as fh:
            pw_path = Path(fh.name)
            fh.write(ssh_password)
            fh.flush()
            os.fchmod(fh.fileno(), 0o600)
        target_lines = "\n".join(
            f"{row['domain']}\t{row['path']}\t{row['owner']}" for row in rows
        )
        script = f'''set -euo pipefail
while IFS=$'\\t' read -r domain path owner; do
  [ -n "$domain" ] || continue
  uid=$(runuser -u "$owner" -- wp --path="$path" user get atena --field=ID --skip-plugins --skip-themes)
  email=$(runuser -u "$owner" -- wp --path="$path" user get "$uid" --field=user_email --skip-plugins --skip-themes)
  role=$(runuser -u "$owner" -- wp --path="$path" user get "$uid" --field=roles --skip-plugins --skip-themes)
  apps=$(runuser -u "$owner" -- wp --path="$path" user application-password list "$uid" --format=json --skip-plugins --skip-themes)
  facts=$(runuser -u "$owner" -- wp --path="$path" eval "\\$u=$uid; echo json_encode(['edit_posts'=>user_can(\\$u,'edit_posts'),'publish_posts'=>user_can(\\$u,'publish_posts'),'upload_files'=>user_can(\\$u,'upload_files'),'edit_others_posts'=>user_can(\\$u,'edit_others_posts')]);" 2>/dev/null)
  wf=not_active
  if runuser -u "$owner" -- wp --path="$path" plugin is-active wordfence --skip-themes >/dev/null 2>&1; then
    disabled=$(runuser -u "$owner" -- wp --path="$path" eval 'echo class_exists("wfConfig") && wfConfig::get("loginSec_disableApplicationPasswords") ? "1" : "0";' --skip-themes 2>/dev/null || printf unknown)
    wf="disabled_option_${{disabled}}"
  fi
  python3 - "$domain" "$uid" "$email" "$role" "$apps" "$facts" "$wf" <<'PY'
import json,sys
apps=json.loads(sys.argv[5]); facts=json.loads(sys.argv[6])
print(json.dumps({{'domain':sys.argv[1],'user_id':int(sys.argv[2]),'email':sys.argv[3],'role':sys.argv[4],'application_password_count':len(apps),'atena_application_password_count':sum(1 for x in apps if x.get('name')=='Atena API - MGS'),'capabilities':facts,'wordfence':sys.argv[7]}},separators=(',',':')))
PY
done <<'TARGETS'
{target_lines}
TARGETS
'''
        try:
            proc = provision.run(
                [
                    "sshpass", "-f", str(pw_path), "ssh",
                    "-o", "PreferredAuthentications=password",
                    "-o", "PubkeyAuthentication=no",
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "UserKnownHostsFile=/root/.ssh/known_hosts_mgs",
                    f"zeus@{host}", "sudo", "-n", "bash", "-s",
                ],
                input_bytes=script.encode(), timeout=300,
            )
        finally:
            pw_path.unlink(missing_ok=True)
        for line in proc.stdout.decode().splitlines():
            if line.startswith("{"):
                row = json.loads(line)
                results[row["domain"]] = row
    return results


def external_readback(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for target in targets:
        domain = target["domain"]
        admin_user, admin_password = provision.external_admin_credentials(target)
        _, users = provision.curl_json(
            f"https://{domain}/wp-json/wp/v2/users?search=atena&context=edit&per_page=100&_fields=id,slug,email,roles,name",
            admin_user,
            admin_password,
        )
        exact = [u for u in users if str(u.get("slug", "")).casefold() == "atena"]
        if len(exact) != 1:
            raise provision.ProvisionError(f"{domain}: expected one Atena user, got {len(exact)}")
        user = exact[0]
        user_id = int(user["id"])
        _, apps = provision.curl_json(
            f"https://{domain}/wp-json/wp/v2/users/{user_id}/application-passwords?context=edit",
            admin_user,
            admin_password,
        )
        results[domain] = {
            "domain": domain,
            "user_id": user_id,
            "email": user.get("email"),
            "role": (user.get("roles") or [None])[0],
            "application_password_count": len(apps),
            "atena_application_password_count": sum(
                1 for app in apps if app.get("name") == provision.APP_NAME
            ),
            "capabilities": "validated_by_editor_role_and_rest",
            "wordfence": "external_existing_admin_route",
        }
    return results


def onepassword_and_api_readback(
    targets: dict[str, dict[str, Any]], wordpress: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    listed = provision.list_items()
    relevant = [
        x for x in listed if x.get("title", "").casefold().startswith(provision.ITEM_PREFIX.casefold())
    ]
    title_counts = Counter(x.get("title", "").casefold() for x in relevant)
    expected_titles = {f"{provision.ITEM_PREFIX}{domain}".casefold() for domain in targets}
    if set(title_counts) != expected_titles or any(count != 1 for count in title_counts.values()):
        raise provision.ProvisionError("1Password Atena item title set or uniqueness mismatch")
    validated = 0
    for item in relevant:
        raw = json.loads(
            provision.op(
                ["item", "get", item["id"], "--vault", provision.VAULT, "--format", "json", "--reveal"]
            )
        )
        fields = {f.get("id"): f.get("value", "") for f in raw.get("fields", [])}
        domain = fields.get("site_domain", "")
        if domain not in targets:
            raise provision.ProvisionError("1Password item has an unexpected site_domain")
        wp = wordpress[domain]
        checks = [
            fields.get("username") == provision.USERNAME,
            bool(fields.get("password")),
            bool(fields.get("wp_app_password")),
            fields.get("wp_role") == provision.ROLE,
            str(fields.get("wp_user_id")) == str(wp["user_id"]),
            raw.get("title") == f"{provision.ITEM_PREFIX}{domain}",
        ]
        if not all(checks):
            raise provision.ProvisionError(f"{domain}: 1Password field readback mismatch")
        provision.validate_atena_api(domain, fields["wp_app_password"])
        validated += 1
    return {"listed": len(relevant), "unique_titles": len(title_counts), "api_smokes": validated}


def main() -> int:
    runcloud_targets = json.loads(provision.RUNCLOUD_MANIFEST.read_text())["targets"]
    external_targets = json.loads(provision.EXTERNAL_MANIFEST.read_text())["targets"]
    targets = {x["domain"]: x for x in runcloud_targets + external_targets}
    if len(targets) != 45:
        raise provision.ProvisionError("target manifest is not exactly 45 domains")
    state = json.loads(provision.STATE_PATH.read_text())
    if len(state.get("results", {})) != 45 or state.get("failures"):
        raise provision.ProvisionError("provision state is not complete and clean")

    wordpress = remote_runcloud_readback_v2(runcloud_targets)
    wordpress.update(external_readback(external_targets))
    if len(wordpress) != 45:
        raise provision.ProvisionError(f"WordPress readback count mismatch: {len(wordpress)}")
    for domain, row in wordpress.items():
        if (
            str(row.get("email", "")).casefold() != provision.EMAIL
            or row.get("role") != provision.ROLE
            or row.get("atena_application_password_count") != 1
        ):
            raise provision.ProvisionError(f"{domain}: WordPress identity readback mismatch")
        caps = row.get("capabilities")
        if isinstance(caps, dict) and not all(caps.values()):
            raise provision.ProvisionError(f"{domain}: missing editor capability")
        if row.get("wordfence") == "disabled_option_1":
            raise provision.ProvisionError(f"{domain}: Wordfence disables Application Passwords")

    op_summary = onepassword_and_api_readback(targets, wordpress)

    doc = Path("/root/mgs-agent/skills/content-publish-wordpress/references/atena-dedicated-wordpress-access.md")
    skill = Path("/root/mgs-agent/skills/content-publish-wordpress/SKILL.md")
    atena_live = Path("/root/.hermes/profiles/atena/skills/wordpress/content-site-vertical-operations/SKILL.md")
    atena_mirror = Path("/root/mgs-agent/profiles/atena-skills/wordpress/content-site-vertical-operations/SKILL.md")
    doc_text = doc.read_text()
    skill_text = skill.read_text()
    atena_live_text = atena_live.read_text()
    doc_checks = {
        "reference_exists": doc.is_file(),
        "skill_routes_reference": "references/atena-dedicated-wordpress-access.md" in skill_text,
        "credential_title_contract": "Atena WordPress - <domain>" in doc_text,
        "pipeline_gate_documented": "data/sites.json" in doc_text,
        "wordfence_pitfall_documented": "loginSec_disableApplicationPasswords" in doc_text,
        "atena_live_routes_canonical_reference": str(doc) in atena_live_text,
        "atena_live_mirror_equal": atena_live.read_bytes() == atena_mirror.read_bytes(),
        "no_secret_values_in_docs": all(
            marker not in (doc_text + atena_live_text)
            for marker in ["OP_SERVICE_ACCOUNT_TOKEN=", "Authorization: *** "]
        ),
    }
    if not all(doc_checks.values()):
        raise provision.ProvisionError(f"documentation validation failed: {doc_checks}")

    summary = {
        "operation": "atena-wordpress-access-20260920",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "targets": 45,
        "wordpress": {
            "validated": len(wordpress),
            "runcloud": len(runcloud_targets),
            "external": len(external_targets),
            "editor_role": sum(row.get("role") == provision.ROLE for row in wordpress.values()),
            "email_match": sum(str(row.get("email", "")).casefold() == provision.EMAIL for row in wordpress.values()),
            "named_application_password_exactly_one": sum(
                row.get("atena_application_password_count") == 1 for row in wordpress.values()
            ),
            "wordfence_disabled_option_true": sum(
                row.get("wordfence") == "disabled_option_1" for row in wordpress.values()
            ),
        },
        "onepassword": op_summary,
        "documentation": doc_checks,
        "secrets_emitted": False,
        "status": "PASS",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    os.chmod(SUMMARY_PATH, 0o600)
    print(
        "VALIDATION_PASS targets=45 wordpress=45 onepassword=45 api_smokes=45 "
        "docs=PASS wordfence_blocking=0 secrets_emitted=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
