# OpenZed canary deploy — MGS Chat Funnels

Sessão de referência: deploy canário do plugin `MGS Chat Funnels` em `openzed.com`.

## Fluxo validado

1. Construir pacote local:
   ```bash
   cd /root/mgs-agent/plugins
   zip -qr /tmp/mgs-chat-funnels.zip mgs-chat-funnels
   ```
2. Validar local/remoto:
   - `node --check assets/chat-funnels.js`
   - `python3 -m json.tool configs/*.json`
   - `php -l` remoto em RunCloud para arquivo PHP quando o host local não tem PHP.
3. Login WP Admin via `https://openzed.com/rodloguda/` com item 1Password `openzed wordpress zeus` campos `username` + `password`.
4. Upload pelo `plugin-install.php?tab=upload`.
5. Se WordPress mostrar “already exists / Replace current with uploaded”, seguir o link de replace para atualizar o plugin.
6. Ativar/verificar por REST:
   ```text
   GET/POST https://openzed.com/wp-json/wp/v2/plugins/mgs-chat-funnels/mgs-chat-funnels
   ```
7. Validar rotas públicas:
   ```text
   https://openzed.com/chat/emp/br1
   https://openzed.com/chat/car/br1
   ```
8. Validar no browser: gate abre, CTA libera chat, links finais preservam UTM.

## Pitfall corrigido

No renderer PHP, não usar `esc_html($json)` dentro de `<script type="application/json">`. Isso transforma aspas em `&quot;`, faz `JSON.parse(script.textContent)` falhar e deixa a página vazia sem mensagem visível.

Padrão correto:

```php
$json = wp_json_encode($config, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP);
```

E depois imprimir o JSON cru dentro do script, com justificativa de segurança porque `JSON_HEX_TAG`/`JSON_HEX_AMP` protegem o contexto:

```php
<script type="application/json" class="mgs-chat-funnel-config"><?php echo $json; ?></script>
```

## Checklist específico para este tipo de plugin

- [ ] Página pública contém `mgs-chat-funnel-config`.
- [ ] O conteúdo do script JSON não contém `&quot;` no começo da config.
- [ ] `document.body.innerText` mostra o gate/chat, não vazio.
- [ ] `browser_console` não mostra `MGS Chat Funnel config error`.
- [ ] Links finais incluem UTMs originais.
- [ ] REST plugin endpoint retorna `status=active`.
