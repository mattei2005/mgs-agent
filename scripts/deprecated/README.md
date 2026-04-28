# Deprecated Scripts

Scripts mantidos só para histórico. NÃO USAR em produção.

## update-yoast-scores.sh

- **Deprecated em:** 2026-04-27
- **Razão:** Usa `wp yoast index --object-id=` que NÃO existe no Yoast v27.x.
- **Substituto ativo:** `/root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh`
- **Substituto criado em:** 2026-04-24 (commit `7f19c4e` — Atena testou com post 62008: SEO 84/Read 90, ambos verdes).
- **Validação:** 5/5 testes confirmaram zero referências ativas (cron, scripts, skills, systemd, access time).

## monitor-rec-readability.sh

- **Deprecated em:** 2026-04-26
- **Substituto:** `/root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh`
- **Razão:** Substituído por monitor unificado de saúde Yoast (cobre SEO + Readability juntos).
- **Cron:** Já estava comentado como `# DEPRECATED 2026-04-26` antes da mudança.

## monitor-yoast-readability-eggbev.sh

- **Deprecated em:** 2026-04-26
- **Substituto:** `/root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh`
- **Razão:** Substituído por monitor unificado (cobre SEO + Readability juntos).
- **Cron:** Já estava comentado como `# DEPRECATED 2026-04-26` antes da mudança.
