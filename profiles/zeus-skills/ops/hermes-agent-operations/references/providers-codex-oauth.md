# Providers, Models, and OpenAI Codex OAuth

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 3. Providers, modelos e OpenAI Codex OAuth

Use quando Rodolfo quiser trocar provider de Zeus/Atena/Ares, usar GPT via assinatura ChatGPT, reduzir custo Anthropic/Claude, autenticar `openai-codex`, validar cron jobs após migração, ou auditar chamadas LLM pagas.

Para rollout de modelo/reasoning em múltiplos profiles, incluindo distinção principal vs. auxiliares, verificação auth por agente, smoke real 4/4, limites de `xhigh` vs. Sol Pro e proibição de chamar default fixo de “roteamento automático”, use `references/openai-codex-multi-profile-model-rollout.md`.

### Provider incident gate — before credential repair

- Before proposing reauthentication, credential copying, config edits or restarts for sudden Codex401s, check the official OpenAI incident feed (`https://status.openai.com/api/v2/incidents.json`) and correlate UTC timestamps across the affected profiles. An `invalid_api_key` message alone does not prove local credential damage; simultaneous failures with unchanged configuration can originate at the provider. Never call an outage confirmed from a screenshot alone, and never call credential corruption confirmed from the HTTP label alone.
- During a matching acknowledged incident, preserve local credentials/configuration and wait for provider recovery instead of repeatedly authenticating or restarting. After resolution, prove recovery with one harmless exact-marker inference per operational profile using its own existing OAuth credentials, plus live gateway/Discord state. If only a particular profile still fails, investigate that profile under the credential Critical Subset; do not relogin every agent by default.
- Inspect the current auth schema before declaring credentials missing: supported Codex sessions may live in `credential_pool.openai-codex[]` with top-level `access_token` and `refresh_token`, even when `providers.openai-codex` is absent. Compare the active pool entries pairwise internally; never compare missing legacy values, print tokens or publish token fingerprints. A matching legacy provider block within one profile is compatibility state, not proof of cross-profile cloning or a deletion candidate.
- Classify historic401 markers, gateway locks/sockets, session databases and normal service logs separately from abandoned repair artifacts. Do not delete normal runtime/audit state to make an incident appear clean. Verify full live/mirror config equality, source-tree integrity, service PIDs, active auth-sync triggers and recent control-file changes before proposing cleanup. Read-only inference is credential validation, not proof that an untested Discord conversation or pending business task completed.

### Provider safety rejection versus session recovery

- Treat `This request was blocked by our safety systems / Potentially unintended activity` as an explicit provider rejection, not proof of outage, quota exhaustion or a failed dashboard MFA. Do not keep retrying the same rejected request or disable security controls to get it accepted.
- Different models working in different threads do not isolate model as the cause: context and requested action also differ. Do not assert a particular safety trigger or promise that a reset/model switch resolves it without a benign, read-only inference test.
- For an authorized recovery that must preserve important work, first snapshot the profile session DB outside Git, validate SQLite and exact source messages, reconcile completed side effects, and create a source-linked continuity report. Prefer native lease-guarded atomic compression publication over an empty reset or ad-hoc transcript deletion. Preserve the original session/ancestors and actual financial decisions; summarize closed security operations as history, never as a new user authorization.
- Resolve the LIVE gateway checkout from its actual service process before importing SessionDB/SessionStore: a launcher may point to a staged runtime while `~/.hermes/hermes-agent` is stale. Use native compression-tip healing and a one-row routing writer; avoid whole-index replacement that can clobber concurrent sessions. Test the intended model against the continuity context and distinguish provider PASS from a still-unobserved incoming Discord turn.
- After a wrapper fails following publication, reconcile the existing child and original transcript before retry. The canonical conversation reader may strip a trailing newline even though stored rows are exact; validate that contract without publishing a second child.
- Keep finance MFA and provider safety separate. An exposed DB dump calls for credential/session remediation; removing user MFA does not repair a model request and weakens account protection.

### Fatos essenciais

