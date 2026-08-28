from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from .adapters import CPV_ACCOUNT_ID, CPV_PAGE_ID, build_cpv_manifest
from .cli import real_transport_factory
from .coordination import AccountWriterLeaseStore
from .engine import CampaignEngine
from .media_registry import MediaRegistry
from .prestage import AdAccountVideoUploader
from .prevalidation import prevalidate_payload
from .schema import Manifest
from .source_selection import (
    SourceSelectionError,
    aggregate_smart_bidding_roi,
    asset_group_vehicle_types,
    authorized_request_vehicle_type,
    canonical_vehicle_type,
    expand_source_selections,
    select_canonical_source_ads,
    select_best_roi_campaign,
    vehicle_type_from_text,
)
from .transport import BatchTransportError, FakeBatchTransport

BASE = Path("/root/mgs-agent")
PROFILE = Path("/root/.hermes/profiles/ares")
SP = ZoneInfo("America/Sao_Paulo")
GRAPH_VERSION = "v26.0"
ACCOUNT_ID = CPV_ACCOUNT_ID
ACCOUNT_ACT = f"act_{ACCOUNT_ID}"
ACCOUNT_ALIAS = "Creditoparaveiculo-BR-CAR-BR-13-G006"
PAGE_ID = CPV_PAGE_ID
DRIVE_ID = "0AEwt4Ye690ocUk9PVA"
FOLDER_MIME = "application/vnd.google-apps.folder"
TOKEN_ITEM = "Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006"
SB_TOKEN_ITEM = "Ares - Smartbidding Dashboard"
SB_PUBLISHER = "digital-trust_creditoparaveiculo"
SB_DOMAIN = "creditoparaveiculo"
THREAD_CREATION = "1539826050765299872"
COMMON_PATH = BASE / "scripts/ares-meta-common.py"
SB_COMMON_PATH = BASE / "scripts/ares-smartbidding-common.py"
DRIVE_MODULE_PATH = BASE / "scripts/ares-drive-upload-manual-inventory.py"
SANITIZER = BASE / "scripts/clean-creative-metadata.sh"
CONFIG_PATH = BASE / "data/ares/meta-ads/engine-v3/config.json"
OPERATION_PATH = BASE / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json"
REGISTRY_PATH = BASE / "data/ares/meta-ads/engine-v3/media-registry.json"
INVENTORY_PATH = BASE / "data/ares/creative-ops/inventory/assets.jsonl"
RECONCILIATION_PATH = BASE / "data/ares/meta-ads/reconciliation/Creditoparaveiculo-BR-CAR-BR.json"
STATE_PATH = BASE / "data/ares/meta-ads/engine-v3/state/cpv-daily.json"
LOCK_PATH = BASE / "data/ares/meta-ads/engine-v3/state/cpv-daily.lock"
AUDIT_ROOT = BASE / "data/ares/meta-ads/engine-v3/audit/daily"
WORK_ROOT = PROFILE / "work/creditoparaveiculo-v3-daily"
FIRST_DELIVERY_GUARDRAIL_SCRIPT = PROFILE / "scripts/creditoparaveiculo-first-delivery-guardrail.py"
PHASE_ORDER = ["meta_preflight", "drive_preflight", "reconciliation", "asset_selection", "source_selection", "prestage", "manifest_prevalidation", "engine", "postprocess"]
_CALL_COUNTER: ContextVar[dict[str, int] | None] = ContextVar("cpv_v3_daily_call_counter", default=None)


class DailyBlocked(RuntimeError):
    def __init__(self, stage: str, message: str, detail: dict[str, Any] | None = None):
        self.stage = stage
        self.detail = detail or {}
        super().__init__(message)


@dataclass(frozen=True)
class DailyPaths:
    config: Path = CONFIG_PATH
    operation: Path = OPERATION_PATH
    registry: Path = REGISTRY_PATH
    inventory: Path = INVENTORY_PATH
    reconciliation: Path = RECONCILIATION_PATH
    state: Path = STATE_PATH
    lock: Path = LOCK_PATH
    audit_root: Path = AUDIT_ROOT
    work_root: Path = WORK_ROOT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def count_call(kind: str, amount: int = 1) -> None:
    counter = _CALL_COUNTER.get()
    if counter is not None:
        counter[kind] = int(counter.get(kind) or 0) + int(amount)


def phase_begin(counter: dict[str, int]) -> tuple[float, dict[str, int]]:
    return time.perf_counter(), dict(counter)


def phase_end(audit: dict[str, Any], name: str, started: float, before: dict[str, int], counter: dict[str, int], *, detail: dict[str, Any] | None = None) -> None:
    calls = {key: int(counter.get(key) or 0) - int(before.get(key) or 0) for key in sorted(set(counter) | set(before))}
    calls = {key: value for key, value in calls.items() if value}
    row: dict[str, Any] = {"duration_ms": round((time.perf_counter() - started) * 1000, 3), "calls": calls, "skipped": False}
    if detail:
        row["detail"] = detail
    audit.setdefault("observability", {}).setdefault("phases", {})[name] = row


def init_observability(audit: dict[str, Any]) -> None:
    audit["observability"] = {
        "phase_order": list(PHASE_ORDER),
        "phases": {name: {"duration_ms": 0.0, "calls": {}, "skipped": True} for name in PHASE_ORDER},
        "total": {"duration_ms": 0.0, "calls": {}},
    }


def atomic_json(path: Path, payload: dict[str, Any], *, sort_keys: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=sort_keys)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_inventory(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DailyBlocked("json", f"expected JSON object: {path}")
    return payload


def safe_error(exc: Exception) -> dict[str, Any]:
    result: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)[:500]}
    if isinstance(exc, DailyBlocked):
        result.update(stage=exc.stage, detail=exc.detail)
        return result
    stage = getattr(exc, "stage", None)
    detail = getattr(exc, "detail", None)
    if isinstance(stage, str) and stage:
        result["stage"] = stage[:120]
    if isinstance(detail, dict):
        safe_detail: dict[str, Any] = {}
        if isinstance(detail.get("http"), int):
            safe_detail["http"] = detail["http"]
        if isinstance(detail.get("message"), str):
            safe_detail["message"] = detail["message"][:300]
        if isinstance(detail.get("error"), str):
            safe_detail["error"] = detail["error"][:120]
        if isinstance(detail.get("recommended_retry_after_seconds"), int):
            safe_detail["recommended_retry_after_seconds"] = max(1, detail["recommended_retry_after_seconds"])
        payload_error = (detail.get("payload") or {}).get("error") if isinstance(detail.get("payload"), dict) else None
        if isinstance(payload_error, dict):
            safe_detail["error_response"] = {
                key: payload_error.get(key)
                for key in ("message", "type", "code", "error_subcode", "error_user_title", "error_user_msg")
                if payload_error.get(key) is not None
            }
        children = []
        for child in detail.get("children") or []:
            if not isinstance(child, dict):
                continue
            raw_error = child.get("error")
            error: dict[str, Any] = raw_error if isinstance(raw_error, dict) else {}
            children.append({
                "name": str(child.get("name") or "")[:120],
                "code": child.get("code"),
                "error": {
                    key: error.get(key)
                    for key in ("message", "type", "code", "error_subcode", "error_user_title", "error_user_msg")
                    if error.get(key) is not None
                },
            })
        if children:
            safe_detail["children"] = children[:20]
        if safe_detail:
            result["detail"] = safe_detail
    return result


RESUME_STATUSES = {
    "ASSETS_RESERVED",
    "MEDIA_READY",
    "MANIFEST_SEALED",
    "PARTIAL_DEFERRED_QUOTA",
    "POSTPROCESS_PENDING",
    "READBACK_DEFERRED",
    "RECOVERY_PENDING",
}


def is_resume_state(state: dict[str, Any], operational_date: str) -> bool:
    return (
        str(state.get("operational_date_sp") or "") == operational_date
        and str(state.get("status") or "") in RESUME_STATUSES
    )


def request_operational_date(now_sp: datetime, state: dict[str, Any]) -> date:
    """Keep the original delivery contract when recovery crosses midnight."""
    raw = str(state.get("operational_date_sp") or "")
    if raw and str(state.get("status") or "") in RESUME_STATUSES:
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise DailyBlocked("state", "resumable operational date is invalid", {"operational_date_sp": raw}) from exc
    return now_sp.date()


def gate_due(now_sp: datetime, state: dict[str, Any]) -> bool:
    day = request_operational_date(now_sp, state).isoformat()
    if is_resume_state(state, day):
        retry_after = int(state.get("retry_after_epoch") or 0)
        return retry_after <= int(now_sp.timestamp())
    return now_sp.hour == 17


def rollover_completed_state(state: dict[str, Any], operational_date: str) -> dict[str, Any]:
    """Do not reuse a completed request as the next day's resumable state."""
    completed_day = str(state.get("completed_operational_date_sp") or "")
    if completed_day and completed_day != operational_date:
        return {}
    return state


def finalize_completed_state(state: dict[str, Any], **values: Any) -> dict[str, Any]:
    """Close a resumable request without stale recovery markers."""
    completed = dict(state)
    for key in ("failure", "retry_after_epoch", "operator_authorization"):
        completed.pop(key, None)
    completed.update(values)
    completed["manual_reconciliation_required"] = False
    completed["automatic_recovery_required"] = False
    return completed


def discord_failure_message(
    failure: dict[str, Any],
    failure_status: str,
    operational_date: date,
    campaign_numbers: list[int] | None = None,
) -> str:
    """Render a useful, credential-safe failure explanation for operators."""
    stage = str(failure.get("stage") or failure.get("type") or "desconhecida")
    message = str(failure.get("message") or "")
    failure_type = str(failure.get("type") or "")

    if message == "reconciliation manifest expired":
        cause = "A validação Drive × Meta usada na retomada venceu antes deste ciclo."
        correction = "Atualizar a conciliação, reselecionar somente criativos elegíveis e retomar sem repetir writes já confirmados."
    elif message == "one or more selected assets are not reconciled":
        cause = "Um ou mais criativos selecionados não passaram na conciliação Drive × Meta."
        correction = "Remover os candidatos em conflito, atualizar a conciliação e completar o lote apenas com linhagens elegíveis."
    elif failure_type == "BatchTransportError":
        raw_detail = failure.get("detail")
        detail: dict[str, Any] = raw_detail if isinstance(raw_detail, dict) else {}
        raw_children = detail.get("children")
        children: list[Any] = raw_children if isinstance(raw_children, list) else []
        first_error = (children[0].get("error") or {}) if children and isinstance(children[0], dict) else {}
        code = first_error.get("code")
        subcode = first_error.get("error_subcode")
        reason = first_error.get("error_user_title") or first_error.get("error_user_msg") or first_error.get("message")
        code_label = "/".join(str(value) for value in (code, subcode) if value is not None)
        if reason:
            compact_reason = " ".join(str(reason).split())[:260]
            suffix = f" (código {code_label})" if code_label else ""
            cause = f"A Meta rejeitou uma operação do lote{suffix}: {compact_reason}"
        elif stage == "consolidated_readback":
            cause = "Os writes terminaram, mas a Meta não confirmou todos os GETs do readback consolidado."
        else:
            cause = "A Meta não devolveu confirmação confiável do lote."
        correction = "Fazer readback dos objetos esperados antes de qualquer nova tentativa; nunca repetir o POST às cegas."
    elif stage == "budget_cap":
        cause = "O plano ultrapassou o teto operacional ou não havia espaço suficiente no orçamento ativo."
        correction = "Recalcular o budget ativo por API e reduzir o lote; aumentar o teto exige nova autorização."
    elif stage in {"readback", "completion"}:
        cause = "A plataforma não confirmou integralmente a estrutura esperada no readback final."
        correction = "Reconciliar campanha, conjunto e anúncios pelos IDs já persistidos antes de retomar."
    elif stage == "first_delivery_guardrail":
        cause = "O pós-processamento não confirmou o cadastro das campanhas no guardrail de primeiro gasto."
        correction = "Validar o estado do watcher e rearmar somente os IDs já confirmados, sem novo write de campanha."
    elif stage == "creation_hold":
        cause = "A criação de novas campanhas está pausada para observar a coorte mais recente durante D1, D2 e D3."
        correction = "Manter análise, pausa e escala normais; criar nova coorte somente quando a leitura do ciclo justificar e Rodolfo ou Nicolas liberar."
    else:
        cause = "O executor encontrou uma falha técnica não classificada; o detalhe seguro ficou registrado no audit."
        correction = "Revisar o audit, confirmar o estado real por readback e corrigir a causa antes de retomar."

    if failure_status == "FAILED":
        consequence = "O ciclo parou antes de confirmar novos writes."
    elif failure_status == "READBACK_DEFERRED":
        consequence = "Pode haver alteração na Meta; o estado foi preservado e nenhum write será repetido."
    else:
        consequence = "Os objetos já identificados foram preservados; falta concluir a reconciliação ou o pós-processamento."

    campaign_label = ", ".join(f"C{int(number):02d}" for number in campaign_numbers or []) or "ciclo diário programado"

    return (
        f"⚠️ V3 EM RECUPERAÇÃO — CPV G006 — {operational_date:%d/%m}\n"
        f"Objeto: {campaign_label} · criação CBO programada\n"
        f"Etapa: {stage}\n"
        f"Causa: {cause}\n"
        f"Consequência: {consequence}\n"
        f"Correção: {correction}\n"
        "Ação automática: Ares reconcilia o estado real e retoma somente a camada faltante do mesmo request até concluir, sem replay cego e sem ampliar o escopo autorizado."
    )


