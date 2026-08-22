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
from .engine import CampaignEngine
from .media_registry import MediaRegistry
from .prestage import PageVideoUploader
from .prevalidation import prevalidate_payload
from .schema import Manifest
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
THREAD_CREATION = "1539826050765299872"
COMMON_PATH = BASE / "scripts/ares-meta-common.py"
DRIVE_MODULE_PATH = BASE / "scripts/ares-drive-upload-manual-inventory.py"
SANITIZER = BASE / "scripts/clean-creative-metadata.sh"
CONFIG_PATH = BASE / "data/ares/meta-ads/engine-v3/config.json"
OPERATION_PATH = BASE / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json"
TEMPLATES_PATH = BASE / "data/ares/meta-ads/engine-v3/templates/cpv-c08-source-templates.json"
REGISTRY_PATH = BASE / "data/ares/meta-ads/engine-v3/media-registry.json"
INVENTORY_PATH = BASE / "data/ares/creative-ops/inventory/assets.jsonl"
RECONCILIATION_PATH = BASE / "data/ares/meta-ads/reconciliation/Creditoparaveiculo-BR-CAR-BR.json"
STATE_PATH = BASE / "data/ares/meta-ads/engine-v3/state/cpv-daily.json"
LOCK_PATH = BASE / "data/ares/meta-ads/engine-v3/state/cpv-daily.lock"
AUDIT_ROOT = BASE / "data/ares/meta-ads/engine-v3/audit/daily"
WORK_ROOT = PROFILE / "work/creditoparaveiculo-v3-daily"
FIRST_DELIVERY_GUARDRAIL_SCRIPT = PROFILE / "scripts/creditoparaveiculo-first-delivery-guardrail.py"
PHASE_ORDER = ["meta_preflight", "drive_preflight", "reconciliation", "asset_selection", "prestage", "manifest_prevalidation", "engine", "postprocess"]
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
    templates: Path = TEMPLATES_PATH
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


def is_resume_state(state: dict[str, Any], operational_date: str) -> bool:
    return (
        str(state.get("operational_date_sp") or "") == operational_date
        and str(state.get("status") or "")
        in {
            "ASSETS_RESERVED",
            "MEDIA_READY",
            "MANIFEST_SEALED",
            "PARTIAL_DEFERRED_QUOTA",
            "POSTPROCESS_PENDING",
            "READBACK_DEFERRED",
        }
    )


def gate_due(now_sp: datetime, state: dict[str, Any]) -> bool:
    day = now_sp.date().isoformat()
    if is_resume_state(state, day):
        if state.get("manual_reconciliation_required") is True:
            return False
        retry_after = int(state.get("retry_after_epoch") or 0)
        return retry_after <= int(now_sp.timestamp())
    return now_sp.hour == 17


def rollover_completed_state(state: dict[str, Any], operational_date: str) -> dict[str, Any]:
    """Do not reuse a completed request as the next day's resumable state."""
    completed_day = str(state.get("completed_operational_date_sp") or "")
    if completed_day and completed_day != operational_date:
        return {}
    return state


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
        f"⚠️ V3 BLOQUEADO — CPV G006 — {operational_date:%d/%m}\n"
        f"Objeto: {campaign_label} · criação CBO programada\n"
        f"Etapa: {stage}\n"
        f"Causa: {cause}\n"
        f"Consequência: {consequence}\n"
        f"Solução proposta: {correction}\n"
        "Autorização necessária: Rodolfo ou Nicolas. Até a aprovação, Ares faz somente diagnóstico/readback e não executa write corretivo."
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


def failure_resume_state(side_effects: dict[str, Any], *, known_campaign_ids: bool) -> tuple[str, bool]:
    if side_effects.get("drive_move"):
        return "POSTPROCESS_PENDING", False
    if side_effects.get("campaign_write"):
        return "READBACK_DEFERRED", not known_campaign_ids
    if side_effects.get("media_upload"):
        return "READBACK_DEFERRED", False
    return "FAILED", False


