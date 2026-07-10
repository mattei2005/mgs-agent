## P_ORIENT

`P_ORIENT` combina presença de pessoa + orientação visual.

Regra oficial MGS definida por Rodolfo: usar **somente** `PV`, `PH`, `NV`, `NH`. Códigos de square ou orientação desconhecida ficam desconsiderados e não devem entrar em nome final.

```text
Código | Pessoa     | Orientação
-------|------------|------------
PV     | PERSON     | VERTICAL
PH     | PERSON     | HORIZONTAL
NV     | NO_PERSON  | VERTICAL
NH     | NO_PERSON  | HORIZONTAL
```

Códigos removidos/desconsiderados:

```text
PS, NS, PU, NU, UU
```

Para operações Meta comuns, tratar o placement como vertical ou horizontal para fins de nome:

```text
Código | Pessoa     | Orientação | Uso típico
-------|------------|------------|-------------------------
PV     | PERSON     | VERTICAL   | Story/Reels vertical
NV     | NO_PERSON  | VERTICAL   | Story/Reels vertical
PH     | PERSON     | HORIZONTAL | Feed/landscape/não vertical
NH     | NO_PERSON  | HORIZONTAL | Feed/landscape/não vertical
```

Se pessoa ou orientação não puderem ser determinados com segurança, marcar revisão no inventário em vez de criar nome final incorreto. Não usar código `UNKNOWN` no nome final.
