# Contratos de pedidos naturais de campanha

## Princípio

O operador pode pedir campanhas em linguagem natural e omitir dados já resolvidos inequivocamente pelo canal/thread e pelo contrato ativo da operação. Não transformar o pedido em formulário obrigatório nem perguntar o que pode ser lido da rota canônica e do runtime.

Nos modelos que o operador pedir para montar, explicite a etapa desejada: `APENAS VALIDAR`, `PREPARAR E AGUARDAR OK` ou `EXECUTAR`. Não exija esses prefixos em um pedido natural já inequívoco: uma ordem autorizada para duplicar ou concluir é intenção de execução, não elaboração de modelo. Quando a conversa mostrar que o operador ainda está elaborando e a etapa não estiver explícita, trate como intake/validação; nunca antecipe write.

Horário e status são parâmetros do pedido. Não promova um valor ilustrativo do modelo a padrão permanente. Quando a conta estiver resolvida, `timezone da conta de anúncio` é especificação suficiente; preserve a data/hora local solicitada sem obrigar o operador a escrever o identificador IANA. Só use um default quando o contrato ativo da operação o declarar como default real e o pedido não trouxer override.

## Resolução por contexto

- Dentro de um canal dedicado a uma única operação, um alias curto de conta pode bastar para resolver site, país, vertical, idioma, gestor e estratégia.
- Fora do canal operacional, ou quando duas operações compartilham o mesmo alias, exigir o identificador que elimine a ambiguidade.
- O contexto nunca autoriza inferir Page, `pg_XXXXX`, modo, budget ou outra variável que o contrato marque como obrigatória por request.
- Fazer readback do contrato e da conta antes de materializar o manifest; nome de canal é pista de roteamento, não prova de estado Meta.

## Pedidos encadeados, ativação manual e emendas

1. Reconstrua uma linha por intenção a partir das mensagens autenticadas e do checkpoint: `origem → conta → alvos existentes ou fontes/quantidades novas → ação → budget → início → estado comprovado`. Use o binding da thread e o runtime para completar somente os campos já unívocos. Um relato de ativação manual e uma nova lista de duplicações na mesma conta não são o mesmo pedido.
2. Para a ativação manual, faça GET dos campaign/adset/ad IDs existentes e atribua a ação ao relato do operador, não ao Ares. Informe o estado de cada nível e as exceções atuais. Não reative, pause, recrie ou tente corrigir esses objetos como etapa implícita de uma nova duplicação; status do pai não comprova habilitação de todos os anúncios.
3. Para a nova duplicação, congele as próprias fontes e quantidades, leia os lances de cada fonte viva e preserve o início explícito. Não herde um cap ou orçamento de outro pedido só por proximidade na conversa. Mantenha o pedido novo separado do histórico manual mesmo quando a coordenação account-scoped exigir reconciliação.
4. Quando vier uma emenda com alvo inequívoco, registre mensagem, autor, campo anterior, campo aprovado e vínculo com o request original. Preserve a versão anterior como histórico e indique uma única versão efetiva. Se ainda houver duas interpretações que alterariam objetos diferentes, faça somente a pergunta de delimitação; a resposta resolve essa lacuna sem exigir que o operador repita o pedido inteiro.
5. Antes de executar uma versão emendada, confira os efeitos reais e os três bindings: input efetivo, snapshot PREPARED e job da fila. Um arquivo novo sozinho não invalida o cache anterior. Sem writes comprovados, use a reconciliação pré-write suportada para renovar a preparação e o dry-run sob os mesmos request/relógio, com backup e recibo; mantenha o hold até a consistência estar verificada. Com objetos já criados, preserve manifests selados e IDs e aplique somente o delta autorizado nos alvos existentes, com pre-read e GET final. Nunca execute a versão supersedida para contornar um erro de imutabilidade.
6. Verifique a dependência técnica antes de alegar que o lote antigo bloqueia o novo: leia lease, dono, fase e reservas e use o mecanismo canônico para inspecionar dependências. Se uma reconciliação manual estiver instalada, valide seu recibo e a preservação do histórico; ela encerra somente a coordenação e não certifica QA nem libera anúncios rejeitados. Uma capacidade ainda ausente exige manutenção separada e os gates próprios, não terminal fictício, bypass ou alteração dos objetos antigos.
7. Depois de esclarecida a separação dos pedidos, atualize o dono já existente e continue a execução. Em operação gerida por cards, use `kanban_show` para localizar dono/dependências e `kanban_comment` para vincular a emenda ou o aviso de conclusão; não crie outro grafo nem um writer paralelo. Só anuncie início de execução central após verificar o comando real ou avanço do checkpoint, e conclusão somente após readback integral da plataforma.

### Casos mínimos de verificação do contrato

- Lote existente assumido manualmente + nova duplicação agendada: os IDs antigos permanecem fora dos writes do novo pedido; data e hora novas continuam explícitas.
- Emenda que altera somente o budget do lote novo: todos os alvos novos usam o valor aprovado, os demais campos e o relógio permanecem iguais e nenhum orçamento antigo é alterado.
- Input atualizado com PREPARED ou fila ainda na versão anterior: o execute permanece bloqueado até a reconciliação suportada; o cache antigo nunca vira autorização para executar o budget supersedido.
- Pedido de aviso na origem: existe um único dono da entrega e uma única conclusão vinculada ao lote completo, sem novo cron ou aviso de manutenção apresentado como resultado.

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
- `duplicar igual` não seleciona mídia nova do Drive: preserve a definição real da fonte, seu Ad setup e a localização aprovada do tracking, exceto os deltas expressamente pedidos e a renumeração canônica. Use a materialização prevista pelo contrato da operação; ela pode gerar creative/post novos. Exija preservação de post/prova social somente quando solicitada ou contratada e compatível com o tracking do alvo; `source_ad_id` comprova lineage, não igualdade de `effective_object_story_id`;
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
