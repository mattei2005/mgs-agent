# F028 — Fechamento pós-atualização do Polylang em growpowerhub.com

**Estado:** RESOLVIDA E VALIDADA  
**Data:** 2026-09-23 UTC  
**Domínio:** `growpowerhub.com`  
**Aplicação:** `growpowerhub` / MatteiInc03JBF  
**Ação de atualização:** executada por Rodolfo no painel WordPress  
**Autorização para rechecagem:** Discord `1552330625262952529`

## Resultado executivo

Rodolfo atualizou todos os plugins do site. A rechecagem confirmou que o Polylang passou de 3.6.7 para 3.8.9 e que o patch manual antigo desapareceu.

O Polylang ao vivo agora coincide integralmente com o pacote oficial 3.8.9:

- 537 arquivos ao vivo;
- 537 arquivos oficiais;
- zero arquivo modificado;
- zero arquivo extra;
- zero arquivo faltante;
- checksum do `canonical.php` ao vivo igual ao oficial;
- `wp plugin verify-checksums polylang`: PASS.

Não foi necessário editar, restaurar ou corrigir manualmente qualquer arquivo.

## Mudança estrutural do Polylang

Na versão 3.6.7, o arquivo auditado ficava em:

`frontend/canonical.php`

Na versão 3.8.9, o arquivo oficial foi movido para:

`src/frontend/canonical.php`

SHA-256 ao vivo e oficial:

`ff0de190a8efd48d29df69623fe37527b6ca156b9f8add735ca757ad23a63c92`

Pacote oficial:

- URL: `https://downloads.wordpress.org/plugin/polylang.3.8.9.zip`;
- SHA-256: `de5fae3d399e34c2db496a02b7cff4e4ca79723c418c8542b82bb7c030204a60`.

## Integridade geral pós-atualização

- WordPress core checksum: PASS;
- 20 plugins normais verificados individualmente: PASS;
- dois mu-plugins locais (`hide-from-home` e `yoast-rest-meta`) não possuem pacote público/checksum WordPress.org, como esperado;
- nenhum plugin normal permanece com atualização disponível;
- `wp-file-manager` aparece como “version higher than expected”, mas a versão 8.0.5 passou no checksum oficial;
- Polylang permanece ativo;
- configurações de idiomas e menus foram preservadas;
- opção interna do Polylang atualizada de 3.6.7 para 3.8.9.

## Validação funcional

Foram testados no público e diretamente na origem:

- homepage alemã;
- `/en/`;
- `/es/`;
- `/fr/`;
- uma publicação de cada idioma;
- `?lang=de`;
- `?lang=en`;
- `?lang=es`;
- `?lang=fr`;
- URL de post sem barra final;
- `?lang=en` com UTMs, `fbclid` e `gclid` sintéticos.

Resultados:

- todas as rotas válidas responderam HTTP 200;
- público e origem produziram os mesmos hashes de corpo por URL;
- nenhum loop de redirecionamento;
- nenhum HTTP 5xx após o smoke pós-atualização;
- UTMs, `fbclid` e `gclid` foram preservados;
- canonical permaneceu correto para `/`, `/en/`, `/es/`, `/fr/` e posts.

A versão oficial 3.8.9 continua respondendo 200 nas variantes `?lang=...`, com canonical apontando para a URL de idioma. Portanto, o comportamento que o patch antigo preservava continuou existindo sem adulteração do plugin.

## Reconciliação de falhas transitórias

Durante o bulk update, quatro chamadas POST para `/wp-admin/admin-ajax.php` retornaram HTTP 503 entre `14:40:57Z` e `14:41:06Z`.

Essas respostas foram restritas à janela de atualização:

- arquivo `.maintenance`: ausente ao final;
- após `14:50:21Z`: 49 respostas Nginx 200 e 63 respostas Apache 200;
- HTTP 5xx pós-smoke: zero.

Dois registros de warning eram do `wp-file-manager` tentando inspecionar paths fora do `open_basedir` durante o bulk update. Não eram erros do Polylang, não foram fatais e não produziram regressão pública.

## Conclusão

F028 está **RESOLVIDA E VALIDADA**.

A atualização executada por Rodolfo:

- removeu o patch manual antigo;
- restaurou a integridade oficial do Polylang;
- manteve o comportamento multilíngue necessário;
- preservou tracking e canonicals;
- não deixou falha persistente.

Não é necessário criar mu-plugin, restaurar linhas manualmente ou executar novo canário.

## Evidências

Workspace:

`/root/.hermes/profiles/zeus/workspace/growpowerhub-f028-audit-20260923/`

Artefatos principais:

- `post-update-live.json`;
- `post-update-discovery.json`;
- `post-update-logs.json`;
- `post-update-5xx.json`;
- `audit-live.json`;
- `behavior-live.json`.
