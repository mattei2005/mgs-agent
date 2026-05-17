#!/usr/bin/env python3
"""REC duplicate-content fingerprint helper.

Compares a candidate REC HTML/text against previously saved REC fingerprints for
same-card multi-site scaling. The runner can use this before publishing; Atena
can also call it during audits.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DB = Path('/root/mgs-agent/data/rec-fingerprints.db')


def normalize(raw: str) -> str:
    raw = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', raw)
    raw = re.sub(r'<!--.*?-->', ' ', raw, flags=re.S)
    raw = re.sub(r'<[^>]+>', ' ', raw)
    raw = html.unescape(raw).lower()
    raw = re.sub(r'[^a-z0-9\s]', ' ', raw)
    raw = re.sub(r'\s+', ' ', raw).strip()
    return raw


def shingles(text: str, n: int = 5) -> set[str]:
    words = text.split()
    if len(words) < n:
        return {' '.join(words)} if words else set()
    return {' '.join(words[i:i+n]) for i in range(len(words) - n + 1)}


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def ensure_db(con: sqlite3.Connection) -> None:
    con.execute('''CREATE TABLE IF NOT EXISTS rec_fingerprints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_key TEXT NOT NULL,
        card_slug TEXT NOT NULL,
        post_id INTEGER,
        post_url TEXT,
        title TEXT,
        sha256 TEXT NOT NULL,
        normalized_text TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    con.execute('CREATE INDEX IF NOT EXISTS idx_rec_fp_card ON rec_fingerprints(card_slug)')


def main() -> int:
    ap = argparse.ArgumentParser(description='Check/store REC content fingerprints')
    ap.add_argument('--card-slug', required=True)
    ap.add_argument('--site', required=True)
    ap.add_argument('--file', required=True, help='Candidate HTML/text file')
    ap.add_argument('--post-id', type=int)
    ap.add_argument('--post-url', default='')
    ap.add_argument('--title', default='')
    ap.add_argument('--store', action='store_true')
    ap.add_argument('--threshold', type=float, default=0.35, help='Warn when 5-gram similarity >= threshold')
    args = ap.parse_args()

    text = normalize(Path(args.file).read_text(errors='ignore'))
    fp = hashlib.sha256(text.encode()).hexdigest()
    cand = shingles(text)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    ensure_db(con)
    rows = con.execute('SELECT * FROM rec_fingerprints WHERE card_slug=? AND site_key<>? ORDER BY created_at DESC', (args.card_slug, args.site)).fetchall()
    comparisons = []
    for r in rows:
        sim = jaccard(cand, shingles(r['normalized_text']))
        comparisons.append({
            'site_key': r['site_key'],
            'post_id': r['post_id'],
            'post_url': r['post_url'],
            'title': r['title'],
            'similarity': round(sim, 4),
            'sha256': r['sha256'],
        })
    comparisons.sort(key=lambda x: x['similarity'], reverse=True)
    max_sim = comparisons[0]['similarity'] if comparisons else 0.0
    status = 'WARN_SIMILAR' if max_sim >= args.threshold else 'OK'

    if args.store:
        con.execute('''INSERT INTO rec_fingerprints
            (site_key, card_slug, post_id, post_url, title, sha256, normalized_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (
            args.site, args.card_slug, args.post_id, args.post_url, args.title,
            fp, text, datetime.now(timezone.utc).isoformat()
        ))
        con.commit()
    con.close()

    print(json.dumps({
        'status': status,
        'card_slug': args.card_slug,
        'site_key': args.site,
        'sha256': fp,
        'max_similarity': max_sim,
        'threshold': args.threshold,
        'comparisons': comparisons[:10],
        'stored': bool(args.store),
    }, ensure_ascii=False, indent=2))
    return 0 if status == 'OK' else 2


if __name__ == '__main__':
    raise SystemExit(main())
