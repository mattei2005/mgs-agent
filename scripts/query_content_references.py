#!/usr/bin/env python3
"""Query Atena content reference map.

Examples:
  python3 /root/mgs-agent/scripts/query_content_references.py "wells fargo" --limit 20
  python3 /root/mgs-agent/scripts/query_content_references.py "financiamento sem entrada" --domain utua.com.br
"""
from __future__ import annotations
import argparse, sqlite3, re
DB='/root/mgs-agent/data/content-reference-map/content_reference_map.sqlite'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('query')
    ap.add_argument('--domain')
    ap.add_argument('--type', dest='article_type')
    ap.add_argument('--limit', type=int, default=20)
    args=ap.parse_args()
    terms=[t for t in re.split(r'\s+', args.query.lower().strip()) if t]
    where=[]; params=[]
    for t in terms:
        where.append("lower(coalesce(url,'')||' '||coalesce(html_title,'')||' '||coalesce(h1,'')||' '||coalesce(product_guess,'')||' '||coalesce(product_slug,'')) LIKE ?")
        params.append('%'+t+'%')
    if args.domain:
        where.append('domain=?'); params.append(args.domain)
    if args.article_type:
        where.append('article_type=?'); params.append(args.article_type.upper())
    sql="""
    SELECT domain, article_type, country, vertical, product_guess, url, reference_p1_url, html_title, h1
    FROM content_reference_urls
    WHERE {where}
    ORDER BY CASE article_type WHEN 'REC' THEN 0 WHEN 'P1' THEN 1 ELSE 2 END,
             CASE WHEN html_title<>'' OR h1<>'' THEN 0 ELSE 1 END,
             domain, url
    LIMIT ?
    """.format(where=' AND '.join(where) if where else '1=1')
    params.append(args.limit)
    conn=sqlite3.connect(DB)
    cur=conn.execute(sql, params)
    for i,row in enumerate(cur.fetchall(),1):
        domain,typ,country,vertical,prod,url,p1,title,h1=row
        print(f"{i}. [{domain}] {typ} {country}/{vertical} — {prod}")
        print(f"   URL: {url}")
        if p1: print(f"   P1:  {p1}")
        if title: print(f"   Title: {title}")
        if h1 and h1 != title: print(f"   H1: {h1}")
    conn.close()
if __name__=='__main__': main()
