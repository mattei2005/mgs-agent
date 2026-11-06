from pathlib import Path
import subprocess,json,sys
b=Path(__file__).parent;ph=json.loads((b/'phases.json').read_text());r=Path(ph['publish_pay_now']['run_dir'])
h=Path(subprocess.check_output(['which','hermes'],text=True).strip());py=h.read_text().splitlines()[1].split(' -I ',1)[0].removeprefix('exec ')
i=int(sys.argv[1]);ids=json.loads((b/'batches.json').read_text())[i]
x=subprocess.run([py,str(b/'read-accounts-recovery.py'),'--run-dir',str(r),'--account-ids',*ids],capture_output=True,text=True,timeout=450);(b/('batch'+str(i)+'-output.txt')).write_text(x.stdout+'\n'+x.stderr);print(x.stdout);raise SystemExit(x.returncode)
