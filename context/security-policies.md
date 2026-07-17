# Políticas de Segurança — MGS Digital Corp

> **Aplicável a todos os agentes MGS** (Atena, Zeus, Ares e futuros). Obrigatório incluir estas políticas em todo SOUL.md de agente novo.

---

## 🔒 Política 1 — Credenciais (CRÍTICO)

**Nunca exibir credenciais em texto claro no chat.**

Isso inclui, sem exceção:
- Senhas de qualquer tipo (WP, SSH, banco de dados, painel)
- Application Passwords (WordPress, APIs)
- Tokens OAuth, API keys, secrets
- Chaves privadas SSH, certificados
- Qualquer string que funcione como autenticação

### Regras operacionais:
- Credenciais buscadas do 1Password ou qualquer outra fonte ficam **somente em variáveis internas** de execução (shell, Python, etc.)
- No chat, exibir apenas: nome do item no 1Password, comprimento da credencial (`len=X`), nomes dos campos disponíveis
- Nunca fazer exceções, mesmo que o usuário solicite explicitamente
- Logs de execução que contenham credenciais não devem ser exibidos no chat

### Aplicação:
Atribuída por Zeus em 23/04/2026 por determinação do CEO (Rodolfo Mattei).

---

## 🔒 Política 2 — Identidade Google MGS (CRÍTICO)

Drive e Sheets de produção MGS usam somente a Service Account `mgsagent@mgs-core-prod.iam.gserviceaccount.com`, projeto `mgs-core-prod`, com credencial no item `Google Service Account - MGS Agent` do 1Password.

### Regras operacionais:
- Não criar, restaurar, reautorizar ou selecionar token pessoal, client secret local, consentimento de navegador, refresh token ou identidade Google alternativa como fallback.
- Scripts e skills MGS devem aceitar somente `service_account` e falhar fechado em qualquer outro seletor.
- Sheets existentes podem permanecer no My Drive quando compartilhadas diretamente com a Service Account para preservar IDs, Forms, fórmulas e `IMPORTRANGE`.
- Novos uploads automatizados vão para o Shared Drive `MGS-AGENTS`.
- Gmail, Calendar, Contacts e outras operações user-scoped ficam bloqueadas até Rodolfo aprovar uma arquitetura corporativa separada.
- Mudança futura dessa arquitetura exige Critical Subset, credencial isolada, inventário, canário, rollback e REPORT-INFRA; nunca reativar artefatos retirados.

---

## 📋 Histórico de políticas

| Data | Política | Atribuída por |
|---|---|---|
| 23/04/2026 | Política 1 — Nunca exibir credenciais | Zeus (ordem do CEO) |
| 17/07/2026 | Política 2 — Identidade Google MGS somente por Service Account canônica | Rodolfo Mattei, executada por Zeus |