- Endpoint Codex: `https://chatgpt.com/backend-api/codex` (não `api.openai.com`).
- Auth: OAuth device-code via assinatura ChatGPT; tokens em `auth.json`.
- Billing Hermes: `openai-codex` deve aparecer como `subscription_included`/included, sem pay-per-token.
- Modelo principal MGS atual: `gpt-5.6-sol` via plano ChatGPT; `gpt-5.5` é legado/fallback apenas quando explicitamente mantido.
- Roteamento MGS por dificuldade: Medium para simples, High para operação normal e `xhigh`/Extra High para crítico/long/code-heavy. Override explícito `/reasoning` sempre vence. Implementação e validação: `references/gpt56-sol-auto-reasoning-routing-mgs.md`.
- Migração de modelo/config só termina após restart seguro + smoke real de cada profile. Quando Zeus precisar reiniciar, não depender de auto-resume: preparar finalizer externo com callback verificável para a thread de origem. Em `systemd-run`, usar executável absoluto (`/root/.local/bin/hermes`), porque unidades detached não herdam o PATH interativo. Agendar só depois da resposta pré-restart e deixar o turno ativo terminar; caso contrário Zeus pode permanecer `deactivating` e gerar falso `not ready`.
- `gpt-5.6-sol-pro` só pode ser oferecido depois de smoke real. Não confiar apenas no picker/lista sintetizada: no OAuth ChatGPT MGS, uma chamada real ao slug retornou HTTP 400 “model is not supported when using Codex with a ChatGPT account”. Para trabalho crítico, usar `gpt-5.6-sol` com `xhigh` até um smoke Pro passar.
- Política operacional MGS: zero Anthropic/Claude API pay-per-token por padrão, salvo autorização explícita do Rodolfo.

### Login inicial

```bash
hermes model
# selecionar openai-codex, abrir URL, inserir device code e autorizar
```

O login no perfil raiz atualiza `~/.hermes/auth.json`; profiles Zeus/Atena/Ares/agente legado mantêm stores próprios.

### OAuth por profile — gate de identidade antes do login

**Supersessão da recomendação anterior de logins independentes para todos os profiles:** antes de iniciar device-code, conferir o runtime atual e comparar internamente a identidade Codex `(chatgpt_account_id, sub)`, sem imprimir valores, tokens ou fingerprints. O runtime pode advertir em `_warn_same_codex_account` que um novo login da mesma conta compartilha a família OAuth e revoga o grant anterior. Se profiles usam a mesma identidade e esse aviso estiver presente, não iniciar logins sequenciais por profile: tratar como risco de invalidar os agentes saudáveis, informar o conflito com o procedimento antigo e pedir nova autorização para uma arquitetura compartilhada com lock cross-process e write-through demonstrados. O comentário do runtime é evidência de risco, não prova isolada da causa histórica de uma revogação.

Logins independentes continuam adequados para contas OpenAI realmente distintas. Copiar permanentemente o mesmo bloco para stores independentes também não é uma solução: refresh tokens rotativos/single-use exigem um único caminho coordenado de renovação. Preservar a assinatura incluída; não mudar para API paga nem pedir novas assinaturas como fallback automático.

O fluxo abaixo é histórico e só se aplica depois de passar o gate de identidade; exigir cadeias diferentes entre profiles da mesma conta está supersedido pelo gate acima.

Fluxo:

1. Backup de cada `auth.json` fora do Git, com diretório `700`; antes do picker, registrar também hashes do `config.yaml` live e do mirror versionado.
2. Executar o login OAuth no contexto de cada profile (`hermes -p <profile> model`) e concluir o device-code.
3. Em uma conversa Discord, assim que o device flow mostrar URL e código, enviar imediatamente ao Rodolfo um link Markdown clicável (`[Abrir autorização da OpenAI](https://auth.openai.com/codex/device)`) e o código em destaque. Não depender de URL em tool progress, não enterrar o link em explicação e não responder apenas que está aguardando.
4. Validar presença de access/refresh sem imprimir valores.
5. Comparar o refresh token internamente com os demais profiles e exigir cadeia independente; reportar apenas os booleanos de igualdade/independência.
6. O model picker pode normalizar `config.yaml`, remover defaults vazios e inserir defaults novos mesmo quando a intenção era somente autenticar. Em um fluxo auth-only, quando o picker oferecer a opção, selecionar **`Skip (keep current)`** em vez de escolher novamente o modelo atual; isso reduz superfície de drift, mas não substitui o readback. Depois do login, comparar o config live com o hash/backup e o mirror. Se houve drift não autorizado e o provider/model pretendidos já eram os mesmos, restaurar exatamente o config pré-login, preservar o novo `auth.json` e provar live=mirror por hash e leitura semântica.
7. Rodar inferência real em sessão nova do profile e confirmar que o gateway permaneceu ativo; OAuth isolado não exige restart por si só.
8. Para rollout de comportamento/SOUL, validar também no `state.db` read-only que o marker distintivo aparece exatamente uma vez no `sessions.system_prompt` da nova sessão. Falha OAuth antes da criação da sessão não é prova parcial de cutover.

Copiar apenas o provider block de um profile saudável é permitido somente como recuperação emergencial e temporária após confirmação crítica. Registrar prazo de correção e substituir por sessões OAuth independentes ou por store compartilhado que tenha lock cross-process e write-through comprovados.

