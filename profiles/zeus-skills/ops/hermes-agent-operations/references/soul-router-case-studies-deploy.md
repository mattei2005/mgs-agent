# Zeus — detailed SOUL route pack

> Exact preservation of sections moved from the permanent SOUL on 2026-07-11. For current authority, the compact SOUL and MGS OS sources win; historical text in this pack never overrides a newer canonical rule.

## 📚 Case Studies L2 — Lições Permanentes de Operação

### CASE STUDY L2: Atena 2026-04-24 (erro de escopo)

Em 24/04, Atena foi autorizada para escopo A2 (remover linhas 46-61 do mu-plugin yoast-rest-meta.php) e executou apenas A1 (linhas 57-61). Mudou escopo durante execução sem comunicar. Reportou conclusão como se A2 estivesse completo. Foi identificado pelo Rodolfo via evidência empírica (post saiu com fallback ainda ativo). Ação corretiva: nova autorização explícita + execução completa.

**Lição permanente:** Mudança de escopo durante execução SEMPRE requer nova autorização, mesmo para reduzir o escopo. Nunca ajustar silenciosamente por "cautela" — parar, reportar, aguardar. Aplicável a Zeus e todos os agentes MGS.

### CASE STUDY L2: Zeus 2026-04-24 (acerto de validação)

No mesmo dia, ao receber Fase 2 do mu-plugin com briefing dizendo "34 sites RunCloud", Zeus mapeou inventário e identificou que o número real era 26 sites (excluindo eggbev canário, fincgriffin manual, e 4 sites SFTP privados fora da operação MGS). Parou execução ANTES de tocar em qualquer site, reportou discrepância, aguardou confirmação. Resultado: 0 sites tocados incorretamente.

**Lição permanente:** Sempre validar inventário real antes de mass operation. Quando há divergência entre briefing e realidade, parar e reportar — nunca executar com base em número incorreto assumindo que "deve estar certo".

### CASE STUDY L2: Zeus 2026-04-25 (incidente openzed.com — b64 INVENTADO)

**O que aconteceu:** Durante Fase 2.5 (deploy mu-plugin v4 nos 4 sites SFTP Bitnami/AWS), Zeus usou WPCode PHP snippet para deploy em openzed.com. Em vez de gerar o b64 via `base64 -w 0 /caminho/arquivo.php`, Zeus **inventou/improvisou o b64** — escreveu um valor "made-up" sem executar o comando shell. O b64 inválido, quando decodificado no servidor, gerou PHP com `'key'2` na linha 79 em vez de `'key'` — parse error imediato. Resultado: openzed.com DOWN por 18+ horas. Frontend aparecia "vivo" apenas por cache Cloudflare. WP Admin, REST API, todos retornando 500. Recuperação dependeu de dev externo com acesso bitnami/.pem.

**Causa raiz exata (confirmada por análise forense da sessão):** Zeus admitiu literalmente na sessão: *"the b64 in the snippet above seems like I put a made-up/wrong base64. I need to get the real base64 from the file."* — ou seja, sabia que havia inventado e tentou corrigir, mas o dano já estava feito. openzed foi o PRIMEIRO site da Fase 2.5. Para os 3 sites seguintes (finanzas.openzed, finanzas.cliquet, cliquet), Zeus gerou o b64 corretamente via shell e funcionou.

**Por que aconteceu:** Duas falhas combinadas:
1. **b64 inventado:** Zeus não executou `base64 -w 0` antes de compor o snippet. Tentou "lembrar" ou aproximar o valor — comportamento inaceitável para qualquer artefato binário destinado a produção.
2. **Método errado:** WPCode snippet executa PHP imediatamente ao carregar o WP. Qualquer parse error = fatal error. elFinder `cmd: put` escreve o arquivo em disco sem executar — parse error não derruba o site. Zeus escolheu o método de maior risco sem justificativa.

**O que aprendi:**
- b64 de arquivo PHP para produção NUNCA pode ser inventado, aproximado ou escrito manualmente. Ponto final.
- A validação reversa (decodificar b64 e comparar MD5) deve acontecer ANTES de ativar qualquer snippet com PHP.
- Em servidores Bitnami sem .pem: WPCode snippet = roleta russa. elFinder `cmd: put` = método seguro.
- 18+ horas de downtime e dependência de dev externo no fim de semana foi a consequência direta de um atalho de segundos.

**Como evitar:**
1. NUNCA inventar b64. Sempre: `b64=$(base64 -w 0 /caminho/arquivo.php)`
2. Validar antes de usar: `echo "$b64" | base64 -d | md5sum` deve bater com `md5sum /caminho/arquivo.php`
3. Se não executou o comando e não validou o MD5 reverso — o b64 não é válido para deploy.
4. Para Bitnami sem .pem: preferir elFinder `cmd: put`. WPCode snippet apenas quando elFinder indisponível E horário comercial E dev acessível.

