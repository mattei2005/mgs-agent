## SEÇÃO G — Importar histórico de thread antiga por link/ID

Quando Rodolfo/Raquel pedir para Zeus, Atena, Ares ou outro agente MGS ler uma thread antiga, use o importador read-only canônico por link/ID. Ver `references/discord-thread-history-import.md`.

Comandos padrão:

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile ares '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile hera '<LINK_OU_ID>'
```

Pitfall: usar o `--profile` correto evita tentar acessar private threads com o token do bot errado. Os snapshots em `data/discord-thread-imports/` são local-only e não devem ser versionados.

---
