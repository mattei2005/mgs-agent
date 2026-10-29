# Pitfalls operacionais atuais — Meta Ads

## Conta e token

- Nunca usar token global implícito. O item 1Password vem de `accounts/<account_id>.json` ou argumento explícito.
- Cache válido não prova acesso à conta; auth check read-only precisa retornar a conta solicitada.
- Não imprimir token. Audit registra somente item, campo, comprimento, HTTP e timestamps.

## Estado e escrita

- `status=ACTIVE` em campanha não garante entrega se adset/ad estiver pausado; preservar status hierárquico no audit.
- UI e API podem representar deleted/archived de forma diferente; declarar o mapeamento específico da operação.
- Timeout de POST não é autorização para repetir. Reconciliar campanha, adset, creative e ad antes de retry.
- Objeto parcialmente criado deve ser retomado pelos IDs persistidos; cleanup nunca atinge source nem objetos de outra request.
- Passe o ID imutável explicitamente aos helpers de GET/POST em múltiplos lotes; não dependa de um mapa global mutável de alvos, pois uma leitura do lote seguinte pode trocar esse mapa entre o POST e seu readback. Se um helper legado exigir estado global, delimite e restaure esse contexto por lote antes de cada chamada. Teste alternância A→B→A e interrupção entre POST e GET: a recuperação deve ler o ID persistido, reconhecer o valor desejado e concluir sem segundo POST.
- Ao corrigir URLs de anúncios, validar o payload com `execution_options=["validate_only"]` antes de mutar. Erro Meta `10/3858749` com função **Anunciante** ausente descreve a tarefa de publicidade da **Página**, não exige token pessoal por anunciante. Preservar o System User/item corporativo canônico; conceder tarefas ou trocar arquitetura de credencial exige autoridade separada.
- Tratar renomeação de campanha/conjunto e edição de URL como camadas independentes: registrar os IDs e readbacks concluídos, manter a URL como pendente se a Página bloquear, e nunca declarar a colisão UTM resolvida apenas porque os nomes mudaram. Se POST retornar sucesso e o GET imediato ainda mostrar o nome antigo, repetir somente a leitura antes de qualquer novo POST.
- Em edição de URL que exige nova versão do pacote AdCreative, erro `100/3858504` pode decorrer do campo legado `degrees_of_freedom_spec.creative_features_spec.standard_enhancements` no readback da fonte. Remover somente esse agregador descontinuado do payload, preservar todos os recursos individuais e suas customizações, validar novamente e comparar os recursos após o write. Manter ad IDs/source_ad_id e mídia/copy; registrar novos creative/post IDs e avisar sobre processamento/revisão sem afirmar entrega ativa.
- Para sondar a Página diretamente, usar GET com `fields=id,name`; não pedir `tasks` como campo direto de Page. Ler delegação pelo edge administrativo `assigned_users` quando autorizado. Scopes granted e ativo no portfólio não substituem validate-only do anúncio.
- Campanha nova nasce PAUSED salvo autorização explícita.
- Allowlist dinâmica não pode validar proveniência somente por um literal de `source`. Para campanhas Engine v3 criadas por rota diária ou live/one-time, exigir audit terminal legível com `engine_version`, `request_id`, status concluído e `campaign_id` exatos; para cópia manual terminal, exigir autorização, audit de cleanup/readback, ID e status terminal correspondentes. Uma nova nomenclatura de source com evidência completa deve receber branch explícito e teste de mismatch fail-closed, sem bloquear Diário/Intraday/watchers por mera diferença de rótulo.

## Auditoria pontual de alterações via Activities

