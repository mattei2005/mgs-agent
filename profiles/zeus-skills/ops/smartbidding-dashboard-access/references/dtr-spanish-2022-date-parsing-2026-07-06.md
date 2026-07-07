# DTR Spanish #2022 date parsing — 2026-07-06

## Context

While applying rows from Rodolfo's Google Sheet with `#2022` in column F, several DigitalTRChat reports were in Spanish:

```text
(#2022) Se restringió temporalmente tu permiso para enviar mensajes a usuarios hasta el 21 de julio a las 11:10 p. m.
```

The production parser previously handled English (`until July 31 at 3:24 AM`) and Portuguese (`até 15 de julho às 23:08`) but not Spanish. That prevented `RESTRICTED_UNTIL` writes even when the DTR report clearly had the expiry date.

## Rule

`/root/mgs-agent/scripts/dtr-sb-page-health-sync.py::parse_restricted_date()` must parse all three DTR language shapes currently seen:

- EN: `until July 31 at 3:24 AM`
- PT: `até 15 de julho às 23:08`
- ES: `hasta el 21 de julio a las 11:10 p. m.`

Normalize to:

```text
restricted_until      YYYY-MM-DD
restricted_until_time YYYY-MM-DD HH:MM
```

## Validation command

```bash
cd /root/mgs-agent
python3 -m py_compile scripts/dtr-sb-page-health-sync.py
/tmp/sb-venv/bin/python - <<'PY'
import importlib.util
p='scripts/dtr-sb-page-health-sync.py'
spec=importlib.util.spec_from_file_location('sync', p)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.parse_restricted_date('Se restringió temporalmente tu permiso para enviar mensajes a usuarios hasta el 21 de julio a las 11:10 p. m.'))
PY
```

Expected: `('2026-07-21', '2026-07-21 23:10')`.