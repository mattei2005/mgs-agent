---
name: hermes-update
description: "Processo seguro de update do Hermes Agent no VPS MGS: checagem de versão, backup de profiles, verificação de patches locais, execução do update, validação pós-update e comparação de integridade."
tags: [hermes, update, backup, profiles, gateway, zeus, atena, systemd, version]
related_skills: [discord-ops, log-monitor-discord-alert]
---

# Hermes Update — Processo Seguro

## Quando usar

Rodolfo pediu atualização do Hermes, ou monitor de updates detectou nova versão disponível.

## Checagem prévia de versão

```bash
hermes --version
# Output inclui: versão instalada + "Update available: N commits behind — run 'hermes update'"
```

Verificar tag instalada vs latest:
```bash
cd /root/.hermes/hermes-agent
git log --oneline --no-walk --tags | head -3   # últimas tags
git log --oneline HEAD..origin/main | head -5  # commits pendentes específicos
```

---

## Pré-requisitos antes do update

### 1. Verificar se há sessões/crons em andamento

```bash
# Crons Hermes (agendamentos internos)
hermes cron list 2>/dev/null   # deve retornar vazio idealmente

# Services ativos
systemctl is-active zeus-gateway.service atena-gateway.service
```

### 2. Checar patches locais customizados

O VPS MGS tem um patch local em `gateway/run.py` para `busy_input_mode: queue`. **Após qualquer update, verificar se o patch ainda está aplicado:**

```bash
grep "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py
```

- Se retornar match → patch sobreviveu ao update ✅
- Se retornar vazio → reaplicar:
  ```bash
  patch -p1 < /root/mgs-agent/patches/hermes/busy_input_mode_queue_gateway.patch
  systemctl restart zeus-gateway atena-gateway
  ```

### 3. Fazer backup dos profiles (recomendado antes de major updates)

Profiles contêm memories, skills e state.db — **não são versionados no GitHub**, apenas no VPS.

```bash
tar -czf /root/hermes-profiles-backup-$(date +%Y%m%d).tar.gz /root/.hermes/profiles/
ls -lh /root/hermes-profiles-backup-*.tar.gz   # confirmar geração
```

**O que está em risco se a migração de banco falhar:**
| Arquivo | Risco |
|---|---|
| `profiles/*/memories/` | Alto — contexto acumulado dos agentes |
| `profiles/*/skills/` | Médio — recriáveis, mas demorado |
| `profiles/*/state.db` | Baixo — histórico de sessões |
| `/root/mgs-agent/` | Zero — versionado no GitHub |

---

## Executar o update

```bash
hermes update 2>&1
```

O comando:
- Faz pull do repo hermes-agent
- Reinstala o pacote Python
- Reinicia os gateways (Zeus e Atena ficam offline ~1-2 min)
- Preserva crontab e dados em `/root/mgs-agent/`

**Nota:** o terminal vai aguardar aprovação (Command Approval Required) porque reinicia os gateways. Aprovação automática ao confirmar.

Timeout normal: o comando demora ~60s+ em atualizações grandes — timeout no terminal é esperado, não indica falha. O update continua em background.

---

## Validação pós-update

```bash
# Aguardar ~10s para gateways reiniciarem
sleep 10

# 1. Versão instalada
hermes --version
# Deve mostrar: nova versão + "Up to date" (ou N commits behind se houver commits recentes)

# 2. Services ativos
systemctl is-active zeus-gateway.service atena-gateway.service
# Esperado: active / active

# 3. Patch local ainda aplicado?
grep "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py
```

---

## Comparação de integridade pós-update

Comparar backup com estado atual para confirmar que nada foi perdido:

```bash
# Extrair backup em /tmp
cd /tmp && rm -rf hermes-backup-compare && mkdir hermes-backup-compare
tar -xzf /root/hermes-profiles-backup-YYYYMMDD.tar.gz -C /tmp/hermes-backup-compare

# Memories
diff <(ls /tmp/hermes-backup-compare/root/.hermes/profiles/zeus/memories/ | sort) \
     <(ls /root/.hermes/profiles/zeus/memories/ | sort)

diff <(ls /tmp/hermes-backup-compare/root/.hermes/profiles/atena/memories/ | sort) \
     <(ls /root/.hermes/profiles/atena/memories/ | sort)

# Skills
diff <(find /tmp/hermes-backup-compare/root/.hermes/profiles/zeus/skills/ -name "SKILL.md" | sed 's|.*/skills/||' | sort) \
     <(find /root/.hermes/profiles/zeus/skills/ -name "SKILL.md" | sed 's|.*/skills/||' | sort)

diff <(find /tmp/hermes-backup-compare/root/.hermes/profiles/atena/skills/ -name "SKILL.md" | sed 's|.*/skills/||' | sort) \
     <(find /root/.hermes/profiles/atena/skills/ -name "SKILL.md" | sed 's|.*/skills/||' | sort)
```

