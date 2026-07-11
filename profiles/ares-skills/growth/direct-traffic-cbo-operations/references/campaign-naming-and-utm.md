# Campaign naming and UTM contract

## Scope

Contrato para campanhas Meta/Facebook de tráfego direto por CBO. Esta nomenclatura não substitui nomes de criativos da `creative-taxonomy-mgs` nem a taxonomia de campanhas DTR/ChatPion.

## Tokens

```text
Token | Significado                                    | Formato
------|------------------------------------------------|--------
bNN   | Business Manager onde está a conta             | 2 dígitos
fbNN  | Conta de anúncio Meta dentro da sequência MGS  | 2 dígitos
cNN   | Campanha dentro da conta                       | 2 dígitos
gNN   | Adset/conjunto dentro da campanha              | 2 dígitos
gXXX  | Gestor responsável                             | 3 dígitos
-f    | Estratégia de chat                             | literal
-s    | Estratégia de quiz                             | literal
```

A numeração é sequencial no cadastro operacional definido pela MGS, não deve ser inferida de ID longo da Meta, domínio, nome da página ou posição visual no Ads Manager.

## Parâmetros obrigatórios

### utm_source

Valor literal e case-sensitive para o contrato MGS:

`utm_source=facebook`

### utm_medium

```text
Estratégia | Formato  | Exemplo
-----------|----------|--------
Chat       | gXXX-f   | g002-f
Quiz       | gXXX-s   | g002-s
```

O gestor sempre usa 3 dígitos. `g02-f`, `G002-f`, `g002 -f` e ` g002-f` são inválidos.

### utm_campaign

`b{BM:02d}fb{ACCOUNT:02d}c{CAMPAIGN:02d}`

Exemplo: `b01fb01c01`.

### utm_adgroup

`{utm_campaign}g{ADSET:02d}`

Exemplo: `b01fb01c01g01`.

## Regras de consistência

1. `utm_adgroup` começa com o valor exato de `utm_campaign`.
2. O sufixo de `utm_adgroup` contém somente um `gNN` adicional.
3. BM, conta, campanha e adset usam no mínimo/contrato atual exatamente 2 dígitos.
4. Gestor usa exatamente 3 dígitos.
5. Não há espaços em nomes ou valores.
6. A URL contém uma ocorrência de cada UTM obrigatória.
7. Outros parâmetros podem coexistir (`fbclid`, parâmetros internos), mas não duplicar/chocar UTMs canônicas.

## Estrutura padrão da campanha

```text
Objeto     | Padrão | Observação
-----------|--------|----------------------------------------
Campanha   | 1 CBO  | orçamento no nível de campanha
Adset      | 1      | `g01` no primeiro conjunto
Criativos  | 3      | todos imagem, todos vídeo ou mix
Destino    | direto | URL final com UTMs canônicas
```

## Evento obrigatório no nome da campanha

```text
Experiência | Captura                  | Texto literal obrigatório
------------|--------------------------|-----------------------------
Chat        | com ou sem captura       | `event_add_to_wishlist`
Quiz        | com ou sem captura       | `event_Subscribe`
```

Regras:

1. O evento pertence ao **nome da campanha Meta**; não é parâmetro UTM.
2. Captura não altera o evento obrigatório.
3. Preservar exatamente capitalização e underscores: `event_add_to_wishlist` e `event_Subscribe`.
4. Antes de criar/clonar, validar o nome final juntamente com BM, conta e sequência da campanha.

## Exemplos

### Chat, gestor G002

`https://example.com/oferta/?utm_source=facebook&utm_medium=g002-f&utm_campaign=b01fb01c01&utm_adgroup=b01fb01c01g01`

### Quiz, gestor G002

`https://example.com/quiz/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b01fb01c02&utm_adgroup=b01fb01c02g01`

## Validação automática

```bash
python3 scripts/validate_direct_traffic_utm.py 'https://example.com/quiz/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b01fb01c02&utm_adgroup=b01fb01c02g01'
```

Saída esperada: JSON com `valid: true`, estratégia, gestor, BM, conta, campanha e adset.

Para gerar:

```bash
python3 scripts/validate_direct_traffic_utm.py \
  --build --base-url 'https://example.com/quiz/' \
  --bm 1 --account 1 --campaign 2 --adset 1 --manager 2 --strategy quiz
```

O gerador sempre produz a URL e a revalida antes de retornar.
