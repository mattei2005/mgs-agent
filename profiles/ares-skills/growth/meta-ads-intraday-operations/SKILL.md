---
name: meta-ads-intraday-operations
description: "Use em governança, relatórios e crons Meta por operação."
version: 3.0.3
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, intraday, daily, campaigns, reporting, growth, mgs]
---

# Meta Ads Intraday Operations — Ares/MGS

Use esta skill para estruturar, revisar ou manter leitura intraday, relatório diário, guardrails e crons Meta Ads do Ares. Ela é uma camada **genérica de governança**: métricas, thresholds, horários, budgets, threads e ações pertencem ao contrato específico de cada operação.

## Disclosure progressivo

1. Identifique a operação, a conta e o pedido exato.
2. Abra primeiro o arquivo vivo em `/root/mgs-agent/data/ares/meta-ads/operations/` e a conta em `accounts/`.
3. Carregue a skill específica da estratégia/operação, quando existir.
4. Para layout de relatório, abra `references/current-reporting-contract.md`.
5. Para falhas conhecidas, abra `references/current-operational-pitfalls.md`.
6. Evidência histórica nunca vira regra ativa por semelhança.

## Contrato obrigatório por operação

Antes de criar cron ou executar write, o contrato deve definir explicitamente:

```text
Campo                         Obrigatório
----------------------------  -------------------------------------------------
operation_id                  site, país, vertical, idioma e estratégia
account_id / alias            conta real validada por API
currency / timezone           readback da Meta
owner / manager               pessoas autorizadas e gates de budget
objective / optimization      objetivo, evento e fonte da métrica
campaign structure            budget level, adsets, ads, bid strategy
report metrics                fórmula, período, moeda e fonte
Intraday / Daily schedule     horários no timezone da conta
fixed Discord threads         destino por tipo de relatório/operação
write mode                    read_only, dry_run ou controlled_write
creative policy               reserva, Drive × Meta e elegibilidade
recovery / rollback           proveniência e readback pós-write
```

Campos ausentes ficam `pending_review` e bloqueiam somente a ação dependente. Nunca preencher usando contrato de outra operação.

## Modos

```text
Modo                Comportamento
------------------  ------------------------------------------------------------
read_only           Consulta API/config e salva evidência; zero write.
dry_run             Calcula ações sem alterar a Meta.
recommend           Recomenda e aguarda a autorização aplicável.
controlled_write    Executa somente o escopo pontual e pré-aprovado.
autonomous_guarded  Exige política própria, allowlist, limites e aprovação formal.
```

## Governança consolidada

- Runtime/API/dados reais vencem snapshots para estado atual.
- MGS OS, `authorized-users.json` e `permissions-matrix.md` vencem para dono e autoridade.
- Token vem do item 1Password registrado na conta; nunca existe token global implícito e nunca é impresso.
- Em auditoria de confidencialidade, isolamento e pedidos globais, seguir `references/confidentiality-scope-audit.md`: testar formatos alternativos e fontes antes de concluir que o gate cobre toda a operação.
- Scripts usam `ares-meta-common.py` para cache protegido, throttle, headers de quota e backoff limitado.
- Toda resposta GET/POST/batch alimenta o estado de quota quando os headers existirem.
- Erros de validação, parâmetro ou compliance não recebem retry cego.
- Antes de correção, reconciliar efeitos parciais e reutilizar o request/IDs persistidos; nunca repetir POST não idempotente às cegas.
- Sucesso de write exige GET/readback do alvo completo e audit com estado anterior/posterior.
- Após budget write, `effective_status=IN_PROCESS` pode ser transitório mesmo com `status/configured_status=ACTIVE` e budget correto. Valide os campos configurados e imutáveis separadamente, faça novo GET para reconciliar o effective e não repita o POST somente por essa transição. Teste live confirmado: budget desejado presente no primeiro GET e effective retornando a ACTIVE no segundo GET, sem POST adicional.
- Para monitorar alterações externas, usar `act_<ACCOUNT_ID>/activities` com Graph `v26.0` explicitamente fixada antes de carregar o helper Meta, `since`/`until` ISO e paginação bounded. O helper legado em `v20.0` pode devolver uma fatia antiga/stale e mascarar eventos recentes. O baseline inicial apenas marca eventos já existentes; alertas futuros cruzam `actor_id` + `application_id` com o audit local do Ares. Uma fonte Ares allowlisted sem audit correspondente preserva anomalia/classificação local; a política específica da operação decide se isso chega ao Discord.
- Quando o contrato disser **alertar somente se outra pessoa/ferramenta mexer**, eventos com `actor_id=0` são automações da própria Meta e ficam silenciosos, inclusive cobrança e regra nativa; writes com audit local do Ares ficam silenciosos independentemente do app; fontes API allowlisted como pertencentes ao Ares também ficam silenciosas no Discord mesmo sem audit correspondente, preservando a classificação local para investigação de integridade. A identidade exibida do perfil anunciante não basta para suprimir: Ares e uma pessoa podem usar o mesmo perfil, então a distinção usa o par `actor_id+application_id` e o audit local. Humano no mesmo perfil via Ads Manager/Power Editor alerta; Ares via API allowlisted não alerta. Somente mudança material restante, atribuível a pessoa ou ferramenta externa, gera alerta.
- Pausar, reativar, criar, clonar ou editar exige o modo autorizado no contrato da operação.
- Budget segue o gate explícito vigente; billing, credencial, pixel/CAPI e app/permissão continuam críticos.
- Campanha nova deve nascer PAUSED, salvo autorização operacional explícita em contrato validado.
- IDs técnicos ficam em audit; relatório humano mostra alias e nomes operacionais.

