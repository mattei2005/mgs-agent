# Openzed US-CC-EN — corte de destinos aprovado por Rodolfo

## Autoridade e escopo

- Discord thread: `1559601841036198031`.
- Pedido/decisão: `1559931178050527265`.
- Alterar somente as URLs das 450 rotas do Grupo A e das 159 rotas Vizioid dos Grupos B/C, usando os cinco destinos live Openzed US-CC-EN.
- Preservar IDs/nomes/topologia dos pools, nomes de rota, UTM_Content literal, SOURCE/COUNTRY/VERTICAL/LANGUAGE/MEDIUM, APPEND_PARAMS, ACTIVE e freeze.
- Fincgriffin, oito casos isolados, 33 rotas de perda de parâmetros e Crédito para Veículo não fazem parte do corte de destinos explicitamente escolhido. Foram revalidados, sem alteração de produção.

## Resultado e decisão ativa

609 rotas foram alteradas em 26 pools existentes de seis publishers: Boostingecon 90, Escalatepower 90, Growpowerhub 90, Mavroa 90, Yolokfx 90, Vizioid 159. Nenhum pool criado/excluído, nenhum rascunho republicado, nenhuma alteração DNS/SSL/credencial ou congelamento do otimizador.

Destinos aprovados e testados:

- https://openzed.com/rec-us-cc-first-digital-nextgen-mastercard
- https://openzed.com/rec-us-cc-fit-mastercard
- https://openzed.com/rec-us-cc-milestone-gold-mastercard
- https://openzed.com/rec-us-cc-bankamericard
- https://openzed.com/rec-us-cc-citi-double-cash

O snapshot live Openzed forneceu a sequência por família. A atribuição aos pools-alvo foi cíclica na ordem semântica das identidades, preservando a topologia e a ordem armazenada das linhas. Esta é uma configuração de destino, não autorização para congelamento ou mudança de país/idioma das identidades legadas.

## Validação efetivamente executada

- Canário: 22 rotas, readback SB passou; primeiro teste público falhou porque a configuração servida ainda continha URLs antigas.
- Causa localizada: RewriteRules Apache geradas em `.htaccess`; resposta Cloudflare DYNAMIC e queries novas preservavam o destino antigo, descartando a hipótese inicial de cache de redirect como explicação suficiente. O mecanismo nativo de publicação SB não foi certificado; não atribuir a falha a PHP 8.3 nem afirmar que esse mecanismo foi reparado.
- Recovery dentro do mesmo escopo: backup privado completo, SHA-256/CAS, substituição atômica somente dos tokens de destino das regras autorizadas. Preservados padrões, `R=302`, QSA, captura de barra, todas as outras linhas, proprietário e mode.
- Canário público após recovery: 22/22 HTTP 200, destino Openzed esperado e sete parâmetros preservados.
- Teste final público direto de cada link: 609/609 HTTP 200, destino esperado e igualdade de parâmetros; sem extrapolação por destino.
- Readback SB em nova sessão: 26 pools/609 rotas corretos, 482 pools globais com IDs, metadata e identidades preservadas.
- Readback remoto posterior: seis arquivos com hashes esperados; reconstrução a partir do backup original prova que somente os 609 tokens de URLs aprovados diferem.
- Guardas públicos: seis homepages HTTP 200; seis `.htaccess` públicos HTTP 403.

## Limitação AdOps — não confundir com link saudável

Os catálogos live dos seis publishers de origem não contêm as URLs Openzed. Não transportar operações do publisher Openzed nem inventar identificadores. Conforme a exceção operacional para URL explicitamente ordenada e publicada, as 609 rotas foram gravadas com `jbf_operation` vazia. Estado: **destinos públicos recuperados, AdOps pendente**, não certificação de prontidão completa de monetização. Cadastro e geração das operações pertencem a AdOps SB; não realizados por Zeus.

## Lista residual revalidada

Foram retestados 201 links residuais, separadamente dos 609 migrados:

- Fincgriffin: 159/159 ainda terminam em 404, nos prefixos `fincg-es-cc-es`, `fincg-gb-cc-en`, `fincg-tr-cc-tr`; cada um tem Drip m0–m28 + nm e Broadcast 001–023. Não alterados.
- Oito casos isolados: 8/8 ainda terminam em 404. Cephyric: `ceph-us-cc-en-drip-m1-1`, `ceph-us-cc-en-drip-nm`, `ceph-us-cc-en-mct-001-2`, `ceph-us-cc-en-mct-002-2`; os dois destinos antigos levam a `?p=7323` com 404 e query removida. Eggbev `eb-us-cc-es-drip-m14-1`, Newsoun `ns-us-cc-es-drip-m14-1`, Lyzmo `ly-us-cc-es-drip-m0-2`, Topfeed `ftf-us-cc-es-mct-001`: encaminham para aliases inexistentes em seus sites Finanzas. As rotas iniciais encaminham; seus destinos é que não abrem.
- Perda de parâmetros: 32/33 continuam reproduzindo: Ducapes 29, Helixenit 2 Drips, Xyvlov 1. `heli-us-cc-en-mct-010-2` atualmente encaminha para Upgrade Triple Cash Rewards com query preservada, portanto não reproduziu a falha antiga. Não foi alterada por Zeus; destinos podem mudar pelo otimizador.
- Crédito para Veículo: `cv-car-br-001` permanece 404, retestado com `g003-s` e `utm_content` vazio literal.

Dentro do conjunto original de 810 links problemáticos, o reteste deste corte resultou em 610 HTTP 200 sem perda de parâmetros (609 corrigidos + um residual que hoje não reproduz), 168 links 404 e 32 HTTP 200 com perda de parâmetros. Os demais links da auditoria original não foram recertificados neste corte.

## Evidências e rollback

- Work/evidence: `/root/mgs-agent/work/sb-smart-routing/openzed-cutover-1559931178050527265/`.
- `plan.json`: backup integral dos pools e atribuição exata por identidade; snapshots before/after, receipts e readback independente.
- `public-final.jsonl` e `public-final-summary.json`: 609 cadeias públicas completas.
- `public-residual.jsonl` e `residual-summary.json`: 201 cadeias residuais.
- `origin-final-validation.json`: hashes e prova de alteração mínima.
- Backups privados no MatteiInc03JBF: `/root/mgs-route-backups/1559931178050527265/`, originais por domínio e candidatos por hash.
- Rollback: restaurar somente os 26 payloads anteriores e os seis arquivos originais mediante CAS dos hashes da configuração aplicada; validar novamente as cadeias públicas. Não executar rollback sobre configuração concorrente sem reconciliação.

## Aprendizado reutilizável

Atualizada a skill própria `smartbidding-dashboard-access`, referência `smart-routing-pool-create.md`: incluir ACTIVE explicitamente; separar save SB de publicação servida; canário público obrigatório; recuperação cirúrgica de RewriteRules somente dentro do mesmo escopo e com backups/hashes.
