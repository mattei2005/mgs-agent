from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class BatchTransportError(RuntimeError):
    def __init__(self, stage: str, detail: dict[str, Any]):
        self.stage = stage
        self.detail = detail
        super().__init__(f"{stage}: batch request failed")


def _form_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


@dataclass(frozen=True)
class BatchOperation:
    name: str
    method: str
    relative_url: str
    body: dict[str, Any] = field(default_factory=dict)
    depends_on: str | None = None
    kind: str = "generic"

    def graph_payload(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "method": self.method.upper(),
            "relative_url": self.relative_url.lstrip("/"),
            "name": self.name,
            "omit_response_on_success": False,
        }
        if self.body:
            row["body"] = urllib.parse.urlencode({key: _form_value(value) for key, value in self.body.items()})
        if self.depends_on:
            row["depends_on"] = self.depends_on
        return row


@dataclass(frozen=True)
class BatchResult:
    name: str
    code: int
    body: dict[str, Any]
    headers: tuple[dict[str, Any], ...] = ()


def _operational_scope_guard():
    import importlib.util
    spec = importlib.util.spec_from_file_location('ares_engine_asset_scope', '/root/mgs-agent/scripts/mgs-ares-asset-scope.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('operational_scope_unavailable')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    return guard


class GraphBatchTransport:
    def __init__(self, account_id: str, graph_version: str, token: str, app_secret: str | None = None, timeout: int = 90):
        self.account_id = str(account_id).removeprefix("act_")
        self.graph_version = graph_version
        self._token = token
        self._app_secret = app_secret
        self.timeout = timeout
        self.calls: list[dict[str, Any]] = []
        self.last_outer_headers: dict[str, Any] = {}

    def execute(self, operations: list[BatchOperation], stage: str) -> list[BatchResult]:
        if not operations:
            return []
        batch = [operation.graph_payload() for operation in operations]
        # Same fail-closed guard as the common Graph client, before any HTTP.
        guard = _operational_scope_guard()
        if guard.is_ares_context():
            guard.enforce_meta_path('act_' + self.account_id, {'fields': 'id'})
            guard.enforce_meta_path('', {'batch': batch}, 'POST')
            scope_data = guard.load_scope()
            for operation in operations:
                clean, _ = guard._request_parts(operation.relative_url, operation.body)
                node = clean.split('/')[0]
                dependency = guard._dependency_for_node(node, scope_data)
                if dependency:
                    if self.account_id not in dependency['account_ids']:
                        raise guard.ScopeError(guard.DENY)
                elif guard._account_for_node(node, scope_data) != self.account_id:
                    raise guard.ScopeError(guard.DENY)
        form: dict[str, str] = {
            "access_token": self._token,
            "batch": json.dumps(batch, ensure_ascii=False, separators=(",", ":")),
        }
        if self._app_secret:
            form["appsecret_proof"] = hmac.new(self._app_secret.encode(), self._token.encode(), hashlib.sha256).hexdigest()
        req = urllib.request.Request(
            f"https://graph.facebook.com/{self.graph_version}/",
            data=urllib.parse.urlencode(form).encode(),
            headers={"User-Agent": "mgs-ares-campaign-engine-v3/3.0", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        self.last_outer_headers = {}
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                payload = json.loads(raw)
                outer_headers = {str(k).lower(): str(v) for k, v in resp.headers.items()}
                self.last_outer_headers = outer_headers
        except urllib.error.HTTPError as exc:
            self.last_outer_headers = {str(k).lower(): str(v) for k, v in exc.headers.items()} if exc.headers else {}
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"error": {"message": "non-json batch error"}}
            raise BatchTransportError(stage, {"http": exc.code, "payload": payload}) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise BatchTransportError(stage, {"error": type(exc).__name__}) from exc
        if not isinstance(payload, list) or len(payload) != len(operations):
            raise BatchTransportError(stage, {"message": "batch response shape mismatch", "expected": len(operations)})
        results: list[BatchResult] = []
        for operation, item in zip(operations, payload):
            body_raw = item.get("body") if isinstance(item, dict) else None
            try:
                body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})
            except json.JSONDecodeError:
                body = {"error": {"message": "non-json child response"}}
            code = int(item.get("code") or 0) if isinstance(item, dict) else 0
            headers = tuple(item.get("headers") or ()) if isinstance(item, dict) else ()
            results.append(BatchResult(operation.name, code, body, headers))
        successful_ids = [{'name': row.name, 'code': row.code, 'ids': {
            key: row.body[key] for key in ('id', 'copied_campaign_id', 'copied_adset_id', 'copied_ad_id', 'ad_object_ids') if key in row.body
        }} for row in results if 200 <= row.code < 300]
        try:
            for operation, row in zip(operations, results):
                if 200 <= row.code < 300:
                    guard.observe_meta_response(operation.relative_url, operation.body, row.body, operation.method)
        except Exception as exc:
            # IDs survive even if post-HTTP provenance validation fails.
            raise BatchTransportError(stage, {'error': 'scope_observation_failed', 'error_type': type(exc).__name__,
                                             'successful_children': successful_ids}) from None
        self.calls.append({"stage": stage, "operations": len(operations), "outer_headers": outer_headers})
        failures = [result for result in results if result.code < 200 or result.code >= 300]
        if failures:
            safe = [{"name": row.name, "code": row.code, "error": row.body.get("error")} for row in failures]
            successful = []
            for row in results:
                if row.code < 200 or row.code >= 300:
                    continue
                ids = {
                    key: row.body.get(key)
                    for key in ("id", "copied_campaign_id", "copied_adset_id", "copied_ad_id", "ad_object_ids")
                    if row.body.get(key) is not None
                }
                successful.append({"name": row.name, "code": row.code, "ids": ids})
            raise BatchTransportError(stage, {"children": safe, "successful_children": successful, "outer_headers": outer_headers})
        return results


