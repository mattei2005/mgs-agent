# Auditoria de regras de Campaign Ops contra runtime

Use quando um gestor pedir para ver “todas as regras”, revisar a configuração de uma thread ou procurar furos antes de simulação/produção.

## Objetivo

Separar quatro camadas que não podem ser tratadas como equivalentes:

1. **Política ativa** — fonte canônica e registro institucional.
2. **Roteamento** — thread canônica, prompt específico e membros obrigatórios.
3. **Implementação** — config, runner, engine, manifest, testes e flags efetivas.
4. **Runtime** — API/live readback, cron history, output do último ciclo e efeitos reais.

Uma regra bem escrita não prova implementação; um objeto/config presente não prova ativação; um cron salvo não prova execução; `ACTIVE` não prova delivery.

## Procedimento

1. **Localizar a verdade canônica**
   - Ler registry/checkpoint e depois a fonte apontada.
   - Confirmar operação, conta/alias, estratégia, timezone, moeda, gestão e gates de autoridade.
   - Identificar supersessões explícitas; não misturar thread histórica com rota ativa.

2. **Auditar as rotas Discord**
   - Enumerar todas as threads fixas a partir do contrato.
   - Comparar cada thread com `channel_prompts` do runtime e do mirror versionado.
   - Exigir prompt específico para perguntas genéricas de configuração nas rotas funcionais.
   - Diferenciar política de membros de evidência de inclusão; sucesso exige readback real.

3. **Comparar contrato global e módulos**
   - Procurar contradições como `write_enabled=false` no topo e controlled-write ativo em um módulo.
   - Comparar `status`, `activation_enabled`, timestamps gerais e eventos internos posteriores.
   - Marcar campos históricos como históricos; não permitir que consumidores ingênuos os interpretem como estado vigente.

4. **Reconciliar implementação**
   - Conferir onboarding da conta, modos suportados, operação v3, prompt dedicado, mídia pre-stageada e placements/payloads obrigatórios.
   - Executar validadores/config reports existentes.
   - Rodar a suíte pelo runner disponível no projeto; relatar quantidade executada e falhas exatas, sem converter ausência de um runner opcional em regra durável.
   - Verificar alterações paralelas no working tree e impedir que arquivos de outra operação entrem na mesma consolidação.

5. **Validar crons pelo efeito real**
   - Listagem do scheduler é apenas uma camada; ler o output da última execução.
   - Para um ciclo marcado `error`, distinguir:
     - falha insegura ou efeito parcial;
     - bloqueio fail-closed esperado por fonte stale/irreconciliável.
   - Um fail-closed saudável precisa mostrar `write_ready=false`, zero writes e alerta/readback quando contratado.
   - Histórico real de ticks vence flag de observador sabidamente divergente, mas a divergência continua como gap de observabilidade.

6. **Classificar os achados**
   - **Crítico:** rota errada, prompt ausente, executor parcialmente instalado, teste de gate falhando.
   - **Alto:** flags contraditórias, fonte econômica sem freshness, criação/clone sem onboarding ou payload completo.
   - **Médio:** registry/timestamp/título stale, documentação histórica ambígua.
   - Informar o que está correto, o que está bloqueado e o que depende de decisão humana.

7. **Persistir sem promover hipótese**
   - Se o gestor disser apenas “salve” após uma auditoria, gravar os achados como **checkpoint operacional**.
   - Não transformar inconsistências, recomendações ou hipóteses em política canônica.
   - O checkpoint deve registrar objetivo, estado, próximos passos, thread e fontes, além de declarar quais writes não ocorreram.
   - Validar por readback e pelo controle institucional.
   - Alteração de data operacional exige REPORT-INFRA conforme a política MGS.

## Forma de resposta

- Começar pelo veredito e pela thread/rota efetivamente ativa.
- Consolidar regras por domínio: autoridade, criação, criativos/copy, tracking, ciclos, escala, guardrails, reporting e clone.
- Depois listar erros por severidade e concluir com sequência de correção.
- Não tratar snapshots históricos como estado atual.
- Não expor credenciais, IDs de objetos de campanha desnecessários, paths de runtime, traces ou payloads sensíveis.

## Pitfalls

- Concluir “cron ativo” apenas porque está enabled/scheduled.
- Chamar fail-closed de falha de segurança quando houve zero write e alerta confirmado.
- Corrigir contrato durante pedido de auditoria sem autorização de mudança.
- Salvar análise como regra ativa só porque o gestor disse “salve”.
- Misturar naming/budget divergentes sem obter uma decisão única e supersessão explícita.
- Usar a thread onde a pergunta chegou como prova de que ela ainda é a rota canônica.
