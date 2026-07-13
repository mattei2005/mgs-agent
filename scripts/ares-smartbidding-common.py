#!/usr/bin/env python3
"""Read-only Smart Bidding helpers for Ares HOA reports.

Credentials are resolved internally from 1Password. Access tokens are cached in a
0600 file and are never printed or persisted in operational reports.
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import secrets
import shlex
import subprocess
import tempfile
import time
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

import requests

AUTH0_DOMAIN = "jbfdigital.us.auth0.com"
AUTH0_CLIENT_ID = "ATDoMPuhKZUDX9UvbJ80OvcIcsbzAbPN"
API_AUDIENCE = "https://api.jbfdigital.com.br"
API_BASE = "https://api.jbfdigital.com.br"
REDIRECT_URI = "https://app.smartbiddingdigital.com"
TOKEN_ITEM_DEFAULT = "Ares - Smartbidding Dashboard"
TOKEN_CACHE_PATH = Path(os.environ.get("ARES_SB_TOKEN_CACHE_PATH", "/root/.cache/mgs/ares-smartbidding-token.json"))
TOKEN_CACHE_LOCK_PATH = Path(os.environ.get("ARES_SB_TOKEN_CACHE_LOCK_PATH", f"{TOKEN_CACHE_PATH}.lock"))
TOKEN_EXPIRY_MARGIN_SECONDS = int(os.environ.get("ARES_SB_TOKEN_EXPIRY_MARGIN_SECONDS", "300"))
HTTP_TIMEOUT_SECONDS = int(os.environ.get("ARES_SB_HTTP_TIMEOUT_SECONDS", "30"))
USER_AGENT = "mgs-ares-smartbidding-readonly/1.0"


class LoginFormsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict] = []
        self.current: dict | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        data = dict(attrs)
        if tag == "form":
            self.current = {"action": data.get("action", ""), "inputs": {}}
        elif self.current is not None and tag == "input" and data.get("name"):
            self.current["inputs"][data["name"]] = data.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None


def _shell_quote(value: str) -> str:
    return shlex.quote(str(value))


def _fetch_credentials(item_name: str) -> tuple[str, str]:
    vault = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
    command = (
        "set -a; [ -f /root/mgs-agent/.env ] && . /root/mgs-agent/.env; set +a; "
        f"op item get {_shell_quote(item_name)} --vault {_shell_quote(vault)} --format json --reveal"
    )
    result = subprocess.run(
        ["bash", "-lc", command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Smart Bidding credential item is not readable from 1Password")
    data = json.loads(result.stdout)
    fields = {
        str(field.get("label") or field.get("id") or "").lower(): str(field.get("value") or "")
        for field in data.get("fields", [])
    }
    username = fields.get("username") or fields.get("email") or ""
    password = fields.get("password") or ""
    if not username or not password:
        raise RuntimeError("Smart Bidding credential fields are incomplete")
    return username, password


def _open_cache_lock():
    TOKEN_CACHE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(TOKEN_CACHE_LOCK_PATH.parent, 0o700)
    fd = os.open(TOKEN_CACHE_LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, "r+")


def _read_token_cache(item_name: str) -> tuple[str, int] | None:
    try:
        stat = TOKEN_CACHE_PATH.stat()
        if stat.st_mode & 0o077:
            return None
        data = json.loads(TOKEN_CACHE_PATH.read_text())
        token = str(data.get("access_token") or "")
        expires_at = int(data.get("expires_at") or 0)
        if data.get("item") != item_name or not token:
            return None
        if expires_at <= int(time.time()) + TOKEN_EXPIRY_MARGIN_SECONDS:
            return None
        return token, expires_at
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _write_token_cache(item_name: str, token: str, expires_in: int) -> int:
    expires_at = int(time.time()) + int(expires_in)
    TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(TOKEN_CACHE_PATH.parent, 0o700)
    payload = json.dumps(
        {"item": item_name, "access_token": token, "expires_at": expires_at, "cached_at": int(time.time())},
        ensure_ascii=False,
    )
    fd, temporary_name = tempfile.mkstemp(prefix=".ares-sb-token-", dir=TOKEN_CACHE_PATH.parent)
    temporary = Path(temporary_name)
    os.fchmod(fd, 0o600)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(payload + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, TOKEN_CACHE_PATH)
        os.chmod(TOKEN_CACHE_PATH, 0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return expires_at


def invalidate_token_cache(item_name: str = TOKEN_ITEM_DEFAULT, rejected_token: str | None = None) -> bool:
    with _open_cache_lock() as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            data = json.loads(TOKEN_CACHE_PATH.read_text())
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False
        if data.get("item") != item_name:
            return False
        if rejected_token is not None and data.get("access_token") != rejected_token:
            return False
        try:
            TOKEN_CACHE_PATH.unlink()
            return True
        except FileNotFoundError:
            return False


def _oauth_login(item_name: str) -> tuple[str, int]:
    username, password = _fetch_credentials(item_name)
    verifier = secrets.token_urlsafe(48).rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    params = {
        "client_id": AUTH0_CLIENT_ID,
        "scope": "openid profile email offline_access",
        "redirect_uri": REDIRECT_URI,
        "audience": API_AUDIENCE,
        "response_type": "code",
        "response_mode": "query",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    login_page = session.get(f"https://{AUTH0_DOMAIN}/authorize", params=params, timeout=HTTP_TIMEOUT_SECONDS)
    login_page.raise_for_status()
    parser = LoginFormsParser()
    parser.feed(login_page.text)
    form = next(
        (entry for entry in parser.forms if "username" in entry["inputs"] and "password" in entry["inputs"]),
        None,
    )
    if not form:
        raise RuntimeError("Smart Bidding Auth0 username/password form was not found")
    action = urllib.parse.urljoin(login_page.url, form["action"] or login_page.url)
    payload = {key: value for key, value in form["inputs"].items() if key not in {"username", "password"}}
    payload.update({"username": username, "password": password, "action": "default"})
    callback = session.post(
        action,
        data=payload,
        headers={"Referer": login_page.url, "Origin": f"https://{AUTH0_DOMAIN}"},
        allow_redirects=True,
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    callback.raise_for_status()
    query = urllib.parse.parse_qs(urllib.parse.urlparse(callback.url).query)
    code = (query.get("code") or [""])[0]
    returned_state = (query.get("state") or [""])[0]
    if not code or returned_state != state:
        raise RuntimeError("Smart Bidding Auth0 callback did not return a valid authorization code")
    exchange = session.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": AUTH0_CLIENT_ID,
            "code_verifier": verifier,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    exchange.raise_for_status()
    body = exchange.json()
    token = str(body.get("access_token") or "")
    expires_in = int(body.get("expires_in") or 0)
    if not token or expires_in <= TOKEN_EXPIRY_MARGIN_SECONDS:
        raise RuntimeError("Smart Bidding Auth0 token response was incomplete")
    return token, expires_in


def get_access_token(item_name: str = TOKEN_ITEM_DEFAULT, force_refresh: bool = False) -> tuple[str, str]:
    if not force_refresh:
        cached = _read_token_cache(item_name)
        if cached:
            token, expires_at = cached
            return token, f"cache_expires_at={expires_at}"
    with _open_cache_lock() as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not force_refresh:
            cached = _read_token_cache(item_name)
            if cached:
                token, expires_at = cached
                return token, f"cache_expires_at={expires_at}"
        token, expires_in = _oauth_login(item_name)
        expires_at = _write_token_cache(item_name, token, expires_in)
        return token, f"auth0_expires_at={expires_at}"


def api_request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    item_name: str = TOKEN_ITEM_DEFAULT,
) -> tuple[int, object, dict]:
    token, token_source = get_access_token(item_name)
    for attempt in range(2):
        response = requests.request(
            method,
            f"{API_BASE}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        try:
            body: object = response.json()
        except ValueError:
            body = {"raw_length": len(response.content)}
        if response.status_code not in {401, 403} or attempt == 1:
            return response.status_code, body, {
                "credential_item": item_name,
                "token_len": len(token),
                "token_source": token_source,
            }
        invalidate_token_cache(item_name, rejected_token=token)
        token, token_source = get_access_token(item_name, force_refresh=True)
    raise RuntimeError("Smart Bidding API retry loop exhausted")


def compute_roi_pct(revenue: float | int | None, spend: float | int | None) -> float | None:
    spend_value = float(spend or 0)
    if spend_value <= 0:
        return None
    return (float(revenue or 0) - spend_value) * 100.0 / spend_value


def _sum_field(rows: list[dict], key: str) -> float:
    total = 0.0
    for row in rows:
        try:
            total += float(row.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return total


def fetch_page_revenue(
    *,
    report_date: str,
    pg_id: str,
    config: dict,
) -> dict:
    item_name = str(config.get("credential_item") or TOKEN_ITEM_DEFAULT)
    publisher_name = str(config.get("publisher_name") or "").strip().lower()
    status, companies, token_report = api_request("GET", "/company", item_name=item_name)
    if status != 200 or not isinstance(companies, list):
        raise RuntimeError(f"Smart Bidding /company failed with HTTP {status}")
    publishers: list[str] = []
    for company in companies:
        for publisher in company.get("publishers") or []:
            name = str(publisher.get("name") or "").strip().lower()
            if name != publisher_name:
                continue
            publisher_id = str(publisher.get("publisherId") or "")
            if publisher_id and "_" not in publisher_id:
                publisher_id = f"{company.get('companyId')}_{publisher_id}"
            if publisher_id:
                publishers.append(publisher_id)
    publishers = sorted(set(publishers))
    if not publishers:
        raise RuntimeError("Smart Bidding publisher configured for HOA was not found")
    payload = {
        "initialDate": f"{report_date}T00:00:00.000Z",
        "finalDate": f"{report_date}T23:59:59.999Z",
        "publishers": publishers,
        "currency": str(config.get("currency") or "USD"),
    }
    report_status, report_rows, token_report = api_request(
        "POST",
        str(config.get("revenue_endpoint") or "/report/messenger"),
        payload=payload,
        item_name=item_name,
    )
    if report_status not in {200, 201} or not isinstance(report_rows, list):
        raise RuntimeError(f"Smart Bidding messenger report failed with HTTP {report_status}")
    domain = str(config.get("domain") or "").lower()
    country = str(config.get("country") or "").lower()
    vertical = str(config.get("vertical") or "").lower()
    account_name = str(config.get("account_name") or "")
    matched = []
    for row in report_rows:
        if not isinstance(row, dict):
            continue
        if domain and str(row.get("DOMAIN") or "").lower() != domain:
            continue
        if country and str(row.get("COUNTRY") or "").lower() != country:
            continue
        if vertical and str(row.get("VERTICAL") or "").lower() != vertical:
            continue
        if account_name and str(row.get("ACCOUNT_NAME") or "") != account_name:
            continue
        if str(row.get("UTM_CAMPAIGN") or "").lower() != str(pg_id).lower():
            continue
        matched.append(row)
    drip_revenue = _sum_field(matched, "DRIP_REVENUE")
    broadcast_revenue = _sum_field(matched, "BD_REVENUE")
    total_revenue = _sum_field(matched, "REVENUE")
    return {
        "status": "ok" if matched else "no_matching_revenue_row",
        "report_date": report_date,
        "pg_id": pg_id,
        "currency": payload["currency"],
        "matched_rows": len(matched),
        "drip_revenue": round(drip_revenue, 4),
        "broadcast_revenue": round(broadcast_revenue, 4),
        "total_revenue": round(total_revenue, 4),
        "revenue_residual": round(total_revenue - drip_revenue - broadcast_revenue, 4),
        "source": "smart_bidding_report_messenger",
        "token_report": token_report,
    }
