#!/usr/bin/env python3
import importlib.util, json, os, pathlib, urllib.parse, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

GOOGLE_AUTH_HELPER_PATH=pathlib.Path(__file__).resolve().parent/'mgs_google_workspace_auth.py'
_google_auth_spec=importlib.util.spec_from_file_location('mgs_google_workspace_auth',GOOGLE_AUTH_HELPER_PATH)
if not _google_auth_spec or not _google_auth_spec.loader:
    raise RuntimeError(f'cannot load Google Service Account helper: {GOOGLE_AUTH_HELPER_PATH}')
GOOGLE_AUTH=importlib.util.module_from_spec(_google_auth_spec)
_google_auth_spec.loader.exec_module(GOOGLE_AUTH)

TOKEN_FILE=pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
AUTH_MODE=os.environ.get('MGS_GOOGLE_SHEETS_AUTH_MODE','service_account').strip().lower()
SHEET_ID='1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY'; GID=232316676
STATE_PATH=pathlib.Path('/root/mgs-agent/data/sb-restricted-pages-monitor.json')
NY=ZoneInfo('America/New_York')

COLS=8
ROWS_CLEAR=200

def token():
    if AUTH_MODE=='service_account':
        return GOOGLE_AUTH.service_account_access_token(GOOGLE_AUTH.SHEETS_SCOPE)
    if AUTH_MODE!='oauth':
        raise RuntimeError(f'unsupported Google Sheets auth mode: {AUTH_MODE}')
    c=json.loads(TOKEN_FILE.read_text())
    body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
    req=urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)['access_token']
ACCESS=token()

def api(method,url,data=None):
    body=None; h={'Authorization':'Bearer '+ACCESS}
    if AUTH_MODE=='service_account':
        h['x-goog-user-project']=GOOGLE_AUTH.service_account_project_id()
    if data is not None:
        body=json.dumps(data).encode(); h['Content-Type']='application/json; charset=UTF-8'
    req=urllib.request.Request(url,method=method,headers=h,data=body)
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            raw=r.read(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode(errors="ignore")[:1500]}') from e

def rgb(hexstr):
    h=hexstr.lstrip('#')
    return {'red':int(h[0:2],16)/255,'green':int(h[2:4],16)/255,'blue':int(h[4:6],16)/255}

NAVY=rgb('#0F2742'); BLUE=rgb('#1F4E79'); LIGHT=rgb('#EAF3FA'); VERY_LIGHT=rgb('#F7FAFC'); WHITE=rgb('#FFFFFF'); GRAY=rgb('#6B7280'); BORDER=rgb('#D9E2EC')

def clean_user(u): return (u or '').replace('@gmail.com','')
def segurador(r):
    pub=(r.get('publisher_id') or '').split('_',1)
    return r.get('profile_name') or (pub[1] if len(pub)>1 else (r.get('company') or ''))

def cell(value='', *, bold=False, bg=None, fg=None, size=None, align=None, valign='MIDDLE', wrap=False, link=None, number=None):
    c={}
    if isinstance(value, (int,float)):
        c['userEnteredValue']={'numberValue': value}
    else:
        c['userEnteredValue']={'stringValue': '' if value is None else str(value)}
    fmt={'verticalAlignment':valign}
    tf={}
    if bold: tf['bold']=True
    if fg: tf['foregroundColor']=fg
    if size: tf['fontSize']=size
    if link: tf['link']={'uri': link}; tf['foregroundColor']=rgb('#1155CC'); tf['underline']=True
    if tf: fmt['textFormat']=tf
    if bg: fmt['backgroundColor']=bg
    if align: fmt['horizontalAlignment']=align
    if wrap: fmt['wrapStrategy']='WRAP'
    if number: fmt['numberFormat']=number
    c['userEnteredFormat']=fmt
    return c

def blank_row(): return [cell('') for _ in range(COLS)]

def row(vals, **style):
    return [cell(v, **style) for v in vals] + [cell('') for _ in range(max(0, COLS-len(vals)))]

