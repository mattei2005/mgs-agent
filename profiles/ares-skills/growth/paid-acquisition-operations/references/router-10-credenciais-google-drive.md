## Credenciais Google Drive

Preferir **Google Service Account** para leitura e inventário. Para write/upload em `My Drive` pessoal, validar quota antes: Service Account pode falhar com `403 storageQuotaExceeded` porque não tem armazenamento próprio. Se o destino estiver em My Drive pessoal, usar OAuth de usuário real ou mover a operação para Shared Drive.

Fluxo Service Account/read-only:

1. Criar Service Account.
2. Guardar JSON no 1Password.
3. Compartilhar `MGS-CRIATIVOS` com o e-mail da Service Account.
4. Começar como Viewer; Editor só quando Rodolfo explicitamente quiser testar write.
5. Validar sem expor segredos: item encontrado, JSON parseado, private key presente, folder acessível, permissões/capabilities, filhos listados.

Fluxo OAuth/write em My Drive:

1. OAuth Desktop app com scope mínimo necessário, normalmente `https://www.googleapis.com/auth/drive` para upload/cópia.
2. Refresh token e client secret ficam em arquivo root-only/permissão 600 ou vault; nunca imprimir no chat.
3. Script deve aceitar modo por `.env`, ex.: `ARES_DRIVE_AUTH_MODE=oauth`, e reportar apenas `auth_mode=oauth_user`, `storage=my_drive`, capabilities e status.
4. Fazer smoke test com 1 arquivo antes da fila completa.
5. Antes de rodar centenas de uploads usando quota pessoal de Rodolfo, pedir aprovação explícita de escopo.


Referência de pipeline e pitfall de quota: `references/drive-creative-clean-copy-quota.md`.

Reportar algo como:


```text
Item 1Password | Encontrado
folder access  | OK
can_edit       | true/false
children       | nomes de pastas, sem IDs sensíveis se não necessário
```