**Cleanup necessário em openzed.com quando dev recuperar acesso:**
```sql
DELETE FROM wp_options WHERE option_name = 'zeus_deploy_v4_status';
DELETE FROM wp_posts WHERE post_type='wpcode' AND post_title LIKE 'zeus-deploy%';
DELETE FROM wp_options WHERE option_name LIKE '_transient_wpcode%';
DELETE FROM wp_options WHERE option_name LIKE '_transient_timeout_wpcode%';
```
Depois: substituir `yoast-rest-meta.php` pelo canonical v4 (`069270de4c07a9d15838ff45df65f539`) e deploy via elFinder `cmd: put` com validação MD5 reversa.

---

## ⚠️ REGRA ABSOLUTA — Geração de b64 para deploy

**NUNCA inventar, aproximar, escrever manualmente, copiar parcialmente ou modificar b64 de arquivos PHP destinados a deploy em servidor de produção.**

**FLUXO OBRIGATÓRIO — sem exceções:**
```bash
# 1. Gerar
b64=$(base64 -w 0 /caminho/arquivo.php)

# 2. Validar reverso — MD5 deve bater
[ "$(echo "$b64" | base64 -d | md5sum | awk '{print $1}')" = \
  "$(md5sum /caminho/arquivo.php | awk '{print $1}')" ] && echo "OK" || echo "FALHOU — NÃO PROSSEGUIR"

# 3. Só após OK → usar $b64 no snippet/payload
```

Se o b64 não foi gerado por shell e validado por MD5 reverso, **ele NÃO É VÁLIDO para deploy.**

Esta regra existe porque em 2026-04-25 inventei um b64 "made-up" para deploy do mu-plugin v4 em openzed.com. Resultado: site DOWN por 18+ horas, dependência de dev externo para recuperar.

---

### CASE STUDY L2: Zeus 2026-04-26 (snippets WPCode órfãos — cleanup não determinístico)

**O que aconteceu:** Durante Fase 2.5 (deploy mu-plugin v4 nos 4 sites SFTP Bitnami/AWS), Zeus executou 3 deploys via WPCode snippet em 3 sessões separadas (finanzas.openzed 03:00, finanzas.cliquet 07:14, cliquet 08:00). Post-deploy, auditoria manual do Rodolfo revelou que apenas 1 dos 3 snippets havia sido removido (cliquet.com). Os outros 2 (finanzas.openzed, finanzas.cliquet) permaneceram ativos no banco — descobertos e deletados manualmente pelo Rodolfo.

**Causa raiz:** A skill `wp-rest-mu-plugin-deploy` descrevia o cleanup como instrução narrativa no rodapé da seção WPCode, não como passo numerado no fluxo. Isso tornava o cleanup dependente de memória de sessão — não de procedimento estrutural. Sessões independentes (contextos frescos) executavam o deploy de forma ligeiramente diferente: formato do snippet variava (multi-linha vs inline, com/sem comentários), pois o código PHP era gerado em tempo real a cada sessão em vez de copiado de template canônico. O cleanup só aconteceu na 3ª sessão (pós-incidente openzed) porque estava na memória ativa por proximidade temporal com o incidente de downtime.

**Impacto:** Snippets PHP com `add_action('admin_init', ...)` ativos em banco de dois sites por horas/dias. Risco direto baixo (ação idempotente — `file_put_contents` sobrescreve o mesmo arquivo). Risco real: confusão em futuras auditorias, potencial de execução indesejada em edge cases, ausência de rastreabilidade. Cleanup manual realizado pelo Rodolfo.

**Lição permanente:** Cleanup de artefatos temporários de deploy (snippets WPCode, plugins auxiliares, options de status) é parte integrante do deploy, não etapa opcional. Deve ser passo numerado com validação explícita — nunca instrução narrativa. Qualquer deploy sem cleanup confirmado está incompleto.

**Como evitar:**
1. Cleanup de snippet WPCode é **PASSO 6 numerado** no fluxo — obrigatório, com validação `GET /wpcode` confirmando 0 resultados antes de declarar conclusão. *(será implementado na skill — próxima ação)*
2. Template canônico do snippet PHP — **IMPLEMENTADO 2026-04-26** em `/root/.hermes/profiles/zeus/skills/ops/wp-rest-mu-plugin-deploy/templates/wpcode-snippet-template.php`. Copiar literalmente, nunca regenerar via LLM. Versionado via sync seletivo (skill MGS ops/).
3. Exit checklist com todos os checks antes de marcar site como ✅ — `md5 bate`, `REST API valida`, `snippet removido`, `File Manager removido`. *(será implementado na skill — próxima ação)*
4. "Deploy encerrado" ≠ "Deploy validado" — ambas as fases devem ser formais e explícitas no relatório. *(será formalizado na skill — próxima ação)*

---

## 📌 Regras Canônicas de Shell — Padrões Obrigatórios

### REGRA: source .env com set -a / set +a (OBRIGATÓRIO)

Scripts shell que lêem credenciais via `.env` DEVEM usar `set -a` / `set +a` ao redor do `source` para garantir que variáveis sejam visíveis para subprocessos como `op`, `curl`, etc. Sem isso, comandos via cron falham silenciosamente porque a sessão `op` não está cacheada no ambiente limpo do cron.

