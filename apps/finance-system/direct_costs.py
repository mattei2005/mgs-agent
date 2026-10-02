"""Validated monthly direct costs in their original BRL amount."""
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from calc import num
from domain import fx_convert

_ALLOWED_MANAGERS = {'joe', 'nicolas', 'kelly', 'isliago', 'george', 'SEM_COMISSAO'}
_ID = re.compile(r'^[a-z0-9][a-z0-9._:-]{2,119}$')
_AUTHORITY = re.compile(r'^\d{17,20}$')
_DECIMAL = re.compile(r'^\d+(?:\.\d{1,2})?$')
_UNIT_DECIMAL = re.compile(r'^\d+(?:\.\d{1,6})?$')
_SHA256 = re.compile(r'^[0-9a-f]{64}$')


def direct_monthly_costs(additions, sites, workbook, period):
    """Project fixed-BRL monthly costs into USD facts for the calculation graph.

    The source amount remains BRL and is converted on every calculation, so an
    automatic FX refresh cannot change the recognized BRL cost. These facts are
    monthly closing movements, not invented daily media spend.
    """
    site_by_name = {s['name']: s for s in sites if s.get('status') == 'ATIVO'}
    fx = num(workbook.get('principal', 'Agosto 2026', 'F1'))
    if fx <= 0:
        raise ValueError('Câmbio BRL indisponível para custo direto')
    seen = set()
    rows = []
    for addition in additions:
        if addition.get('kind') != 'direct_monthly_cost':
            continue
        ident = addition.get('id')
        if not isinstance(ident, str) or not _ID.fullmatch(ident) or ident in seen:
            raise ValueError('Identificador de custo direto inválido ou repetido')
        seen.add(ident)
        if addition.get('period') != period or addition.get('date') != period:
            raise ValueError('Custo direto fora da competência')
        site = site_by_name.get(addition.get('site'))
        if not site:
            raise ValueError('Site ativo do custo direto não encontrado')
        manager = addition.get('manager')
        if manager not in _ALLOWED_MANAGERS:
            raise ValueError('Gestor do custo direto inválido')
        if addition.get('currency') != 'BRL':
            raise ValueError('Custo direto deve permanecer em BRL')
        raw = addition.get('amount')
        if not isinstance(raw, str) or not _DECIMAL.fullmatch(raw):
            raise ValueError('Valor do custo direto inválido')
        amount = num(raw)
        if amount <= 0 or amount > num('1000000000'):
            raise ValueError('Valor do custo direto fora do limite')
        authority = addition.get('authority')
        if not isinstance(authority, str) or not _AUTHORITY.fullmatch(authority):
            raise ValueError('Autoridade do custo direto inválida')
        label = addition.get('label')
        source = addition.get('source')
        if not isinstance(label, str) or not label.strip() or len(label) > 180:
            raise ValueError('Descrição do custo direto inválida')
        if not isinstance(source, str) or not source.strip() or len(source) > 240:
            raise ValueError('Fonte do custo direto inválida')
        usd = abs(num(fx_convert(raw, 'BRL', {'USDBRL': fx, 'USDCAD': num(1), 'GBPUSD': num(1)})))
        rows.append({
            'id': ident,
            'segment': addition['site'],
            'site': addition['site'],
            'partner': site.get('network') or site.get('partner'),
            'manager': manager,
            'status': 'CENARIO',
            'country': 'BR',
            'date': period,
            'gross': num(0),
            'invalid': num(0),
            'net': num(0),
            'tax': num(0),
            'spend': -usd,
            'profit': -usd,
            'source': {},
            'invalid_rate': num(0),
            'share_rate': num(0),
            'tax_rate': num(0),
            'native_addition': True,
            'monthly_closing': True,
            'spend_only': True,
            'cost_currency': 'BRL',
            'cost_amount': raw,
            'cost_label': label.strip(),
            'authority': authority,
            'source_note': source.strip(),
        })
    return rows


