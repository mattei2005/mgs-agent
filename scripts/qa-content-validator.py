#!/usr/bin/env python3
"""qa-content-validator.py — deterministic editorial QA for REC/P1 content.

Purpose: catch repeated/generic copy, placeholders and REC↔P1 contamination before
publication. This is intentionally deterministic and conservative: it reports
WARN/BLOCK with evidence; it does not generate or rewrite content.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PLACEHOLDERS = [
    "check issuer terms",
    "check terms",
    "terms apply placeholder",
    "lorem ipsum",
    "insert ",
    "todo",
    "tbd",
    "n/a n/a",
]

VISIBLE_EXTRACTION_FAILURES = [
    "not stated on the official product page",
    "the official source states not stated",
    "official source states not stated",
    "not stated on the officia",
    "check the official issuer page for the latest confirmed benefit details",
    "latest confirmed benefit details",
]

CROSS_ARTICLE_BOILERPLATE = [
    "applications eligibility checks and final lending decisions are handled by the issuer not by",
    "therefore the button sends you to the official card page",
    "use this page as a decision support step then read the issuer s latest summary box and terms before submitting any application",
    "the issuer does not guarantee acceptance it may assess credit history income affordability existing borrowing and other information before making a decision",
    "an eligibility check can help users understand whether acceptance is likely before submitting a full application follow the issuer s own process and guidance",
    "only apply if the monthly cost possible interest charges and repayment obligations fit your situation responsible use matters more than earning any reward",
    "select the apply button to continue to the official issuer website you will be redirected and the application will continue away from this site",
]

GENERIC_OPENINGS = [
    "if you are looking for",
    "if you're looking for",
    "this card is designed for people who want",
    "this credit card is designed for",
    "choosing the right credit card",
    "when it comes to choosing",
    "credit cards can be a useful way",
    "a credit card can help you manage",
    "whether you are looking to",
    "highlights real benefits costs and application steps",
    "confirmed benefits costs and application steps",
]

WEAK_INVENTORY_OPENING = [
    "highlights real benefits",
    "highlights its confirmed costs and benefits",
    "confirmed costs and benefits",
    "costs and application steps",
    "confirmed benefits costs",
    "clear reason to compare it with",
    "focused value proposition",
    "overall the card should be framed around its real practical value",
    "rather than forced into a generic rewards or premium card story",
]

REC_TABLE_AFTERTEXT = [
    "the table is a quick orientation tool",
    "it is not a full eligibility check",
    "rates and terms can change therefore the official page should remain the final reference",
]

WEAK_PERCEIVED_BENEFIT_PHRASES = [
    "the product presents",
    "functionalities relevant",
    "confirmed benefits and costs",
    "real practical value rather than",
    "generic rewards or premium card story",
    "eligible spend",
    "planned trips hotels transport and partner spending",
    "spending abroad feel cleaner",
    "the reader",
    "readers should",
    "applicants should",
    "may suit users",
]

IMPERSONAL_AUDIENCE_TERMS = [
    "the reader",
    "readers should",
    "users who",
    "may suit users",
    "applicants should",
    "applicants whose",
]
REC_BALANCE_TRANSFER_TOP_KEYWORDS = [
    "balance transfer",
    "0 interest",
    "interest free",
    "months",
    "existing card debt",
    "repayments",
    "interest pressure",
]

BAD_LAZYBLOCK_LABELS = {
    "credit card",
    "card benefits",
    "features",
    "official terms",
    "transfer fee",
    "annual fee",
    "balance transfer",
    "balance transfers",
}

GENERIC_FINANCE_FILLER = [
    "make the most of your spending",
    "manage your finances more effectively",
    "enjoy a range of benefits",
    "valuable benefits and features",
    "help you reach your financial goals",
    "suit your lifestyle",
    "peace of mind",
    "simple and convenient way",
]

REC_FORBIDDEN_TONE = [
    "comprehensive guide",
    "in-depth guide",
    "full application guide",
]

P1_FORBIDDEN_TONE = [
    "quick recommendation",
    "quick pick",
    "short recommendation",
]


def strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    raw = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def normalize(raw: str) -> str:
    text = strip_html(raw).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text: str) -> List[str]:
    visible = strip_html(text)
    parts = re.split(r"(?<=[.!?])\s+", visible)
    return [p.strip() for p in parts if len(p.strip().split()) >= 5]


def shingles(text: str, n: int = 5) -> set[str]:
    words = normalize(text).split()
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i+n]) for i in range(len(words) - n + 1)}


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def count_occurrences(text: str, needles: List[str]) -> List[Dict[str, Any]]:
    low = normalize(text)
    out = []
    for needle in needles:
        count = len(re.findall(re.escape(needle), low))
        if count:
            out.append({"phrase": needle, "count": count})
    return out


def first_sentence(text: str) -> str:
    s = sentences(text)
    return s[0] if s else ""


def repeated_sentences(text: str) -> List[Dict[str, Any]]:
    seen: Dict[str, int] = {}
    for s in sentences(text):
        key = normalize(s)
        if len(key.split()) >= 7:
            seen[key] = seen.get(key, 0) + 1
    return [{"sentence": k, "count": v} for k, v in seen.items() if v > 1][:10]


def missing_card_specificity(text: str, card: str) -> bool:
    if not card:
        return False
    words = [w for w in re.split(r"[^a-z0-9]+", card.lower()) if len(w) >= 4]
    if not words:
        return False
    low = normalize(text)
    hits = sum(1 for w in words if w in low)
    return hits == 0


def extract_lazyblock_labels(raw: str) -> List[Dict[str, str]]:
    labels: List[Dict[str, str]] = []
    for m in re.finditer(r"<!--\s*wp:lazyblock/credit-card\s+(\{.*?\})\s*/-->", raw, re.S):
        try:
            payload = json.loads(html.unescape(m.group(1)))
        except Exception:
            continue
        labels.append({
            "tag10": str(payload.get("tag10") or "").strip(),
            "tag2": str(payload.get("tag2") or "").strip(),
            "texto": str(payload.get("texto") or "").strip(),
        })
    return labels


def bad_lazyblock_label(label: str, card: str, full_text: str) -> str:
    value = html.unescape(str(label or "")).strip()
    low = normalize(value)
    card_low = normalize(card)
    full_low = normalize(full_text)
    if not value:
        return "empty_label"
    if low in BAD_LAZYBLOCK_LABELS:
        if low in {"balance transfer", "balance transfers"} and "balance transfer" not in card_low:
            return ""
        return "generic_or_redundant_label"
    if re.fullmatch(r"[0-9£%\s.]+", value):
        return "numeric_fragment_label"
    if "fee" in low and re.search(r"\d", low):
        return "fee_fragment_label"
    if low in {"0", "2", "24", "2 99", "2.99", "over 1"}:
        return "truncated_fragment_label"
    if low == "no fees" and re.search(r"\b(fee|fees|2\s*99|minimum|annual fee)\b", full_low):
        return "ambiguous_fee_claim"
    return ""


def lazyblock_label_blocks(raw: str, card: str) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for idx, labels in enumerate(extract_lazyblock_labels(raw), 1):
        for field in ("tag10", "tag2"):
            reason = bad_lazyblock_label(labels.get(field, ""), card, raw)
            if reason:
                blocks.append({"code": reason, "block": idx, "field": field, "value": labels.get(field, "")})
    return blocks


def weak_opening_inventory(first: str) -> List[Dict[str, Any]]:
    hits = count_occurrences(first, WEAK_INVENTORY_OPENING)
    return hits


def top_visible_sentences(text: str, n: int = 4) -> str:
    return " ".join(sentences(text)[:n])


def rec_top_keyword_blocks(text: str, card: str) -> List[Dict[str, Any]]:
    joined = normalize(card + " " + text)
    if "balance transfer" not in joined:
        return []
    top = normalize(top_visible_sentences(text, 4))
    hits = [kw for kw in REC_BALANCE_TRANSFER_TOP_KEYWORDS if normalize(kw) in top]
    # Require at least commercial intent + user pain terms before the first ad/card area.
    has_offer = any(k in hits for k in ["balance transfer", "0 interest", "interest free", "months"])
    has_pain = any(k in hits for k in ["existing card debt", "repayments", "interest pressure"])
    if len(hits) < 4 or not (has_offer and has_pain):
        return [{"code": "weak_rec_top_keywords", "hits": hits, "top_excerpt": top[:280]}]
    return []


def validate(article_type: str, text: str, *, card: str = "", compare_text: str = "") -> Dict[str, Any]:
    blocks: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    visible = strip_html(text)
    norm = normalize(text)
    wc = len(norm.split())
    fs = first_sentence(text)

    placeholders = count_occurrences(text, PLACEHOLDERS)
    if placeholders:
        blocks.append({"code": "placeholder_text", "evidence": placeholders})

    extraction_failures = count_occurrences(text, VISIBLE_EXTRACTION_FAILURES)
    if extraction_failures:
        blocks.append({"code": "visible_extraction_failure", "evidence": extraction_failures})

    boilerplate_hits = count_occurrences(text, CROSS_ARTICLE_BOILERPLATE)
    if boilerplate_hits:
        blocks.append({"code": "cross_article_boilerplate", "evidence": boilerplate_hits})

    generic_opening_hits = count_occurrences(fs, GENERIC_OPENINGS)
    if generic_opening_hits:
        blocks.append({"code": "generic_opening", "first_sentence": fs, "evidence": generic_opening_hits})

    weak_opening_hits = weak_opening_inventory(fs)
    if weak_opening_hits:
        blocks.append({"code": "weak_inventory_opening", "first_sentence": fs, "evidence": weak_opening_hits})

    impersonal_hits = count_occurrences(text, IMPERSONAL_AUDIENCE_TERMS)
    if impersonal_hits:
        blocks.append({"code": "impersonal_audience_language", "evidence": impersonal_hits})

    bad_labels = lazyblock_label_blocks(text, card)
    if bad_labels:
        blocks.append({"code": "bad_lazyblock_labels", "evidence": bad_labels})

    filler_hits = count_occurrences(text, GENERIC_FINANCE_FILLER)
    if len(filler_hits) >= 2:
        warnings.append({"code": "generic_finance_filler", "evidence": filler_hits})

    reps = repeated_sentences(text)
    if reps:
        blocks.append({"code": "repeated_sentences", "evidence": reps})

    if missing_card_specificity(text, card):
        blocks.append({"code": "missing_card_name_specificity", "card": card})

    if article_type == "rec":
        table_aftertext = count_occurrences(text, REC_TABLE_AFTERTEXT)
        if table_aftertext:
            blocks.append({"code": "rec_comparison_table_aftertext", "evidence": table_aftertext})
        weak_benefit_hits = count_occurrences(text, WEAK_PERCEIVED_BENEFIT_PHRASES)
        if weak_benefit_hits:
            blocks.append({"code": "weak_perceived_benefit_copy", "evidence": weak_benefit_hits})
        top_blocks = rec_top_keyword_blocks(text, card)
        if top_blocks:
            blocks.extend(top_blocks)
        tone_hits = count_occurrences(text, REC_FORBIDDEN_TONE)
        if tone_hits:
            warnings.append({"code": "rec_too_p1_like", "evidence": tone_hits})
        if wc > 850:
            warnings.append({"code": "rec_unusually_long", "word_count": wc})
    elif article_type == "p1":
        intro = sentences(text)[:5]
        long_intro = [{"sentence": s, "word_count": len(s.split())} for s in intro if len(s.split()) > 35]
        if long_intro:
            blocks.append({"code": "p1_intro_paragraph_too_long", "evidence": long_intro})
        weak_benefit_hits = count_occurrences(text, WEAK_PERCEIVED_BENEFIT_PHRASES)
        if weak_benefit_hits:
            blocks.append({"code": "weak_perceived_benefit_copy", "evidence": weak_benefit_hits})
        tone_hits = count_occurrences(text, P1_FORBIDDEN_TONE)
        if tone_hits:
            warnings.append({"code": "p1_too_rec_like", "evidence": tone_hits})
        if wc < 750:
            warnings.append({"code": "p1_unusually_short", "word_count": wc})

    compare = None
    if compare_text:
        sim = round(jaccard(shingles(text, 5), shingles(compare_text, 5)), 4)
        compare = {"jaccard_5gram": sim, "threshold_block": 0.22, "threshold_warn": 0.14}
        if sim >= 0.22:
            blocks.append({"code": "near_duplicate_compare_file", "similarity": sim})
        elif sim >= 0.14:
            warnings.append({"code": "similar_to_compare_file", "similarity": sim})

    status = "BLOCK" if blocks else ("WARN" if warnings else "OK")
    return {
        "status": status,
        "article_type": article_type,
        "sha256": hashlib.sha256(normalize(text).encode()).hexdigest(),
        "word_count_visible": wc,
        "first_sentence": fs,
        "blocks": blocks,
        "warnings": warnings,
        "compare": compare,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic QA validator for MGS REC/P1 content")
    ap.add_argument("--type", choices=["rec", "p1"], required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--card", default="")
    ap.add_argument("--compare-file", default="", help="Optional REC/P1 counterpart to detect contamination/duplication")
    ap.add_argument("--warn-only", action="store_true", help="Always exit 0; JSON still reports BLOCK/WARN")
    args = ap.parse_args()

    text = Path(args.file).read_text(errors="ignore")
    compare = Path(args.compare_file).read_text(errors="ignore") if args.compare_file else ""
    result = validate(args.type, text, card=args.card, compare_text=compare)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.warn_only:
        return 0
    return 0 if result["status"] in {"OK", "WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