def build_rows():
    st=json.loads(STATE_PATH.read_text())
    active=list(st['active'].values())
    # The Sheet section is named "Novos". It must show only the delta from the
    # last monitor execution, never a sample of all active restricted pages.
    sample=st.get('last_new_rows') or []
    by=Counter(r.get('restricted_until') or '?' for r in active)
    detected=(st.get('last_check') or datetime.now(NY).isoformat(timespec='seconds')).replace('T',' ')[:16]
    rows=[]
    rows.append([cell('Registros SB de Restrição — MGS', bold=True, bg=NAVY, fg=WHITE, size=18, align='CENTER')] + [cell('', bg=NAVY) for _ in range(COLS-1)])
    rows.append([cell('Atualizado em ' + datetime.now(NY).strftime('%Y-%m-%d %H:%M %Z') + '  •  Fonte SB-only: DTR/Bot não lido nesta aba', bg=NAVY, fg=rgb('#DDEBFF'), size=10, align='CENTER')] + [cell('', bg=NAVY) for _ in range(COLS-1)])
    rows.append(blank_row())
    rows.append([cell('Resumo Executivo', bold=True, bg=BLUE, fg=WHITE, size=11)] + [cell('', bg=BLUE) for _ in range(COLS-1)])
    total_pages = int(st.get('last_total_rows', 0) or 0)
    on_hold_pages = int(st.get('last_on_hold_count', 0) or 0)
    block_pages = int(st.get('last_block_count', 0) or 0)
    restricted_pages = int(st.get('last_active_restricted_count', 0) or 0)
    sem_restricao_pages = int(st.get('last_sem_restricao_count', max(0, total_pages - on_hold_pages - block_pages - restricted_pages)) or 0)
    novas_pages = int((st.get('last_summary') or {}).get('new', 0) or 0)
    rows.append([cell('Total Paginas', bold=True, bg=LIGHT, align='CENTER'), cell('Paginas On-hold', bold=True, bg=LIGHT, align='CENTER'), cell('Paginas Block', bold=True, bg=LIGHT, align='CENTER'), cell('Paginas Restritas', bold=True, bg=LIGHT, align='CENTER'), cell('Sem Restricao', bold=True, bg=LIGHT, align='CENTER'), cell('Novas', bold=True, bg=LIGHT, align='CENTER')])
    rows.append([cell(total_pages, bold=True, size=13, align='CENTER'), cell(on_hold_pages, bold=True, size=13, align='CENTER'), cell(block_pages, bold=True, size=13, align='CENTER'), cell(restricted_pages, bold=True, size=13, align='CENTER'), cell(sem_restricao_pages, bold=True, size=13, align='CENTER'), cell(novas_pages, bold=True, size=13, align='CENTER')])
    rows.append(blank_row())
    rows.append([cell('Por Data de Saída', bold=True, bg=BLUE, fg=WHITE, size=11)] + [cell('', bg=BLUE) for _ in range(COLS-1)])
    rows.append([cell('Data saída', bold=True, bg=LIGHT), cell('Páginas', bold=True, bg=LIGHT)] + [cell('', bg=LIGHT) for _ in range(4)])
    for d,cnt in sorted(by.items(), key=lambda kv:kv[0])[:8]:
        rows.append([cell(d), cell(cnt, align='RIGHT')] + [cell('') for _ in range(COLS-2)])
    rows.append(blank_row())
    rows.append([cell('Registros SB com Restricted Until - Novos:', bold=True, bg=BLUE, fg=WHITE, size=11)] + [cell('', bg=BLUE) for _ in range(COLS-1)])
    rows.append([cell(x, bold=True, bg=LIGHT) for x in ['Entrou registro','Página','FB Page ID','Page ID','Usuário bot','Segurador','Expira SB','Origem']])
    for r in sample:
        fb=(r.get('fb_page_id') or '').strip(); uri=f'https://facebook.com/{fb}' if fb else None
        rows.append([cell(detected), cell(r.get('page_name') or '', link=uri), cell(fb), cell(r.get('page_id') or ''), cell(clean_user(r.get('user_login'))), cell(segurador(r)), cell(r.get('restricted_until') or ''), cell('SB-only; DTR não lido', bold=True, fg=rgb('#B45309'), bg=rgb('#FEF3C7'))])
    rows.append(blank_row())
    rows.append([cell('Legenda de Erros', bold=True, bg=BLUE, fg=WHITE, size=11)] + [cell('', bg=BLUE) for _ in range(COLS-1)])
    rows.append([cell('Código erro', bold=True, bg=LIGHT), cell('Significado', bold=True, bg=LIGHT), cell('', bg=LIGHT), cell('', bg=LIGHT), cell('Ação', bold=True, bg=LIGHT), cell('', bg=LIGHT), cell('', bg=LIGHT)])
    legend=[
        ('#2022','Página temporariamente restrita pelo Messenger/Facebook para envio de mensagens.','Registrar expiração, pular no DTR até liberar e rechecá-la depois.'),
        ('PERMISSION','Any of pages_read_engagement, pages_manage_metadata, pages_read_user_content, pages_manage_ads, pages_show_list or pages_messaging permission(s) must be granted before impersonating.','Revisar permissões do app/token/página e reconectar o perfil se necessário.'),
        ('APP_DELETED','Error validating application. Application has been deleted.','Migrar página para app válido ou corrigir configuração do app no segurador.'),
        ('#10_WINDOW','Mensagem enviada fora da janela permitida pela política do Messenger.','Não insistir no envio; revisar regra de janela/opt-in antes de nova tentativa.'),
        ('#551_UNAVAILABLE','(#551) Esta pessoa não está disponível no momento.','Tratar como indisponibilidade do destinatário; monitorar recorrência.'),
        ('#100_TEMPLATE','Erro de template: parâmetros ausentes/extras ou modelo/template não encontrado.','Corrigir template/params no Broadcast Template antes de reenviar.'),
        ('TOKEN','Mensagens típicas: Error validating access token; Invalid OAuth access token; Session has expired.','Renovar/reconectar token, perfil, página ou app afetado.'),
        ('OTHER','Erro não mapeado automaticamente.','Especificar a mensagem exata no report e classificar depois.'),
    ]
    for e,s,a in legend:
        rows.append([cell(e, bold=True), cell(s, wrap=True), cell(''), cell(''), cell(a, wrap=True), cell(''), cell('')])
    return rows

