# Finance — home no mês atual após login

- Autorização: Rodolfo `1550142625485561919`
- Thread: `1545426987756298340`
- Produção: `https://dash.mgsdigitalcorp.com`
- Status: **PASS**

## Mudança

Todo caminho de login concluído, inclusive continuação após cadastro de MFA/códigos de recuperação, substitui uma competência antiga armazenada no navegador e abre a home `Dashboard` na competência corrente em `America/New_York`. A seleção manual de outro mês continua funcionando depois da entrada.

Arquivos implantados:

- `apps/finance-system/public/login.js`
- `apps/finance-system/public/login.html`

Cobertura adicionada:

- `apps/finance-system/tests/login-current-period.test.mjs`
- `apps/finance-system/tests/login-current-period-public.mjs`

Regra persistida em:

- `/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/current-security-performance-and-dr.md`
- mirror versionado sincronizado em `profiles/zeus-skills/ops/mgs-finance-dashboard/references/current-security-performance-and-dr.md`

## Validação

- Node: `147/147` PASS.
- Python: `102/102` PASS.
- `npm audit`: zero vulnerabilidades.
- Browser produtivo com autenticação real e MFA: seleção antiga `2026-08` substituída por `2026-09`; URL, seletor e `sessionStorage` reconciliados; home `Dashboard`; zero erro JavaScript; logout validado.
- Assets públicos: `/login` HTTP 200 com versão nova; JavaScript público tem o mesmo SHA-256 do arquivo implantado.
- Serviços remotos: PostgreSQL, aplicação e socket ativos.
- Banco financeiro: fingerprint de cenários e ledger inalterado; zero write financeiro.
- Reinício: não necessário.
- Backup exato: `/home/mgsfinance/backups/login-current-month-1550142625485561919`.

## Reconciliação concorrente

O SHA produtivo anterior do `login.js` não coincidia com o `HEAD` Git. A origem foi reconciliada no audit log: hotfix MFA autorizado `finance_mfa_second_submit_bug_recovered`, fonte `1548936711084572714`, SHA produtivo `1263cf53d14c1051f0d4ed30116a44a2250ac3a6b89512824434063fcad6c78b`. A implantação partiu desse arquivo produtivo e preservou integralmente o hotfix.

## Evidência

`/root/mgs-agent/apps/finance-system/private/login-current-month-1550142625485561919/final-validation.json`
