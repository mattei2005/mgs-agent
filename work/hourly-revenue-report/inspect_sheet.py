#!/usr/bin/env python3
import importlib.util, json, urllib.parse
from pathlib import Path
HELPER=Path('/root/mgs-agent/scripts/mgs_google_workspace_auth.py')
SHEET_ID='1dNRy8Yu4s5YTopEOzSu7BcoG8PyXPt82BcPy_FxUMWo'
spec=importlib.util.spec_from_file_location('mgs_google_workspace_auth',HELPER)
if not spec or not spec.loader: raise RuntimeError('helper unavailable')
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
token=g.service_account_access_token(); project=g.service_account_project_id(); sa=g.load_service_account()
if project!='mgs-core-prod' or sa.get('client_email')!='mgsagent@mgs-core-prod.iam.gserviceaccount.com': raise RuntimeError('canonical identity mismatch')
def api(method,url,payload=None):
    status,data=g.api_json(method,url,token,payload,quota_project=project)
    if status not in (200,201): raise RuntimeError(f'{method} HTTP {status}: {(data.get("error") or {}).get("status")}')
    return data
fields=urllib.parse.quote('id,name,driveId,trashed,capabilities(canEdit,canModifyContent)',safe=',()')
drive=api('GET',f'https://www.googleapis.com/drive/v3/files/{SHEET_ID}?supportsAllDrives=true&fields={fields}')
meta=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=spreadsheetId,properties.title,sheets.properties')
if drive.get('trashed') or not (drive.get('capabilities') or {}).get('canEdit') or not (drive.get('capabilities') or {}).get('canModifyContent'): raise RuntimeError('not editable')
tabs=[]
for s in meta.get('sheets') or []:
    p=s.get('properties') or {}
    tabs.append({'sheetId':p.get('sheetId'),'title':p.get('title'),'index':p.get('index'),'rows':(p.get('gridProperties') or {}).get('rowCount'),'columns':(p.get('gridProperties') or {}).get('columnCount')})
first=next((x for x in tabs if x['sheetId']==0),tabs[0] if tabs else None)
preview=[]
if first:
    rng=urllib.parse.quote(f"'{first['title']}'!A1:Z12",safe='')
    preview=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{rng}?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE').get('values') or []
print(json.dumps({'drive_name':drive.get('name'),'title':(meta.get('properties') or {}).get('title'),'canEdit':True,'tabs':tabs,'gid0':first,'preview':preview},ensure_ascii=False))
