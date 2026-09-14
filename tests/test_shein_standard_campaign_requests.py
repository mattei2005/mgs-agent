import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "profiles/ares-skills/growth/direct-traffic-shein-operations/references/standard-campaign-requests.md"
OPERATION = ROOT / "data/ares/meta-ads/operations/SHEIN-US-DIRECT.json"


def test_shein_standard_campaign_request_templates_are_registered():
    operation = json.loads(OPERATION.read_text(encoding="utf-8"))
    templates = operation["request_templates"]

    assert templates["status"] == "ACTIVE"
    assert templates["version"] == "1.0"
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
    assert "Não reutilizar source_campaign_id, source_adset_id ou source_ad_id" in text
    assert "Modo: Clonar com criativos novos" in text
    assert "Não preservar o post social ou a prova social da fonte" in text
    assert "Modo: Duplicar igual uma campanha existente" in text
    assert "Manter o mesmo effective_object_story_id da fonte" in text
    assert "Budget: Utilizar o mesmo budget da campanha duplicada." in text
    assert "A campanha fonte deve pertencer" not in text
    assert "Ares deve confirmar por readback que a fonte utiliza" not in text