## Métricas e decisão

- Cada operação declara a métrica principal e sua fórmula. Não assumir `subs`, `MO`, `CPMO`, `CPS`, purchase ROAS ou ROI por país/estratégia.
- Toda métrica reportada informa período, moeda, fonte e limitação relevante.
- Antes de atribuir queda à campanha, checar anomalia de monetização, entrega e fonte de receita quando o contrato exigir reconciliação externa.
- Calibração inicial deve começar read-only/dry-run e comparar API com conferência manual do gestor antes de liberar automação.
- Learning, carência, persistência e exceções de bid strategy são parâmetros do contrato, não defaults globais.

## Crons e Discord

- Antes de criar ou alterar qualquer cron, aplicar `context/cron-scheduling-policy.md`: inventariar root/systemd/Hermes de todos os profiles e schedulers próprios, normalizar timezones, exigir zero colisão com outro job operacional fora das baselines e, quando baselines contínuas/densas ocuparem todos os 60 minutos, escolher o minuto de menor contenção com exceção auditada; repetir a auditoria depois do readback e verificar lock, duração, conta/API e recurso compartilhado.
- Crons operacionais determinísticos usam `script` + `no_agent=true`.
- Em Discord operacional, preferir `deliver=local` quando o wrapper publica diretamente; stdout vazio evita duplicidade.
- Não usar cron com agente e `deliver=origin/all` para conclusão diferida pós-restart.
- O wrapper deve ficar abaixo do timeout do scheduler e transformar timeout/rate-limit em mensagem sanitizada + audit local.
- Threads fixas são registradas no contrato da operação. Nunca criar thread nova quando houver rota fixa aplicável.
- Intraday, Diário, criação e incidentes permanecem separados quando o contrato assim definir.
- Sem ação/erro, o cron fica silencioso, exceto relatório periódico explicitamente configurado.
- Alteração de cron exige readback `enabled/state/schedule/script/deliver/no_agent` e REPORT-INFRA.
- Cutover de credencial exige percorrer a cadeia completa `job → wrapper → módulo → account/operation contract → item do cofre → cache`. `last_status=ok` não prova uso do token novo quando a credencial antiga ainda existe, pois um hardcode residual pode manter o job verde. Validar cada consumidor ativo por import/readback do item, remover nomes antigos dos caches e executar dry-run live sem postagem/write antes de aposentar o rollback.

## Exclusão pontual de campanha solicitada pelo operador

