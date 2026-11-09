import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

BASE=Path('/root/mgs-agent')
LOCK=BASE/'scripts/mgs-pc1-computer-use-lock.py'


class PC1IngressTests(unittest.TestCase):
    def test_busy_is_durable_without_stealing_desktop(self):
        import sys
        sys.path.insert(0,str(BASE/'scripts'))
        from mgs_automation_continuity import Queue
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            env=dict(os.environ,MGS_PC1_CUA_LOCK_ROOT=str(root/'locks'),MGS_CONTINUITY_DB=str(root/'queue.sqlite3'))
            def run(agent,sid):
                return subprocess.run([sys.executable,str(LOCK),'acquire','--agent',agent,'--session-id',sid,'--thread-id','999000111'],capture_output=True,text=True,env=env,timeout=15)
            a=run('zeus','fixture-owner');self.assertEqual(a.returncode,0,a.stderr)
            b=run('ares','fixture-waiter');self.assertEqual(b.returncode,2,b.stderr)
            result=json.loads(b.stdout)
            self.assertTrue(result.get('continuity_queued'), 'Busy currently drops the scheduled request instead of queueing it')
            q=Queue(root/'queue.sqlite3');rows=q.open();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['state'],'waiting_resource')
            self.assertEqual(json.loads((root/'locks/pc1-computer-use.json').read_text())['session_id'],'fixture-owner')
            q.close()


if __name__=='__main__':unittest.main()
