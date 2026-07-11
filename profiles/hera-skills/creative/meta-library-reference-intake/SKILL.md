---
name: meta-library-reference-intake
description: Use quando Rodolfo enviar URLs da Meta/Facebook Ads Library para a Hera validar acesso, baixar imagens/vídeos de referência, preservar sessão no perfil persistente, sanitizar e inventariar os arquivos.
version: 2.0.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [mgs, hera, creative-ops, meta-library, playwright, persistent-profile]
    related_skills: [creative-brief-handoff, local-browser-automation]
---

# Meta/Facebook Ads Library — Hera

## Contrato permanente

O runtime canônico é versionado e o perfil do navegador é persistente:

- Runtime: `/root/mgs-agent/tools/meta-library-collector/`
- Wrapper: `/root/mgs-agent/scripts/hera-meta-library-collector.sh`
- Perfil/cookies: `/root/.hermes/profiles/hera/browser-profiles/meta-library-chromium/`
- Saídas: `/root/.hermes/profiles/hera/artifacts/meta-library/<timestamp>/`

Nunca recriar esse fluxo em `/tmp`. Nunca apagar, substituir, anexar ou versionar o diretório do perfil. Ele pode conter uma sessão autenticada do Rodolfo. Cookies podem expirar por decisão da Meta, mas não devem ser removidos pela operação MGS.

## Fluxo obrigatório

1. Rodar o wrapper com a URL recebida, preservando a rota de rede do último sucesso autenticado. Se o último `proxyMode` for `windows-home-socks`, verificar primeiro `127.0.0.1:1080` e usar `HERA_META_LIBRARY_PROXY=socks5://127.0.0.1:1080`; nunca testar `direct-vps` antes:

```bash
HERA_META_LIBRARY_PROXY=socks5://127.0.0.1:1080 /root/mgs-agent/scripts/hera-meta-library-collector.sh --url '<URL>' --download 1
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
/root/mgs-agent/scripts/hera-meta-library-login-browser.sh '<URL DA LIBRARY>'
```

O helper usa o mesmo perfil persistente, Xvfb + x11vnc + noVNC, com VNC/noVNC vinculados somente a `127.0.0.1`. Rodolfo acessa por túnel SSH; nunca publicar a porta nem pedir senha/cookies no Discord. Após ele confirmar o login, encerrar a sessão visual de forma limpa para o Chromium salvar o perfil e só então rodar novamente o coletor headless.

Se uma sessão anterior morrer e deixar `x11vnc`/`websockify` órfãos, o helper só pode limpar listeners conhecidos após adquirir o lock do perfil. Nunca usar `pkill` amplo; processo inesperado nas portas deve falhar com exit `76`.

Se o Facebook entrar em CAPTCHA repetitivo pelo IP do VPS, parar a tentativa para não aumentar o risco da conta. Não trocar apenas de navegador nem usar proxy público/terceiro. A rota preferida é um SOCKS temporário pelo próprio Windows do Rodolfo: o SSH abre `-R 127.0.0.1:1080`, e o helper é iniciado com `HERA_META_LIBRARY_PROXY=socks5://127.0.0.1:1080`. O proxy deve ficar local-only, existir somente enquanto o túnel SSH estiver aberto e nunca aceitar outro endereço no helper.

### Continuidade obrigatória da rota residencial

Antes de reutilizar uma sessão autenticada, leia o `proxyMode` do último `report.json` bem-sucedido. Se ele for `windows-home-socks`, confirme que `127.0.0.1:1080` continua aberto e execute o coletor com `HERA_META_LIBRARY_PROXY=socks5://127.0.0.1:1080`. **Não rode primeiro em `direct-vps`**: a troca de IP/rota pode fazer a Meta remover `c_user`/`xs` do perfil persistente e invalidar a sessão recém-salva. Se o SOCKS estiver fechado, pare antes de abrir o Chromium e peça somente a reabertura do túnel residencial; depois valide os nomes `c_user`/`xs` sem expor valores e retome a coleta pela mesma rota.

## Verificação de encerramento

Uma coleta só está concluída quando houver readback real de:

- `report.json`;
- screenshot;
- IDs/mídia detectados;
- arquivo baixado com bytes > 0 e HTTP 200, quando solicitado;
- sanitização `clean=true`, quando o arquivo virar entrega.
