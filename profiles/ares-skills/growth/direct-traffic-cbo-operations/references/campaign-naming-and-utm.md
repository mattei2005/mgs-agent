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

## Unicidade e reciclagem dos slots 01–60

1. `utm_campaign` e `utm_adgroup` são chaves de linhagem da Smart Bidding e não podem ser reutilizadas por outra campanha, mesmo depois de a campanha Meta antiga ficar `PAUSED` ou `DELETED`.
2. Os números visuais/operacionais da campanha permanecem limitados a `01–60`; reciclar o slot exige uma nova chave de geração dentro das UTMs.
3. Deletar a campanha Meta antiga não garante apagar receita, conversões ou histórico já registrados pela Smart Bidding sob a UTM anterior.
4. O formato da geração ainda depende de aprovação de Rodolfo e validação do parser/relatórios SB. Exemplo apenas candidato, não ativo: slot 15, geração 2 → `utm_campaign=b01fb13c15r02` e `utm_adgroup=b01fb13c15r02g01`.
5. Até a aprovação do formato, qualquer tentativa de criar campanha com par UTM já utilizado falha fechada.
6. Depois da aprovação, a ordem segura é: confirmar ciclo terminal após D3/reconciliação → criar nova geração `PAUSED` e validar → deletar a campanha terminal antiga → ativar a nova somente após revisão.

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
