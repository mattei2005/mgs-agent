### Quando usar
- SOUL.md de algum agente precisa de backup remoto / histórico git
- Novo agente criado e precisa ter SOUL.md rastreado
- Skills MGS-específicas precisam ser versionadas no repo
- Rodolfo pede ajuste de tom/verbosity/persona operacional do Zeus ou Atena
- Rodolfo pede uma “indexação”/auditoria de contexto sem mexer em providers de memória
- Rodolfo pede validação de acesso GitHub ou varredura completa de repositório privado/público

Para varredura GitHub/repo, ver `references/github-repo-audit.md`: validação segura de PAT via 1Password sem persistir credencial no remote, `GIT_ASKPASS` temporário, checklist de secrets atual+histórico, varredura de arquivos comprimidos no histórico (`*.tar.gz` com `.env`/profiles), sintaxe, crons/logs, dependências e relatório executivo. Ao reportar achados de secrets, nunca imprimir valores; separar `current tree clean` de `history dirty`, confirmar revogação/exposição externa antes de propor reescrita destrutiva de histórico.

Para hardening iterativo do `/root/mgs-agent`, ver também `references/mgs-repo-hardening-audit.md`: cobre pitfalls duráveis desta classe (`grep -c` gerando `0\n0`, guardrail contra auto-commit de segredos, detecção semântica de erro em cron fresco, SSH `accept-new` + `known_hosts_mgs`, stubs para scripts deprecated e higiene de runtime/backups versionados).

Para hardening pós-auditoria do repo MGS, ver `references/mgs-repo-hardening-audit-2026-05-16.md`: cobre correções reutilizáveis de `grep -c` com `set -e`, guardrails do auto-commit watcher, detecção semântica de erro em cron logs, SSH/SCP com `accept-new` + `known_hosts_mgs`, stubs para scripts deprecated, higiene de backups/runtime e ACK imediato em botões Discord.

Para a fase final de dependências/tooling, ver `references/mgs-deps-tooling-audit.md`: enumeração de manifests, `npm audit/outdated/test` sem upgrades destrutivos, conversão de API legacy Anthropic/FastAPI para stub fail-closed quando o serviço já está masked/inactive, e checklist de validação.

Para lint Bash profundo com ShellCheck durante hardening MGS, ver `references/mgs-shellcheck-hardening.md`: instalação aprovada, escopo de scripts rastreados, priorização de error/warning, correção do pitfall `cmd | python <<HEREDOC` (stdin sobrescrito), e formato de validação/relatório.

Para o fechamento pós-hardening, ver `references/mgs-hardening-release-hygiene.md`: classificar referências históricas vs runtime ativo, consolidar release note em `docs/changelog/`, documentar commits fragmentados do auto-commit watcher e validar git/serviços antes do relatório final.

### Ajustes de tom/verbosity, layout visual e contexto semântico

Ver `references/atena-profile-prompt-slimming.md` quando o objetivo for reduzir latência/loop de leitura da Atena no Discord: manter `SOUL.md` e `channel_prompts` curtos, remover leitura obrigatória de AGENT.md, evitar scripts longos de rename/mention antes de REC direto, sincronizar via `sync-souls.sh` e reiniciar/validar o gateway.

Ver `references/hermes-profile-style-context-ops.md` para o padrão validado de:
- adicionar “Modo executivo curto — teste ativo” no SOUL.md sem colar persona crua de curso;
- criar backup e rollback de SOUL.md;
- manter `reasoning_effort` inalterado quando o usuário pedir;
- fazer um manifesto read-only dos arquivos de memória/contexto como equivalente seguro de “indexação” sem mudar memória;
- rodar warm-up pós-troca de modelo/profile.

Ver também `references/agent-response-layout-standard.md` para o padrão MGS de respostas visuais no Discord: quando houver dados estruturados/comparáveis, usar bloco monoespaçado `text` com colunas alinhadas e separadores; os nomes das colunas devem nascer do contexto da thread, nunca ser copiados de exemplos. Se Rodolfo apontar regressão visual após update, auditar a regra em todos os agentes ativos (Zeus/Atena/Ares/agente legado/futuros) antes de culpar o renderer Hermes; novos profiles podem estar sem a regra mesmo quando os antigos estão corretos.

