#!/usr/bin/env python3
"""Render the standard first response for an Eggbev creation-thread call."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def normalized(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(char))


def parse_call(message: str, now: datetime | None = None) -> dict:
    simple = normalized(message)
    campaign_match = re.search(r"\b(\d+)\s+campanh", simple)
    campaign_count = int(campaign_match.group(1)) if campaign_match else 1
    creative_match = re.search(r"\b(?:com\s+)?(3|5)\s+criativ", simple)
    creatives_per_campaign = int(creative_match.group(1)) if creative_match else 3
    page_match = re.search(r"\bpagina\s+([^,;]+?)(?=\s+(?:com|budget|orcamento|usd|us\$|\$)\b|$)", simple)
    page = (page_match.group(1).strip() if page_match else "").strip(" .")
    budget_match = re.search(r"(?:budget|orcamento)?\s*(?:usd|us\$|\$)\s*([0-9]+(?:[.,][0-9]{1,2})?)", simple)
    budget = None
    if budget_match:
        try:
            budget = Decimal(budget_match.group(1).replace(",", "."))
        except InvalidOperation:
            budget = None
    base = (now or datetime.now(ET)).astimezone(ET)
    start = (base + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    required_assets = campaign_count * creatives_per_campaign
    missing = []
    if not page:
        missing.append("page")
    if budget is None or budget <= 0:
        missing.append("daily_budget_usd_per_campaign")
    return {
        "campaign_count": campaign_count,
        "page": page or None,
        "creatives_per_campaign": creatives_per_campaign,
        "required_unique_assets": required_assets,
        "daily_budget_usd_per_campaign": float(budget) if budget is not None and budget > 0 else None,
        "start_time": start.isoformat(),
        "missing_inputs": missing,
    }


def render(result: dict) -> str:
    campaigns = result["campaign_count"]
    creatives = result["creatives_per_campaign"]
    page = result.get("page") or "não informada"
    assets = result["required_unique_assets"]
    lines = [
        "✅ **Pedido entendido**",
        f"- Página: **{page}** — vou validar o `pg_XXXXX` e a Page real.",
        f"- Estrutura padrão: **{campaigns} campanha{'s' if campaigns != 1 else ''} × 1 AdG1 × {creatives} ads**.",
        f"- Criativos: **{assets} {'arquivos inéditos' if assets != 1 else 'arquivo inédito'}** da `CC_US_EN`, sem reutilização.",
        f"- Início: **{result['start_time']}** (`America/New_York`).",
        "- Aplicação automática: naming, copy, JSON Messenger, placements manuais, tracking e nomes `AD NN - {canonical_stem}`.",
    ]
    if result.get("daily_budget_usd_per_campaign") is None:
        lines.extend([
            "",
            "Falta apenas o **budget diário por campanha**.",
            "Responda em uma linha, por exemplo: `Budget USD 50`.",
            "",
            "Depois disso faço preflight, reconciliação, pre-stage e plan; volto com o resumo final para seu **OK**. Nenhuma campanha é publicada nesta etapa.",
        ])
    else:
        lines.extend([
            f"- Budget informado: **USD {result['daily_budget_usd_per_campaign']:.2f} por campanha**.",
            "",
            "Os inputs estão completos. O próximo passo é executar preflight, reconciliação, pre-stage e plan e então apresentar o resumo final para seu **OK**. Nenhuma campanha é publicada antes desse resumo.",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = parse_call(args.message)
    result["reply"] = render(result)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["reply"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
