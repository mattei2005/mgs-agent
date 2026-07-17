# Providers, Models, and OpenAI Codex OAuth

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 3. Providers, modelos e OpenAI Codex OAuth

Use quando Rodolfo quiser trocar provider de Zeus/Atena/Ares, usar GPT via assinatura ChatGPT, reduzir custo Anthropic/Claude, autenticar `openai-codex`, validar cron jobs após migração, ou auditar chamadas LLM pagas.

Para rollout de modelo/reasoning em múltiplos profiles, incluindo distinção principal vs. auxiliares, verificação auth por agente, smoke real 4/4, limites de `xhigh` vs. Sol Pro e proibição de chamar default fixo de “roteamento automático”, use `references/openai-codex-multi-profile-model-rollout.md`.

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

### OAuth por profile — regra durável

Para produção multi-profile, autenticar cada profile por device-code e validar com inferência real. Não copiar permanentemente o mesmo bloco `openai-codex` entre profiles: refresh tokens Codex são rotativos/single-use; clones podem funcionar no smoke inicial e falhar depois com `refresh_token_reused` quando dois gateways renovarem a mesma cadeia.

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
- Token expira; refresh deve ser automático, mas falhas exigem novo `hermes model` e recópia para profiles.
- Não manter Claude/Haiku como fallback silencioso após decisão de custo.
- Backups de `auth.json`/tokens/OAuth NUNCA devem ser criados dentro de `/root/mgs-agent` ou qualquer path versionado/auto-commitado. Se precisar de rollback, usar diretório fora do Git com permissão `700` (ex.: `/root/.hermes/secure-backups/<agent>/`) e validar `git -C /root/mgs-agent status` imediatamente; remover/shredar qualquer cópia sensível criada por engano antes de continuar.
- Quando limpar Anthropic/Claude, remover também `credential_pool.anthropic`, root `~/.hermes/auth.json`, root `~/.hermes/.env`, snapshots/backups com credenciais e espelhos versionados em `/root/mgs-agent/profiles/`; só limpar `providers.anthropic` nos profiles é insuficiente.
- Alguns serviços fora do gateway podem continuar chamando Anthropic mesmo depois de migrar Zeus/Atena/Ares.
- OpenHands “funcionando” não basta: se wrapper/trajectory usa `anthropic/claude-*` + API key 1Password, isso é uma falha de custo/governança salvo autorização explícita de Rodolfo. Diagnóstico canônico: `references/atena-openhands-provider-diagnostic.md`.
- Para OpenHands na Atena/Zeus, a política correta é **GPT-5.5/OpenAI-Codex OAuth para tudo por padrão**. Não sugerir “backend não-Anthropic aprovado” genérico, OpenRouter, Haiku ou Claude como workaround. Se OpenHands precisar de compatibilidade com Codex, forçar `openai/gpt-5.5`, usar OAuth do profile sem imprimir token e validar o modelo real no output. Playbook: `references/openhands-gpt55-codex-wrapper.md`.
- Quando um agente MGS falhar em thread Discord com `Provider authentication failed` e logs OpenAI-Codex mostrarem refresh inválido, reparar o profile antes de responder: backup fora do Git, reautenticação OAuth independente preferida, smoke `hermes -p <agent> -z ...`, resposta na thread original e readback Discord. Copiar um bloco válido de outro profile só como recuperação emergencial temporária após confirmação crítica; nunca chamar isso de correção durável por causa de `refresh_token_reused`. Playbook: `references/mgs-agent-codex-auth-repair-and-thread-reply.md` e `references/gpt56-sol-auto-reasoning-routing-mgs.md`.
