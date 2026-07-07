# DTR #2022 date extraction in page language — 2026-07-06

## Rodolfo correction

DigitalTRChat/Facebook `#2022` responses can appear in the language of the page/profile, not only English or Portuguese. Do not treat an unfamiliar language as missing data.

## Rule

When the latest DTR `Completed` report contains `#2022` but the current parser does not extract `RESTRICTED_UNTIL`:

1. Read the raw response text.
2. Identify/translate the phrase that means "restricted until DATE/TIME".
3. Extract the expiry date/time from that language.
4. Only then update Smart Bidding `RESTRICTED_UNTIL`.
5. If no expiry date exists after checking all available sent-message/report rows, report the page as unresolved; do not invent a date unless Rodolfo explicitly gives one.

Known parsed formats now include:

- EN: `until July 31 at 3:24 AM`
- PT: `até 15 de julho às 23:08`
- ES: `hasta el 21 de julio a las 11:10 p. m.`

## Manual fallback

If parser support is missing for a language, manually inspect the raw DTR response before giving up. Add the new language pattern to `/root/mgs-agent/scripts/dtr-sb-page-health-sync.py::parse_restricted_date()` and validate with `py_compile` + sample parse test.

## Capri Branson precedent

For Capri Branson, no expiry date was found after opening the available reports. Rodolfo manually set the date to `2026-08-07`; that was a user override, not parser inference.