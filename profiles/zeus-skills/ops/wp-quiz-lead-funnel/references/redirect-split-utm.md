# Redirect Split + UTM Preservation

## Goal

After a successful lead submit, redirect the user to the final REC/sales page while preserving all acquisition parameters.

## Required Behavior

- Do not redirect before server returns `ok:true`.
- Preserve every incoming URL param unless the destination URL already has that param.
- Preserve at minimum: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `fbclid`, `gclid`.
- Support weighted split between multiple redirect URLs.

## Operator UI

Use business-facing rows, not raw JSON:

- Section title: `URLs de redirecionamento (split de tráfego)`
- Button: `+ Adicionar URL`
- Row fields: URL + weight
- Remove action for extra rows
- Helper text: show computed distribution

Examples:

- One row: URL + `100` → 100% to that URL.
- Two rows: URL A `50`, URL B `50` → even split.
- Three rows: 70/20/10 → weighted split.

## Validation

- Submit a test lead with visible query params.
- Confirm final redirect URL includes original params.
- Confirm no redirect happens on simulated SMS failure when require-success is enabled.
