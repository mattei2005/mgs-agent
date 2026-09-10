import sys,json,urllib.parse,shlex,pathlib
from decimal import Decimal as D
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();DOUT=pathlib.Path('/root/mgs-agent/work/finance-payments-indicators-1547706561210753114');sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy');from runcloud_ops import ssh
# Active frozen history cells for one changed site settlement block.
env='env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';pg='sudo -n -u mgs_pg '+env+'/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -At '
q="""WITH current AS (SELECT result->'versions'->>'2026-07/principal' vid FROM scenarios WHERE id='master-history-source'), doc AS (SELECT result->'history_payload' p FROM scenarios,current WHERE id=current.vid) SELECT jsonb_agg(x ORDER BY (x->>'row')::int,(x->>'col')::int) FROM doc,jsonb_array_elements(p->'cells') x WHERE (x->>'row')::int BETWEEN 80 AND 98 AND (x->>'col')::int BETWEEN 55 AND 61;""";hist_cells=json.loads(ssh(pg+'-c '+shlex.quote(q),timeout=120).strip());hist={c['a1']:c for c in hist_cells}
sa=load_service_account();token=service_account_access_token(['https://www.googleapis.com/auth/spreadsheets.readonly']);sid='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak';rng="'Julho 2026'!BC80:BI98"
def get(render):
 u='https://sheets.googleapis.com/v4/spreadsheets/'+sid+'/values/'+urllib.parse.quote(rng,safe='')+'?'+urllib.parse.urlencode({'majorDimension':'ROWS','valueRenderOption':render,'dateTimeRenderOption':'SERIAL_NUMBER'});s,d=api_json('GET',u,token,quota_project='mgs-core-prod');assert s==200;return d.get('values',[])
raw=get('UNFORMATTED_VALUE');formula=get('FORMULA');formatted=get('FORMATTED_VALUE')
def col(n):
 s=''
 while n:n,k=divmod(n-1,26);s=chr(65+k)+s
 return s
live={}
for ri in range(19):
 for ci in range(7):
  a=col(55+ci)+str(80+ri);live[a]={'raw':raw[ri][ci] if ri<len(raw) and ci<len(raw[ri]) else None,'formula':formula[ri][ci] if ri<len(formula) and ci<len(formula[ri]) else None,'formatted':formatted[ri][ci] if ri<len(formatted) and ci<len(formatted[ri]) else None}
changes=[]
for a,h in hist.items():
 hv=h.get('value');lv=live.get(a,{}).get('raw');
 if isinstance(hv,(int,float)) and isinstance(lv,(int,float)) and abs(D(str(lv))-D(str(hv)))>D('0.000000001'):changes.append({'cell':a,'before':str(hv),'after':str(lv),'delta':str(D(str(lv))-D(str(hv))),'label':next((live.get(col(c)+str(h['row']),{}).get('formatted') for c in range(55,62) if isinstance(live.get(col(c)+str(h['row']),{}).get('formatted'),str) and live.get(col(c)+str(h['row']),{}).get('formatted').strip()),None),'formula':live.get(a,{}).get('formula')})
out={'pass':True,'range':rng,'historical_cells':len(hist_cells),'changed_numeric':changes,'sheet_writes':0};(DOUT/'july-component-root.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
