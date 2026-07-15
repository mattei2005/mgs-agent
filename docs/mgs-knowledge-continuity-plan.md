# Plano MGS — Memória Institucional e Continuidade

> Status: implementação inicial v1.0  
> Aprovado por: Rodolfo Mattei em 2026-07-15  
> Escopo aprovado: Fase 0 + Fase 1, aditivas, sem restart, sem alterar permissões e sem apagar memória.

## Objetivo executivo

Rodolfo não deve precisar repetir decisões, funções, estratégias ou contexto importante quando uma sessão mudar, um agente reiniciar ou outro agente assumir.

A solução não é aumentar indefinidamente MEMORY/USER. A solução é manter a memória individual pequena e criar uma camada institucional, versionada, pesquisável e recuperável.

## Baseline confirmado antes da implantação

- Zeus, Atena e Ares estavam `active/enabled` no systemd.
- Memória e USER estavam habilitados nos três profiles.
- Zeus USER: 1.796/1.800 caracteres antes da consolidação deste bloco.
- Ares USER: 1.632/1.800 caracteres.
- Existiam três dead-letters de `capacity_overflow`: dois Zeus e um Ares.
- Os três payloads estavam preservados; nenhum aprendizado foi silenciosamente perdido.
- O backup MGS existente era local, com intervalo máximo de três dias, e excluía `.db`, `.sqlite`, logs e profiles Hermes vivos.
- Não foi encontrada evidência canônica de backup off-site ou restore drill no repositório MGS.
- `docs/mgs-os-restructure-plan.md` ainda tratava Hera como pendente, em conflito com `context/agent-map.md`, que registra a consolidação no Ares em 2026-07-12.

## Fase 0 — Estabilização

```text
Item                                      Estado
---------------------------------------- ----------------------------------------
Classificar 3 capacity overflows           Concluído
Preservar conteúdo                         Concluído; payloads intactos
Consolidar preferência Zeus                Concluído com readback em USER
Provar cobertura do Ares                    Concluído; fato já está na USER do Ares
Excluir dead-letters recuperados            Não executado; exclusão exige gate crítico
Corrigir drift Hera/Ares                    Incluído neste bloco
Mapear cobertura real do backup             Concluído documentalmente
```

Os arquivos dead-letter permanecem até Rodolfo confirmar explicitamente a exclusão crítica. Isso não representa perda de aprendizado: os fatos foram recuperados semanticamente e os payloads continuam preservados.

## Fase 1 — Fundação institucional

Artefatos:

```text
context/knowledge-governance.md             Política de classificação e promoção
data/knowledge-registry.json                Registro de fontes/decisões/capacidades
data/knowledge-inbox.jsonl                  Candidatos ainda não canônicos
data/agent-checkpoints.json                 Continuidade entre sessões/agentes
scripts/mgs-knowledge-control.py            Controle, lock, atomicidade e validação
tests/test_mgs_knowledge_control.py          Regressão e concorrência
docs/mgs-knowledge-continuity-plan.md        Plano e status executivo
```

Invariantes implementados:

- captura idempotente por conteúdo normalizado;
- lock exclusivo comum a todos os mutadores;
- releitura depois do lock;
- escrita JSON atômica, `fsync` e readback;
- IDs únicos;
- somente uma versão ativa por chave canônica;
- supersessão explícita;
- validação de fonte local;
- checkpoint atualizado sem duplicação;
- nenhuma promoção automática de chat para política.

## Fase 2 — Piloto Zeus

Escopo futuro, ainda não ativado:

- Zeus registrar candidatos duráveis durante a operação normal;
- criar checkpoint para iniciativas longas;
- promover somente após autoridade e fonte correta;
- adicionar perguntas de regressão empresarial;
- medir candidatos pendentes e tempo de resolução.

Essa fase altera comportamento operacional do agente e terá gate separado.

## Fase 3 — Atena e Ares

Escopo futuro:

- um agente por vez;
- mapear conhecimento sempre ativo versus roteado;
- validar conteúdo/WordPress na Atena;
- validar Creative/Campaign Ops no Ares;
- não recriar Hera como agente ativo;
- preservar rollback e histórico.

## Fase 4 — Backup e recuperação

Escopo futuro:

- backup incremental criptografado fora da VPS;
- incluir repositório, memórias, sessions/state.db, configs e bancos aprovados;
- excluir segredos ou protegê-los em fluxo criptografado separado;
- retenção diária, semanal e mensal;
- restore drill isolado;
- monitorar idade do último backup e do último restore aprovado.

Metas iniciais propostas:

```text
Conhecimento institucional    RPO <= 1 hora
Sessões/checkpoints           RPO <= 1 hora
Restauração funcional         RTO <= 2 horas
Dead-letter sem classificação máximo 24 horas
```

Essas metas são objetivos de engenharia, não garantias ativas antes da Fase 4.

## Critério de sucesso final

- Rodolfo não precisa repetir uma decisão já promovida e vigente.
- Agentes localizam a fonte correta sem carregar toda a empresa no prompt.
- Regras antigas ficam superseded, não concorrentes.
- Uma iniciativa pode ser retomada pelo checkpoint.
- Falha de capacidade não perde aprendizado.
- Backup e restore test provam reconstrução fora da VPS original.