**Interpretar resultados:**
- Sem diff → idêntico ✅
- Linhas com `>` (só no atual) → skills/memories adicionadas **após** o backup — normal, não é perda
- Linhas com `<` (só no backup) → algo foi removido pelo update — investigar

---

## Release notes rápidas

Para ver o que mudou entre versões:

```bash
# Arquivo de release notes local
cat /root/.hermes/hermes-agent/RELEASE_v0.13.0.md   # ajustar versão

# Commits entre duas tags
git -C /root/.hermes/hermes-agent log --oneline v0.12.0...v0.13.0 | head -50

# Commits pendentes ainda não instalados
git -C /root/.hermes/hermes-agent log --oneline HEAD..origin/main
```

## Review pré-update antes de pedir aprovação

Quando Rodolfo perguntar se vale atualizar, fazer primeiro uma análise read-only e só depois recomendar. Ver detalhe em `references/pre-update-review.md`.

Checklist mínimo:

```bash
hermes --version 2>&1 | head -20
cd /root/.hermes/hermes-agent
git fetch --quiet origin main
git status --short
git rev-parse --short HEAD
git rev-parse --short origin/main
git diff --shortstat HEAD..origin/main
git log --oneline --no-merges HEAD..origin/main | head -120
```

Se houver patches locais (`git status --short` não vazio), exportar `git diff` e testar `git apply --check` contra um worktree temporário em `origin/main` antes de dizer que o update é seguro. Reportar explicitamente:
- commits atrás e delta de arquivos/linhas
- features/fixes/docs/manutenção por contagem aproximada
- melhorias relevantes para a operação MGS
- risco de conflito com patch local
- recomendação executiva: atualizar agora, deferir, ou atualizar em janela controlada

---

## Pitfalls

1. **Timeout do terminal ≠ falha do update** — `hermes update` reinicia gateways e pode levar >60s. Terminal pode dar timeout enquanto o processo ainda roda. Verificar resultado com `hermes --version` após ~15s.

2. **2 commits pendentes logo após update** — normal quando commits são feitos entre o pull do `hermes update` e o momento da verificação. Se forem só fixes menores, pode ignorar ou rodar `hermes update` novamente.

3. **Patch MGS busy_input_mode — NÃO reaplicar após v0.13.0+** — o patch `PATCH (MGS Digital Corp)` de busy_input_mode/queue foi integrado nativamente no upstream (v0.13.0, 2026-05-07). O upstream agora tem queue mode + steer mode + ack com status detalhado (tempo decorrido, iteração X/Y, tool atual). Nunca mais reaplicar o patch — ele não existe mais no código e a funcionalidade nativa é superior. Verificar com `grep "PATCH (MGS Digital Corp)" gateway/run.py` — se retornar vazio, é o comportamento correto.

4. **Backup antes de major updates (diferença grande de versão)** — para atualizações de 1-2 commits, backup é opcional. Para atualizações com 100+ commits, fazer backup é prudente devido a possíveis migrations de `state.db`. Comando: `tar -czf /root/hermes-profiles-backup-$(date +%Y%m%d).tar.gz /root/.hermes/profiles/` — erro "file changed as we read it" é normal (Atena escrevendo), backup gerado mesmo assim.

5. **Skills novas no backup compare são normais** — skills bundled do Hermes podem ser adicionadas pelo próprio update. Não é perda, é ganho.

6. **Confirmar ambos os gateways ativos** — após restart, verificar `zeus-gateway` E `atena-gateway`. Em casos raros um sobe e o outro não. Se `deactivating` persistir após 5s, forçar: `systemctl restart zeus-gateway.service`.

7. **Versão permanece igual após update com apenas commits (sem nova tag)** — `hermes --version` pode mostrar a mesma tag (ex: v0.13.0) mesmo após atualizar dezenas de commits. Isso é normal — a tag só muda em releases oficiais. "Up to date" no output confirma que o update foi aplicado.