### Gate pós-isolamento: automações que podem desfazer a separação

Depois de autenticar profiles com cadeias OAuth independentes, auditar **antes de declarar estabilidade** toda automação que possa copiar auth entre stores: crontab, systemd timers/services, scripts de sync, jobs Hermes e finalizers. Procurar especialmente fluxos `~/.hermes/auth.json` global → `profiles/*/auth.json`.

Regras:

1. Comparar access/refresh internamente e reportar apenas booleanos de igualdade; nunca valores ou fingerprints.
2. Ler a direção e a condição temporal do sincronizador. Um dry-run que faz zero writes porque o global está mais antigo prova apenas o estado atual — se o global renovar depois, um sync baseado em `last_refresh` pode sobrescrever todas as cadeias exclusivas.
3. Não chamar OAuth independente de “durável/estável” enquanto existir cron/timer ativo capaz de reintroduzir o mesmo refresh token nos profiles.
4. Se a automação conflitar com a arquitetura atual, parar antes de compactação ou rollout adicional e pedir autorização para neutralizar somente o gatilho ativo. Preferir comentar/desabilitar a linha de cron com backup e preservar o script para rollback, em vez de apagar artefatos.
5. Validar após a correção: gatilho ausente/inativo, profiles pairwise diferentes, inferência real por profile e nenhuma alteração de credencial fora do escopo.
6. Corrigir também USER/MEMORY/SOUL que ainda descrevam modelo, curator ou sync legado, mas tratar essa reescrita como mutação separada com diff explícito quando houver promessa de revisão prévia.

Pitfall: três logins device-code independentes podem estar corretos agora e ainda assim serem revertidos silenciosamente quinze minutos ou semanas depois por um sincronizador global legado. A ausência de write no dry-run não elimina o risco futuro.

Formato esperado em cada `config.yaml`:

```yaml
model:
  default: gpt-5.6-sol
  provider: openai-codex
  base_url: 'https://chatgpt.com/backend-api/codex'
```

### Verificação sem vazar tokens

```bash
python3 - <<'EOF'
import json
for path in ['/root/.hermes/auth.json', '/root/.hermes/profiles/zeus/auth.json', '/root/.hermes/profiles/atena/auth.json']:
    print(path)
    with open(path) as f:
        d=json.load(f)
    p=d.get('providers',{}).get('openai-codex',{})
    tokens=p.get('tokens',{}) if isinstance(p,dict) else {}
    print('  active_provider:', d.get('active_provider'))
    print('  auth_mode:', p.get('auth_mode') if isinstance(p,dict) else None)
    print('  access_token_len:', len(tokens.get('access_token','')))
    print('  refresh_token_present:', bool(tokens.get('refresh_token')))
EOF

grep "provider:\|default:" /root/.hermes/profiles/zeus/config.yaml /root/.hermes/profiles/atena/config.yaml | grep -v "auto\|haiku\|edge\|local"
```

### Auditoria read-only de backups OAuth/JWT

Quando uma cópia histórica de `auth.json` aparecer em reports, snapshots ou backups, não classifique como “stale” apenas pela data, pelo nome da pasta ou porque alguns JWTs expiraram.

Auditoria sem expor valores:

1. Validar arquivo regular, symlink, owner, modo do arquivo e permissões de todos os diretórios pais (`stat` + `namei`).
2. Confirmar JSON válido e reportar somente nomes de providers/campos sensíveis; nunca valores, hashes ou trechos de token.
3. Extrair internamente apenas `access_token`, `refresh_token` e `id_token`. Decodificar `exp` de JWT somente para contagem expirado/futuro; um refresh token pode continuar sensível mesmo quando access/id JWTs expiraram.
4. Comparar por igualdade interna com os auth stores atuais. Qualquer refresh/token coincidente torna o backup **cópia sensível ativa**, não material morto.
5. Diferenciar localização física de estado Git: um arquivo pode estar dentro da árvore do repositório, porém ignorado e não rastreado. Verificar `git ls-files`, `git check-ignore`, árvore rastreada atual e histórico.
6. Para o histórico, procurar os valores sem colocá-los em argv/output. Se a varredura por cada árvore/blob for lenta, usar um único fluxo `git log --all --full-history --no-ext-diff --text -p` e comparar chunks em memória, preservando overlap de `max_token_length-1`; reportar somente bytes examinados e contagem de matches.
7. Procurar cópias exatas em diretórios seguros e validar `0700/0600`; listar apenas paths e metadados.
8. Encerrar a auditoria com quatro estados separados: exposição pública/Git, cópia local protegida, coincidência com credencial atual e lacuna de cobertura.

