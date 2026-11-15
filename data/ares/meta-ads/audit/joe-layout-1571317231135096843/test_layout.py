import ast
import copy
import importlib.util
import json
import re
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

HERE=Path(__file__).parent
SCRIPTS=Path('/root/.hermes/profiles/ares/scripts')
STATE=Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-roi-updates')
PAIRS=[('1571247040074219553','shein-g004-mavroa-cpr-roi-20261114.py'),('1571247080448720938','shein-g004-cpr-roi-20261114.py')]

def loadmodule(name,path) -> Any:
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec is not None and spec.loader is not None
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mods={req:loadmodule('layout_test_'+req,SCRIPTS/name) for req,name in PAIRS}
        cls.table=loadmodule('table_layout_test',SCRIPTS/'joe_custom_report_table.py')

    def render(self,req,snap):
        mod=self.mods[req]
        if req==PAIRS[0][0]:
            return mod.text(snap,mod.load(STATE/req/'manifest.json'))
        return mod.text(snap)

    def parsed(self,parts):
        out=[]
        for p in parts:
            self.assertLessEqual(len(p),2000)
            self.assertEqual(p.count('```')%2,0)
            for table in re.findall(r'```text\n(.*?)\n```',p,re.S):
                lines=table.splitlines()
                self.assertEqual([v.strip() for v in lines[0].split(' | ')],['Camp','Status','CPR','Gasto','Res.','ROI'])
                positions=[i for i,c in enumerate(lines[0]) if c=='|']
                for line in lines[1:]:
                    self.assertEqual([i for i,c in enumerate(line) if c=='|'],positions)
                    out.append([v.strip() for v in line.split(' | ')])
        return out

    def test_all_real_saved_snapshots(self):
        stats=[]
        for req,_ in PAIRS:
            for path in sorted((STATE/req/'runs').glob('*/snapshot.json')):
                with self.subTest(snapshot=str(path)):
                    snap=json.loads(path.read_text());unchanged=copy.deepcopy(snap)
                    parts=self.render(req,snap);parsed=self.parsed(parts)
                    self.assertEqual(snap,unchanged)
                    self.assertEqual(len(parsed),len(snap['rows']))
                    bynum={r[0]:r for r in parsed}
                    self.assertEqual(len(bynum),len(parsed))
                    for row in snap['rows'].values():
                        cells=bynum['C'+row['number']]
                        fmt=lambda v:format(Decimal(str(v)),'.2f').replace('.',',') if v is not None else 'n/d'
                        self.assertEqual(cells[2],fmt(row['cpr']))
                        self.assertEqual(cells[3],fmt(row.get('meta_spend',row.get('spend'))))
                        expected_roi=format(Decimal(str(row['roi'])),'+.2f').replace('.',',')+'%' if row['roi'] is not None else 'n/d'
                        self.assertEqual(cells[5],expected_roi)
                    latest=HERE/(req+'-rendered.json')
                    latest.write_text(json.dumps(parts,ensure_ascii=False,indent=2))
                    stats.append({'snapshot':str(path),'rows':len(parsed),'parts':len(parts),'lengths':[len(p) for p in parts]})
        (HERE/'snapshots-validation.json').write_text(json.dumps(stats,indent=2))
        self.assertGreaterEqual(len(stats),23)

    def test_only_text_changed(self):
        for _,name in PAIRS:
            a=ast.parse((HERE/'before'/name).read_text());b=ast.parse((SCRIPTS/name).read_text())
            a.body=[x for x in a.body if not isinstance(x,ast.FunctionDef) or x.name!='text']
            b.body=[x for x in b.body if not isinstance(x,ast.FunctionDef) or x.name!='text']
            self.assertEqual(ast.dump(a),ast.dump(b))

    def test_large_pagination(self):
        rows=[('C'+str(i).zfill(3),'Ativa','0,61','123456,78','9999','+101,94%') for i in range(300)]
        parts=self.table.render(['**Conta · corte verificado · USD**'],[('Criadas hoje',rows)],['Fontes preservadas.'])
        out=self.parsed(parts)
        self.assertEqual(out,[list(x) for x in rows])
        self.assertGreater(len(parts),1)
        for p in parts:
            self.assertTrue(p.startswith('**Conta'))
            if '```text' in p:self.assertIn('Criadas hoje (300)',p)

    def test_missing_zero_pending_and_empty(self):
        req=PAIRS[0][0]
        snap=json.loads((STATE/req/'runs/1858/snapshot.json').read_text())
        first=next(iter(snap['rows'].values()))
        first.update(cpr=None,roi=None,meta_spend=None,results=None,pending='evento não confirmado')
        out=self.parsed(self.render(req,snap));row=next(r for r in out if r[0]=='C'+first['number'])
        self.assertEqual(row[2:],['n/d','n/d','n/d','n/d'])
        first.update(roi='0',meta_spend='0',pending=None)
        row=next(r for r in self.parsed(self.render(req,snap)) if r[0]=='C'+first['number'])
        self.assertEqual(row[2:],['n/d','0,00','0','+0,00%'])
        snap['rows']={};snap['campaigns']=[]
        self.assertEqual(self.parsed(self.render(req,snap)),[])

    def test_execute_replay_and_expiry_without_api(self):
        import argparse
        for req,_ in PAIRS:
            mod=self.mods[req];oldroot=mod.ROOT;oldscope=mod.scope
            root=HERE/('fixture-'+req);root.mkdir(exist_ok=True)
            manifest=mod.load(STATE/req/'manifest.json')
            (root/'manifest.json').write_text(json.dumps(manifest))
            mod.ROOT=root
            def forbidden(*args,**kwargs):raise AssertionError('No API in replay/expiry')
            mod.scope=forbidden
            try:
                a=argparse.Namespace(initial=False,dry_run=False)
                at=datetime.fromisoformat(manifest['slots'][0])
                key=mod.slot(manifest,at);run=root/'runs'/key;run.mkdir(parents=True,exist_ok=True)
                receipt={'status':'COMPLETE_GET_VERIFIED','sentinel':True}
                (run/'complete.json').write_text(json.dumps(receipt))
                self.assertEqual(mod.execute(a,at),receipt)
                self.assertEqual(mod.execute(a,datetime.fromisoformat(manifest['expires_at']))['status'],'EXPIRED')
            finally:mod.ROOT=oldroot;mod.scope=oldscope

    def test_wrappers_and_scheduler_preserved(self):
        for name in ['shein-g004-mavroa-cpr-roi-20261114.sh','shein-g004-cpr-roi-20261114.sh']:
            self.assertEqual((HERE/'before'/name).read_bytes(),(SCRIPTS/name).read_bytes())
        before=json.loads((HERE/'before-jobs.json').read_text())
        data=json.loads(Path('/root/.hermes/profiles/ares/cron/jobs.json').read_text());jobs=data['jobs'] if isinstance(data,dict) else data
        for old in before:
            new=next(j for j in jobs if j['id']==old['id'])
            for field in ['script','prompt','schedule','enabled','state','deliver','no_agent','failure_deliver','timezone','origin']:
                self.assertEqual(old.get(field),new.get(field))

if __name__=='__main__':
    unittest.main(verbosity=2)
