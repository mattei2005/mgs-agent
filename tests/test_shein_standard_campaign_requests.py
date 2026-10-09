import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "profiles/ares-skills/growth/direct-traffic-shein-operations/references/standard-campaign-requests.md"
OPERATION = ROOT / "data/ares/meta-ads/operations/SHEIN-US-DIRECT.json"


def test_shein_standard_campaign_request_templates_are_registered():
    operation = json.loads(OPERATION.read_text(encoding="utf-8"))
    templates = operation["request_templates"]

    assert templates["status"] == "ACTIVE_DOCUMENT_APPROVED_RUNTIME_OFFLINE_TESTED"
    assert templates["version"] == "3.0"
    assert templates["runtime_pending"] == []
    assert "offline-tested" in templates["bid_override_implementation"]
    assert templates["source"] == str(REFERENCE.relative_to(ROOT))
    assert templates["modes"] == [
        "from_zero_prestaged",
        "clone_prestaged",
        "pure_clone",
    ]


def test_shein_standard_campaign_request_templates_preserve_mode_identity():
    text = REFERENCE.read_text(encoding="utf-8")

    assert text.count("PEDIDO DE CAMPANHA — SHEIN") == 3
    assert "Modo: Criar do zero com criativos novos" in text
    assert "Não reutilizar source_campaign_id ou source_adset_id" in text
    assert "Ares resolve source_ad_id somente quando a conta exigir lineage técnica" in text
    assert "Modo: Clonar com criativos novos" in text
    assert "Não preservar o post social ou a prova social da fonte" in text
    assert "Modo: Duplicar igual uma campanha existente" in text
    assert "Preservação do mesmo post/prova social não é automática" in text
    assert "## Histórico supersedido — formulários 1.0" in text
    assert "### Pedido aprovado" in text
    assert "Suba essa campanha" in text
    assert "duplicação com delta explícito" in text
    assert "Budget: Utilizar o mesmo budget da campanha duplicada." in text
    assert "A campanha fonte deve pertencer" not in text
    assert "Ares deve confirmar por readback que a fonte utiliza" not in text
