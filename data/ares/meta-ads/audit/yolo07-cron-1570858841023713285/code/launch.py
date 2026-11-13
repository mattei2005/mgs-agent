import pathlib,json,subprocess,sys
name=sys.argv[1];assert name in ('smoke','probe')
path=str(pathlib.Path(__file__).with_name(name+'.py'));args=[path,*sys.argv[2:]]
argv=json.loads(subprocess.check_output(['/root/.local/bin/hermes','--print-runtime-command'],text=True));old="runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)";assert argv[-1].count(old)==1;argv[-1]=argv[-1].replace(old,f"sys.argv={args!r};runpy.run_path(sys.argv[0],run_name='__main__')",1);raise SystemExit(subprocess.call(argv))
