# Família de estratégia, contratos e projeção de threads

Use quando vários sites/contas compartilham o mesmo mecanismo de aquisição, mas precisam manter identidade, valores, autoridade, runtime e estado isolados.

## Modelo em quatro camadas

1. **Skill da família:** procedimento reutilizável, rotas funcionais, gates, recovery e verificação. Não contém nomes de consumidores, contas, IDs ou valores operacionais.
2. **Contrato da família:** schema, mecanismos, campos obrigatórios, precedência e política de onboarding/projeção.
3. **Consumer registry:** liga cada operação ativa ao contrato, conta, threads e prompts próprios. Canal preparado não significa consumidor ativo.
4. **Contrato da operação:** identidade, valores, overrides, authority, runners, states, audits, schedules e flags de write.

Princípio: copiar o mecanismo; parametrizar a operação; nunca copiar estado técnico ou autorização da fonte.

## Classificação de mudanças

### Mudança de família

Altera um mecanismo compartilhado: sequência de gates, semântica de rota, contrato de readback, recovery, aprovação ou projeção.

- atualizar skill e contrato da família;
- validar todos os consumidores ativos;
- projetar a rota afetada e `rules` em cada consumidor;
- não copiar valores ou state entre operações.

### Mudança de operação

Altera threshold, budget, horário, Page, evento, layout, hold, cron, fonte, authority ou capability de um consumidor.

- atualizar somente o contrato/runtime dessa operação;
- projetar a rota funcional afetada e `rules` dessa operação;
- preservar os demais consumidores sem alterações;
- superseder explicitamente a versão anterior.

Se uma mudança específica revelar um procedimento reutilizável, promover somente o procedimento; o valor continua operation-scoped.

## Projeção canônica em threads

Uma alteração durável aprovada inclui sua projeção Discord no mesmo request.

1. Persistir e validar a fonte canônica.
2. Resolver os consumidores pelo escopo `family` ou `operation`.
3. Sincronizar prompt-fonte, config versionado e config ativo.
4. Atualizar a rota funcional e `rules`.
5. Editar somente a mensagem de projeção persistida e pertencente ao bot; criar uma se ainda não existir.
6. Antes de POST, procurar conteúdo idêntico recente para reconciliar resposta perdida e evitar duplicata.
7. Fazer GET e comparar conteúdo/autoria exatos.
8. Persistir message ID, digest e audit.

O sincronizador não apaga mensagens. Histórico humano, eventos de sistema e rotas permanecem preservados; limpeza destrutiva é uma operação separada com autorização própria.

## Migração segura de uma operação existente

1. Inventariar skills, contratos, prompts, config, runners e testes.
2. Criar checkpoint antes do primeiro write estrutural.
3. Materializar skill/contrato da família sem identidade de consumidor.
4. Criar consumer registry com somente operações comprovadamente ativas.
5. Adicionar binding explícito ao contrato da operação.
6. Trocar rotas/prompts para a skill da família.
7. Converter skills antigas em redirects de compatibilidade, sem manter regras duplicadas.
8. Sincronizar config por mecanismo que preserve o YAML e faça readback do valor resolvido.
9. Rodar regressões antes da primeira publicação Discord.
10. Publicar projeções idempotentes, fazer GET e repetir o comando para provar `action=none`.
11. Corrigir blocos antigos controlados pelo bot quando forem apresentados como vigentes; caso contrário, marcá-los superseded.
12. Registrar knowledge/checkpoint, inventário, REPORT-INFRA e commit escopado.

## Onboarding posterior

Nova operação começa fail-closed. Revalidar conta, authority, Pages, UTMs, pixel/evento, JSON, structure, modes, thresholds, horários, reports, holds e crons. Primeiro read-only; depois canário; depois controlled-write; automação por último.

## Pitfalls

- Uma skill por site duplica o mecanismo e cria drift.
- Uma skill de família que contém threshold, budget ou conta específica deixa de ser reutilizável.
- Não transformar canal preparado em consumidor ativo sem contrato/readiness.
- Não usar valor ausente de uma operação como autorização para herdar o de outra.
- Não repetir POST de projeção após timeout sem reconciliar mensagens recentes.
- Não reformatar um config YAML inteiro para trocar um único prompt; substituir o nó exato e validar parse/readback.
- Não remover compatibilidade histórica antes de atualizar prompts, registries e testes consumidores.

## Verificação

- skill/contrato da família sem identidade de consumidor;
- uma operação resolve para um contrato e conjunto de threads;
- rota funcional e `rules` sincronizadas;
- mensagem de projeção Ares com GET/readback e digest;
- segunda execução idempotente sem nova mensagem;
- uma versão ativa por chave canônica;
- testes da família e regressões da operação aprovados;
- zero write de campanha/cron durante a reestruturação, salvo autorização separada.