1. Resolva operação e conta pelo contrato da conversa, valide autoridade e os gates aplicáveis. Faça descoberta restrita ao contrato e ao helper existente; não procure runners de criação, relatórios ou inventário global para um pedido somente de status.
2. Confirme a conta por GET (`id,name,currency,timezone_name,account_status`). Localize a campanha no edge `act_<account_id>/campaigns` com `filtering` por nome/wrapper e campos mínimos (`id,name,account_id,status,configured_status,effective_status,daily_budget,updated_time`). `CONTAIN` gera candidatos, não identidade: valide o token completo do wrapper/número e a conta, percorra a paginação se houver e exija alvo inequívoco antes de escrever. Não reutilize IDs de exemplos anteriores.
3. Separe exclusão manual de corte automático por performance. A exclusão nominal não cria um motivo D3 nem autoriza rejeitar/mover criativos, apagar arquivos, limpar mídia técnica, alterar budget ou criar substituta. Execute o pós-corte criativo somente quando o contrato e a proveniência realmente exigirem esse fluxo.
4. Use o helper `ares-meta-common.py` com a versão Graph vigente explicitamente configurada antes do import e o item de token da conta. Adquira a coordenação account-scoped vigente e releia o ID exato. Persista o mesmo request, autorização, origem, ID imutável e estado anterior; grave `IN_FLIGHT` com flush/fsync antes do write. Uma writer lease persistente sinaliza propriedade, mas não substitui o lock físico exigido pela operação.
5. Se o objeto já estiver no estado terminal aceito pelo contrato, conclua sem POST. Caso contrário, envie somente `graph_post_once(campaign_id, token, {'status': 'DELETED'})` e faça GET direto do mesmo ID. Aceite os literais terminais previstos pela operação, registre o literal real e confira que budget e identidade foram preservados. Timeout/resposta ambígua exige GET antes de qualquer retry; HTTP de sucesso sozinho não confirma exclusão.
6. Marque o request concluído e libere sua coordenação somente após readback terminal. Se persistir incerteza, mantenha o estado resumível e siga a recuperação vigente; não use um `finally` que marque a lease COMPLETE apesar de falha. Responda em uma linha curta com campanha, alias da conta e status confirmado na Meta, sem IDs técnicos ou trilha interna.

## Diagnóstico de campanha ativa sem dados

1. Separe três perguntas: os objetos estão habilitados, houve entrega no período e qual é a causa da ausência de entrega? Confirme conta/moeda/fuso e leia a campanha exata, seus conjuntos e anúncios por ID. Compare `configured_status` com `effective_status`; todos ACTIVE ainda não provam impressões ou gasto.
2. Consulte Insights na janela solicitada; se vier sem linhas, faça uma consulta bounded com `date_preset=maximum` para distinguir ausência no período de ausência no histórico disponível. Preserve a resposta vazia como evidência, não como causa nem prova de falha do relatório. Informe a janela consultada.
3. Expanda somente os alvos: `issues_info`, `ad_review_feedback`, `recommendations`, início/fim, lance e evento. Quando houver vídeo, leia `status` dos video IDs em batch. Inspecione UTMs/creative IDs apenas quando necessário, mantendo payloads completos no audit e evitando despejar asset feeds ou URLs de thumbnails na conversa.
4. Corrija somente uma divergência comprovada e autorizada, com pre-read e GET posterior. Se conjuntos/anúncios já estiverem configurados ACTIVE, não envie toggles redundantes para aparentar reparo. Ausência de erros retornados e vídeos `ready` não demonstram elegibilidade integral nem explicam o serving; não invente uma causa ou anuncie correção da entrega.
5. Execute os campos independentes autorizados — pausa, budget e agendamento — mesmo que a causa continue aberta. Congele o snapshot somente depois dos ajustes confirmados e diferencie no resumo: diagnóstico confirmado, mudanças concluídas, ativação agendada e causa ainda pendente. Mantenha o diagnóstico não resolvido no mesmo request/checkpoint com próxima ação concreta; nunca marque a recuperação de entrega como concluída apenas porque o job foi criado ou a campanha voltou a ACTIVE.

## Pausa imediata e ativação pontual agendada