def account_budget_summary(budget: dict[str, Any]) -> dict[str, Any]:
    active_minor = int(budget.get("projected_minor") or 0)
    cap_minor = int(budget.get("cap_minor") or 0)
    if active_minor < 0 or cap_minor <= 0 or active_minor > cap_minor:
        raise DailyBlocked("budget_cap", "post-creation budget summary is invalid", {"active_minor": active_minor, "cap_minor": cap_minor})
    return {
        "active_minor": active_minor,
        "remaining_minor": cap_minor - active_minor,
        "cap_minor": cap_minor,
        "currency": "USD",
        "source": "live Meta preflight plus validated campaign budgets from this request",
    }


def usd_minor_label(value: int) -> str:
    amount = Decimal(int(value)) / Decimal(100)
    text = f"{amount:.2f}"
    return text.rstrip("0").rstrip(".")


def media_title(kind: str, asset_id: str, checksum: str) -> str:
    normalized_kind = str(kind or "").upper()
    if normalized_kind not in {"VERTICAL", "SQUARE"}:
        raise ValueError("media title kind must be VERTICAL or SQUARE")
    short = re.sub(r"[^a-fA-F0-9]", "", str(checksum or ""))[:12].lower()
    if len(short) < 8:
        raise ValueError("media title checksum is too short")
    return f"V3 {normalized_kind} {asset_id} {short}"


def campaign_name_collisions(manifest: Manifest, live_campaigns: list[dict[str, Any]], mapped_campaign_ids: set[str]) -> list[dict[str, str]]:
    expected_names = {campaign.name for campaign in manifest.campaigns}
    collisions = []
    for row in live_campaigns:
        status = str(row.get("effective_status") or row.get("status") or "").upper()
        name = str(row.get("name") or "")
        campaign_id = str(row.get("id") or "")
        if status in {"ARCHIVED", "DELETED"} or name not in expected_names or campaign_id in mapped_campaign_ids:
            continue
        collisions.append({"campaign_id": campaign_id, "name": name, "status": status})
    return collisions


def recovery_checkpoint_campaign_ids(config: dict[str, Any], request_id: str) -> list[str]:
    """Return persisted campaign IDs that are safe to map during recovery."""
    checkpoint_dir = Path(str(config.get("state_root") or "")) / "checkpoints"
    if not checkpoint_dir.is_dir():
        return []
    safe_request = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(request_id)).strip("-")[:120] or "request"
    campaign_ids: set[str] = set()
    for checkpoint in checkpoint_dir.glob(f"{safe_request}-*.json"):
        payload = load_json(checkpoint)
        for bundle in payload.get("bundles") or []:
            for campaign_id in bundle.get("campaign_ids") or []:
                if str(campaign_id).isdigit():
                    campaign_ids.add(str(campaign_id))
    return sorted(campaign_ids)


def failure_resume_state(side_effects: dict[str, Any], *, known_campaign_ids: bool) -> tuple[str, bool]:
    if side_effects.get("drive_move"):
        return "POSTPROCESS_PENDING", False
    if side_effects.get("campaign_write"):
        return "READBACK_DEFERRED", not known_campaign_ids
    if side_effects.get("media_upload"):
        return "READBACK_DEFERRED", False
    return "RECOVERY_PENDING", False


def corrective_write_authorization() -> dict[str, Any]:
    return {
        "required": False,
        "standing_authority": "Rodolfo Mattei",
        "scope": "diagnose, reconcile and correct the same authorized request until completion",
        "guards": ["readback_before_write", "missing_layer_only", "no_blind_replay", "no_scope_expansion"],
    }


def requested_campaign_count(operation: dict[str, Any], operational_date: date) -> int:
    routine = operation.get("daily_new_campaign_routine") or {}
    raw_hold = routine.get("creation_hold")
    hold: dict[str, Any] = raw_hold if isinstance(raw_hold, dict) else {}
    if str(routine.get("status") or "").startswith("paused") or hold.get("enabled") is True:
        raise DailyBlocked(
            "creation_hold",
            "scheduled campaign creation is paused for lifecycle observation",
            {
                "operational_date_sp": operational_date.isoformat(),
                "observe_campaigns": list(hold.get("observe_campaigns") or []),
                "resume_authority": list(hold.get("resume_authority") or []),
            },
        )
    override = routine.get(f"one_time_override_{operational_date:%Y%m%d}") or {}
    if override and str(override.get("status") or "").startswith("authorized"):
        count = int(override.get("campaign_count") or 0)
    else:
        pool = Decimal(str(routine.get("new_campaign_budget_pool_usd") or 0))
        initial = Decimal(str(routine.get("default_campaign_initial_budget_usd") or 0))
        if pool <= 0 or initial <= 0:
            raise DailyBlocked("campaign_count", "daily pool or initial budget is invalid")
        count = int((pool / initial).to_integral_value(rounding=ROUND_FLOOR))
    if not 1 <= count <= 100:
        raise DailyBlocked("campaign_count", "campaign count is outside 1..100", {"count": count})
    return count


def parse_campaign_number(name: str | None) -> int | None:
    match = re.search(r"\bb01fb13c(\d{1,3})\b", str(name or ""), re.I)
    return int(match.group(1)) if match else None


def next_campaign_numbers(campaigns: list[dict[str, Any]], count: int, operation: dict[str, Any]) -> list[int]:
    numbers = []
    for row in campaigns:
        status = str(row.get("effective_status") or row.get("status") or "").upper()
        if status in {"ARCHIVED", "DELETED"}:
            continue
        number = parse_campaign_number(row.get("name"))
        if number is not None:
            numbers.append(number)
    live_max = max(numbers, default=0)
    configured = int((operation.get("campaign_numbering_policy") or {}).get("next_required_campaign_number") or live_max + 1)
    start = live_max + 1
    if configured != start:
        raise DailyBlocked(
            "campaign_numbering",
            "configured next campaign number drifted from live Meta",
            {"configured": configured, "live_next": start},
        )
    selected = list(range(start, start + count))
    if selected[-1] > 59:
        raise DailyBlocked("campaign_numbering", "Smart Bidding tracked range ends at C59", {"selected": selected})
    return selected


def active_budget_minor(campaigns: list[dict[str, Any]]) -> int:
    total = 0
    for row in campaigns:
        status = str(row.get("configured_status") or row.get("status") or "").upper()
        effective = str(row.get("effective_status") or "").upper()
        if status == "ACTIVE" and effective not in {"ARCHIVED", "DELETED"}:
            try:
                value = int(str(row.get("daily_budget") or "0"))
            except ValueError as exc:
                raise DailyBlocked("budget_cap", "active campaign budget is malformed", {"campaign_id": row.get("id")}) from exc
            if value <= 0:
                raise DailyBlocked("budget_cap", "active campaign budget is missing", {"campaign_id": row.get("id")})
            total += value
    return total


def effective_account_cap_minor(policy: dict[str, Any], required_minor: int, scope: str) -> dict[str, int | bool]:
    base_cap_minor = int(Decimal(str(policy.get("operational_account_cap_usd") or 0)) * 100)
    if base_cap_minor <= 0:
        raise DailyBlocked("budget_cap", "operational account budget floor is invalid")
    dynamic = policy.get("dynamic_account_cap") or {}
    allowed_scopes = {str(item) for item in dynamic.get("allowed_scopes") or []}
    dynamic_enabled = dynamic.get("enabled") is True and scope in allowed_scopes
    cap_minor = max(base_cap_minor, required_minor) if dynamic_enabled else base_cap_minor
    return {
        "base_cap_minor": base_cap_minor,
        "cap_minor": cap_minor,
        "cap_adjusted_minor": max(0, cap_minor - base_cap_minor),
        "dynamic_enabled": dynamic_enabled,
    }


def enforce_budget_cap(campaigns: list[dict[str, Any]], count: int, operation: dict[str, Any]) -> dict[str, int | bool]:
    policy = operation.get("daily_budget_policy") or {}
    initial_minor = int(Decimal(str(policy.get("new_campaign_initial_budget_usd") or 0)) * 100)
    before = active_budget_minor(campaigns)
    if initial_minor <= 0:
        raise DailyBlocked("budget_cap", "initial campaign budget is invalid")
    required_minor = before + count * initial_minor
    envelope = effective_account_cap_minor(policy, required_minor, "scheduled_creation")
    cap_minor = int(envelope["cap_minor"])
    available = max(0, cap_minor - before)
    capacity = available // initial_minor
    selected = min(count, capacity)
    if selected < 1:
        raise DailyBlocked(
            "budget_cap",
            "no new campaign fits the operational account budget envelope at the approved initial budget",
            {"active_before_minor": before, "available_minor": available, "initial_minor": initial_minor, "desired_count": count, "capacity": capacity, **envelope},
        )
    after = before + selected * initial_minor
    return {
        "active_before_minor": before,
        "available_minor": available,
        "initial_minor": initial_minor,
        "desired_count": count,
        "selected_count": selected,
        "deferred_by_budget_count": count - selected,
        "new_minor": selected * initial_minor,
        "projected_minor": after,
        **envelope,
    }


def resume_budget_plan(
    campaigns: list[dict[str, Any]],
    count: int,
    completed_before: int,
    operation: dict[str, Any],
) -> dict[str, int | bool]:
    """Budget only the missing layer; a fully-created request reports live total."""
    pending = max(0, count - completed_before)
    if pending:
        budget = enforce_budget_cap(campaigns, pending, operation)
        if int(budget["selected_count"]) < pending:
            raise DailyBlocked("budget_cap", "remaining resumable campaign no longer fits the operational cap", budget)
        return budget
    policy = operation.get("daily_budget_policy") or {}
    initial_minor = int(Decimal(str(policy.get("new_campaign_initial_budget_usd") or 0)) * 100)
    active_minor = active_budget_minor(campaigns)
    envelope = effective_account_cap_minor(policy, active_minor, "scheduled_creation")
    return {
        "active_before_minor": active_minor,
        "available_minor": max(0, int(envelope["cap_minor"]) - active_minor),
        "initial_minor": initial_minor,
        "desired_count": count,
        "selected_count": 0,
        "deferred_by_budget_count": 0,
        "new_minor": 0,
        "projected_minor": active_minor,
        **envelope,
    }


def validate_engine_config(config: dict[str, Any]) -> None:
    required_true = ["enabled", "write_enabled", "media_upload_enabled", "require_prevalidated_manifest"]
    missing = [key for key in required_true if config.get(key) is not True]
    if missing:
        raise DailyBlocked("engine_config", "required v3 gates are not active", {"missing_true": missing})
    if int(config.get("engine_version") or 0) != 3 or str(config.get("graph_version") or "") != GRAPH_VERSION or int(config.get("bundle_size") or 0) != 2:
        raise DailyBlocked("engine_config", "v3 engine identity, Graph version or bundle size drifted")


def reconciliation_asset_ok(row: dict[str, Any], allowed: dict[str, dict[str, Any]]) -> bool:
    source = allowed.get(str(row.get("asset_id") or "")) or {}
    return (
        source.get("approved") is True
        and str(source.get("asset_drive_id") or "") == str(row.get("asset_drive_id") or "")
        and str(source.get("clean_checksum") or "") == str(row.get("clean_checksum") or "")
        and not (source.get("meta_conflicts") or [])
    )


def _creative_candidate(
    row: dict[str, Any],
    drive_ids: set[str],
    allowed: dict[str, dict[str, Any]] | None,
    *,
    max_test_attempts: int,
) -> bool:
    status = str(row.get("status") or "")
    ready = status == "01_READY"
    retest = (
        status == "03_TESTED"
        and row.get("evaluation_status") == "INCONCLUSIVO_POR_SUBENTREGA"
        and row.get("retest_eligible") is True
        and int(row.get("test_attempt_count") or 0) < max_test_attempts
    )
    return (
        row.get("vertical") == "CAR"
        and row.get("country") == "BR"
        and row.get("language") == "BR"
        and row.get("format") == "VID"
        and (ready or retest)
        and row.get("metadata_clean") is True
        and row.get("ares_eligible") is True
        and not row.get("used_by")
        and str(row.get("asset_drive_id") or "") in drive_ids
        and (allowed is None or reconciliation_asset_ok(row, allowed))
    )


