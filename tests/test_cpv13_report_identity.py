"""Presentation regression; offline fixtures, no Meta/SB/Discord writes."""
import importlib.util
from pathlib import Path
import pytest

SCRIPT = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py')

def load():
    spec = importlib.util.spec_from_file_location('cpv13_identity_tests', SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@pytest.mark.parametrize('name,expected', [
    ('80 - 14-10 - Garagem - COPY C20', 'C80 COPY C20'),
    ('80 - 14-10 - Garagem - C020-DUP001', 'C80 COPY C20'),
    ('80 - 14-10 - Garagem - C008-DUP003', 'C80 COPY C08'),
    ('80 - 14-10 - Garagem - MOTO - C020-DUP001', 'C80M COPY C20'),
    ('80 - 14-10 - Garagem', 'C80'),
    ('80 - 14-10 - Garagem - COPY C20 - C021-DUP001', 'C80 COPY ?'),
    ('80 - 14-10 - Garagem - COPY', 'C80 COPY ?'),
    ('80 - 14-10 - Garagem - NOTCOPY C20 - NOTMOTO', 'C80'),
])
def test_identity(name, expected):
    row = load().report_campaign_identity('80', name)
    assert row['campaign_label'] == expected
    assert row['campaign_date'] == '14/10'

def test_date_fallback_and_no_inference():
    mod = load()
    assert mod.report_campaign_identity('80', 'Campaign', '2026-10-14')['campaign_date'] == '14/10'
    assert mod.report_campaign_identity('80', 'Campaign')['campaign_date'] == 'n/d'
    assert mod.report_campaign_identity('80', 'Campaign')['copy_source_number'] is None

def test_real_size_pagination_keeps_each_copy_once():
    mod = load()
    rows = [['14/10', f'C{n} COPY C20', 'D1', '$25,00'] for n in range(80, 110)]
    text = '\n\n'.join(mod.table_pages(['Data', 'Camp', 'Dia', 'Budget'], rows))
    chunks, _ = mod.discord_message_plan(text)
    assert all(len(chunk) <= 1900 for chunk in chunks)
    for row in rows:
        assert text.count(row[1] + ' ') == 1
    assert all('Data' in chunk and 'Camp' in chunk and chunk.count('```') % 2 == 0 for chunk in chunks)