1. Resolva conta e campanhas pelo contrato da conversa e confirme IDs, moeda, timezone e estado pela Meta. Interprete “meia-noite” como a próxima ocorrência de `00:00` no fuso operacional confirmado; informe a data civil explicitamente na conclusão.
2. Trate o pedido como **status-only** quando não houver outra mudança expressa: preserve o budget live de cada campanha, filhos, nome/data, tracking, mídia, copy e ciclo D1. Reativação não autoriza reinício operacional de D1 nem aplicação de um budget padrão. Valide que os filhos permitem a ativação; se estiverem pausados, não os altere implicitamente.
3. Faça o preflight mínimo e persista o request antes do write. Execute a pausa imediata solicitada e confirme-a por GET antes de dedicar tempo à auditoria global de agenda; discovery de scheduler não deve prolongar gasto evitável. Campanha já pausada não recebe POST redundante.
4. Congele o estado preparado por ID, incluindo budget individual, hierarquia, campos materiais e `updated_time`; confirme estabilidade com uma segunda leitura bounded. Em pedido combinado com budget nominal, aplique e confirme primeiro somente o ajuste autorizado e preserve o budget live dos demais alvos; o ativador deve validar os valores finais congelados e fazer apenas status write, sem reaplicar budgets ou confundir o próprio ajuste com drift externo. Reutilize helpers de transporte/readiness validados, sem herdar seus IDs, budgets ou ações históricas. Não reescreva `start_time` de conjunto já iniciado para simular reativação.
5. Audite a agenda global, faça backup e registre um one-shot determinístico. Se necessário, inicie fisicamente pouco antes do alvo e aguarde dentro do runner, sem adquirir a lane durante a espera. Escolha a menor contenção **dentro da janela compatível** e reserve timeout para espera, lock, API e readback. Não retome crons pausados como efeito lateral.
6. Teste bloqueio antecipado sem chamadas Meta, rejeição de drift de budget/hierarquia e replay concluído sem write. No horário alvo, adquira a lane account-scoped, faça novo pre-read, persista `in_flight`, aplique somente `status=ACTIVE` e confirme cada alvo por GET. Reconcilie tentativas ambíguas pelos IDs antes de qualquer retry; conclua somente quando todos os alvos estiverem confirmados.
7. Leia de volta o job exato, incluindo horário com offset, `enabled`, `no_agent`, script e destino/thread; vincule-o ao request e repita a auditoria excluindo somente esse próprio job. Registre checkpoint, inventário e REPORT-INFRA. Na conversa, diferencie **pausada agora**, **ativação agendada** e **ativação confirmada**; use bullets curtos com data, fuso e budgets preservados, sem IDs internos.

## Emendas a campanhas já agendadas

1. Releia o request, os IDs imutáveis e os jobs existentes antes de aplicar uma correção. Preserve literalmente o identificador corrigido e compare sua presença em todos os lotes: trocar um alvo por outro já agendado em data diferente não define se o operador quer mover a ativação ou repetir o reinício de D1. Pergunte somente sobre essa decisão; não crie uma segunda ativação, pausa intermediária ou novo ciclo por inferência.
2. Separe os campos independentes da emenda. Budget exato autorizado pode ser ajustado e validado enquanto a decisão de agenda aguarda resposta; preserve os horários anteriores e diga explicitamente que continuam vigentes. Não deixe a dúvida de um alvo bloquear os demais campos seguros, nem trate uma correção nominal como confirmação de uma agenda contraditória.
3. Para budget, adquira a lane da conta e compare o GET atual com o snapshot preparado. Preserve o valor anterior no audit, persista o desejo absoluto em unidade mínima e faça POST único somente nos alvos cujo budget difira. Se houver tentativa anterior, consulte o ID exato primeiro: valor desejado confirmado significa concluir a camada de readback, não repetir o POST.
4. Depois do GET correto, exija duas leituras estáveis de budget, nome, status, hierarquia e `updated_time`. Arquive o snapshot preparado anterior como emenda do mesmo request e atualize o congelamento para o estado autorizado novo, sob lock; assim o ativador futuro não interpreta a própria alteração de budget como drift externo. Preserve IDs, horário, criação/ativação, histórico do ciclo e checkpoints; emenda apenas de budget não reinicia D1 nem zera guardrails novamente.
5. Atualize somente os campos correspondentes no contrato e checkpoint, mantendo a decisão pendente separada. Rode o dry-run live do ativador de cada lote afetado e o validador de proveniência antes de confirmar a emenda. Não desabilite o gate de drift para acomodá-la e não recrie jobs cujo horário e escopo permanecem iguais. Na resposta, confirme primeiro o campo já validado e faça uma única pergunta curta sobre a decisão restante.

## Antecipação de execução e substituição autorizada

