#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv,json,io,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

BASE=Path('/root/mgs-agent')
SHEET_ID='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
TOKEN_FILE=BASE/'.secrets/ares-google-drive-oauth-client.json'
OUT=BASE/'work/sheet-bkp-restore-20260708'; OUT.mkdir(parents=True,exist_ok=True)
NY=ZoneInfo('America/New_York')
SOURCE_150_GID='177903400'  # Não encontrado por IDs BKP, restored from 2026-07-06 backup
CADASTRO_GID='907050576'
IGNORE_FILE=BASE/'data/mgs-global-page-ignore-list.json'
SCAN_CSV=BASE/'reports/dtr-missing-sb-page-lead-scan/result-20260707-194028.csv'
TITLE_BASE='Fase 1 - DTR sem SB Custom FULL BKP'

def fetch_csv_gid(gid):
    url=f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={gid}'
    data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8-sig','replace')
    return [r for r in csv.reader(io.StringIO(data)) if any(c.strip() for c in r)]

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
def unique(base, existing):
    if base not in existing: return base
    n=2
    while f'{base} {n}' in existing: n+=1
    return f'{base} {n}'

def main():
    global ACCESS
    no_sb=fetch_csv_gid(SOURCE_150_GID)
    src_header=no_sb[0]
    # columns in restored BKP: DTR Bot user=3, Segurador=4, Página=5, PG=6, FB=7, URL=8, email=9, raw=10
    rows150=[]
    for r in no_sb[1:]:
        rows150.append({
            'bot_user':r[3], 'account':r[4], 'page':r[5], 'pg':r[6], 'fb':r[7], 'url':r[8], 'email':r[9] if len(r)>9 else '', 'raw':r[10] if len(r)>10 else ''
        })
    scan={}
    with SCAN_CSV.open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            scan[(r.get('bot_user','').lower(), r.get('pg',''), r.get('fb_page_id',''))]=r
    ignore=json.loads(IGNORE_FILE.read_text())
    decisions={}
    for e in ignore.get('entries',[]):
        decisions[(e.get('bot_user','').lower(), e.get('page_id_pg',''), e.get('fb_page_id',''))]=e
    cadastro=fetch_csv_gid(CADASTRO_GID)
    cad_keys=set()
    for r in cadastro[1:]:
        if len(r)>=3:
            cad_keys.add((r[0].lower(), r[2], r[1]))
    header=['Bot user DTR','Segurador DTR','Página DTR','Leads / scan','Status decisão','Ação final','PAGE_ID / PG','FB_PAGE_ID','Facebook URL','DTR Email página','DTR raw','Cadastro payload?','Efeito sistêmico / observação']
    values=[header]
    for x in rows150:
        key=(x['bot_user'].lower(),x['pg'],x['fb'])
        sc=scan.get(key,{})
        lead=sc.get('lead_count','')
        scan_status=sc.get('status','')
        lead_cell=lead if lead not in ('',None) else scan_status
        dec=decisions.get(key)
        if dec:
            status=dec.get('decision_status','')
            action=dec.get('decision_action','')
            effect='Ignorar globalmente: não escanear DTR/Bot, não cadastrar na SB, não agendar, não fazer backfill'
            payload='NÃO'
        else:
            status='READY'
            action='cadastrar na dash e colocar o status broadcast e escolher template'
            effect='Acionável; payload correspondente esperado na aba CADASTRO NA DASH'
            payload='SIM' if key in cad_keys else 'NÃO_ENCONTRADO'
        values.append([x['bot_user'],x['account'],x['page'],lead_cell,status,action,x['pg'],x['fb'],x['url'],x['email'],x['raw'],payload,effect])
    counts=Counter(r[4] for r in values[1:])
    payload_counts=Counter(r[11] for r in values[1:])
    tsv=OUT/(TITLE_BASE+'.tsv')
    with tsv.open('w',encoding='utf-8',newline='') as f:
        csv.writer(f,delimiter='\t',lineterminator='\n').writerows(values)
    ACCESS=token()
    meta=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
    title=unique(TITLE_BASE,{s['properties']['title'] for s in meta.get('sheets',[])})
    add=api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':[{'addSheet':{'properties':{'title':title}}}]})
    gid=add['replies'][0]['addSheet']['properties']['sheetId']
    api('PUT',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{q(title)}!A1?valueInputOption=RAW',{'majorDimension':'ROWS','values':values},timeout=240)
    width=len(header); rows=len(values)
    requests=[
        {'updateSheetProperties':{'properties':{'sheetId':gid,'gridProperties':{'frozenRowCount':1}},'fields':'gridProperties.frozenRowCount'}},
        {'setBasicFilter':{'filter':{'range':{'sheetId':gid,'startRowIndex':0,'endRowIndex':rows,'startColumnIndex':0,'endColumnIndex':width}}}},
        {'repeatCell':{'range':{'sheetId':gid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':width},'cell':{'userEnteredFormat':{'textFormat':{'bold':True,'foregroundColor':{'red':1,'green':1,'blue':1}},'backgroundColor':{'red':0.12,'green':0.31,'blue':0.47}}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
        {'autoResizeDimensions':{'dimensions':{'sheetId':gid,'dimension':'COLUMNS','startIndex':0,'endIndex':width}}}
    ]
    api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':requests},timeout=180)
    rb=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{q(title)}!A:A?majorDimension=COLUMNS')
    readback=max(0,len(rb.get('values',[[]])[0])-1)
    if readback!=150: raise RuntimeError(f'readback mismatch: {readback}')
    result={'created_at_et':datetime.now(NY).isoformat(timespec='seconds'),'title':title,'gid':gid,'rows':150,'readback':readback,'status_counts':dict(counts),'payload_counts':dict(payload_counts),'local_tsv':str(tsv),'url':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={gid}#gid={gid}'}
    (OUT/'restore-full-custom-dtr-sem-sb-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