1. **Fixe conta e janela.** Resolva o binding da conversa e confirme por GET `id,name,currency,timezone_name`. Para “hoje”, use meia-noite civil até o instante de coleta no `ZoneInfo` live da conta; envie `since` e `until` ISO com offset. Use a versão Graph e o helper definidos na governança desta skill. Comece pela receita já disponível em `ares-meta-account-activity-monitor.py::fetch_activities`, sem executar seu entrypoint de monitoramento/postagem. Não use o baseline de um watcher como lista completa das alterações do período.
2. **Colete e persista antes de analisar.** No edge `act_<account_id>/activities`, peça `event_time,date_time_in_timezone,event_type,object_id,object_name,object_type,actor_id,actor_name,application_id,application_name,translated_event_type,extra_data`. Percorra a paginação bounded até não haver `next`, registre contagem e completude de cada página e filtre também localmente pela janela. Preserve fontes e timestamps protegidos do mesmo pedido; projete somente os eventos operacionais necessários e não exponha billing, credenciais ou payloads brutos. Se surgir falha local de agrupamento, retome da resposta persistida, sem repetir a coleta já concluída.
3. **Resolva a hierarquia por IDs, não pelo rótulo legado.** Activities pode representar campanha atual como `CAMPAIGN_GROUP`, conjunto como `CAMPAIGN` e anúncio como `ADGROUP`. Portanto, não filtre apenas pelo literal `CAMPAIGN` nem agrupe só pelo nome do evento. Leia os object IDs por batch GET com campos adequados: campanha `id,account_id,name,status,effective_status,daily_budget,bid_strategy`; conjunto acrescenta `campaign_id,bid_strategy,bid_amount`; anúncio usa `campaign_id,adset_id`. Valide HTTP externo, cada child e `account_id`. Complete a coleção com GET dos campaign IDs pais ausentes **antes** de exigir que todos os ancestrais estejam no mapa: uma edição somente de bid pode ter evento no conjunto e nenhum evento na campanha. Agrupe então pelo `campaign_id` real; nomes/wrappers são rótulos de apresentação, não prova de parentesco.
4. **Decodifique a mudança no campo certo.** Faça parsing de `extra_data` quando vier como JSON textual. Em `update_campaign_budget`, os montantes podem estar dentro de `old_value.old_value` e `new_value.new_value`, com tipo `payment_amount`, moeda e periodicidade; converta unidades menores com `Decimal` e a escala da moeda comprovada. Em `update_ad_set_bid_strategy`, compare tanto `old_value/new_value` da estratégia quanto `additional_value.old_value/new_value` do cap: `COST_CAP → COST_CAP` ainda pode conter alteração real da meta. Preserve uma sequência de budgets como A → B → C e seus horários, em vez de mostrar apenas o delta líquido. Traduza o alias legado `LOWEST_COST_BID_STRATEGY` para MAXVOL na apresentação, preservando o literal bruto no audit.
5. **Separe edição, criação e ciclo automático.** Use `create_campaign_group` como prova de campanha criada; reúna criação de conjuntos/anúncios e configuração inicial no bloco de novas, sem contá-las como edições de campanhas preexistentes. Eventos de segmentação ou otimização com valor anterior null/vazio durante criação não comprovam uma mudança posterior. Exclua `first_delivery_event` e transições de processamento/revisão da lista de decisões humanas. Em status, examine `extra_data.run_status` e os rótulos: no formato validado, `1 → 15` corresponde a ativa → inativa; `1 → 17 → 1` é processamento, não pausa/reativação manual. Não atribua uma decisão humana apenas porque o evento carrega um actor não zero.
6. **Atribua com limite explícito.** Cruze `actor_id + application_id` e, quando aplicável, o audit local do Ares. Perfil anunciante via Power Editor/Ads Manager comprova a origem técnica, não quem estava ao teclado; não troque silenciosamente o nome Meta pelo nome Discord do solicitante. Separe ações Ares comprovadas de mudanças manuais e da Meta automática; quando a pessoa física não estiver comprovada, informe essa limitação sem bloquear a lista de mudanças verificadas.
7. **Reconcilie e entregue.** Compare a última alteração registrada de cada campo com GET atual dos mesmos IDs, preservando horários distintos de histórico e readback. Se `adset.bid_strategy` vier ausente, use somente a estratégia explícita da campanha pai e o `bid_amount` live do conjunto; não infira pelo nome. Divergência posterior deve ser descrita, não corrigida nem ocultada. Conte IDs únicos programaticamente e separe existentes alteradas de novas. Entregue bullets por número/produto, horários no fuso informado, valores anterior → novo e moeda/periodicidade; mantenha IDs técnicos no audit. Esse levantamento não autoriza writes, alertas recorrentes ou publicação fora da origem.

