---
name: discord-ops
description: "Operações do ecossistema de agentes MGS (Zeus/Atena): comunicação inter-agente via Discord, diagnóstico e reinicialização de gateway, versionamento de profiles (SOUL.md, skills) via git, roles managed, e hook git post-commit com notificação via webhook. Cobre IDs de canais/bots, DISCORD_ALLOW_BOTS, TTY check, sessão stale, rate limit, Message Content Intent, symlink pitfall e ciclo cron de sync."
tags: [discord, inter-agent, messaging, webhook, hook, git, roles, infra, notification, hermes, agent, restart, versioning, soul, profile, systemd, cron]
related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
---


## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Habilitar respostas em canais compartilhados

Quando Rodolfo pedir para habilitar agentes em um canal, separar o destino indicado da thread onde ele fez o pedido e distinguir acesso Discord, roteamento do gateway e regra de menção. Por padrão operacional, deixar o executor responsável responder sem menção no canal dedicado e Zeus por menção, sem habilitar resposta livre dos dois nem ampliar permissões de usuários. Validar comunicação real no destino antes de concluir; teste com @menção não prova resposta sem menção. Receita: `references/route-pack-02.md`, seção **Canal novo de relatórios: diagnóstico e habilitação**.

## Correção de respostas em outra thread

Quando Rodolfo pedir para ler uma thread e corrigir a resposta de outro agente, diagnosticar o pedido e a execução exatos antes de atribuir erro ao agente. Publicar a retificação na thread indicada, sem apagar ou se passar pelo autor original, e validar o conteúdo entregue; explicar apenas na conversa atual não satisfaz o pedido. Distinguir resposta corrigida, bloqueio resolvido e entrega operacional concluída. Após confirmação, reler o alvo e a continuidade da origem antes de escrever ou acionar o executor: confirmações do mesmo pedido em duas threads correspondem a uma única recuperação, não a duas execuções. Não descrever o relatório como retomado apenas porque existe uma sessão dona ou um payload de handoff preparado; exigir envio confirmado e atividade nova do executor. Receita de leitura, correlação de sessão e investigação de recusa: `references/route-pack-03.md`, seção **Investigar e retificar resposta de outro agente**.

## Orientar outro agente sem assumir a execução

Quando Rodolfo pedir para ensinar ou explicar ao agente como corrigir, executar nesta ordem:

1. Fixar o agente como único executor e dono da investigação, reparo autorizado, QA e entrega; Zeus orienta, não assume uma escrita paralela. Atualizar o checkpoint se a escolha do executor substituir um plano anterior.
2. Validar os pré-requisitos recuperáveis em leitura e consultar o procedimento técnico relevante antes do envio. Quando o pedido for equiparar a capacidade técnica do executor, comparar ferramentas habilitadas, referências permitidas e receitas disponíveis e exercitar a operação segura pelo runtime/perfil dele; sucesso de Zeus não comprova acesso do destinatário. Se faltar uma receita, disponibilizar procedimento ou helper compartilhado testado, em vez de repetir “você tem autonomia”. Fornecer próxima ação concreta, fontes, alvos, teste de aceite e condições de parada, sem inferir concessão global de privilégios.
3. Publicar na origem solicitada e conferir o conteúdo entregue. Se Rodolfo pedir resposta antes do envio, responder primeiro se o caminho está comprovado ou ainda é uma hipótese; não prometer que instrução equivale a capacidade de executar.
4. Deixar descoberta, preparação local e etapas não críticas já autorizadas com o agente, sem aprovação rotineira de Zeus nem coordenação devolvida a Rodolfo/Raquel. Isolar somente a ação realmente protegida que precise de confirmação específica, explicando seu efeito e preservando o restante do trabalho.
5. Ao receber nova evidência, avançar da última camada comprovada. Não reiniciar o ciclo com a mesma busca, nova cobrança de autonomia ou repetição do mesmo pedido de confirmação sem mudança material. Se o pré-requisito continuar indisponível, dar uma conclusão única com fato, lacuna e decisão necessária; não apresentar outra orientação como recuperação.

Não transformar envio de instrução em implantação autorizada, nem afirmar que o método funciona ponta a ponta apenas porque o acesso administrativo passou. Distinguir instrução entregue, execução observada e resultado aceito.

## Acompanhar execução de outro agente

Quando Rodolfo pedir para acompanhar, observar a execução até a entrega ou um bloqueio decisório concreto, sem assumir o writer nem enviar cobranças repetidas ao agente:

