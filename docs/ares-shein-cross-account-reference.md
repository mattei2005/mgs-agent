# SHEIN — referência read-only entre contas

Task: t_37bef547. Autorização de comportamento: Rodolfo, mensagem 1560012034580414530.
Fonte de autoridade: `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json#/cross_account_reference_policy`.
Capacidade instalada: `data/ares/meta-ads/engine-v3/config.json#/shein_cross_account_reference`.

## Estado técnico e limites

Implementação no intake/compiler e no schema/planner do mesmo Engine v3, sem writer paralelo, cron ou restart.
A fonte mantém seu `account_id` real e é somente lida. Campanha/conjunto novos usam os edges diretos da conta destino.
`reference` guarda conta/campanha/conjunto/anúncios/Page originais, idioma, acesso READ_ONLY e a rota de lineage.
`source_ad_id` entra somente no anúncio novo direto, não no shell de campanha/conjunto. Não se trata de clone nativo entre contas.
A documentação oficial aceita `source_ad_id` no create de anúncio, mas não comprova aceitação cross-account nem serving do caso. Esses dois estados continuam explicitamente não verificados.

Escopo implementado:
- Qualquer uma das seis partições SHEIN, com fonte e alvo exatos na mesma partição/canal, USD e idioma compatíveis.
- Uma campanha por pedido de Website URL literal; 1–5 anúncios novos, em ordem expressa. Múltiplas campanhas com a mesma UTM literal são rejeitadas, não fracionadas ou reinterpretadas.
- `mode=from_zero_prestaged`, `source_account`, `source_campaign_id`, `source_number`, `website_url`, mídia/copy e demais inputs normais.
- Fonte/exact campaign, acesso/saúde/moeda/timezone, Page/tarefas, pixel existente e evento ADD_TO_WISHLIST verificados separadamente; não modifica credenciais/delegação/pixel.
- Budget explícito ou `budget_from_reference=true`; estratégia/cap resolvidos pela API/delta. USD0.90 gera COST_CAP + bid_amount 90.
- Número novo livre: destino vazio começa 001; inventário é relido antes do primeiro write. O tracking explícito c01 permanece literal; nome visível recebe três dígitos. Colisão com número/UTM solicitados bloqueia antes de mídia/write.
- Em criação nova com referência externa, usar a Page aprovada da conta destino ou expressamente escolhida (`target_page_id`), nunca herdar a Page/Instagram da origem automaticamente. Essa regra supersede a herança anterior por correção explícita de Rodolfo (1560031432968114310). Validar tarefas e identidade da Page alvo; reference.page_id conserva a origem e reference.target_page_id conserva o alvo quando diferentes.
- Configuração compatível viva de público, atribuição e identidade regional é preservada; ausência de configuração material bloqueia. Country de categoria especial ausente com categories=[] é normalizado para [] apenas no alvo.
- Website URL/copy expressos permanecem literais. URL tags ficam vazios para não sobrepor a Website URL solicitada.
- Features individuais do creative são preservadas; somente standard_enhancements descontinuado é removido. QA e pré-ativação comparam os campos originais; defaults novos só podem ser OPT_OUT. O GET existente inclui essa evidência, sem adicionar chamadas ou alterar as rotas dos pedidos comuns.

## Mídia e recuperação

`campaign_groups` também aceita from-zero com referência explícita, mantendo 1–5 arquivos, ordem e texto do grupo.
`prepare-media` valida fonte/alvo/capacidade antes de upload/reserva, usa somente o alvo e o registry canônico.
Pasta `{gestor} - USADOS` precisa pertencer ao VID/pool canônico da operação, com Shared Drive, língua e ascendência confirmados. A pasta não é tratada como pool inédito.
Arquivos selecionados expressamente são reuse request-scoped; download/checksum, sanitização, reserva, conciliação e pre-stage canônicos continuam obrigatórios. Arquivos do gestor permanecem na pasta, sem move/cópia de conveniência.
Recuperação central relê objetos e cria somente a camada comprovadamente ausente. Teste com crash após primeiro anúncio confirmou que o próximo tick criou apenas o segundo anúncio, sem repetir shells/creatives. Falha de readback depois dos IDs completos retomou somente readback.

## Caso exato exercitado

