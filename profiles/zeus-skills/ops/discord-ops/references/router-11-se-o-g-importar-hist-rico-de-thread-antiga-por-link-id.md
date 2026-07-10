## SEÇÃO G — Importar histórico de thread antiga por link/ID

Quando Rodolfo/Raquel pedir para Zeus, Atena, Ares, Hera ou outro agente MGS ler uma thread antiga, use o importador read-only canônico por link/ID. Ver `references/discord-thread-history-import.md` e `references/discord-thread-import-profile-rollout.md`.

Comandos padrão:

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile ares '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile hera '<LINK_OU_ID>'
```

Regra operacional: nunca responder “só leio o contexto entregue pelo gateway” quando Rodolfo fornece ID/link antes de tentar o importador com o profile correto. O contexto ativo pode não conter histórico completo; isso é diferente de incapacidade de importar histórico read-only.

Pitfalls:
- Usar o `--profile` correto evita tentar acessar private threads com o token do bot errado.
- Se retornar `403 Missing Access`, reportar falta de acesso real do bot do profile à thread/canal e pedir liberação; não inventar conteúdo.
- Para agentes novos, garantir que o `import-discord-thread.py` aceite o profile sem lista hardcoded restrita. Validado após remover `choices=["zeus","atena"]` e validar nomes por regex segura.
- Os snapshots em `data/discord-thread-imports/` são local-only e não devem ser versionados.

---
