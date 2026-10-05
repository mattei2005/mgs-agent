# MGS Router — Última Verificação and DNS dialog

## Authority and current UI

Rodolfo message `1556501154287058974`, thread `1555381168894115912`, authorizes removal of the long saved-check explanation from domain rows, a rightmost Última Verificação column with only the date, and a popup for Ver instruções DNS instead of inline instructions at the bottom.

Extends/supersedes only these UI details in `docs/mgs-router-domain-layout-top-pagination.md`. All traffic, schemas, groups, identity, query, indexing and credential contracts remain intact.

- Domain status no longer includes the repeated “Última verificação…resultado salvo; Verificar consulta online novamente” line.
- Rightmost `Última Verificação` cell displays saved `checked_at` as `toLocaleDateString('pt-BR')`, without time or explanatory text, using the browser's existing timezone. Unverified/missing/invalid dates display `—`; never fabricate a date or replace the stored timestamp.
- `Ver instruções DNS` opens a native accessible `<dialog>` named `Como configurar o DNS`, with the selected host and existing record/instructions. Close through Fechar or Escape. Responsive maximum height and scrolling keep desktop/mobile within the viewport. The same dialog also opens for existing post-add-domain instructions.
- Opening/closing instructions is local UI only; no DNS or state API writes. `Verificar` retains its explicit fresh online DNS/HTTPS check and saves the genuine timestamp. Date/green status remains a saved observation, not continuous monitoring.

## Publication and validation

Source: `apps/mgs-router/web/{admin.html,app.js,style.css}`. Receipt: `data/mgs-router-dns-dialog-validation.json`; later independent checker: `data/mgs-router-public-validation.json`. Single-use UI-only executor: `scripts/mgs-router-dns-dialog-deploy.py`. Private rollback: `/root/.local/share/mgs-router-rollbacks/1556501154287058974`.

78 Go/browser cases, race, vet, JS syntax and build passed; 1,856 real public route checks passed. Both production accounts validated the modal's correct domain, Fechar, Escape, mobile width, and every displayed date against the saved API timestamp. Browser tests cover the empty date placeholder and real local saved-check refresh/reload. Adapted existing fixtures to close the modal before underlying controls and to inspect the new date cell instead of the removed hint.

The UI-only deployment wrote no route/domain/user/check data. Exact bytes of routes.json, domains.json, users.json and domain-checks.json preserved; 445 campaigns, 943 Landing Pages, 19 domains in MGS, and 29 groups per campaign/LP area remain unchanged. No DNS/SSL/credential/permission/gateway changes. Only the Router application was restarted for embedded assets.

Never replay previous single-use executors or roll back over intervening operator writes. Preserve private rollback files until a separately authorized deletion.