1. Quando o operador trocar uma condição futura por execução imediata, registre a supersessão antes de agir. Liste os jobs, identifique somente os vinculados aos IDs do pedido, pause/cancele os que ficaram obsoletos e confirme `enabled=false` por readback. Superseda também request, contrato e checkpoint anteriores, para impedir reativação tardia das fontes ou repetição do fallback.
2. Mantenha a autorização pontual separada de recorrência: não crie o monitor condicional que foi supersedido, nem retome watchers, escala ou criação diária pausados. Preserve budgets exatos e a ordem explícita de ações do operador.
3. Para “duplicar, ativar e depois excluir as originais”, use `meta-campaign-engine-v3` para as cópias com próximos números e UTMs próprias. Mantenha as fontes preservadas até concluir a criação, a validação semântica e a ativação das substitutas; erro parcial retoma os mesmos IDs, sem novas cópias.
4. Antes de excluir, releia as substitutas por ID: conta, budget, estrutura, filhos configurados ACTIVE, tracking correto e ausência de erro hard devem estar confirmados. Preserve o snapshot de entrega das fontes e aplique a exclusão nominal somente nos IDs autorizados, com GET terminal. Não transforme essa exclusão em corte D3, reprovação de criativos ou remoção de arquivos.
5. Reconcilie os novos usos na mesma linhagem criativa: registre campanhas/anúncios/creatives/vídeos antigos e novos, preserve Drive IDs, checksums, reserva e histórico. Duplicação com a mesma mídia não consome novos assets; não libere a fonte como candidata inédita nem altere contadores de tentativa sem critério canônico.
6. Faça readback final de originais, substitutas e agenda desativada. Responda com mapeamento fonte→cópia, budgets, status de campanha/conjunto/anúncio, exclusões e cancelamento do agendamento; informe o budget ativo e delta quando houver criação. Diferencie sempre ativação confirmada de gasto/impressões observados: a troca pode estar concluída sem a causa de serving estar comprovadamente resolvida.

## Onboarding de nova operação

1. Validar solicitante e autoridade.
2. Validar token e conta por API read-only sem expor segredo.
3. Criar `accounts/<account_id>.json` com referência 1Password e readback Meta.
4. Criar `operations/<operation_id>.json` inicialmente com `write_enabled=false`.
5. Registrar gestores, aliases e threads fixas.
6. Fechar objetivo, estrutura, naming, métricas, budgets e horários com o dono.
7. Criar skill específica da estratégia/operação somente após o contrato mínimo.
8. Implementar runner e wrappers determinísticos com testes.
9. Criar crons apenas em read-only/dry-run e validar entrega.
10. Liberar controlled-write ou autonomia somente por decisão explícita e readback.

## Operação Eggbev

O contrato vivo está em:

```text
/root/mgs-agent/data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json
/root/mgs-agent/data/ares/meta-ads/accounts/1034081997659047.json
```

A skill específica é `eggbev-us-cc-en-bot-operations`. Nas Fases 1/2 do ciclo ROAS, somente cortes/reativações de anúncios e a postagem dos relatórios estão autorizados em controlled-write fail-closed; campanha e ad set nunca recebem status write nessas fases. A Fase 3 Eggbev das 00:00 é uma exceção contratual separada: pode ajustar budget CBO para a escolha idempotente US$45/US$65 e garantir campanha, ad set e anúncios vencedores `ACTIVE`, inclusive quando pausados manualmente, sempre com pre-read e GET/readback. O guardrail separado de LEADS pode pausar campanha conforme contrato próprio. A escala automática genérica de +10% continua bloqueada; a autorização de budget da Fase 3 não a libera. Daily continua read-only sem cron. Campos ainda pendentes bloqueiam somente a ação dependente; nunca herdar regras de tráfego direto ou de outra operação.

## Segurança e autoridade

- Rodolfo, Geizian, Icaro, Isliago, Joe, Kelly e Nicolas podem operar Ares conforme o registry real.
- A autorização de Campaign Ops não libera automaticamente budget, billing, credencial ou produção fora do playbook.
- Nunca expor token, senha, cookie, payment data ou chave.
- Mudança de estratégia, exclusão permanente, billing ou ampliação de escopo exige o gate próprio.

## Referências atuais

- Layout de relatórios: `references/current-reporting-contract.md`
- Pitfalls operacionais: `references/current-operational-pitfalls.md`
- Histórico removido das rotas ativas permanece somente no Git/audit e não deve ser carregado como procedimento.
