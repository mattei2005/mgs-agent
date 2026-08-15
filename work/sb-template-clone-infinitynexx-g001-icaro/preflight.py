#!/usr/bin/env python3
import asyncio
import importlib.util
import json
from pathlib import Path

BASE = Path('/root/mgs-agent')
SOURCE = 'Infinitynexx - MX-CC-ES/ES-ZW-SR - g004-d Joe'
TARGET = 'Infinitynexx - MX-CC-ES/ES-ZW-SR - g001-d Icaro'
OUT = BASE / 'work' / 'sb-template-clone-infinitynexx-g001-icaro'

spec = importlib.util.spec_from_file_location('mgr', BASE / 'scripts' / 'sb-utility-rollout-manager.py')
mgr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mgr)

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = browser = ctx = page = None
    try:
        p, browser, ctx, page, rows, headers, post_url = await mgr.capture_rows_headers()
        sources = [r for r in rows if r.get('NAME') == SOURCE]
        targets = [r for r in rows if r.get('NAME') == TARGET]
        if len(sources) != 1:
            raise RuntimeError(f'exact source count {len(sources)}')
        source = sources[0]
        (OUT / 'source-live-before.json').write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding='utf-8')
        msgs = mgr.parse_messages(source)
        links = []
        for msg in msgs:
            for key in ('LINK_1', 'LINK_2'):
                value = msg.get(key)
                if value:
                    links.append(value)
        buttons = await page.get_by_role('button').all_inner_texts()
        print(json.dumps({
            'source_found': len(sources),
            'target_found': len(targets),
            'source_id': source.get('ID'),
            'source_company': source.get('COMPANY'),
            'source_publisher_id': source.get('PUBLISHER_ID'),
            'source_language': source.get('LANGUAGE'),
            'source_pages': source.get('PAGES'),
            'source_leads': source.get('LEADS'),
            'message_count': len(msgs),
            'link_count': len(links),
            'g004_link_count': sum('utm_medium=g004-d' in x for x in links),
            'g001_link_count': sum('utm_medium=g001-d' in x for x in links),
            'field_keys': sorted(source.keys()),
            'buttons': buttons,
            'post_url': post_url,
            'backup': str(OUT / 'source-live-before.json'),
        }, ensure_ascii=False, indent=2))
    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()

if __name__ == '__main__':
    asyncio.run(main())
