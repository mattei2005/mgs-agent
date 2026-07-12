# Meta Ads Library — continuidade por rota residencial

## Quando usar

Use em toda coleta da Meta Ads Library que reutilize o perfil autenticado da Ares.

## Rotas autorizadas

1. `dedicated-us-residential` — padrão 24/7. Credenciais são resolvidas em runtime no 1Password pelo item referenciado em `/root/mgs-agent/data/ares/creative-ops-meta-library-proxy.json`.
2. `windows-home-socks` — fallback temporário pelo Windows do Rodolfo em `socks5://127.0.0.1:1080`.
3. `direct-vps` — proibida para esse perfil.

Nunca gravar host, porta, usuário ou senha do proxy em logs, relatórios, argumentos ou Discord.

## Evidência operacional observada

O canário do proxy dedicado, criado a partir do snapshot autenticado e sem tocar no perfil canônico, confirmou:

- país US e IP estável no teste curto;
- `proxyMode=dedicated-us-residential`;
- `authenticatedLikely=true`, com `c_user` e `xs` presentes;
- `~63 results` e 42 Library IDs;
- 3 imagens e 30 vídeos detectados;
- challenge persistente ausente;
- download piloto HTTP 200 com MIME e magic-bytes válidos.

O `gotoStatus=403` isolado não significa falha quando o Chromium conclui o challenge e o report confirma DOM real, IDs, mídia e ausência de challenge persistente.

## Procedimento padrão

1. Confirmar que `/root/mgs-agent/data/ares/creative-ops-meta-library-proxy.json` está válido e `direct_vps_allowed=false`.
2. Os wrappers carregam `/root/mgs-agent/.env` com `set -a/set +a`; `proxy-config.js` busca o item 1Password e injeta a configuração diretamente no Playwright.
3. Executar normalmente, sem variável de proxy explícita:

```
/root/mgs-agent/scripts/ares-meta-library-collector.sh \
  --url '<META_LIBRARY_URL>' --download 100 --scrolls 100
```

4. Validar `proxyMode=dedicated-us-residential`, `authenticatedLikely=true`, IDs/mídia reais, downloads HTTP 200 e `persistentChallenge=false`.
5. Após login/2FA ou mudança de rota, testar primeiro em cópia canário do snapshot; nunca usar o perfil canônico como experimento.
6. Após shutdown autenticado e antes de nova operação crítica no perfil, executar `/root/mgs-agent/scripts/ares-meta-library-profile-snapshot.sh`.

## Fallback

Se o dedicado falhar, parar e reportar. Não testar pela VPS direta. Só então usar:

```
ARES_META_LIBRARY_PROXY_MODE=windows-home-socks \
  /root/mgs-agent/scripts/ares-meta-library-collector.sh \
  --url '<META_LIBRARY_URL>' --download 100 --scrolls 100
```

O túnel do Rodolfo precisa estar ativo apenas nesse fallback.

## Pitfalls

- `profileReused=true` não prova autenticação; valide `authenticatedLikely` e apenas os nomes `c_user`/`xs`.
- Não pedir ação humana quando o readback autenticado já passou.
- Não confundir contagem de resultados com assets únicos; deduplicar por URL/hash e registrar Library IDs separadamente.
- `captcha=true` pode ser falso positivo por texto escondido; priorizar DOM visível, IDs, mídia, screenshot e `persistentChallenge`.
- Nunca expor credenciais, cookies ou hashes do banco de cookies.
