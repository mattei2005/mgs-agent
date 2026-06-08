#!/usr/bin/env python3
"""mgs-p1-runner.py — deterministic P1/application-page runner.

Goal: create GB credit-card P1 pages without Atena doing the workflow manually.
Default mode is dry-run unless --status draft/publish is supplied. Credentials are
resolved only through existing WordPress utility scripts and never printed.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import random
import re
import string
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path("/root/mgs-agent")
SITES_JSON = ROOT / "data/sites.json"
GEN_SCRIPTS = ROOT / "skills/content-generate-rec-p1/scripts"
WP_SCRIPTS = ROOT / "skills/content-publish-wordpress/scripts"
REC_RUNNER = ROOT / "scripts/mgs-rec-runner.py"
P1_CONTRACT = ROOT / "skills/content-generate-rec-p1/contracts/cc-p1.md"
FEATURED_AUDIT_SCRIPT = ROOT / "scripts/audit-featured-image.py"
SUPPORTED_LANGS = {"en", "es", "pt", "tr"}
CONTRACT_MODE = "deterministic_python_from_versioned_spec"


class RunnerError(Exception):
    pass


def ts() -> float:
    return time.perf_counter()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


def run(cmd: List[str], *, timeout: int = 120, allow_fail: bool = False) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if p.returncode != 0 and not allow_fail:
        raise RunnerError(f"Command failed rc={p.returncode}: {' '.join(cmd)}\n{(p.stderr or p.stdout)[:2000]}")
    return p


def run_json(cmd: List[str], *, timeout: int = 120, allow_fail: bool = False) -> Dict[str, Any]:
    p = run(cmd, timeout=timeout, allow_fail=allow_fail)
    text = p.stdout.strip() or p.stderr.strip() or "{}"
    try:
        data = json.loads(text)
    except Exception:
        if allow_fail:
            return {"ok": False, "returncode": p.returncode, "output": text[:1200]}
        raise RunnerError(f"Command did not return JSON: {' '.join(cmd)}\n{text[:1200]}")
    if p.returncode != 0 and not allow_fail:
        raise RunnerError(f"Command failed JSON rc={p.returncode}: {data}")
    return data


def load_site(site_key: str) -> Dict[str, Any]:
    data = json.loads(SITES_JSON.read_text())
    site = data.get(site_key)
    if not site:
        raise RunnerError(f"Site not found: {site_key}")
    return site


def effective_lang(site: Dict[str, Any]) -> str:
    lang = (site.get("language") or "en").strip().lower()
    if lang not in SUPPORTED_LANGS:
        raise RunnerError(f"Unsupported P1 language: {lang}. Supported: {', '.join(sorted(SUPPORTED_LANGS))}")
    return lang


def load_p1_template_contract() -> Dict[str, Any]:
    if not P1_CONTRACT.exists():
        raise RunnerError(f"Missing active P1 editorial contract: {P1_CONTRACT}")
    text = P1_CONTRACT.read_text(errors="ignore")
    return {"path": str(P1_CONTRACT), "bytes": P1_CONTRACT.stat().st_size, "contract_loaded": True, "contract_mode": CONTRACT_MODE, "has_language_gate": "LANGUAGE OF THE FINAL ARTICLE" in text, "has_rec_url_gate": "rec_url" in text, "has_word_count_gate": "900" in text and "1000" in text}


P1_COPY = {
    "en": {"apply":"APPLY NOW","redir":"You will be redirected.","cat":"Credit Card","subtitle":"{card} helps match confirmed card benefits with the way you actually plan to spend and repay.","heads":["Main Benefits","How Does It Work","Costs, Fees and Key Conditions","Reward and Usage Value","Requirements to Qualify for the Card","How to Maximise the Benefits","How to Apply","Is This Card Right for You?"],"title":"{focus}: Costs, Rewards and How to Apply","meta":"{focus} application guide with key costs, rewards, eligibility notes and official issuer apply link before you continue.","tags":["rewards credit card","travel credit card","avios rewards","airport lounge access"]},
    "es": {"apply":"SOLICITAR AHORA","redir":"Serás redirigido.","cat":"Tarjeta de crédito","subtitle":"{card} ayuda a comparar beneficios confirmados con la forma en que realmente piensas gastar y pagar.","heads":["Beneficios principales","Cómo funciona","Costos, comisiones y condiciones clave","Valor de recompensas y uso","Requisitos para calificar","Cómo maximizar los beneficios","Cómo solicitar","¿Esta tarjeta es adecuada para ti?"],"title":"{focus}: costos, recompensas y cómo solicitar","meta":"Guía de {focus} con costos clave, recompensas, elegibilidad y enlace oficial del emisor antes de continuar.","tags":["tarjeta con recompensas","tarjeta para viajes","recompensas avios","acceso a salas vip"]},
    "pt": {"apply":"SOLICITAR AGORA","redir":"Você será redirecionado.","cat":"Cartão de crédito","subtitle":"{card} ajuda a comparar benefícios confirmados com a forma como você pretende gastar e pagar.","heads":["Principais benefícios","Como funciona","Custos, tarifas e condições-chave","Valor de recompensas e uso","Requisitos para se qualificar","Como maximizar os benefícios","Como solicitar","Este cartão é adequado para você?"],"title":"{focus}: custos, recompensas e como solicitar","meta":"Guia do {focus} com custos-chave, recompensas, elegibilidade e link oficial do emissor antes de continuar.","tags":["cartão com recompensas","cartão para viagem","recompensas avios","acesso a sala vip"]},
    "tr": {"apply":"HEMEN BAŞVUR","redir":"Yönlendirileceksiniz.","cat":"Kredi kartı","subtitle":"{card}, onaylanmış kart avantajlarını gerçek harcama ve ödeme planınla karşılaştırmana yardımcı olur.","heads":["Başlıca avantajlar","Nasıl çalışır","Maliyetler, ücretler ve temel koşullar","Ödül ve kullanım değeri","Kart için uygunluk şartları","Avantajları en iyi şekilde kullanma","Nasıl başvurulur","Bu kart senin için doğru mu?"],"title":"{focus}: maliyetler, ödüller ve başvuru","meta":"{focus} için temel maliyetler, ödüller, uygunluk notları ve devam etmeden önce resmi başvuru bağlantısı rehberi.","tags":["ödüllü kredi kartı","seyahat kartı","avios ödülleri","lounge erişimi"]},
}


def copy_for(lang: str) -> Dict[str, Any]:
    if lang not in P1_COPY: raise RunnerError(f"Unsupported P1 language: {lang}")
    return P1_COPY[lang]


def localize_fact(text: str, lang: str) -> str:
    if lang == "en": return str(text)
    repl={"no annual fee":{"es":"sin cuota anual","pt":"sem anuidade","tr":"yıllık ücret yok"},"annual fee":{"es":"cuota anual","pt":"anuidade","tr":"yıllık ücret"},"balance transfer":{"es":"transferencia de saldo","pt":"transferência de saldo","tr":"bakiye transferi"},"purchases":{"es":"compras","pt":"compras","tr":"alışverişler"},"purchase":{"es":"compra","pt":"compra","tr":"alışveriş"},"rewards":{"es":"recompensas","pt":"recompensas","tr":"ödüller"},"travel":{"es":"viaje","pt":"viagem","tr":"seyahat"},"interest":{"es":"intereses","pt":"juros","tr":"faiz"},"eligibility":{"es":"elegibilidad","pt":"elegibilidade","tr":"uygunluk"}}
    out=str(text)
    for src, vals in sorted(repl.items(), key=lambda kv: len(kv[0]), reverse=True): out=re.sub(src, vals[lang], out, flags=re.I)
    return out


def p1_static(lang: str, card: str, fee: str, apr: str, value: str, domain: str) -> Dict[str, str]:
    fee=localize_fact(fee,lang); apr=localize_fact(apr,lang); value=localize_fact(value,lang)
    data={
    "en":[f"The {card} is most relevant when its confirmed benefits match a real spending need, not only a general interest in another credit card.",f"This guide focuses on {value} and how those details affect everyday use, repayment decisions and the application step.",f"Start with the product-specific numbers: {fee}, {apr}, then compare them with the use case you have in mind.","The card works like a standard credit card for eligible purchases, but its real value depends on how the stated benefits match your usual spending.","The issuer may show different rates or limits depending on your circumstances, so the final offer can differ from the representative example.",f"Start with the stated cost: {fee}. Judge that cost against the specific benefit you expect to use.",f"The APR context is {apr}. If a balance remains after any promotional period, interest can change the value calculation quickly.",f"For the {card}, eligibility depends on the issuer’s credit and affordability checks.",f"Use the apply button only after checking the current issuer page for the {card}; the application continues away from {domain}.",f"The {card} may suit you if you can use its confirmed benefits regularly and repay responsibly."],
    "es":[f"{card} es más relevante cuando sus beneficios confirmados responden a una necesidad real de gasto, no solo al interés general por otra tarjeta.",f"Esta guía se centra en {value} y en cómo esos detalles afectan el uso diario, el pago y el momento de solicitar.",f"Empieza por los números específicos del producto: {fee}, {apr}, y compáralos con el uso que tienes en mente.","La tarjeta funciona como una tarjeta de crédito estándar para compras elegibles, pero su valor real depende de cómo los beneficios encajan con tu gasto habitual.","El emisor puede mostrar tasas o límites distintos según tus circunstancias, así que la oferta final puede diferir del ejemplo representativo.",f"Empieza por el costo declarado: {fee}. Evalúalo frente al beneficio específico que esperas usar.",f"El contexto de APR es {apr}. Si queda saldo después de una promoción, los intereses pueden cambiar rápido el cálculo de valor.",f"Para {card}, la elegibilidad depende de las revisiones de crédito y capacidad de pago del emisor.",f"Usa el botón de solicitud solo después de revisar la página actual del emisor para {card}; la solicitud continúa fuera de {domain}.",f"{card} puede convenirte si puedes usar sus beneficios confirmados con frecuencia y pagar de forma responsable."],
    "pt":[f"{card} é mais relevante quando seus benefícios confirmados resolvem uma necessidade real de gasto, não apenas o interesse genérico por outro cartão.",f"Este guia foca em {value} e em como esses detalhes afetam o uso diário, o pagamento e a etapa de solicitação.",f"Comece pelos números específicos do produto: {fee}, {apr}, e compare com o uso que você tem em mente.","O cartão funciona como um cartão de crédito padrão para compras elegíveis, mas o valor real depende de como os benefícios combinam com seus gastos habituais.","O emissor pode mostrar taxas ou limites diferentes conforme suas circunstâncias, então a oferta final pode divergir do exemplo representativo.",f"Comece pelo custo declarado: {fee}. Compare esse custo com o benefício específico que você espera usar.",f"O contexto de APR é {apr}. Se restar saldo após uma promoção, os juros podem mudar rapidamente o cálculo de valor.",f"Para {card}, a elegibilidade depende das análises de crédito e capacidade de pagamento do emissor.",f"Use o botão de solicitação só depois de conferir a página atual do emissor para {card}; a solicitação continua fora de {domain}.",f"{card} pode fazer sentido se você conseguir usar seus benefícios confirmados com frequência e pagar com responsabilidade."],
    "tr":[f"{card}, onaylanmış avantajları gerçek bir harcama ihtiyacına uyduğunda en anlamlı hale gelir; amaç yalnızca yeni bir kredi kartı almak değildir.",f"Bu rehber {value} konusuna ve bu ayrıntıların günlük kullanım, ödeme kararı ve başvuru adımını nasıl etkilediğine odaklanır.",f"Önce ürüne özgü rakamlara bak: {fee}, {apr}; sonra bunları aklındaki kullanım senaryosuyla karşılaştır.","Kart, uygun alışverişlerde standart bir kredi kartı gibi çalışır; gerçek değeri ise belirtilen avantajların normal harcamalarına ne kadar uyduğuna bağlıdır.","Kartı veren kurum koşullarına göre farklı oranlar veya limitler gösterebilir; bu yüzden son teklif temsilî örnekten ayrılabilir.",f"Belirtilen maliyetle başla: {fee}. Bu maliyeti kullanmayı beklediğin özel avantajla karşılaştır.",f"APR bağlamı {apr}. Promosyon dönemi sonrası bakiye kalırsa faiz değer hesabını hızla değiştirebilir.",f"{card} için uygunluk, kartı veren kurumun kredi ve ödeme gücü kontrollerine bağlıdır.",f"Başvuru düğmesini yalnızca {card} için güncel resmi sayfayı kontrol ettikten sonra kullan; başvuru {domain} dışına devam eder.",f"{card}, onaylanmış avantajlarını düzenli kullanabiliyor ve sorumlu şekilde geri ödeyebiliyorsan uygun olabilir."]}
    return dict(zip(["intro1","intro2","intro3","work1","work2","cost1","cost2","qual1","apply1","right1"], data[lang]))


def load_rec_helpers():
    spec = importlib.util.spec_from_file_location("mgs_rec_runner", REC_RUNNER)
    if not spec or not spec.loader:
        raise RunnerError("Cannot import REC runner helpers")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def get_public(url: str) -> str:
    r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code >= 400:
        raise RunnerError(f"Public GET failed {r.status_code}: {url}")
    return r.text


def post_id_from_public_html(public_html: str, rec_url: str) -> int:
    m = re.search(r"postid-(\d+)", public_html)
    if m:
        return int(m.group(1))
    # Fallback: public REST by slug is broken on some sites, but keep a helpful error.
    raise RunnerError(f"Could not detect REC post ID from public HTML: {rec_url}")


def p1_slug_from_rec_buttons(public_html: str, rec_raw: str, site_domain: str) -> Optional[str]:
    """Return the P1 slug already linked from the REC buttons, if present.

    REC pages may be created before the P1 exists. In that case, the REC button
    URL is the source of truth for the future P1 slug. Do not re-infer a shorter
    slug from the card name when the REC already points to an apply-now URL.
    """
    haystack = "\n".join([public_html or "", rec_raw or ""])
    candidates: List[str] = []
    patterns = [
        rf"https?://{re.escape(site_domain)}/(apply-now-[a-z0-9-]+)/?",
        r"/(apply-now-[a-z0-9-]+)/?",
    ]
    for pat in patterns:
        for m in re.finditer(pat, haystack, flags=re.I):
            slug = m.group(1).strip("/").lower()
            if slug not in candidates:
                candidates.append(slug)
    return candidates[0] if candidates else None


def resolve_credentials(site_key: str) -> Dict[str, Any]:
    return run_json([str(WP_SCRIPTS / "resolve-credentials.sh"), site_key], timeout=90)


def wp_get_post(site_key: str, post_id: int, fields: str = "id,title,content,featured_media,link,tags,categories,slug") -> Dict[str, Any]:
    creds = resolve_credentials(site_key)
    url = creds["wp_url"].rstrip("/") + f"/wp-json/wp/v2/posts/{post_id}?context=edit&_fields={urllib.parse.quote(fields)}"
    r = requests.get(url, auth=(creds["username"], creds["password"]), timeout=25)
    if r.status_code >= 400:
        raise RunnerError(f"WP GET post failed {r.status_code}: {r.text[:800]}")
    return r.json()


def parse_card_from_rec(raw: str, rendered: str, rec_title: str) -> Dict[str, Any]:
    block = re.search(r"<!-- wp:lazyblock/credit-card\s+(\{.*?\})\s+/-->", raw, re.S)
    payload: Dict[str, Any] = {}
    if block:
        try:
            payload = json.loads(block.group(1))
        except Exception:
            payload = {}
    card_name = payload.get("titulo") or html.unescape(re.sub(r"<[^>]+>", " ", rec_title)).strip()
    if card_name and not card_name.lower().endswith("card") and "barclaycard" in card_name.lower():
        # Do not force Card for all issuers, but Barclaycard official pages often use it.
        card_name = card_name + " Card"
    card_url = None
    card_id = None
    if payload.get("imagem"):
        try:
            media = json.loads(urllib.parse.unquote(payload["imagem"]))
            card_url = media.get("url") or media.get("link")
            card_id = media.get("id")
        except Exception:
            pass
    if not card_url:
        m = re.search(r"https?://[^\"'<>\s)]+(?:card|barclaycard|avios)[^\"'<>\s)]*\.(?:png|jpg|jpeg|webp)", rendered, re.I)
        if m:
            card_url = m.group(0)
    return {
        "card_name": card_name,
        "card_url": card_url,
        "card_id": int(card_id) if card_id else None,
        "tag10": payload.get("tag10") or "Card benefits",
        "tag2": payload.get("tag2") or "Credit card",
        "descriptor": payload.get("texto") or f"Learn more about the {card_name}.",
    }


def infer_card_slug(rec_url: str, card_name: str) -> str:
    path = urllib.parse.urlparse(rec_url).path.strip("/")
    m = re.search(r"rec-[a-z]{2}-[a-z]+-(.+)$", path)
    if m:
        slug = re.sub(r"-\d+$", "", m.group(1))
        return slug
    slug = slugify(card_name)
    return re.sub(r"-card$", "", slug)


def meaningful_card_terms(card_name: str) -> List[str]:
    stop = {"credit", "card", "the", "and", "visa", "mastercard", "platinum", "classic", "gold"}
    terms: List[str] = []
    for word in re.sub(r"[^A-Za-z0-9 ]", " ", card_name).lower().split():
        if len(word) >= 3 and word not in stop and word not in terms:
            terms.append(word)
    return terms[:6]


def official_source_has_content(official_url: str, text: str, card_name: str = "") -> Tuple[bool, str]:
    """Reject issuer URLs that return a branded error/404/search page or generic category page."""
    clean = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip().lower()
    if not clean or len(clean) < 500:
        return False, "official source has no meaningful body"
    product_terms = [
        "credit card", "representative apr", "annual fee", "monthly fee", "purchase rate",
        "eligibility", "apply", "rewards", "cashback", "avios", "mastercard", "visa",
    ]
    product_hits = [t for t in product_terms if t in clean]
    name_terms = meaningful_card_terms(card_name) if card_name else []
    error_markers = [
        "page not found", "we can’t find that page", "we can't find that page",
        "try our search tool", "internet banking - error",
        "we are sorry an error has occurred", "error 1007", "access denied",
        "cloudflare", "temporarily unavailable",
    ]
    for marker in error_markers:
        if marker in clean:
            return False, f"official source appears to be an error page: {marker}"
    if "sorry about this" in clean and len(product_hits) < 2 and not any(t in clean for t in name_terms):
        return False, "official source appears to be an error page: sorry about this"
    if len(product_hits) < 2:
        return False, "official source does not expose enough product content"
    if name_terms and not any(t in clean for t in name_terms):
        return False, "official source does not mention the requested product/issuer terms"
    return True, "ok"


def validate_no_review(fields: Dict[str, str]) -> None:
    offenders = [name for name, value in fields.items() if re.search(r"\breview\b", value or "", flags=re.I)]
    if offenders:
        raise RunnerError("Review hard gate failed in " + ", ".join(offenders))


def compact_focus(card_name: str) -> str:
    words = [w for w in re.sub(r"[^A-Za-z0-9 ]", " ", card_name).split() if w.lower() not in {"credit", "card", "the"}]
    return " ".join(words[:3]) if words else card_name[:40]


def validate_seo_fields(title: str, meta: str, focus: str) -> None:
    validate_no_review({"title": title, "meta": meta, "focus": focus})
    if len(title) > 60 or not title.strip():
        raise RunnerError(f"P1 title length invalid: {len(title)}")
    if focus.lower() not in title.lower():
        raise RunnerError(f"P1 title missing focus keyphrase: {focus}")
    # Contract v2: P1 meta description must be 130-150 visible characters.
    if len(meta) < 130 or len(meta) > 150:
        raise RunnerError(f"P1 meta length invalid: {len(meta)}")
    if len(focus.split()) > 4:
        raise RunnerError(f"P1 focus keyphrase too long: {focus}")


def validate_taxonomy_names(tag_names: List[str], expected_lang: str) -> None:
    bad = [t for t in tag_names if "-" in t]
    if bad:
        raise RunnerError(f"Tag names must use spaces, not hyphens: {bad}")
    missing = sorted({"atena_agent", f"lang_{expected_lang}"} - set(tag_names))
    if missing:
        raise RunnerError(f"Missing mandatory tags: {missing}")


def validate_yoast_score(score: Dict[str, Any]) -> None:
    if not score or score.get("status") not in {"ok", "success", "OK"}:
        raise RunnerError(f"Yoast scorer failed or returned non-ok status: {score}")
    seo = score.get("seo_score")
    read = score.get("readability_score")
    if seo is None or read is None:
        raise RunnerError(f"Yoast scorer missing scores: {score}")
    if int(seo) < 70 or int(read) < 70:
        raise RunnerError(f"Yoast scores below green threshold: seo={seo} readability={read}")


def fetch_official_source_text(official_url: str, card_name: str = "") -> Tuple[int, str, str]:
    """Fetch official product text, using a reader fallback for issuer geo/bot error shells.

    The canonical URL remains the issuer URL. The reader is only a rendering aid
    for the same official URL and must still expose product content.
    """
    rec = load_rec_helpers()
    status, text = rec.fetch_reference_text(official_url)
    has_content, _ = official_source_has_content(official_url, text, card_name)
    if has_content:
        return status, text, official_url
    reader_url = "https://r.jina.ai/http://" + official_url
    try:
        r = requests.get(reader_url, timeout=35, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code < 400:
            ok, _reason = official_source_has_content(official_url, r.text, card_name)
            if ok:
                return r.status_code, r.text, reader_url
    except Exception:
        pass
    return status, text, official_url


def preflight_official_source(official_url: str, card_name: str = "") -> None:
    status, text, source_fetch_url = fetch_official_source_text(official_url, card_name)
    has_content, source_reason = official_source_has_content(official_url, text, card_name)
    if not has_content:
        raise RunnerError(f"Official source URL has no usable product content; ask Raquel/Rodolfo for the correct official link before publishing. url={official_url} reason={source_reason}")


def extract_official_data(card_name: str, official_url: str, explicit_benefits: List[str], annual_fee: Optional[str], apr: Optional[str]) -> Dict[str, Any]:
    status, text, source_fetch_url = fetch_official_source_text(official_url, card_name)
    has_content, source_reason = official_source_has_content(official_url, text, card_name)
    if not has_content:
        raise RunnerError(f"Official source URL has no usable product content; ask Raquel/Rodolfo for the correct official link before publishing. url={official_url} reason={source_reason}")
    rec = load_rec_helpers()
    try:
        data = rec.extract_card_data_with_llm(card_name, official_url, text)
    except Exception as e:
        if not (explicit_benefits and annual_fee and apr):
            raise
        data = {
            "card_name": card_name,
            "annual_fee": annual_fee,
            "apr": apr,
            "benefits": explicit_benefits[:6],
            "competitors": [],
            "tag10": "Avios rewards",
            "tag2": annual_fee[:25],
            "descriptor": "A UK travel credit card with Avios rewards and issuer terms.",
            "extraction_mode": f"explicit_facts_after_short_fetch:{type(e).__name__}",
            "source_url": official_url,
        }
    if explicit_benefits:
        data["benefits"] = explicit_benefits[:6]
    if annual_fee:
        data["annual_fee"] = annual_fee
    if apr:
        data["apr"] = apr
    data["fetch_status"] = status
    # Product-specific deterministic improvements from official text.
    clean = re.sub(r"\s+", " ", text)
    if re.search(r"25,000\s+Avios", clean, re.I):
        add_unique(data["benefits"], "New Barclaycard customers can collect 25,000 Avios after spending £3,000 in the first three months.")
    if re.search(r"1\.5\s+Avios", clean, re.I):
        add_unique(data["benefits"], "Collect 1.5 Avios for every £1 spent on eligible purchases.")
    if re.search(r"cabin upgrade voucher", clean, re.I):
        add_unique(data["benefits"], "Spend £10,000 within 12 months and choose between a British Airways cabin upgrade voucher or 7,000 bonus Avios.")
    if re.search(r"1,000 airport lounges|£24 per lounge pass", clean, re.I):
        add_unique(data["benefits"], "Access over 1,000 airport lounges worldwide at a discounted rate of £24 per lounge pass, per person.")
    m = re.search(r"Representative\s+([0-9.]+%\s+APR).*?Purchase rate\s+([0-9.]+%[^£]{0,30}).*?Monthly fee\s+(£\d+)", clean, re.I)
    if m:
        data["apr"] = f"Representative {m.group(1)} variable; purchase rate {m.group(2).strip()}"
        data["annual_fee"] = f"{m.group(3)} monthly fee"
    elif "£20" in clean and "monthly fee" in clean.lower():
        data["annual_fee"] = "£20 monthly fee"
    return data


def add_unique(items: List[str], value: str) -> None:
    low = {i.lower() for i in items}
    if value.lower() not in low:
        items.append(value)


def ensure_card_local(card_url: str, card_slug: str) -> str:
    ext = Path(urllib.parse.urlparse(card_url).path).suffix or ".png"
    out = Path(tempfile.gettempdir()) / f"p1-card-{card_slug}{ext}"
    r = requests.get(card_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code >= 400 or not r.content:
        raise RunnerError(f"Card image download failed {r.status_code}: {card_url}")
    out.write_bytes(r.content)
    return str(out)


def make_exact_featured(card_path: str, card_slug: str) -> str:
    # Generate the P1 contextual advertising scene directly. Do not blur the
    # scene and paste a card-only overlay: P1 requires the visual layer order
    # scenario -> card -> foreground person, with depth and no cropped card.
    gen = run_json([str(GEN_SCRIPTS / "generate-featured-image.sh"), f"p1-{card_slug}", card_path], timeout=180)
    scene_path = gen.get("path")
    if not scene_path or not Path(scene_path).exists():
        raise RunnerError(f"Featured generator did not create a file: {gen}")
    try:
        from PIL import Image
    except Exception as e:
        raise RunnerError(f"PIL unavailable for featured normalization: {e}")
    bg = Image.open(scene_path).convert("RGB").resize((1280, 720))
    out = Path(tempfile.gettempdir()) / f"featured-p1-{card_slug}.jpg"
    bg.save(out, quality=91, optimize=True)
    return str(out)


def upload_image(site_key: str, image_path: str, filename: str) -> Dict[str, Any]:
    return run_json([str(WP_SCRIPTS / "upload-image.sh"), site_key, image_path, filename], timeout=120)


def cleanup_created_media(site_key: str, media_created: List[Dict[str, Any]]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for media in media_created:
        mid = media.get("id")
        if not mid:
            continue
        try:
            res = run_json([str(WP_SCRIPTS / "delete-media-safe.sh"), site_key, str(mid)], timeout=90, allow_fail=True)
            results.append({"id": mid, "role": media.get("role"), "result": res})
        except Exception as exc:
            results.append({"id": mid, "role": media.get("role"), "error": str(exc)})
    return {"created_count": len(media_created), "attempted_count": len(results), "items": results}


def rand_block_id() -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


def media_payload(media_id: int, media_url: str, title: str) -> str:
    obj = {"alt":"","title":title,"caption":"","description":{"raw":"","rendered":""},"id":int(media_id),"link":media_url,"url":media_url,"sizes":""}
    return urllib.parse.quote(json.dumps(obj, separators=(",", ":")), safe="")


def clean_sentence_punctuation(text: Any) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\s*\.\.\.$", "...", text)
    text = re.sub(r"\.\s*\.\.\.$", "...", text)
    text = re.sub(r",\s*\.$", ".", text)
    text = re.sub(r",\s*\.\.\.$", "...", text)
    if text and not re.search(r"(\.|!|\?|\.\.\.)$", text):
        text += "."
    return text


GENERIC_VISIBLE_VALUE_RE = re.compile(
    r"\b(not stated|not provided|not available|n/?a|unknown|check issuer terms|check terms|official product page|latest confirmed benefit details)\b",
    re.I,
)


def is_generic_visible_value(value: Any) -> bool:
    raw = html.unescape(str(value or "")).strip()
    if not raw:
        return True
    return bool(GENERIC_VISIBLE_VALUE_RE.search(raw))


def require_specific_visible_value(value: Any, field: str) -> str:
    raw = html.unescape(str(value or "")).strip()
    if is_generic_visible_value(raw):
        raise RunnerError(f"{field} is generic/unusable for visible content: {raw!r}; fetch the official fact or provide verified request facts")
    return raw


def card_ui_tag(text: Any, fallback: str = "Cashback rewards", *, card_name: str = "", annual_fee: str = "") -> str:
    """Short benefit-led LazyBlock tag. Block numeric fragments and redundant category labels."""
    value = html.unescape(str(text or "")).strip()
    # Split only on semicolon/comma/"and". Do not split decimal values like 2.99.
    value = re.split(r"[;,]|\s+ and \s+", value, maxsplit=1, flags=re.I)[0].strip()
    value = re.sub(r"\bcard features\b", "", value, flags=re.I).strip()
    value = re.sub(r"\s+", " ", value).strip(" .;:,!")
    low = value.lower()
    name_low = (card_name or "").lower()
    fee_low = (annual_fee or "").lower()
    bad = (
        is_generic_visible_value(value)
        or low in {"credit card", "card benefits", "features", "official terms", "transfer fee", "annual fee"}
        or bool(re.fullmatch(r"[0-9.£%\s]+", value))
        or ("fee" in low and bool(re.search(r"\d", low)))
        or (low in {"balance transfer", "balance transfers"} and "balance transfer" in name_low)
        or (low == "no fees" and any(t in fee_low for t in ["fee", "2.99", "annual", "minimum"]))
    )
    if bad:
        value = fallback
    value = re.sub(r"\s+", " ", value).strip(" .;:,!")
    if is_generic_visible_value(value) or re.fullmatch(r"[0-9.£%\s]+", value):
        raise RunnerError(f"LazyBlock tag is generic/unusable: {value!r}")
    return value[:25].rstrip(" .;:,")


def derive_lazyblock_tags(card_name: str, benefits: List[str], annual_fee: str = "") -> Tuple[str, str, str]:
    """Choose commercial, non-redundant card tags and descriptor from current benefits."""
    joined = " ".join([card_name] + benefits).lower()
    fee_low = (annual_fee or "").lower()
    tags: List[str] = []
    descriptor = "Designed around confirmed benefits and practical repayment use."

    month = re.search(r"0%[^.]{0,80}?(\d{1,2})\s*months?", joined)
    if ("balance transfer" in joined or "0% balance" in joined) and month:
        tags.append(f"{month.group(1)} mo 0%")
        descriptor = "Helps move existing card debt into a clearer repayment window."
    elif "balance transfer" in joined or "0% balance" in joined:
        tags.append("0% transfers")
        descriptor = "Helps move existing card debt into a clearer repayment plan."
    if "no nationwide fees" in joined or "purchases abroad" in joined or "foreign transaction" in joined or "abroad" in joined:
        tags.append("No FX fees")
    if "0%" in joined and "purchase" in joined:
        tags.append("0% purchases")
    if "cashback" in joined:
        tags.append("Cashback")
        descriptor = "Turns eligible everyday spending into cashback value."
    if any(t in joined for t in ["avios", "travel", "lounge", "hotel", "points"]):
        tags.append("Travel rewards")
        descriptor = "Connects planned travel spending with usable card rewards."
    if "no annual fee" in joined or ("annual fee" in fee_low and "0" in fee_low):
        tags.append("No annual fee")

    clean: List[str] = []
    for tag in tags:
        try:
            t = card_ui_tag(tag, tag, card_name=card_name, annual_fee=annual_fee)
        except RunnerError:
            continue
        if t.lower() not in [x.lower() for x in clean]:
            clean.append(t)
    while len(clean) < 2:
        clean.append("Everyday value" if not clean else "Apply online")
    return clean[0], clean[1], descriptor


def card_ui_descriptor(card_data: Dict[str, Any], fallback: str) -> str:
    benefits = [str(b) for b in (card_data.get("benefits") or [])]
    joined = " ".join(benefits).lower()
    if "cashback" in joined:
        desc = "Earn cashback on eligible purchases."
    elif any(term in joined for term in ["avios", "travel", "points", "marriott", "bonvoy", "elite night"]):
        desc = "Make regular trips and bookings feel more rewarding."
    elif "no annual fee" in joined or "no fee" in joined:
        desc = "A no-annual-fee card for everyday spend."
    else:
        desc = fallback
    desc = clean_sentence_punctuation(desc)
    if len(desc) > 70:
        desc = desc[:69].rsplit(" ", 1)[0].rstrip(" ,;:") + "."
    return desc


def lazy_credit_card_p1(site: Dict[str, Any], card_name: str, card_slug: str, card_id: int, card_url: str, card_data: Dict[str, Any], official_url: str, button_hex: str, lang: str) -> str:
    b = rand_block_id()
    c = copy_for(lang)
    payload = {
        "imagem": media_payload(card_id, card_url, f"card-{card_slug}"),
        "categoria": c["cat"],
        "titulo": card_name,
        "tag10": card_ui_tag(card_data.get("tag10"), c["tags"][0], card_name=card_name, annual_fee=str(card_data.get("annual_fee") or "")),
        "tag2": card_ui_tag(card_data.get("tag2") or card_data.get("annual_fee"), c["tags"][0], card_name=card_name, annual_fee=str(card_data.get("annual_fee") or "")),
        "texto": localize_fact(card_ui_descriptor(card_data, card_data.get("descriptor") or f"Learn more about the {card_name}."), lang),
        "botao-texto": c["apply"],
        "siteXfora": c["redir"],
        "botao-url": official_url,
        "color-botao": button_hex,
        "blockId": b,
        "blockUniqueClass": f"lazyblock-credit-card-{b}",
    }
    return "<!-- wp:lazyblock/credit-card " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + " /-->"


def wp_paragraph(text: str) -> str:
    return f"<!-- wp:paragraph -->\n<p>{html.escape(text)}</p>\n<!-- /wp:paragraph -->"


def wp_paragraph_raw(inner_html: str) -> str:
    return f"<!-- wp:paragraph -->\n<p>{inner_html}</p>\n<!-- /wp:paragraph -->"


def wp_heading(text: str) -> str:
    return f"<!-- wp:heading -->\n<h2 class=\"wp-block-heading\">{html.escape(text)}</h2>\n<!-- /wp:heading -->"


def wp_details(summary: str, paragraphs: List[str]) -> str:
    inner = "\n\n".join(wp_paragraph(p) for p in paragraphs if str(p).strip())
    return (
        '<!-- wp:details -->\n'
        '<details class="wp-block-details"><summary>' + html.escape(summary) + '</summary>\n'
        + inner +
        '\n</details>\n<!-- /wp:details -->'
    )


def infer_p1_positioning(card_name: str, benefits: List[str]) -> Dict[str, str]:
    """Return benefit-specific P1 copy so scaled pages do not read as duplicated templates."""
    joined = " ".join(benefits).lower()
    name_l = card_name.lower()
    if "amazon" in joined or "amazon" in name_l:
        return {
            "subtitle_tail": "turns Amazon shopping into rewards, a welcome gift and 0% purchases.",
            "use_case": "people who already spend through Amazon and want those purchases to generate direct reward value",
            "value_focus": "Amazon-linked benefits, the app-first setup and the main repayment points",
            "reward_heading": "Amazon Rewards and Purchase Value",
            "reward_1": "This is not a miles card trying to feel premium. Its value is simpler: frequent Amazon shoppers can turn familiar purchases into direct rewards.",
            "reward_2": "The key question is how much of your normal basket already goes through Amazon, because that is where the card can feel more useful.",
            "reward_3": "Prime members should look closely at eligible shopping events such as Prime Day, when the temporary boost can make planned purchases more rewarding.",
            "max_1": "Use it first for Amazon and everyday purchases you were already going to make. That keeps the reward value connected to real behaviour, not extra borrowing.",
            "max_2": "Treat the welcome gift and rewards as a bonus, not a reason to carry a balance. Interest can wipe out the benefit quickly if repayment slips.",
            "max_3": "Recheck the reward rules around Prime events, the welcome gift and the first-year earn rate so you know exactly which purchases count.",
            "right_1": "For Amazon-focused spending, estimate how often you actually buy on Amazon, whether you have Prime and how fast you usually repay purchases.",
            "right_2": "Check whether the reward rules still match your shopping habits before submitting the application.",
            "right_3": "A strong fit usually means regular Amazon use, comfort with app-based account management and a repayment plan that protects the reward value.",
        }
    if any(t in joined or t in name_l for t in ["balance transfer", "0% balance", "balance-transfer"]):
        return {
            "subtitle_tail": "helps reduce interest pressure and simplify repayments by moving existing card debt into one clearer plan.",
            "use_case": "people who are juggling existing card debt, interest charges or multiple repayments and want a clearer route to pay the balance down",
            "value_focus": "interest relief, repayment simplification, transfer fee, promotional window and the discipline needed before interest returns",
            "reward_heading": "Debt Relief, Interest Pressure and Repayment Control",
            "reward_1": "The strongest value is practical: a balance-transfer window can reduce interest pressure while you organise existing debt into a more manageable repayment plan.",
            "reward_2": "The transfer fee still matters, so the emotional relief only becomes real value when the fee is smaller than the interest likely to be avoided.",
            "reward_3": "This card should be framed as a repayment tool first. Purchases and extra spending need to stay secondary so the transferred balance remains the priority.",
            "max_1": "Start with the total debt being moved, then divide it by the promotional months to set a monthly repayment target before applying.",
            "max_2": "Use the card to simplify repayments, not to create a new spending habit that competes with the transferred balance.",
            "max_3": "Check the summary box for the transfer deadline, transfer fee, post-promotional APR and any purchase-rate rules before relying on the offer.",
            "right_1": "This card is most useful when you have existing card debt and a realistic plan to clear or reduce it before interest returns.",
            "right_2": "Compare it with another balance-transfer option by total repayment cost, monthly target and the practical length of the 0% window.",
            "right_3": "A good fit usually means the transfer fee, promotional period and monthly repayment target all support the same goal: fewer interest charges and simpler debt organisation.",
        }
    if any(t in joined or t in name_l for t in ["avios", "lounge", "hotel", "travel", "companion voucher", "travel spending", "travel reward"]):
        return {
            "subtitle_tail": "can make travel, overseas purchases and partner spending feel more useful when they already fit your routine.",
            "use_case": "people who already book trips, hotels, transport or overseas purchases and want those costs to create more practical value",
            "value_focus": "travel rewards, partner value, foreign purchase fees, annual cost and repayment behaviour",
            "reward_heading": "Travel Rewards That Feel Useful in Real Trips",
            "reward_1": "If you already pay for flights, hotels, transport or travel bookings during the year, earning value on those purchases can help your travel budget go further.",
            "reward_2": "Using the card abroad without extra foreign transaction fees can make everyday travel spending feel more predictable and easier to manage.",
            "reward_3": "The strongest fit is someone who wants rewards as a useful bonus on travel spending they already planned, not a reason to stretch the trip budget.",
            "max_1": "Use it where the travel or partner value is clear: flights, hotels, transport, travel agents or selected retailers you were already planning to use.",
            "max_2": "Keep repayments current so interest does not erase the travel value, foreign-fee saving or cashback you expected from the trip.",
            "max_3": "Check participating brands, travel categories, foreign purchase rules and exclusions before relying on headline value.",
            "right_1": "Estimate how much travel, partner and overseas spending would realistically go on the card in a normal year.",
            "right_2": "Check whether the participating brands and overseas purchase rules still match your plans before applying.",
            "right_3": "A good fit usually means regular travel or partner spending, no need to carry debt, and enough discipline to preserve the reward value.",
        }
    if any(t in joined for t in ["low interest", "low rate", "12.9%", "no annual fee", "foreign transaction"]):
        return {
            "subtitle_tail": "may suit people who want simpler costs, lower-rate positioning and practical overseas purchase value.",
            "use_case": "people who care more about predictable costs and simple fees than points or premium perks",
            "value_focus": "representative APR, annual fee, overseas purchase fees and repayment considerations",
            "reward_heading": "Low-Rate and Overseas Purchase Value",
            "reward_1": "The product is best judged through cost control rather than reward chasing. The representative APR and annual fee shape how manageable it may feel over time.",
            "reward_2": "No foreign transaction fee on purchases can make overseas spending more predictable, although cash withdrawals and local fees still need separate checks.",
            "reward_3": "A rewards card may be better if you always pay in full and care more about cashback, miles or points.",
            "max_1": "Start with planned spending and a realistic repayment plan. The lower-rate positioning only helps when balances stay manageable.",
            "max_2": "Use overseas purchase benefits carefully and avoid assuming cash withdrawals receive the same fee treatment.",
            "max_3": "Check the official summary box for the final personal rate, balance transfer rules and any fees before applying.",
            "right_1": "Estimate whether rate control, no annual fee and overseas purchase use matter more than rewards in a normal year.",
            "right_2": "Check whether the final APR and credit limit still match your budget before submitting the application.",
            "right_3": "A careful comparison should include repayment behaviour, overseas use, annual fee, final APR and whether rewards are actually more important.",
        }
    return {
        "subtitle_tail": "explains its confirmed benefits, costs and application steps before you apply.",
        "use_case": "people whose normal spending matches the card’s confirmed strongest benefit",
        "value_focus": "confirmed benefits, costs, eligibility and repayment considerations",
        "reward_heading": "Rewards and Everyday Value",
        "reward_1": "The real value depends on how often you would use the confirmed benefit in ordinary spending.",
        "reward_2": "Compare the benefit with your repayment habits so interest does not outweigh the card’s value.",
        "reward_3": "A simpler card may be better if the headline feature does not match your routine.",
        "max_1": "Start with spending you can repay comfortably. Benefits should follow existing behaviour, not create extra borrowing.",
        "max_2": "Pay close attention to payment dates and statement balances so fees or interest do not reduce value.",
        "max_3": "Check the official rules regularly because terms, exclusions and availability can change.",
        "right_1": "Estimate how often you would use the strongest confirmed benefit during a normal year.",
        "right_2": "Check whether the rules still match your needs before submitting the application.",
        "right_3": "A careful comparison should include benefit use, repayment behaviour and total cost.",
    }


def p1_perceived_benefit(raw: str, *, card_name: str = "") -> str:
    text = re.sub(r"\s+", " ", str(raw or "")).strip().rstrip(".")
    low = text.lower()
    name_low = card_name.lower()
    if not text:
        return "Use the card only where the main benefit clearly matches your normal spending."
    if "foreign transaction" in low or "abroad" in low or "overseas" in low:
        return "During international trips, eligible card purchases can avoid the usual foreign transaction fee, making everyday travel spending feel easier to predict."
    if "15%" in low and "reward" in low:
        return "Up to 15% back with chosen partner retailers matters most when those partners match travel, transport or everyday purchases you already planned."
    if "annual fee" in low and ("no" in low or "£0" in low):
        return "With no annual fee, the card can be easier to keep for occasional travel or partner rewards without needing heavy monthly use to justify a yearly cost."
    if "travel" in low and ("reward" in low or "partner" in low):
        return "Travel rewards are most useful when they attach to real plans — hotels, transport, trips or partner spending — rather than encouraging extra purchases."
    if "reward" in low or "cashback" in low or "points" in low:
        if "2,500" in low or "welcome" in low:
            return "The welcome bonus can feel useful after your first transaction, as long as the card already fits purchases you planned to make."
        if "pay with rewards" in low or "offset" in low:
            return "Using points to offset purchases can make rewards feel more practical than collecting points with no clear everyday use."
        if "mastercard" in low or "online" in low or "recurring" in low:
            return "Earning points across familiar Mastercard purchases can make ordinary spending feel more rewarding over time."
        return "The reward only becomes real value when it comes from spending you would have made anyway and can repay comfortably."
    if "fee" in low or "apr" in low:
        return f"{text}. Read this as part of the total cost, because interest or fees can quickly reduce any benefit."
    if "travel" in name_low:
        return f"{text}. In practice, this matters most when it supports planned trips, overseas purchases or partner spending."
    return text



def count_keyword_occurrences(card_name: str, *texts: str) -> int:
    pattern = re.compile(r"\b" + re.escape(card_name).replace(r"\ ", r"\s+") + r"\b", re.I)
    return sum(len(pattern.findall(t or "")) for t in texts)


def validate_p1_keyword_count(card_name: str, title: str, subtitle: str, body: str, meta: str) -> int:
    total = count_keyword_occurrences(card_name, title, subtitle, body, meta)
    if total < 5 or total > 8:
        raise RunnerError(f"P1 keyword count outside contract v2 range 5-8: {total}")
    return total

def generate_p1_body(site: Dict[str, Any], card_name: str, card_slug: str, card_data: Dict[str, Any], official_url: str, featured_id: int, featured_url: str, card_id: int, card_url: str, button_hex: str, contract: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    lang = effective_lang(site); c = copy_for(lang)
    fee = require_specific_visible_value(card_data.get("annual_fee"), "annual_fee"); apr = require_specific_visible_value(card_data.get("apr"), "apr")
    benefits = [b for b in (card_data.get("benefits") or []) if b and not is_generic_visible_value(b)][:6]
    if len(benefits) < 4: raise RunnerError("P1 requires at least 4 specific benefits/facts; generic benefit padding is blocked")
    benefits_l = [localize_fact(str(b), lang) for b in benefits]
    tag10, tag2, descriptor_default = derive_lazyblock_tags(card_name, benefits, fee)
    card_data["tag10"] = localize_fact(tag10, lang); card_data["tag2"] = localize_fact(tag2, lang)
    positioning = infer_p1_positioning(card_name, benefits); value_focus = localize_fact(positioning["value_focus"], lang)
    card_data["descriptor"] = localize_fact(card_data.get("descriptor") or descriptor_default, lang)
    subtitle = c["subtitle"].format(card=card_name)
    if len(subtitle) > 100:
        subtitle = subtitle[:97].rsplit(" ", 1)[0].rstrip(" ,;:") + "."
    st = p1_static(lang, card_name, fee, apr, value_focus, site.get("domain", ""))
    # Contract v2 keeps keyword use controlled (5-8 total). Keep the first
    # introduction mention, then use natural references in later sections.
    for _k in ("qual1", "apply1", "right1"):
        st[_k] = st[_k].replace(card_name, "the card")
    card_block = lazy_credit_card_p1(site, card_name, card_slug, card_id, card_url, card_data, official_url, button_hex, lang)

    def benefit_para(raw: str, idx: int) -> str:
        base = p1_perceived_benefit(raw, card_name=card_name)
        if idx == 0:
            return f"{base} This is the first point to judge because it defines whether the product solves a real spending need."
        if idx == 1:
            return f"{base} The practical value depends on using the feature without creating unnecessary purchases or carrying avoidable debt."
        if idx == 2:
            return f"{base} Compare this benefit with your current card so the difference is specific, not just promotional."
        return f"{base} It should support the main use case rather than distract from costs, repayment and eligibility."

    cost_paras = [
        st["cost1"],
        st["cost2"],
        localize_fact("For this card, confirm fees, APR, exclusions, promotional timing and any reward rules on the current issuer page before applying.", lang),
    ]
    req_paras = [
        st["qual1"],
        localize_fact(f"Use any issuer eligibility checker to compare {value_focus} with your own circumstances before a full application.", lang),
        localize_fact("Approval, credit limit and final terms are decided by the issuer, so this page should help you prepare rather than promise an outcome.", lang),
    ]

    blocks = [
        wp_paragraph(subtitle),
        f'<!-- wp:image {{"id":{featured_id},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{featured_url}" alt="{html.escape(card_name)}" class="wp-image-{featured_id}"/></figure>\n<!-- /wp:image -->',
        wp_paragraph(st["intro1"]),
        wp_paragraph(st["intro2"]),
        wp_paragraph(st["intro3"]),
        card_block,
        wp_details("Benefícios", [benefit_para(benefits_l[0],0), benefit_para(benefits_l[1],1), benefit_para(benefits_l[2],2), benefit_para(benefits_l[3],3)]),
        wp_details("Quem deveria usar", [
            localize_fact(f"This card is most useful when {value_focus} fits spending you already expect to make.", lang),
            localize_fact("It may suit readers who want to compare benefits, cost and application requirements before leaving for the official issuer page.", lang),
            localize_fact("It is less suitable when the strongest benefit would require extra spending or when repayment discipline is uncertain.", lang),
        ]),
        wp_heading("Como funciona o cartão" if lang == "pt" else c["heads"][1]),
        wp_paragraph(st["work1"]),
        wp_paragraph(st["work2"]),
        wp_paragraph(localize_fact("If rewards, cashback, points or travel benefits apply, they should be judged through ordinary purchases and realistic repayment behaviour.", lang)),
        wp_heading("Como solicitar o cartão" if lang == "pt" else c["heads"][6]),
        wp_paragraph(st["apply1"]),
        wp_paragraph(localize_fact(f"Have income, address and borrowing details ready, then compare the issuer’s final offer with {value_focus}.", lang)),
        wp_paragraph(localize_fact("If the official page shows different fees, APR, transfer terms or reward rules from what you expected, pause before submitting personal information.", lang)),
        wp_details("APR, taxas e custos" if lang == "pt" else c["heads"][2], cost_paras),
        wp_details("Requisitos para solicitar" if lang == "pt" else c["heads"][4], req_paras),
        wp_heading(c["heads"][7]),
        wp_paragraph(st["right1"]),
        wp_paragraph(localize_fact("If the fee, APR or eligibility conditions do not fit your situation, compare other cards before applying.", lang)),
        wp_paragraph(localize_fact(positioning.get("right_3") or "Compare the card with at least one alternative before applying.", lang)),
        card_block,
    ]
    body = "\n\n".join(blocks)
    body, wc = fit_word_count(body, lang)
    keyword_count = count_keyword_occurrences(card_name, body)
    return body, {"subtitle":subtitle,"subtitle_chars":len(subtitle),"word_count":wc,"featured_inserted":True,"lazyblocks":2,"details_blocks":4,"effective_language":lang,"contract_p1":contract.get("path"),"contract_mode":contract.get("contract_mode", CONTRACT_MODE),"keyword_count_body":keyword_count}


def visible_word_count(body: str) -> int:
    src = re.sub(r"<!-- wp:lazyblock/credit-card.*?/-->", " ", body, flags=re.S)
    src = re.sub(r"<figure.*?</figure>", " ", src, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", src))
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return len(re.findall(r"\b[\w£’'.%-]+\b", text))


def fit_word_count(body: str, lang: str = "en") -> Tuple[str, int]:
    wc = visible_word_count(body)
    localized = {
        "en": [
            "Also consider existing borrowing before applying, because another credit product can affect affordability and future applications.",
            "If you are unsure, pause and check the issuer documents again before submitting personal details.",
            "Compare at least one alternative so the fee, reward structure and repayment terms are easier to judge.",
        ],
        "es": [
            "También considera cómo encajaría la tarjeta junto con cualquier deuda existente antes de solicitar.",
            "Si tienes dudas, detente y revisa de nuevo los documentos del emisor.",
            "Compara al menos una alternativa antes de enviar la solicitud.",
        ],
        "pt": [
            "Considere também como o cartão se encaixaria junto de qualquer dívida existente antes de solicitar.",
            "Se tiver dúvidas, pare e confira novamente os documentos do emissor.",
            "Compare ao menos uma alternativa antes de enviar a solicitação.",
        ],
        "tr": [
            "Başvurmadan önce kartın mevcut borçlarla birlikte nasıl duracağını da düşün.",
            "Emin değilsen kişisel bilgileri göndermeden önce kurum belgelerini yeniden kontrol et.",
            "Başvurmadan önce ürünü en az bir alternatifle karşılaştır.",
        ],
    }.get(lang, [])
    generic_extra = [
        "Think about how often the strongest benefit would be used during a normal year.",
        "Occasional use may not justify a fee or a more complex rewards structure.",
        "Keep the official page open while applying so you can confirm the latest rates and exclusions.",
        "If your circumstances change, reassess the card rather than keeping it only for historic benefits.",
        "Credit products should continue to match your current budget and repayment habits.",
        "Check whether the reward rules still match your spending habits before submitting the application.",
        "Confirm the product’s specific fees and standard rate before relying on any headline offer.",
        "Set a repayment plan early if you expect to carry a balance beyond the statement date.",
        "Do not spend more than you can realistically repay from normal monthly income.",
        "Missed payments can affect promotional rates, borrowing costs and future credit access.",
        "For travel-focused cards, estimate foreign-spend savings against your expected trips.",
        "If a cashback cap applies, compare that cap with your usual monthly spending.",
        "Keep evidence of the offer terms that applied when you submitted the application.",
        "Issuer terms can change, so the final check should happen immediately before applying.",
        "The best fit is usually the card that solves a specific spending pattern.",
        "A simple benefit can be more valuable than a larger reward you rarely use.",
        "Look at everyday groceries, fuel, subscriptions and travel costs before estimating value.",
        "If the card is mainly for trips, compare airport, hotel and overseas purchase habits.",
        "If the card is mainly for cashback, check whether excluded transactions affect your plan.",
        "If the card is mainly for protection, remember that section 75 rules have limits.",
        "A card with no obvious fee can still be expensive when balances are carried.",
        "The official eligibility checker is useful because it avoids a full application too early.",
        "Use the card only where the confirmed benefit is stronger than your current option.",
        "Review the statement cycle so rewards and repayments are easier to track.",
        "The practical question is whether the card improves purchases you already make.",
        "Avoid treating rewards as a reason to create extra spending.",
    ]
    filler = localized + generic_extra
    used = {re.sub(r"\s+", " ", s).strip().lower() for s in re.findall(r"[^.!?]+[.!?]", re.sub(r"<[^>]+>", " ", html.unescape(body)))}
    inserted = False
    for sentence in filler:
        if wc >= 900:
            break
        norm = re.sub(r"\s+", " ", sentence).strip().lower()
        if norm in used:
            continue
        insert = wp_paragraph(sentence)
        if not inserted and "<!-- wp:lazyblock/credit-card" in body:
            body = body.replace("<!-- wp:lazyblock/credit-card", insert + "\n\n<!-- wp:lazyblock/credit-card", 1)
            inserted = True
        else:
            body = body + "\n\n" + insert
        used.add(norm)
        wc = visible_word_count(body)
    if wc > 1000:
        raise RunnerError(f"P1 body word count above hard limit: {wc}")
    if wc < 900:
        raise RunnerError(f"P1 body word count below hard limit after expansion: {wc}")
    return body, wc

def title_and_meta(card_name: str, card_data: Dict[str, Any], lang: str) -> Tuple[str, str, str]:
    focus = compact_focus(card_name); c = copy_for(lang)
    title = f"{card_name}: {c['heads'][6]}"
    if len(title) > 60:
        title = c["title"].format(focus=focus)
    if len(title) > 60: title = f"{focus}: {c['heads'][6]}"
    meta = f"{card_name} guide with costs, benefits, eligibility notes and official issuer apply link before you continue." if lang == "en" else c["meta"].format(focus=card_name)
    additions = {"en":" Check issuer terms before applying.","es":" Revisa los términos del emisor antes de solicitar.","pt":" Confira os termos do emissor antes de solicitar.","tr":" Başvurmadan önce kurum şartlarını kontrol et."}
    while len(meta) < 130:
        candidate = meta.rstrip(".") + additions[lang]
        if len(candidate) > 150:
            break
        meta = candidate
    if len(meta) > 150:
        meta = meta[:147].rsplit(" ", 1)[0] + "."
    if len(meta) < 130:
        meta = (meta.rstrip(".") + " " + {"en":"Check official issuer terms first.","es":"Revisa términos oficiales.","pt":"Confira termos oficiais.","tr":"Resmi şartları kontrol et."}[lang]).strip()
    if len(meta) > 150: meta = meta[:147].rsplit(" ", 1)[0] + "."
    validate_seo_fields(title, meta, focus)
    return title, meta, focus

def resolve_term(site_key: str, taxonomy: str, name: str) -> int:
    p = run([str(WP_SCRIPTS / "resolve-term.sh"), site_key, taxonomy, name], timeout=60, allow_fail=True)
    out = p.stdout.strip() or p.stderr.strip()
    if p.returncode == 0:
        return int(json.loads(p.stdout)["id"])
    m = re.search(r'"term_id":(\d+)', out)
    if m:
        return int(m.group(1))
    raise RunnerError(f"Could not resolve {taxonomy} term {name}: {out[:800]}")


def resolve_taxonomy(site_key: str, site: Dict[str, Any], card_name: str, card_slug: str, benefits: List[str]) -> Tuple[int, List[int], List[str]]:
    lang = effective_lang(site); c=copy_for(lang)
    cat_name = site.get("default_category", c["cat"]); category_id = resolve_term(site_key, "categories", cat_name)
    vertical=(site.get("verticals") or ["cc"])[0]; country=site.get("country", "gb")
    card_tag = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9À-ÿğüşöçıİĞÜŞÖÇ ]+", " ", card_name.replace("Card", ""))).strip().lower()
    tags=["p1", vertical, country, card_tag, f"lang_{lang}", "atena_agent", c["tags"][0]]
    benefit_text=" ".join(benefits).lower()
    if "travel" in benefit_text or "avios" in benefit_text: tags.append(c["tags"][1])
    if "avios" in benefit_text: tags.append(c["tags"][2])
    if "lounge" in benefit_text: tags.append(c["tags"][3])
    tags=list(dict.fromkeys(tags))[:10]
    tag_ids=[resolve_term(site_key, "tags", t) for t in tags]
    return category_id, tag_ids, tags

def create_or_update_post(site_key: str, post_json: Dict[str, Any], update_post_id: Optional[int]) -> Dict[str, Any]:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(post_json, tmp, ensure_ascii=False)
    tmp.close()
    if update_post_id:
        creds = resolve_credentials(site_key)
        url = creds["wp_url"].rstrip("/") + f"/wp-json/wp/v2/posts/{update_post_id}"
        r = requests.post(url, auth=(creds["username"], creds["password"]), json=post_json, timeout=60)
        if r.status_code >= 400:
            raise RunnerError(f"WP update failed {r.status_code}: {r.text[:1000]}")
        return r.json()
    return run_json([str(WP_SCRIPTS / "create-post.sh"), site_key, tmp.name], timeout=180)


def update_yoast(site_key: str, post_id: int, title: str, body: str, meta: Dict[str, str]) -> Dict[str, Any]:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"title": title, "content": body, "meta": meta}, tmp, ensure_ascii=False)
    tmp.close()
    return run_json([str(WP_SCRIPTS / "update-yoast.sh"), site_key, str(post_id), tmp.name, "verify"], timeout=180)


def public_verify(url: str, official_url: str, featured_url: str, card_url: str, lang: str = "en") -> Dict[str, Any]:
    r = requests.get(url + ("?nocache=1" if "?" not in url else "&nocache=1"), timeout=25, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    html_text = r.text
    m = re.search(r'"wordCount":(\d+)', html_text)
    c = copy_for(lang)
    checks = {
        "http": r.status_code,
        "contains_apply_now": c["apply"] in html_text,
        "contains_redirected": c["redir"] in html_text,
        "contains_official_url": official_url in html_text,
        "contains_featured": bool(featured_url and featured_url in html_text),
        "contains_card": bool(card_url and card_url in html_text),
        "yoast_schema_word_count": int(m.group(1)) if m else None,
    }
    checks["ok"] = (
        checks["http"] == 200
        and checks["contains_apply_now"]
        and checks["contains_redirected"]
        and checks["contains_official_url"]
        and checks["contains_featured"]
        and checks["contains_card"]
    )
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--rec-url", required=True, help="Existing REC URL to use as source context")
    ap.add_argument("--status", choices=["draft", "publish"], default="draft")
    ap.add_argument("--official-url", default="")
    ap.add_argument("--card", default="")
    ap.add_argument("--annual-fee", default="")
    ap.add_argument("--apr", default="")
    ap.add_argument("--benefit", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--update-post-id", type=int, default=0, help="Update an existing P1 instead of creating a new post")
    ap.add_argument("--lang", default="", help="Debug-only language override. Production language comes from site.language.")
    ap.add_argument("--allow-language-override", action="store_true", help="Allow --lang in dry-run/draft debug. Publish aborts if it conflicts with site.language.")
    args = ap.parse_args()

    started = ts()
    timings: Dict[str, float] = {}
    steps: List[str] = []
    media_created: List[Dict[str, Any]] = []
    result: Dict[str, Any] = {"ok": False, "runner": "mgs-p1-runner", "site": args.site, "status_requested": args.status, "dry_run": args.dry_run}
    try:
        t = ts(); site = load_site(args.site); timings["load_site"] = ts() - t; steps.append("site_loaded")
        canonical_language = (site.get("language") or "").strip().lower()
        if args.lang:
            requested_language = args.lang.strip().lower()
            if not args.allow_language_override:
                raise RunnerError("--lang is debug-only. Use site.language for production, or pass --allow-language-override for dry-run/draft debugging.")
            if args.status == "publish" and canonical_language and requested_language != canonical_language:
                raise RunnerError(f"language_override_conflicts_with_site_language: site.language={canonical_language} --lang={requested_language}; publish blocked")
            site["language"] = requested_language
        lang = effective_lang(site)
        t = ts(); p1_contract = load_p1_template_contract(); timings["contract_load"] = ts() - t; steps.append("p1_contract_loaded")
        result["policy"] = {"contract_p1": p1_contract["path"], "contract_mode": p1_contract["contract_mode"], "effective_language": lang, "article_generation": "deterministic_python", "llm_runtime": "disabled"}

        t = ts()
        rec_id_match = re.search(r"[?&]p=(\d+)", args.rec_url)
        if rec_id_match:
            rec_id = int(rec_id_match.group(1))
            rec = wp_get_post(args.site, rec_id)
            public_html = f"<body class='postid-{rec_id}'>" + (rec.get("content", {}).get("rendered") or rec.get("content", {}).get("raw") or "") + "</body>"
        else:
            public_html = get_public(args.rec_url)
            rec_id = post_id_from_public_html(public_html, args.rec_url)
            rec = wp_get_post(args.site, rec_id)
        timings["fetch_rec"] = ts() - t; steps.append("rec_loaded")
        rec_raw = rec.get("content", {}).get("raw") or ""
        rec_rendered = rec.get("content", {}).get("rendered") or ""
        rec_title = rec.get("title", {}).get("raw") or rec.get("title", {}).get("rendered") or ""
        parsed = parse_card_from_rec(rec_raw, rec_rendered, rec_title)
        card_name = args.card or parsed["card_name"]
        card_slug = infer_card_slug(args.rec_url, card_name)
        official_url = args.official_url or ""
        if not official_url:
            raise RunnerError("official URL missing; pass --official-url. Editorial card-cache is disabled for production content")
        t = ts(); preflight_official_source(official_url, card_name); timings["official_source_preflight"] = ts() - t; steps.append("official_source_preflight_passed")
        card_url = parsed.get("card_url")
        card_id = parsed.get("card_id")
        card_image_source = "rec_lazyblock" if card_url and card_id else "missing_from_rec"
        if not card_url or not card_id:
            # P1 created from an existing REC must not silently inject an external/manual
            # cache image when the REC card LazyBlock is empty. That bypasses the
            # card-only normalization/crop gate and hides the issue from Raquel.
            raise RunnerError("REC card image is missing from the LazyBlock; do not publish P1. Ask Raquel for the correct card image or repair the REC card image first.")

        country = site.get("country", "gb"); vertical = (site.get("verticals") or ["cc"])[0]
        inferred_target_slug = f"apply-now-{country}-{vertical}-{card_slug}"
        rec_button_slug = p1_slug_from_rec_buttons(public_html, rec_raw, site["domain"])
        target_slug = rec_button_slug or inferred_target_slug
        target_url = f"https://{site['domain']}/{target_slug}/"
        existing_check = requests.get(target_url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        result["existing_p1_check"] = {"url": target_url, "http": existing_check.status_code, "slug_source": "rec_button" if rec_button_slug else "inferred", "inferred_slug": inferred_target_slug}
        if existing_check.status_code < 400 and not args.dry_run and not args.update_post_id:
            raise RunnerError(f"Target P1 already exists at {target_url}; pass --update-post-id to update instead of creating a duplicate")

        t = ts(); official_data = extract_official_data(card_name, official_url, args.benefit, args.annual_fee or None, args.apr or None); timings["official_facts"] = ts() - t; steps.append("official_facts_extracted")
        # Do not preserve REC LazyBlock labels by default; P1 derives fresh labels from current official/request facts.
        for key in ("tag10", "tag2", "descriptor"):
            official_data.pop(key, None)

        card_path = ensure_card_local(card_url, card_slug)
        featured_path = None
        featured_audit = None
        featured_failures: List[str] = []
        for featured_attempt in range(1, 4):
            t = ts(); featured_path = make_exact_featured(card_path, card_slug); timings["featured_image"] = timings.get("featured_image", 0) + (ts() - t)
            t = ts()
            featured_audit = run_json([
                str(FEATURED_AUDIT_SCRIPT),
                "--featured", featured_path,
                "--card", card_path,
                "--mode", "p1",
                "--card-name", card_name,
                "--require-person",
            ], timeout=150, allow_fail=True)
            timings["featured_semantic_audit"] = timings.get("featured_semantic_audit", 0) + (ts() - t)
            if featured_audit.get("ok"):
                if featured_attempt > 1:
                    result.setdefault("warnings", []).append(f"featured_semantic_audit_passed_after_retry:{featured_attempt}")
                break
            reasons = featured_audit.get("blocking_reasons") or []
            featured_failures.append(f"attempt {featured_attempt}: {', '.join(map(str, reasons))}")
        if not featured_audit or not featured_audit.get("ok") or not featured_path:
            raise RunnerError("featured_semantic_audit_failed_after_retries: " + " | ".join(featured_failures))
        steps.append("featured_generated_exact_overlay")
        steps.append("featured_semantic_audited")

        if args.dry_run:
            featured_media = {"id": None, "source_url": featured_path, "dry_run_local_path": featured_path}
        else:
            t = ts(); featured_media = upload_image(args.site, featured_path, f"featured-p1-{card_slug}.jpg"); timings["upload_featured"] = ts() - t; media_created.append({"id": featured_media.get("id"), "url": featured_media.get("source_url"), "role": "p1_featured"}); steps.append("featured_uploaded")

        t = ts(); button = run_json([str(WP_SCRIPTS / "resolve-button-color.sh"), args.site], timeout=60); button_hex = button["hex"]; timings["button_color"] = ts() - t
        featured_id = int(featured_media.get("id") or 0)
        featured_url = featured_media.get("source_url")
        # For dry-run, use placeholder id in body so validation can still run.
        body, validation = generate_p1_body(site, card_name, card_slug, official_data, official_url, featured_id or 999999, featured_url, int(card_id), card_url, button_hex, p1_contract)
        title, metadesc, focuskw = title_and_meta(card_name, official_data, lang)
        keyword_count_total = validate_p1_keyword_count(card_name, title, validation.get("subtitle", ""), body, metadesc)
        validate_no_review({"body": body, "subtitle": validation.get("subtitle", ""), "title": title, "meta": metadesc})
        body_path = Path(tempfile.gettempdir()) / f"p1-qa-{card_slug}.html"
        rec_compare_path = Path(tempfile.gettempdir()) / f"p1-qa-rec-compare-{card_slug}.html"
        body_path.write_text(body)
        rec_compare_path.write_text("\n\n".join([rec_raw, rec_rendered]))
        t = ts()
        semantic_qa = run_json([
            str(ROOT / "scripts/qa-content-validator.py"),
            "--type", "p1",
            "--file", str(body_path),
            "--card", card_name,
            "--compare-file", str(rec_compare_path),
        ], timeout=30, allow_fail=True)
        timings["semantic_qa"] = ts() - t
        if semantic_qa.get("status") == "BLOCK":
            raise RunnerError(f"semantic_qa_blocked: {semantic_qa}")
        steps.append("semantic_qa_checked")
        result["content_validation"] = {**validation, "title_chars": len(title), "meta_chars": len(metadesc), "focus_keyphrase": focuskw, "keyword_count_total": keyword_count_total, "semantic_qa": semantic_qa}
        steps.append("content_assembled")

        t = ts(); category_id, tag_ids, tag_names = resolve_taxonomy(args.site, site, card_name, card_slug, official_data.get("benefits") or []); validate_taxonomy_names(tag_names, site.get("language") or "en"); timings["taxonomy"] = ts() - t; steps.append("taxonomy_resolved")

        slug = target_slug
        meta = {"_yoast_wpseo_title": "", "_yoast_wpseo_metadesc": metadesc, "_yoast_wpseo_focuskw": focuskw}
        post_json = {
            "title": title,
            "slug": slug,
            "content": body,
            "status": args.status,
            "author": site.get("publishing_user", {}).get("id", 11),
            "categories": [category_id],
            "tags": tag_ids,
            "featured_media": featured_id or None,
            "meta": meta,
        }
        if site.get("hide_p1_from_home"):
            post_json.setdefault("meta", {})["_hide_from_home"] = "1"

        post = None; yoast = None; score = None; verify = None
        if not args.dry_run:
            t = ts(); post = create_or_update_post(args.site, post_json, args.update_post_id or None); timings["wp_publish"] = ts() - t; steps.append("post_published" if not args.update_post_id else "post_updated")
            post_id = int(post["id"])
            t = ts(); yoast = update_yoast(args.site, post_id, title, body, meta); timings["yoast_update"] = ts() - t; steps.append("yoast_verified")
            t = ts(); score = run_json([str(GEN_SCRIPTS / "yoast-score-post.sh"), args.site, str(post_id)], timeout=180, allow_fail=True); validate_yoast_score(score); timings["yoast_score"] = ts() - t; steps.append("yoast_scored")
            if args.status == "publish":
                t = ts(); verify = public_verify(post["link"], official_url, featured_url or "", card_url or "", lang); timings["public_verify"] = ts() - t
                if not verify.get("ok"):
                    raise RunnerError(f"public_verify_failed: {verify}")
                steps.append("public_verified")
            else:
                verify = {"ok": True, "skipped": "draft_not_public", "url": post.get("link")}
                steps.append("draft_public_verify_skipped")
        else:
            post = {"id": None, "link": f"https://{site['domain']}/{slug}/", "slug": slug, "status": args.status}
            steps.append("dry_run_no_publish")

        duration = ts() - started
        result.update({
            "ok": True,
            "status_detail": "fully_validated" if not args.dry_run else "dry_run_validated",
            "steps": steps,
            "duration_sec": round(duration, 3),
            "timings_sec": {k: round(v, 3) for k, v in timings.items()},
            "rec_source": {"url": args.rec_url, "post_id": rec_id},
            "official_url": official_url,
            "policy": {"contract_p1": p1_contract["path"], "contract_mode": p1_contract["contract_mode"], "effective_language": lang, "article_generation": "deterministic_python", "llm_runtime": "disabled"},
            "card": {"name": card_name, "slug": card_slug, "image_id": int(card_id), "image_url": card_url},
            "post": {"id": post.get("id"), "status": post.get("status", args.status), "slug": post.get("slug"), "link": post.get("link"), "edit_url": f"https://{site['domain']}/wp-admin/post.php?post={post.get('id')}&action=edit" if post.get("id") else None},
            "seo": {"title": title, "meta_description": metadesc, "focus_keyphrase": focuskw, "yoast": yoast, "score": score},
            "taxonomy": {"category_id": category_id, "tag_ids": tag_ids, "tag_names": tag_names},
            "images": {"card_reused_from_rec": card_image_source == "rec_lazyblock", "card_image_source": card_image_source, "featured": featured_media, "featured_audit": featured_audit, "media_created": media_created},
            "public_verify": verify,
            "cost_usd": {"runner_api_est": 0.0, "featured_image_est": 0.04, "total_est": 0.04},
        })
    except Exception as e:
        failure_cleanup = None
        if media_created and not args.dry_run:
            try:
                failure_cleanup = cleanup_created_media(args.site, media_created)
                steps.append("failure_media_cleanup_attempted")
            except Exception as cleanup_exc:
                failure_cleanup = {"error": str(cleanup_exc), "media_created": media_created}
        result.update({"ok": False, "error": str(e), "steps": steps, "duration_sec": round(ts() - started, 3), "timings_sec": {k: round(v, 3) for k, v in timings.items()}, "images": {"media_created": media_created, "failure_cleanup": failure_cleanup}})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
