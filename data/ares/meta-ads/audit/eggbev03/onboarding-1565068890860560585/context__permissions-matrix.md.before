# MGS OS — Matriz de Permissões e Autoridade

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`
> Regra: permissões reais continuam em `data/authorized-users.json`.

## Níveis de decisão

```text
Nível                 Descrição                                      Exemplo
-------------------- ---------------------------------------------- ------------------------------
Operacional           Execução dentro de playbook aprovado            REC/P1, artigo SEO, QA.
Supervisão humana     Humano da área valida/coordena                  Raquel, Geizian, Kelly.
Orquestração Zeus     Roteamento, auditoria, alerta, coordenação      autorização, incidente.
CEO / Rodolfo         Decisão crítica/final                           budget, credencial, produção.
```

## Matriz por ação

```text
Ação                                  Executor/proponente       Aprovação necessária
------------------------------------- ------------------------ ----------------------
Criar REC/P1                          Atena / Raquel           Playbook/Raquel.
Editar REC/P1                          Atena / Raquel           Playbook/Raquel.
Publicar WordPress editorial           Atena                    Regra editorial.
Criar artigo SEO                       Atena / Raquel           Playbook/Raquel.
Criar/tratar criativo                 Ares / Kelly humana      Kelly/gestor/Rodolfo.
Gerenciar criativo no Drive            Ares                     Escopo aprovado.
Reservar/conciliar Meta × Drive        Ares                     Antes de seleção/write.
Subir/gerenciar campanha               Ares / gestores          Autorização Ares vigente.
Alterar budget                         Ares / gestores          Rodolfo/Geizian.
Configurar ChatPion/DigitalTrChat       Rodolfo/Geizian/gestores Ares não participa.
Configurar quiz/SMS Funnel              Rodolfo                  Ares não participa.
Configurar pixel                       Rodolfo/Tech             Rodolfo.
Montar site WordPress                  Rodolfo/Tech             Rodolfo.
Analisar ROI                           Ares / Zeus report       Rodolfo/Geizian.
Cobrar tarefa pendente de gestor        Ially                    Geizian/Rodolfo se escalar.
Ajustar blocos AdOps                   Smart Bidding/gestor     Rodolfo/gestor.
Fechamento financeiro                  Rodolfo                  Rodolfo.
Autorizar usuário externo              Zeus                     Rodolfo confirmado.
Alterar authorized-users.json           Zeus                     Rodolfo confirmado.
Ler credencial do 1Password             Zeus/agente autorizado   Só uso interno; não exibir.
Alterar script/cron produtivo           Zeus/Tech                Rodolfo se risco.
Restart gateway/agente                  Zeus/Tech                Rodolfo se sensível/crítico.
Remover/mover arquivo estrutural         Zeus/Tech                Rodolfo aprovado.
Criar agente novo                       Zeus/Rodolfo             Rodolfo.
```

### Autonomia de Raquel — conteúdo e dependências técnicas localizadas

Autoridade: Rodolfo Mattei, mensagem `1564661630766424096`, thread `1564660286164570125`, adendo `1564671680444370955` e correções permanentes `1564705532424495105` / `1564706598130032710` na origem Atena `1564289742567112795`. Fonte canônica única do escopo: `data/atena/editorial-manager-authority.json`; identidade e acesso em `data/authorized-users.json`. Supersede a exigência de nova decisão do CEO para toda dependência editorial e a interpretação que reservava ao CEO cada exclusão de arquivo-cache regenerável seletivo.

- Raquel Oliveira (`1496254952501280974`) pode conversar, decidir, solicitar e aprovar a rotina editorial e as correções técnicas localizadas, seguras e reversíveis necessárias à entrega pública em portais MGS autorizados, inclusive categorias/traduções/menus, representações de cache/sitemap, idioma exibido, datas, bios e layout pontual apresentados nas threads `1564508692701909014` e `1564558610263187547`, dentro dos limites da fonte canônica.
- Atena mantém conteúdo e QA final; Zeus executa o apoio técnico quando Raquel autorizar o plano delimitado na origem Atena. Não exigir novo OK editorial ou técnico não crítico do CEO para o mesmo recorte. Esta delegação não aprova automaticamente os pacotes pendentes e não concede acesso global ao canal privado Zeus.
- Raquel pode solicitar e autorizar permanentemente limpeza/invalidação e exclusão seletiva de cópias comprovadas de cache regenerável necessárias a ContentOps, neste pedido e nos futuros equivalentes. Sua aprovação dos alvos delimitados é a confirmação válida nesse recorte; não exigir novo OK do CEO a cada pedido nem limitar a correção aos 14 arquivos ratificados. Validar URL/camada/path/hash/owner/no-symlink, backup, canário, executor único e readback da URL normal. A restrição atual continua sendo URLs específicas, nunca purge global/site/host/wildcard/prefixo; duas homes ES ou outros alvos não entram por inferência no manifesto14.
- O Critical Subset geral de `AGENT.md` permanece protegido fora da delegação específica de cache regenerável seletivo acima. Exclusão geral de arquivos/diretórios, credenciais, permissões, billing/budget, campanhas, monetização, runtime crítico, upgrades, locale global, migração de acervo e mudanças amplas não foram delegados por essa correção. Dash financeira e Router preservam a regra exclusiva abaixo. Não tratar a confirmação delegada à gestora para cache como isenção geral de exclusão de arquivos.

### Delegação permanente — membros dos canais Ares e sites SB

Autoridade: Rodolfo Mattei, mensagem `1564748349431881972`, thread `1564744929660637264`. Fonte canônica: `data/ares/sb-site-member-authority.json`; ponteiro de acesso em `data/authorized-users.json#/agents/ares/authorization_policy/sb_site_member_requests`.