def direct_daily_costs(additions, sites, workbook, period):
    """Project a verified daily SMS consumption in BRL as a direct expense.

    Unlike media spend, this cost has its own dimension. The BRL amount remains
    authoritative and is converted on every calculation. Zero-volume manager
    groups are omitted by the collector instead of creating placeholder facts.
    """
    site_by_name = {s['name']: s for s in sites if s.get('status') == 'ATIVO'}
    fx = num(workbook.get('principal', 'Agosto 2026', 'F1'))
    if fx <= 0:
        raise ValueError('Câmbio BRL indisponível para custo direto diário')
    seen = set()
    rows = []
    for addition in additions:
        if addition.get('kind') != 'direct_daily_cost':
            continue
        ident = addition.get('id')
        if not isinstance(ident, str) or not _ID.fullmatch(ident) or ident in seen:
            raise ValueError('Identificador de custo direto diário inválido ou repetido')
        seen.add(ident)
        day = addition.get('date')
        try:
            parsed = date.fromisoformat(day)
        except (TypeError, ValueError):
            raise ValueError('Data do custo direto diário inválida') from None
        if addition.get('period') != period or day[:7] != period or parsed.isoformat() != day:
            raise ValueError('Custo direto diário fora da competência')
        site = site_by_name.get(addition.get('site'))
        if not site:
            raise ValueError('Site ativo do custo direto diário não encontrado')
        manager = addition.get('manager')
        if manager not in _ALLOWED_MANAGERS:
            raise ValueError('Gestor do custo direto diário inválido')
        if addition.get('currency') != 'BRL':
            raise ValueError('Custo direto diário deve permanecer em BRL')
        raw = addition.get('amount')
        unit_raw = addition.get('unit_cost_brl')
        if not isinstance(raw, str) or not _DECIMAL.fullmatch(raw):
            raise ValueError('Valor do custo direto diário inválido')
        if not isinstance(unit_raw, str) or not _UNIT_DECIMAL.fullmatch(unit_raw):
            raise ValueError('Custo unitário diário inválido')
        amount = Decimal(raw)
        unit = Decimal(unit_raw)
        count = addition.get('message_count')
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError('Quantidade diária de mensagens inválida')
        if amount <= 0 or amount > Decimal('1000000000') or unit <= 0:
            raise ValueError('Valor do custo direto diário fora do limite')
        expected = (unit * count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amount.quantize(Decimal('0.01')) != expected:
            raise ValueError('Valor diário diverge de quantidade × custo unitário')
        authority = addition.get('authority')
        if not isinstance(authority, str) or not _AUTHORITY.fullmatch(authority):
            raise ValueError('Autoridade do custo direto diário inválida')
        label = addition.get('label')
        source = addition.get('source')
        source_hash = addition.get('source_hash')
        if not isinstance(label, str) or not label.strip() or len(label) > 180:
            raise ValueError('Descrição do custo direto diário inválida')
        if not isinstance(source, str) or not source.strip() or len(source) > 240:
            raise ValueError('Fonte do custo direto diário inválida')
        if not isinstance(source_hash, str) or not _SHA256.fullmatch(source_hash):
            raise ValueError('Hash da fonte diária inválido')
        usd = abs(num(fx_convert(raw, 'BRL', {'USDBRL': fx, 'USDCAD': num(1), 'GBPUSD': num(1)})))
        rows.append({
            'id': ident,
            'segment': addition['site'],
            'site': addition['site'],
            'partner': site.get('network') or site.get('partner'),
            'manager': manager,
            'status': 'CENARIO',
            'country': 'BR',
            'date': day,
            'gross': num(0),
            'invalid': num(0),
            'net': num(0),
            'tax': num(0),
            'spend': num(0),
            'direct_expense': -usd,
            'profit': -usd,
            'source': {},
            'invalid_rate': num(0),
            'share_rate': num(0),
            'tax_rate': num(0),
            'native_addition': True,
            'monthly_closing': False,
            'spend_only': False,
            'direct_cost': True,
            'cost_currency': 'BRL',
            'cost_amount': raw,
            'cost_label': label.strip(),
            'authority': authority,
            'source_note': source.strip(),
            'source_hash': source_hash,
            'message_count': count,
            'unit_cost_brl': unit_raw,
        })
    return rows
