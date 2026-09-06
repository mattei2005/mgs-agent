#!/usr/bin/env python3
"""Silent quote schedule with bounded retries, incident dedupe and recovery."""
import sys,pathlib,json,subprocess,time,datetime
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system')
def alert_for(current,previous):
 count=current.get('consecutive_failures',0)
 if not current.get('ok'):
  if count not in (1,3,5) or previous.get('reported')==count:return None,previous
  prefix='<@344196393512075265> ' if count>=3 else ''
  text=prefix+'Câmbio financeiro: atualização automática falhou. Último valor preservado; taxas fixadas não foram alteradas. Código: '+current.get('error','runner_failed')+'. Falhas consecutivas: '+str(count)+('. Tentativas suspensas; requer intervenção Zeus.' if count>=5 else '. Zeus deve investigar apps/finance-system/sync-quotes.py.' if count>=3 else '.')
  return text,{'reported':count,'open':True}
 return ('Câmbio financeiro: sincronização recuperada e validada. Taxas fixadas preservadas.' if previous.get('open') else None),{'reported':0,'open':False}
def main():
 state=ROOT/'private/quote-sync-state.json';delivery=ROOT/'private/quote-sync-alert-state.json'
 prior=json.loads(state.read_text()) if state.exists() else {};alert=json.loads(delivery.read_text()) if delivery.exists() else {}
 if prior.get('consecutive_failures',0)>=5:return
 if '--now' not in sys.argv:time.sleep(25)
 try:
  p=subprocess.run(['python3',str(ROOT/'sync-quotes.py'),'--publish','--quiet'],capture_output=True,text=True,timeout=240)
  current=json.loads(state.read_text()) if state.exists() else {}
  if current.get('updated_at')==prior.get('updated_at') and not p.returncode:return
  if p.returncode and current.get('ok'):raise RuntimeError('runner_failed')
 except Exception as e:
  current={'ok':False,'consecutive_failures':prior.get('consecutive_failures',0)+1,'error':'runner_timeout' if isinstance(e,subprocess.TimeoutExpired) else 'runner_failed','updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()};state.write_text(json.dumps(current))
 text,new=alert_for(current,alert)
 if text:print(text)
 delivery.write_text(json.dumps(new))
if __name__=='__main__':main()