Zeus pode autorizar, sem novo OK de Rodolfo, pedidos explícitos de qualquer membro humano com acesso efetivo comprovado ao canal/thread de origem do Ares sobre qualquer site cadastrado na Smart Bidding corporativa, inclusive novos cadastros ou companies ausentes do snapshot atual. Validar ID individual, participação/permissões live e a correspondência exata publisher → host; se o snapshot estiver desatualizado, Zeus pode reconciliar o alvo SB comprovado sob esta delegação, sem exigir nova autorização do CEO. Não promover todos os membros à whitelist global: registrar o grant individual limitado à origem, ao site e ao pedido, com audit.

Esta autorização de solicitante/site não muda o executor/área do agente nem libera contas Meta fora da operação, partições de campanhas, budgets sem autoridade específica, credenciais, billing, Critical Subset, permissões Discord ou acesso privado Zeus/Atena. Dash financeira e Router mantêm o gate exclusivo de Rodolfo. Não alterar o gateway para wildcard nem tratar a persistência desta política como prova de que um usuário novo já passou pelo filtro de transporte.

### Exceção ativa por operação

- **Eggbev-US-CC-EN-BOT / Eggbev-US-CC-EN-01-G006:** por decisões explícitas de Rodolfo em 30/08/2026 e 31/08/2026, Nicolas pode definir, reduzir ou aumentar budgets de campanha — inclusive a baseline de USD45 — e autorizar, por pedido, início imediato sem schedule para criação ou clone, sem nova aprovação do Rodolfo. Cada write continua exigindo instrução explícita do Nicolas ou política operacional aprovada, resumo final/OK do pedido, pré-leitura e readback Meta. O início padrão permanece no próximo dia às 00:00 ET; pedidos imediatos exigem request ID allowlisted e horário Meta-safe atualizado no execute. A delegação não autoriza billing, `account_spend_limit`, credenciais, automação recorrente nem escala automática sem regra própria aprovada.
- **SHEIN-US-DIRECT / `shein-g001`…`shein-g006`:** a decisão vigente de Rodolfo na thread `1557274000680288307` supersede a restrição de 11/09/2026 ao gestor titular como único solicitante. Toda pessoa humana com permissão efetiva de comunicação no canal pai listado e na thread de origem pode conversar, solicitar e autorizar Campaign Ops sobre as contas/perfis vinculados àquele canal: criação, duplicação, clone, relatórios, organização de threads, otimização, pausa/reativação, exclusão/arquivamento, definição/alteração de budget, schedule e ativação. O G00N identifica a partição da conta; não restringe o remetente ao titular. Geizian, por exemplo, não deve ser recusado no G005 por ser titular do G002, se a permissão do canal/da thread estiver confirmada. Fonte única da elegibilidade: `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json#/channel_authorization_policy`. Validar ID real, canal pai real e permissões live (roles + overwrites por membro, acesso a thread privada), relendo antes de criação/ativação; não aceitar nome exibido ou autodeclaração como prova. A regra é restrita aos seis canais e suas threads; não promove usuários globalmente nem altera `authorized-users.json`/permissões Discord/outros agentes. O pedido deve trazer valor/moeda exatos quando houver budget e identificar os objetos dependentes; Ares faz pre-read, menor write e GET. Não é exigida nova aprovação de Rodolfo para o budget de campanha dentro desse recorte delegado. Billing, `account_spend_limit`, credenciais, ownership, permissões de app, pixel/CAPI, automação recorrente sem política própria e contas/perfis fora da partição do canal continuam excluídos; Critical Subset permanece.
 Geizian (`321263240782807040`) tem autoridade integral de Campaign Ops nos seis canais SHEIN e nas threads deles, reafirmada por Rodolfo na mensagem `1558225355930861649`; não exigir aprovação exclusiva do CEO para uma retomada/ativação tardia explicitamente autorizada por ele. O review de atraso segue a mesma elegibilidade live do canal, na origem do pedido, via `channel_authorization_policy.late_recovery_review`, preservando SLA/relógio original, QA, request, IDs, budget, lance e todos os limites críticos.