def requested_campaign_count(operation: dict[str, Any], operational_date: date) -> int:
    routine = operation.get("daily_new_campaign_routine") or {}
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


def enforce_budget_cap(campaigns: list[dict[str, Any]], count: int, operation: dict[str, Any]) -> dict[str, int]:
    policy = operation.get("daily_budget_policy") or {}
    cap_minor = int(Decimal(str(policy.get("operational_account_cap_usd") or 0)) * 100)
    initial_minor = int(Decimal(str(policy.get("new_campaign_initial_budget_usd") or 0)) * 100)
    before = active_budget_minor(campaigns)
    if cap_minor <= 0 or initial_minor <= 0:
        raise DailyBlocked("budget_cap", "operational cap or initial campaign budget is invalid")
    available = max(0, cap_minor - before)
    capacity = available // initial_minor
    selected = min(count, capacity)
    if selected < 1:
        raise DailyBlocked(
            "budget_cap",
            "no new campaign fits the operational account cap at the approved initial budget",
            {"active_before_minor": before, "available_minor": available, "initial_minor": initial_minor, "desired_count": count, "capacity": capacity, "cap_minor": cap_minor},
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
        "cap_minor": cap_minor,
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


def select_assets(
    rows: list[dict[str, Any]],
    drive_ids: set[str],
    count: int,
    *,
    reconciliation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    allowed = (
        {str(row.get("asset_id") or ""): row for row in reconciliation.get("assets") or []}
        if reconciliation is not None
        else None
    )
    candidates = [
        row
        for row in rows
        if row.get("vertical") == "CAR"
        and row.get("country") == "BR"
        and row.get("language") == "BR"
        and row.get("format") == "VID"
        and row.get("status") == "01_READY"
        and row.get("metadata_clean") is True
        and row.get("ares_eligible") is True
        and not row.get("used_by")
        and str(row.get("asset_drive_id") or "") in drive_ids
        and (allowed is None or reconciliation_asset_ok(row, allowed))
    ]
    candidates.sort(key=lambda row: (str(row.get("first_seen_at") or ""), str(row.get("canonical_filename") or "")))
    selected: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    for row in candidates:
        fingerprint = str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id") or "")
        if not fingerprint or fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        selected.append(row)
        if len(selected) == count:
            break
    if len(selected) != count:
        raise DailyBlocked(
            "asset_selection",
            "insufficient unique eligible reconciled assets",
            {"required": count, "available_unique": len(selected)},
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
                conflicts.append({"asset_id": row.get("asset_id"), "match_kind": haystack["kind"], "match_id": haystack["id"], "exact_name": exact, "source_sequence": sequence if sequence_match else None})
    return conflicts


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
        ready = one_folder(children, "01_READY", f"drive_{kind}_ready")
        testing = one_folder(children, "02_TESTING", f"drive_{kind}_testing")
        current_ready = [row for row in drive_children(token, ready["id"]) if row.get("mimeType") != FOLDER_MIME]
        current_testing = [row for row in drive_children(token, testing["id"]) if row.get("mimeType") != FOLDER_MIME]
        for row in current_ready:
            row.update(kind=kind, location="01_READY", ready_parent_id=ready["id"], testing_parent_id=testing["id"])
        for row in current_testing:
            row.update(kind=kind, location="02_TESTING", ready_parent_id=ready["id"], testing_parent_id=testing["id"])
        files.extend(current_ready)
        files.extend(current_testing)
        counts[kind] = len(current_ready)
    counts["TOTAL"] = sum(counts.values())
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
    raw = destination.with_suffix(".raw.mp4")
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


def move_to_testing(token: str, source: dict[str, Any]) -> dict[str, Any]:
    if source.get("location") == "02_TESTING" or set(source.get("parents") or []) == {source.get("testing_parent_id")}:
        return {
            "id": source.get("id"),
            "name": source.get("name"),
            "driveId": source.get("driveId"),
            "parents": [source.get("testing_parent_id")],
            "trashed": False,
            "size": source.get("size"),
            "md5Checksum": source.get("md5Checksum"),
            "already_in_testing": True,
        }
    params = urllib.parse.urlencode({"addParents": source["testing_parent_id"], "removeParents": source["ready_parent_id"], "fields": "id,name,driveId,parents,trashed,size,md5Checksum", "supportsAllDrives": "true"})
    result = drive_request(token, "PATCH", f"https://www.googleapis.com/drive/v3/files/{source['id']}?{params}", body=b"{}", content_type="application/json")
    if result.get("driveId") != DRIVE_ID or result.get("trashed") or set(result.get("parents") or []) != {source["testing_parent_id"]} or str(result.get("md5Checksum") or "") != str(source.get("md5Checksum") or ""):
        raise DailyBlocked("drive_move", "Drive move readback failed", {"file_id": source.get("id")})
    return result


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
    return {"ready_folder_total": int((drive.get("counts") or {}).get("TOTAL") or 0), "ready_folder_img": int((drive.get("counts") or {}).get("IMG") or 0), "ready_folder_vid": int((drive.get("counts") or {}).get("VID") or 0), "eligible_unique_creatives": len(unique)}


def reserve_inventory(path: Path, rows: list[dict[str, Any]], selected: list[dict[str, Any]], audit_path: Path) -> None:
    ids = {str(row.get("asset_id") or "") for row in selected}
    for row in rows:
        if str(row.get("asset_id") or "") in ids:
            row.update(reservation_status="RESERVADO_PELO_ARES_V3_DAILY", ares_eligible=False, used_by="ARES_V3_IN_FLIGHT", campaign_owner="Ares", reservation_audit=str(audit_path), last_reconciled_at=utc_now())
    atomic_inventory(path, rows)


def release_inventory(path: Path, rows: list[dict[str, Any]], selected_ids: set[str]) -> None:
    for row in rows:
        if str(row.get("asset_id") or "") in selected_ids and row.get("used_by") == "ARES_V3_IN_FLIGHT":
            row.update(reservation_status="LIBERADO_POR_RODOLFO_PARA_ARES_DAILY", ares_eligible=True, used_by=None, campaign_owner="Ares", last_reconciled_at=utc_now())
            row.pop("reservation_audit", None)
    atomic_inventory(path, rows)


def update_inventory_assignments(path: Path, rows: list[dict[str, Any]], assignments: list[dict[str, Any]], moves: dict[str, dict[str, Any]], audit_path: Path) -> None:
    by_asset = {str(row["asset_id"]): row for row in assignments}
    for row in rows:
        assignment = by_asset.get(str(row.get("asset_id") or ""))
        if not assignment:
            continue
        moved = str(row.get("asset_drive_id") or "") in moves
        row.update(
            status="02_TESTING" if moved else "01_READY_USED_MOVE_PENDING",
            reservation_status="UTILIZADO_PELO_ARES",
            ares_eligible=False,
            used_by="ARES",
            campaign_owner="Ares",
            ad_account_id=ACCOUNT_ID,
            meta_campaign_id=assignment["campaign_id"],
            meta_adset_id=assignment["adset_id"],
            meta_ad_id=assignment["ad_id"],
            meta_creative_id=assignment["creative_id"],
            meta_video_id=assignment["vertical_video_id"],
            meta_video_ids=[assignment["vertical_video_id"], assignment["square_video_id"]],
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
        ready_ids = {str(row.get("id") or "") for row in drive.get("files") or [] if row.get("location") == "01_READY"}
        candidates = [
            row for row in inventory
            if row.get("vertical") == "CAR"
            and row.get("country") == "BR"
            and row.get("language") == "BR"
            and row.get("format") == "VID"
            and row.get("status") == "01_READY"
            and row.get("metadata_clean") is True
            and row.get("ares_eligible") is True
            and not row.get("used_by")
            and str(row.get("asset_drive_id") or "") in ready_ids
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
        assets = [
            {
                "asset_id": row.get("asset_id"),
                "canonical_filename": row.get("canonical_filename"),
                "asset_drive_id": row.get("asset_drive_id"),
                "clean_checksum": row.get("clean_checksum"),
                "perceptual_fingerprint": row.get("perceptual_fingerprint"),
                "approved": not conflicts_by_asset.get(str(row.get("asset_id") or "")),
                "meta_conflicts": conflicts_by_asset.get(str(row.get("asset_id") or ""), []),
            }
            for row in candidates
        ]
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
        if not self.page_token or not self.drive_token:
            raise DailyBlocked("prestage", "Meta Page or Drive token not initialized")
        by_id = {str(row.get("id") or ""): row for row in drive.get("files") or []}
        uploader = PageVideoUploader(common=self.common, page_token=self.page_token, page_id=PAGE_ID, graph_version=GRAPH_VERSION)
        expected_titles = {
            title
            for row in selected
            for title in (
                media_title("VERTICAL", str(row["asset_id"]), str(row["clean_checksum"])),
                media_title("SQUARE", str(row["asset_id"]), str(row["clean_checksum"])),
            )
        }
        existing_by_title: dict[str, list[str]] = {}
        for video in self._graph_pages_with_token(f"{PAGE_ID}/videos", {"fields": "id,title,status", "limit": 500}, self.page_token):
            title = str(video.get("title") or "")
            if title in expected_titles and video.get("id"):
                existing_by_title.setdefault(title, []).append(str(video["id"]))
        duplicates = {title: ids for title, ids in existing_by_title.items() if len(ids) > 1}
        if duplicates:
            raise DailyBlocked("prestage", "duplicate deterministic Page video titles require reconciliation", {"duplicates": duplicates})
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
            record = registry.register(
                account_id=ACCOUNT_ID,
                asset_id=str(row["asset_id"]),
                checksum=clean["sha256"],
                vertical_video_id=str(vertical_id),
                square_video_id=str(square_id),
                ready=True,
                source="v3-daily-resumable-meta-readback",
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
        ads = self._graph_pages(f"{campaign_id}/ads", {"fields": "id,name,status,effective_status,configured_status,adset_id,creative{id,name}", "limit": 50})
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
    ads_ok = len(ads) == 3 and all(str(row.get("status") or row.get("configured_status") or "").upper() == "ACTIVE" for row in ads)
    return {"valid": campaign_ok and adsets_ok and ads_ok, "campaign_ok": campaign_ok, "adsets_ok": adsets_ok, "ads_ok": ads_ok}


def assignments_from_readback(manifest: Manifest, campaign_ids: list[str], readbacks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
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
            creative = live_ad.get("creative") or {}
            assignments.append({"asset_id": ad.media.asset_id, "campaign_id": campaign_id, "adset_id": adset_id, "ad_id": str(live_ad.get("id") or ""), "creative_id": str(creative.get("id") or ""), "vertical_video_id": ad.media.vertical_video_id, "square_video_id": ad.media.square_video_id})
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
    operational_date = current.date()
    day = operational_date.isoformat()
    state = load_json(paths.state) if paths.state.exists() else {}
    if gate and not gate_due(current, state):
        return {"status": "SILENT_NOT_DUE", "operational_date_sp": day}
    paths.lock.parent.mkdir(parents=True, exist_ok=True)
    with paths.lock.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = {} if plan_only else (load_json(paths.state) if paths.state.exists() else {})
        state = rollover_completed_state(state, day)
        if state.get("completed_operational_date_sp") == day:
            return {"status": "ALREADY_COMPLETE", "operational_date_sp": day, "audit": state.get("audit_path")}
        total_started = time.perf_counter()
        call_counter: dict[str, int] = {}
        call_counter_token = _CALL_COUNTER.set(call_counter)
        request_id = str(state.get("request_id") or f"cpv-daily-{operational_date:%Y%m%d}")
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
        try:
            operation = load_json(paths.operation)
            config = load_json(paths.config)
            validate_engine_config(config)
            desired_count = int(state.get("desired_campaign_count") or requested_campaign_count(operation, operational_date))
            phase_started, phase_calls = phase_begin(call_counter)
            meta = backend.meta_preflight()
            phase_end(audit, "meta_preflight", phase_started, phase_calls, call_counter)
            completed_before = len(state.get("campaign_ids") or [])
            if state.get("campaign_count"):
                count = int(state["campaign_count"])
                pending_budget_count = max(0, count - completed_before)
                budget = enforce_budget_cap(meta["campaigns"], max(1, pending_budget_count), operation)
                if int(budget["selected_count"]) < pending_budget_count:
                    raise DailyBlocked("budget_cap", "remaining resumable campaign no longer fits the operational cap", budget)
            else:
                budget = enforce_budget_cap(meta["campaigns"], desired_count, operation)
                count = int(budget["selected_count"])
            numbers = list(state.get("campaign_numbers") or next_campaign_numbers(meta["campaigns"], count, operation))
            phase_started, phase_calls = phase_begin(call_counter)
            drive_info = backend.drive_preflight()
            drive = drive_info["drive"]
            phase_end(audit, "drive_preflight", phase_started, phase_calls, call_counter)
            if not selected:
                phase_started, phase_calls = phase_begin(call_counter)
                reconciliation_payload = backend.refresh_reconciliation(inventory_rows, drive, current)
                phase_end(audit, "reconciliation", phase_started, phase_calls, call_counter)
                phase_started, phase_calls = phase_begin(call_counter)
                selected = select_assets(
                    inventory_rows,
                    {str(row.get("id") or "") for row in drive.get("files") or [] if row.get("location") == "01_READY"},
                    count * 3,
                    reconciliation=reconciliation_payload,
                )
                reconciliation = verify_reconciliation(paths.reconciliation, selected, current)
                phase_end(audit, "asset_selection", phase_started, phase_calls, call_counter, detail={"selected": len(selected)})
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
                        "reconciliation": reconciliation,
                        "drive_counts": drive.get("counts") or {},
                        "side_effects": {"inventory_reservation": False, "media_upload": False, "campaign_write": False, "drive_move": False},
                        "audit": str(audit_path),
                    }
                    audit.update(stage="DRY_RUN_OK", final=result, completed_at_utc=utc_now())
                    atomic_json(audit_path, audit)
                    if not quiet:
                        print(json.dumps(result, ensure_ascii=False, indent=2))
                    return result
                reserve_inventory(paths.inventory, inventory_rows, selected, audit_path)
                selected_ids = {str(row.get("asset_id") or "") for row in selected}
                state = {"schema_version": 3, "status": "ASSETS_RESERVED", "operational_date_sp": day, "request_id": request_id, "audit_path": str(audit_path), "desired_campaign_count": desired_count, "campaign_count": count, "campaign_numbers": numbers, "selected_asset_ids": sorted(selected_ids), "reconciliation": reconciliation, "budget_plan": budget, "updated_at_utc": utc_now()}
                atomic_json(paths.state, state)
            else:
                phase_started, phase_calls = phase_begin(call_counter)
                verify_reconciliation(paths.reconciliation, selected, current)
                phase_end(audit, "reconciliation", phase_started, phase_calls, call_counter, detail={"resume_validation": True})
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
            manifest_dir.mkdir(parents=True, exist_ok=True)
            draft_path = manifest_dir / "draft.json"
            sealed_path = manifest_dir / "sealed.json"
            if sealed_path.exists():
                sealed = load_json(sealed_path)
            else:
                templates = load_json(paths.templates).get("templates") or []
                draft = build_cpv_manifest(registry=registry, asset_refs=assets_payload["assets"], campaign_numbers=[int(item) for item in numbers], operational_date=day, request_id=request_id, creative_templates=templates, status="ACTIVE")
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
                {str(item) for item in state.get("campaign_ids") or []},
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
            state.update(status="COMPLETE", completed_operational_date_sp=day, campaign_ids=campaign_ids, stock_remaining=stock, updated_at_utc=utc_now())
            atomic_json(paths.state, state)
            if post_report:
                labels = ", ".join(f"C{number:02d}" for number in numbers)
                audit["discord_readback"] = post_discord(
                    f"✅ V3 CONCLUÍDO — CPV G006 — {operational_date:%d/%m}\n"
                    f"{labels} · USD 30 cada · 1×1×3 · ACTIVE com início futuro 00:30 SP\n"
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
            manual_gate = True
            authorization = {"required": True, "authorized_roles": ["Rodolfo", "Nicolas"], "scope": "any corrective write after this failure"}
            audit.update(stage=failure_status, failure=failure, failed_at_utc=utc_now(), manual_reconciliation_required=True, operator_authorization=authorization)
            atomic_json(audit_path, audit)
            if failure_status == "FAILED" and selected_ids:
                inventory_rows = [json.loads(line) for line in paths.inventory.read_text(encoding="utf-8").splitlines() if line.strip()]
                release_inventory(paths.inventory, inventory_rows, selected_ids)
            if not plan_only:
                state.update(
                    status=failure_status,
                    failure=failure,
                    retry_after_epoch=int(time.time()) + 300 if failure_status != "FAILED" else 0,
                    manual_reconciliation_required=True,
                    operator_authorization=authorization,
                    updated_at_utc=utc_now(),
                )
                atomic_json(paths.state, state)
            if post_report:
                try:
                    post_discord(discord_failure_message(failure, failure_status, operational_date, list(state.get("campaign_numbers") or [])))
                except Exception:
                    pass
            if not quiet:
                print(json.dumps({"status": failure_status, "failure": failure, "manual_reconciliation_required": True, "operator_authorization": authorization, "audit": str(audit_path)}, ensure_ascii=False, indent=2))
            return {"status": failure_status, "failure": failure, "manual_reconciliation_required": True, "operator_authorization": authorization, "audit": str(audit_path)}
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
            )
            assets.append({
                "asset_id": asset_id,
                "checksum": checksum,
                "canonical_filename": f"CAR_BR_BR_VID_OFFLINE_PV_{index + 1:03d}.mp4",
            })
        operational_date = datetime.now(SP).date().isoformat()
        draft = build_cpv_manifest(
            registry=registry,
            asset_refs=assets,
            campaign_numbers=[14, 15, 16],
            operational_date=operational_date,
            request_id=f"offline-cpv-{operational_date.replace('-', '')}",
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
            "soft_score": 100,
            "hard_score": 120,
            "score_window_seconds": 300,
            "points_per_mode": {"pure_clone": 20, "clone_prestaged": 45},
            "state_root": str(root / "state"),
            "audit_root": str(root / "audit"),
        }
        transport = FakeBatchTransport(ACCOUNT_ID)
        engine = CampaignEngine(config, transport_factory=lambda account: transport)
        first = engine.execute(manifest)
        if first.get("status") != "PARTIAL_DEFERRED_QUOTA" or len(first.get("campaign_ids") or []) != 2:
            raise RuntimeError("offline first wave did not produce guarded 2+deferred plan")
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
            "final_status": second["status"],
            "final_campaigns": len(second["campaign_ids"]),
            "unique_campaign_ids": len(set(second["campaign_ids"])),
            "intermediate_get_calls": second["metrics"]["intermediate_get_calls"],
            "external_network_calls": 0,
        }
