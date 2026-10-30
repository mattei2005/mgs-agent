#!/usr/bin/env python3
"""Read-only, domain-gated WordPress capability preflight for ContentOps.
No credentials in argv/output; no remote mutation and no identity/ACL changes.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit

ROOT = Path('/root/mgs-agent')
OP = str(ROOT / 'scripts/mgs-op-with-service-account.sh')
VAULT = 'MGS Conteúdo'

class PreflightError(Exception):
    pass

def op_json(*args):
    r = subprocess.run([OP, *args, '--format', 'json'], capture_output=True, text=True, timeout=90)
    if r.returncode:
        raise PreflightError('canonical_1password_read_failed')
    return json.loads(r.stdout)

def gate(domain):
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', domain) or '.' not in domain:
        raise PreflightError('literal_domain_required')
    r = subprocess.run(['python3', str(ROOT / 'scripts/mgs-domain-scope.py'), 'check', '--agent', 'atena', domain, '--json'], capture_output=True, text=True, timeout=30)
    try:
        data = json.loads(r.stdout)
    except ValueError:
        raise PreflightError('domain_gate_unverified') from None
    if r.returncode != 0 or data.get('allowed') is not True:
        raise PreflightError('domain_not_authorized')

def resolve(domain):
    items = op_json('item', 'list', '--vault', VAULT)
    matches = [x for x in items if x.get('title', '').casefold() == ('Wordpress - ' + domain).casefold()]
    if len(matches) != 1:
        raise PreflightError('canonical_login_missing_or_ambiguous')
    item = op_json('item', 'get', matches[0]['id'], '--vault', VAULT)
    fields = {x.get('label'): x.get('value') for x in item.get('fields', [])}
    pairs = [('api_auth_user', 'api_application_password'), ('username', 'wp_app_password'), ('app user', 'app password')]
    credentials = next(((fields.get(a), fields.get(b)) for a, b in pairs if fields.get(a) and fields.get(b)), None)
    if credentials is None:
        raise PreflightError('canonical_rest_fields_missing')
    user, password = credentials
    if not isinstance(user, str) or not isinstance(password, str):
        raise PreflightError('canonical_rest_fields_invalid_type')
    if any(x in user + password for x in ('\n', '\r', '"', '\\')):
        raise PreflightError('unsupported_auth_transport_characters')
    base = (fields.get('api_base') or ('https://' + domain + '/wp-json/wp/v2')).rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or parsed.netloc != domain or parsed.query or parsed.fragment:
        raise PreflightError('canonical_api_origin_mismatch')
    if parsed.path.rstrip('/') == '/wp-json':
        base += '/wp/v2'
    elif parsed.path.rstrip('/') != '/wp-json/wp/v2':
        raise PreflightError('canonical_api_path_unrecognized')
    return user, password, base

def get_json(user, password, url):
    scratch = os.environ.get('TMPDIR')
    if not scratch or not Path(scratch).is_dir():
        raise PreflightError('profile_scratch_directory_required')
    script = '''set -euo pipefail
source /root/mgs-agent/skills/content-publish-wordpress/scripts/wp-curl-auth.sh
wp_curl_auth() {
 local user="$1" pass="$2"; shift 2
 builtin printf 'user = "%s:%s"\\n' "$user" "$pass" | curl -K - "$@"
}
IFS= read -r user
IFS= read -r pass
IFS= read -r url
wp_curl_auth_http "$1" "$user" "$pass" -X GET "$url"
'''
    with tempfile.TemporaryDirectory(prefix='contentops-preflight-', dir=scratch) as td:
        body = Path(td) / 'body.json'
        r = subprocess.run(['bash', '-c', script, 'contentops-readonly', str(body)], input=user + '\n' + password + '\n' + url + '\n', capture_output=True, text=True, timeout=120, env={**os.environ, 'WP_CURL_MAX_TIME': '45', 'WP_CURL_RETRY': '1'})
        if not re.fullmatch(r'\d{3}', r.stdout.strip()):
            raise PreflightError('http_transport_status_unverified')
        status = int(r.stdout.strip())
        try:
            data = json.loads(body.read_text())
        except (OSError, ValueError):
            raise PreflightError('http_response_not_json') from None
    return status, data

def run(domain):
    gate(domain)  # Must precede 1Password enumeration or any remote site request.
    user, password, base = resolve(domain)
    status, identity = get_json(user, password, base + '/users/me?context=edit&_fields=id,roles,capabilities')
    if status != 200:
        return {'status': 'blocked', 'domain': domain, 'identity_http': status, 'reason': 'native_rest_identity_rejected', 'remote_mutations': 0}
    caps = identity.get('capabilities', {})
    result = {'status': 'verified', 'domain': domain, 'identity_http': status, 'roles': identity.get('roles', []), 'capabilities': {k: bool(caps.get(k)) for k in ('edit_posts', 'publish_posts', 'manage_options', 'install_plugins', 'activate_plugins', 'delete_plugins')}, 'rest_route_composition_verified': True, 'remote_mutations': 0, 'credentials_changed': False, 'permissions_changed': False}
    if caps.get('activate_plugins'):
        code, plugins = get_json(user, password, base + '/plugins?context=edit')
        result['plugins_http'] = code
        if code == 200 and isinstance(plugins, list):
            result['maintenance_plugins'] = [{'plugin': p.get('plugin'), 'status': p.get('status'), 'version': p.get('version')} for p in plugins if p.get('plugin', '').startswith(('wordpress-seo/', 'wp-file-manager/', 'mgs-home-indexable-maintenance-'))]
        else:
            result['status'] = 'partial'
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain', required=True, help='Exact allowlisted domain; no URL, inferred alias or wildcard')
    args = parser.parse_args()
    try:
        result = run(args.domain)
    except PreflightError as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc), 'remote_mutations': 0, 'secrets_emitted': False}))
        return 2
    except Exception as exc:
        print(json.dumps({'status': 'error', 'error_class': type(exc).__name__, 'remote_mutations': 0, 'secrets_emitted': False}))
        return 3
    result['secrets_emitted'] = False
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'verified' else 2

if __name__ == '__main__':
    raise SystemExit(main())
