# Openzed — Saved templates baseline

> Live read-only observation from 2026-07-16. Re-read the live page before operational conclusions because saved templates can be added, renamed or removed.

## Access route

- Account: `Disparos Openzed US-CC-EN`
- Bot manager page selected before opening: `Hortensia Martínez` (`#1084`)
- UI route: `Bot manager` → `Saved templates` → `Change settings`
- The link opens a new tab at `https://digitaltrchat.com/messenger_bot/saved_templates`
- Page title: `Digital TR Chat | Facebook saved templates`

## Safety boundary

This page contains several write/destructive controls. Read-only inspection must not click any of them:

- `Upload template` — creates/imports a template.
- `Install template` (`.install_template`) — installs the selected template and can mutate the account/page setup.
- Category trash icon with `.delete_template_category` and `title="Delete Category"` — destructive.
- Gray category trash icons are disabled and display `You do not have permission to delete this.`; do not rely on color alone because at least one category showed an actionable red delete icon.
- Three-dot menus on template cards may expose additional actions; do not open them until Rodolfo teaches the exact intended action.

Completion criterion for inspection: the page and cards were read, but no upload, install, ellipsis action or category trash control was clicked.

## Live visible baseline

Eleven template cards were visible:

1. `OPENZED - US EN/EN - DRIP - 28 MSGS - IMG - 23/03`
2. `OPENZED - US EN/EN - DRIP - 15 MSGS - 13/03`
3. `OPENZED - US EN/EN - SMART ROUTER - DRIP - BD - 18/02`
4. `Openzed US-CC-EN/EN - FUNIL 12H - COM BOTAO`
5. `Openzed US-CC-EN/EN - SEM BOTAO - FUNIL 12H`
6. `Openzed US-CC-ES/ES - COM BOTAO/ZERO WIDTH - FUNIL 12H`
7. `(NÃO USAR) Openzed US-CC-ES/ES - COM BOTAO/ZERO WIDTH - FUN...` (UI truncada)
8. `(NÃO USAR) Openzed US-CC-EN/EN - COM BOTAO - FUNIL PRIMEIRO DIA`
9. `Openzed US-CC-EN/EN - COM BOTAO - FUNIL MAIOR`
10. `Openzed US-CC-ES/ES - COM BOTAO/ZERO WIDTH - FUNIL MAIOR`
11. `Openzed - US LOAN CAR - EN - Botao`

Every visible card showed an `Install template` button and a three-dot menu. The first rows were dated between three and ten months ago.

## Category panel baseline

- `All categories` was selected.
- 79 saved categories were listed.
- Category names were largely duplicated variants of `TEMPLATE`/`template`, plus `test`, `emprego` and `1`.
- 78 trash controls were disabled; one category exposed an actionable delete control.

Treat this category clutter as historical state, not as the operational template scope. Do not delete or clean categories without Rodolfo explicitly naming the target and confirming the destructive operation required by MGS policy.
