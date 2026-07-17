#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv,json,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
SHEET_ID='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
TOKEN_FILE=BASE/'.secrets/ares-google-drive-oauth-client.json'
IGNORE_FILE=BASE/'data/mgs-global-page-ignore-list.json'
OUT=BASE/'work/sheet-bkp-restore-20260708'
OUT.mkdir(parents=True,exist_ok=True)
NY=ZoneInfo('America/New_York')
DESIRED_TITLE='Fase 1 - DTR sem SB Custom BKP'

def token():
    c=json.loads(TOKEN_FILE.read_text())
    body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=body),timeout=30).read())['access_token']
ACCESS=None
def api(method,url,data=None,timeout=180):
    body=None; h={'Authorization':'Bearer '+ACCESS}
    if data is not None:
        body=json.dumps(data).encode(); h['Content-Type']='application/json; charset=UTF-8'
    req=urllib.request.Request(url,method=method,headers=h,data=body)
    try:
        raw=urllib.request.urlopen(req,timeout=timeout).read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode(errors="ignore")[:1000]}')

def q(s): return urllib.parse.quote(s,safe='')
def unique_title(base, existing):
    if base not in existing: return base
    n=2
    while f'{base} {n}' in existing: n+=1
    return f'{base} {n}'

def main():
    global ACCESS
    data=json.loads(IGNORE_FILE.read_text())
    entries=sorted(data.get('entries',[]), key=lambda e:int(e.get('source_row') or 0))
    header=['Bot user DTR','Segurador DTR','Página DTR','PAGE_ID / PG','Status decisão','Ação / observação','FB_PAGE_ID','Facebook URL','Fonte','Row original','Efeito sistêmico']
    values=[header]
    for e in entries:
        values.append([
            e.get('bot_user',''), e.get('dtr_account',''), e.get('page_name',''), e.get('page_id_pg',''),
            e.get('decision_status',''), e.get('decision_action',''), e.get('fb_page_id',''), e.get('facebook_url',''),
            f"{e.get('source_tab','')} gid={e.get('source_gid','')}", e.get('source_row',''),
            'Ignorar globalmente: não escanear DTR/Bot, não cadastrar na SB, não agendar, não fazer backfill'
        ])
    # local TSV backup too
    tsv=OUT/(DESIRED_TITLE+'.tsv')
    with tsv.open('w',encoding='utf-8',newline='') as f:
        csv.writer(f,delimiter='\t',lineterminator='\n').writerows(values)
    ACCESS=token()
    meta=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
    existing={s['properties']['title'] for s in meta.get('sheets',[])}
    title=unique_title(DESIRED_TITLE, existing)
    add=api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':[{'addSheet':{'properties':{'title':title}}}]})
    gid=add['replies'][0]['addSheet']['properties']['sheetId']
    api('PUT',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{q(title)}!A1?valueInputOption=RAW',{'majorDimension':'ROWS','values':values},timeout=240)
    width=len(header); rows=len(values)
    requests=[
        {'updateSheetProperties':{'properties':{'sheetId':gid,'gridProperties':{'frozenRowCount':1}},'fields':'gridProperties.frozenRowCount'}},
        {'setBasicFilter':{'filter':{'range':{'sheetId':gid,'startRowIndex':0,'endRowIndex':rows,'startColumnIndex':0,'endColumnIndex':width}}}},
        {'repeatCell':{'range':{'sheetId':gid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':width},'cell':{'userEnteredFormat':{'textFormat':{'bold':True,'foregroundColor':{'red':1,'green':1,'blue':1}},'backgroundColor':{'red':0.45,'green':0.13,'blue':0.13}}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
        {'autoResizeDimensions':{'dimensions':{'sheetId':gid,'dimension':'COLUMNS','startIndex':0,'endIndex':width}}}
    ]
    # color Status column E values: BLOCKED red-ish, IGNORAR yellow-ish via conditional formatting not necessary; static status column header enough.
    api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':requests},timeout=180)
    rb=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{q(title)}!A:A?majorDimension=COLUMNS')
    readback=max(0,len(rb.get('values',[[]])[0])-1)
    if readback != len(entries):
        raise RuntimeError(f'readback mismatch expected {len(entries)} got {readback}')
    result={'created_at_et':datetime.now(NY).isoformat(timespec='seconds'),'title':title,'gid':gid,'entries':len(entries),'readback':readback,'blocked':sum(1 for e in entries if e.get('decision_status')=='BLOCKED'),'ignorar':sum(1 for e in entries if e.get('decision_status')=='IGNORAR'),'source':str(IGNORE_FILE),'local_tsv':str(tsv),'url':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={gid}#gid={gid}'}
    (OUT/'restore-custom-ignore-tab-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
