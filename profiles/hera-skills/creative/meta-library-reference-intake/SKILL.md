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

1. Rodar o wrapper com a URL recebida:

```bash
/root/mgs-agent/scripts/hera-meta-library-collector.sh --url '<URL>' --download 1
```

2. Ler o resumo JSON do stdout e depois o `report.json` indicado.
3. Validar o caminho real do browser, não apenas o status inicial:
   - `page.markers.adLibrary=true`;
   - pelo menos um `Library ID` ou mídia útil;
   - download HTTP 200 quando o pedido envolver baixar mídia;
   - screenshot real no diretório da execução.
4. O `gotoStatus` pode ser 403 e ainda assim a Meta concluir o challenge no Chromium. Não declarar bloqueio se o DOM/cards/mídia carregaram.
5. Se `session.authenticatedLikely=false`, isso não é erro quando a Library pública abre. Se a Meta exigir login ou esconder mídia, parar e pedir reautenticação manual; não pedir senha/cookie no Discord.
6. Para entrega, sanitizar os downloads com `/root/mgs-agent/scripts/clean-creative-metadata.sh`, validar `clean=true`, deduplicar e criar `README.txt` + `inventory.json`.
7. Material de Library é referência/inspiração. Não tratar como asset MGS final nem copiar diretamente para campanha.

## Segurança

- Nunca imprimir valores de cookies, headers de autenticação ou tokens.
- Nunca commitar o perfil persistente.
- O coletor só reporta contagem de cookies e presença dos nomes `c_user`/`xs`, sem valores.
- Não usar `/tmp` para runtime, perfil, sessão ou artefato que precise sobreviver.

## Verificação de encerramento

Uma coleta só está concluída quando houver readback real de:

- `report.json`;
- screenshot;
- IDs/mídia detectados;
- arquivo baixado com bytes > 0 e HTTP 200, quando solicitado;
- sanitização `clean=true`, quando o arquivo virar entrega.
