#!/usr/bin/env python3
import hashlib, importlib.util, json, math, urllib.parse, uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
P=BASE/'work/hourly-revenue-report'
HELPER=BASE/'scripts/mgs_google_workspace_auth.py'
SHEET_ID='1dNRy8Yu4s5YTopEOzSu7BcoG8PyXPt82BcPy_FxUMWo'
SUMMARY='Resumo atual'; DETAIL='Receita por hora'; NY=ZoneInfo('America/New_York'); CENT=Decimal('0.01')

spec=importlib.util.spec_from_file_location('mgs_google_workspace_auth',HELPER)
if not spec or not spec.loader: raise RuntimeError('canonical helper unavailable')
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
token=g.service_account_access_token(); project=g.service_account_project_id(); sa=g.load_service_account()
if project!='mgs-core-prod' or sa.get('client_email')!='mgsagent@mgs-core-prod.iam.gserviceaccount.com': raise RuntimeError('canonical Google identity mismatch')

def api(method,url,payload=None):
    status,data=g.api_json(method,url,token,payload,quota_project=project)
    if status not in (200,201): raise RuntimeError(f'Google API {method} HTTP {status}: {(data.get("error") or {}).get("status")}')
    return data

def enc(s): return urllib.parse.quote(s,safe='')
def rows_file(date,kind):
    d=json.loads((P/f'{date}-{kind}.json').read_text())
    return d if isinstance(d,list) else next((d[k] for k in ('data','rows','result','results') if isinstance(d.get(k),list)),[])
def dec(v): return Decimal(str(v or 0))
def money(v): return float(dec(v).quantize(CENT,rounding=ROUND_HALF_UP))
def pct(a,b): return float(((a-b)/b).quantize(Decimal('0.000001'),rounding=ROUND_HALF_UP)) if b else None
def meta(): return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=spreadsheetId,properties.title,sheets.properties')
def values(title,rng):
    return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc(chr(39)+title+chr(39)+"!"+rng)}?majorDimension=ROWS&valueRenderOption=UNFORMATTED_VALUE').get('values') or []
def put(title,start,vals):
    a1=f"'{title}'!{start}"
    api('PUT',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc(a1)}?valueInputOption=RAW',{'range':a1,'majorDimension':'ROWS','values':vals})
def clear(title,rng):
    a1=f"'{title}'!{rng}"; api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc(a1)}:clear',{})
def canon(rows):
    out=[]
    for row in rows:
        o=[]
        for v in row:
            if isinstance(v,(int,float)) and not isinstance(v,bool): o.append(round(float(v),6))
            elif v is None: o.append('')
            else: o.append(v)
        while o and o[-1]=='': o.pop()
        out.append(o)
    return out

