"""Read-only bridge: API daily vs exact July Sheet, screenshot deltas separate."""
import pathlib,json,sys,datetime,decimal
S=pathlib.Path(__file__).resolve().parents[1]/'private/navigation-1546682010066489394'
sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557');import audit
cells=audit.cells(json.loads((S/'july-sheet.json').read_text())['sheets'][0]);D=decimal.Decimal
v=lambda key:cells.get(key,{}).get('effectiveValue',{}).get('numberValue',0)
day=lambda row:(datetime.date(1899,12,30)+datetime.timedelta(days=v('B'+str(row)))).isoformat()
api=next(x for x in json.loads((S/'meta-july-canaries.json').read_text()) if x['account']['name']=='TopfeedFinanzas-US-CC-ES-01');rows={x['date_start']:D(x['spend']) for x in api['rows']};differences=[]
for r in range(46,77):
 date=day(r);sheet=D(str(v('CJ'+str(r)))).quantize(D('.01'));remote=rows.get(date,D(0))
 if sheet!=remote:differences.append({'date':date,'sheet':str(sheet),'api':str(remote)})
# Values independently transcribed by vision from Rodolfo attachments, not API output.
screens=[('Mattei 1','AGS',74,'1474.66','img_7dde0e75e2b2.png'),('Mattei 1','AGS',75,'850.54','img_7dde0e75e2b2.png'),('Mattei 1','AGS',76,'716.12','img_7dde0e75e2b2.png'),('Gamingadx-US-01','AGA',75,'25.21','img_3616735d5631.png'),('Gamingadx-US-01','AGA',76,'65.30','img_3616735d5631.png')]
out={'read_only':True,'topfeed_daily':{'account_id':api['account']['account_id'],'days':31,'differences':differences,'total_api':api['sum'],'total_sheet':str(D(str(v('CJ78'))).quantize(D('.01')))},'google_screenshot_deltas':[],'google_api_verified':False,'cause':'unattributed: not enough evidence to classify as refund'}
for name,col,row,amount,img in screens:
 sheet=D(str(v(col+str(row)))).quantize(D('.01'));screenshot=D(amount)
 out['google_screenshot_deltas'].append({'account':name,'date':day(row),'cell':col+str(row),'sheet_brl':str(sheet),'screenshot_brl':str(screenshot),'screenshot_minus_sheet_brl':str(screenshot-sheet),'image':img})
(S/'july-bridge.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,ensure_ascii=False))
