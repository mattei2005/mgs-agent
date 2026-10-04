# MGS Router — auditoria de páginas de destino

## Autoridade e limite

- Rodolfo confirmou em1556352434480095341, thread1555381168894115912, a investigação dos destinos dos seis hosts previamente identificados, **mantendo rotas e SSL intactos**.
- Esta é auditoria read-only, não autorização para corrigir URLs, recriar conteúdo, cadastrar aliases, emitir certificados, alterar DNS ou reparar WordPress.
- Escopo: car.cliquet.com, car.openzed.com, job.conectageral.com, tarjeta.conectageral.com, tarjeta.eggbev.com, tarjeta.portalrelevante.com.

## Cobertura e resultado

- Enumeradas **52 rotas** e **134 URLs de destino únicas por host/path**, preservando todas as variantes originais de query e referências de aliases. Todas as URLs correspondem ao snapshot Keitaro autorizado.
- **104 destinos HTTP404** e **30 destinos HTTP525**. Bare URL e URL com query real da fonte apresentam o mesmo status; nenhuma mudança de resultado causada pelas UTMs. Nenhum desses134 destinos antigos retornou200.
- Agrupamento por host de tráfego (há um destino compartilhado entre dois hosts, portanto somar os grupos produz135 referências, não134 URLs únicas):
  - car.cliquet.com:21 destinos404.
  - car.openzed.com:22 destinos404.
  - job.conectageral.com:13 destinos404.
  - tarjeta.conectageral.com:15 destinos404 e15 destinos525.
  - tarjeta.eggbev.com:24 destinos404.
  - tarjeta.portalrelevante.com:10 destinos404 e15 destinos525.
- Homes dos cinco domínios principais retornam200. Homes es.conectageral.com e es.portalrelevante.com retornam525.
- Coleta REST autenticada GET-only nos cinco WordPress principais mais finanzas.conectageral.com, finanzas.eggbev.com, finanzas.portalrelevante.com e jobs.conectageral.com. Paginação reconciliada com os totais do provedor em cada tipo; posts/pages publicados e não publicados consultados, além de coleta independente da lixeira (zero objetos nos nove sites).
- Chromium real confirmou página404 antiga, artigo KFC atual e falhas525 públicas nos dois hostses.

## Causa e candidatos confirmados

### 1. Empregos ConectaGeral — conteúdo encontrado em outro host

Todos os **13 slugs** de `https://conectageral.com/en/<slug>/` existem publicados em `https://jobs.conectageral.com/<slug>/`, com IDs e slugs exatos, e as13 páginas atuais retornaram200.

Exemplo:
- Antigo404: https://conectageral.com/en/kfc-employment-opportunities-lp/
- Atual200: https://jobs.conectageral.com/kfc-employment-opportunities-lp/

A rota ponderada `job.conectageral.com/artigosjobs` contém esses13 destinos. Correção proposta, **não aplicada**: substituir somente host/prefixo de cada um por seu link WordPress atual confirmado, preservando aliases, pesos, query fixa/macros e demais rotas. A decisão anterior de fidelidade literal deve ser excepcionada explicitamente para esses13 URLs antes de gravar.

### 2. Hosts antigos es — falha TLS antes do WordPress

- Cloudflare mantém es.conectageral.com e es.portalrelevante.com proxied, A162.55.28.178, SSLFull. Esse DNS e SSL não foram alterados pelo cutover de tráfego.
- OpenSSL na origem162.55.28.178 com SNI de cada hostes recebe **TLS alert80/internal error**, antes de servir um certificado/aplicação.
- O mesmo IP com SNI conectageral.com/portalrelevante.com completa TLS1.3, certificado correto e verificaçãoOK.
- API RunCloud live confirma webapps atuais do domínio principal, finanzas e jobs; os nomeses não aparecem nos domínios cadastrados dos apps desses sites.
- Diagnóstico: apontamentos legados es chegam a uma origem que não atende corretamente esses nomes em TLS. **Não classificar como simples certificado vencido**, nem diminuir SSL paraFlexible. Reativar nomeses ou substituir destinos por páginas atuais são decisões diferentes; os30 slugs não têm correspondência exata no catálogo consultado.

### 3. Outros404 — alvo antigo sem equivalência exata localizada

Além das13 páginas de emprego recuperadas, **91 URLs404** não têm correspondência exata de slug entre posts/pages publicados, não publicados ou lixeira dos nove sites consultados. Isso prova ausência de equivalente exato no catálogo atual consultado; **não prova exclusão permanente nem ausência em backups/outros WordPress**. Há artigos com nomes de produtos semelhantes, mas não foram tratados como o mesmo destino nem escolhidos automaticamente.

Ações possíveis exigem novo escopo: recuperar os artigos exatos de backup, mapear substituições produto/país/idioma/REC-P1 com revisão humana ou retirar destinos/rotas especificamente autorizados. Não recriar conteúdo editorial por iniciativa de Zeus.

## Preservação, recuperação de coleta e concorrência

- Readback final:35 registros de tráfego ativos,SSL das11zonas e digest de todos os DNS não-alvo iguais ao cutover; rotas/domínios/usuários/unidade e binário iguais ao baseline capturado no início desta auditoria. Zero escrita externa deliberada nesta tarefa.
- BinárioRouter difere do recibo histórico de cutover, mas já era o novo binário quando esta auditoria começou. Origem reconciliada na ordem audit→inventário→REPORT→Git→session: implantação de segurança autorizada1556332890743115850, receipt `backups/security-round-1556332890743115850/router-deployment.json`, hash instalado/processo igual ao runtime. Não é anomalia e não foi restaurado.
- RunCloud API retornou403 no User-Agent genérico. A mesma credencial/chamadaGET funcionou200 com o User-Agent canônico do inventário; coletor corrigido e retomado sem token/permission changes. Paginação parcial inicial foi corrigida para seguir meta.pagination/lastPage; coleção integral pertinente foi repetida. Paramiko opcional não estava instalado e não foi necessário; usou-se OpenSSL e API canônica, sem instalação ou credencial nova.
- Validator inicialmente comparava binário com recibo histórico, não com baseline fresco. Comparação corrigida, origem histórica reconciliada e readback final aprovado. Nenhuma alteração de produção foi feita para satisfazer o teste.

## Artefatos

- `data/mgs-router-destination-audit-1556352434480095341.json`:134 destinos, probes públicos/queries, homes e hashes.
- `data/mgs-router-destination-audit-provider-readonly.json`:Cloudflare DNS/SSL relevantes.
- `data/mgs-router-destination-audit-origin-tls.json`:SNI origem, controles positivos e alertasTLS.
- `data/mgs-router-destination-audit-wordpress-controlplane.json`:catálogos REST e apps/domínios RunCloud sanitizados.
- `data/mgs-router-destination-audit-wordpress-trash.json`:lixeira GET-only.
- `data/mgs-router-destination-audit-url-candidates.json`:13 equivalências exatas/HTTP200, demais não equivalentes.
- `data/mgs-router-destination-audit-public-browser.json`:evidência DOM pública.
- `data/mgs-router-destination-audit-final-validation.json`:contagem/invariância final.

## Próxima decisão

Auditoria completa; correção de destinos não realizada. Recomenda-se o menor canário já verificável: autorizar **somente os13 destinos da rota job.conectageral.com/artigosjobs** para suas páginas atuais jobs.conectageral.com, mantendo query/pesos/path e sem mexer emDNS/SSL. Os demais121 destinos dependem de recuperação/mapeamento; o tratamento dos hostses permanece separado.