def select_assets(
    rows: list[dict[str, Any]],
    drive_ids: set[str],
    count: int,
    *,
    reconciliation: dict[str, Any] | None = None,
    mix_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    allowed = (
        {str(row.get("asset_id") or ""): row for row in reconciliation.get("assets") or []}
        if reconciliation is not None
        else None
    )
    policy = mix_policy or {}
    max_attempts = int(policy.get("max_test_attempts") or 2)
    candidates = [
        row
        for row in rows
        if _creative_candidate(row, drive_ids, allowed, max_test_attempts=max_attempts)
    ]
    candidates.sort(
        key=lambda row: (
            int(row.get("test_attempt_count") or 0),
            str(row.get("first_seen_at") or ""),
            str(row.get("canonical_filename") or ""),
        )
    )

    ready = [row for row in candidates if row.get("status") == "01_READY"]
    retest = [row for row in candidates if row.get("status") == "03_TESTED"]
    selected: list[dict[str, Any]] = []
    fingerprints: set[str] = set()

    def take(pool: list[dict[str, Any]], amount: int) -> int:
        taken = 0
        while pool and taken < amount:
            row = pool.pop(0)
            fingerprint = str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id") or "")
            if not fingerprint or fingerprint in fingerprints:
                continue
            fingerprints.add(fingerprint)
            selected.append(row)
            taken += 1
        return taken

    if policy.get("enabled") is True:
        if count % 3:
            raise DailyBlocked("asset_selection", "creative retest mix requires complete 1x1x3 campaign groups")
        ready_slots = int(policy.get("ready_slots_per_campaign") or 2)
        retest_slots = int(policy.get("retest_slots_per_campaign") or 1)
        if ready_slots + retest_slots != 3 or ready_slots < 1 or retest_slots < 0:
            raise DailyBlocked("asset_selection", "creative retest mix policy is invalid")
        for _ in range(count // 3):
            if take(ready, ready_slots) != ready_slots:
                break
            retest_taken = take(retest, retest_slots)
            if retest_taken < retest_slots:
                take(ready, retest_slots - retest_taken)
    else:
        take(ready, count)

    if len(selected) != count:
        raise DailyBlocked(
            "asset_selection",
            "insufficient unique eligible reconciled assets for the approved READY/TESTED mix",
            {
                "required": count,
                "selected": len(selected),
                "ready_candidates": len([row for row in candidates if row.get("status") == "01_READY"]),
                "retest_candidates": len([row for row in candidates if row.get("status") == "03_TESTED"]),
            },
        )
    return selected


def normalize_title(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def source_sequence(value: str | None) -> str | None:
    matches = re.findall(r"(?:^|[_\s-])(\d{3})(?:\s*-|[_\s])", str(value or ""))
    return matches[-1] if matches else None


def reconciliation_conflicts(candidates: list[dict[str, Any]], ads: list[dict[str, Any]], videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    haystacks = []
    for ad in ads:
        creative = ad.get("creative") or {}
        haystacks.append({
            "kind": "ad",
            "id": str(ad.get("id") or ""),
            "text": normalize_title(" ".join([str(ad.get("name") or ""), str(creative.get("name") or ""), str((ad.get("campaign") or {}).get("name") or "")])),
            "configured_status": str(ad.get("configured_status") or ad.get("status") or "").upper(),
            "effective_status": str(ad.get("effective_status") or "").upper(),
            "campaign_id": str((ad.get("campaign") or {}).get("id") or ""),
            "campaign_status": str((ad.get("campaign") or {}).get("effective_status") or (ad.get("campaign") or {}).get("status") or "").upper(),
        })
    for video in videos:
        haystacks.append({"kind": "video", "id": str(video.get("video_id") or ""), "text": normalize_title(video.get("title"))})
    conflicts = []
    for row in candidates:
        canonical = normalize_title(Path(str(row.get("canonical_filename") or "")).stem)
        original = normalize_title(Path(str(row.get("original_filename") or "")).stem)
        sequence = source_sequence(row.get("original_filename"))
        for haystack in haystacks:
            text = haystack["text"]
            exact = bool(canonical and canonical in text) or bool(original and len(original) >= 12 and original in text)
            sequence_match = bool(sequence and re.search(rf"(?:^|\s){re.escape(sequence)}(?:\s|$)", text))
            if exact or sequence_match:
                conflicts.append({
                    "asset_id": row.get("asset_id"),
                    "match_kind": haystack["kind"],
                    "match_id": haystack["id"],
                    "exact_name": exact,
                    "source_sequence": sequence if sequence_match else None,
                    "configured_status": haystack.get("configured_status"),
                    "effective_status": haystack.get("effective_status"),
                    "campaign_id": haystack.get("campaign_id"),
                    "campaign_status": haystack.get("campaign_status"),
                })
    return conflicts


def expected_retest_meta_ids(row: dict[str, Any]) -> set[str]:
    values = {
        str(row.get("meta_ad_id") or ""),
        str(row.get("meta_video_id") or ""),
        *(str(item) for item in row.get("meta_video_ids") or []),
        *(str(item) for item in row.get("meta_prestage_video_ids") or []),
    }
    for attempt in row.get("test_history") or []:
        values.update(
            {
                str(attempt.get("ad_id") or attempt.get("meta_ad_id") or ""),
                str(attempt.get("vertical_video_id") or ""),
                str(attempt.get("square_video_id") or ""),
                str(attempt.get("prestage_vertical_video_id") or ""),
                str(attempt.get("prestage_square_video_id") or ""),
                *(str(item) for item in attempt.get("meta_video_ids") or []),
            }
        )
    return {value for value in values if value}


def expected_retest_conflict(row: dict[str, Any], conflict: dict[str, Any]) -> bool:
    if str(conflict.get("match_id") or "") not in expected_retest_meta_ids(row):
        return False
    if conflict.get("match_kind") != "ad":
        return True
    return str(conflict.get("effective_status") or "").upper() not in {"ACTIVE", "PENDING_REVIEW", "IN_PROCESS"}


def verify_reconciliation(path: Path, selected: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    payload = load_json(path)
    if payload.get("status") != "valid" or str(payload.get("account_id") or "") != ACCOUNT_ID:
        raise DailyBlocked("reconciliation", "reconciliation manifest is invalid or belongs to another account")
    try:
        valid_until = datetime.fromisoformat(str(payload.get("valid_until_utc") or "").replace("Z", "+00:00"))
    except ValueError as exc:
        raise DailyBlocked("reconciliation", "reconciliation manifest expiry is invalid") from exc
    if valid_until <= now.astimezone(timezone.utc):
        raise DailyBlocked("reconciliation", "reconciliation manifest expired", {"valid_until_utc": payload.get("valid_until_utc")})
    allowed = {str(row.get("asset_id") or ""): row for row in payload.get("assets") or []}
    checks = []
    for row in selected:
        ok = reconciliation_asset_ok(row, allowed)
        checks.append({"asset_id": row.get("asset_id"), "ok": ok})
    if not checks or not all(item["ok"] for item in checks):
        raise DailyBlocked("reconciliation", "one or more selected assets are not reconciled", {"checks": checks})
    return {"generated_at_utc": payload.get("generated_at_utc"), "valid_until_utc": payload.get("valid_until_utc"), "checks": checks}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if not spec or not spec.loader:
        raise DailyBlocked("module", f"cannot load module {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def drive_request(token: str, method: str, url: str, *, body: bytes | None = None, content_type: str | None = None) -> dict[str, Any]:
    count_call("drive_http")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "MGS-Ares-CPV-V3-Daily/1.0"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read().decode("utf-8", "replace"))
        except Exception:
            error = {"type": "non_json_error"}
        raise DailyBlocked("drive_request", "Drive request failed", {"http": exc.code, "error": error}) from exc


def drive_children(token: str, parent_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "q": f"'{parent_id}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,mimeType,size,md5Checksum,driveId,parents,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive))",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "orderBy": "name_natural",
        }
        if page_token:
            params["pageToken"] = page_token
        payload = drive_request(token, "GET", "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params))
        rows.extend(payload.get("files") or [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            return rows


def one_folder(rows: list[dict[str, Any]], name: str, stage: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("name") == name and row.get("mimeType") == FOLDER_MIME]
    if len(matches) != 1:
        raise DailyBlocked(stage, f"expected exactly one folder named {name}", {"count": len(matches)})
    return matches[0]


def drive_inventory(token: str) -> dict[str, Any]:
    root = drive_request(
        token,
        "GET",
        f"https://www.googleapis.com/drive/v3/files/{DRIVE_ID}?"
        + urllib.parse.urlencode({"fields": "id,name,driveId,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive)", "supportsAllDrives": "true"}),
    )
    caps = root.get("capabilities") or {}
    if root.get("driveId") != DRIVE_ID or root.get("trashed") or not all(caps.get(name) for name in ("canDownload", "canEdit", "canMoveItemWithinDrive")):
        raise DailyBlocked("drive_root", "canonical Shared Drive identity or capabilities failed")
    creatives = one_folder(drive_children(token, DRIVE_ID), "CRIATIVOS", "drive_creatives")
    operation = one_folder(drive_children(token, creatives["id"]), "CAR_BR_BR", "drive_operation")
    files: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for kind in ("IMG", "VID"):
        folder = one_folder(drive_children(token, operation["id"]), kind, f"drive_{kind}")
        children = drive_children(token, folder["id"])
        status_folders = {
            status: one_folder(children, status, f"drive_{kind}_{status.lower()}")
            for status in ("01_READY", "02_TESTING", "03_TESTED", "04_WINNERS", "05_REJECTED")
        }
        current_by_status = {
            status: [row for row in drive_children(token, folder["id"]) if row.get("mimeType") != FOLDER_MIME]
            for status, folder in status_folders.items()
        }
        parent_ids = {status: folder["id"] for status, folder in status_folders.items()}
        for status, current in current_by_status.items():
            for row in current:
                row.update(
                    kind=kind,
                    location=status,
                    source_parent_id=parent_ids[status],
                    status_parent_ids=parent_ids,
                    ready_parent_id=parent_ids["01_READY"],
                    testing_parent_id=parent_ids["02_TESTING"],
                    tested_parent_id=parent_ids["03_TESTED"],
                    winners_parent_id=parent_ids["04_WINNERS"],
                    rejected_parent_id=parent_ids["05_REJECTED"],
                )
            files.extend(current)
        current_ready = current_by_status["01_READY"]
        counts[kind] = len(current_ready)
        counts[f"{kind}_RETEST_ELIGIBLE_PHYSICAL"] = len(current_by_status["03_TESTED"])
    counts["TOTAL"] = counts.get("IMG", 0) + counts.get("VID", 0)
    return {"root": root, "files": files, "counts": counts}


def download_drive_file(token: str, source: dict[str, Any], destination: Path) -> dict[str, Any]:
    count_call("drive_download")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files/{source['id']}?"
        + urllib.parse.urlencode({"alt": "media", "supportsAllDrives": "true"}),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "MGS-Ares-CPV-V3-Daily/1.0"},
    )
    digest = hashlib.md5()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=240) as response, destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if digest.hexdigest() != str(source.get("md5Checksum") or "") or size != int(source.get("size") or 0):
        destination.unlink(missing_ok=True)
        raise DailyBlocked("drive_download", "Drive download checksum or size mismatch", {"file_id": source.get("id")})
    return {"md5": digest.hexdigest(), "bytes": size}


def verify_clean(path: Path) -> dict[str, Any]:
    result = subprocess.run([str(SANITIZER), "verify", str(path)], capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0 or "clean: true" not in result.stdout:
        raise DailyBlocked("metadata_verify", "creative metadata verification failed", {"file": path.name, "rc": result.returncode})
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size, "clean": True}


def make_square_clean(source: Path, destination: Path) -> dict[str, Any]:
    count_call("local_square_render")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        try:
            verified = verify_clean(destination)
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", str(destination)],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            body = json.loads(probe.stdout or "{}") if probe.returncode == 0 else {}
            video = next((row for row in body.get("streams") or [] if row.get("codec_type") == "video"), {})
            if video.get("width") == 1080 and video.get("height") == 1080:
                return {**verified, "width": 1080, "height": 1080, "reused_existing": True}
        except Exception:
            pass
        destination.unlink(missing_ok=True)
    raw = destination.with_suffix(".raw.mp4")
    raw.unlink(missing_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-vf", "crop=iw:iw:0:(ih-iw)/2,scale=1080:1080", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(raw)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        raise DailyBlocked("square", "square render failed", {"file": source.name})
    cleaned = subprocess.run([str(SANITIZER), "clean", str(raw), "--out", str(destination), "--agent", "ares", "--json"], capture_output=True, text=True, timeout=300, check=False)
    raw.unlink(missing_ok=True)
    if cleaned.returncode != 0:
        raise DailyBlocked("square", "square metadata sanitization failed", {"file": source.name})
    verified = verify_clean(destination)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", str(destination)], capture_output=True, text=True, timeout=60, check=False)
    body = json.loads(probe.stdout or "{}") if probe.returncode == 0 else {}
    video = next((row for row in body.get("streams") or [] if row.get("codec_type") == "video"), {})
    if video.get("width") != 1080 or video.get("height") != 1080:
        raise DailyBlocked("square", "square dimensions are not 1080x1080", {"file": source.name})
    return {**verified, "width": 1080, "height": 1080}


def move_to_status(token: str, source: dict[str, Any], target_status: str) -> dict[str, Any]:
    parent_ids = source.get("status_parent_ids") or {}
    target_parent_id = str(parent_ids.get(target_status) or source.get({
        "01_READY": "ready_parent_id",
        "02_TESTING": "testing_parent_id",
        "03_TESTED": "tested_parent_id",
        "04_WINNERS": "winners_parent_id",
        "05_REJECTED": "rejected_parent_id",
    }.get(target_status, "")) or "")
    if not target_parent_id:
        raise DailyBlocked("drive_move", "target Drive status folder is unavailable", {"target_status": target_status})
    if source.get("location") == target_status or set(source.get("parents") or []) == {target_parent_id}:
        result = {
            "id": source.get("id"),
            "name": source.get("name"),
            "driveId": source.get("driveId"),
            "parents": [target_parent_id],
            "trashed": False,
            "size": source.get("size"),
            "md5Checksum": source.get("md5Checksum"),
            "already_in_target": True,
            "target_status": target_status,
        }
        if target_status == "02_TESTING":
            result["already_in_testing"] = True
        return result
    source_parent_id = str(source.get("source_parent_id") or ((source.get("parents") or [""])[0]))
    if not source_parent_id:
        raise DailyBlocked("drive_move", "source Drive status folder is unavailable", {"file_id": source.get("id")})
    params = urllib.parse.urlencode({"addParents": target_parent_id, "removeParents": source_parent_id, "fields": "id,name,driveId,parents,trashed,size,md5Checksum", "supportsAllDrives": "true"})
    result = drive_request(token, "PATCH", f"https://www.googleapis.com/drive/v3/files/{source['id']}?{params}", body=b"{}", content_type="application/json")
    if result.get("driveId") != DRIVE_ID or result.get("trashed") or set(result.get("parents") or []) != {target_parent_id} or str(result.get("md5Checksum") or "") != str(source.get("md5Checksum") or ""):
        raise DailyBlocked("drive_move", "Drive move readback failed", {"file_id": source.get("id")})
    result["target_status"] = target_status
    return result


def move_to_testing(token: str, source: dict[str, Any]) -> dict[str, Any]:
    return move_to_status(token, source, "02_TESTING")


def stock_counts(inventory: list[dict[str, Any]], drive: dict[str, Any]) -> dict[str, int]:
    live_ids = {str(row.get("id") or "") for row in drive.get("files") or []}
    unique = {
        str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id"))
        for row in inventory
        if row.get("ares_eligible") is True
        and row.get("status") == "01_READY"
        and not row.get("used_by")
        and str(row.get("asset_drive_id") or "") in live_ids
    }
    retest_unique = {
        str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id"))
        for row in inventory
        if row.get("ares_eligible") is True
        and row.get("status") == "03_TESTED"
        and row.get("evaluation_status") == "INCONCLUSIVO_POR_SUBENTREGA"
        and row.get("retest_eligible") is True
        and not row.get("used_by")
        and str(row.get("asset_drive_id") or "") in live_ids
    }
    return {
        "ready_folder_total": int((drive.get("counts") or {}).get("TOTAL") or 0),
        "ready_folder_img": int((drive.get("counts") or {}).get("IMG") or 0),
        "ready_folder_vid": int((drive.get("counts") or {}).get("VID") or 0),
        "eligible_unique_creatives": len(unique),
        "retest_eligible_unique_creatives": len(retest_unique),
    }


def reserve_inventory(path: Path, rows: list[dict[str, Any]], selected: list[dict[str, Any]], audit_path: Path) -> None:
    ids = {str(row.get("asset_id") or "") for row in selected}
    for row in rows:
        if str(row.get("asset_id") or "") in ids:
            row.update(reservation_status="RESERVADO_PELO_ARES_V3_DAILY", ares_eligible=False, used_by="ARES_V3_IN_FLIGHT", campaign_owner="Ares", reservation_audit=str(audit_path), last_reconciled_at=utc_now())
    atomic_inventory(path, rows)


def release_inventory(path: Path, rows: list[dict[str, Any]], selected_ids: set[str]) -> None:
    for row in rows:
        if str(row.get("asset_id") or "") in selected_ids and row.get("used_by") == "ARES_V3_IN_FLIGHT":
            reservation = "LIBERADO_PARA_RETESTE" if row.get("status") == "03_TESTED" else "LIBERADO_POR_RODOLFO_PARA_ARES_DAILY"
            row.update(reservation_status=reservation, ares_eligible=True, used_by=None, campaign_owner="Ares", last_reconciled_at=utc_now())
            row.pop("reservation_audit", None)
    atomic_inventory(path, rows)


def update_inventory_assignments(path: Path, rows: list[dict[str, Any]], assignments: list[dict[str, Any]], moves: dict[str, dict[str, Any]], audit_path: Path) -> None:
    by_asset = {str(row["asset_id"]): row for row in assignments}
    for row in rows:
        assignment = by_asset.get(str(row.get("asset_id") or ""))
        if not assignment:
            continue
        moved = str(row.get("asset_drive_id") or "") in moves
        existing_attempt = next(
            (
                item
                for item in row.get("test_history") or []
                if str(item.get("campaign_id") or "") == str(assignment["campaign_id"])
                and str(item.get("ad_id") or "") == str(assignment["ad_id"])
            ),
            None,
        )
        attempt_number = int((existing_attempt or {}).get("attempt") or (int(row.get("test_attempt_count") or 0) + 1))
        attempt = existing_attempt or {
            "attempt": attempt_number,
            "assigned_at_utc": utc_now(),
            "campaign_id": assignment["campaign_id"],
            "adset_id": assignment["adset_id"],
            "ad_id": assignment["ad_id"],
            "creative_id": assignment["creative_id"],
            "source_ad_id": assignment["source_ad_id"],
            "effective_object_story_id": assignment["effective_object_story_id"],
            "vertical_video_id": assignment["vertical_video_id"],
            "square_video_id": assignment["square_video_id"],
            "prestage_vertical_video_id": assignment["prestage_vertical_video_id"],
            "prestage_square_video_id": assignment["prestage_square_video_id"],
            "meta_video_ids": [assignment["vertical_video_id"], assignment["square_video_id"]],
            "campaign_audit": str(audit_path),
        }
        if existing_attempt is None:
            row.setdefault("test_history", []).append(attempt)
        row.update(
            status="02_TESTING" if moved else "01_READY_USED_MOVE_PENDING",
            evaluation_status="EM_TESTE",
            retest_eligible=False,
            test_attempt_count=attempt_number,
            reservation_status="UTILIZADO_PELO_ARES",
            ares_eligible=False,
            used_by="ARES",
            campaign_owner="Ares",
            ad_account_id=ACCOUNT_ID,
            meta_campaign_id=assignment["campaign_id"],
            meta_adset_id=assignment["adset_id"],
            meta_ad_id=assignment["ad_id"],
            meta_creative_id=assignment["creative_id"],
            meta_lineage_source_ad_id=assignment["source_ad_id"],
            effective_object_story_id=assignment["effective_object_story_id"],
            meta_video_id=assignment["vertical_video_id"],
            meta_video_ids=[assignment["vertical_video_id"], assignment["square_video_id"]],
            meta_prestage_video_ids=[assignment["prestage_vertical_video_id"], assignment["prestage_square_video_id"]],
            meta_video_materialization="ad_copies_api_derived",
            campaign_audit=str(audit_path),
            drive_status_readback=moves.get(str(row.get("asset_drive_id") or "")),
            last_reconciled_at=utc_now(),
        )
    atomic_inventory(path, rows)


def load_discord_token() -> str:
    for line in (PROFILE / ".env").read_text(errors="ignore").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise DailyBlocked("discord", "Ares Discord token unavailable")


def post_discord(message: str) -> dict[str, Any]:
    if len(message) > 1900:
        raise DailyBlocked("discord", "Discord message exceeds 1900 characters")
    token = load_discord_token()
    payload = json.dumps({"content": message, "allowed_mentions": {"parse": []}}, ensure_ascii=False).encode()
    request = urllib.request.Request(f"https://discord.com/api/v10/channels/{THREAD_CREATION}/messages", data=payload, headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent": "MGS-Ares-CPV-V3-Daily/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    message_id = str(body.get("id") or "")
    if not message_id:
        raise DailyBlocked("discord", "Discord response missing message id")
    check = urllib.request.Request(f"https://discord.com/api/v10/channels/{THREAD_CREATION}/messages/{message_id}", headers={"Authorization": f"Bot {token}", "User-Agent": "MGS-Ares-CPV-V3-Daily/1.0"})
    with urllib.request.urlopen(check, timeout=30) as response:
        readback = json.load(response)
    if str(readback.get("channel_id") or "") != THREAD_CREATION or str(readback.get("content") or "") != message:
        raise DailyBlocked("discord", "Discord readback mismatch")
    return {"message_id": message_id, "thread_id": THREAD_CREATION, "content_match": True}


class LiveDailyBackend:
    def __init__(self, paths: DailyPaths):
        self.paths = paths
        self.common = _load_module(COMMON_PATH, "ares_meta_common_cpv_v3_daily")
        self.sb_common = _load_module(SB_COMMON_PATH, "ares_sb_common_cpv_v3_daily")
        self.drive_module = _load_module(DRIVE_MODULE_PATH, "ares_drive_cpv_v3_daily")
        self.drive_module.load_env()
        setattr(self.drive_module, "SCOPES", "https://www.googleapis.com/auth/drive")
        self.token: str | None = None
        self.page_token: str | None = None
        self.drive_token: str | None = None

    def meta_preflight(self) -> dict[str, Any]:
        token, token_field = self.common.get_token_from_1password(TOKEN_ITEM)
        self.token = token
        count_call("meta_get")
        status, account, _ = self.common.graph_get(ACCOUNT_ACT, token, {"fields": "id,name,currency,timezone_name,account_status,disable_reason"})
        if status != 200 or not isinstance(account, dict) or str(account.get("currency")) != "USD" or str(account.get("timezone_name")) != "America/Sao_Paulo" or int(account.get("account_status") or 0) != 1 or int(account.get("disable_reason") or 0) != 0:
            raise DailyBlocked("meta_preflight", "Meta account identity or health failed", {"http": status})
        campaigns = self._graph_pages(f"{ACCOUNT_ACT}/campaigns", {"fields": "id,name,status,effective_status,configured_status,daily_budget,created_time,start_time,updated_time", "limit": 500})
        count_call("meta_get")
        page_status, pages, _ = self.common.graph_get("me/accounts", token, {"fields": "id,name,tasks,access_token", "limit": 200})
        page = next((row for row in (pages.get("data") or []) if str(row.get("id")) == PAGE_ID), None) if page_status == 200 and isinstance(pages, dict) else None
        if not page or "ADVERTISE" not in (page.get("tasks") or []) or not page.get("access_token"):
            raise DailyBlocked("meta_preflight", "Page is missing ADVERTISE or Page token", {"http": page_status})
        self.page_token = str(page["access_token"])
        return {"account": account, "campaigns": campaigns, "token_report": {"item": TOKEN_ITEM, "field": token_field, "len": len(token)}, "page": {"id": PAGE_ID, "tasks": page.get("tasks")}}

    def _source_hierarchy_snapshot(self, winner: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            raise DailyBlocked("source_selection", "Meta token not initialized")
        campaign_id = str(winner.get("campaign_id") or "")
        count_call("meta_get")
        status, campaign, _ = self.common.graph_get(
            campaign_id,
            self.token,
            {
                "fields": (
                    "id,name,status,effective_status,configured_status,daily_budget,bid_strategy,"
                    "objective,buying_type,special_ad_categories,special_ad_category_country"
                )
            },
        )
        if status != 200 or not isinstance(campaign, dict):
            raise DailyBlocked("source_selection", "ROI-winning source campaign readback failed", {"campaign_id": campaign_id, "http": status})
        configured_status = str(campaign.get("configured_status") or campaign.get("status") or "").upper()
        if configured_status in {"DELETED", "ARCHIVED"}:
            raise DailyBlocked("source_selection", "ROI-winning source campaign is terminal", {"campaign_id": campaign_id})
        if str(campaign.get("bid_strategy") or "").upper() != "LOWEST_COST_WITHOUT_CAP":
            raise DailyBlocked("source_selection", "ROI-winning source campaign is not MAXVOL", {"campaign_id": campaign_id})
        expected_vehicle = canonical_vehicle_type(winner.get("vehicle_type"))
        if vehicle_type_from_text(campaign.get("name")) != expected_vehicle:
            raise DailyBlocked("source_selection", "ROI-winning source vehicle type changed on Meta", {"campaign_id": campaign_id})

        adsets = self._graph_pages(
            f"{campaign_id}/adsets",
            {
                "fields": (
                    "id,name,status,effective_status,configured_status,billing_event,optimization_goal,"
                    "targeting,promoted_object,attribution_spec,regional_regulated_categories,"
                    "regional_regulation_identities,is_dynamic_creative,bid_amount,bid_constraints"
                ),
                "limit": 20,
            },
        )
        adsets = [row for row in adsets if str(row.get("configured_status") or row.get("status") or "").upper() not in {"DELETED", "ARCHIVED"}]
        if len(adsets) != 1:
            raise DailyBlocked("source_selection", "ROI-winning source must have exactly one non-terminal adset", {"campaign_id": campaign_id, "adset_count": len(adsets)})
        source_adset = adsets[0]
        if str(source_adset.get("optimization_goal") or "").upper() != "OFFSITE_CONVERSIONS":
            raise DailyBlocked("source_selection", "ROI-winning source adset optimization is invalid", {"campaign_id": campaign_id})
        source_adset_id = str(source_adset.get("id") or "")
        ads_all = self._graph_pages(
            f"{source_adset_id}/ads",
            {
                "fields": (
                    "id,name,status,effective_status,configured_status,adset_id,"
                    "creative{id,name,status,object_story_spec,asset_feed_spec,degrees_of_freedom_spec}"
                ),
                "limit": 50,
            },
        )
        try:
            ads, ignored_ads = select_canonical_source_ads(ads_all)
        except SourceSelectionError as exc:
            raise DailyBlocked(
                "source_selection",
                str(exc),
                {"campaign_id": campaign_id, "ad_count": len(ads_all)},
            ) from exc

        templates: list[dict[str, Any]] = []
        for ad in ads:
            creative = ad.get("creative") or {}
            if not isinstance(creative, dict):
                raise DailyBlocked("source_selection", "ROI-winning source creative readback is invalid", {"ad_id": ad.get("id")})
            creative_payload = {
                key: creative[key]
                for key in ("object_story_spec", "asset_feed_spec", "degrees_of_freedom_spec")
                if isinstance(creative.get(key), dict) and creative.get(key)
            }
            videos = list((creative_payload.get("asset_feed_spec") or {}).get("videos") or [])
            if not creative_payload.get("object_story_spec") or len(videos) < 2:
                raise DailyBlocked("source_selection", "ROI-winning source creative is incomplete", {"ad_id": ad.get("id")})
            templates.append({
                "source_ad_id": str(ad.get("id") or ""),
                "source_ad_name": str(ad.get("name") or ""),
                "source_creative_id": str(creative.get("id") or ""),
                "source_creative_name": str(creative.get("name") or ""),
                "creative_payload": creative_payload,
            })
        return {
            "vehicle_type": expected_vehicle,
            "source_campaign_id": campaign_id,
            "source_adset_id": source_adset_id,
            "source_campaign": campaign,
            "source_adset": source_adset,
            "templates": templates,
            "ignored_source_ads": [
                {
                    "id": str(row.get("id") or ""),
                    "name": str(row.get("name") or ""),
                    "configured_status": str(row.get("configured_status") or row.get("status") or ""),
                }
                for row in ignored_ads
            ],
            "roi_evidence": {
                key: winner.get(key)
                for key in (
                    "campaign_id", "campaign_name", "target_date", "currency", "metric", "formula",
                    "investment_usd", "net_revenue_usd", "roi_pct", "row_count", "candidate_count", "tie_breaker",
                )
            },
        }

    def select_clone_sources(
        self,
        *,
        asset_refs: list[dict[str, Any]],
        campaign_count: int,
        meta_campaigns: list[dict[str, Any]],
        target_date: str,
        operation: dict[str, Any],
        request_id: str,
    ) -> dict[str, Any]:
        try:
            source_policy = ((operation.get("daily_new_campaign_routine") or {}).get("clone_source_policy") or {})
            if not isinstance(source_policy, dict) or "highest Smart Bidding ROI" not in str(source_policy.get("rule") or ""):
                raise SourceSelectionError("canonical same-vehicle highest-ROI source policy is missing")
            campaign_vehicle_types = asset_group_vehicle_types(asset_refs, campaign_count)
            authorized_type = authorized_request_vehicle_type(operation, request_id)
            if authorized_type and any(value != authorized_type for value in campaign_vehicle_types):
                raise SourceSelectionError(f"authorized request is {authorized_type} but selected assets are {campaign_vehicle_types}")
            payload = {
                "initialDate": f"{target_date}T00:00:00.000Z",
                "finalDate": f"{target_date}T23:59:59.999Z",
                "publishers": [SB_PUBLISHER],
                "currency": "USD",
            }
            count_call("smart_bidding_read")
            status, rows, _ = self.sb_common.api_request(
                "POST",
                "/report/performance_per_campaigns",
                payload=payload,
                item_name=SB_TOKEN_ITEM,
            )
            if status not in {200, 201} or not isinstance(rows, list):
                raise DailyBlocked("source_selection", "Smart Bidding source ranking read failed", {"http": status})
            roi_by_campaign = aggregate_smart_bidding_roi(
                rows,
                target_date=target_date,
                account_id=ACCOUNT_ID,
                domain=SB_DOMAIN,
            )
            sources_by_vehicle: dict[str, dict[str, Any]] = {}
            for vehicle_type in sorted(set(campaign_vehicle_types)):
                winner = select_best_roi_campaign(meta_campaigns, roi_by_campaign, vehicle_type=vehicle_type)
                sources_by_vehicle[vehicle_type] = self._source_hierarchy_snapshot(winner)
            return {
                "schema_version": 1,
                "policy": "highest_smart_bidding_roi_same_vehicle_type_at_manifest_preflight",
                "policy_authorized_by": source_policy.get("authorized_by"),
                "policy_authorization_source": source_policy.get("authorization_source"),
                "selected_at_utc": utc_now(),
                "target_date": target_date,
                "currency": "USD",
                "request_id": request_id,
                "campaign_vehicle_types": campaign_vehicle_types,
                "sources_by_vehicle": sources_by_vehicle,
            }
        except SourceSelectionError as exc:
            raise DailyBlocked("source_selection", str(exc)) from exc

    def _graph_pages(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.token:
            raise DailyBlocked("meta", "Meta token not initialized")
        return self._graph_pages_with_token(path, params, self.token)

    def _graph_pages_with_token(self, path: str, params: dict[str, Any], token: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        next_path, next_params = path, dict(params)
        while True:
            count_call("meta_get")
            status, body, _ = self.common.graph_get(next_path, token, next_params)
            if status != 200 or not isinstance(body, dict):
                raise DailyBlocked("meta", "Meta paginated GET failed", {"path": next_path, "http": status})
            rows.extend(body.get("data") or [])
            next_url = (body.get("paging") or {}).get("next")
            if not next_url:
                return rows
            parsed = urllib.parse.urlparse(next_url)
            next_path = parsed.path.split(f"/{GRAPH_VERSION}/", 1)[-1].lstrip("/")
            next_params = {key: values[-1] for key, values in urllib.parse.parse_qs(parsed.query).items()}

    def drive_preflight(self) -> dict[str, Any]:
        service_account = self.drive_module.extract_service_account(self.drive_module.get_op_item_json())
        if service_account.get("client_email") != "mgsagent@mgs-core-prod.iam.gserviceaccount.com" or service_account.get("project_id") != "mgs-core-prod":
            raise DailyBlocked("drive_identity", "Drive Service Account identity mismatch")
        self.drive_token = self.drive_module.get_access_token(service_account)
        if not self.drive_token:
            raise DailyBlocked("drive_identity", "Drive Service Account token unavailable")
        inventory = drive_inventory(self.drive_token)
        return {"service_account": service_account["client_email"], "project_id": service_account["project_id"], "drive": inventory}

    def refresh_reconciliation(self, inventory: list[dict[str, Any]], drive: dict[str, Any], now: datetime) -> dict[str, Any]:
        if not self.token or not self.page_token:
            raise DailyBlocked("reconciliation", "Meta/Page token not initialized")
        operation = load_json(self.paths.operation)
        lifecycle = operation.get("creative_performance_lifecycle") or {}
        retest_policy = lifecycle.get("retest") or {}
        max_attempts = int(retest_policy.get("max_test_attempts") or 2)
        candidate_ids = {
            str(row.get("id") or "")
            for row in drive.get("files") or []
            if row.get("location") in {"01_READY", "03_TESTED"}
        }
        candidates = [
            row for row in inventory
            if _creative_candidate(row, candidate_ids, None, max_test_attempts=max_attempts)
        ]
        fields = "id,name,status,effective_status,configured_status,campaign{id,name,status,effective_status},creative{id,name,asset_feed_spec,object_story_spec}"
        ads_by_id: dict[str, dict[str, Any]] = {}
        for status_filter in (None, ["ARCHIVED"]):
            params: dict[str, Any] = {"fields": fields, "limit": 500}
            if status_filter:
                params["effective_status"] = status_filter
            for row in self._graph_pages(f"{ACCOUNT_ACT}/ads", params):
                ads_by_id[str(row.get("id") or "")] = row
        ads = list(ads_by_id.values())
        video_ids = sorted({
            str(video.get("video_id"))
            for ad in ads
            for video in (((ad.get("creative") or {}).get("asset_feed_spec") or {}).get("videos") or [])
            if video.get("video_id")
        })
        videos = []
        for start in range(0, len(video_ids), 50):
            requests_ = [{"name": video_id, "path": video_id, "params": {"fields": "id,title,length,status"}} for video_id in video_ids[start:start + 50]]
            count_call("meta_batch")
            status, rows, _ = self.common.graph_batch_get(self.page_token, requests_)
            if status != 200 or not isinstance(rows, list):
                raise DailyBlocked("reconciliation", "Meta video reconciliation batch failed", {"http": status})
            for row in rows:
                body = row.get("body") or {}
                if int(row.get("code") or 0) == 200:
                    videos.append({"video_id": str(row.get("name") or ""), "title": body.get("title")})
        conflicts = reconciliation_conflicts(candidates, ads, videos)
        conflicts_by_asset: dict[str, list[dict[str, Any]]] = {}
        for conflict in conflicts:
            conflicts_by_asset.setdefault(str(conflict.get("asset_id") or ""), []).append(conflict)
        assets = []
        for row in candidates:
            raw_conflicts = conflicts_by_asset.get(str(row.get("asset_id") or ""), [])
            expected_conflicts = []
            blocking_conflicts = raw_conflicts
            if row.get("status") == "03_TESTED":
                expected_conflicts = [item for item in raw_conflicts if expected_retest_conflict(row, item)]
                blocking_conflicts = [item for item in raw_conflicts if item not in expected_conflicts]
            assets.append({
                "asset_id": row.get("asset_id"),
                "canonical_filename": row.get("canonical_filename"),
                "asset_drive_id": row.get("asset_drive_id"),
                "clean_checksum": row.get("clean_checksum"),
                "perceptual_fingerprint": row.get("perceptual_fingerprint"),
                "candidate_status": row.get("status"),
                "retest_eligible": row.get("retest_eligible") is True,
                "approved": not blocking_conflicts,
                "meta_conflicts": blocking_conflicts,
                "expected_prior_test_conflicts": expected_conflicts,
            })
        payload = {
            "schema_version": 2,
            "status": "valid",
            "account_id": ACCOUNT_ID,
            "generated_at_utc": now.astimezone(timezone.utc).isoformat(),
            "valid_until_utc": (now.astimezone(timezone.utc) + timedelta(hours=6)).isoformat(),
            "source": {"mode": "v3_live_separate_reconciliation", "current_and_archived": True},
            "meta_counts": {"ads_scanned": len(ads), "video_ids_scanned": len(video_ids)},
            "assets": assets,
        }
        if sum(item["approved"] is True for item in assets) < 3:
            raise DailyBlocked("reconciliation", "fewer than three reconciled assets remain")
        atomic_json(self.paths.reconciliation, payload)
        return payload

    def prepare_and_prestage(self, selected: list[dict[str, Any]], drive: dict[str, Any], work_dir: Path, registry: MediaRegistry) -> list[dict[str, Any]]:
        if not self.token or not self.drive_token:
            raise DailyBlocked("prestage", "Meta advertiser or Drive token not initialized")
        by_id = {str(row.get("id") or ""): row for row in drive.get("files") or []}
        uploader = AdAccountVideoUploader(
            common=self.common,
            user_token=self.token,
            account_id=ACCOUNT_ID,
            graph_version=GRAPH_VERSION,
        )
        expected_titles = {
            title
            for row in selected
            for title in (
                media_title("VERTICAL", str(row["asset_id"]), str(row["clean_checksum"])),
                media_title("SQUARE", str(row["asset_id"]), str(row["clean_checksum"])),
            )
        }
        existing_by_title: dict[str, list[str]] = {}
        for video in self._graph_pages_with_token(
            f"{ACCOUNT_ACT}/advideos", {"fields": "id,title,status", "limit": 500}, self.token
        ):
            title = str(video.get("title") or "")
            if title in expected_titles and video.get("id"):
                existing_by_title.setdefault(title, []).append(str(video["id"]))
        duplicates = {title: ids for title, ids in existing_by_title.items() if len(ids) > 1}
        if duplicates:
            raise DailyBlocked("prestage", "duplicate deterministic ad-account video titles require reconciliation", {"duplicates": duplicates})
        prepared = []
        self.prestage_breakdown_ms = {"download": 0.0, "render_square": 0.0, "upload": 0.0, "ready_readback": 0.0}
        for row in selected:
            source = by_id.get(str(row.get("asset_drive_id") or ""))
            if not source:
                raise DailyBlocked("prestage", "selected Drive asset disappeared", {"asset_id": row.get("asset_id")})
            vertical = work_dir / "vertical" / str(row.get("canonical_filename"))
            square = work_dir / "square" / f"{Path(str(row.get('canonical_filename'))).stem}__SQUARE.mp4"
            started = time.perf_counter()
            drive_readback = download_drive_file(self.drive_token, source, vertical)
            self.prestage_breakdown_ms["download"] += round((time.perf_counter() - started) * 1000, 3)
            clean = verify_clean(vertical)
            if clean["sha256"] != str(row.get("clean_checksum") or ""):
                raise DailyBlocked("prestage", "inventory checksum drift", {"asset_id": row.get("asset_id")})
            started = time.perf_counter()
            square_readback = make_square_clean(vertical, square)
            self.prestage_breakdown_ms["render_square"] += round((time.perf_counter() - started) * 1000, 3)
            vertical_title = media_title("VERTICAL", str(row["asset_id"]), clean["sha256"])
            square_title = media_title("SQUARE", str(row["asset_id"]), clean["sha256"])
            vertical_id = (existing_by_title.get(vertical_title) or [None])[0]
            square_id = (existing_by_title.get(square_title) or [None])[0]
            if not vertical_id:
                started = time.perf_counter()
                count_call("meta_video_upload")
                vertical_id = uploader.upload(vertical, vertical_title)
                self.prestage_breakdown_ms["upload"] += round((time.perf_counter() - started) * 1000, 3)
            if not square_id:
                started = time.perf_counter()
                count_call("meta_video_upload")
                square_id = uploader.upload(square, square_title)
                self.prestage_breakdown_ms["upload"] += round((time.perf_counter() - started) * 1000, 3)
            started = time.perf_counter()
            count_call("meta_ready_wait")
            processing = uploader.wait_ready([str(vertical_id), str(square_id)])
            self.prestage_breakdown_ms["ready_readback"] += round((time.perf_counter() - started) * 1000, 3)
            if any((processing.get(str(video_id)) or {}).get("ready") is not True for video_id in (vertical_id, square_id)):
                raise DailyBlocked("prestage", "dual-video ready readback failed", {"asset_id": row.get("asset_id")})
            count_call("meta_association_readback")
            association = uploader.verify_association([str(vertical_id), str(square_id)])
            if any((association.get(str(video_id)) or {}).get("associated") is not True for video_id in (vertical_id, square_id)):
                raise DailyBlocked("prestage", "dual-video ad-account association readback failed", {"asset_id": row.get("asset_id")})
            record = registry.register(
                account_id=ACCOUNT_ID,
                asset_id=str(row["asset_id"]),
                checksum=clean["sha256"],
                vertical_video_id=str(vertical_id),
                square_video_id=str(square_id),
                ready=True,
                source="v3-daily-ad-account-meta-readback",
                upload_edge="ad_account_advideos",
                association_verified=True,
            )
            registry_readback = registry.require_ready(ACCOUNT_ID, str(row["asset_id"]), clean["sha256"])
            if str(registry_readback.get("vertical_video_id")) != str(vertical_id) or str(registry_readback.get("square_video_id")) != str(square_id):
                raise DailyBlocked("prestage", "media registry readback mismatch", {"asset_id": row.get("asset_id")})
            prepared.append({"asset_id": row["asset_id"], "vertical": str(vertical), "square": str(square), "drive": source, "drive_readback": drive_readback, "clean": clean, "square_readback": square_readback, "registry": record})
        return prepared

    def execute_engine(self, sealed: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.from_dict(sealed)
        engine = CampaignEngine(config, transport_factory=real_transport_factory(config, manifest))
        count_call("engine_execute")
        return engine.execute(manifest)

    def hierarchy_readback(self, campaign_id: str) -> dict[str, Any]:
        if not self.token:
            raise DailyBlocked("readback", "Meta token not initialized")
        count_call("meta_get")
        campaign_status, campaign, _ = self.common.graph_get(campaign_id, self.token, {"fields": "id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time"})
        adsets = self._graph_pages(f"{campaign_id}/adsets", {"fields": "id,name,status,effective_status,configured_status,start_time", "limit": 20})
        ads = self._graph_pages(
            f"{campaign_id}/ads",
            {
                "fields": "id,name,status,effective_status,configured_status,adset_id,source_ad_id,issues_info,creative{id,name,status,effective_object_story_id,asset_feed_spec}",
                "limit": 50,
            },
        )
        if campaign_status != 200 or not isinstance(campaign, dict):
            raise DailyBlocked("readback", "campaign readback failed", {"campaign_id": campaign_id, "http": campaign_status})
        return {"campaign": campaign, "adsets": adsets, "ads": ads}

    def move_asset(self, drive_row: dict[str, Any]) -> dict[str, Any]:
        if not self.drive_token:
            raise DailyBlocked("drive_move", "Drive token not initialized")
        return move_to_testing(self.drive_token, drive_row)


def validate_hierarchy(readback: dict[str, Any], campaign: Any) -> dict[str, Any]:
    live = readback.get("campaign") or {}
    adsets = readback.get("adsets") or []
    ads = readback.get("ads") or []
    campaign_ok = (
        str(live.get("name") or "") == campaign.name
        and str(live.get("status") or live.get("configured_status") or "").upper() == campaign.status
        and int(str(live.get("daily_budget") or "0")) == int(str(campaign.campaign_updates.get("daily_budget") or "0"))
        and str(live.get("start_time") or "")[:16] == str(campaign.start_time)[:16]
    )
    adsets_ok = len(adsets) == 1 and str(adsets[0].get("status") or adsets[0].get("configured_status") or "").upper() == "ACTIVE"
    ads_ok = len(ads) == 3 and all(
        str(row.get("status") or row.get("configured_status") or "").upper() == "ACTIVE"
        and not row.get("issues_info")
        for row in ads
    )
    creatives_ok = len(ads) == 3 and all(
        str(((row.get("creative") or {}).get("status") or "")).upper() == "ACTIVE"
        and bool(str((row.get("creative") or {}).get("effective_object_story_id") or ""))
        for row in ads
    )
    return {
        "valid": campaign_ok and adsets_ok and ads_ok and creatives_ok,
        "campaign_ok": campaign_ok,
        "adsets_ok": adsets_ok,
        "ads_ok": ads_ok,
        "creatives_ok": creatives_ok,
    }


def assignments_from_readback(manifest: Manifest, campaign_ids: list[str], readbacks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    def labels(video: dict[str, Any]) -> set[str]:
        return {
            str(value)
            for row in (video.get("adlabels") or [])
            for value in (row.get("id"), row.get("name"))
            if value
        }

    def materialized_video_id(expected: dict[str, Any], live_videos: list[dict[str, Any]]) -> str:
        expected_labels = labels(expected)
        matches = [row for row in live_videos if expected_labels and labels(row) & expected_labels]
        if len(matches) != 1 or not str(matches[0].get("video_id") or ""):
            raise DailyBlocked("readback", "materialized video label mapping failed", {"expected_labels": sorted(expected_labels)})
        return str(matches[0]["video_id"])

    assignments: list[dict[str, Any]] = []
    for campaign, campaign_id in zip(manifest.campaigns, campaign_ids):
        readback = readbacks[campaign_id]
        if not validate_hierarchy(readback, campaign)["valid"]:
            raise DailyBlocked("readback", "campaign hierarchy validation failed", {"campaign_id": campaign_id})
        adset_id = str((readback["adsets"][0] or {}).get("id") or "")
        ads_by_name = {str(row.get("name") or ""): row for row in readback.get("ads") or []}
        for ad in campaign.ads:
            live_ad = ads_by_name.get(ad.name)
            if not live_ad:
                raise DailyBlocked("readback", "ad name missing from readback", {"campaign_id": campaign_id, "ad_name": ad.name})
            if str(live_ad.get("source_ad_id") or "") != ad.source_ad_id:
                raise DailyBlocked("readback", "ad source lineage mismatch", {"campaign_id": campaign_id, "ad_name": ad.name})
            creative = live_ad.get("creative") or {}
            expected_videos = list(((ad.creative_payload.get("asset_feed_spec") or {}).get("videos") or []))
            live_videos = list(((creative.get("asset_feed_spec") or {}).get("videos") or []))
            if len(expected_videos) != 2 or len(live_videos) != 2:
                raise DailyBlocked("readback", "dual-video materialization readback failed", {"campaign_id": campaign_id, "ad_name": ad.name})
            assignments.append({
                "asset_id": ad.media.asset_id,
                "campaign_id": campaign_id,
                "adset_id": adset_id,
                "ad_id": str(live_ad.get("id") or ""),
                "creative_id": str(creative.get("id") or ""),
                "source_ad_id": ad.source_ad_id,
                "effective_object_story_id": str(creative.get("effective_object_story_id") or ""),
                "prestage_vertical_video_id": ad.media.vertical_video_id,
                "prestage_square_video_id": ad.media.square_video_id,
                "vertical_video_id": materialized_video_id(expected_videos[0], live_videos),
                "square_video_id": materialized_video_id(expected_videos[1], live_videos),
            })
    return assignments


def update_operation_after_creation(
    path: Path,
    manifest: Manifest,
    campaign_ids: list[str],
    operational_date: date,
    *,
    complete_request: bool = True,
) -> None:
    operation = load_json(path)
    scope = ((operation.get("management_scope") or {}).get("autonomous_action_scope") or {})
    allowed = scope.setdefault("allowed_campaigns", {})
    for campaign, campaign_id in zip(manifest.campaigns, campaign_ids):
        number = parse_campaign_number(campaign.name)
        if number is None:
            raise DailyBlocked("operation_update", "manifest campaign number is missing")
        allowed[f"{number:02d}"] = {"campaign_id": campaign_id, "cycle_start_date": (operational_date + timedelta(days=1)).isoformat(), "source": "campaign_engine_v3_daily_readback", "request_id": manifest.request_id}
    numbering = operation.setdefault("campaign_numbering_policy", {})
    numbers = [parse_campaign_number(campaign.name) for campaign in manifest.campaigns]
    numbering["next_required_campaign_number"] = max(number for number in numbers if number is not None) + 1
    override = (operation.get("daily_new_campaign_routine") or {}).get(f"one_time_override_{operational_date:%Y%m%d}")
    if complete_request and isinstance(override, dict):
        override["status"] = "completed_validated"
        override["completed_at_utc"] = utc_now()
    atomic_json(path, operation, sort_keys=False)
    readback = load_json(path)
    if int((readback.get("campaign_numbering_policy") or {}).get("next_required_campaign_number") or 0) != numbering["next_required_campaign_number"]:
        raise DailyBlocked("operation_update", "operation config readback failed")


def auto_arm_first_delivery_campaigns(
    campaign_ids: list[str],
    operational_start_date: date,
    request_id: str,
    *,
    script: Path = FIRST_DELIVERY_GUARDRAIL_SCRIPT,
) -> dict[str, Any]:
    """Register newly validated campaigns in the one-shot first-delivery watcher."""
    command = [
        "python3",
        str(script),
        "--auto-arm",
        "--operational-date",
        operational_start_date.isoformat(),
        "--request-id",
        request_id,
    ]
    for campaign_id in campaign_ids:
        command.extend(["--campaign-id", str(campaign_id)])
    proc = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise DailyBlocked(
            "first_delivery_guardrail",
            "new campaigns could not be enrolled in the first-delivery watcher",
            {"campaign_ids": list(campaign_ids), "safe_error": proc.stderr.strip()[-700:]},
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise DailyBlocked("first_delivery_guardrail", "first-delivery watcher returned invalid JSON") from exc
    if (
        payload.get("status") != "AUTO_ARMED"
        or set(str(item) for item in payload.get("campaign_ids") or []) != set(str(item) for item in campaign_ids)
        or int(payload.get("armed_count") or 0) != len(campaign_ids)
        or int(payload.get("meta_writes") or 0) != 0
    ):
        raise DailyBlocked(
            "first_delivery_guardrail",
            "first-delivery watcher enrollment readback mismatch",
            {"campaign_ids": list(campaign_ids), "result": payload},
        )
    return payload


def run_daily(
    *,
    paths: DailyPaths = DailyPaths(),
    now_sp: datetime | None = None,
    gate: bool = False,
    post_report: bool = False,
    quiet: bool = False,
    plan_only: bool = False,
    backend_factory: Callable[[DailyPaths], Any] = LiveDailyBackend,
) -> dict[str, Any]:
    current = now_sp.astimezone(SP) if now_sp else datetime.now(SP)
    state = load_json(paths.state) if paths.state.exists() else {}
    operational_date = request_operational_date(current, state)
    day = operational_date.isoformat()
    if gate and not gate_due(current, state):
        return {"status": "SILENT_NOT_DUE", "operational_date_sp": day}
    paths.lock.parent.mkdir(parents=True, exist_ok=True)
    with paths.lock.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = {} if plan_only else (load_json(paths.state) if paths.state.exists() else {})
        operational_date = request_operational_date(current, state)
        day = operational_date.isoformat()
        state = rollover_completed_state(state, day)
        if state.get("completed_operational_date_sp") == day:
            return {"status": "ALREADY_COMPLETE", "operational_date_sp": day, "audit": state.get("audit_path")}
        total_started = time.perf_counter()
        call_counter: dict[str, int] = {}
        call_counter_token = _CALL_COUNTER.set(call_counter)
        request_id = (
            f"cpv-daily-{operational_date:%Y%m%d}-dry-run"
            if plan_only
            else str(state.get("request_id") or f"cpv-daily-{operational_date:%Y%m%d}")
        )
        audit_path = Path(state.get("audit_path") or (paths.audit_root / f"{request_id}.json"))
        audit = load_json(audit_path) if audit_path.exists() else {"schema_version": 3, "kind": "cpv_daily_v3", "request_id": request_id, "operational_date_sp": day, "created_at_utc": utc_now(), "stage": "INITIALIZING", "side_effects": {"campaign_write": False, "media_upload": False, "drive_move": False}}
        if audit.get("failure"):
            audit.setdefault("attempt_history", []).append({
                "stage": audit.get("stage"),
                "failed_at_utc": audit.get("failed_at_utc"),
                "failure": audit.get("failure"),
            })
            audit.pop("failure", None)
            audit.pop("failed_at_utc", None)
        if audit.get("observability"):
            audit.setdefault("observability_attempts", []).append(audit["observability"])
        init_observability(audit)
        atomic_json(audit_path, audit)
        backend = backend_factory(paths)
        inventory_rows = [json.loads(line) for line in paths.inventory.read_text(encoding="utf-8").splitlines() if line.strip()]
        selected_ids = set(str(item) for item in state.get("selected_asset_ids") or [])
        selected = [row for row in inventory_rows if str(row.get("asset_id") or "") in selected_ids]
        writer_leases: AccountWriterLeaseStore | None = None
        try:
            operation = load_json(paths.operation)
            config = load_json(paths.config)
            validate_engine_config(config)
            if not plan_only:
                writer_leases = AccountWriterLeaseStore(config["state_root"])
                writer_leases.claim(ACCOUNT_ID, request_id, status="PREFLIGHT_ACTIVE")
            desired_count = int(state.get("desired_campaign_count") or requested_campaign_count(operation, operational_date))
            phase_started, phase_calls = phase_begin(call_counter)
            meta = backend.meta_preflight()
            phase_end(audit, "meta_preflight", phase_started, phase_calls, call_counter)
            checkpoint_campaign_ids = recovery_checkpoint_campaign_ids(config, request_id)
            completed_before = len(set(str(item) for item in state.get("campaign_ids") or []) | set(checkpoint_campaign_ids))
            if state.get("campaign_count"):
                count = int(state["campaign_count"])
                budget = resume_budget_plan(meta["campaigns"], count, completed_before, operation)
            else:
                budget = enforce_budget_cap(meta["campaigns"], desired_count, operation)
                count = int(budget["selected_count"])
            numbers = list(state.get("campaign_numbers") or next_campaign_numbers(meta["campaigns"], count, operation))
            phase_started, phase_calls = phase_begin(call_counter)
            drive_info = backend.drive_preflight()
            drive = drive_info["drive"]
            phase_end(audit, "drive_preflight", phase_started, phase_calls, call_counter)
            assets_were_reserved = bool(selected_ids)
            if not selected:
                phase_started, phase_calls = phase_begin(call_counter)
                reconciliation_payload = backend.refresh_reconciliation(inventory_rows, drive, current)
                phase_end(audit, "reconciliation", phase_started, phase_calls, call_counter)
                phase_started, phase_calls = phase_begin(call_counter)
                selected = select_assets(
                    inventory_rows,
                    {
                        str(row.get("id") or "")
                        for row in drive.get("files") or []
                        if row.get("location") in {"01_READY", "03_TESTED"}
                    },
                    count * 3,
                    reconciliation=reconciliation_payload,
                    mix_policy={
                        **(((operation.get("creative_performance_lifecycle") or {}).get("retest") or {}).get("selection_mix") or {}),
                        "max_test_attempts": int((((operation.get("creative_performance_lifecycle") or {}).get("retest") or {}).get("max_test_attempts") or 2)),
                    },
                )
                reconciliation = verify_reconciliation(paths.reconciliation, selected, current)
                phase_end(audit, "asset_selection", phase_started, phase_calls, call_counter, detail={"selected": len(selected)})
            else:
                phase_started, phase_calls = phase_begin(call_counter)
                reconciliation = verify_reconciliation(paths.reconciliation, selected, current)
                phase_end(audit, "reconciliation", phase_started, phase_calls, call_counter, detail={"resume_validation": True})

            assets_payload = {
                "assets": [
                    {
                        "asset_id": str(row["asset_id"]),
                        "checksum": str(row["clean_checksum"]),
                        "canonical_filename": str(row["canonical_filename"]),
                    }
                    for row in selected
                ]
            }
            manifest_dir = paths.work_root / request_id / "manifest"
            draft_path = manifest_dir / "draft.json"
            sealed_path = manifest_dir / "sealed.json"
            source_snapshot_path = Path(
                state.get("source_snapshot_path")
                or (paths.work_root / request_id / "source-selection.json")
            )
            source_payload: dict[str, Any] = {}
            source_selections: list[dict[str, Any]] = []
            source_summary: list[dict[str, Any]] = []
            phase_started, phase_calls = phase_begin(call_counter)
            if sealed_path.exists():
                existing_sealed = load_json(sealed_path)
                source_summary = list(existing_sealed.get("source_selections") or [])
                source_detail = {"reused_sealed_manifest": True, "campaigns": len(existing_sealed.get("campaigns") or [])}
            else:
                if state.get("source_snapshot_path") and not source_snapshot_path.exists():
                    raise DailyBlocked("source_selection", "persisted source snapshot is missing; refusing to reselect implicitly")
                if source_snapshot_path.exists():
                    source_payload = load_json(source_snapshot_path)
                else:
                    source_payload = backend.select_clone_sources(
                        asset_refs=assets_payload["assets"],
                        campaign_count=count,
                        meta_campaigns=meta["campaigns"],
                        target_date=day,
                        operation=operation,
                        request_id=request_id,
                    )
                    if not plan_only:
                        atomic_json(source_snapshot_path, source_payload)
                if str(source_payload.get("request_id") or "") != request_id or str(source_payload.get("target_date") or "") != day:
                    raise DailyBlocked("source_selection", "source snapshot identity mismatch")
                source_selections = expand_source_selections(source_payload)
                source_summary = [
                    {
                        "vehicle_type": vehicle_type,
                        "source_campaign_id": source.get("source_campaign_id"),
                        "source_campaign_name": (source.get("source_campaign") or {}).get("name"),
                        "source_adset_id": source.get("source_adset_id"),
                        "roi_evidence": source.get("roi_evidence") or {},
                    }
                    for vehicle_type, source in sorted((source_payload.get("sources_by_vehicle") or {}).items())
                ]
                source_digest = hashlib.sha256(
                    json.dumps(source_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                if state.get("source_selection_digest") and state.get("source_selection_digest") != source_digest:
                    raise DailyBlocked("source_selection", "persisted source snapshot digest mismatch")
                source_detail = {"campaigns": count, "vehicle_types": source_payload.get("campaign_vehicle_types"), "digest": source_digest}
            phase_end(audit, "source_selection", phase_started, phase_calls, call_counter, detail=source_detail)

            if plan_only:
                result = {
                    "status": "DRY_RUN_OK",
                    "operational_date_sp": day,
                    "campaign_count": count,
                    "desired_campaign_count": desired_count,
                    "campaign_numbers": numbers,
                    "planner_bundles": [2] * (count // 2) + ([1] if count % 2 else []),
                    "budget": budget,
                    "selected_assets": [str(row.get("canonical_filename") or "") for row in selected],
                    "selected_asset_sources": [str(row.get("status") or "") for row in selected],
                    "source_selection": source_summary,
                    "reconciliation": reconciliation,
                    "drive_counts": drive.get("counts") or {},
                    "side_effects": {"inventory_reservation": False, "media_upload": False, "campaign_write": False, "drive_move": False},
                    "audit": str(audit_path),
                }
                audit.update(stage="DRY_RUN_OK", source_selection=source_summary, final=result, completed_at_utc=utc_now())
                atomic_json(audit_path, audit)
                if not quiet:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                return result

            if not assets_were_reserved:
                reserve_inventory(paths.inventory, inventory_rows, selected, audit_path)
                selected_ids = {str(row.get("asset_id") or "") for row in selected}
                state = {
                    "schema_version": 3,
                    "status": "ASSETS_RESERVED",
                    "operational_date_sp": day,
                    "request_id": request_id,
                    "audit_path": str(audit_path),
                    "desired_campaign_count": desired_count,
                    "campaign_count": count,
                    "campaign_numbers": numbers,
                    "selected_asset_ids": sorted(selected_ids),
                    "reconciliation": reconciliation,
                    "budget_plan": budget,
                    "source_snapshot_path": str(source_snapshot_path),
                    "source_selection_digest": source_detail.get("digest"),
                    "source_selection_summary": source_summary,
                    "updated_at_utc": utc_now(),
                }
                atomic_json(paths.state, state)
            elif source_payload:
                state.update(
                    source_snapshot_path=str(source_snapshot_path),
                    source_selection_digest=source_detail.get("digest"),
                    source_selection_summary=source_summary,
                    updated_at_utc=utc_now(),
                )
                atomic_json(paths.state, state)
            audit["source_selection"] = source_summary
            atomic_json(audit_path, audit)
            phase_started, phase_calls = phase_begin(call_counter)
            registry = MediaRegistry(paths.registry)
            ready = []
            for row in selected:
                try:
                    registry.require_ready(ACCOUNT_ID, str(row["asset_id"]), str(row["clean_checksum"]))
                    ready.append(str(row["asset_id"]))
                except Exception:
                    pass
            if len(ready) != len(selected):
                work_dir = paths.work_root / request_id
                work_dir.mkdir(parents=True, exist_ok=True)
                audit["side_effects"]["media_upload"] = True
                audit["stage"] = "MEDIA_UPLOAD_IN_FLIGHT"
                atomic_json(audit_path, audit)
                prepared = backend.prepare_and_prestage(selected, drive, work_dir, registry)
                audit["prepared_assets"] = [{"asset_id": item["asset_id"], "clean": item["clean"], "square": item["square_readback"], "registry": item["registry"]} for item in prepared]
                audit["stage"] = "MEDIA_READY"
                atomic_json(audit_path, audit)
                state.update(status="MEDIA_READY", updated_at_utc=utc_now())
                atomic_json(paths.state, state)
            phase_end(
                audit,
                "prestage",
                phase_started,
                phase_calls,
                call_counter,
                detail={"assets": len(selected), "breakdown_ms": getattr(backend, "prestage_breakdown_ms", {})},
            )
            phase_started, phase_calls = phase_begin(call_counter)
            manifest_dir.mkdir(parents=True, exist_ok=True)
            if sealed_path.exists():
                sealed = load_json(sealed_path)
            else:
                if not source_selections:
                    raise DailyBlocked("source_selection", "ROI-selected source is missing before manifest materialization")
                draft = build_cpv_manifest(
                    registry=registry,
                    asset_refs=assets_payload["assets"],
                    campaign_numbers=[int(item) for item in numbers],
                    operational_date=day,
                    request_id=request_id,
                    source_selections=source_selections,
                    status="ACTIVE",
                    daily_budget_minor=int(budget["initial_minor"]),
                )
                atomic_json(draft_path, draft)
                sealed = prevalidate_payload(draft, registry)
                atomic_json(sealed_path, sealed)
                state.update(status="MANIFEST_SEALED", manifest_path=str(sealed_path), manifest_digest=sealed["prevalidation"]["content_digest"], updated_at_utc=utc_now())
                atomic_json(paths.state, state)
                audit.update(stage="MANIFEST_SEALED", manifest_path=str(sealed_path), manifest_digest=sealed["prevalidation"]["content_digest"], campaign_numbers=numbers, budget=budget)
                atomic_json(audit_path, audit)
            manifest = Manifest.from_dict(sealed)
            phase_end(audit, "manifest_prevalidation", phase_started, phase_calls, call_counter, detail={"prevalidated": True, "campaigns": len(manifest.campaigns)})
            collisions = campaign_name_collisions(
                manifest,
                meta["campaigns"],
                {str(item) for item in state.get("campaign_ids") or []} | set(checkpoint_campaign_ids),
            )
            if collisions:
                raise DailyBlocked(
                    "campaign_collision",
                    "exact manifest campaign name already exists without idempotent request mapping",
                    {"collisions": collisions, "manual_reconciliation_required": True},
                )
            audit["side_effects"]["campaign_write"] = True
            audit["stage"] = "ENGINE_IN_FLIGHT"
            atomic_json(audit_path, audit)
            phase_started, phase_calls = phase_begin(call_counter)
            result = backend.execute_engine(sealed, config)
            phase_end(audit, "engine", phase_started, phase_calls, call_counter, detail={"status": result.get("status"), "metrics": result.get("metrics") or {}})
            audit["engine_result"] = result
            audit["stage"] = result.get("status")
            atomic_json(audit_path, audit)
            campaign_ids = [str(item) for item in result.get("campaign_ids") or []]
            processed_ids = set(str(item) for item in state.get("postprocessed_campaign_ids") or [])
            pending_ids = [item for item in campaign_ids if item not in processed_ids]
            if pending_ids:
                phase_started, phase_calls = phase_begin(call_counter)
                indexed_pairs = [
                    (index, campaign_id)
                    for index, campaign_id in enumerate(campaign_ids)
                    if campaign_id in pending_ids
                ]
                manifest_subset = Manifest.from_dict({
                    **manifest.raw,
                    "campaigns": [manifest.raw["campaigns"][index] for index, _ in indexed_pairs],
                })
                pending_order = [campaign_id for _, campaign_id in indexed_pairs]
                readbacks = {campaign_id: backend.hierarchy_readback(campaign_id) for campaign_id in pending_order}
                assignments = assignments_from_readback(manifest_subset, pending_order, readbacks)
                inventory_rows = [json.loads(line) for line in paths.inventory.read_text(encoding="utf-8").splitlines() if line.strip()]
                drive_by_asset = {str(row.get("asset_id") or ""): row for row in selected}
                drive_rows = {str(row.get("id") or ""): row for row in drive.get("files") or []}
                moves: dict[str, dict[str, Any]] = {}
                audit["side_effects"]["drive_move"] = True
                audit["stage"] = "POSTPROCESS_IN_FLIGHT"
                atomic_json(audit_path, audit)
                for assignment in assignments:
                    inventory_row = drive_by_asset[assignment["asset_id"]]
                    drive_row = drive_rows[str(inventory_row["asset_drive_id"])]
                    moves[str(inventory_row["asset_drive_id"])] = backend.move_asset(drive_row)
                update_inventory_assignments(paths.inventory, inventory_rows, assignments, moves, audit_path)
                update_operation_after_creation(
                    paths.operation,
                    manifest_subset,
                    pending_order,
                    operational_date,
                    complete_request=False,
                )
                state.update(
                    status="FIRST_DELIVERY_ARM_IN_FLIGHT",
                    campaign_ids=campaign_ids,
                    first_delivery_pending_ids=pending_order,
                    updated_at_utc=utc_now(),
                )
                atomic_json(paths.state, state)
                first_delivery = auto_arm_first_delivery_campaigns(
                    pending_order,
                    operational_date + timedelta(days=1),
                    request_id,
                )
                armed_ids = set(str(item) for item in state.get("first_delivery_armed_campaign_ids") or [])
                armed_ids.update(pending_order)
                state["first_delivery_armed_campaign_ids"] = sorted(armed_ids)
                state.pop("first_delivery_pending_ids", None)
                audit.setdefault("first_delivery_guardrail", []).append(first_delivery)
                processed_ids.update(pending_ids)
                state["postprocessed_campaign_ids"] = sorted(processed_ids)
                state["status"] = "POSTPROCESSED"
                state["updated_at_utc"] = utc_now()
                atomic_json(paths.state, state)
                audit.setdefault("assignments", []).extend(assignments)
                audit.setdefault("drive_moves", {}).update(moves)
                audit["side_effects"]["drive_move"] = bool(moves)
                phase_end(
                    audit,
                    "postprocess",
                    phase_started,
                    phase_calls,
                    call_counter,
                    detail={"campaigns": len(pending_ids), "assets": len(assignments), "first_delivery_armed": len(pending_order)},
                )
                atomic_json(audit_path, audit)
            if result.get("status") == "PARTIAL_DEFERRED_QUOTA":
                retry_after = int(time.time()) + max(60, int(result.get("retry_after_seconds") or 300))
                state.update(status="PARTIAL_DEFERRED_QUOTA", retry_after_epoch=retry_after, campaign_ids=campaign_ids, updated_at_utc=utc_now())
                atomic_json(paths.state, state)
                message = f"🟡 V3 PARCIAL — CPV G006 — {operational_date:%d/%m}\n{len(campaign_ids)}/{count} campanhas concluídas e validadas. O mesmo request será retomado após a janela de quota, sem replay."
                if post_report:
                    audit["discord_readback"] = post_discord(message)
                    atomic_json(audit_path, audit)
                return {"status": "PARTIAL_DEFERRED_QUOTA", "campaign_ids": campaign_ids, "retry_after_epoch": retry_after, "audit": str(audit_path)}
            if len(campaign_ids) != count or len(processed_ids) != count:
                raise DailyBlocked("completion", "engine completed without the full validated campaign set", {"campaign_ids": campaign_ids, "processed": sorted(processed_ids), "count": count})
            update_operation_after_creation(paths.operation, manifest, campaign_ids, operational_date, complete_request=True)
            inventory_rows = [json.loads(line) for line in paths.inventory.read_text(encoding="utf-8").splitlines() if line.strip()]
            drive_after = backend.drive_preflight()["drive"]
            stock = stock_counts(inventory_rows, drive_after)
            budget_after = account_budget_summary(budget)
            final = {"status": "COMPLETE_FUTURE_ACTIVE", "request_id": request_id, "campaign_numbers": numbers, "campaign_ids": campaign_ids, "start_time_sp": (operational_date + timedelta(days=1)).isoformat() + "T00:30:00-03:00", "assets_used": len(selected), "stock_remaining": stock, "account_budget_after_creation": budget_after, "audit": str(audit_path)}
            audit.update(stage="COMPLETE", final=final, completed_at_utc=utc_now())
            atomic_json(audit_path, audit)
            state = finalize_completed_state(
                state,
                status="COMPLETE",
                completed_operational_date_sp=day,
                campaign_ids=campaign_ids,
                stock_remaining=stock,
                updated_at_utc=utc_now(),
            )
            atomic_json(paths.state, state)
            if writer_leases is not None:
                writer_leases.release(ACCOUNT_ID, request_id)
            if post_report:
                labels = ", ".join(f"C{number:02d}" for number in numbers)
                audit["discord_readback"] = post_discord(
                    f"✅ V3 CONCLUÍDO — CPV G006 — {operational_date:%d/%m}\n"
                    f"{labels} · USD {usd_minor_label(budget['initial_minor'])} cada · 1×1×3 · ACTIVE com início futuro 00:30 SP\n"
                    f"Budget ativo: USD {usd_minor_label(budget_after['active_minor'])} · restante: USD {usd_minor_label(budget_after['remaining_minor'])} / cap USD {usd_minor_label(budget_after['cap_minor'])}\n"
                    f"Criativos novos: {len(selected)} · estoque elegível restante: {stock['eligible_unique_creatives']}"
                )
                atomic_json(audit_path, audit)
            if not quiet:
                print(json.dumps(final, ensure_ascii=False, indent=2))
            return final
        except Exception as exc:
            failure = safe_error(exc)
            known_campaign_ids = bool(state.get("campaign_ids") or (audit.get("engine_result") or {}).get("campaign_ids"))
            failure_status, _ = failure_resume_state(audit.get("side_effects") or {}, known_campaign_ids=known_campaign_ids)
            authorization = corrective_write_authorization()
            audit.update(stage=failure_status, failure=failure, failed_at_utc=utc_now(), manual_reconciliation_required=False, automatic_recovery_required=True, operator_authorization=authorization)
            atomic_json(audit_path, audit)
            if failure_status == "FAILED" and selected_ids:
                inventory_rows = [json.loads(line) for line in paths.inventory.read_text(encoding="utf-8").splitlines() if line.strip()]
                release_inventory(paths.inventory, inventory_rows, selected_ids)
            if not plan_only:
                state.update(
                    status=failure_status,
                    failure=failure,
                    retry_after_epoch=int(time.time()) + max(
                        5,
                        int((failure.get("detail") or {}).get("recommended_retry_after_seconds") or 300),
                    ),
                    manual_reconciliation_required=False,
                    automatic_recovery_required=True,
                    operator_authorization=authorization,
                    updated_at_utc=utc_now(),
                )
                atomic_json(paths.state, state)
                if writer_leases is not None:
                    writer_leases.mark(ACCOUNT_ID, request_id, failure_status)
            if post_report:
                try:
                    post_discord(discord_failure_message(failure, failure_status, operational_date, list(state.get("campaign_numbers") or [])))
                except Exception:
                    pass
            if not quiet:
                print(json.dumps({"status": failure_status, "failure": failure, "manual_reconciliation_required": False, "automatic_recovery_required": True, "operator_authorization": authorization, "audit": str(audit_path)}, ensure_ascii=False, indent=2))
            return {"status": failure_status, "failure": failure, "manual_reconciliation_required": False, "automatic_recovery_required": True, "operator_authorization": authorization, "audit": str(audit_path)}
        finally:
            audit.setdefault("observability", {})["total"] = {
                "duration_ms": round((time.perf_counter() - total_started) * 1000, 3),
                "calls": {key: int(value) for key, value in sorted(call_counter.items())},
            }
            atomic_json(audit_path, audit)
            _CALL_COUNTER.reset(call_counter_token)
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def offline_smoke(campaign_count: int = 3) -> dict[str, Any]:
    """Exercise v3 planning, sealing and resumable execution without network or production paths."""
    if campaign_count != 3:
        raise ValueError("offline smoke currently validates the required three-campaign 2+1 route")
    with tempfile.TemporaryDirectory(prefix="ares-cpv-v3-offline-") as raw:
        root = Path(raw)
        registry = MediaRegistry(root / "media.json")
        assets = []
        for index in range(campaign_count * 3):
            asset_id = f"offline-asset-{index + 1:02d}"
            checksum = f"offline-sha256-{index + 1:02d}"
            registry.register(
                account_id=ACCOUNT_ID,
                asset_id=asset_id,
                checksum=checksum,
                vertical_video_id=f"offline-v-{index + 1:02d}",
                square_video_id=f"offline-s-{index + 1:02d}",
                ready=True,
                source="offline-smoke",
                upload_edge="ad_account_advideos",
                association_verified=True,
            )
            assets.append({
                "asset_id": asset_id,
                "checksum": checksum,
                "canonical_filename": f"CAR_BR_BR_VID_OFFLINE_PV_{index + 1:03d}.mp4",
            })
        operational_date = datetime.now(SP).date().isoformat()
        templates = [
            {
                "source_ad_id": f"offline-source-ad-{index + 1}",
                "creative_payload": {
                    "object_story_spec": {"page_id": PAGE_ID},
                    "asset_feed_spec": {"videos": []},
                },
            }
            for index in range(3)
        ]
        draft = build_cpv_manifest(
            registry=registry,
            asset_refs=assets,
            campaign_numbers=[14, 15, 16],
            operational_date=operational_date,
            request_id=f"offline-cpv-{operational_date.replace('-', '')}",
            source_selections=[
                {
                    "vehicle_type": "CARRO",
                    "source_campaign_id": "offline-source-campaign",
                    "source_adset_id": "offline-source-adset",
                    "templates": templates,
                    "roi_evidence": {"roi_pct": 1.0, "target_date": operational_date, "currency": "USD"},
                }
                for _ in range(3)
            ],
            status="ACTIVE",
        )
        sealed = prevalidate_payload(draft, registry)
        manifest = Manifest.from_dict(sealed)
        config = {
            "engine_version": 3,
            "enabled": True,
            "write_enabled": True,
            "require_prevalidated_manifest": True,
            "bundle_size": 2,
            "max_ads_per_batch": 10,
            "max_account_workers": 8,
            "soft_score": 60,
            "hard_score": 60,
            "score_window_seconds": 300,
            "development_access_readback_cooldown_seconds": 305,
            "quota_retry_safety_seconds": 5,
            "readback_recovery_points_per_campaign": 3,
            "points_per_mode": {"pure_clone": 30, "clone_prestaged": 30},
            "state_root": str(root / "state"),
            "audit_root": str(root / "audit"),
        }
        transport = FakeBatchTransport(ACCOUNT_ID)
        engine = CampaignEngine(config, transport_factory=lambda account: transport)
        first = engine.execute(manifest)
        if first.get("status") != "PARTIAL_DEFERRED_QUOTA" or len(first.get("campaign_ids") or []) != 0:
            raise RuntimeError("offline first wave did not defer the two-campaign readback after persisting writes")
        lane_files = list((root / "state").glob("lane-*.json"))
        if len(lane_files) != 1:
            raise RuntimeError("offline lane state missing")
        lane = load_json(lane_files[0])
        lane.update(events=[], reservations={}, points=0)
        atomic_json(lane_files[0], lane)
        second = engine.execute(manifest)
        if second.get("status") != "COMPLETE_FUTURE_ACTIVE" or len(second.get("campaign_ids") or []) != 3:
            raise RuntimeError("offline resume did not complete the third campaign")
        return {
            "status": "OFFLINE_SMOKE_OK",
            "campaign_count": 3,
            "planner": [2, 1],
            "first_status": first["status"],
            "first_campaigns": len(first["campaign_ids"]),
            "first_stage": "two_campaign_writes_persisted_readback_deferred",
            "final_status": second["status"],
            "final_campaigns": len(second["campaign_ids"]),
            "unique_campaign_ids": len(set(second["campaign_ids"])),
            "intermediate_get_calls": second["metrics"]["intermediate_get_calls"],
            "external_network_calls": 0,
        }
