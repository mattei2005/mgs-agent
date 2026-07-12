# Auditoria transversal de dependências de agentes fora dos profiles

Use quando um agente será consolidado, renomeado ou desativado e o pedido exigir uma auditoria **read-only** além de `/root/.hermes/profiles/`.

## Escopo obrigatório

1. **Contexto e governança**
   - `context/`: mapas operacionais, rotas, áreas, permissões, sources-of-truth e modelo operacional.
   - `docs/`: inventário estrutural, crons, pendências e documentação corrente.
   - Classificar changelogs e documentos datados como históricos; não reescrevê-los retroativamente.

2. **Runtime externo ao profile**
   - `/etc/systemd/system/<agent>-gateway.service`, estado active/enabled e processo real.
   - root crontab, `/etc/cron*` e jobs Hermes relevantes, sem exibir payloads/segredos.
   - scripts genéricos que enumeram agentes: restart, update, health, discovery, backup e housekeeping.
   - `/etc/needrestart/conf.d/` e outros guardrails que nomeiam services.

3. **Automação e espelhamento**
   - `scripts/sync-souls.sh`: listas de agentes, SOUL/config, categorias de skills e destinos `rsync --delete`.
   - Verificar o comportamento quando a origem some: mirrors podem ficar stale em vez de serem removidos.
   - Nunca reapontar `rsync --delete` para um destino unificado sem snapshot e manifesto; isso pode propagar deleções.

4. **Dados e integrações compartilhadas**
   - `data/<agent>/`, `data/generated/<agent>/`, references, artifacts, caches e estados.
   - Medir arquivos/bytes por árvore e separar: runtime, corpus criativo, audit, reports, state e histórico.
   - Procurar credenciais com nome de um agente consumidas por scripts de outros domínios. Tratar o nome do arquivo/item como rótulo, não prova de ownership.
   - Para secrets, registrar somente path, existência, modo e tamanho; nunca ler valor.

5. **Discord**
   - Confirmar bot membro, bot ID, canal live, canal de logs e canal de infra.
   - Comparar IDs/names live com `authorized-users.json`, contexto e `infra-inventory.json`.
   - Mapear overwrites, roles, handoffs e mentions bot→bot.
   - Em consolidação, manter canal/thread/imports como histórico durante rollback; bot pode ficar no guild com gateway offline antes da remoção definitiva.

6. **Backups e rollback**
   - Inventariar units, crontab, jobs, data e mirrors disponíveis.
   - Ler as exclusões do backup: um snapshot que exclui `.env`, auth, tokens, cookies e browser profiles não é rollback completo.
   - Mapear housekeeping/retention que pode remover backups durante a janela.
   - Exigir escrow seguro de credenciais e browser state, manifesto/hash e teste documentado de reativação antes do cutover.

7. **Auditoria e drift**
   - Usar estado live como verdade para active/enabled/jobs.
   - Comparar com `data/infra-inventory.json`, `docs/CRONS.md` e audit logs; destacar divergências explícitas.
   - Verificar Git antes e depois. Se já houver dirty state, declarar como preexistente e não tocá-lo.

## Auditoria de conteúdo e comparação source → destination

Além do escopo transversal, quando o objetivo for absorver capacidades:

- Compare SOUL/config live com o mirror versionado por hash e declare qualquer drift.
- Compare configs source/destination estruturalmente após redigir chaves sensíveis; foque providers, toolsets, approvals, canais, geração de imagem/vídeo e comportamento de sessão.
- Conte skills por `SKILL.md`, separando active/archived/vendor e referências/scripts/templates. Compare mirrors seletivos arquivo a arquivo.
- Para umbrellas operacionais compartilhados, classifique `source-only`, `destination-only` e `different-common`; nunca sobrescreva um umbrella atual do destino com uma cópia antiga da origem.
- Extraia dos SOULs, contextos e skills custom os paths absolutos contratados e valide sua existência. Essa etapa revela dependências ocultas melhor que uma listagem ampla.
- Em SQLite, inspecione schema e contagens em modo read-only. Não faça merge direto de `state.db`: sessões, routing, FTS e metadados de plataforma são específicos do profile.
- Hashes de mídia/dados podem quantificar duplicação, mas cópias `raw`, `clean`, `READY` e `LEGACY` podem ser rastreabilidade deliberada.
- Preserve limites de área semanticamente no SOUL consolidado; unificar runtime não transforma automaticamente Creative Ops e Campaign Ops na mesma autoridade.

## Guard de drift concorrente

Capture Git status no início e no fim. Se um arquivo ficar dirty durante a auditoria read-only, reporte como drift externo concorrente com estatística sanitizada do diff; não atribua a mudança ao auditor e não tente limpá-la.

## Validações antes de desativar o agente origem

1. Congelar hashes/snapshots de arquivos canônicos, dados, DBs e browser profiles.
2. Migrar skills class-level e adaptar paths hardcoded sem desligar a origem.
3. Validar imagem, vídeo, sanitização de metadata e entrega de artefato real quando aplicável.
4. Validar readback externo de Drive/library/providers sem expor credenciais.
5. Validar o agente destino no canal Discord da origem, incluindo threads, free-response, prompts e permissões.
6. Buscar referências restantes ao profile/service/path de origem.
7. Confirmar que monitores unificados realmente substituem jobs pausados/duplicados.
8. Preservar DB/sessões históricas read-only em vez de mesclá-las.
9. Só então stop/disable, janela de observação e eventual arquivamento.

## Redução de ruído

- Imports Discord, backups, reports e mídia gerada produzem milhares de falsos positivos. Primeiro faça inventário por path/count/size; depois busque evidência somente em fontes canônicas e runtime ativo.
- Exclua `profiles/` quando o escopo for “fora dos profiles”, mas considere referências externas que apontam para profiles.
- Ignore binários, `__pycache__`, vendor e `node_modules` nas buscas textuais.
- Evidência compacta: `path:linha — fato`, sem tokens, URLs de webhook ou payloads de auth.

## Classificação de saída

Para cada superfície, use uma destas ações:

- **atualizar/migrar** — dependência ativa que muda de owner/nome/path;
- **manter operacional** — continua sendo usada pelo agente consolidado;
- **manter como histórico** — audit, changelog, imports, reports e execuções datadas;
- **desativar após validação** — service, cron, bot route ou monitor do agente antigo;
- **não tocar até plano de rollback** — secrets, dados compartilhados, browser profiles e runtime sensível.

## Ordem segura de consolidação

1. Manifesto + snapshot + escrow seguro.
2. Migrar skills, rotas e scripts para o agente destino sem desligar a origem.
3. Parametrizar paths hardcoded e neutralizar nomes de credenciais compartilhadas com compatibilidade temporária.
4. Migrar jobs/crons e validar outputs reais.
5. Atualizar autorização, Discord, contexto e inventário corrente.
6. Smoke tests end-to-end no agente destino.
7. Stop/disable do gateway antigo, preservando unit/profile/bot/canal para rollback.
8. Janela de observação.
9. Arquivamento e remoção definitiva somente com aprovação.

## Achados duráveis do caso Hera/Ares

- `sync-souls.sh` pode deixar mirrors stale quando a origem desaparece.
- Uma credencial chamada `ares-google-drive-*` era consumida por monitores, finance, Sheets e fluxos atribuídos à Hera; renomear/remover por ownership nominal quebraria outros domínios.
- `infra-inventory.json` pode divergir do `jobs.json` live em `enabled`.
- Units e safety backup não bastam para rollback quando secrets/browser profiles são excluídos.
- Bots/canais e threads devem ser tratados separadamente: desligar gateway não implica apagar bot, canal ou histórico.
