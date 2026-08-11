---
name: meta-library-reference-intake
description: Use quando Rodolfo enviar URLs da Meta/Facebook Ads Library para o Ares validar acesso, baixar imagens/vídeos de referência, preservar sessão no perfil persistente, sanitizar e inventariar os arquivos.
version: 2.0.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [mgs, ares, creative-ops, meta-library, playwright, persistent-profile]
    related_skills: [creative-operations-mgs, local-browser-automation]
---

# Meta/Facebook Ads Library — Ares

## Contrato permanente

O runtime canônico é versionado e o perfil do navegador é persistente:

- Runtime: `/root/mgs-agent/tools/meta-library-collector/`
- Wrapper: `/root/mgs-agent/scripts/ares-meta-library-collector.sh`
- Perfil/cookies: `/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium/`
- Saídas: `/root/.hermes/profiles/ares/artifacts/meta-library/<timestamp>/`

Nunca recriar esse fluxo em `/tmp`. Nunca apagar, substituir, anexar ou versionar o diretório do perfil. Ele pode conter uma sessão autenticada do Rodolfo. Cookies podem expirar por decisão da Meta, mas não devem ser removidos pela operação MGS. Limpezas genéricas de VPS, caches ou criativos também devem excluir explicitamente o perfil, `/root/.hermes/profiles/ares/browser-profiles/.meta-library-collector.lock`, o runtime `/root/mgs-agent/tools/meta-library-collector` e o Playwright Chromium 1228 exigido pelo coletor.

Se Rodolfo marcar “confiar neste dispositivo” ou a sessão depender de 2FA, após encerrar o helper visual de forma limpa e liberar o lock, exigir snapshot seguro do perfil canônico **antes** de iniciar o coletor. Não abrir duas instâncias, não remover `SingletonLock` manualmente e não prosseguir até haver confirmação do snapshot. O coletor deve continuar pela rota residencial dedicada resolvida pelo wrapper; `direct-vps` é proibido.

## Fluxo obrigatório

1. Rodar o wrapper normalmente, **sem** definir `ARES_META_LIBRARY_PROXY`. O runtime resolve a rota `dedicated-us-residential` e suas credenciais diretamente no 1Password e falha fechado se a configuração estiver ausente/inválida. `windows-home-socks` é apenas fallback após reportar falha do dedicado; nunca usar `direct-vps`:

```bash
/root/mgs-agent/scripts/ares-meta-library-collector.sh --url '<URL>' --download 1
```

2. Ler o resumo JSON do stdout e depois o `report.json` indicado.
3. Validar o caminho real do browser, não apenas o status inicial:
   - `page.markers.adLibrary=true`;
   - pelo menos 3 `Library ID` distintos e mídia útil associada aos cards;
   - download HTTP 200 quando o pedido envolver baixar mídia;
   - MIME permitido, magic-byte válido, tamanho dentro dos limites e hash SHA-256;
   - screenshot real no diretório da execução.
4. O `gotoStatus` pode ser 403 e ainda assim a Meta concluir o challenge no Chromium. Não declarar bloqueio se o DOM/cards/mídia carregaram.
5. Coletar incrementalmente durante o scroll; a Meta virtualiza cards antigos. Em libraries maiores, continuar até quatro ciclos sem novos IDs/mídias ou até o limite de segurança, registrando `scrollsPerformed` e `stoppedAfterStableRounds`.
6. Se `session.authenticatedLikely=false`, isso não é erro quando a Library pública abre. Se a Meta exigir login ou esconder mídia, parar e pedir reautenticação manual; não pedir senha/cookie no Discord.
7. Para entrega, sanitizar os downloads com `/root/mgs-agent/scripts/clean-creative-metadata.sh`, validar `clean=true`, deduplicar e criar `README.txt` + `inventory.json`.
8. Material de Library é referência/inspiração. Não tratar como asset MGS final nem copiar diretamente para campanha.

## Segurança

- Nunca imprimir valores de cookies, headers de autenticação ou tokens.
- Nunca commitar o perfil persistente.
- O coletor só reporta contagem de cookies e presença dos nomes `c_user`/`xs`, sem valores.
- Não usar `/tmp` para runtime, perfil, sessão ou artefato que precise sobreviver.
- O wrapper usa lock exclusivo; nunca abrir dois Chromium simultaneamente no mesmo perfil nem remover `SingletonLock` manualmente.
- O browser roda como root apenas por limitação atual do host e mantém `--no-sandbox`; não desativar site isolation e não usar esse runtime para navegação fora de `facebook.com/ads/library/`.

## Reautenticação manual persistente

Quando a Library pública abrir, mas uma busca específica não carregar cards e `authenticatedLikely=false`, abrir a sessão visual local-only:

```bash
/root/mgs-agent/scripts/ares-meta-library-login-browser.sh '<URL DA LIBRARY>'
```

