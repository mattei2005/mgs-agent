# Campaign naming and UTM contract

## Scope

Contrato para campanhas Meta/Facebook de tráfego direto por CBO. Esta nomenclatura não substitui nomes de criativos da `creative-taxonomy-mgs` nem a taxonomia de campanhas DTR/ChatPion.

## Tokens

```text
Token | Significado                                    | Formato
------|------------------------------------------------|--------
bNN   | Business Manager onde está a conta             | 2 dígitos
fbNN  | Conta de anúncio Meta dentro da sequência MGS  | 2 dígitos
cN    | Campanha dentro da conta                       | mínimo 2 dígitos, sem limite superior
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
3. BM, conta e adset usam exatamente 2 dígitos. Campanha usa no mínimo 2 dígitos e cresce naturalmente sem limite superior (`01..99`, depois `100`, `101` etc.).
4. Gestor usa exatamente 3 dígitos.
5. Não há espaços em nomes ou valores.
6. A URL contém uma ocorrência de cada UTM obrigatória.
7. Outros parâmetros podem coexistir (`fbclid`, parâmetros internos), mas não duplicar/chocar UTMs canônicas.

## Unicidade e sequência sem limite superior

1. A campanha usa numeração sequencial sem limite em `c59` ou `c60`. Números de 1 a 9 recebem zero à esquerda; de `c100` em diante a largura cresce naturalmente.
2. O wrapper é imutável: `utm_campaign=bNNfbNNc{N}` e `utm_adgroup=bNNfbNNc{N}gNN`. Não adicionar `rNN`, data, versão ou outro sufixo.
3. Não pode haver duas campanhas não deletadas com o mesmo par `utm_campaign`/`utm_adgroup` no estado final.
4. Segundo Ciro, desenvolvedor da Smart Bidding, deletar a campanha antiga é suficiente para que a UTM canônica do slot possa ser reutilizada.
5. Rollover seguro: confirmar antiga `PAUSED` e terminal após D3/reconciliação → criar substituta `PAUSED` e validar → deletar antiga → readback operador `DELETED` → ativar substituta após revisão.
6. Campanha antiga `ACTIVE`, em hold, sem D3 fechado ou com reconciliação pendente bloqueia o rollover.
7. `ARCHIVED` cru no Graph equivale a `DELETED` no Ads Manager desta operação e não bloqueia a reutilização do slot.

## Estrutura padrão da campanha

```text
Objeto     | Padrão | Observação
-----------|--------|----------------------------------------
Campanha   | 1 CBO  | orçamento no nível de campanha
Adset      | 1      | `g01` no primeiro conjunto
Criativos  | 3      | todos imagem, todos vídeo ou mix
Destino    | direto | URL final com UTMs canônicas
```

## Evento de conversão obrigatório no adset

```text
Experiência | Captura            | Evento informado             | Valor Meta Graph
------------|--------------------|------------------------------|-------------------
Chat        | com ou sem captura | `event_add_to_wishlist`      | `ADD_TO_WISHLIST`
Quiz        | com ou sem captura | `event_Subscribe`            | `SUBSCRIBE`
```

Regras:

1. O evento pertence à configuração de conversão do **adset/conjunto**, não ao nome da campanha nem às UTMs.
2. Captura não altera o evento obrigatório.
3. Validar por GET real: `optimization_goal=OFFSITE_CONVERSIONS`, `promoted_object.pixel_id` presente e `promoted_object.custom_event_type` conforme a tabela.
4. O Ads Manager pode exibir `event_add_to_wishlist`/`event_Subscribe`; a Graph API normaliza para `ADD_TO_WISHLIST`/`SUBSCRIBE`.
5. Não exigir o literal do evento no nome da campanha sem uma regra de naming separada e explícita.

## Exemplos

### Chat, gestor G002

`https://example.com/oferta/?utm_source=facebook&utm_medium=g002-f&utm_campaign=b01fb01c01&utm_adgroup=b01fb01c01g01`

### Quiz, gestor G002

`https://example.com/quiz/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b01fb01c02&utm_adgroup=b01fb01c02g01`

## Validação automática

```bash
python3 scripts/validate_direct_traffic_utm.py \
  'https://example.com/quiz/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b01fb01c02&utm_adgroup=b01fb01c02g01' \
  --conversion-event SUBSCRIBE
```

Saída esperada: JSON com `valid: true`, estratégia, gestor, BM, conta, campanha, adset e `conversion_event_verified: true`.

Para gerar:

```bash
python3 scripts/validate_direct_traffic_utm.py \
  --build --base-url 'https://example.com/quiz/' \
  --bm 1 --account 1 --campaign 2 --adset 1 --manager 2 --strategy quiz
```

O gerador sempre produz a URL e a revalida antes de retornar.
