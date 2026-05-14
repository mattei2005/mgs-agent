# CHECKPOINT FASE 3 + 4 — MGS Agent
Data: 14/05/2026
Status: ✅ AMBAS CONCLUÍDAS

## Fase 3 (concluída antes desta sessão, com fix 14/05)
- 12 marcos históricos catalogados PEND-074 a PEND-085 (cobertura 22/04 → 03/05)
- Bug v1 do pendencia-historico-add.sh corrigido (3 bugs: numeração resetada, proximo_id, schema)
- v2 do script com schema canônico + anti-duplicata + heredoc seguro

## Fase 4 (concluída 14/05 nesta sessão)
- 6 das 7 ALTA fechadas via Claude Code
- PEND-001 (Play Store publish) rebaixada alta→baixa (async/cosmético)
- 1 nova baixa criada (PEND-086 — monitor Tier 4 Anthropic)

## Bug crítico descoberto e corrigido (14/05 tarde)
Colisão de IDs: pendencia-add.sh usava metadata.proximo_id, pendencia-historico-add.sh usava root .proximo_id. Renumeração da Fase 3 atualizou só root, deixando metadata=74 desatualizado. Primeira nova add após Fase 3 (PEND-074 "Monitor Tier 4") colidiu com PEND-074 já em resolvidas[].

Solução:
1. Migration scripts/migration-2026-05-14-proximo-id-collision-fix.sh aplicada: renumerou PEND-074 nova→PEND-086 preservando todos os campos, sincronizou ambos proximo_id em 87
2. Patches em pendencia-add.sh + pendencia-historico-add.sh: read root com fallback metadata, write em AMBOS
3. Convenção scripts/migration-YYYY-MM-DD-<desc>.sh estabelecida pra mudanças one-off futuras
4. Discovery adicional: ultima_atualizacao também tem schema dual (root + metadata), mesma classe de bug — preventivamente sincronizado nos scripts

## Estado final do sistema
- ALTA: 0 (zero)
- MEDIA: 25
- BAIXA: 33
- Total abertas: 58
- Total resolvidas: 28
- proximo_id: 87 (root = metadata, SYNC ✓)
- Backups acumulados: 5 (pode limpar após 1 semana se estável)

## Próximos passos (Fase 5 — opcional)
- 25 MEDIA aguardando priorização interna
- Auditar outros campos "duais" no JSON com risco de drift (total_abertas, total_resolvidas)
- Limpar .bak-* antigos após validação de estabilidade