Auditoria read-only não autoriza apagar, mover ou rotacionar. Exclusão de backup sensível e reautenticação/rotação são operações separadas: apresentar escopo exato, autenticação que permanece, backups preservados e risco de lockout antes da confirmação crítica.

### Cron jobs e custo após migração

- Cron agent-based sem override herda provider/model do perfil. Após migração para Codex, jobs com `model/provider: null` passam a herdar `openai-codex` + `gpt-5.5`.
- Preferir `script` + `no_agent: true` para watchdogs determinísticos.
- Antes de reativar cron antigo, auditar model/provider e evitar fallback Anthropic acidental.
- Procurar `ANTHROPIC_API_KEY`, `api.anthropic.com`, `anthropic.Anthropic`, `claude-*`, `provider: anthropic` em serviços/repos ativos.

Referências: `references/openai-codex-cron-model-pinning.md`, `references/openai-codex-anthropic-api-decommission.md`, `references/openai-codex-cost-monitoring-gpt-oauth.md`.

### Purge total Anthropic/Claude quando Rodolfo exigir GPT-5.5 para tudo

Quando Rodolfo disser “GPT-5.5 pra tudo”, “zero Anthropic”, “deleta de tudo” ou equivalente, usar o playbook `references/openai-codex-gpt55-all-profiles-purge.md`. Regra operacional: depois de confirmação crítica, limpar **root + profiles + backups/snapshots**, não só `config.yaml`. Validar `providers.anthropic=false`, `credential_pool.anthropic=false`, `active_provider=openai-codex`, auxiliares pinados em `openai-codex/gpt-5.5`, scan de `sk-ant-*` real igual a zero fora do código-fonte/testes/docs upstream, e gateways reconectados.

### Pitfalls de provider/OAuth

- `hermes model --status` não existe; verificar config/auth diretamente.
- Endpoint Codex não lista modelos via API (`/codex/models` pode retornar 400; `/backend-api/models` 403).
- Token expira; refresh normal é automático. Em falhas, aplicar primeiro o gate de incidente acima; reautenticação só quando a credencial daquele profile continuar comprovadamente inválida, com confirmação crítica. A antiga sugestão de recópia entre profiles está supersedida pela regra de cadeias OAuth independentes.
- Não manter Claude/Haiku como fallback silencioso após decisão de custo.
- Backups de `auth.json`/tokens/OAuth NUNCA devem ser criados dentro de `/root/mgs-agent` ou qualquer path versionado/auto-commitado. Se precisar de rollback, usar diretório fora do Git com permissão `700` (ex.: `/root/.hermes/secure-backups/<agent>/`) e validar `git -C /root/mgs-agent status` imediatamente; remover/shredar qualquer cópia sensível criada por engano antes de continuar.
- Quando limpar Anthropic/Claude, remover também `credential_pool.anthropic`, root `~/.hermes/auth.json`, root `~/.hermes/.env`, snapshots/backups com credenciais e espelhos versionados em `/root/mgs-agent/profiles/`; só limpar `providers.anthropic` nos profiles é insuficiente.
- Alguns serviços fora do gateway podem continuar chamando Anthropic mesmo depois de migrar Zeus/Atena/Ares.
- OpenHands “funcionando” não basta: se wrapper/trajectory usa `anthropic/claude-*` + API key 1Password, isso é uma falha de custo/governança salvo autorização explícita de Rodolfo. Diagnóstico canônico: `references/atena-openhands-provider-diagnostic.md`.
- Para OpenHands na Atena/Zeus, a política correta é **GPT-5.5/OpenAI-Codex OAuth para tudo por padrão**. Não sugerir “backend não-Anthropic aprovado” genérico, OpenRouter, Haiku ou Claude como workaround. Se OpenHands precisar de compatibilidade com Codex, forçar `openai/gpt-5.5`, usar OAuth do profile sem imprimir token e validar o modelo real no output. Playbook: `references/openhands-gpt55-codex-wrapper.md`.
- Quando um agente MGS falhar em thread Discord com `Provider authentication failed` e logs OpenAI-Codex mostrarem refresh inválido, reparar o profile antes de responder: backup fora do Git, reautenticação OAuth independente preferida, smoke `hermes -p <agent> -z ...`, resposta na thread original e readback Discord. Copiar um bloco válido de outro profile só como recuperação emergencial temporária após confirmação crítica; nunca chamar isso de correção durável por causa de `refresh_token_reused`. Playbook: `references/mgs-agent-codex-auth-repair-and-thread-reply.md` e `references/gpt56-sol-auto-reasoning-routing-mgs.md`.
