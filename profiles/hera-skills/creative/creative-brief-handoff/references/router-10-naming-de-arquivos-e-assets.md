## Naming de arquivos e assets

Use nomes previsíveis, sem acento e sem espaço.

O Drive tem várias verticais/operações. Identifique a operação correta e aplique a taxonomia correspondente.

Modelo geral:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplo/piloto `CC_US_ES`, já alinhado com o Ares:

```text
CC_US_ES_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplos:

```text
CC_US_ES_IMG_APROBACION_PS_01.jpg
CC_US_ES_IMG_APROBACION_NS_02.jpg
CC_US_ES_IMG_SIN_VERIFICACION_PV_01.jpg
CC_US_ES_VID_CASHBACK_NV_01.mp4
```

Campos:

```text
Campo       Regra
──────────  ─────────────────────────────────────────────────────────────
FORMAT      IMG ou VID.
ANGLE       Dicionário controlado por operação; usar UNKNOWN se incerto.
P_ORIENT    Para CC_US_ES, apenas PV, NV, PS ou NS.
VARIANT     Sequencial 01, 02, 03...
ext         Extensão real do arquivo.
```

Dicionário inicial de `ANGLE` para `CC_US_ES` — exemplo/piloto; outras verticais podem ter dicionário próprio conforme o uso real:

```text
APROBACION
SIN_VERIFICACION
LIMITE_ALTO
SIN_CREDITO
MAL_CREDITO
CASHBACK
RECOMPENSAS
COMPARACION
WALLET
URGENCIA
UNKNOWN
```

`UNKNOWN` é permitido para `ANGLE`, mas exige observação no inventário. Não use UNKNOWN para `P_ORIENT`; se pessoa/orientação estiver incerta, marque o asset para revisão.

Para outras operações ainda não padronizadas, use um naming provisório e declare que precisa validação de Rodolfo/Kelly antes de virar padrão.
