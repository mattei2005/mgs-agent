"""Reproduce existing empty-file race without launching a browser or using API."""
import hashlib,json,sys
from pathlib import Path
from unittest.mock import Mock,patch
B=Path('/root/mgs-agent');W=B/'work/t_8426333c';sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3 import preview_renderer as r
proc=Mock(pid=987654321)
def launch(args, **kwargs):
    directory=Path(next(a.split('=',1)[1] for a in args if a.startswith('--user-data-dir=')))
    (directory/'DevToolsActivePort').write_text('')
    return proc
with patch.object(r.subprocess,'Popen',side_effect=launch),patch.object(r.os,'killpg'),patch.object(r.time,'sleep'):
    try:r.render_previews([],chrome_path='/root/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',timeout=1)
    except ValueError as e:
        assert isinstance(e.__cause__,IndexError),type(e.__cause__).__name__
        result={'reproduced':True,'installed_original_sha256':hashlib.sha256(Path(r.__file__).read_bytes()).hexdigest(),'cause':'IndexError','file_state':'existing empty DevToolsActivePort','api_calls':0,'browser_launches':0,'credentials_accessed':False,'campaign_related':False}
    else:raise AssertionError('Expected original empty-file failure')
(W/'original-race-reproduced.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
