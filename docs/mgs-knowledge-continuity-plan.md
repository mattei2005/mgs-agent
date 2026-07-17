# Plano MGS — Memória Institucional e Continuidade

> Status: implementação v1.4, Fases 2–4 ativas e validadas nos agentes operacionais
> Aprovado por: Rodolfo Mattei em 2026-07-15  
> Escopo aprovado: Fases 0–1 aditivas + Fase 2 Zeus em 2026-07-15; Fase 3 Atena e Ares e Fase 4 de backup/recuperação autorizadas e ativadas em 2026-07-16.

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
- `docs/mgs-os-restructure-plan.md` ainda tinha um agente legado pendente, em conflito com o mapa canônico do Ares.

## Fase 0 — Estabilização

```text
Item                                      Estado
---------------------------------------- ----------------------------------------
Classificar 3 capacity overflows           Concluído
Preservar conteúdo                         Concluído; payloads intactos
Consolidar preferência Zeus                Concluído com readback em USER
Provar cobertura do Ares                    Concluído; fato já está na USER do Ares
Excluir dead-letters recuperados            Não executado; exclusão exige gate crítico
Corrigir drift de Creative Operations       Incluído neste bloco
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

```text
Status: ativo e validado em sessão nova do Zeus em 2026-07-15.
Escopo: Zeus somente; Atena e Ares permanecem inalterados.
```

- SOUL live e versionado apontam para governança, registry e checkpoints;
- decisões/contextos duráveis passam por classificação antes da escrita;
- destino canônico claro e autorizado é persistido e registrado na própria tarefa;
- item bloqueado/ambíguo vira somente candidato, nunca verdade ativa;
- iniciativas longas recebem checkpoint em transições materiais;
- `data/knowledge-regression-cases.json` protege perguntas empresariais críticas;
- `mgs-knowledge-control.py regression` valida fontes e termos obrigatórios/proibidos;
- cutover de SOUL precisa ser provado em sessão nova; restart não é necessário.

Validação de cutover:

- SOUL live e versionado byte-identical;
- marker de continuidade presente uma vez em ambos;
- sessão local nova `20260715_190940_434738` reproduziu a primeira regra da seção;
- `state.db` read-only confirmou o marker exato em `sessions.system_prompt`;
- nenhum gateway foi reiniciado.

## Fase 3 — Atena e Ares

Status: pilotos da Atena e do Ares ativos e validados em 2026-07-16.

Atena:

- recebeu somente o kernel de continuidade relevante a Content Operations;
- consulta registry/checkpoint e depois a fonte canônica antes de pedir repetição de decisão editorial;
- persiste procedimento em skill, regra/fato na fonte canônica e estado temporário em checkpoint;
- itens globais, ambíguos ou fora da área continuam escalando para Zeus;
- SOUL live e versionado estão byte-identical, config e permissões permaneceram inalteradas;
- OAuth OpenAI-Codex foi reautenticado com cadeia independente após o smoke revelar um refresh clonado/inválido;
- sessão local nova `20260716_034612_a9a42a` respondeu corretamente e contém o marker de continuidade exatamente uma vez no `sessions.system_prompt`;
- nenhum gateway foi reiniciado.

Ares:

- recebeu somente o kernel de continuidade relevante a Creative Ops e Campaign Ops;
- consulta registry/checkpoint e depois a fonte canônica antes de pedir repetição de decisão ou retomada;
- persiste procedimento em skill, estrutura/regra na fonte canônica e estado temporário em checkpoint dentro da autoridade vigente;
- itens globais, ambíguos ou fora da área continuam escalando para Zeus;
- preserva as rotas canônicas do Ares sem recriar agentes legados;
- SOUL live e versionado estão byte-identical, config e permissões permaneceram inalteradas;
- OAuth OpenAI-Codex foi reautenticado com cadeia independente após o preflight revelar refresh inválido;
- sessão local nova `20260716_094808_1d73e9` consultou registry/checkpoint e contém o marker de continuidade exatamente uma vez no `sessions.system_prompt`;
- nenhum gateway foi reiniciado.

## Fase 4 — Backup e recuperação

Status: ativo e validado em 2026-07-16.

- backup horário e completo criptografado com chave pública antes do upload;
- chave privada exclusiva preservada no 1Password e ausente da rotina normal de backup;
- destino off-site no Shared Drive canônico `MGS-AGENTS/_DISASTER_RECOVERY`;
- inclui MGS OS, memórias, sessions, `state.db`, configs, crons, units e bancos aprovados;
- segredos locais necessários ficam somente dentro do pacote criptografado;
- retenção por quantidade: 48 horários, 14 diários, 8 semanais e 12 mensais;
- restore test semanal em diretório isolado, sem alterar profiles vivos;
- monitor de SLA silencioso, com alerta somente em atraso/falha;
- incidente de `.env.save*` foi contido com rotação de token e chave, remoção dos backups afetados e reexecução integral.

Metas ativas:

```text
Conhecimento institucional    RPO <= 1 hora
Sessões/checkpoints           RPO <= 1 hora
Restauração funcional         RTO <= 2 horas
Dead-letter sem classificação máximo 24 horas
```

Validação real da ativação:

- backup horário criptografado: PASS;
- backup completo criptografado: PASS;
- upload e readback Drive por tamanho, MD5 e SHA-256: PASS;
- download do pacote completo: PASS;
- descriptografia com a chave privada recuperada do 1Password: PASS;
- import isolado de Zeus, Atena e Ares: PASS;
- SQLite `quick_check`: PASS; índices FTS derivados do Ares foram reconstruídos somente na cópia isolada;
- validação do knowledge registry restaurado: PASS;
- monitor atual: saudável, sem lacunas de SLA.

## Critério de sucesso final

- Rodolfo não precisa repetir uma decisão já promovida e vigente.
- Agentes localizam a fonte correta sem carregar toda a empresa no prompt.
- Regras antigas ficam superseded, não concorrentes.
- Uma iniciativa pode ser retomada pelo checkpoint.
- Falha de capacidade não perde aprendizado.
- Backup e restore test provam reconstrução fora da VPS original.
