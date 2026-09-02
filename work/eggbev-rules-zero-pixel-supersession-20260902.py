#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

THREAD_ID = "1541578622106865815"
HELPER = Path("/root/mgs-agent/scripts/ares-eggbev-thread-reconcile.py")
AUDIT = Path("/root/mgs-agent/data/ares/meta-ads/audit/eggbev/rules-zero-pixel-supersession-20260902.json")

spec = importlib.util.spec_from_file_location("eggbev_thread_reconcile", HELPER)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load Discord helper")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

token = module.load_token()

replacements = {
    "1544504385105694823": [
        (
            "7. **Página e Limites** pausa campanhas por Page restrita, LEADS ou ausência de resultado do pixel.",
            "7. **Página e Limites** mantém LEADS e restrição DTR ativas; a etapa zero-pixel está suspensa desde 02/09 03:55 ET por decisão do Nicolas.",
        ),
    ],
    "1544504391132778618": [
        (
            "Fallback de zero resultado do pixel:\n- Depois das 03:00 ET, campanha efetivamente ativa com gasto do dia `> US$2` e zero resultado do evento `eggbev-pv-u` é pausada no nível campanha.\n- Exatamente US$2 não pausa; qualquer resultado mantém.\n- Pixel/evento divergente = zero write + alerta.\n- Toda pausa exige GET/readback; nunca há reativação automática.",
            "Fallback de zero resultado do pixel — **SUSPENSO**:\n- Nicolas suspendeu somente essa etapa em 02/09/2026 às 03:55 ET.\n- Ela foi removida do wrapper, está com write/schedule desativados e não pode pausar campanhas.\n- As duas campanhas pausadas por essa etapa antes da suspensão foram reativadas por correção pontual autorizada e confirmadas `ACTIVE`.\n- Só pode voltar por nova instrução explícita de gestor autorizado; LEADS e restrição DTR permanecem ativas.",
        ),
    ],
    "1544504392018042930": [
        (
            "**Restrição de Page + fallback de zero pixel**\n- Físico: a cada 5 minutos nos offsets `:03/:08/.../:58`, com stagger de 30 segundos.\n- As duas etapas rodam em série e compartilham lock com o ciclo ROAS; não existem dois writers Eggbev simultâneos.\n\n**Sem cron ativo**\n- Diário, Criar Campanhas e Clonar Campanhas.",
            "**Restrição de Page — ativa**\n- Físico: a cada 5 minutos nos offsets `:03/:08/.../:58`, com stagger de 30 segundos.\n- Compartilha lock com o ciclo ROAS; não existem dois writers Eggbev simultâneos.\n- O zero-pixel foi removido desse wrapper e está suspenso.\n\n**Sem cron ativo**\n- Zero-pixel, Diário, Criar Campanhas e Clonar Campanhas.",
        ),
    ],
    "1544584629170737224": [
        (
            "**Limites ativos:** LEADS em hold/dry-run; `clone_page_switch` bloqueado; cron/post do Diário e escala automática desligados; `ACTIVE` não prova serving sem Insights.",
            "**Limites ativos:** LEADS em hold/dry-run; zero-pixel suspenso e sem cron/write; `clone_page_switch` bloqueado; cron/post do Diário e escala automática desligados; `ACTIVE` não prova serving sem Insights.",
        ),
    ],
}

results = []
for message_id, pairs in replacements.items():
    status, before = module.request(token, "GET", f"/channels/{THREAD_ID}/messages/{message_id}")
    if status != 200 or not isinstance(before, dict):
        raise SystemExit(f"pre-read failed message={message_id} http={status}")
    current = str(before.get("content") or "")
    updated = current
    for old, new in pairs:
        if updated.count(old) != 1:
            raise SystemExit(f"expected text mismatch message={message_id} count={updated.count(old)}")
        updated = updated.replace(old, new)
    if len(updated) > 2000:
        raise SystemExit(f"message too long message={message_id} chars={len(updated)}")
    if updated == current:
        raise SystemExit(f"no change message={message_id}")

    patch_status, patched = module.request(
        token,
        "PATCH",
        f"/channels/{THREAD_ID}/messages/{message_id}",
        {"content": updated},
    )
    if patch_status != 200 or not isinstance(patched, dict):
        raise SystemExit(f"patch failed message={message_id} http={patch_status}")

    read_status, after = module.request(token, "GET", f"/channels/{THREAD_ID}/messages/{message_id}")
    readback_ok = (
        read_status == 200
        and isinstance(after, dict)
        and str(after.get("content") or "") == updated
        and str(after.get("channel_id") or "") == THREAD_ID
    )
    if not readback_ok:
        raise SystemExit(f"readback failed message={message_id} http={read_status}")
    results.append(
        {
            "message_id": message_id,
            "http_patch": patch_status,
            "http_readback": read_status,
            "chars": len(updated),
            "readback_ok": True,
        }
    )

payload = {
    "ok": True,
    "thread_id": THREAD_ID,
    "scope": "supersede stale zero-pixel active wording; preserve nine-part manual",
    "messages_edited": len(results),
    "results": results,
    "meta_writes": 0,
    "cron_writes": 0,
}
AUDIT.parent.mkdir(parents=True, exist_ok=True)
AUDIT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
