#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv, io, json, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

BASE=Path('/root/mgs-agent')
SHEET='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
TOKEN_FILE=BASE/'.secrets/ares-google-drive-oauth-client.json'
IGNORE_FILE=BASE/'data/mgs-global-page-ignore-list.json'
OUT=BASE/'work/sheet-phase1-update-20260708'
OUT.mkdir(parents=True,exist_ok=True)
NY=ZoneInfo('America/New_York')
GID_RESUMO='315043175'
GID_DTR_SEM_SB='130786795'

def fetch_csv(gid):
    url=f'https://docs.google.com/spreadsheets/d/{SHEET}/gviz/tq?tqx=out:csv&gid={gid}'
    data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8-sig','replace')
    return [r for r in csv.reader(io.StringIO(data)) if any(c.strip() for c in r)]

def tok():
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

def sheet_titles():
    meta=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}?fields=sheets(properties(sheetId,title))')
    return {str(s['properties']['sheetId']):s['properties']['title'] for s in meta['sheets']}

def update_title_range(title, values):
    # Clear broad range first so stale columns/rows disappear in CSV export.
    api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{q(title)}!A1:Z1000:clear',{})
    api('PUT',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{q(title)}!A1?valueInputOption=RAW',{'majorDimension':'ROWS','values':values},timeout=180)

def main():
    global ACCESS
    before_resumo=fetch_csv(GID_RESUMO)
    before_dtr=fetch_csv(GID_DTR_SEM_SB)
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    with (OUT/f'backup-before-global-ignore-phase1-{stamp}.json').open('w',encoding='utf-8') as f:
        json.dump({'resumo':before_resumo,'dtr_sem_sb':before_dtr},f,ensure_ascii=False,indent=2)
    ignore=json.loads(IGNORE_FILE.read_text())
    entries=ignore.get('entries',[])
    counts=Counter(e.get('decision_status') for e in entries)
    now=datetime.now(NY).isoformat(timespec='seconds')
    dtr_values=[
        ['Estado','Qtd','Regra operacional','Fonte'],
        ['PENDÊNCIA ACIONÁVEL', '0', 'Nenhuma página desta aba deve ser cadastrada/varrida agora.', 'Correção Rodolfo 2026-07-08'],
        ['IGNORADAS GLOBALMENTE', str(len(entries)), 'Páginas antigas/fora de nicho dos seguradores; match com DTR/SB é irrelevante; nunca consultar/varrer/cadastrar.', str(IGNORE_FILE)],
        ['BLOCKED', str(counts.get('BLOCKED',0)), 'Ignorar 100% do sistema MGS.', 'Aba Custom BKP gid=1798040517'],
        ['IGNORAR', str(counts.get('IGNORAR',0)), 'Ignorar 100% do sistema MGS.', 'Aba Custom BKP gid=1798040517'],
        ['Detalhe das páginas', '', 'Ver aba Fase 1 - DTR sem SB Custom BKP / FULL BKP e ignore-list canônica.', ''],
    ]
    # Preserve a compact audit section in the same tab, but not as pending rows.
    dtr_values += [['','','',''], ['Bot user DTR','Segurador DTR','Página DTR','PAGE_ID / PG','FB_PAGE_ID','Status decisão','Efeito']]
    for e in entries:
        dtr_values.append([e.get('bot_user',''),e.get('dtr_account',''),e.get('page_name',''),e.get('page_id_pg',''),e.get('fb_page_id',''),e.get('decision_status',''),'GLOBAL_IGNORE_DO_NOT_SCAN'])
    resumo_values=[
        ['Código técnico','Legenda humana','Valor'],
        ['Atualizado em','Horário do relatório/correção aplicado',now],
        ['Fonte','Fonte canônica da exclusão global',str(IGNORE_FILE)],
        ['Usuários DTR lidos','Logins do DigitalTRChat auditados','88/88'],
        ['Seguradores DTR lidos','Seguradores/accounts varridos no DTR','226'],
        ['Páginas DTR lidas','Páginas encontradas no DTR','2911'],
        ['Publishers SB','Publishers SmartBidding no escopo completo','56'],
        ['Rows SB live','Linhas lidas em Accounts > Messenger > Page','2885'],
        ['Matches OK','Páginas batendo entre DTR e SB antes do filtro de ignore','2874'],
        ['DTR sem SB acionável','Páginas no DTR sem cadastro na SB após aplicar ignore-list global','0'],
        ['DTR sem SB ignorado global','Páginas antigas/fora de nicho, não entram em varredura nem comparação','36'],
        ['BLOCKED ignorado','Entradas BLOCKED na ignore-list global',str(counts.get('BLOCKED',0))],
        ['IGNORAR ignorado','Entradas IGNORAR na ignore-list global',str(counts.get('IGNORAR',0))],
        ['Login divergente','Mesmo FB_PAGE_ID/PAGE_ID, mas login diferente','1'],
        ['SB sem DTR','Rows na SB sem match no DTR','10'],
        ['Regra final','Global ignore vence match: não consultar DTR/Bot, não comparar com SB, não cadastrar, não agendar, não fazer backfill','ATIVA'],
    ]
    # Save local TSV mirrors
    for path, vals in [(OUT/'fase1-dtr-sem-sb.tsv', dtr_values),(OUT/'00-resumo-fase1.tsv', resumo_values)]:
        with path.open('w',encoding='utf-8',newline='') as f: csv.writer(f,delimiter='\t',lineterminator='\n').writerows(vals)
    ACCESS=tok(); titles=sheet_titles()
    update_title_range(titles[GID_DTR_SEM_SB], dtr_values)
    update_title_range(titles[GID_RESUMO], resumo_values)
    rb_dtr=fetch_csv(GID_DTR_SEM_SB); rb_res=fetch_csv(GID_RESUMO)
    result={'updated_at_et':now,'gid_dtr_sem_sb':GID_DTR_SEM_SB,'gid_resumo':GID_RESUMO,'ignored_entries':len(entries),'counts':dict(counts),'readback_dtr_rows':len(rb_dtr)-1,'readback_resumo_rows':len(rb_res)-1,'backup':str(OUT/f'backup-before-global-ignore-phase1-{stamp}.json')}
    (OUT/'apply-global-ignore-phase1-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
