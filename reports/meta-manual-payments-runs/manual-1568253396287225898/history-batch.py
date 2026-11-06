from pathlib import Path
import json,sys,subprocess
B=Path(__file__).parent;ph=json.loads((B/'phases.json').read_text());pending=ph['refresh_workbook']['pending_ui'];h=Path(subprocess.check_output(['which','hermes'],text=True).strip());py=h.read_text().splitlines()[1].split(' -I ',1)[0].removeprefix('exec ')
f=B/'history-captures.json';captures=json.loads(f.read_text())if f.exists()else{}
for i in map(int,sys.argv[1:]):
 aid=pending[i]['account_id'];r=subprocess.run([py,str(B/'run.py'),'worker','read_pc1_billing_history.py','--pid','19372','--window-id','328816','--mode','read','--account-id',aid,'--history-scroll-ticks','5'],capture_output=True,text=True,timeout=180);(B/('history-'+aid+'.txt')).write_text(r.stdout+'\n'+r.stderr);print(r.stdout,flush=True)
 for line in r.stdout.splitlines():
  try:
   d=json.loads(line);rec=d['results'][-1];captures[aid]=rec;f.write_text(json.dumps(captures,ensure_ascii=False,indent=2))
  except (ValueError,KeyError,IndexError):pass
 if r.returncode:raise SystemExit(r.returncode)
