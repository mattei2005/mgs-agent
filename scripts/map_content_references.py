#!/usr/bin/env python3
"""Map site/competitor sitemap URLs into a reusable content reference DB.

Input: one domain/brand per line. Domains without a dot are normalized to lowercase + .com,
while keeping original_label and guessed_domain=1 for audit.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

UA = "Mozilla/5.0 (compatible; MGS-Atena-ReferenceMapper/1.0; +https://mgsdigitalcorp.com)"
ROOT = Path("/root/mgs-agent/data/content-reference-map")
DB_PATH = ROOT / "content_reference_map.sqlite"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = ROOT / f"run-{RUN_ID}"
TIMEOUT = 20
MAX_WORKERS_DOMAINS = 8
MAX_WORKERS_PAGES = 20
MAX_PAGE_FETCH_PER_DOMAIN = int(os.getenv("MAX_PAGE_FETCH_PER_DOMAIN", "100"))  # cap title/H1 fetching per domain; all sitemap URLs are still stored

@dataclass
class FetchResult:
    url: str
    status: int | None
    body: bytes | None
    content_type: str
    error: str


def fetch(url: str, timeout: int = TIMEOUT) -> FetchResult:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(8_000_000)
            ct = r.headers.get("content-type", "")
            return FetchResult(url, getattr(r, "status", None), body, ct, "")
    except urllib.error.HTTPError as e:
        body = e.read(2000) if e.fp else b""
        return FetchResult(url, e.code, body, e.headers.get("content-type", "") if e.headers else "", f"HTTP {e.code}")
    except Exception as e:
        return FetchResult(url, None, None, "", type(e).__name__ + ": " + str(e)[:300])


def decode_body(fr: FetchResult) -> bytes:
    if not fr.body:
        return b""
    data = fr.body
    if fr.url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(data)
        except Exception:
            return data
    return data


def parse_xml(data: bytes):
    data = data.strip()
    if not data:
        raise ValueError("empty xml")
    return ET.fromstring(data)


def strip_ns(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def child_text(el, name: str) -> str:
    for c in list(el):
        if strip_ns(c.tag) == name:
            return (c.text or "").strip()
    return ""


def image_locs(el) -> list[str]:
    imgs=[]
    for x in el.iter():
        if strip_ns(x.tag) in ("loc", "image") and x.text:
            txt=x.text.strip()
            if re.search(r"\.(jpe?g|png|webp|gif)(\?|$)", txt, re.I):
                imgs.append(txt)
    return sorted(set(imgs))


def normalize_domain(line: str) -> tuple[str,str,int]:
    label=line.strip()
    x=label.lower().strip()
    x=re.sub(r"^https?://", "", x).strip("/")
    if "/" in x:
        x=x.split("/",1)[0]
    guessed=0
    if "." not in x:
        guessed=1
        x=x + ".com"
    return label, x, guessed


def likely_post_url(url: str) -> bool:
    p=urllib.parse.urlparse(url).path.strip('/').lower()
    if not p: return False
    bad=("category/","tag/","author/","wp-content/","page/","privacy","terms","contact","about","login")
    if any(b in p for b in bad): return False
    if re.search(r"\.(jpg|jpeg|png|gif|webp|pdf|xml|css|js)$", p): return False
    # include all simple article-looking slugs; prioritize rec/p1 by article_type later
    return len(p.split('/')) <= 3


def infer_from_slug(url: str):
    slug=urllib.parse.urlparse(url).path.strip('/').split('/')[-1].lower()
    article_type="article"
    country=""; vertical=""; product_slug=""; product_guess=""
    m=re.match(r"^(rec|p1|p2|pq|seo)-([a-z]{2})-([a-z0-9]+)-(.+)$", slug)
    if m:
        article_type=m.group(1).upper() if m.group(1)!="rec" else "REC"
        country=m.group(2)
        vertical=m.group(3)
        product_slug=m.group(4)
    else:
        for prefix in ("rec", "p1", "p2", "pq", "seo"):
            if slug == prefix or slug.startswith(prefix+'-'):
                article_type=prefix.upper() if prefix != "rec" else "REC"
                product_slug=slug[len(prefix):].strip('-')
                break
        if not product_slug:
            product_slug=slug
    product_guess=re.sub(r"[-_]+", " ", product_slug).strip().title()
    return slug, article_type, country, vertical, product_slug, product_guess


def sitemap_class(url: str) -> str:
    u=url.lower()
    if "post-sitemap" in u: return "post_sitemap"
    if "page-sitemap" in u: return "page_sitemap"
    if "category" in u: return "category_sitemap"
    if "sitemap" in u: return "sitemap"
    return "unknown"


def extract_title_h1(data: bytes) -> tuple[str,str]:
    txt=data[:1_500_000].decode('utf-8', 'ignore')
    title=""; h1=""
    mt=re.search(r"<title[^>]*>(.*?)</title>", txt, re.I|re.S)
    if mt: title=clean_text(mt.group(1))
    mh=re.search(r"<h1[^>]*>(.*?)</h1>", txt, re.I|re.S)
    if mh: h1=clean_text(mh.group(1))
    return title, h1


def clean_text(s: str) -> str:
    s=re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.I|re.S)
    s=re.sub(r"<[^>]+>", " ", s)
    s=html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def likely_p1_link(page_url: str, data: bytes) -> str:
    txt=data[:1_500_000].decode('utf-8', 'ignore')
    candidates=[]
    for m in re.finditer(r"<a\b[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", txt, re.I|re.S):
        href=html.unescape(m.group(1).strip())
        label=clean_text(m.group(2)).lower()
        absu=urllib.parse.urljoin(page_url, href)
        if urllib.parse.urlparse(absu).netloc != urllib.parse.urlparse(page_url).netloc:
            continue
        if any(x in absu.lower() for x in ["privacy", "terms", "contact", "category", "tag", "author"]):
            continue
        score=0
        if re.search(r"apply|aplicar|solicitar|inscrev|como solicitar|how to|saiba mais|veja|conheça|ver", label): score+=3
        if re.search(r"/(p1|p2|pq)-", urllib.parse.urlparse(absu).path.lower()): score+=4
        if score:
            candidates.append((score, absu))
    if not candidates: return ""
    candidates.sort(key=lambda x: (-x[0], len(x[1])))
    return candidates[0][1]


def collect_domain(label: str, domain: str, guessed: int) -> tuple[list[dict], dict]:
    started=time.time()
    sitemap_url=f"https://{domain}/sitemap_index.xml"
    first=fetch(sitemap_url)
    if first.status is None or (first.status and first.status >= 400):
        # try http fallback only if https failed
        alt=f"http://{domain}/sitemap_index.xml"
        altfr=fetch(alt)
        if altfr.status and altfr.status < 400:
            sitemap_url=alt; first=altfr
    summary={"original_label":label,"domain":domain,"guessed_domain":guessed,"sitemap_index":sitemap_url,"sitemap_status":first.status,"sitemap_error":first.error,"sitemaps_read":0,"urls_found":0,"pages_fetched":0,"duration_sec":0}
    rows=[]
    if not first.body or not first.status or first.status >= 400:
        summary["duration_sec"]=round(time.time()-started,2)
        return rows, summary
    queue=[sitemap_url]
    seen_sitemaps=set()
    url_entries=[]
    while queue and len(seen_sitemaps)<300:
        sm=queue.pop(0)
        if sm in seen_sitemaps: continue
        seen_sitemaps.add(sm)
        fr=first if sm==sitemap_url else fetch(sm)
        if not fr.body or not fr.status or fr.status>=400:
            continue
        try:
            root=parse_xml(decode_body(fr))
        except Exception:
            continue
        root_tag=strip_ns(root.tag)
        if root_tag == "sitemapindex":
            for se in root:
                if strip_ns(se.tag)!="sitemap": continue
                loc=child_text(se,"loc")
                if loc and loc not in seen_sitemaps:
                    queue.append(loc)
        elif root_tag == "urlset":
            for ue in root:
                if strip_ns(ue.tag)!="url": continue
                loc=child_text(ue,"loc")
                if not loc: continue
                url_entries.append({"url":loc,"lastmod":child_text(ue,"lastmod"),"source_sitemap":sm,"image_urls":image_locs(ue)})
    summary["sitemaps_read"]=len(seen_sitemaps)
    summary["urls_found"]=len(url_entries)
    # rows for every URL in sitemap
    now=datetime.now(timezone.utc).isoformat()
    for ent in url_entries:
        u=ent["url"]
        slug,atype,country,vertical,pslug,pguess=infer_from_slug(u)
        rows.append({
            "run_id":RUN_ID,"mapped_at":now,"original_label":label,"domain":domain,"guessed_domain":guessed,
            "article_type":atype,"sitemap_rec_classification":sitemap_class(ent["source_sitemap"]),"country":country,"vertical":vertical,
            "product_guess":pguess,"product_slug":pslug,"slug":slug,"url":u,"reference_p1_url":"",
            "html_title":"","h1":"","lastmod":ent["lastmod"],"http_status":"","image_urls":"|".join(ent["image_urls"]),
            "source_sitemap":ent["source_sitemap"],"fetch_error":"","is_likely_article":1 if likely_post_url(u) else 0,
        })
    # fetch HTML title/h1/P1 link for likely article URLs, prioritizing REC then post sitemaps
    likely=[r for r in rows if r["is_likely_article"]]
    likely.sort(key=lambda r: (0 if r["article_type"]=="REC" else 1, 0 if r["sitemap_rec_classification"]=="post_sitemap" else 1, r["url"]))
    target=likely[:MAX_PAGE_FETCH_PER_DOMAIN]
    by_url={r["url"]: r for r in rows}
    def fetch_page(u):
        fr=fetch(u, timeout=18)
        title=h1=p1=""
        if fr.body and fr.status and fr.status<400 and ("html" in fr.content_type or fr.body[:100].lower().find(b"<html")>=0):
            title,h1=extract_title_h1(fr.body)
            p1=likely_p1_link(u, fr.body)
        return u, fr.status, fr.error, title, h1, p1
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_PAGES) as ex:
        futs=[ex.submit(fetch_page, r["url"]) for r in target]
        for fut in as_completed(futs):
            u,status,err,title,h1,p1=fut.result()
            r=by_url.get(u)
            if r:
                r["http_status"]="" if status is None else str(status)
                r["fetch_error"]=err
                r["html_title"]=title
                r["h1"]=h1
                r["reference_p1_url"]=p1
                summary["pages_fetched"] += 1
    summary["duration_sec"]=round(time.time()-started,2)
    return rows, summary


def ensure_db(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS content_reference_urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT, mapped_at TEXT, original_label TEXT, domain TEXT, guessed_domain INTEGER,
        article_type TEXT, sitemap_rec_classification TEXT, country TEXT, vertical TEXT,
        product_guess TEXT, product_slug TEXT, slug TEXT, url TEXT UNIQUE, reference_p1_url TEXT,
        html_title TEXT, h1 TEXT, lastmod TEXT, http_status TEXT, image_urls TEXT,
        source_sitemap TEXT, fetch_error TEXT, is_likely_article INTEGER
    )""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS content_reference_runs (
        run_id TEXT, original_label TEXT, domain TEXT, guessed_domain INTEGER, sitemap_index TEXT,
        sitemap_status TEXT, sitemap_error TEXT, sitemaps_read INTEGER, urls_found INTEGER,
        pages_fetched INTEGER, duration_sec REAL, PRIMARY KEY(run_id, domain)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_domain ON content_reference_urls(domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_product ON content_reference_urls(product_slug, product_guess)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_type ON content_reference_urls(article_type, country, vertical)")


def upsert_rows(conn, rows):
    cols=["run_id","mapped_at","original_label","domain","guessed_domain","article_type","sitemap_rec_classification","country","vertical","product_guess","product_slug","slug","url","reference_p1_url","html_title","h1","lastmod","http_status","image_urls","source_sitemap","fetch_error","is_likely_article"]
    sql=f"INSERT INTO content_reference_urls ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) ON CONFLICT(url) DO UPDATE SET " + ",".join([f"{c}=excluded.{c}" for c in cols if c!="url"])
    conn.executemany(sql, [[r.get(c,"") for c in cols] for r in rows])


def main():
    if len(sys.argv)<2:
        print("usage: map_content_references.py domains.txt", file=sys.stderr); return 2
    domains_file=Path(sys.argv[1])
    ROOT.mkdir(parents=True, exist_ok=True); RUN_DIR.mkdir(parents=True, exist_ok=True)
    items=[]; seen=set()
    for line in domains_file.read_text().splitlines():
        if not line.strip(): continue
        label,domain,guessed=normalize_domain(line)
        if domain in seen: continue
        seen.add(domain); items.append((label,domain,guessed))
    all_rows=[]; summaries=[]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_DOMAINS) as ex:
        futs={ex.submit(collect_domain,*item): item for item in items}
        for fut in as_completed(futs):
            item=futs[fut]
            try:
                rows, summary=fut.result()
            except Exception as e:
                label,domain,guessed=item
                rows=[]; summary={"original_label":label,"domain":domain,"guessed_domain":guessed,"sitemap_index":f"https://{domain}/sitemap_index.xml","sitemap_status":"","sitemap_error":type(e).__name__+": "+str(e)[:300],"sitemaps_read":0,"urls_found":0,"pages_fetched":0,"duration_sec":0}
            all_rows.extend(rows); summaries.append(summary)
            print(json.dumps({"domain":summary["domain"],"status":summary["sitemap_status"],"urls":summary["urls_found"],"pages":summary["pages_fetched"],"error":summary["sitemap_error"][:80]}, ensure_ascii=False), flush=True)
    # write run artifacts
    rows_csv=RUN_DIR/"content-reference-urls.csv"
    summary_csv=RUN_DIR/"content-reference-summary.csv"
    rows_json=RUN_DIR/"content-reference-urls.json"
    summary_json=RUN_DIR/"content-reference-summary.json"
    fieldnames=["run_id","mapped_at","original_label","domain","guessed_domain","article_type","sitemap_rec_classification","country","vertical","product_guess","product_slug","slug","url","reference_p1_url","html_title","h1","lastmod","http_status","image_urls","source_sitemap","fetch_error","is_likely_article"]
    with rows_csv.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(all_rows)
    with summary_csv.open('w', newline='', encoding='utf-8') as f:
        keys=["original_label","domain","guessed_domain","sitemap_index","sitemap_status","sitemap_error","sitemaps_read","urls_found","pages_fetched","duration_sec"]
        w=csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(summaries)
    rows_json.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding='utf-8')
    summary_json.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    # sqlite upsert
    conn=sqlite3.connect(DB_PATH)
    ensure_db(conn)
    upsert_rows(conn, all_rows)
    conn.executemany("INSERT OR REPLACE INTO content_reference_runs VALUES (?,?,?,?,?,?,?,?,?,?,?)", [[s.get(k,"") for k in ["run_id","original_label","domain","guessed_domain","sitemap_index","sitemap_status","sitemap_error","sitemaps_read","urls_found","pages_fetched","duration_sec"]] for s in []])
    # manual insert with run_id included
    conn.executemany("INSERT OR REPLACE INTO content_reference_runs (run_id,original_label,domain,guessed_domain,sitemap_index,sitemap_status,sitemap_error,sitemaps_read,urls_found,pages_fetched,duration_sec) VALUES (?,?,?,?,?,?,?,?,?,?,?)", [[RUN_ID,s["original_label"],s["domain"],s["guessed_domain"],s["sitemap_index"],str(s["sitemap_status"] or ""),s["sitemap_error"],s["sitemaps_read"],s["urls_found"],s["pages_fetched"],s["duration_sec"]] for s in summaries])
    conn.commit(); conn.close()
    ok=sum(1 for s in summaries if s.get("urls_found",0)>0)
    total_urls=len(all_rows)
    likely=sum(1 for r in all_rows if r.get("is_likely_article"))
    rec=sum(1 for r in all_rows if r.get("article_type")=="REC")
    result={"run_id":RUN_ID,"domains_input":len(items),"domains_with_urls":ok,"total_urls":total_urls,"likely_articles":likely,"rec_urls":rec,"db_path":str(DB_PATH),"run_dir":str(RUN_DIR),"rows_csv":str(rows_csv),"summary_csv":str(summary_csv)}
    (RUN_DIR/"result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print("FINAL " + json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
