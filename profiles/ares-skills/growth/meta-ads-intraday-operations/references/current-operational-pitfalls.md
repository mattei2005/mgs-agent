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
- Ao corrigir URLs de anúncios, validar o payload com `execution_options=["validate_only"]` antes de mutar. Erro Meta `10/3858749` com função **Anunciante** ausente descreve a tarefa de publicidade da **Página**, não exige token pessoal por anunciante. Preservar o System User/item corporativo canônico; conceder tarefas ou trocar arquitetura de credencial exige autoridade separada.
- Tratar renomeação de campanha/conjunto e edição de URL como camadas independentes: registrar os IDs e readbacks concluídos, manter a URL como pendente se a Página bloquear, e nunca declarar a colisão UTM resolvida apenas porque os nomes mudaram. Se POST retornar sucesso e o GET imediato ainda mostrar o nome antigo, repetir somente a leitura antes de qualquer novo POST.
- Em edição de URL que exige nova versão do pacote AdCreative, erro `100/3858504` pode decorrer do campo legado `degrees_of_freedom_spec.creative_features_spec.standard_enhancements` no readback da fonte. Remover somente esse agregador descontinuado do payload, preservar todos os recursos individuais e suas customizações, validar novamente e comparar os recursos após o write. Manter ad IDs/source_ad_id e mídia/copy; registrar novos creative/post IDs e avisar sobre processamento/revisão sem afirmar entrega ativa.
- Para sondar a Página diretamente, usar GET com `fields=id,name`; não pedir `tasks` como campo direto de Page. Ler delegação pelo edge administrativo `assigned_users` quando autorizado. Scopes granted e ativo no portfólio não substituem validate-only do anúncio.
- Campanha nova nasce PAUSED salvo autorização explícita.
- Allowlist dinâmica não pode validar proveniência somente por um literal de `source`. Para campanhas Engine v3 criadas por rota diária ou live/one-time, exigir audit terminal legível com `engine_version`, `request_id`, status concluído e `campaign_id` exatos; para cópia manual terminal, exigir autorização, audit de cleanup/readback, ID e status terminal correspondentes. Uma nova nomenclatura de source com evidência completa deve receber branch explícito e teste de mismatch fail-closed, sem bloquear Diário/Intraday/watchers por mera diferença de rótulo.

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
- Alteração de cron exige readback de schedule, script, enabled, no_agent e deliver.
- Separar relatório read-only de alteração de campanha: um writer lease persistente de recuperação não pode interromper indefinidamente Diário/Intraday, nem uma operação bloquear outra. Na conta CPV13, os wrappers de relatório usam `--report-only --gate` sem o gate persistente de writer; checkpoints `--actions-only` preservam todos os gates de write. Manter lock físico account-scoped com espera limitada; caso ele impeça a leitura, publicar aviso sanitizado/idempotente na thread fixa e retornar não-sucesso. Nunca liberar a lease ou marcar um pedido COMPLETE apenas para recuperar o relatório.
- Preservar deduplicação ao combinar `--report-only --gate`: modo somente leitura não é ordem de repostagem. Forçar novo envio somente no pedido manual sem `--gate`. `last_status=ok` exige GET/readback real da entrega quando o horário prevê relatório; saída vazia sozinha não prova postagem. Testar pendência POSTPROCESS_PENDING, zero campaign writes, timeout de lock com aviso, dedupe e readback diferido.
- Ao auditar crons pausados, cruzar timestamps e instruções canônicas antes de qualquer resume. Ausência de `paused_reason` não invalida um hold autorizado registrado em checkpoint. Não reativar todos os jobs para corrigir uma falha isolada.