ss=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))')
props={s['properties']['sheetId']:s['properties'] for s in ss.get('sheets',[])}[GID]
title=props['title']; max_rows=max(props.get('gridProperties',{}).get('rowCount',1000),ROWS_CLEAR); max_cols=max(props.get('gridProperties',{}).get('columnCount',26),26)
rows=build_rows()
# Requests: unmerge, clear everything, write, merge title/section rows, widths, borders, hide gridlines.
requests=[]
requests.append({'unmergeCells': {'range': {'sheetId':GID, 'startRowIndex':0, 'endRowIndex':max_rows, 'startColumnIndex':0, 'endColumnIndex':max_cols}}})
requests.append({'updateCells': {'range': {'sheetId': GID, 'startRowIndex':0, 'endRowIndex':max_rows, 'startColumnIndex':0, 'endColumnIndex':max_cols}, 'fields': 'userEnteredValue,userEnteredFormat,note,textFormatRuns,dataValidation'}})
requests.append({'updateCells': {'start': {'sheetId':GID,'rowIndex':0,'columnIndex':0}, 'rows': [{'values': r} for r in rows], 'fields': 'userEnteredValue,userEnteredFormat'}})
# merge full-width title and section bars
for r in [0,1,3,7,18,25]:
    requests.append({'mergeCells': {'range': {'sheetId':GID,'startRowIndex':r,'endRowIndex':r+1,'startColumnIndex':0,'endColumnIndex':COLS}, 'mergeType':'MERGE_ALL'}})
# merge legend columns: Significado B:D, Ação E:G
for r in range(27, 36):
    requests.append({'mergeCells': {'range': {'sheetId':GID,'startRowIndex':r,'endRowIndex':r+1,'startColumnIndex':1,'endColumnIndex':4}, 'mergeType':'MERGE_ALL'}})
    requests.append({'mergeCells': {'range': {'sheetId':GID,'startRowIndex':r,'endRowIndex':r+1,'startColumnIndex':4,'endColumnIndex':COLS}, 'mergeType':'MERGE_ALL'}})
# widths
widths=[145,190,150,90,145,160,120,160]
for i,w in enumerate(widths):
    requests.append({'updateDimensionProperties': {'range': {'sheetId':GID,'dimension':'COLUMNS','startIndex':i,'endIndex':i+1}, 'properties': {'pixelSize':w}, 'fields':'pixelSize'}})
# row heights
requests.append({'updateDimensionProperties': {'range': {'sheetId':GID,'dimension':'ROWS','startIndex':0,'endIndex':2}, 'properties': {'pixelSize':34}, 'fields':'pixelSize'}})
# borders for compact tables
for start,end in [(4,5),(8,17),(19,24),(26,32)]:
    requests.append({'updateBorders': {'range': {'sheetId':GID,'startRowIndex':start,'endRowIndex':end+1,'startColumnIndex':0,'endColumnIndex':COLS}, 'top': {'style':'SOLID','width':1,'color':BORDER}, 'bottom': {'style':'SOLID','width':1,'color':BORDER}, 'left': {'style':'SOLID','width':1,'color':BORDER}, 'right': {'style':'SOLID','width':1,'color':BORDER}, 'innerHorizontal': {'style':'SOLID','width':1,'color':BORDER}, 'innerVertical': {'style':'SOLID','width':1,'color':BORDER}}})
requests.append({'updateSheetProperties': {'properties': {'sheetId':GID,'gridProperties': {'frozenRowCount':2, 'hideGridlines': True}}, 'fields':'gridProperties.frozenRowCount,gridProperties.hideGridlines'}})
# Alternating background for data rows in sample and legend subtle
for start,end in [(20,24),(27,31)]:
    for r in range(start,end+1):
        if r % 2 == 0:
            requests.append({'repeatCell': {'range': {'sheetId':GID,'startRowIndex':r,'endRowIndex':r+1,'startColumnIndex':0,'endColumnIndex':COLS}, 'cell': {'userEnteredFormat': {'backgroundColor': VERY_LIGHT}}, 'fields':'userEnteredFormat.backgroundColor'}})
api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':requests})
enc=urllib.parse.quote(title)
rb=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc}!A1:H45')
print(json.dumps({'ok':True,'rows_written':len(rows),'readback_rows':len(rb.get('values',[])),'url':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}#gid={GID}'},ensure_ascii=False,indent=2))
