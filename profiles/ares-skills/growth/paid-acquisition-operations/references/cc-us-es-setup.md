# CC_US_ES setup — decisões iniciais

Sessão-base: estruturação inicial do Ares para operação de aquisição paga `CC_US_ES`.

## Operação piloto

```text
Operação  | CC_US_ES
Vertical  | CC — Credit Card
Country   | US
Language  | ES
Uso       | Cartões de crédito nos EUA em espanhol
```

## Drive

Pasta raiz validada com Service Account:

```text
MGS-AGENTS/CRIATIVOS/
├── CC_US_EN
└── CC_US_ES
```

Estrutura oficial de `CC_US_ES`:

```text
CC_US_ES/
├── IMG/
│   ├── 01_READY
│   ├── 02_TESTING
│   ├── 03_TESTED
│   ├── 04_WINNERS
│   ├── 05_REJECTED
│   └── 99_LEGACY
└── VID/
    ├── 01_READY
    ├── 02_TESTING
    ├── 03_TESTED
    ├── 04_WINNERS
    ├── 05_REJECTED
    └── 99_LEGACY
```

## Credencial Drive

Item 1Password criado por Rodolfo:

```text
Vault | MGS Conteúdo
Item  | Google Service Account - MGS Agent
```

Campos esperados no item:

```text
service_account_email
folder_id
pasta
permissao
service_account_json
```

Validação segura feita nesta sessão:

```text
service_account_json          | parse OK
private_key                   | presente
service_account_email         | confere com client_email do JSON
Drive folder access           | OK
folder_name                   | MGS-AGENTS/CRIATIVOS
can_edit/can_add_children     | true na configuração atual
```

Nunca imprimir JSON, private_key, tokens ou folder_id se não houver necessidade operacional explícita.

## Taxonomia oficial inicial

Modelo:

```text
CC_US_ES_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplos:

```text
CC_US_ES_IMG_APROBACION_NV_001.jpg
CC_US_ES_IMG_SIN_VERIFICACION_PH_001.jpg
CC_US_ES_VID_LIMITE_ALTO_PV_001.mp4
CC_US_ES_IMG_CASHBACK_NH_002.png
```

## Ângulos iniciais para CC_US_ES

```text
ANGLE              | Significado
-------------------|--------------------------------------------------
APROBACION          | Aprovação / pré-aprovação
SIN_VERIFICACION    | Sem verificação / baixa fricção
LIMITE_ALTO         | Limite alto
SIN_CREDITO         | Sem crédito / histórico limitado
MAL_CREDITO         | Crédito ruim / negativado
CASHBACK            | Cashback / recompensas
RECOMPENSAS         | Benefícios, pontos, milhas
COMPARACION         | Comparativo / escolha entre cartões
WALLET              | Uso cotidiano / carteira / pagamento do dia a dia
URGENCIA            | Aprovação rápida / necessidade imediata
UNKNOWN             | Ângulo incerto; exige note
```

## Tamanhos oficiais

Rodolfo informou que a operação usa somente:

```text
Formato | Dimensão  | Aspect ratio | Uso
--------|-----------|--------------|----------------------------
FEED    | 1080x1080 | 1:1          | Feed Facebook + Instagram
STORY   | 1080x1920 | 9:16         | Stories Facebook + Instagram
```

Decisão: não colocar tamanho no nome; registrar em inventário.

Mapeamento:

```text
Tamanho   | Sem pessoa | Com pessoa | Orientation | placement_fit
----------|------------|------------|-------------|--------------
1080x1080 | NH         | PH         | HORIZONTAL  | FEED
1080x1920 | NV         | PV         | VERTICAL    | STORY
```

## Inventário mínimo usado nesta operação

```text
filename
vertical
country
language
format
angle
person
orientation
p_orient
variant
status
performance_label
source
page_id
asset_drive_id
meta_creative_id
origin_campaign_id
width
height
aspect_ratio
placement_fit
created_at
notes
```

## Ordem de continuidade

1. Receber/adicionar criativos em `IMG/01_READY` ou `VID/01_READY`.
2. Validar nomes contra taxonomia.
3. Montar inventário inicial.
4. Confirmar CPA alvo e regra de pausa/substituição com gestores.
5. Só depois conectar Meta Ads read-only e gerar diagnóstico.
