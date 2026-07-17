# Google Sheets browser-paste fallback

Use this when a Google Sheet is editable in the browser but API writes are blocked, e.g. service-account project has Sheets API disabled or lacks permission to enable it.

## Pattern

1. Build the intended sheet content as TSV, not CSV.
   - TSV pastes into Google Sheets as columns/rows.
   - Preserve accents/Unicode with UTF-8.
2. Open the target spreadsheet/worksheet in browser.
3. Select the target tab.
4. Navigate to `A1` or the intended starting cell.
5. Clear the existing target area if replacing the sheet.
6. Write TSV to clipboard with browser context if available:
   - `navigator.clipboard.writeText(tsv)`
7. Paste with `Ctrl+V`.
8. Wait for save/render.
9. Verify visually or by export/read-back:
   - confirm data is distributed over multiple rows/columns, not one cell;
   - confirm headers and row count roughly match expected output;
   - if public/readable, use CSV export/read-back as secondary validation.

## Playwright notes

For Sheets UI automation under Xvfb/headed Chromium, browser clipboard paste can work more reliably than trying to type large data into the formula bar.

Minimal flow:

```python
await page.goto(sheet_url)
await page.get_by_role('button', name=re.compile('Target tab', re.I)).click()
await page.mouse.click(x, y)  # grid A1 area, or navigate via name box
await page.keyboard.press('Control+A')
await page.keyboard.press('Control+A')
await page.keyboard.press('Backspace')
await page.evaluate('(text)=>navigator.clipboard.writeText(text)', tsv)
await page.keyboard.press('Control+V')
```

## Pitfalls

- Google Sheets API disabled in the service-account project is not proof the sheet cannot be edited; use browser fallback when UI access exists.
- Do not paste CSV when commas/BR currency/locale values are present; use TSV.
- After paste, verify distribution over rows/columns; if the first row looks concatenated, the paste target or delimiter handling failed.
- Do not expose credentials used to access the sheet; report only item name/account and verification status.
