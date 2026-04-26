---
name: hermes-profile-versioning
description: "Versiona arquivos de profile Hermes (SOUL.md, config.yaml, etc) via git. Documenta o comportamento de symlinks no git e as alternativas reais validadas em 2026-04-24."
tags: [hermes, soul, git, versioning, symlink, profile]
---

# Versionamento de arquivos de profile Hermes via git

## Contexto

Arquivos de identidade dos agentes Hermes (SOUL.md, config.yaml) ficam em:
```
/root/.hermes/profiles/{agent}/SOUL.md
/root/.hermes/profiles/{agent}/config.yaml
```

O repositório com auto-push ativo é `/root/mgs-agent` (push automático via `mgs-autocommit.service`).

O objetivo é versionar e fazer backup remoto desses arquivos via GitHub.

---

## ⚠️ PITFALL CRÍTICO: Symlink NÃO versiona conteúdo

**Testado e confirmado em 2026-04-24.**

```bash
ln -s /root/.hermes/profiles/zeus/SOUL.md /root/mgs-agent/profiles/zeus-soul.md
git add profiles/zeus-soul.md
git commit -m "add symlink"
```

O git armazena o **apontador** (o path), não o conteúdo:
```
git show HEAD:profiles/zeus-soul.md → /root/.hermes/profiles/zeus/SOUL.md
git ls-files -s profiles/ → 120000 ... (mode 120000 = symlink, não arquivo)
```

**Consequência:** Mudanças no SOUL.md real não aparecem em `git diff`, não disparam auto-push, e não são rastreadas. O repositório só sabe que o link *existe*.

---

## Alternativas reais

| Opção | Funciona? | Notas |
|---|---|---|
| Symlink (`ln -s`) | ❌ para conteúdo | Git rastreia apontador, não conteúdo |
| Hardlink (`ln`) | ✅ se mesmo filesystem | Git vê como arquivo real; falha cross-filesystem |
| Mover SOUL.md para mgs-agent + symlink inverso | ✅ | Git versiona direto; Hermes lê via symlink |
| Cópia periódica via cron/script | ✅ | Simples, confiável, sem acoplamento |
| Git hook pós-edição | ✅ | Mais complexo |

---

## Solução recomendada: mover + symlink inverso

**Mais limpo e sem duplicação:**

```bash
# 1. Mover o arquivo real para dentro do repo
mv /root/.hermes/profiles/zeus/SOUL.md /root/mgs-agent/profiles/zeus-soul.md

# 2. Criar symlink de volta para onde Hermes espera encontrar
ln -s /root/mgs-agent/profiles/zeus-soul.md /root/.hermes/profiles/zeus/SOUL.md

# 3. Validar que Hermes ainda lê corretamente
cat /root/.hermes/profiles/zeus/SOUL.md | head -5  # deve mostrar conteúdo real

# 4. Validar que git agora detecta mudanças de conteúdo
echo "test" >> /root/mgs-agent/profiles/zeus-soul.md
git -C /root/mgs-agent diff profiles/zeus-soul.md  # deve mostrar diff real
```

**Resultado esperado em `git ls-files -s`:** mode `100644` (arquivo real), não `120000` (symlink).

---

## Solução alternativa: cópia periódica via cron Hermes

Se mover o arquivo for indesejável (ex: Hermes tem lógica que verifica ownership do path):

```bash
# Script de cópia — executar após cada edição do SOUL.md
cp /root/.hermes/profiles/zeus/SOUL.md /root/mgs-agent/profiles/zeus-soul.md
cp /root/.hermes/profiles/atena/SOUL.md /root/mgs-agent/profiles/atena-soul.md
cd /root/mgs-agent && git add profiles/ && git commit -m "chore(profiles): sync SOUL.md snapshots"
```

Ou via cronjob Hermes agendado diariamente.

---

## Solução implantada em produção — cópia periódica via cron (2026-04-24, estendida 2026-04-26)

Rodolfo escolheu a cópia periódica como solução definitiva. O script sincroniza **SOUL.md + skills MGS-específicas**.

**Script:** `/root/mgs-agent/scripts/sync-souls.sh`
```bash
#!/bin/bash
# Sync SOUL.md + MGS-specific skills from Hermes profiles to mgs-agent for versioning
set -e

PROFILES_DIR="/root/.hermes/profiles"
TARGET_DIR="/root/mgs-agent/profiles"
mkdir -p "$TARGET_DIR"

# ── SOUL.md sync ───────────────────────────────────────────────────────────
for agent in zeus atena; do
    SOURCE="$PROFILES_DIR/$agent/SOUL.md"
    TARGET="$TARGET_DIR/$agent-soul.md"
    if [ -f "$SOURCE" ] && [ "$SOURCE" -nt "$TARGET" ]; then
        cp "$SOURCE" "$TARGET"
        echo "$(date -Iseconds) synced $agent SOUL"
    fi
done

# ── Skills MGS-específicas sync ────────────────────────────────────────────
# Zeus: ops/ (skills de infra e deploy MGS)
mkdir -p "$TARGET_DIR/zeus-skills"
rsync -a --delete \
    "$PROFILES_DIR/zeus/skills/ops/" \
    "$TARGET_DIR/zeus-skills/ops/" \
    && echo "$(date -Iseconds) synced zeus skills/ops"

# Atena: wordpress/ + devops/ (skills WP e deploy MGS-específicas)
mkdir -p "$TARGET_DIR/atena-skills"
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
- `profiles/zeus-soul.md` — SOUL.md do Zeus
- `profiles/atena-soul.md` — SOUL.md da Atena
- `profiles/zeus-skills/ops/` — skills operacionais MGS do Zeus (12 skills)
- `profiles/atena-skills/wordpress/` — skills WP da Atena (3 skills)
- `profiles/atena-skills/devops/` — skills devops da Atena (3 skills)

**Por que rsync para skills (e não -nt como SOUL.md):** SOUL.md é 1 arquivo — `-nt` (mtime) é suficiente. Skills são árvores de diretórios — `rsync -a --delete` detecta adições, modificações e deleções de forma atômica. O `--delete` propaga remoções para o repo (sem ele, skills deletadas ficam "zumbis" no git).

**Ciclo validado end-to-end:**
1. Editar/criar skill em `.hermes/profiles/{agent}/skills/ops/` (ou wordpress/, devops/)
2. Cron roda no próximo tick de 5 min → rsync detecta e copia
3. `mgs-autocommit.service` detecta via inotify → commit automático → push GitHub
4. Log: `2026-04-26T16:11:08-04:00 synced zeus skills/ops`

**Pitfall `-nt`:** a flag `-nt` compara mtime. Se TARGET não existir, a condição retorna true (target inexistente = mtime=0) — funciona corretamente na primeira execução.

**Política de extensão:** se nova skill MGS-específica for criada em categoria não coberta (ex: `zeus/skills/data-science/`), adicionar ao bloco rsync do script E reportar via `[REPORT-INFRA]`. Skill fora do sync = não versionada = sem rastreabilidade.

---

## Diagnóstico rápido: symlink vs arquivo real no git

```bash
# Verificar mode (120000 = symlink, 100644 = arquivo real)
git ls-files -s profiles/

# Ver o que git armazenou como conteúdo
git show HEAD:profiles/zeus-soul.md

# Teste definitivo: editar e checar diff
echo "x" >> /root/.hermes/profiles/zeus/SOUL.md
git -C /root/mgs-agent diff  # vazio se symlink, diff real se arquivo
```
