# Contratos de pedidos naturais de campanha

## Princípio

O operador pode pedir campanhas em linguagem natural e omitir dados já resolvidos inequivocamente pelo canal/thread e pelo contrato ativo da operação. Não transformar o pedido em formulário obrigatório nem perguntar o que pode ser lido da rota canônica e do runtime.

Comece todo padrão de pedido com a etapa desejada: `APENAS VALIDAR`, `PREPARAR E AGUARDAR OK` ou `EXECUTAR`. Quando a conversa mostrar que o operador ainda está elaborando e a etapa não estiver explícita, trate como intake/validação; nunca antecipe write.

Horário e status são parâmetros do pedido. Não promova um valor ilustrativo do modelo a padrão permanente. Quando a conta estiver resolvida, `timezone da conta de anúncio` é especificação suficiente; preserve a data/hora local solicitada sem obrigar o operador a escrever o identificador IANA. Só use um default quando o contrato ativo da operação o declarar como default real e o pedido não trouxer override.

## Resolução por contexto

- Dentro de um canal dedicado a uma única operação, um alias curto de conta pode bastar para resolver site, país, vertical, idioma, gestor e estratégia.
- Fora do canal operacional, ou quando duas operações compartilham o mesmo alias, exigir o identificador que elimine a ambiguidade.
- O contexto nunca autoriza inferir Page, `pg_XXXXX`, modo, budget ou outra variável que o contrato marque como obrigatória por request.
- Fazer readback do contrato e da conta antes de materializar o manifest; nome de canal é pista de roteamento, não prova de estado Meta.

## Campos mínimos do pedido

```text
Etapa solicitada
Conta
Quantidade de campanhas
Tipo/vertical e quantidade de criativos por campanha
Origem dos criativos quando houver mídia nova
Liberdade de seleção/ângulo
Modo de criação
Budget exato + moeda por campanha
Destino
Início com data, hora e timezone explícitos
Status desejado
```

Rotular sempre `Quantidade de campanhas`; `Quantidade: N` é ambíguo com quantidade de criativos. Prefira data explícita a “próximo dia” quando o pedido puder ser executado depois. O gestor não precisa informar token, Page/pixel já unívocos nem o próximo número: Ares resolve o binding da conta e lê a sequência live.

## Modo humano versus rota técnica

Preservar a intenção comercial sem falsificar a implementação:

- `campanhas novas com criativos novos` significa novos objetos e mídia nova para o operador;
- uma conta pode exigir linhagem técnica de anúncio ou shell copiado para servir corretamente;
- o bloco de IDs técnicos pode ser explícito quando o padrão aprovado da operação o pedir; Ares valida `source_ad_id`, `creative_id` e `effective_object_story_id` e os informa no readback;
- em `criar do zero com criativos novos`, campanha/adset/creative/post/mídia são novos; contas com `lineage_required_for_new_media` podem exigir somente `source_ad_id` nos anúncios diretos;
- em `clonar com criativos novos`, o pedido declara o que preservar da estrutura/copy e quais creatives/posts substituir; a implementação mantém `source_ad_id`, cria novos creative/post/media IDs e preserva a URL base com UTMs do destino;
- `duplicar igual` não usa Drive: o pedido declara preservação de mídia, copy, estrutura, público, objetivo, bid, budget, URL base e post/prova social, além do próximo número e tracking novo; o executor cria novo Creative ID para os `url_tags`, confirma `source_ad_id` e preserva `effective_object_story_id`;
- não escreva “mesmo creative ID” quando a intenção é preservar lineage/prova social; traduza para `source_ad_id` e, quando necessário, post fonte + tracking do alvo;
- para `N` duplicações, reservar `N` números-alvo sequenciais e aplicar a convenção ordinal+fonte da operação; todas apontam diretamente para a campanha fonte informada, sem formar cadeia entre as duplicações, salvo pedido explícito em contrário;
- `clonar com criativos novos` informa a quantidade desejada no destino; ela pode diferir da fonte quando o pedido diz isso explicitamente;
- se o pedido proibir literalmente qualquer clone e o contrato só suportar lineage/clone, isso é conflito real e requer decisão/arquitetura, não tradução silenciosa.

Para qualquer modo que crie campanha nova, ler o maior número live antes de selar e novamente antes do write; atualizar juntos nome, identificador entre parênteses, `utm_campaign` e `utm_adgroup`. Nunca reutilizar tracking da fonte, pois mistura a atribuição de receita.

## Tráfego direto

Normalmente o pedido fecha com conta, quantidade, veículo/vertical, Drive, ângulos, modo, budget, horário no timezone da operação e status programado. Estrutura, evento, URL, Page/pixel, copy e UTM podem vir do contrato quando ele os declarar defaults vivos.

## ChatPion/Messenger

Além dos campos gerais, exigir:

- Facebook Page exata e `pg_XXXXX` quando a operação possui várias Pages;
- quantidade de criativos/anúncios por campanha quando o contrato aceita alternativas;
- pasta/vertical do Drive;
- `copy: padrão aprovado` ou os quatro campos Meta fornecidos;
- Messenger JSON/template padrão ou override explícito;
- horário no timezone da operação, que pode ser diferente do tráfego direto.

A criação literal do zero só é usada quando `supported_modes` e `ad_serving_route` da conta permitirem.

## Budget global

Sempre ler a política global de limites internos. Enquanto estiver inativa, o pedido não precisa declarar exceção de cap/pool: quantidade e budget explicitamente autorizados não são reduzidos. Ainda exigir budget exato, autoridade, pre-read/readback; billing, `account_spend_limit`, credenciais e automatic scaling mantêm gates próprios.

## Pitfalls

- Pedir site/país/idioma que a rota já resolve sem ambiguidade.
- Aceitar `Quantidade: N` sem determinar se são campanhas ou criativos.
- Confundir `copy` com imagem/vídeo.
- Omitir Page/`pg_XXXXX` em Messenger multi-Page.
- Reutilizar criativos quando o pedido diz novos e o saldo elegível é insuficiente.
- Transformar horário ou status de um exemplo em padrão da operação; esses campos pertencem ao pedido salvo default canônico explícito.
- Aplicar o horário do tráfego direto a uma operação ChatPion.
- Tratar lineage técnica como autorização para duplicar mídia ou copy.
- Iniciar onboarding, criação de runner, reparo de Drive ou pesquisa de payload dentro de um pedido cronometrado; setup termina antes do hot path.
- Medir somente o Engine quando o gestor esperou por preflight, mídia e pós-processamento; reportar também o tempo end-to-end.
- Incluir anúncio PAUSED/hold da fonte em duplicação; selecionar somente a estrutura configurada ACTIVE válida.