def main():
    now=datetime.now(NY); today=now.date().isoformat(); yesterday=now.date().fromordinal(now.date().toordinal()-1).isoformat()
    ct_rows=rows_file(today,'cumulative'); it_rows=rows_file(today,'incremental'); cy_rows=rows_file(yesterday,'cumulative'); iy_rows=rows_file(yesterday,'incremental')
    ct={(r['COMPANY'],r['DOMAIN'],int(r['TIME'])):dec(r.get('NET_REVENUE')) for r in ct_rows}; it={(r['COMPANY'],r['DOMAIN'],int(r['TIME'])):dec(r.get('NET_REVENUE')) for r in it_rows}
    cy={(r['COMPANY'],r['DOMAIN'],int(r['TIME'])):dec(r.get('NET_REVENUE')) for r in cy_rows}; iy={(r['COMPANY'],r['DOMAIN'],int(r['TIME'])):dec(r.get('NET_REVENUE')) for r in iy_rows}
    keys=sorted({k[:2] for m in (ct,it,cy,iy) for k in m}); max_hour=max(k[2] for k in ct)
    if max_hour!=now.hour: raise RuntimeError(f'current-hour freshness mismatch: report={max_hour}, ET={now.hour}')
    cutoff=max_hour
    def cumulative(m,key,h):
        company,domain=key
        return next((m[(company,domain,x)] for x in range(h,-1,-1) if (company,domain,x) in m),Decimal(0))
    issues=[]
    for cm,im,label in ((ct,it,today),(cy,iy,yesterday)):
        for key in keys:
            prev=Decimal(0)
            for h in range(24):
                cur=cumulative(cm,key,h); inc=im.get((*key,h),Decimal(0))
                if abs((cur-prev)-inc)>Decimal('0.02'): issues.append((label,*key,h,str((cur-prev)-inc)))
                prev=cur
    if issues: raise RuntimeError(f'cumulative/incremental validation failed: {issues[:3]}')
    scope=json.loads((P/'company.json').read_text()); scope_companies={c['companyId']:len(c['publishers']) for c in scope}
    if scope_companies!={'digital-trust':45,'digital-trust-2':7}: raise RuntimeError(f'publisher scope mismatch: {scope_companies}')
    summary_data=[]
    for key in keys:
        th=cumulative(ct,key,cutoff); yh=cumulative(cy,key,cutoff); ih=it.get((*key,cutoff),Decimal(0)); ioy=iy.get((*key,cutoff),Decimal(0))
        summary_data.append([key[0],key[1],money(th),money(yh),money(th-yh),pct(th,yh),money(ih),money(ioy),money(ih-ioy),pct(ih,ioy)])
    summary_data.sort(key=lambda r:(-r[2],r[0],r[1]))
    t_th=sum((cumulative(ct,k,cutoff) for k in keys),Decimal(0)); t_yh=sum((cumulative(cy,k,cutoff) for k in keys),Decimal(0)); t_ih=sum((it.get((*k,cutoff),Decimal(0)) for k in keys),Decimal(0)); t_ioy=sum((iy.get((*k,cutoff),Decimal(0)) for k in keys),Decimal(0))
    total=['TOTAL','TODOS OS DOMÍNIOS',money(t_th),money(t_yh),money(t_th-t_yh),pct(t_th,t_yh),money(t_ih),money(t_ioy),money(t_ih-t_ioy),pct(t_ih,t_ioy)]
    extracted=now.strftime('%d/%m/%Y %H:%M:%S %Z')
    summary=[
        ['Receita por domínio — hoje x ontem'],
        ['Atualizado em (ET)',extracted],
        ['Período comparado',f'00h–{cutoff:02d}h; a hora {cutoff:02d}h está parcial'],
        ['Empresas selecionadas','Digital trust + Digital trust 2'],
        ['Domínios selecionados','Todos (52 publishers: 45 + 7)'],
        ['Fonte','Smart Bidding > Reports > Photo by Vertical; métrica REVENUE (NET_REVENUE)'],
        ['Observação','Digital trust 2 não retornou linhas de receita em hoje nem ontem'],
        [],
        ['EMPRESA','DOMÍNIO',f'HOJE ATÉ {cutoff:02d}H',f'ONTEM ATÉ {cutoff:02d}H','DIFERENÇA R$','VARIAÇÃO %',f'HORA {cutoff:02d}H HOJE',f'HORA {cutoff:02d}H ONTEM','DIF. HORA R$','VAR. HORA %'],
        total,*summary_data,
    ]
    detail=[
        ['Receita incremental e acumulada por hora — hoje x ontem'],
        ['Atualizado em (ET)',extracted],
        ['Corte',f'00h–{cutoff:02d}h; a hora {cutoff:02d}h está parcial'],
        ['Escopo','Digital trust + Digital trust 2; todos os 52 publishers'],
        [],
        ['HORA','EMPRESA','DOMÍNIO','HOJE NA HORA','ONTEM NA HORA','DIFERENÇA R$','VARIAÇÃO %','ACUM. HOJE','ACUM. ONTEM','DIF. ACUM. R$','VAR. ACUM. %'],
    ]
    for h in range(cutoff+1):
        hour_rows=[]
        ht=hy=hat=hay=Decimal(0)
        for key in keys:
            a=it.get((*key,h),Decimal(0)); b=iy.get((*key,h),Decimal(0)); ac=cumulative(ct,key,h); bc=cumulative(cy,key,h)
            ht+=a; hy+=b; hat+=ac; hay+=bc
            hour_rows.append([f'{h:02d}:00',key[0],key[1],money(a),money(b),money(a-b),pct(a,b),money(ac),money(bc),money(ac-bc),pct(ac,bc)])
        hour_rows.sort(key=lambda r:(-r[3],r[1],r[2]))
        detail.append([f'{h:02d}:00','TOTAL','TODOS OS DOMÍNIOS',money(ht),money(hy),money(ht-hy),pct(ht,hy),money(hat),money(hay),money(hat-hay),pct(hat,hay)])
        detail.extend(hour_rows)

    # Drive + Sheets target preflight and exact backup.
    fields=urllib.parse.quote('id,name,driveId,trashed,capabilities(canEdit,canModifyContent)',safe=',()')
    drive=api('GET',f'https://www.googleapis.com/drive/v3/files/{SHEET_ID}?supportsAllDrives=true&fields={fields}')
    caps=drive.get('capabilities') or {}
    if drive.get('trashed') or not caps.get('canEdit') or not caps.get('canModifyContent'): raise RuntimeError('target is not editable')
    before_meta=meta(); before_tabs=[s.get('properties') or {} for s in before_meta.get('sheets') or []]
    if len(before_tabs)!=1 or before_tabs[0].get('sheetId')!=0 or before_tabs[0].get('title')!='Sheet1': raise RuntimeError('unexpected target Sheet structure')
    before_values=values('Sheet1','A1:Z1000')
    if before_values: raise RuntimeError('target Sheet is no longer empty')
    (P/'sheet-before.json').write_text(json.dumps({'metadata':before_meta,'values':before_values},ensure_ascii=False,indent=2)+'\n')

    # Reversible canary in a blank edge cell.
    sentinel='MGS-CANARY-'+uuid.uuid4().hex
    if values('Sheet1','Z1000'): raise RuntimeError('canary cell is not blank')
    put('Sheet1','Z1000',[[sentinel]])
    if values('Sheet1','Z1000')!=[[sentinel]]: raise RuntimeError('canary readback failed')
    clear('Sheet1','Z1000')
    if values('Sheet1','Z1000'): raise RuntimeError('canary restore failed')

    created_detail=False
    try:
        api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':[
            {'updateSheetProperties':{'properties':{'sheetId':0,'title':SUMMARY,'gridProperties':{'rowCount':max(100,len(summary)+20),'columnCount':12,'frozenRowCount':9}},'fields':'title,gridProperties.rowCount,gridProperties.columnCount,gridProperties.frozenRowCount'}},
            {'addSheet':{'properties':{'title':DETAIL,'gridProperties':{'rowCount':len(detail)+20,'columnCount':12,'frozenRowCount':6}}}},
        ]})
        created_detail=True
        put(SUMMARY,'A1',summary); put(DETAIL,'A1',detail)
        m=meta(); props={s['properties']['title']:s['properties'] for s in m.get('sheets') or []}; dsid=props[DETAIL]['sheetId']
        requests=[]
        # Title and headers.
        for sid,title_row,header_row,width in ((0,0,8,10),(dsid,0,5,11)):
            requests.extend([
                {'repeatCell':{'range':{'sheetId':sid,'startRowIndex':title_row,'endRowIndex':title_row+1,'startColumnIndex':0,'endColumnIndex':width},'cell':{'userEnteredFormat':{'backgroundColor':{'red':0.10,'green':0.25,'blue':0.45},'textFormat':{'foregroundColor':{'red':1,'green':1,'blue':1},'bold':True,'fontSize':14}}},'fields':'userEnteredFormat'}},
                {'repeatCell':{'range':{'sheetId':sid,'startRowIndex':header_row,'endRowIndex':header_row+1,'startColumnIndex':0,'endColumnIndex':width},'cell':{'userEnteredFormat':{'backgroundColor':{'red':0.16,'green':0.42,'blue':0.67},'textFormat':{'foregroundColor':{'red':1,'green':1,'blue':1},'bold':True},'horizontalAlignment':'CENTER','wrapStrategy':'WRAP'}},'fields':'userEnteredFormat'}},
                {'setBasicFilter':{'filter':{'range':{'sheetId':sid,'startRowIndex':header_row,'endRowIndex':len(summary) if sid==0 else len(detail),'startColumnIndex':0,'endColumnIndex':width}}}},
                {'autoResizeDimensions':{'dimensions':{'sheetId':sid,'dimension':'COLUMNS','startIndex':0,'endIndex':width}}},
            ])
        # Total rows.
        requests.extend([
            {'repeatCell':{'range':{'sheetId':0,'startRowIndex':9,'endRowIndex':10,'startColumnIndex':0,'endColumnIndex':10},'cell':{'userEnteredFormat':{'backgroundColor':{'red':0.86,'green':0.92,'blue':0.98},'textFormat':{'bold':True}}},'fields':'userEnteredFormat'}},
            {'repeatCell':{'range':{'sheetId':0,'startRowIndex':9,'endRowIndex':len(summary),'startColumnIndex':2,'endColumnIndex':5},'cell':{'userEnteredFormat':{'numberFormat':{'type':'CURRENCY','pattern':'R$ #,##0.00'}}},'fields':'userEnteredFormat.numberFormat'}},
            {'repeatCell':{'range':{'sheetId':0,'startRowIndex':9,'endRowIndex':len(summary),'startColumnIndex':5,'endColumnIndex':6},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.00%'}}},'fields':'userEnteredFormat.numberFormat'}},
            {'repeatCell':{'range':{'sheetId':0,'startRowIndex':9,'endRowIndex':len(summary),'startColumnIndex':6,'endColumnIndex':9},'cell':{'userEnteredFormat':{'numberFormat':{'type':'CURRENCY','pattern':'R$ #,##0.00'}}},'fields':'userEnteredFormat.numberFormat'}},
            {'repeatCell':{'range':{'sheetId':0,'startRowIndex':9,'endRowIndex':len(summary),'startColumnIndex':9,'endColumnIndex':10},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.00%'}}},'fields':'userEnteredFormat.numberFormat'}},
            {'repeatCell':{'range':{'sheetId':dsid,'startRowIndex':6,'endRowIndex':len(detail),'startColumnIndex':3,'endColumnIndex':6},'cell':{'userEnteredFormat':{'numberFormat':{'type':'CURRENCY','pattern':'R$ #,##0.00'}}},'fields':'userEnteredFormat.numberFormat'}},
            {'repeatCell':{'range':{'sheetId':dsid,'startRowIndex':6,'endRowIndex':len(detail),'startColumnIndex':6,'endColumnIndex':7},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.00%'}}},'fields':'userEnteredFormat.numberFormat'}},
            {'repeatCell':{'range':{'sheetId':dsid,'startRowIndex':6,'endRowIndex':len(detail),'startColumnIndex':7,'endColumnIndex':10},'cell':{'userEnteredFormat':{'numberFormat':{'type':'CURRENCY','pattern':'R$ #,##0.00'}}},'fields':'userEnteredFormat.numberFormat'}},
            {'repeatCell':{'range':{'sheetId':dsid,'startRowIndex':6,'endRowIndex':len(detail),'startColumnIndex':10,'endColumnIndex':11},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.00%'}}},'fields':'userEnteredFormat.numberFormat'}},
        ])
        # Green/red conditional formatting on differences.
        for sid,start,end,cols in ((0,9,len(summary),(4,8)),(dsid,6,len(detail),(5,9))):
            for col in cols:
                requests.extend([
                    {'addConditionalFormatRule':{'rule':{'ranges':[{'sheetId':sid,'startRowIndex':start,'endRowIndex':end,'startColumnIndex':col,'endColumnIndex':col+1}],'booleanRule':{'condition':{'type':'NUMBER_GREATER','values':[{'userEnteredValue':'0'}]},'format':{'textFormat':{'foregroundColor':{'red':0.05,'green':0.45,'blue':0.15},'bold':True}}}},'index':0}},
                    {'addConditionalFormatRule':{'rule':{'ranges':[{'sheetId':sid,'startRowIndex':start,'endRowIndex':end,'startColumnIndex':col,'endColumnIndex':col+1}],'booleanRule':{'condition':{'type':'NUMBER_LESS','values':[{'userEnteredValue':'0'}]},'format':{'textFormat':{'foregroundColor':{'red':0.75,'green':0.08,'blue':0.08},'bold':True}}}},'index':0}},
                ])
        # Highlight each hourly TOTAL row.
        for idx,row in enumerate(detail):
            if idx>=6 and len(row)>1 and row[1]=='TOTAL':
                requests.append({'repeatCell':{'range':{'sheetId':dsid,'startRowIndex':idx,'endRowIndex':idx+1,'startColumnIndex':0,'endColumnIndex':11},'cell':{'userEnteredFormat':{'backgroundColor':{'red':0.90,'green':0.94,'blue':0.98},'textFormat':{'bold':True}}},'fields':'userEnteredFormat'}})
        api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':requests})

        rb_summary=values(SUMMARY,f'A1:J{len(summary)}'); rb_detail=values(DETAIL,f'A1:K{len(detail)}')
        if canon(rb_summary)!=canon(summary): raise RuntimeError('summary full-range readback mismatch')
        if canon(rb_detail)!=canon(detail): raise RuntimeError('detail full-range readback mismatch')
        final_meta=meta(); final_props={s['properties']['title']:s['properties'] for s in final_meta.get('sheets') or []}
        if set(final_props)!={SUMMARY,DETAIL} or final_props[SUMMARY]['sheetId']!=0: raise RuntimeError('final tab structure mismatch')
        result={'status':'ok','sheet_id':SHEET_ID,'sheet_title':(final_meta.get('properties') or {}).get('title'),'tabs':{SUMMARY:len(summary)-9,DETAIL:len(detail)-6},'cutoff_hour_et':cutoff,'hour_partial':True,'publishers_selected':52,'companies_selected':['digital-trust','digital-trust-2'],'companies_with_rows':sorted(set(r['COMPANY'] for r in ct_rows+cy_rows)),'domain_keys':len(keys),'total_today_to_cutoff':money(t_th),'total_yesterday_to_cutoff':money(t_yh),'difference_to_cutoff':money(t_th-t_yh),'variation_to_cutoff':pct(t_th,t_yh),'current_hour_today':money(t_ih),'current_hour_yesterday':money(t_ioy),'current_hour_difference':money(t_ih-t_ioy),'current_hour_variation':pct(t_ih,t_ioy),'summary_sha256':hashlib.sha256(json.dumps(canon(rb_summary),ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'detail_sha256':hashlib.sha256(json.dumps(canon(rb_detail),ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'canary_restored':True,'full_readback':True}
        (P/'sheet-write-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False))
    except Exception:
        try:
            current=meta(); by={s['properties']['title']:s['properties'] for s in current.get('sheets') or []}
            if SUMMARY in by: clear(SUMMARY,'A1:Z1000')
            if DETAIL in by:
                api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':[{'deleteSheet':{'sheetId':by[DETAIL]['sheetId']}}]})
            current=meta(); zero=next((s['properties'] for s in current.get('sheets') or [] if s['properties']['sheetId']==0),None)
            if zero and zero['title']!='Sheet1': api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':[{'updateSheetProperties':{'properties':{'sheetId':0,'title':'Sheet1','gridProperties':{'rowCount':1000,'columnCount':26,'frozenRowCount':0}},'fields':'title,gridProperties.rowCount,gridProperties.columnCount,gridProperties.frozenRowCount'}}]})
        finally: raise

if __name__=='__main__': main()
