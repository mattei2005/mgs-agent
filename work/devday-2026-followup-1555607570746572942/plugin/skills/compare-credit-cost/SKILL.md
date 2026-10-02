---
name: compare-credit-cost
description: Compare nominal total payments for two to five fixed-installment credit offers that provide the same amount received, using only prices and fees supplied by the user. No credit recommendations or eligibility assessment.
---

# MGS Custo Claro — comparação educativa

Use only for a user's explicit request to compare the nominal cost of concrete fixed-installment offers. This experimental skills-only plugin runs offline and has no backend, login, telemetry, affiliation, advertising or internal-system access.

1. Gather the common amount received and currency, and for each offer a short non-personal label, number of installments, fixed installment amount and upfront fees not already included in the installments. Ask if any value is missing. Never infer a zero fee. Confirm the same amount received and currency for every offer and that all payments are fixed; otherwise stop and explain why the offers cannot be compared with this tool.
2. Use decimal strings with a dot and at most two decimal places. Interpret local punctuation only when unambiguous; ask when ambiguous. Do not request CPF/SSN, bank credentials, account numbers, phone, address, income, credit score or other identifiers. Do not pass any such data to the script or include it in offer labels.
3. Run `python3 scripts/compare_cost.py` from this skill directory. Supply a JSON object through stdin with exactly `currency`, `amount_received` and `offers`. Each offer has exactly `label`, `installments`, `installment_amount`, `upfront_fees`. See `references/inputs-and-boundaries.md` for the schema and evaluation prompts.
4. Use the real script output. If execution fails or is unavailable, explicitly state that the calculation was not validated; do not fabricate results or substitute model arithmetic.
5. Explain nominal total paid, cost above the amount received and number/value of installments. Ordering reflects nominal total only; it is NOT a recommendation to contract the lowest-total offer. Highlight that a smaller monthly installment may still produce a larger nominal total.
6. Clearly state: educational calculation, not financial advice, APR/CET or approval. Differences in deadlines, insurance, variable rates, late fees and present value are outside this comparison. Do not invent current bank rates, offer links, eligibility, guarantees or individualized recommendations. Do not calculate legally defined APR/CET from these incomplete inputs.
7. Do not create leads, submit applications, open accounts, buy products, collect identifiers, publish data or contact any external service. If asked, explain that these actions are outside this plugin.

This prototype has been tested locally at the script level only until a separately documented host-level evaluation is performed. Never call it installed, published, policy-approved or commercially validated solely because its files or unit tests exist.