1. Ler mensagens posteriores ao último checkpoint e conferir os artefatos que sustentam o avanço; ACK, indicador de atividade e resumo do próprio agente não comprovam aceite.
2. Identificar o pacote e o recibo finais. Não somar testes de candidatos substituídos nem promover fixtures, lint ou revisão local a recuperação certificada em produção.
3. Se a revisão mudar a finalidade do pacote, explicitar a diferença antes de recomendar autorização: inspeção/exportação não é reparo, e sua aprovação não libera escrita posterior.
4. Para acompanhamento curto, manter observação limitada em foreground. Só prometer continuidade após encerrar o turno quando existir um mecanismo durável configurado e verificado; não criar cron apenas para responder uma consulta pontual.
5. Encerrar com o resultado ou com fato, causa comprovada/lacuna, recomendação e decisão exata pendente. Não pedir novamente uma confirmação igual sem mudança material, nem apresentar monitoramento concluído como reparo concluído.

## Corrigir documentação de escopo de outro agente

Quando Rodolfo corrigir uma recusa e pedir atualização da documentação, compare primeiro a regra específica do agente com o gate executável; não transforme automaticamente a correção em ampliação de permissões. Para Ares, consulte `context/ares-asset-scope.md`, o catálogo positivo SB e `mgs-domain-scope.py list --agent ares` antes de exigir cadastro institucional adicional. Uma consulta por vertical, como SHEIN, não fornece nem exige por si só um domínio explícito: comece pelo catálogo autorizado e confirme a classificação com evidência operacional.

Atualize a fonte canônica, o trecho conflitante do SOUL vivo e seu espelho versionado; confira igualdade dos espelhos, limite de contexto e testes do gate. Quando uma delegação volta a ser ignorada apesar de já constar da skill, compare a regra sempre carregada no SOUL com as referências sob demanda: uma fonte correta fora do contexto não elimina uma instrução ampla de escalonamento presente no prompt. Corrija essa precedência sem ampliar permissões nem editar skills de outro agente sem a confirmação crítica exigida. Preserve pausas editoriais pedidas pela gestora e separe falta de capacidade técnica de falta de autoridade. Registre a supersessão pelo controlador institucional quando a regra mudar. Antes de encerrar uma correção de autoridade/comportamento:

1. **Validar a fonte e a montagem do contexto.** Conferir identidade/permissão vigente, fonte canônica, SOUL vivo/mirror e carregamento pelo resolver nativo, verificando ausência de truncamento. Testes de texto e loader comprovam persistência e montagem, não adesão do modelo nem conclusão da tarefa recusada.
2. **Verificar a ativação nas conversas existentes.** Inspecionar no runtime implantado a construção do prompt, a assinatura de reutilização do agente e os pontos de invalidação; não deduzir hot reload da simples edição do arquivo. Se o prompt estiver congelado por sessão, distinguir um contexto recém-construído da sessão já aberta, que pode continuar usando os bytes anteriores.
3. **Delimitar a intervenção realmente necessária.** Não chamar reinício de gateway de obrigatório apenas porque uma sessão pode estar desatualizada. Antes de recomendar recarga localizada, comprovar que o mecanismo nativo existe, preserva histórico/ownership e efetivamente reconstrói o contexto; uma possibilidade não testada não é procedimento validado. Não executar campanhas, resetar sessões, interromper trabalho ativo ou acordar o agente apenas para provar uma atualização documental.
4. **Responder com o escopo exato de conclusão.** A perguntas como “foi tudo corrigido?” ou “precisa reiniciar?”, dizer primeiro o que está comprovado e, na mesma resposta, qual camada continua sem validação. Não abrir com um “sim” irrestrito quando só a documentação passou, nem apresentar atualização de contexto apenas recomendada como já executada. Separar documentação persistida, gate validado, contexto ativo atualizado e comportamento operacional observado.

Receita e diagnóstico de recusas: `references/route-pack-03.md`, seção **Investigar e retificar resposta de outro agente**.

## Consolidar rotas funcionais na mesma thread

Ao consolidar criação e clone, preserve os contratos separados e selecione o modo pela intenção do pedido, não apenas pelo ID da thread. Reconcile registry, consumidor, contratos, prompts, verificadores e config vivo/versionado; testes de unicidade de destinos precisam admitir compartilhamento explicitamente autorizado. Antes do fechamento, releia decisões posteriores no destino antigo: ele pode ter recebido outro propósito autorizado em paralelo. Não sobrescreva esse adendo nem trate variação de serialização YAML como drift semântico. Receita: `references/functional-route-consolidation.md`.

## Resumos executivos de threads para Rodolfo

Quando Rodolfo pedir para resumir threads ou disser que há informação demais, leia as fontes e entregue uma síntese para decisão, não outro relatório técnico:

