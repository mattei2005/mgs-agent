### Challenges por IP de datacenter em fluxos Ares/Hera

Quando Rodolfo suspeitar que Hetzner/VPS/datacenter IP está causando bloqueio em YouTube/Hera ou Meta/Ares, não responder de memória nem propor migração de VPS como primeira ação. Importar a thread afetada em modo read-only, separar `browser consumer anti-bot` de `Marketing API endpoint trust`, e usar o teste de isolamento: mesma conta/token/payload/script, mudando apenas a origem de rede via proxy residencial/AdsPower. Para o playbook completo, ver `references/datacenter-ip-browser-api-challenge-diagnostics-2026-06-18.md`.

Padrão seguro para habilitar cross-agent por mention:
- Adicionar o canal do outro agente em `allowed_channels` do agente chamado.
- Manter `free_response_channels` restrito ao canal próprio do agente para evitar resposta livre fora da área dele.
- Manter `require_mention=true` e `thread_require_mention=true`, de modo que ele só acorde no canal externo com mention direta.
- Atualizar os três lugares quando existirem: config ativa (`/root/.hermes/profiles/<agent>/config.yaml`), config versionada (`/root/mgs-agent/profiles/<agent>-config.yaml`) e `.env` ativo se ele define `DISCORD_ALLOWED_CHANNELS`/`DISCORD_REQUIRE_MENTION` (env vence config em runtime).
- Ao patchar `.env`, preservar linhas operacionais não relacionadas (`DISCORD_HOME_CHANNEL`, `DISCORD_ALLOW_BOTS`, `BROWSER_DISABLE_SCREENSHOTS`, etc.) e evitar deixar chaves duplicadas; validar exibindo só chaves não secretas/valores sanitizados.
- Registrar audit log, deixar auto-commit/versionamento capturar o config versionado e reiniciar somente o gateway do agente afetado via restart seguro/detached.

Exemplo validado: para Ares responder a mentions em threads Hera, `allowed_channels` do Ares deve incluir `1508853425952133180,1513005743954198538`, mas `free_response_channels` deve continuar apenas `1508853425952133180`.

Regra prática:
1. Identificar o escopo ativo da thread antes de mencionar arquivos fora dele.
2. Se um arquivo modificado for de outro agente/área, só reportar se ele bloquear a ação atual.
3. Caso o usuário corrija o escopo, incorporar imediatamente e manter os reports seguintes restritos ao escopo correto.

