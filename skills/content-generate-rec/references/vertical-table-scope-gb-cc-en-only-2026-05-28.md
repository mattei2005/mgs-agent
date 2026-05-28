# Vertical-specific table scope — gb-cc-en only — 2026-05-28

## Trigger

Use this reference when applying, migrating, reviewing, or designing REC/P1 table requirements across vertical contracts.

## Rodolfo correction

Rodolfo clarified that the article comparison-table requirement discussed as “point 8” is **only for the `gb-cc-en` vertical**.

Do not generalize this table requirement to other verticals. A future vertical should only require an article table when its own active contract/template explicitly says so.

## Durable rule

- `gb-cc-en` REC may require a comparison/positioning table according to its active contract and runtime gates.
- Other verticals must not inherit that requirement by default.
- Final reports should include table status only when the active vertical contract requires a table.
- QA validators and runners should be parameterized by vertical/template contract, not by a global REC assumption.
- Historical references mentioning REC comparison tables are incident evidence for GB credit-card content unless promoted into another vertical contract.

## Pitfall

Do not let a successful GB credit-card benchmark become a global content rule. The library target is class-level skills plus vertical-specific contracts, not one flat list of rules applied everywhere.
