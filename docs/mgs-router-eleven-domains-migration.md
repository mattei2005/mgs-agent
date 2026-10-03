# MGS Router — migração dos onze sites Keitaro

## Autoridade e estado

- Thread: `1555381168894115912`.
- Rodolfo pediu migração integral dos onze sites em `1556013403586306080`, seguida de Cloudflare e testes em `1556013519823175741`.
- Rodolfo informou renovação da licença e pediu novo login em `1556017623978999884`.
- Novo login protegido validado. A licença observada é Starter: a edição está bloqueada pelo limite Domains 29/1 e Users 2/1, mas a leitura de toda a configuração funcionou. Não há necessidade técnica de upgrade para concluir a extração feita.

## Snapshot salvo e reconciliado

- Fonte completa: `data/mgs-router-complete-keitaro-source-20261003.json` — **599 campanhas** reconciliadas por ID com a listagem integral e **1274 Landing Pages**. Streams, aliases, hosts, estados, ações, URLs e shares sanitizados; sem token de campanha, cookies, senha ou logs de clique.
- Fonte do escopo: `data/mgs-router-eleven-domains-keitaro-source.json` — **428 campanhas ativas**, **18 hosts de tráfego**, **1247 entradas de destino**.
- Cloudflare: todas as onze zonas visíveis; SSL Full, proxy ativo; DNS de tráfego ainda na origem anterior. Preflight/rollback sanitizado: `data/mgs-router-11-domains-dns-preflight.json`.
- Fontes completas fora do cache efêmero e registradas no inventário. Snapshot não depende de manter a licença ativa; nova alteração na origem exige reconciliação antes de importar.

## Fidelidade antes de importação

O importador `scripts/mgs-router-import-eleven-domains.py` foi exercitado em modo sem alterações. A validação recusou corretamente uma importação parcial. **Zero rotas importadas e zero DNS alterado nesta iniciativa.**

1. Distribuições relativas fracionárias nas campanhas 118, 119, 127 e 185. Shares originais preservados. O Router atual exige percentuais inteiros somando 100; arredondar modificaria a distribuição. Precisa suportar a razão original sem arredondamento.
2. Campanha 133, `card.topfeed.fun/lpsfinance`: URL de destino contém `utm_campaign=pg_#PAGE_ID#&utm_content=drip_m0-1`. O primeiro `#` transforma o restante em fragmento; isso foi confirmado por HTTP302 real na origem. Não corrigir silenciosamente nem presumir o valor pretendido do Page ID.
3. Campanha 304, `card.cliquet.com/6TQYS31C`, nome `CLIQUET EN LOAN CAR - funil 11 03`: zero landings e HTTP500 real na origem. É defeito anterior à migração. Não inventar destino nem descartar sem decisão de Rodolfo.

Os seis casos foram testados na origem: cinco HTTP302, um HTTP500 (campanha304). Evidência: `data/mgs-router-eleven-domains-fidelity-validation.json`; plano bloqueado: `data/mgs-router-eleven-domains-import-plan.json`.

## Próxima decisão e execução

- Obter destino ou tratamento explicitamente autorizado para a rota vazia, e tratamento da URL com `#PAGE_ID#`.
- Preservar as razões dos quatro conjuntos de pesos sem arredondar.
- Só então importar a configuração integral, preservando as 41 rotas Wantabrand/catalog/grupos existentes e suas revisões concorrentes.
- Mostrar/confirmar o diff exato de Cloudflare conforme política vigente, aplicar canário por host com rollback e exigir varredura limpa GET+HEAD de todas as rotas, além de TLS/challenge assinado e cadeias de destino.
- Nenhuma escrita no Keitaro, DTR ou Smart Bidding faz parte desta migração.

## Falhas recuperadas

- Sessão do navegador foi reinicializada durante a extração; os 490 IDs já persistidos foram preservados e somente os 109 ausentes foram recuperados, fechando 599/599 sem duplicação.
- Campo de tipo de Landing Page é `landing_type`, não `type`; listagem completa reconsultada e reconciliada com todos os IDs/nomes/ações/URLs referenciados. Importador repetido com diagnóstico correto e sem escrita produtiva.
- Todos os relays criptografados temporários do login foram removidos e a contagem restante foi validada como zero.