### SHEIN — SLA de desempenho não expira autorização

Autoridade: Rodolfo Mattei, mensagem `1564747521354629371`, thread `1564746043768311910`, após diagnóstico `1564746600012582913`. Fonte canônica: `data/ares/meta-ads/engine-v3/config.json#/shein_execution_sla`. Esta decisão supersede somente a exigência de nova confirmação por atraso técnico além do alvo E2E de 144s: `late_activation_allowed=true`. Manter o relógio original e registrar o atraso, mas retomar o mesmo pedido/IDs já autorizados sem nova pergunta ao gestor. Autoridade live, QA semântico/renderizado, manifests, budget/lance, horário comercial aprovado, quota, pre-read/readback e Critical Subset continuam obrigatórios. Review de divergência material de horário/escopo permanece separado; não ativar campanhas históricas por efeito desta manutenção.

## Dash financeira e Dash do Router — autorização exclusiva de Rodolfo

Autoridade: Rodolfo Mattei, mensagem `1557426794137653248`, thread `1557406793603358742`. Chave canônica: `permissions.ares-atena.finance-router-write`.

- Ares e Atena não podem alterar absolutamente nada na Dash financeira nem na Dash do Router sem pedido explícito de Rodolfo dirigido à ação e ao sistema em questão.
- O bloqueio abrange interface, dados, cadastros, valores, regras, rotas/redirecionamentos, código, arquivos, banco, APIs de escrita, configurações, deploys, integrações e automações que modifiquem esses painéis, inclusive por ferramentas, scripts ou terceiros.
- Pedidos de gestores, Geizian, Raquel ou outros agentes; posse de credencial; autorização genérica de campanha/editorial; alertas; diagnóstico; correção automática; e políticas antigas não autorizam essas alterações. Esta restrição prevalece sobre autonomia genérica de write/reparo nesses dois sistemas.
- Somente o pedido explícito de Rodolfo abre exceção no escopo solicitado; não libera alterações futuras ou adjacentes. Critical Subset e demais gates de segurança continuam obrigatórios.
- Consulta/read-only continua sujeita às permissões e limites de confidencialidade existentes; esta regra não concede novo acesso de leitura. Se uma tarefa exigir alteração sem o pedido de Rodolfo, preservar o estado, explicar o bloqueio e encaminhar a ele/Zeus, sem executar.
- A regra restringe Ares e Atena. Não bloqueia os fluxos financeiros/Router do Zeus que Rodolfo já autorizou, nem altera as permissões técnicas dos sistemas por si só.

## Segurança

Nunca expor senhas, tokens, application passwords ou qualquer credencial em texto claro no chat. Credenciais vivem no 1Password. Autorização externa exige confirmação do Rodolfo. Acesso permanente é exceção. Mudanças em produção devem ser pequenas, auditáveis e reversíveis.

## Níveis de acesso externo

```text
Nível        Uso
----------- -------------------------------------------------------------------
Full         Acesso permanente/equipe; exige decisão explícita de Rodolfo.
One-time     Acesso só para pedido atual; expira após uso.
Limited      Pode conversar/solicitar, mas não executar pipelines sensíveis.
Denied       Pedido negado.
```

## Escalonamento obrigatório

```text
Tema                                    Escalar para
-------------------------------------- ----------------------------------------
Dinheiro/budget                         Rodolfo/Geizian conforme área.
Credenciais/tokens/API                  Rodolfo.
Acesso permanente                       Rodolfo.
Produção crítica                        Rodolfo se risco relevante.
Remoção/migração estrutural             Rodolfo.
Política operacional                    Rodolfo.
Agente novo                             Rodolfo.
Risco jurídico/financeiro/reputacional  Rodolfo.
Erro crítico de agente/Hermes/VPS       Zeus reporta para Rodolfo.
```

## Regras de execução por Zeus

```text
Ação de Zeus                            Regra
-------------------------------------- ----------------------------------------
Responder status operacional             Pode consultar fontes e responder.
Autorizar/negar usuário                  Confirmar com Rodolfo antes de aplicar.
Editar JSON de permissões                Só após confirmação explícita.
Notificar agente afetado                 Após decisão aplicada.
Registrar audit log                      Obrigatório em autorização/incidente.
Ler credencial                           Apenas para uso interno operacional.
Exibir credencial                        Proibido.
Mudar runtime/prod                       Validar escopo; pedir aprovação se risco.
```
