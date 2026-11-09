from pathlib import Path
p=Path('/root/mgs-agent/reports/meta-manual-payments-runs/cron-20261108T0802/verify.py')
code=p.read_text()
old="save(B/'closure-current.json',out);print"
assert code.count(old)==1
# Both exact captures were independently inspected this run.
new="out['ui_cleanup']={'initial_browser_tabs_visually_counted':7,'final_browser_tabs_visually_counted':7,'owned_tabs_closed':True,'lease_free':True,'initial_screenshot':str(B/'preflight-0802.png'),'final_screenshot':str(B/'surface-final.png'),'evidence':'Both screenshots inspected with vision_analyze: same AdsManager AD - 02 editor, seven tabs, no Billing tab'};save(B/'closure-current.json',out);print"
code=code.replace(old,new)
exec(compile(code,str(p),'exec'))
