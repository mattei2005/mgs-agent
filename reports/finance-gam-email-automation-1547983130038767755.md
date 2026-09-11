# Automação diária GAM por e-mail — implantação

- Autorização: Rodolfo `1547983130038767755`.
- Thread: `1545426987756298340`.
- Resultado estrutural: coletor IMAP read-only, parser fail-closed, runner transacional remoto e cron instalados.
- Janela: 08:03, 08:13, 08:22 e 08:28 Eastern.
- Colisões operacionais em oito dias: zero.
- Credencial: 1Password por ID; nenhum segredo persistido em script, contrato, cron ou log.
- Relatórios: par obrigatório `Digital Trust.xlsx` CAD + `Report Digital Trust (adx 2).xlsx` USD da mesma data.
- Dedupe: Message-ID + SHA-256 e import ID determinístico.
- Segurança: mensagens permanecem não lidas; país/domínio/gestor novo bloqueia; datas sem par ou lacuna bloqueiam; CAD/USD preservados; backup e recovery antes do write; revision guard; aplicação idempotente; readback obrigatório.
- Testes: 118/118 Node e 79/79 Python; sintaxe Python/Node aprovada; auto-intake IMAP real aprovado; schedule gate fora da janela sem mutação; simulação remota completa aprovada com zero writes.
- Primeiro par: 10/09/2026, 3.058 linhas, CAD `28042.38632477471319015898`, USD `6303.6497353978632530296`.
- Classificações confirmadas por Rodolfo `1548001704119762945`: TopFeed Finanzas source ES → US/`us-cc-es`; GameZoneAd source MX → BR/`br-game-br`; medium ausente em qualquer site → `g002-s` desde 10/09.
- Produção: aplicada e validada, 74 grupos, revisão 122→123, cutoff 10/09, audit 593 e recovery bloqueado.
- Backup: dump remoto + cópia local de 49.720.742 bytes com SHA-256 idêntico; archive listing aprovado.
- Idempotência: segunda aplicação retornou `already_applied=true`, revisão permaneceu 123.
- Interface: owner autenticado, desktop/mobile, 31 linhas, três sites revisados visíveis e zero erros JavaScript.
- Recuperação técnica: tentativas iniciais falharam antes de qualquer write porque o parent remoto do backup não era gravável pelo usuário `zeus` e um teste de ausência retornava exit 1. O helper passou a criar somente o parent exato via `sudo install`, tratar ausência por condicional e reutilizar uma única resolução 1Password em memória por run. Rehearsal, backup, apply e verify passaram depois da correção.
- Restart: nenhum.

Artefatos principais:

- `apps/finance-system/finance_gam_revenue_sync.py`
- `apps/finance-system/gam_revenue.py`
- `apps/finance-system/gam-revenue-core.mjs`
- `apps/finance-system/gam-revenue-cli.mjs`
- `apps/finance-system/deploy/gam-revenue-schedule-preflight.py`
- `apps/finance-system/deploy/gam-revenue-schedule-install.py`
- `data/finance-gam-revenue-rules.json`
- `data/finance-gam-revenue-contract.json`
- `data/finance-gam-revenue-state.json`
- `docs/finance-gam-email-automation.md`