O helper usa o mesmo perfil persistente, Xvfb + x11vnc + noVNC, com VNC/noVNC vinculados somente a `127.0.0.1`. Rodolfo acessa por túnel SSH; nunca publicar a porta nem pedir senha/cookies no Discord. Após ele confirmar o login, encerrar a sessão visual de forma limpa para o Chromium salvar o perfil e só então rodar novamente o coletor headless.

Se uma sessão anterior morrer e deixar `x11vnc`/`websockify` órfãos, o helper só pode limpar listeners conhecidos após adquirir o lock do perfil. Nunca usar `pkill` amplo; processo inesperado nas portas deve falhar com exit `76`.

Se o status do helper já mostrar `state=ready`, `pageTitle=Ad Library`, `authenticatedLikely=true` e a rota correta, não pedir a Rodolfo para abrir noVNC apenas para confirmar o que o readback já provou. Ação humana só é necessária para login, MFA, CAPTCHA/challenge visível ou ausência real de cards/autenticação.

Quando Rodolfo marcar “confiar neste dispositivo” ou concluir 2FA, preservar os cookies vira gate crítico. Após shutdown limpo e antes de qualquer nova operação no perfil, executar `/root/mgs-agent/scripts/ares-meta-library-profile-snapshot.sh`. O script exige lock exclusivo, recusa processo Chromium vivo, não remove `Singleton*`, aceita apenas evidência autenticada recente pela rota residencial, mantém permissões 700/600 e retenção dos cinco snapshots mais recentes. Nunca imprimir valores ou hashes de cookies no Discord.

Se o Facebook entrar em CAPTCHA repetitivo mesmo pela rota dedicada, parar a tentativa para não aumentar o risco da conta e reportar a falha do dedicado. Não trocar apenas de navegador nem usar proxy público/terceiro. O fallback aprovado é o SOCKS temporário pelo próprio Windows do Rodolfo: o SSH abre `-R 127.0.0.1:1080`, e o helper/coletor são iniciados com `ARES_META_LIBRARY_PROXY=socks5://127.0.0.1:1080`. Esse fallback deve ficar local-only, existir somente enquanto o túnel SSH estiver aberto e nunca ser solicitado em operação normal com o dedicado saudável.

Depois de autenticar pela rota residencial, não testar a rota `direct-vps` com o mesmo perfil persistente: isso pode reativar o challenge e alterar o estado da sessão. Se uma tentativa direta ocorrer e `c_user`/`xs` ficarem ausentes, não atribuir causalidade sem evidência; reabrir o helper visual pela rota residencial, autenticar se necessário, encerrar de forma limpa e só então coletar pela mesma rota SOCKS. Processos de coleta em background nunca devem despejar JSON bruto no Discord; aguardar/poll manualmente e publicar apenas resumo validado.

### Continuidade obrigatória da rota residencial

A rota padrão agora é `dedicated-us-residential`, resolvida em runtime pelo item 1Password definido em `/root/mgs-agent/data/ares/creative-ops/meta-library-proxy.json`. Credenciais nunca entram em arquivo, log, argumento de processo ou Discord. Os wrappers carregam `.env` com `set -a/set +a`; `proxy-config.js` busca host/porta/usuário/senha diretamente no 1Password, remove segredos do ambiente herdado pelo Chromium e proíbe `direct-vps` fail-closed.

Antes de tocar no perfil canônico, validar mudança de proxy em cópia canário do último snapshot. Só promover quando o report confirmar país esperado, `proxyMode=dedicated-us-residential`, `authenticatedLikely=true`, ausência de challenge persistente, IDs reais e download HTTP 200 com magic-bytes. O `gotoStatus` pode ser 403 quando o Chromium conclui o challenge e o DOM real carrega; avaliar o report completo, não o status isolado.

A rota `windows-home-socks` fica apenas como fallback temporário. Se o proxy dedicado falhar, não testar `direct-vps`; usar o túnel residencial do Rodolfo somente após reportar a falha. Com o dedicado saudável, Rodolfo pode fechar o PowerShell e o Ares consulta libraries 24/7 sem ação humana. Login/MFA/CAPTCHA continuam sendo as únicas exceções humanas quando a sessão realmente expirar.

Para evidência, comando de retomada e distinção entre perfil reutilizado e sessão autenticada, consulte `references/residential-route-session-continuity.md`.

Para coleta integral, deduplicação SHA-256, sanitização, pacote de referências, upload e readback no Drive, consulte `references/full-collection-drive-packaging.md`.

Para comprovar mudanças task-local sem tocar no collector canônico, use o A/B reproduzível de `references/task-local-collector-controlled-validation.md`: baseline byte-identical, candidato com diff isolado, dois `report.json`, hashes dos downloads, SHA antes/depois do canônico e `git diff --exit-code`.

## Verificação de encerramento

Uma coleta só está concluída quando houver readback real de:

- `report.json`;
- screenshot;
- IDs/mídia detectados;
- arquivo baixado com bytes > 0 e HTTP 200, quando solicitado;
- sanitização `clean=true`, quando o arquivo virar entrega.
