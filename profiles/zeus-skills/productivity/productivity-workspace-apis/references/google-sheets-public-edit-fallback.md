# Google Sheets public-edit fallback

Use this when Rodolfo provides a Google Sheet link that is publicly readable/editable, but Hermes Google Workspace OAuth/Sheets API is unavailable in the current profile.

## Pattern

1. **Read source data without OAuth when possible**
   - For a public Sheet/tab, export CSV directly:
     - `https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}`
   - Parse by header names, not visible column letters alone.
   - Preserve original row numbers when creating an analysis tab so Rodolfo can trace rows back.

2. **Create the destination tab**
   - Prefer Sheets API when authenticated.
   - If not authenticated and the browser has edit access, use the Sheets UI: click `Add Sheet`, then rename/populate via the UI/browser fallback.

3. **Populate readable analysis output**
   - Include a short metadata block at top: source tab, criteria, summary counts.
   - Then include a detailed table with traceable columns, e.g. original row, publisher/id, campaign/key, metric, status, derived flag.
   - For status audits, add an explicit boolean/flag column (`ON_HOLD_FLAG`, `MATCH_FLAG`) instead of forcing the operator to infer from text.

4. **Browser write fallback**
   - First try normal clipboard/HTML/TSV paste into A1.
   - For medium/large tables where clipboard access is blocked but the Sheets UI is editable, use a headed/headless Playwright UI paste that dispatches a synthetic `ClipboardEvent` to the Sheets offscreen textarea:

```js
const dt = new DataTransfer();
dt.setData('text/plain', tsv);
const ev = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true });
document.querySelector('textarea.trix-offscreen').dispatchEvent(ev);
```

   - Navigate to each target `gid`, select `A1` via the Name box (`Ctrl+J`, type `A1`, Enter), dispatch the TSV paste, wait for save, then verify by CSV export.
   - If UI paste is not enough and the page is publicly editable, a last-resort browser-console write can use the same internal `/save` request pattern emitted by Google Sheets:
     - capture or infer `sid` from page resource URLs;
     - send `FormData` to `/spreadsheets/d/{id}/save?...` with header `X-Same-Domain: 1`;
     - command payload can update individual cells with the current sheet `gid`.
   - This internal protocol is undocumented and brittle. Use it only for small/medium operational tables and always verify by export/readback.

5. **Verify by readback**
   - Export the new tab as CSV by gid and count rows/flags from the actual remote sheet.
   - Force UTF-8 decode before parsing (`r.content.decode('utf-8')`) when using Python `requests`; Google CSV exports can be UTF-8 while `requests` guesses ISO-8859-1, which corrupts accents like `botões` and can break exact alert-count checks.
   - Report only after readback confirms the expected row count and key totals.

## Pitfalls

- Do not claim the tab was created/populated from the browser UI alone; verify the destination gid via CSV export.
- Do not leave scratch/test cells from probing. Clear them before final readback.
- Do not encode a permanent claim that Google Sheets API is unavailable; treat it as current-profile setup state and use this only as a fallback.
