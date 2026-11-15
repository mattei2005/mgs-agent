#!/usr/bin/env python3
"""Supplement required by real installed regression: from-zero consumer app binding."""
import hashlib,json
from pathlib import Path
R=Path('/root/mgs-agent');H=Path(__file__).parent
changes={}
for name in ['scripts/ares_campaign_v3/eggbev_create.py','scripts/ares-eggbev-creation.py']:
 p=R/name;s=p.read_text();b=H/'backup'/name;b.parent.mkdir(parents=True,exist_ok=True);assert not b.exists();b.write_text(s)
 if name.endswith('eggbev_create.py'):
  old='    adset_name: str = "AdG1",\n) -> dict[str, Any]:';assert s.count(old)==1;s=s.replace(old,'    adset_name: str = "AdG1",\n    app_key: str = APP_KEY,\n) -> dict[str, Any]:')
  old='                "app_key": APP_KEY,';assert s.count(old)==2;s=s.replace(old,'                "app_key": _clean_display(app_key, "app_key"),',1)
 else:
  old='def seal_manifest_from_state(state: dict[str, Any], start_time: str)';assert s.count(old)==1;s=s.replace(old,'def runtime_app_key() -> str:\n    """Exact account app binding; never inherit the previous issuer in a live manifest."""\n    return load_json(CONFIG_PATH)["accounts"][ACCOUNT_ID]["app_key"]\n\n\n'+old)
  old='        registry=registry,\n        request_id=str(state["request_id"]),';assert s.count(old)==1;s=s.replace(old,'        registry=registry,\n        app_key=runtime_app_key(),\n        request_id=str(state["request_id"]),')
  for old in ['registry=registry, request_id="eggbev-offline-smoke"','registry=registry, request_id=args.request_id']:
   assert s.count(old)==1;s=s.replace(old,old.replace('registry=registry,','registry=registry, app_key=runtime_app_key(),'))
 dest=H/'staged'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(s)
 changes[name]={'before_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
 (H/'isolated'/name).write_text(s)
(H/'supplement-changes.json').write_text(json.dumps(changes,indent=2)+'\n');print('supplement staged 2 exact consumers')
