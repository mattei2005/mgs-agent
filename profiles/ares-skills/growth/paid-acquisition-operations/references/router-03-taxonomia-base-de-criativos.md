## Taxonomia base de criativos

Para qualquer trabalho de nomenclatura, renomeação, inventário ou classificação de criativos, carregar também a skill dedicada `creative-taxonomy-mgs`. Ela é a fonte operacional detalhada para campos, P_ORIENT, status, inventário mínimo, Drive e metadata gate.

Modelo preferencial:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Regras:

- `STATUS` não entra no nome; fica na pasta ou inventário.
- IDs (`drive_id`, `meta_creative_id`, `campaign_id`) não entram no nome; ficam no inventário/metadados.
- `ANGLE` deve vir de dicionário controlado por operação/idioma.
- Se o ângulo for incerto, usar `UNKNOWN` e preencher `notes`.
- Não inventar classificação confiante sem evidência.
- Nome limpo, uppercase, sem acento, com underscore.

Pitfall: não deixar a taxonomia viva apenas como spec solto ou comentário de sessão. Quando Rodolfo pedir para “criar a skill”/“execute” sobre taxonomia já estabilizada, criar ou atualizar a skill classe `creative-taxonomy-mgs` e apontar esta umbrella para ela, em vez de criar uma skill estreita por sessão.

### P_ORIENT

```text
Código | Person    | Orientation
-------|-----------|------------
PV     | PERSON    | VERTICAL
PH     | PERSON    | HORIZONTAL
NV     | NO_PERSON | VERTICAL
NH     | NO_PERSON | HORIZONTAL
```

Regra atual de Rodolfo: usar somente `PV`, `PH`, `NV`, `NH`. Códigos `PS`, `NS`, `PU`, `NU`, `UU` foram desconsiderados e não devem entrar em nomes finais. Para detalhes, carregar `creative-taxonomy-mgs`.
