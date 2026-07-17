#!/usr/bin/env python3
"""Process MGS weekly revenue × spend Excel reports into Long/Resumo/Validacao.

Validated first against Rodolfo's 2026-06-16..2026-06-29 workbook.

Default output shape for operator-facing Google Sheets:
- Long: Data | Site | Vertical | Gestor | Conta_FB | Gasto | Receita
- Resumo_dia: Data | Gasto | Receita | Lucro | Margem %
- Validacao: concise reconciliation metadata

Diagnostics are written locally as CSV/JSON under --out-dir and are not uploaded
unless this script is extended intentionally.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from zoneinfo import ZoneInfo

GOOGLE_AUTH_HELPER_PATH = Path(__file__).resolve().parent / 'mgs_google_workspace_auth.py'
_google_auth_spec = importlib.util.spec_from_file_location('mgs_google_workspace_auth', GOOGLE_AUTH_HELPER_PATH)
if not _google_auth_spec or not _google_auth_spec.loader:
    raise RuntimeError(f'cannot load Google Service Account helper: {GOOGLE_AUTH_HELPER_PATH}')
GOOGLE_AUTH = importlib.util.module_from_spec(_google_auth_spec)
_google_auth_spec.loader.exec_module(GOOGLE_AUTH)

DEFAULT_TOKEN_FILE = Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
DEFAULT_OUT_ROOT = Path('/root/mgs-agent/work/revenue-spend-reporting')
GOOGLE_QUOTA_PROJECT: str | None = None

TERM_RE = re.compile(r'(us|gb|es|de|mx|ca|za|ar|br)-(cc|job|car|game)-(en|es|de|pt|br)', re.I)
CONTENT_RE = re.compile(r'(?:drip|bd)_(us|gb|es|de|mx|ca|za|ar|br)_(cc|job|car|game)_', re.I)
GESTOR_RE = re.compile(r'(?i)(?:^|[^a-z0-9])g00([1-6])(?:[-_ ]?[sd])?(?=$|[^a-z0-9])')
PLACEMENT_RE = re.compile(r'^pl_digital-trust_([^_]+)_([a-z]{2})$', re.I)

OWNERS = {
    'ducapes.com':'g001-d', 'finance.ducapes.com':'g001-d', 'wantabrand.com':'g001-d', 'finance.wantabrand.com':'g001-d', 'conectageral.com':'g001-d', 'portalrelevante.com':'g001-d', 'marevelx.com':'g001-d',
    'zuout.com':'g002-d', 'finanzas.zuout.com':'g002-d', 'cliquet.com':'g002-d', 'finanzas.cliquet.com':'g002-d', 'fincgriffin.com':'g002-d', 'vizioid.com':'g002-d', 'creditoparaveiculo.com':'g002-d', 'gamezonead.com':'g002-d', 'gamingadx.com':'g002-d',
    'zytiva.com':'g003-d', 'finanzas.zytiva.com':'g003-d', 'openzed.com':'g003-d', 'finanzas.openzed.com':'g003-d', 'wavesbee.com':'g003-d', 'xyvlov.com':'g003-d',
    'finance.topfeed.fun':'g004-d', 'finanzas.topfeed.fun':'g004-d', 'topfeed.fun':'g004-d', 'infinitynexx.com':'g004-d',
    'newsoun.com':'g005-d', 'finanzas.newsoun.com':'g005-d', 'de.newsoun.com':'g005-d', 'helixenit.com':'g005-d',
    'lyzmo.com':'g006-d', 'finanzas.lyzmo.com':'g006-d', 'eggbev.com':'g006-d', 'finanzas.eggbev.com':'g006-d', 'seuprimeiroempregoam.com':'g006-d', 'empleo.seuprimeiroempregoam.com':'g006-d', 'financeadx.com':'g006-d',
}

AV_CONFIG = {
    'cliquet.com':('cc','en',{'us'},'us'), 'ducapes.com':('cc','es',{'us'},'us'), 'eggbev.com':('cc','en',{'us'},'us'),
    'lyzmo.com':('cc','en',{'us','gb'},'us'), 'newsoun.com':('cc','en',{'us','gb'},'us'), 'openzed.com':('cc','en',{'us','gb'},'us'),
    'zuout.com':('cc','en',{'us'},'us'), 'zytiva.com':('cc','en',{'us','gb'},'us'), 'de.newsoun.com':('cc','de',{'de'},'de'),
    'finance.topfeed.fun':('cc','en',{'us','gb'},'us'), 'finance.ducapes.com':('cc','en',{'us'},'us'),
    'finanzas.cliquet.com':('cc','es',{'us'},'us'), 'finanzas.eggbev.com':('cc','es',{'us'},'us'), 'finanzas.lyzmo.com':('cc','es',{'us'},'us'),
    'finanzas.newsoun.com':('cc','es',{'us'},'us'), 'finanzas.openzed.com':('cc','es',{'us','es'},'us'), 'finanzas.topfeed.fun':('cc','es',{'us'},'us'),
    'finanzas.zuout.com':('cc','es',{'us'},'us'), 'finanzas.zytiva.com':('cc','es',{'us'},'us'),
    'seuprimeiroempregoam.com':('job','en',{'us'},'us'), 'empleo.seuprimeiroempregoam.com':('job','es',{'us'},'us'),
    'creditoparaveiculo.com':('car','br',{'br'},'br'), 'fincgriffin.com':('car','en',{'us'},'us'),
    'conectageral.com':('cc','en',{'us'},'us'), 'portalrelevante.com':('cc','en',{'us'},'us'),
    'gamezonead.com':('game','br',{'br'},'br'), 'gamingadx.com':('game','en',{'us'},'us'),
}

JBF_STD = {'financeadx','helixenit','infinitynexx','marevelx','xyvlov','vizioid'}
FB_BRAND_TO_SITE = {
    'cliquet':'cliquet.com', 'cliquetfinanzas':'finanzas.cliquet.com',
    'creditoparaveiculo':'creditoparaveiculo.com', 'eggbev':'eggbev.com', 'eggbevfinanzas':'finanzas.eggbev.com',
    'financeadx':'financeadx.com', 'fincgriffin':'fincgriffin.com', 'helixenit':'helixenit.com', 'infinitynexx':'infinitynexx.com',
    'marevelx':'marevelx.com', 'newsoun':'newsoun.com', 'openzed':'openzed.com', 'openzedfinanzas':'finanzas.openzed.com',
    'topfeed':'finance.topfeed.fun', 'topfeedfinanzas':'finanzas.topfeed.fun', 'wantabrand':'wantabrand.com', 'wantabrandfinance':'finance.wantabrand.com',
    'zuout':'zuout.com', 'zuoutfinanzas':'finanzas.zuout.com', 'zytiva':'zytiva.com',
}
GOOGLE_ACCOUNT_MAP = {
    'mattei1': ('gamezonead.com', 'br-game-br', 'g002-d', 'Mattei 1 (Google Ads - BRL)'),
    'gamingadx-us-01': ('gamingadx.com', 'us-game-en', 'g002-d', 'Gamingadx-US-01 (Google Ads - BRL)'),
}


def clean_str(v: Any) -> str:
    if v is None:
        return ''
    if isinstance(v, float) and math.isnan(v):
        return ''
    s = str(v).strip()
    return '' if s.lower() in {'nan', 'none', 'null', ''} else s


def norm_date(v: Any) -> str:
    if pd.isna(v):
        return ''
    try:
        return pd.to_datetime(v).date().isoformat()
    except Exception:
        return ''


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cm = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.strip().lower() in cm:
            return cm[cand.strip().lower()]
    for key, col in cm.items():
        for cand in candidates:
            if cand.strip().lower() in key:
                return col
    return None


def parse_money(v: Any) -> float:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace('\xa0', '')
    s = re.sub(r'[^0-9,\.\-]', '', s)
    if s.count(',') == 1 and s.count('.') == 0:
        s = s.replace(',', '.')
    elif s.count(',') and s.count('.'):
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    return float(s or 0)


def normalize_gestor_token(text: Any) -> str | None:
    m = GESTOR_RE.search(clean_str(text))
    return f'g00{m.group(1)}-d' if m else None


def country_from_term(v: Any) -> str | None:
    m = TERM_RE.search(clean_str(v).lower())
    return m.group(1).lower() if m else None


def country_from_content(v: Any) -> str | None:
    m = CONTENT_RE.search(clean_str(v).lower())
    return m.group(1).lower() if m else None


def pick(*vals: Any) -> Any:
    for v in vals:
        if isinstance(v, str) and v:
            return v
    return None


def normalize_site(site: Any) -> str:
    s = clean_str(site).lower()
    if s in {'app.conectageral.com', 'finanzas.conectageral.com'}:
        return 'conectageral.com'
    if s in {'app.portalrelevante.com', 'finanzas.portalrelevante.com'}:
        return 'portalrelevante.com'
    if s == 'topfeed.fun':
        return 'finance.topfeed.fun'
    return s


def gestor_from_medium(medium: Any, site: str) -> str:
    if site == 'de.newsoun.com':
        return 'g005-d'
    return normalize_gestor_token(medium) or OWNERS.get(site, 'g002-d')


def vertical_token(site: str, country: str | None) -> tuple[str, bool]:
    if site == 'de.newsoun.com':
        return 'de-cc-de', False
    if site in {'conectageral.com', 'portalrelevante.com'}:
        return 'us', False
    sep, lang, valid, default = AV_CONFIG.get(site, ('cc', 'en', {'us'}, 'us'))
    used = country or default
    redirected = used not in valid
    if redirected:
        used = default
    return f'{used}-{sep}-{lang}', redirected


def placement_to_site_vertical(placement: Any, fincgriffin_gb_to_us_g006: bool = False) -> tuple[str, str, str | None, str]:
    p = clean_str(placement).lower()
    m = PLACEMENT_RE.match(p)
    if not m:
        return '', '', None, f'unparsed-placement:{p}'
    brand, country = m.group(1), m.group(2)
    if brand == 'creditoparaveiculo':
        return 'creditoparaveiculo.com', 'br-car-br', None, ''
    if brand == 'gamezonead':
        return 'gamezonead.com', 'br-game-br', None, ''
    if brand == 'gamingadx':
        return 'gamingadx.com', 'us-game-en', None, ''
    if brand == 'fincgriffin':
        if country == 'gb' and fincgriffin_gb_to_us_g006:
            return 'fincgriffin.com', 'us-car-en', 'g006-d', 'fincgriffin_gb_reassigned_to_us_g006'
        return 'fincgriffin.com', 'gb-car-en' if country == 'gb' else 'us-car-en', None, ''
    if brand in JBF_STD:
        return f'{brand}.com', country, None, ''
    return f'{brand}.com', country, None, ''


def parse_fb_account(account: Any) -> tuple[str, str, str]:
    raw = clean_str(account)
    stripped = re.sub(r'\([^)]*\)', '', raw).strip()
    m = re.match(r'^([A-Za-z]+)-([A-Z]{2})-([A-Z]+)-([A-Z]{2})-', stripped)
    if not m:
        raise ValueError(f'FB account não parseada: {raw}')
    brand, country, sep, lang = m.group(1), m.group(2).lower(), m.group(3).lower(), m.group(4).lower()
    site = FB_BRAND_TO_SITE.get(brand.lower())
    if brand.lower() == 'newsoun' and country == 'de':
        site = 'de.newsoun.com'
    if not site:
        raise ValueError(f'Marca FB sem mapa: {brand} ({raw})')
    if site == 'creditoparaveiculo.com':
        vertical = 'br-car-br'
    elif site == 'de.newsoun.com':
        vertical = 'de-cc-de'
    elif site == 'fincgriffin.com':
        vertical = 'us-car-en'
    elif brand.lower() in JBF_STD:
        vertical = country
    else:
        vertical = f'{country}-{sep}-{lang}'
    gestor = normalize_gestor_token(stripped) or OWNERS.get(site, 'g002-d')
    if site == 'de.newsoun.com':
        gestor = 'g005-d'
    return site, vertical, gestor


def detect_tabs(input_path: Path) -> dict[str, list[str]]:
    xl = pd.ExcelFile(input_path)
    tabs: dict[str, list[str]] = defaultdict(list)
    for sheet in xl.sheet_names:
        df = pd.read_excel(input_path, sheet_name=sheet, nrows=5)
        cols = [str(c).strip().lower() for c in df.columns]
        if not len(df):
            continue
        if 'site' in cols and any('ad exchange revenue' in c for c in cols):
            tabs['av'].append(sheet)
        elif 'placement' in cols and any('ad exchange revenue' in c for c in cols):
            tabs['sb'].append(sheet)
        elif any('gross revenue' in c for c in cols) or sheet.strip().lower() in {'monetizemore', 'wantabrand e finance.'}:
            tabs['monetize'].append(sheet)
        elif any('account name' in c for c in cols) and any('amount spent' in c for c in cols):
            tabs['fb'].append(sheet)
        elif any('valor gasto' in c for c in cols) or any('nome da conta' in c for c in cols):
            tabs['google'].append(sheet)
    return dict(tabs)


def parse_monetize(input_path: Path, sheet: str) -> list[dict[str, Any]]:
    mm = pd.read_excel(input_path, sheet_name=sheet, header=None)
    rows = []
    current: str | None = None
    for _, r in mm.iterrows():
        a = clean_str(r.iloc[0] if len(r) > 0 else None)
        b = clean_str(r.iloc[1] if len(r) > 1 else None)
        if a.endswith('.com'):
            current = a.lower()
            continue
        d = norm_date(r.iloc[0] if len(r) > 0 else None)
        if current and d:
            site = normalize_site(current)
            vertical = 'gb-cc-en' if site == 'finance.wantabrand.com' else 'us-cc-es'
            rows.append({'Data': d, 'Site': site, 'Vertical': vertical, 'Gestor': 'g001-d', 'Receita': parse_money(b), 'Origem': sheet, 'Classificacao': 'monetizemore'})
    return rows


def build_report(input_path: Path, out_dir: Path, fincgriffin_gb_to_us_g006: bool = False) -> tuple[dict[str, list[list[Any]]], dict[str, Any]]:
    tabs = detect_tabs(input_path)
    revenue: list[dict[str, Any]] = []
    spend: list[dict[str, Any]] = []
    raw_rev: dict[str, float] = defaultdict(float)
    raw_spend: dict[str, float] = defaultdict(float)
    date_ranges: dict[str, list[Any]] = {}
    diagnostics: dict[tuple[str, str], float] = defaultdict(float)
    redirects: list[list[Any]] = []
    ambiguous: list[list[Any]] = []
    flags: list[list[Any]] = []

    pg_countries: dict[tuple[str, str], set[str]] = defaultdict(set)
    for sheet in tabs.get('av', []):
        df = pd.read_excel(input_path, sheet_name=sheet)
        c_site, c_pg, c_term, c_cont = find_col(df, ['Site']), find_col(df, ['utm_campaign']), find_col(df, ['utm_term']), find_col(df, ['utm_content'])
        for _, r in df.iterrows():
            site = normalize_site(r.get(c_site))
            pg = clean_str(r.get(c_pg))
            if not pg or pg == '-':
                continue
            country = pick(country_from_term(r.get(c_term)), country_from_content(r.get(c_cont)))
            if country:
                pg_countries[(site, pg)].add(country)
    pgmap = {k: sorted(v)[0] for k, v in pg_countries.items() if len(v) == 1}
    ambiguous = [[k[0], k[1], ','.join(sorted(v))] for k, v in pg_countries.items() if len(v) > 1]

    for sheet in tabs.get('av', []):
        df = pd.read_excel(input_path, sheet_name=sheet)
        c_date, c_site, c_rev = find_col(df, ['Date']), find_col(df, ['Site']), find_col(df, ['Ad Exchange revenue ($)', 'Ad Exchange revenue'])
        c_pg, c_term, c_cont, c_med = find_col(df, ['utm_campaign']), find_col(df, ['utm_term']), find_col(df, ['utm_content']), find_col(df, ['utm_medium'])
        dates = []
        for _, r in df.iterrows():
            d = norm_date(r.get(c_date))
            if not d:
                continue
            dates.append(d)
            site = normalize_site(r.get(c_site)); pg = clean_str(r.get(c_pg)); rev = parse_money(r.get(c_rev)); raw_rev[sheet] += rev
            term_c = country_from_term(r.get(c_term)); cont_c = country_from_content(r.get(c_cont)); page_c = pgmap.get((site, pg)) if pg and pg != '-' else None
            country = pick(term_c, cont_c, page_c)
            layer = 'term' if term_c else ('content' if cont_c else ('pagina' if page_c else 'default'))
            vertical, redirected = vertical_token(site, country)
            if redirected:
                redirects.append([sheet, d, site, pg, country, vertical, rev])
            revenue.append({'Data': d, 'Site': site, 'Vertical': vertical, 'Gestor': gestor_from_medium(r.get(c_med), site), 'Receita': rev, 'Origem': sheet, 'Classificacao': layer})
            diagnostics[(sheet, layer)] += rev
        if dates:
            date_ranges[sheet] = [min(dates), max(dates), len(df)]

    for sheet in tabs.get('sb', []):
        df = pd.read_excel(input_path, sheet_name=sheet)
        c_date, c_place, c_rev, c_med = find_col(df, ['Date']), find_col(df, ['Placement']), find_col(df, ['Ad Exchange revenue']), find_col(df, ['utm_medium'])
        dates = []
        for _, r in df.iterrows():
            d = norm_date(r.get(c_date))
            if not d:
                continue
            dates.append(d)
            site, vertical, forced_gestor, flag = placement_to_site_vertical(r.get(c_place), fincgriffin_gb_to_us_g006=fincgriffin_gb_to_us_g006)
            rev = parse_money(r.get(c_rev)); raw_rev[sheet] += rev
            if flag:
                flags.append([sheet, d, clean_str(r.get(c_place)), flag])
            revenue.append({'Data': d, 'Site': site, 'Vertical': vertical, 'Gestor': forced_gestor or gestor_from_medium(r.get(c_med), site), 'Receita': rev, 'Origem': sheet, 'Classificacao': 'placement'})
        if dates:
            date_ranges[sheet] = [min(dates), max(dates), len(df)]

    for sheet in tabs.get('monetize', []):
        rows = parse_monetize(input_path, sheet)
        for row in rows:
            revenue.append(row); raw_rev[sheet] += row['Receita']
        if rows:
            date_ranges[sheet] = [min(r['Data'] for r in rows), max(r['Data'] for r in rows), len(rows)]

    inferred_single_date = None
    known_dates = sorted({d for rng in date_ranges.values() for d in rng[:2] if isinstance(d, str) and d})
    if len(known_dates) == 1:
        inferred_single_date = known_dates[0]

    for sheet in tabs.get('fb', []):
        df = pd.read_excel(input_path, sheet_name=sheet)
        c_acc, c_day, c_spend = find_col(df, ['Account name']), find_col(df, ['Day']), find_col(df, ['Amount spent'])
        dates = []
        for _, r in df.iterrows():
            d = norm_date(r.get(c_day)) if c_day else (inferred_single_date or '')
            if not d:
                continue
            dates.append(d)
            site, vertical, gestor = parse_fb_account(r.get(c_acc))
            val = parse_money(r.get(c_spend)); raw_spend[sheet] += val
            spend.append({'Data': d, 'Site': site, 'Vertical': vertical, 'Gestor': gestor, 'Conta_FB': clean_str(r.get(c_acc)), 'Gasto': val})
        if dates:
            date_ranges[sheet] = [min(dates), max(dates), len(df)]

    for sheet in tabs.get('google', []):
        df = pd.read_excel(input_path, sheet_name=sheet)
        c_day, c_acc, c_spend = find_col(df, ['Dia']), find_col(df, ['Nome da conta']), find_col(df, ['Valor gasto'])
        dates = []
        for _, r in df.iterrows():
            d = norm_date(r.get(c_day))
            if not d:
                continue
            dates.append(d)
            acct = clean_str(r.get(c_acc)); key = acct.lower().replace(' ', '')
            if key not in GOOGLE_ACCOUNT_MAP:
                raise ValueError(f'Conta Google sem mapa: {acct}')
            site, vertical, gestor, label = GOOGLE_ACCOUNT_MAP[key]
            val = parse_money(r.get(c_spend)); raw_spend[sheet] += val
            spend.append({'Data': d, 'Site': site, 'Vertical': vertical, 'Gestor': gestor, 'Conta_FB': label, 'Gasto': val})
        if dates:
            date_ranges[sheet] = [min(dates), max(dates), len(df)]

    rev_group: dict[tuple[str, str, str, str], float] = defaultdict(float)
    spend_group: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in revenue:
        rev_group[(r['Data'], r['Site'], r['Vertical'], r['Gestor'])] += r['Receita']
    for s in spend:
        spend_group[(s['Data'], s['Site'], s['Vertical'], s['Gestor'])].append(s)

    rows = []
    for key in sorted(set(rev_group) | set(spend_group)):
        d, site, vertical, gestor = key
        spends = spend_group.get(key, [])
        if spends:
            first = True
            for sp in spends:
                rows.append([d, site, vertical, gestor, sp['Conta_FB'], sp['Gasto'], rev_group.get(key, 0.0) if first else 0.0])
                first = False
        else:
            rows.append([d, site, vertical, gestor, '', 0.0, rev_group.get(key, 0.0)])

    long_rows = [['Data', 'Site', 'Vertical', 'Gestor', 'Conta_FB', 'Gasto', 'Receita']] + rows
    resumo = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        resumo[r[0]][0] += r[5]
        resumo[r[0]][1] += r[6]
    resumo_rows = [['Data', 'Gasto', 'Receita', 'Lucro', 'Margem %']]
    for d, (gasto, receita) in sorted(resumo.items()):
        lucro = receita - gasto
        resumo_rows.append([d, gasto, receita, lucro, '' if not gasto else lucro / gasto])

    total_raw_rev = sum(raw_rev.values()); total_long_rev = sum(r[6] for r in rows)
    total_raw_spend = sum(raw_spend.values()); total_long_spend = sum(r[5] for r in rows)
    validation_rows = [
        ['Item', 'Valor'],
        ['Arquivo', input_path.name],
        ['Gerado em', dt.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')],
        ['Receita bruta', total_raw_rev], ['Receita Long', total_long_rev], ['Diferença receita', total_long_rev - total_raw_rev],
        ['Gasto bruto', total_raw_spend], ['Gasto Long', total_long_spend], ['Diferença gasto', total_long_spend - total_raw_spend],
        ['Páginas ambíguas', len(ambiguous)],
        ['Linhas Long', len(rows)],
    ]
    values = {'Long': long_rows, 'Resumo_dia': resumo_rows, 'Validacao': validation_rows}

    diagnostics_files = {
        'Datas_abas': [['Aba', 'Data inicial', 'Data final', 'Linhas']] + [[k] + v for k, v in sorted(date_ranges.items())],
        'Diagnostico_AV': [['Aba', 'Camada', 'Receita']] + [[a, layer, value] for (a, layer), value in sorted(diagnostics.items())],
        'Paginas_ambiguas': [['Site', 'Página', 'Países detectados']] + ambiguous,
        'Flags': [['Aba', 'Data', 'Origem', 'Flag']] + flags,
        'Redirects_AV': [['Aba', 'Data', 'Site', 'Página', 'País detectado', 'Vertical final', 'Receita']] + redirects,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in {**values, **diagnostics_files}.items():
        with (out_dir / f'{name}.csv').open('w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(data)
    audit = {
        'input': str(input_path), 'tabs': tabs, 'date_ranges': date_ranges,
        'raw_rev': dict(raw_rev), 'raw_spend': dict(raw_spend),
        'total_raw_rev': total_raw_rev, 'total_long_rev': total_long_rev,
        'total_raw_spend': total_raw_spend, 'total_long_spend': total_long_spend,
        'rows_long': len(rows), 'ambiguous': len(ambiguous), 'out_dir': str(out_dir),
    }
    (out_dir / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    return values, audit


def access_token(token_file: Path, auth_mode: str | None = None) -> str:
    global GOOGLE_QUOTA_PROJECT
    mode = (auth_mode or os.environ.get('MGS_GOOGLE_SHEETS_AUTH_MODE', 'service_account')).strip().lower()
    if mode == 'service_account':
        GOOGLE_QUOTA_PROJECT = GOOGLE_AUTH.service_account_project_id()
        return GOOGLE_AUTH.service_account_access_token(GOOGLE_AUTH.SHEETS_SCOPE)
    if mode != 'oauth':
        raise RuntimeError(f'unsupported Google Sheets auth mode: {mode}')
    creds = json.loads(token_file.read_text())
    body = urllib.parse.urlencode({
        'client_id': creds['client_id'], 'client_secret': creds['client_secret'],
        'refresh_token': creds['refresh_token'], 'grant_type': 'refresh_token',
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['access_token']


def sheets_api(method: str, url: str, token: str, data: Any = None) -> Any:
    body = None; headers = {'Authorization': 'Bearer ' + token}
    if GOOGLE_QUOTA_PROJECT:
        headers['x-goog-user-project'] = GOOGLE_QUOTA_PROJECT
    if data is not None:
        body = json.dumps(data).encode(); headers['Content-Type'] = 'application/json; charset=UTF-8'
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode(errors="ignore")[:1500]}') from e


def upload_to_sheet(values: dict[str, list[list[Any]]], sheet_id: str, token_file: Path, auth_mode: str | None = None) -> dict[str, int]:
    token = access_token(token_file, auth_mode)
    meta = sheets_api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=sheets(properties(sheetId,title))', token)
    existing = {s['properties']['title']: s['properties']['sheetId'] for s in meta.get('sheets', [])}
    keep = list(values.keys())
    reqs = []
    if keep[0] not in existing and existing:
        first_title, first_id = next(iter(existing.items()))
        reqs.append({'updateSheetProperties': {'properties': {'sheetId': first_id, 'title': keep[0]}, 'fields': 'title'}})
        existing[keep[0]] = first_id; existing.pop(first_title, None)
    for title in keep:
        if title not in existing:
            reqs.append({'addSheet': {'properties': {'title': title}}})
    if reqs:
        sheets_api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate', token, {'requests': reqs})
    meta = sheets_api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=sheets(properties(sheetId,title))', token)
    existing = {s['properties']['title']: s['properties']['sheetId'] for s in meta.get('sheets', [])}
    delete_reqs = [{'deleteSheet': {'sheetId': sid}} for title, sid in existing.items() if title not in keep]
    if delete_reqs:
        sheets_api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate', token, {'requests': delete_reqs})
    meta = sheets_api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=sheets(properties(sheetId,title))', token)
    sheet_ids = {s['properties']['title']: s['properties']['sheetId'] for s in meta.get('sheets', [])}
    for title in keep:
        sheets_api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{urllib.parse.quote(title)}!A:Z:clear', token, {})
    data = []
    for title, rows in values.items():
        data.append({'range': f"'{title}'!A1", 'majorDimension': 'ROWS', 'values': [['' if (isinstance(x, float) and math.isnan(x)) else x for x in row] for row in rows]})
    sheets_api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchUpdate', token, {'valueInputOption': 'RAW', 'data': data})
    fmt = []
    for title, rows in values.items():
        sid = sheet_ids[title]; width = max(len(r) for r in rows)
        fmt += [
            {'updateSheetProperties': {'properties': {'sheetId': sid, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},
            {'repeatCell': {'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1}, 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.86, 'green': 0.92, 'blue': 1.0}}}, 'fields': 'userEnteredFormat(textFormat,backgroundColor)'}},
            {'autoResizeDimensions': {'dimensions': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': width}}},
        ]
    if 'Resumo_dia' in sheet_ids:
        sid = sheet_ids['Resumo_dia']
        fmt.append({'repeatCell': {'range': {'sheetId': sid, 'startRowIndex': 1, 'startColumnIndex': 4, 'endColumnIndex': 5}, 'cell': {'userEnteredFormat': {'numberFormat': {'type': 'PERCENT', 'pattern': '0.00%'}}}, 'fields': 'userEnteredFormat.numberFormat'}})
    if fmt:
        sheets_api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate', token, {'requests': fmt})
    rb = sheets_api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet?' + urllib.parse.urlencode({'ranges': [f"'{t}'!A:A" for t in keep], 'majorDimension': 'COLUMNS'}, doseq=True), token)
    return {vr['range'].split('!')[0].strip("'"): max(0, len(vr.get('values', [[]])[0]) - 1) for vr in rb.get('valueRanges', [])}


def preflight(input_path: Path) -> dict[str, Any]:
    tabs = detect_tabs(input_path)
    summary = {'input': str(input_path), 'tabs': tabs, 'sheets': []}
    xl = pd.ExcelFile(input_path)
    for sheet in xl.sheet_names:
        df = pd.read_excel(input_path, sheet_name=sheet)
        info = {'sheet': sheet, 'rows': len(df), 'cols': len(df.columns), 'columns': [str(c) for c in df.columns]}
        date_col = find_col(df, ['Date', 'Day', 'Dia'])
        if date_col and len(df):
            dates = [d for d in (norm_date(v) for v in df[date_col].dropna()) if d]
            if dates:
                info['date_min'] = min(dates); info['date_max'] = max(dates)
        summary['sheets'].append(info)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description='Process MGS revenue/spend Excel report into Long/Resumo/Validacao.')
    ap.add_argument('--input', required=True, type=Path)
    ap.add_argument('--sheet-id', help='Google Sheet ID to upload. If omitted, only local files are generated.')
    ap.add_argument('--out-dir', type=Path, help='Local audit/output directory.')
    ap.add_argument('--token-file', type=Path, default=DEFAULT_TOKEN_FILE)
    ap.add_argument('--auth-mode', choices=('oauth', 'service_account'), default=os.environ.get('MGS_GOOGLE_SHEETS_AUTH_MODE', 'service_account'))
    ap.add_argument('--preflight', action='store_true', help='Only inspect workbook structure; do not build/upload.')
    ap.add_argument('--fincgriffin-gb-to-us-g006', action='store_true', help='Cycle-specific override: reassign fincgriffin _gb to us-car-en/g006-d.')
    args = ap.parse_args()

    if args.preflight:
        print(json.dumps(preflight(args.input), ensure_ascii=False, indent=2))
        return 0
    out_dir = args.out_dir or DEFAULT_OUT_ROOT / dt.datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d-%H%M%S')
    values, audit = build_report(args.input, out_dir, fincgriffin_gb_to_us_g006=args.fincgriffin_gb_to_us_g006)
    if abs(audit['total_raw_rev'] - audit['total_long_rev']) > 1e-6 or abs(audit['total_raw_spend'] - audit['total_long_spend']) > 1e-6:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        raise SystemExit('Reconciliação falhou; upload bloqueado')
    result = {'ok': True, 'audit': audit}
    if args.sheet_id:
        result['readback_counts'] = upload_to_sheet(values, args.sheet_id, args.token_file, args.auth_mode)
        result['url'] = f'https://docs.google.com/spreadsheets/d/{args.sheet_id}/edit'
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
