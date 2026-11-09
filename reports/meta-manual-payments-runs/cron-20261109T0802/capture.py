from pathlib import Path
p=Path('/root/mgs-agent/reports/meta-manual-payments-runs/cron-20261108T2102/capture.py')
exec(compile(p.read_text(),str(p),'exec'))
