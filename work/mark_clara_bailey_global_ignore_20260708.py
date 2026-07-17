#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv, io, json, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
SHEET='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
TOKEN_FILE=BASE/'.secrets/ares-google-drive-oauth-client.json'
NY=ZoneInfo('America/New_York')

def token():
    c=json.loads(TOKEN_FILE.read_text())
    body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=body),timeout=30).read())['access_token']

def api(method,url,data=None,timeout=120):
    body=None; h={'Authorization':'Bearer '+ACCESS}
    if data is not None:
        body=json.dumps(data).encode(); h['Content-Type']='application/json; charset=UTF-8'
    raw=urllib.request.urlopen(urllib.request.Request(url,method=method,headers=h,data=body),timeout=timeout).read()
    return json.loads(raw) if raw else {}

def q(s): return urllib.parse.quote(s,safe="!:'")
ACCESS=token()
# backup current target ranges
backup={}
for rng in ["'CADASTRO NA DASH'!A94:N94","'00 Resumo Fase 1'!A1:C30"]:
    backup[rng]=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{q(rng)}')
out=BASE/'work/sheet-phase1-update-20260708'/f'backup-before-clara-bailey-ignore-{datetime.now(NY).strftime("%Y%m%d-%H%M%S")}.json'
out.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')
# update Clara row: keep identity columns, mark not operational
row=['disparosxyvlov@gmail.com','838404979365746','13794','Clara Bailey','United States','Credit card','Facebook','pg_13794','IGNORAR','Removida do DTR / não é página MGS — global ignore','NÃO CADASTRAR','', '', 'GLOBAL_IGNORE_DO_NOT_SCAN']
api('PUT',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{q("'CADASTRO NA DASH'!A94:N94")}?valueInputOption=RAW',{'majorDimension':'ROWS','values':[row]})
# update summary rows by rewriting concise current Fase 1 summary values
summary=[
 ['Código técnico','Legenda humana','Valor'],
 ['Atualizado em','Horário da correção aplicado',datetime.now(NY).isoformat(timespec='seconds')],
 ['Fonte','Fonte canônica da exclusão global','/root/mgs-agent/data/mgs-global-page-ignore-list.json'],
 ['DTR sem SB acionável','Páginas no DTR sem cadastro na SB após aplicar ignore-list global','0'],
 ['DTR sem SB ignorado global','Páginas antigas/fora de nicho, não entram em varredura nem comparação','37'],
 ['Cadastro na Dash pendente','Páginas da aba cadastro ainda faltando na SB após excluir global ignore','0'],
 ['Cadastro na Dash feito','Páginas da aba cadastro encontradas na SB','113'],
 ['Clara Bailey','Removida do DTR / não é página MGS; não cadastrar','GLOBAL_IGNORE'],
 ['Login divergente','Mesmo FB_PAGE_ID/PAGE_ID, mas login diferente live','0'],
 ['SB sem DTR não Blocked','Rows na SB sem match no DTR e ainda não Blocked','10'],
 ['Regra final','Global ignore vence match/cadastro/scan/schedule/backfill','ATIVA'],
]
api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{q("'00 Resumo Fase 1'!A1:C30")}:clear',{})
api('PUT',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{q("'00 Resumo Fase 1'!A1")}?valueInputOption=RAW',{'majorDimension':'ROWS','values':summary})
print(json.dumps({'updated':'Clara Bailey marked IGNORAR and summary adjusted','backup':str(out)},ensure_ascii=False,indent=2))
