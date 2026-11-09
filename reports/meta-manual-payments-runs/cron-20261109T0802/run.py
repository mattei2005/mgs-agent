import pathlib
p=pathlib.Path('/root/mgs-agent/reports/meta-manual-payments-runs/cron-20261108T2102/run.py')
code=p.read_text().replace("'2026-11-08T21:02:00-05:00'", "'2026-11-09T08:02:00-05:00'")
exec(compile(code,str(p),'exec'))
