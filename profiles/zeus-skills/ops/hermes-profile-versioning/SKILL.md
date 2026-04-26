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

## Solução implantada em produção (2026-04-24) — cópia periódica via cron

Rodolfo escolheu a cópia periódica como solução definitiva (SOUL.md muda raramente, overhead de cron a cada 5 min é zero).

**Script:** `/root/mgs-agent/scripts/sync-souls.sh`
```bash
#!/bin/bash
set -e
PROFILES_DIR="/root/.hermes/profiles"
TARGET_DIR="/root/mgs-agent/profiles"
mkdir -p "$TARGET_DIR"

for agent in zeus atena; do
    SOURCE="$PROFILES_DIR/$agent/SOUL.md"
    TARGET="$TARGET_DIR/$agent-soul.md"
    if [ -f "$SOURCE" ] && [ "$SOURCE" -nt "$TARGET" ]; then
        cp "$SOURCE" "$TARGET"
        echo "$(date -Iseconds) synced $agent SOUL"
    fi
done
```

**Crontab:** `*/5 * * * * /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`

**Ciclo validado end-to-end:**
1. Editar SOUL.md → MD5 diverge entre original e cópia
2. Cron roda no próximo tick de 5 min → `sync-souls.sh` detecta (`-nt` = newer than) e copia
3. `mgs-autocommit.service` detecta mudança via inotify → commit automático → push para GitHub
4. Log confirma: `2026-04-24T23:15:01-04:00 synced zeus SOUL`

**Pitfall `-nt`:** a flag `-nt` compara mtime. Se o TARGET não existir ainda, a condição falha silenciosamente. Solução: script usa `mkdir -p` e na primeira execução o TARGET não existe, então `[ "$SOURCE" -nt "$TARGET" ]` retorna true (target inexistente = mtime=0).

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
