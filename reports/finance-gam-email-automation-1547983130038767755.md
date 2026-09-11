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
- Estado produtivo: nenhuma receita de 10/09 aplicada; cutoff permanece 09/09.
- Bloqueios empresariais: TopFeed Finanzas ES, GameZoneAd MX e uma linha Yolokfx sem medium. Hipóteses usadas somente na simulação: `es-cc-es`, `mx-game-es/g002-s` e `g002-s`; não promovidas sem Rodolfo.
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
