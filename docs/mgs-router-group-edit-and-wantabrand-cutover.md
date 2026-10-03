# MGS Router — editar grupos e cutover Wantabrand

## Autoridade e supersessão

Pedido de Rodolfo `1555799233452314674`, thread `1555381168894115912`: (1) opção para editar nome de grupo; (2) alterar Cloudflare para testar o Router. Esta entrega sucede o estado **sem cutover** em `docs/mgs-router-catalog-layout.md` e `docs/mgs-router-domain-and-keitaro-import.md`; o catálogo, links e percentuais continuam preservados.

## 1. Edição do nome de grupo

- **Grupos → Editar nome → Salvar nome**; **Cancelar edição** retorna ao cadastro.
- Formulário informa quantas rotas/destinos recebem o novo nome. Renomeação atualiza `groups`, grupos das rotas e grupos do catálogo em uma única gravação com revisão otimista. URLs, IDs de destino, aliases e pesos não mudam.
- Bloqueia nome vazio e duplicado; cancelar não grava; filtros de grupo selecionados acompanham a renomeação.
- Nenhum nome real foi escolhido/alterado por Zeus: a opção foi publicada para Rodolfo usar.
- Chromium local renomeou grupo compartilhado por duas rotas/um destino, verificou reload, filtros, cancelamento e rejeição de duplicado. Dados sintéticos somente no fixture.
- Chromium público nas duas contas confirmou botão, formulário preenchido e cancelamento sem gravação, além das quatro abas/mobile/login/API/logout.
- 33 testes Go, race detector, vet, JS e build passaram.
- Binário ativo SHA-256: `3858da29bc8d2e2c3e4247064206d6e594201dff8581089b9dc0472f61f3d429`.
- Backup binário/estado: `/root/.local/share/mgs-router-rollbacks/1555799233452314674/`, privado. Binário anterior exercitado com estado copiado: 41 rotas, 2 usuários, válido.
- Apenas Router reiniciado. Gateways, unidade, TLS, usuários e configuração de rotas permaneceram iguais ao pre-deploy.

## 2. Cloudflare — cutover ativo

- Zona `wantabrand.com`, ID `cf02cbe3b1401e7825c70927ba7c6f90`, token aprovado `Cloudflare MGS Admin Token - mattei20052`; o item mattei2005 não via esta zona.
- Quatro registros existentes atualizados por PATCH, sem excluir/criar registros:
  - `card.wantabrand.com` A `167.235.247.79` → `2.25.165.171`.
  - `card.wantabrand.com` AAAA `2a01:4f8:c013:55b2::1` → `2a02:4780:75:4061::1`.
  - `tarjeta.wantabrand.com` A e AAAA: mesmos pares acima.
- Proxy ligado e TTL Auto preservados; SSL da zona já era `full` e não foi alterado. Digest das configurações de todos os demais registros DNS permaneceu igual.
- Listener atual aceitou TLS no IPv6 público e respondeu 403 pelo edge guard antes da troca, comprovando Router dual-stack sem alterar `/etc` ou firewall. Não presumir IPv4-only pelo texto `--listen 0.0.0.0:443` quando Go/OS oferecem socket dual-stack; provar no runtime.
- Preflight: sem Page Rules, Workers routes ou load balancers. Rulesets de configurações/redirect dinâmico inexistentes (404/10003). Endpoint `http_request_redirect` não é fase válida de zona (400); foi substituído pelo endpoint correto `http_request_dynamic_redirect`, que confirmou ausência. Não houve alteração de regras.
- A origem anterior e os IDs exatos estão preservados em `data/mgs-router-wantabrand-dns-preflight.json`; rollback é PATCH desses mesmos IDs, sem deleção/recriação.
- Canary por host: `card` validado antes da troca de `tarjeta`.

## Resultado real e recuperação

Durante a convergência Cloudflare, alguns requests ainda receberam a origem Keitaro antiga (302 apenas com cinco UTMs, `Cache-Control: no-cache, no-store, must-revalidate`, sem `Referrer-Policy`) enquanto o challenge assinado já comprovava Router. O CF-Cache-Status era `DYNAMIC`; não era HIT de cache de página. DNS estava correto na API. Nenhum Worker/LB/regra de redirect ou proxy de saída explicava a mistura.

- Primeira tentativa: `public_redirect_mismatch:card.wantabrand.com/WKFq61Xh`; rollback dos dois registros card validado, tarjeta intacto.
- Segunda: 31 rotas card passaram com retries, mas `/admin` ainda recebeu resposta antiga; `traffic_host_reserved_or_unknown_path_not_blocked:card.wantabrand.com/admin`. Rollback card validado novamente.
- Correção segura: registrar diagnósticos sanitizados, tolerar convergência com backoff finito e exigir **uma varredura completa sem falhas**, nunca juntar sucessos isolados de respostas antigas/novas.
- Terceira tentativa: card teve 4 e 8 falhas nas primeiras varreduras, depois 0 na terceira; tarjeta teve 4, depois 0 na segunda. Só após varreduras limpas, readback DNS e SSL/digest dos demais registros o cutover foi concluído.
- `card`: 31 rotas; `tarjeta`: 10 rotas. Todas as **41 rotas** tiveram GET e HEAD 302 para URL permitida pela configuração, query original completa preservada, `no-store` e `no-referrer`.
- `/admin`, `/login`, `/api/routes` e alias desconhecido responderam 404 nos hosts de tráfego, sem expor painel.
- Ambos os hosts passaram o challenge HMAC por HTTPS e ficaram verdes no fluxo real de verificação do painel, confirmado nas duas contas.
- Testes fim a fim seguiram redirects até páginas reais HTTP200, com fbclid e parâmetros repetidos preservados:
  - https://card.wantabrand.com/nWySsksW
  - https://tarjeta.wantabrand.com/8nyMq5pH
- Não houve alteração de Keitaro, DTR, Smart Bidding, credenciais, SSL, firewall, budgets ou outros DNS. Apenas o atendimento dos dois hosts de tráfego passou para o Router.

## Fontes e continuidade

- `data/mgs-router-group-edit-cutover-receipt.json`.
- `data/mgs-router-wantabrand-dns-preflight.json` (rollback exato).
- `data/mgs-router-wantabrand-dns-first-attempt.json`, `data/mgs-router-wantabrand-dns-second-attempt.json` (falhas/rollbacks históricos).
- `data/mgs-router-wantabrand-dns-cutover-validation.json` (resultado ativo).
- `data/mgs-router-public-validation.json`, `data/mgs-router-public-end-to-end-validation.json`.
- Executor: `scripts/mgs-router-cutover-wantabrand-dns.py`, vinculado ao pedido acima; inclui readback, canário, recuperação e varredura limpa.

Renomeações futuras pertencem ao painel e sua revisão atual. Não reexecutar o organizador inicial para impor os três nomes antigos: preserva/falha fechado frente a alterações posteriores. Rollback de DNS ou código após esta entrega precisa reconciliar alterações concorrentes e a autorização aplicável.
