# Origem da taxonomia Empire/MGS

Resumo do arquivo enviado por Rodolfo (`taxonomia_criativos_empire_1.txt`) e decisões consolidadas na skill `creative-taxonomy-mgs`.

## Modelo recebido

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplos recebidos:

```text
CC_CA_FR_IMG_APPROBATION_NV_001.jpg
CC_CA_FR_IMG_WALLET_NV_001.jpg
CC_CA_FR_VID_SANS_VERIFICATION_PV_001.mp4
```

## Campos recebidos

```text
Campo      | Valores / regra
-----------|--------------------------------------------------
VERTICAL   | CC, CAR, EMP, JOB, APP, GAME
COUNTRY    | CA, US etc.
LANG       | FR, EN, ES etc.
FORMAT     | IMG ou VID
ANGLE      | APPROBATION, SANS_VERIFICATION, LIMITE_HAUT, CHOIX, WALLET, UNKNOWN...
P_ORIENT   | pessoa + orientação
VARIANT    | 001, 002, 003... até 999
```

## P_ORIENT recebido

```text
Código | Significado original
-------|-------------------------------------
PV     | pessoa vertical
NV     | sem pessoa vertical
PH     | pessoa horizontal
NH     | sem pessoa horizontal
PS     | pessoa square
NS     | sem pessoa square
PU     | pessoa orientação desconhecida
NU     | sem pessoa orientação desconhecida
UU     | pessoa/orientação desconhecidas
```

## Decisão atual de Rodolfo

A regra MGS final usa somente:

```text
PV, PH, NV, NH
```

Códigos desconsiderados/removidos de nomes finais:

```text
PS, NS, PU, NU, UU
```

## Decisões operacionais incorporadas

- Status não entra no nome do arquivo.
- Status fica em pasta ou metadado/inventário.
- IDs, origem, gestor, page_id, drive_id, meta_creative_id e campaign_id ficam no inventário.
- Se não houver certeza do ângulo, usar `UNKNOWN` e nota.
- `person` deve ser `PERSON`, `NO_PERSON` ou `UNKNOWN` no inventário.
- Para o nome final, `P_ORIENT` aceita apenas `PV`, `PH`, `NV`, `NH`.
- `orientation` do nome final deve ser tratada como `VERTICAL` ou `HORIZONTAL`; square/unknown vai para revisão ou é mapeado operacionalmente como horizontal quando aprovado.

## Extensão veicular MGS — decisão de Rodolfo em 2026-08-25

Para a vertical `CAR`, Ares deve revisar o conteúdo real de cada imagem ou timeline de vídeo e distinguir carro de moto.

```text
Produto dominante  Modelo final
-----------------  -------------------------------------------------------------------------
Carro              {VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
Moto               {VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_MOTO_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

- `MOTO` fica imediatamente depois de `FORMAT`.
- Carro mantém o padrão anterior, sem `CARRO` no nome.
- A classificação é por asset e por evidência visual real; um lote pode conter carros e motos.
- Registrar `vehicle_type=MOTO|CARRO` no inventário.
- A vertical/operação continua `CAR`; `MOTO` é subtipo visual, não uma nova vertical ou pasta.

## Uso futuro

Quando houver novo país/idioma/vertical, não criar uma skill por operação se a regra for só variação de dicionário de ângulos. Atualizar `creative-taxonomy-mgs` ou adicionar referência específica com o dicionário da operação.