class FakeBatchTransport:
    """Deterministic transport used only by tests and offline benchmark."""

    def __init__(self, account_id: str):
        self.account_id = str(account_id)
        self.calls: list[dict[str, Any]] = []
        self.last_outer_headers: dict[str, Any] = {}
        self._sequence = 0

    def _id(self, kind: str) -> str:
        self._sequence += 1
        return f"{self.account_id}-{kind}-{self._sequence}"

    def execute(self, operations: list[BatchOperation], stage: str) -> list[BatchResult]:
        self.calls.append({"stage": stage, "operations": len(operations)})
        rows: list[BatchResult] = []
        for op in operations:
            if op.kind in {"campaign_copy", "pure_clone"}:
                body = {"copied_campaign_id": self._id("campaign")}
            elif op.kind == "campaign_create":
                body = {"id": self._id("campaign")}
            elif op.kind == "adset_copy":
                body = {"copied_adset_id": self._id("adset")}
            elif op.kind == "adset_create":
                body = {"id": self._id("adset")}
            elif op.kind in {"ad_copy_with_creative", "existing_post_ad_copy"}:
                body = {"copied_ad_id": self._id("ad")}
            elif op.kind == "ad_name_update":
                body = {"success": True}
            elif op.kind == "creative_create":
                body = {"id": self._id("creative")}
            elif op.kind == "ad_create":
                body = {"id": self._id("ad")}
            elif op.kind == "campaign_update":
                body = {"success": True}
            elif op.kind == "adset_update":
                body = {"success": True}
            elif op.kind == "readback":
                path = op.relative_url.split("?", 1)[0]
                if path.endswith("/adsets") or path.endswith("/ads"):
                    body = {"data": [{"id": self._id("readback"), "status": "PAUSED", "effective_status": "PAUSED"}]}
                else:
                    body = {"id": path, "status": "PAUSED", "effective_status": "PAUSED"}
            else:
                body = {"success": True}
            rows.append(BatchResult(op.name, 200, body))
        return rows
