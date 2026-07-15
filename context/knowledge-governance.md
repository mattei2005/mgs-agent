# MGS OS — Governança de Conhecimento e Continuidade

> Status: canônico v1.0  
> Dono executivo: Rodolfo Mattei  
> Orquestração: Zeus  
> Objetivo: preservar contexto empresarial importante sem transformar a memória individual dos agentes em fonte única.

## 1. Princípio central

A memória individual de um agente é contexto rápido, não o banco da empresa.

```text
Memória do agente       contexto pequeno, sempre ativo e específico do agente/usuário
MGS OS                  memória institucional da empresa
Fonte externa/runtime   estado técnico ou operacional real
Audit/Git               histórico e rastreabilidade
Checkpoint              continuidade de uma iniciativa entre sessões/agentes
```

Nenhum fato empresarial relevante deve depender apenas de uma sessão Discord, de MEMORY/USER ou de um prompt.

## 2. Classes e destino obrigatório

```text
Classe                         Destino primário
----------------------------- ---------------------------------------------------
Preferência estável             USER/MEMORY do agente relevante
Identidade/regra global         SOUL/AGENT, conforme autoridade
Procedimento reutilizável       skill/reference correspondente
Estrutura/dono/rota/política    context/*.md
Estado operacional atual        data/, banco ou dashboard canônico
Decisão estratégica             data/knowledge-registry.json + fonte canônica
Candidato ainda não aprovado    data/knowledge-inbox.jsonl
Iniciativa em andamento         data/agent-checkpoints.json
Evento executado                logs/events-audit.jsonl
Histórico/plano                 docs/
Credencial                      1Password; nunca registro de conhecimento/chat
```

## 3. Ciclo de conhecimento

```text
conversa/evento
→ capturar candidato
→ classificar classe e domínio
→ identificar dono e autoridade
→ escolher fonte canônica
→ escrever no destino correto
→ validar por readback
→ registrar metadados e consumidores
→ executar consistência
→ audit/Git/REPORT quando aplicável
```

Captura não significa aprovação. `knowledge-inbox.jsonl` é uma fila de candidatos, nunca fonte de verdade.

## 4. Autoridade e promoção

- Fala nova e explícita de Rodolfo vence arquivo antigo, mas deve ser persistida na fonte correta quando for durável.
- Decisão crítica continua sujeita ao `AGENT.md`.
- Agentes podem capturar candidatos dentro de seu escopo.
- Promoção para política, ownership, permissão, budget, credencial ou estrutura exige a autoridade definida no MGS OS.
- A ferramenta de controle não edita automaticamente fontes canônicas e não transforma texto de chat em política.

## 5. Registro institucional

O registro guarda metadados e ponteiros, não cópias concorrentes de toda a operação.

Campos obrigatórios:

```text
id | kind | domain | title | owner | canonical_source | canonical_key
status | consumers | effective_at | review_due | superseded_by | updated_at
```

Estados:

```text
active | draft | superseded | retired
```

Só pode existir um registro `active` por `canonical_key`.

## 6. Supersessão sem perda histórica

Uma regra nova não apaga silenciosamente a antiga:

1. registrar o sucessor;
2. marcar o anterior como `superseded`;
3. preencher `superseded_by`;
4. preservar a fonte histórica;
5. validar que existe apenas uma versão ativa da chave canônica.

## 7. Checkpoints de continuidade

Toda iniciativa longa ou que possa atravessar sessões/agentes deve manter:

- identificador estável;
- agente responsável;
- thread/origem;
- objetivo;
- estado atual;
- próximo passo;
- fonte de contexto;
- data de atualização.

Checkpoint não substitui audit log nem pendência. Ele responde: “onde paramos e qual é o próximo passo?”.

## 8. Recuperação de memória cheia

- Rejeição por capacidade deve permanecer recuperável em dead-letter.
- Nunca compactar ou apagar automaticamente fatos para abrir espaço.
- Antes de remover um fato de USER/MEMORY, provar destino canônico e rota de carregamento.
- Registros recuperados/superseded só saem da fila pelo caminho auditado e com a confirmação exigida para exclusão.
- Meta operacional: nenhum dead-letter de conhecimento sem classificação por mais de 24 horas.

## 9. Continuidade técnica

A continuidade completa possui quatro camadas independentes:

```text
Disponibilidade   systemd, health checks e monitores
Durabilidade      Git, registros e backups
Recuperação       restore test executado
Recuperação lógica fontes, índices, checkpoints e testes de consistência
```

Backup local sem restore test ou sem sessions/memories não prova recuperação completa.

## 10. Ferramenta canônica

```text
Script       scripts/mgs-knowledge-control.py
Registry     data/knowledge-registry.json
Inbox        data/knowledge-inbox.jsonl
Checkpoints  data/agent-checkpoints.json
Tests        tests/test_mgs_knowledge_control.py
Plano        docs/mgs-knowledge-continuity-plan.md
```

Comandos principais:

```text
mgs-knowledge-control.py init
mgs-knowledge-control.py capture ...
mgs-knowledge-control.py register ...
mgs-knowledge-control.py supersede ...
mgs-knowledge-control.py checkpoint-upsert ...
mgs-knowledge-control.py validate
mgs-knowledge-control.py status
```

Todos os mutadores usam um lock comum, releem o estado sob lock, escrevem atomicamente e validam readback.

## 11. Verificação mínima

- IDs únicos.
- Uma versão ativa por chave canônica.
- Fonte local existente.
- `superseded_by` apontando para registro real.
- Candidatos idempotentes.
- Checkpoints únicos e completos.
- Testes de concorrência e escrita atômica aprovados.
- Alterações estruturais inventariadas, auditadas e reportadas.