1. Abra com uma frase dizendo o assunto comum e o impacto prático.
2. Agrupe por problema ou decisão, separando **Problema, Solução recomendada e Quem decide**; não resuma mensagem por mensagem.
3. Diferencie publicação, validação pública e conclusão. Não trate pendência de apresentação como texto errado nem some grupos sobrepostos.
4. Feche com o que já foi feito, o que continua pendente e a recomendação operacional. Use poucos números essenciais e links das fontes; deixe hashes, IDs internos, testes e caminhos fora do corpo.
5. Informe que o estado vem dos últimos registros consultados quando não houve verificação produtiva nova. Não execute nem interprete o pedido de resumo como aprovação.

O quadro de cobertura de leitura é apropriado quando ele pede auditoria ou pergunta se tudo foi lido; não o use como resposta padrão a um pedido de resumo simples. Receita de leitura e resolução da origem: `references/route-pack-03.md`.

## Delegação de decisões e comunicação na origem

Quando Rodolfo transferir a decisão a uma gestora, separe **autoridade delegada**, **aprovação do plano** e **execução validada**. Persistir a autoridade não aprova automaticamente os planos pendentes. Consulte a fonte canônica atual, não uma lista de permissões copiada para a skill. Depois, esclareça as pendências na thread operacional indicada e mencione a pessoa solicitada com allowlist explícita de usuários; não acorde outro bot apenas para anunciar a decisão. Preserve limites críticos, escopo por área e acesso privado. Fluxo de persistência, publicação e readback: `references/route-pack-03.md`, seção **Comunicar delegação e encaminhar decisões pendentes**.

## Authority corrections in ContentOps handoffs

For Raquel editorial/selective-cache requests, resolve the current `data/atena/editorial-manager-authority.json` before applying a historical CEO-only file-cache gate. The confirmation authority for proven regenerable selective cache is delegated there; do not narrow a permanent CEO correction to the example manifest or repeatedly request CEO approval for equivalent ContentOps work. Keep exact-target approval, backup/canary/readback, general file-deletion/credential/runtime/Finance/Router limits, and the current executor. A governance-only handoff does not transfer execution or authorize a parallel writer. Persist the supersession and correct Zeus-owned pending checkpoints so an obsolete hold cannot revive on resume.

## Operational route packs

- **Referências recentes → Escopo por agente/thread antes de reportar pendências** → `references/route-pack-01.md`
- **Mentions cross-agent em canal de outro agente → Challenges por IP de datacenter em fluxos Ares** → `references/route-pack-02.md`
  - Cutover de política em sessão nova, sem produção, com readback de `state.db` → `references/cross-agent-session-policy-cutover.md`
- **Recuperar e consolidar continuidade de thread grande → Novo agente Discord/Hermes — bootstrap de bot, token e service** → `references/route-pack-03.md`
- **Enviar arquivos grandes/anexos no Discord → Formato REPORT-INFRA (Atena/Ares → Zeus)** → `references/route-pack-04.md`
- **Excluir alertas/mensagens em lote com HTTP 429** → `references/discord-batch-message-deletion-rate-limits.md`
- **Processamento Zeus de REPORT-INFRA** → `references/route-pack-05.md`
- **Processamento Zeus de REPORT-INFRA com cron Hermes de outro profile → Alternativa Operacional** → `references/route-pack-06.md`
- **SEÇÃO C — Hook git post-commit com notificação Discord → Política MGS de tool progress no Discord** → `references/route-pack-07.md`
- **Gateway routing/restart incident reference → Channel permission overwrites and narrow delegation** → `references/route-pack-08.md`
- **Adding a user to a private Discord thread → Separar canais privados/diretoria e canais de equipe → Usuário autorizado silencioso por drift entre registry/config/.env → Diagnóstico de título ruim em auto-thread** → `references/route-pack-09.md`
- **Regra MGS: renomear thread nova uma vez; nunca renomear thread já aberta → Pitfall crítico: função segura pode estar sobrescrita por duplicata posterior** → `references/route-pack-10.md`
- **Correção preferida: título IA uma vez após a primeira resposta → Patch local `busy_input_mode` em gateway** → `references/route-pack-11.md`
- **Pitfalls (restart) → Aviso antes de thread ficar oculta por auto-archive** → `references/route-pack-12.md`
- **Threads antigas continuam abertas na sidebar de usuários adicionados → SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)** → `references/route-pack-13.md`
- **Quando usar → Solução implantada em produção — cópia periódica via cron** → `references/route-pack-14.md`
- **Diagnóstico rápido: symlink vs arquivo real no git → Política de extensão de skills** → `references/route-pack-15.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
