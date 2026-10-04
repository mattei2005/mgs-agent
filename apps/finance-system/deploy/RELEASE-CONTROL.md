# Publicação coordenada da dashboard financeira

Autoridade da proteção: Rodolfo `1551985522380111956`, thread `1545426987756298340`. Esta autorização não autoriza novas regras financeiras ou futuras mutações de cadastro.

## Contrato

- Preparar a versão em `private/<release>/candidate/`, nunca editar código/regras ativos para depois testar.
- Runners GAM, gastos e câmbio adquirem admissão compartilhada **antes** dos imports de negócio. O worker de consultas usa admissão por ciclo, não durante toda a vida do processo.
- A publicação usa admissão exclusiva e os locks legados, com espera limitada. Se uma rotina está em andamento, é a publicação que espera/aborta sem alteração; uma rotina disparada durante a troca aguarda e depois executa.
- GAM/gastos conservam o horário original do disparo para validar a janela agendada. Esperar a troca não descarta o slot por mudança de minuto/hora.
- O controlador não pausa cron, não altera horários, não escreve SQL financeiro nem registra automaticamente sites. Cadastro necessário deve ter autorização própria e estar concluído; a checagem é somente leitura. Se faltar, a versão antiga permanece ativa.
- Backups exatos e journal persistem em `private/releases/<release_id>/`. Há readback de todos os destinos e rollback de código em falha. Na próxima admissão, um journal interrompido exige recuperação antes do processamento.
- Escritas remotas usam fence por release e lock no host financeiro. Um comando atrasado de uma publicação já revertida é rejeitado, mesmo se encontrar novamente o hash antigo (problema ABA).
- Hash inesperado de terceiro, backup inválido ou transporte irrecuperável não permitem sobrescrita cega. Bloquear e escalar; nunca prometer disponibilidade absoluta sob esse tipo de falha.

## Preparação source-only — Rodolfo1556332890743115850

O entrypoint reutilizável atual é `deploy/prepare_release.py`, que usa `deploy/source_stage.py` sob admissão compartilhada, sem recuperar/publicar releases durante preparação:

```
python3 -B deploy/prepare_release.py --manifest /caminho/manifesto-explicito.json --destination /root/mgs-agent/apps/finance-system/private/<release>/candidate
```

O manifesto enumera cada arquivo com `path`, `kind` (`code` ou `fixture`) e SHA-256. Fixtures exigem `explicit_fixture: true` e `source_evidence`; copiar somente arquivos necessários, nunca uma árvore private, evidências, dumps, backups ou stages anteriores. Limite de cópia por preparação:96MiB; cada fixture:32MiB. A closure de testes inclui também caminhos dinâmicos/nested fixtures previstos em `current-security-performance-and-dr.md`; preflight não prova closure completa nem substitui gates Node/Python. Arquivos fonte permanecem inalterados; qualquer suplemento deve ser explicitamente enumerado e lido sob a mesma admissão compartilhada.

Symlinks de entrada `public`/`node_modules` são permitidos somente para os diretórios canônicos, sem symlink no próprio alvo, com aprovação explícita e marcadores SHA-256 validados. Nunca escrever através desses links; para alterar public, enumerar e copiar seus arquivos. Marcadores não são hash integral da árvore: drift completo deve ser controlado pelos gates/manifesto de código e lockfile antes da publicação. Não usar este preparador sobre árvores hostis ou mutáveis fora da governança operacional.

A prevenção está integrada a esse entrypoint e sua execução atual. Scripts históricos one-shot não são reescritos e não ganham proteção retroativa. Não há cron de remoção nem prazo de retenção implícito.

Restart apenas de `mgs-finance-dash.service`, necessário para correção explicitamente autorizada, é Level1; não é Critical Subset por si. Isto não autoriza alterar `/etc/systemd`, reiniciar PostgreSQL, gateways/VPS, credenciais, permissões ou dados financeiros. Inclusão de módulo novo exige bootstrap separado, com revisão, ensaio, journal, proteção de concorrência e readback; não é proibição permanente nem motivo para ignorar gates. O executor existente permanece fail-closed: preparação não lhe concede suporte a arquivos novos.