### Checks de aceitação

- Pai ausente no lote inicial: completar somente esse campaign ID e agrupar o evento do conjunto na campanha correta.
- Estratégia igual e cap diferente: registrar alteração de meta; cap ausente em MAXVOL não vira zero.
- A → B → C: preservar os dois eventos e confrontar C com o readback atual.
- Ativa → processamento → ativa: não contar pausa/reativação; ativa → inativa deve corresponder ao status configurado atual ou ter divergência posterior declarada.
- Campanha criada com um conjunto e vários anúncios: contar uma campanha nova, sem inflar o total pelos objetos filhos.
- Perfil Meta diferente do nome Discord: conservar atribuição técnica e limitação de identidade, sem afirmar autoria física.

## Tempo, moeda e métricas

- `today` usa timezone da conta. VPS e UTC servem só para audit.
- Confirmar unidade monetária antes de normalizar budget, spend ou balance.
- Métrica e fórmula vêm do contrato; ausência de action não pode virar zero válido sem regra explícita.
- Receita externa pode ter atraso; declarar freshness e janela do join.

## Rate limit e payload

- Começar com campos mínimos e expandir por ID/lote pequeno.
- Não pedir `object_story_spec` em massa.
- Aplicar throttle e backoff limitado; erro de parâmetro/compliance não recebe retry.

## Discord e cron

- Usar thread fixa registrada e não criar substituta por conveniência.
- Wrapper que publica diretamente usa `deliver=local`, stdout vazio e IDs persistidos para evitar duplicidade.
- Mensagem operacional não inclui path, PID, trace bruto ou rodapé automático.
- Alteração de cron exige readback de schedule, script, enabled, no_agent e deliver; valide também o destino/thread capturado e o offset do horário físico, pois um job correto pode entregar no lugar ou fuso errado.
- Ao reutilizar um auditor de agenda, remova exclusões históricas e exclua no pós-write somente o ID do próprio job recém-criado; ignorar outro job pode produzir zero colisão falso. Separe resultado calculado de descrições herdadas: um auditor criado para observer não prova ausência de business writes no novo runner. Registre os recursos reais, lock, duração e janela de ativação do alvo.
- Compare a contenção de baseline somente entre minutos que preservam a janela e o timeout do pedido. Registre separadamente horário físico do scheduler e horário lógico de write; o runner deve esperar sem segurar a lane da conta para não bloquear relatórios.
- Verifique REPORT-INFRA com GET da mensagem exata e valide canal, embed, conteúdo vazio e ausência de mentions; a resposta de criação do transporte não é uma leitura posterior da mensagem.
- Separar relatório read-only de alteração de campanha: um writer lease persistente de recuperação não pode interromper indefinidamente Diário/Intraday, nem uma operação bloquear outra. Na conta CPV13, os wrappers de relatório usam `--report-only --gate` sem o gate persistente de writer; checkpoints `--actions-only` preservam todos os gates de write. Manter lock físico account-scoped com espera limitada; caso ele impeça a leitura, publicar aviso sanitizado/idempotente na thread fixa e retornar não-sucesso. Nunca liberar a lease ou marcar um pedido COMPLETE apenas para recuperar o relatório.
- Preservar deduplicação ao combinar `--report-only --gate`: modo somente leitura não é ordem de repostagem. Forçar novo envio somente no pedido manual sem `--gate`. `last_status=ok` exige GET/readback real da entrega quando o horário prevê relatório; saída vazia sozinha não prova postagem. Testar pendência POSTPROCESS_PENDING, zero campaign writes, timeout de lock com aviso, dedupe e readback diferido.
- Ao auditar crons pausados, cruzar timestamps e instruções canônicas antes de qualquer resume. Ausência de `paused_reason` não invalida um hold autorizado registrado em checkpoint. Não reativar todos os jobs para corrigir uma falha isolada.
