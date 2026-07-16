#!/usr/bin/env python3
"""Generate a read-only organization proposal from UPLOAD_CANVAS inventory.

No Drive writes. Produces proposed vertical/operation/format/status destination rows.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import re
from pathlib import Path

VISUAL_CC_TOP_FOLDERS = {
    "downloads_GEORGE",
    "downloads_GUSTAVO",
    "downloads_ISLIAGO",
    "downloads_JOE",
    "downloads_NICOLAS",
    "downloads_V3",
    "downloads_TARJETA_IMAGENS",
    "downloads_TARJETA_VIDEOS",
}
VISUAL_MIXED_TOP_FOLDERS = {"downloads", "organized"}


def norm(value: str) -> str:
    value = value.upper()
    value = re.sub(r"[_\-/()]+", " ", value)
    for a, b in [("ÁÀÃÂ", "A"), ("ÉÊ", "E"), ("Í", "I"), ("ÓÔÕ", "O"), ("Ú", "U"), ("Ç", "C")]:
        for ch in a:
            value = value.replace(ch, b)
    return value


def has(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


def proposal(row: dict[str, str], md5_vertical: dict[str, tuple[str, str]]) -> dict[str, str]:
    text = norm(row["relative_path"] + " " + row["original_filename"])
    jobs = has(r"\b(EMPREGO|JOB|JOBS|TRABALHO|TRABAJOS?|ALMACEN|REPARTIDORES?|MEDICAMENTOS|CONTRATANDO|VACANTES?|HORA|HR)\b", text)
    cc = has(r"\b(TARJETA|CARD|CREDITO|CREDIT|KREDIT|KREDITKARTE|CARTAO|LIMITE|LIMIT|VISA|MASTERCARD|APROBADA|APPROVED|GENEHMIGT)\b", text)
    top = row["source_top_folder"]
    if jobs:
        vertical = "JOBS"
        confidence = "high" if top in VISUAL_MIXED_TOP_FOLDERS or top == "downloads_EMPREGO" else "medium"
        reason = "jobs keyword + visual sample confirmed jobs where sampled"
    elif cc:
        vertical = "CC"
        confidence = "high"
        reason = "credit-card keyword"
    elif row.get("md5_checksum") in md5_vertical:
        vertical, inherited_reason = md5_vertical[row["md5_checksum"]]
        confidence = "medium"
        reason = "duplicate MD5 inherits " + inherited_reason
    elif top in VISUAL_CC_TOP_FOLDERS:
        vertical = "CC"
        confidence = "medium"
        reason = "top-folder visual sample homogeneous CC"
    elif top in VISUAL_MIXED_TOP_FOLDERS:
        vertical = "CC_REVIEW"
        confidence = "low"
        reason = "mixed folder; no decisive row keyword"
    else:
        vertical = "REVIEW"
        confidence = "low"
        reason = "insufficient evidence"

    operation = "JOBS_US_ES" if vertical == "JOBS" else "CC_REVIEW" if vertical in {"CC", "CC_REVIEW"} else "REVIEW"
    status = "01_READY_CANDIDATE" if confidence in {"high", "medium"} else "00_REVIEW"
    fmt = row["format"] if row["format"] in {"IMG", "VID"} else "OTHER"
    dest = f"MGS-AGENTS/CRIATIVOS/{operation}/{fmt}/{status}"
    return {
        **row,
        "vertical_proposed": vertical,
        "operation_proposed": operation,
        "proposal_confidence": confidence,
        "proposal_reason": reason,
        "destination_proposed": dest,
        "drive_action_proposed": "COPY_CLEANED_TO_DESTINATION_KEEP_RAW",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory_csv")
    ap.add_argument("--out-dir", default="/root/mgs-agent/data/ares/creative-inventory")
    args = ap.parse_args()
    rows = list(csv.DictReader(open(args.inventory_csv, encoding="utf-8")))
    md5_vertical: dict[str, tuple[str, str]] = {}
    for r in rows:
        checksum = r.get("md5_checksum") or ""
        if not checksum:
            continue
        text = norm(r["relative_path"] + " " + r["original_filename"])
        if has(r"\b(EMPREGO|JOB|JOBS|TRABALHO|TRABAJOS?|ALMACEN|REPARTIDORES?|MEDICAMENTOS|CONTRATANDO|VACANTES?|HORA|HR)\b", text):
            md5_vertical[checksum] = ("JOBS", "jobs keyword")
        elif has(r"\b(TARJETA|CARD|CREDITO|CREDIT|KREDIT|KREDITKARTE|CARTAO|LIMITE|LIMIT|VISA|MASTERCARD|APROBADA|APPROVED|GENEHMIGT)\b", text):
            md5_vertical[checksum] = ("CC", "credit-card keyword")
        elif r["source_top_folder"] in VISUAL_CC_TOP_FOLDERS:
            md5_vertical.setdefault(checksum, ("CC", "homogeneous CC top-folder visual sample"))
    proposed = [proposal(r, md5_vertical) for r in rows]
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"upload-canvas-organization-proposal-{stamp}.csv"
    summary_path = out_dir / f"upload-canvas-organization-proposal-summary-{stamp}.json"
    fields = list(proposed[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(proposed)
    summary = {
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "source_inventory": args.inventory_csv,
        "rows": len(proposed),
        "by_vertical_proposed": dict(collections.Counter(r["vertical_proposed"] for r in proposed).most_common()),
        "by_operation_proposed": dict(collections.Counter(r["operation_proposed"] for r in proposed).most_common()),
        "by_confidence": dict(collections.Counter(r["proposal_confidence"] for r in proposed).most_common()),
        "by_destination_top20": dict(collections.Counter(r["destination_proposed"] for r in proposed).most_common(20)),
        "files": {"proposal_csv": str(csv_path), "summary_json": str(summary_path)},
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
