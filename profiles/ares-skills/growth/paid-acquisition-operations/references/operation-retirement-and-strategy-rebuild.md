# Retirar uma operação e reconstruir a estratégia

Use quando um site/conta deixa de rodar e Ares precisa remover a operação do escopo ativo, preservando auditoria, antes de criar outra operação com estratégia materialmente diferente.

## Princípio central

“Fora do escopo” não significa apagar evidência. Separe sempre:

```text
Classe       Destino
-----------  ------------------------------------------------------------
Ativo        Remover das rotas/loaders/crons/defaults executáveis
Histórico    Preservar em retired/archive, audit, reports, logs e Git
Global       Não alterar se pertence a outro agente, site ou subsistema
Novo         Criar fail-closed, sem herdar regras por semelhança
```

## Fluxo seguro

### 1. Congelar e inventariar

1. Confirmar owner, operação antiga, nova operação, conta, estratégia e autoridade.
2. Fazer readback real de conta/API, configuração Hermes, crons e fontes canônicas.
3. Inventariar separadamente:
   - config/SOUL e mapas operacionais;
   - permissões e registry de usuários;
   - operações, contas, rules, metrics, policies, permissions e state;
   - skills e referências carregáveis;
   - scripts, wrappers e testes específicos;
   - crons ativos, pausados e concluídos;
   - knowledge registry/checkpoints e memória específica da operação.
4. Classificar cada ocorrência como ativa, histórica ou global. Busca textual ampla é só inventário; nunca é autorização para apagar tudo que casar com o nome.

### 2. Retirar runtime antes dos dados

1. Desabilitar/remover crons específicos e validar a lista final.
2. Remover a rota da allowlist/prompt/auto-add pelo comando canônico de configuração; não editar `config.yaml` manualmente.
3. Remover a skill específica obsoleta ou absorver apenas os guardrails realmente genéricos.
4. Arquivar runners, wrappers e testes exclusivos fora dos diretórios executáveis.
5. Neutralizar defaults escondidos em helpers genéricos:
   - nenhuma conta/token/operação implícita;
   - item 1Password obrigatório por conta/argumento;
   - ausência do item falha antes da chamada externa.
6. Compilar/smoke-testar os helpers alterados.

### 3. Arquivar dados com manifest

Mover contratos e state para uma árvore `retired/<operation>/`, preservando a hierarquia relativa. Gerar manifest com:

```text
schema/status/authorization/reason/timestamp
source → retired_path
bytes e checksum quando aplicável
total por categoria
política de histórico
```

Verificação obrigatória:

- todo destino listado existe;
- nenhuma source ativa permanece;
- soma por categoria = total de mappings;
- audit/reports/logs históricos continuam preservados.

Se um state reaparecer durante a migração, fazer readback e comparar destino/checksum. Se o destino não existir, mover e acrescentar ao manifest; se existir, nunca sobrescrever sem reconciliar a diferença.

### 4. Superseder conhecimento, não reescrever história

- Atualizar a fonte canônica da rota nova.
- Registrar a nova chave/decisão no knowledge registry.
- Marcar a decisão antiga como `superseded` apontando para a nova.
- Não alterar procedimentos globais de outro agente/subsistema só porque citam a operação antiga.
- Remover da memória do Ares apenas regras operacionais específicas que poderiam voltar a ser tratadas como ativas.

### 5. Criar a substituta fail-closed

Materializar primeiro:

1. conta com alias, token reference, currency/timezone/status e auth audit read-only;
2. operação com owner/manager, canal, threads fixas e estratégia;
3. `write_enabled=false`, `activation_enabled=false`, `scheduler_jobs={}`;
4. todos os campos não decididos como `pending_review`;
5. skill específica da estratégia/operação em versão draft;
6. proibição explícita de herdar regras de tráfego direto ou de operação anterior.

Não criar runners/crons de produção enquanto objetivo, optimization, métrica, estrutura, budget, horários, autoridade e recovery estiverem pendentes.

### 6. Conduzir a revisão na ordem certa

Perguntar em sequência, começando pelo que altera toda a arquitetura:

1. fluxo real do usuário e evento final;
2. objetivo/destination/optimization Meta;
3. métrica principal, fonte, join key e atraso;
4. estrutura, público, placements e naming;
5. budget/bid/learning;
6. criativos e replacement;
7. Intraday/Diário;
8. thresholds, writes, ativação e autonomia.

Evitar despejar um formulário inteiro. Registrar cada decisão no contrato vivo antes da próxima camada.

## Validação final da fase de migração

```text
Referências antigas em caminhos executáveis Ares     0
Rotas/crons específicos antigos                      0
Manifest retired: destinos ausentes                  0
Manifest retired: sources ainda ativas               0
Nova conta: auth read-only                            HTTP 200
Nova operação: writes/activation                      false/false
Crons novos antes do contrato                         0
Threads fixas                                         todas observadas/registradas
Knowledge registry                                    antiga superseded; nova active
Skills runtime × mirror                               sincronizados
REPORT-INFRA e checkpoint                             readback OK
```

## Pitfalls

- Não trocar labels dentro do contrato antigo e chamá-lo de operação nova.
- Não usar conta/credential antiga como fallback.
- Não copiar thresholds, ROI, CBO/ABO, cost cap ou cron entre estratégias.
- Não deletar audit/report/log por uma busca textual ampla.
- Não reportar “zero ocorrências” a partir de uma varredura vazia/suspeita; repetir com estratégia independente e contagem programática.
- Não considerar POST de relatório/registro concluído sem readback do target.
