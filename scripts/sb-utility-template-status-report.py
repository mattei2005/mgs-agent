#!/usr/bin/env python3
"""Live status report for exact SB Utility templates."""
import argparse, asyncio, collections, importlib.util, json, pathlib
BASE = pathlib.Path('/root/mgs-agent')
spec = importlib.util.spec_from_file_location('rollout', BASE / 'scripts/sb-utility-rollout-manager.py')
assert spec and spec.loader
rollout = importlib.util.module_from_spec(spec); spec.loader.exec_module(rollout)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', action='append', required=True)
    args = ap.parse_args()
    p,b,c,page,rows,headers,url = await rollout.capture_rows_headers()
    try:
        lines=[]
        for name in args.template:
            row=next((r for r in rows if r.get('NAME')==name), None)
            if not row:
                lines.append(f'{name}: NÃO ENCONTRADO')
                continue
            counts=collections.Counter(rollout.status_color(rollout.status_of(m)) for m in rollout.parse_messages(row))
            total=sum(counts.values())
            pages=row.get('PAGES')
            parts=' | '.join(f'{k}: {v}' for k,v in sorted(counts.items()))
            lines.append(f'{name}\nPAGES: {pages} | mensagens: {total} | {parts}')
        print('\n\n'.join(lines))
    finally:
        try: await b.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass
if __name__=='__main__':
    asyncio.run(main())
