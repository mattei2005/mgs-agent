"""Read-only same-scope UI extension: follow the visible transaction-history link."""
from pathlib import Path
source=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/read_pc1_history_uia.py')
code=source.read_text()
assert code.count("assert len(ss)==1,'direct_url_suggestion_not_unique';")==1
code=code.replace("assert len(ss)==1,'direct_url_suggestion_not_unique';", "(B/(a.account_id+'-address-state.json')).write_text(json.dumps(full,ensure_ascii=False));")
anchor=" tp=B/(a.account_id+'.txt');"
assert code.count(anchor)==1
extension=""" if 'View transaction history' in text:
  links=[e for e in es if e.get('label')=='View transaction history' and e.get('role')=='Hyperlink'];assert len(links)==1,'history_link_not_unique'
  action({'action':'click','element':links[0]['index'],'delivery_mode':'foreground','bring_to_front':True});time.sleep(6)
  full,es,text=cap()
"""
code=code.replace(anchor,extension+anchor)
exec(compile(code,str(source),'exec'),globals())
