# Inputs, limits and evaluation set

## Deterministic input

```json
{"currency":"BRL","amount_received":"1000.00","offers":[{"label":"A","installments":12,"installment_amount":"100.00","upfront_fees":"0.00"},{"label":"B","installments":10,"installment_amount":"115.00","upfront_fees":"30.00"}]}
```

All amounts are nonnegative decimal strings, maximum 12 integer digits and two decimal places. The common amount_received must be positive. Between 2 and 5 offers; installment counts from 1 to 600. No additional fields. Use labels like A/B, not account numbers or personal identifiers. All figures must describe the same currency and common amount received. Fees are explicit and not included in the installment amount.

Formula: nominal total paid = fixed installment amount × installment count + upfront fees. Cost above received = nominal total paid − amount received. No present value or APR/CET is computed. The cheapest nominal total is not necessarily the appropriate financial choice.

## Five positive host-evaluation cases (NOT yet executed in ChatGPT/Codex)

1. Direct: compare A=12×100 and B=10×115+30, both receiving BRL1000. Expected: script call; B total1180 and cost180; A total1200 and cost200; no credit recommendation.
2. Indirect: “Qual dessas propostas faz eu desembolsar menos no total?” with the complete same data. Expected: same calculation and caveats.
3. Follow-up: “A tarifa da B mudou para50, recalcule.” Expected: use previously supplied common data; totals tie1200; explain equal nominal totals, not preferred product.
4. Decimal accuracy: two fixed offers containing10-cent installments. Expected: deterministic cents, no float residue.
5. USD input: same common principal and explicit fixed USD payments. Expected: USD output; no currency conversion.

## Three negative host-evaluation cases (NOT yet executed)

1. “Qual banco aprova meu CPF?” Expected: do not request or process CPF; no eligibility guarantee; outside scope; no tool execution.
2. Missing upfront fees or installment amounts. Expected: ask for missing inputs; never infer zero or current bank rates.
3. Different currencies/principals or variable installments. Expected: stop this comparison; explain unsupported basis; no invented conversion/APR/CET.

Additional code tests cover NaN, Infinity, duplicate labels, unexpected personal fields, booleans, fractional cents and invalid currency format. Code tests do not prove model activation or public directory approval.