**Pitfall recorrente — tabela Markdown crua após update/reports:** se Rodolfo mostrar print reclamando que o “modo de tabela voltou ao padrão Hermes” ou que apareceu `|---|---|`, primeiro tratar como possível regressão de **formato de resposta**, não como patch quebrado. Verificar rapidamente: (1) SOUL/AGENT.md ainda contêm a regra de bloco `text`; (2) `display.final_response_markdown` é configuração de CLI/TUI e não corrige Discord; (3) Discord adapter normalmente envia Markdown como texto/render padrão, sem converter para o layout MGS; (4) se os patches MGS de thread/restart passaram no guard, eles não explicam tabela crua. Correção operacional imediata: reconhecer que a resposta violou o padrão MGS e voltar a emitir comparativos em bloco `text` alinhado.

Quando Rodolfo pedir para aplicar padrões de Zeus/Atena em agente novo/existente (ex: Ares) ou reclamar de tabelas Markdown cruas `|---|---|`, usar `references/mgs-agent-profile-pattern-rollout.md`. Esse playbook cobre auditoria comparativa SOUL/config/autorização/systemd, regra de layout `text`, sync de skills MGS-específicas (`Ares: growth/`) e o cuidado de double-confirm antes de editar `AGENT.md`.

Quando Rodolfo pedir para aplicar padrões do Zeus/Atena ao Ares ou outro agente novo, usar `references/agent-profile-parity-audit.md`: auditar SOUL/config ativos e cópias em `/root/mgs-agent/profiles/`, autorização, systemd, thread behavior, REPORT-INFRA, no-secret, validação e sync de skills MGS-específicas. O padrão visual `|---|---| porém em tabela` deve ser traduzido para bloco `text` alinhado, não tabela Markdown crua.

### ⚠️ PITFALL CRÍTICO: Symlink NÃO versiona conteúdo

```bash
ln -s /root/.hermes/profiles/zeus/SOUL.md /root/mgs-agent/profiles/zeus-soul.md
git add profiles/zeus-soul.md
# git armazena O APONTADOR (mode 120000), não o conteúdo
git show HEAD:profiles/zeus-soul.md → /root/.hermes/profiles/zeus/SOUL.md
```

Mudanças no SOUL.md real **não aparecem em `git diff`**, não disparam auto-push. Testado e confirmado em 2026-04-24.

### Solução implantada em produção — cópia periódica via cron

Script `/root/mgs-agent/scripts/sync-souls.sh` sincroniza SOUL.md + skills MGS-específicas:

```bash
#!/bin/bash
set -e

PROFILES_DIR="/root/.hermes/profiles"
TARGET_DIR="/root/mgs-agent/profiles"
mkdir -p "$TARGET_DIR"

# SOUL.md sync (mtime check)
for agent in zeus atena; do
    SOURCE="$PROFILES_DIR/$agent/SOUL.md"
    TARGET="$TARGET_DIR/$agent-soul.md"
    if [ -f "$SOURCE" ] && [ "$SOURCE" -nt "$TARGET" ]; then
        cp "$SOURCE" "$TARGET"
        echo "$(date -Iseconds) synced $agent SOUL"
    fi
done

# Skills MGS-específicas sync (rsync com --delete)
mkdir -p "$TARGET_DIR/zeus-skills"
rsync -a --delete \
    "$PROFILES_DIR/zeus/skills/ops/" \
    "$TARGET_DIR/zeus-skills/ops/" \
    && echo "$(date -Iseconds) synced zeus skills/ops"

for category in wordpress devops; do
    if [ -d "$PROFILES_DIR/atena/skills/$category" ]; then
        rsync -a --delete \
            "$PROFILES_DIR/atena/skills/$category/" \
            "$TARGET_DIR/atena-skills/$category/" \
            && echo "$(date -Iseconds) synced atena skills/$category"
    fi
done
```

**Crontab:** `*/5 * * * * /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`

**Destinos no git:**
- `profiles/zeus-soul.md` / `profiles/atena-soul.md` — SOUL.md dos agentes
- `profiles/zeus-skills/ops/` — skills operacionais MGS do Zeus
- `profiles/atena-skills/wordpress/` e `atena-skills/devops/` — skills MGS da Atena

**Por que rsync para skills (não `-nt`):** SOUL.md é 1 arquivo — mtime é suficiente. Skills são árvores de diretórios — `rsync -a --delete` detecta adições, modificações e deleções. O `--delete` propaga remoções.

