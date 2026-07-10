## SEÇÃO E — Bug History: Regras Universais para Monitors com State File

Lessons learned 2026-04-27 (`check-pending-reports.sh` loop de ~120 msgs):

1. **Detectar mudança SEM atualizar estado = loop garantido.** Persistir ANTES da ação externa (curl)
2. **Separador `:` em arrays shell que carregam `agent:skill_name` causa colisão silenciosa** — usar `|`
3. **`declare -A RESOLVED_DEDUP`** para dedup dentro de uma execução
4. **Sempre fazer dry-run manual** após qualquer modificação em monitor com state file

---
