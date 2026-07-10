## SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)
- Usar o `--profile` correto evita tentar acessar private threads com o token do bot errado.
- Se `GET /channels/<thread_id>` retornar `403 Missing Access`, é uma limitação de permissão do bot/profile naquela thread/canal; reporte isso claramente e não invente conteúdo.
- Não confundir `403 Missing Access` para enviar mensagem no canal Zeus/home com incapacidade de ler uma thread acessível: são permissões separadas.
- Os snapshots em `data/discord-thread-imports/` são local-only e não devem ser versionados.

---