## Uso

Executar no diretório canônico da aplicação:

```
python3 finance_release.py check --manifest private/<release>/manifest.json --candidate private/<release>/candidate
python3 finance_release.py publish --manifest private/<release>/manifest.json --candidate private/<release>/candidate
python3 finance_release.py recover
```

`check` valida pacote, ambos os gates completos, prova de stage e pré-requisitos reais; não publica. `publish` repete verificações sob lock, salva backups, escreve, lê de volta e só então libera. `recover` só reverte uma transição incompleta; não reverte uma release já confirmada.

Manifesto schema1:
- `release_id`: identificador único, nunca reutilizar.
- `authority`: mensagem que autorizou **essa** atualização.
- `files`: lista explícita de `host` (`local`/`remote`), `path`, `source`, `before` e `after` (SHA-256 reais).
  - local: caminho relativo a `/root/mgs-agent`, limitado ao código da aplicação e `data/finance-gam-revenue-rules.json`;
  - remote: caminho relativo ao release financeiro fixado no runbook;
  - source: arquivo dentro do candidato isolado.
- `gates`: diretório relativo dos resultados Node/Python. Ambos devem corresponder exatamente ao código atual do candidato, sem skips.
- `stage_proof`: JSON com `pass`, `authority`, mapa `files` (chave `host:path` → SHA-256), `financial_writes: 0` e `catalog_required`. Produzir somente a partir de ensaio real aprovado; um JSON preenchido manualmente não substitui a execução.
- `catalog_required`: lista de `{period, site_id}` a confirmar no catálogo materializado. Obrigatória em mudança de regras GAM; não é uma autorização de cadastro.
- `remote_health`: validar serviço/socket/PostgreSQL e login interno.
- `restart_app`: obrigatório para mudança remota; reinicia somente o serviço financeiro, não gateway, banco ou socket.
- `restart_worker`: obrigatório para mudança Python local; recarrega somente o worker financeiro local.

## Limites deliberados

- O controlador não é um mecanismo de fechamento, migração de banco ou alteração de credenciais/permissões. Não admite caminhos privados, `/etc`, scripts de deploy, exclusões, symlinks nem comandos arbitrários no manifesto.
- A substituição regular cobre arquivos **já existentes**, em conjunto pequeno (até40). Inclusão de módulos novos, atualização do próprio controlador/guard e alteração do worker exigem um bootstrap explicitamente revisado e testado, como o desta entrega; não contornar o bloqueio editando um arquivo ativo.
- O tempo normal de admissão exclusiva tem orçamento de120s; falha exige rollback/recuperação, que pode demorar mais se houver indisponibilidade externa. A espera do publicador também é limitada. Não apresentar120s como SLA absoluto de recuperação.
- Cron continua com suas proteções anteriores contra execuções simultâneas. Esta proteção impede perda **causada pela janela da atualização**; não promete que toda falha externa, timeout ou interrupção do host seja recuperável sem intervenção.
- Não apagar backups, bancos de teste ou journals nesta rotina. Retenção destrutiva é uma autorização separada.
- Rodar a consulta de catálogo com `sudo -u mgsfinance` **antes** do `cd` ao release protegido. `additions` é array; ler `result.domain.site_catalog`, não presumir um objeto de sites em additions.

## Aceitação

Testar processos reais em concorrência: leitores simultâneos, publicador esperando job, job aguardando publicação e retomando, preservação do horário, morte do processo, rollback de escrita parcial, destino alterado por terceiro e rejeição de escrita remota atrasada. Testes de falha usam arquivos sintéticos isolados, nunca induzem corrupção em produção.

Validar ainda hash do candidato/ativo, catálogo positivo e negativo com consultas reais, serviços produtivos, fingerprint financeiro por hash de linha/documento, interface autenticada e zero POST financeiro. Gate verde não prova sozinho cutover ou paridade financeira.
