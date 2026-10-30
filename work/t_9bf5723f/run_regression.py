"""No external network; stage or installed modules with origin proof."""
import json,socket,sys,os
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_9bf5723f';installed='--installed' in sys.argv
root=B if installed else W/'stage'
sys.path[:0]=[str(root/'scripts'),str(B/'scripts'),str(root/'tests'),str(B)]
import ares_campaign_v3
import pytest
patterns=['test_shein*.py','test_ares_campaign_engine_v3.py','test_ares_shein_campaigns_v3.py','test_eggbev_clone_v3.py','test_eggbev_from_zero_v3.py','test_ares_campaign_v3_daily_cpv.py','test_prestage*.py','test_prestaged*.py','test_ares_asset_scope*.py']
paths=sorted({str(p) for pattern in patterns for p in (B/'tests').glob(pattern)})
if not installed:
    paths=[str(root/'tests'/Path(p).name) if Path(p).name in {'test_shein_image_media.py','test_shein_single_clone_route.py'} else p for p in paths]
    paths.append(str(root/'tests/test_shein_image_sourcing.py'))
if '--focused' in sys.argv:paths=[str(root/'tests/test_shein_image_sourcing.py'),str(root/'tests/test_shein_image_media.py')]
class Receipt:
    def __init__(self):self.rows=[];self.subtests=0
    def pytest_runtest_logreport(self,report):
        if getattr(report,'context',None) is not None:
            if report.passed:self.subtests+=1
        elif report.when=='call' or (report.when in {'setup','teardown'} and report.failed):self.rows.append({'id':report.nodeid,'outcome':report.outcome})
r=Receipt();connect=socket.socket.connect;blocked=[]
def restricted(self,address):
    if isinstance(address,tuple) and address[0] not in {'127.0.0.1','localhost','::1'}:
        blocked.append(str(address[0]));raise AssertionError('external network forbidden in regression')
    return connect(self,address)
socket.socket.connect=restricted
code=pytest.main(['-q','--import-mode=importlib','--tb=short','-p','no:cacheprovider',*paths],plugins=[r])
rows={x['id']:x for x in r.rows}
wrong={n:str(m.__file__) for n,m in sys.modules.items() if n.startswith('ares_campaign_v3.') and getattr(m,'__file__',None) and not Path(m.__file__).is_relative_to(root/'scripts')}
summary={'exit_code':int(code),'passed':sum(x['outcome']=='passed' for x in rows.values()),'failed':[x for x in rows.values() if x['outcome']=='failed'],'subtests_passed':r.subtests,'files':len(paths),'exclusions':[], 'module_origin_mismatch':wrong,'external_network_attempts_blocked':len(blocked),'profile':os.environ.get('HERMES_PROFILE'),'installed':installed}
name='regression-installed' if installed else 'regression-stage'
if '--focused' in sys.argv:name+='-focused'
(W/(name+'.json')).write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));sys.exit(int(code) or bool(wrong) or bool(blocked))