Request original: `shein-1560010597385506986`; mensagem/relógio preservados, nenhuma execução Meta iniciada.
Alvo: Escalatepower-US-SHEIN-EN-02-G002 / 1062887799996139.
Referência: Yolokfx-US-SHEIN-EN-01-G002 / 7840111366055613, C129 / 120255675692010150.
Read-only real confirmou conta destino sem campanhas, slot 001, budget da fonte USD50/dia, Page 1187478564456307 e pixel 1049581090103163.
Os dois arquivos NV_004 e NV_003 foram localizados por ID e lidos na pasta Geizian - USADOS, na ordem original.
Compiler com fonte real + mídia EXPLICITAMENTE SINTÉTICA offline confirmou duas slots, URL/texto literais, USD50/dia, COCAP USD0.90, target shells e Engine COMPLETE_PAUSED. Isso não é criação ou upload real.

Evidências: `data/ares/meta-ads/audit/shein/cross-account-maintenance-t_37bef547/`:
- `inventory-before.json` e `backup/`: inventário/backup das alterações.
- `reference-request.json`: intenção normalizada, IDs da origem e folder real, mesmo request.
- `live-preflight.json`: resultado do comando read-only, sem mídia ou reserva.
- `acceptance-proof.json`: contas/IDs/configuração e Drive real; execução offline claramente distinguida.
- `OFFLINE-template-NOT-EXECUTABLE.json`: template não selado com vídeos sintéticos; nunca usar para execute.
- `verify-acceptance.py`: reprodução de GETs e compiler/core offline, sem writer live.
- `regressions.log`: 295 testes e 164 subtestes aprovados, incluindo Chromium local isolado e recuperação.
- `meta-capability-notes.md`: fontes Meta e limites da documentação.

## Retomada operacional — NÃO executada nesta tarefa técnica

1. Reler checkpoint `ARES-SHEIN-1560010597385506986` e validar origem/autoridade/slot/configuração atuais:
   `python3 /root/mgs-agent/scripts/ares-shein-campaigns.py reference-preflight --input /root/mgs-agent/data/ares/meta-ads/audit/shein/cross-account-maintenance-t_37bef547/reference-request.json --dry-run`
2. Após revisão técnica, preparar somente os dois assets pedidos pelo request original:
   `python3 /root/mgs-agent/scripts/ares-shein-campaigns.py prepare-media --input /root/mgs-agent/data/ares/meta-ads/audit/shein/cross-account-maintenance-t_37bef547/reference-request.json --confirm-execute`
3. O output é o `request-ready.json` no intake do mesmo request. Validar:
   `python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1560010597385506986/request-ready.json --dry-run`
4. A retomada autorizada usa o mesmo comando `campaign`, trocando `--dry-run` por `--confirm-execute`, sem novos requests ou shells artificiais. Construção PAUSED, QA semântico/renderizado e pós-processamento de todos os ads permanecem obrigatórios.
5. O timestamp da mensagem original permanece no request e no E2E. O atraso já excede o alvo de 144s; a aprovação geral do comportamento NÃO é review específico de ativação tardia. Preservar a pendência e usar `shein_continuation.run` somente após mensagem explícita elegível na thread original, pelos mesmos IDs criados e revalidação live.
6. API aceita + lineage/readback + mídia validada não comprovam serving. Confirmar Insights após uma execução humana autorizada; nenhum canário foi liberado por esta manutenção.

## Revisão/publicação procedural

A execução one-shot não alterou skills/memória e deixou a publicação procedural para a sessão responsável. Essa pendência foi resolvida na revisão foreground: o procedimento foi publicado em `direct-traffic-shein-operations/references/general-campaign-fast-route.md` e `meta-campaign-engine-v3/SKILL.md`, supersedendo explicitamente o diagnóstico de capacidade ausente e preservando os limites de aceitação Meta/serving. Readback das duas skills e 63 testes de regressão/referência passaram na revisão. Prova adicional: `data/ares/meta-ads/audit/shein/cross-account-maintenance-t_37bef547/foreground-review.json`. A criação/ativação real da campanha continua sendo etapa operacional separada, não executada nesta manutenção.

Não houve commit/push manual; o auto-commit existente versionou parte das alterações durante o trabalho. Nenhum arquivo alheio ao escopo foi revertido.