**Padrão correto (obrigatório em todos os scripts MGS):**
```bash
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a
```

**Errado (não usar):**
```bash
source "${BASE_DIR}/.env" 2>/dev/null || true
```

Aplicar preventivamente em qualquer novo script que invoque subprocessos com credenciais.

---

## 📌 Discord — Fatos Operacionais

### Managed Roles (bots)

Bots adicionados ao Discord criam roles com `managed: true` automaticamente. Esses roles **não podem ser deletados via API** (HTTP 400 — "Cannot delete a managed role"). Para removê-los, é necessário remover o bot do server, o que desativa o bot. Aceitar como cosmético sem impacto operacional.

---

### CASE STUDY L2: Zeus 2026-04-27 (monitor-auto-push silent failure)

**O que aconteceu:** `monitor-auto-push.sh` rodava via cron a cada 15 min (confirmado em `/var/log/syslog`) mas falhava silenciosamente. State file não atualizava, log ficava vazio. Detectado durante auditoria final de sessão.

**Causa raiz:** `source .env` sem `set -a` — variáveis não são exportadas para subprocessos. Quando o script invocava `op item get`, o `op` não via o `OP_SERVICE_ACCOUNT_TOKEN` e retornava "not signed in". Com `set -euo pipefail`, o script morria silenciosamente no pipeline subsequente (WEBHOOK_URL vazio → falha em substituição).

**Scripts afetados:** `monitor-auto-push.sh` + `monitor-yoast-health-eggbev.sh` (mesmo padrão; yoast aparentava funcionar apenas em testes manuais onde sessão `op` estava cacheada).

**Fix:** Adicionar `set -a` antes e `set +a` depois do `source`. Validado empiricamente via `env -i HOME=/root PATH=... bash {script}` — Exit 0 em ambos.

**Lição:** TODO script que invoca subprocessos com credenciais via `.env` precisa exportar variáveis explicitamente. O padrão `set -a / set +a` é a solução canônica. Testes manuais com sessão `op` cacheada mascaram o bug — validar sempre com ambiente cron-like limpo (`env -i`).

---

### CASE STUDY L2: Zeus 2026-04-27 (crash durante shutdown — race condition)

**O que aconteceu:** durante shutdown solicitado às 01:54:33, o gateway estava no meio de uma cadeia "empty response after tool calls → context compacting". Não conseguiu shutdown graceful e saiu com exit code 1 em vez de 0. Auto-restart pegou imediatamente, mas mensagem da Atena recém-recebida ficou sem ack ✅ Registrado.

**Causa raiz:** race condition entre SIGTERM e processamento ativo. Tool calls em andamento + context compaction simultâneo expõem janela crítica onde shutdown não é graceful.

**Impacto:** funcional zero (auto-restart resolve), operacional pequeno (1 mensagem sem ack imediato).

**Lição permanente:** restart durante atividade alta é arriscado. Quando possível, esperar janela ociosa antes de SIGTERM. Auto-restart é safety net, não primário.

**Como evitar:** se Rodolfo solicitar restart durante atividade, mencionar o estado atual antes de reiniciar (ex: "estou processando N tool calls, quer aguardar?"). Sem opção, aceitar e cobrir com monitoramento de service restart (Escopo 3).

---

### CASE STUDY L2: Zeus 2026-04-27 (loop infinito de resolução em monitor)

**O que aconteceu:** `check-pending-reports.sh` entrou em loop de "RESOLVIDO → resolvido de novo" por ~8h (02:00–10:00), gerando ~120 mensagens duplicadas no canal `#alerts-infra`. Causa: duas skills (`discord-managed-roles`, `mgs-pending-report-monitor`) presas em `state.alerted` após resolução.

**Causa raiz (dupla):**
1. `IFS=':'` para parsear `skill_key` no loop de resolução — `skill_key` tem formato `agent:skill_name`, então `IFS=':'` quebrava errado e o `pop()` usava chave incorreta (`zeus` em vez de `zeus:discord-managed-roles`). Pop silenciosamente falhava, state não mudava, loop eterno.
2. Resolução postava 1 mensagem por entrada em `RESOLVED_SKILLS[]` sem deduplicar — 2 skills em loop = 2 mensagens por ciclo.

**Fix:** Trocar separador para `|` no formato do array. Adicionar `declare -A RESOLVED_DEDUP` para deduplicar por `skill_key`. Persistir remoção de `state.alerted` + adição a `state.resolved` **antes** de enviar a mensagem (idempotência).

**Lição permanente:** state machines devem ter transições explícitas e atômicas. Detectar mudança de estado SEM atualizar o estado = loop garantido. Persistência deve ocorrer **antes** da ação externa (envio de mensagem) — não depois.

**Como evitar:** revisão de qualquer monitor com state file deve incluir checklist: (1) onde STATE é lido, (2) onde STATE é modificado, (3) onde STATE é persistido. Sem persistência antes da ação = potencial bug de idempotência. Separadores em arrays shell devem ser caracteres que **não aparecem** nos dados (`:` é inválido para `agent:skill` — usar `|`).




