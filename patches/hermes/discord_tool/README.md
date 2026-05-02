# discord_tool.py — modify_thread action patch

Custom patch aplicado em `/root/.hermes/hermes-agent/tools/discord_tool.py`
adicionando 4 ocorrências da action `modify_thread`.

## Quando reaplicar

A cada upgrade do Hermes Agent que substitua `discord_tool.py` upstream.

## Arquivos

- `modify-thread-action.patch` — diff aplicável via `git apply` ou `patch -p1`
- `README.md` — este arquivo

## Histórico

- 2026-04-29: patch criado (snapshot pre-hermes-upgrade-20260429_104523)
- 2026-05-02: salvo em patches/hermes/ no fix P0-2
