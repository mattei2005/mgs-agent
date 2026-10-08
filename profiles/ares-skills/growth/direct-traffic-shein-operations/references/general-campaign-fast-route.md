# SHEIN — pipeline comum dos seis gestores

## Regra ativa

Pedidos equivalentes de Rodolfo e dos gestores autorizados seguem o mesmo intake, compiler account-scoped, Engine v3, guards, recovery e readback. Não existe fluxo rápido exclusivo do CEO. Política canônica: `data/ares/meta-ads/policies/SHEIN-US-DIRECT-request-parity.json`. Gestores somente nas próprias contas e no próprio canal pai; Rodolfo conserva escopo global. Nunca mudar credencial, billing, app permissions, pixel/CAPI estrutural ou automação recorrente por consequência dessa regra.

## Intake natural e descoberta de Páginas

- Os seis canais `shein-g001`…`shein-g006` são canais dos gestores SHEIN. O operador informa a conta pelo nome completo como Rodolfo fez; o nome já identifica site/país/vertical/idioma/gestor. Resolver o ID por lookup exato, sem exigir que o operador repita o site ou complete um formulário. Domínio/URL de destino ainda deve ser reconciliado com a fonte canônica e passar pelo gate, nunca inventado acrescentando `.com` ao rótulo.
- Manter dois catálogos compactos e independentes somente quando reduzirem descoberta: contas (nome → ID → gestor/canal) e Páginas (nome → ID + evidência de acesso). Não carregar inventários completos no prompt nem consultar a BM inteira a cada pedido; filtrar apenas os registros necessários. Não transformar observações de uso em regras de propriedade ou associação exclusiva.
- Não presumir relação exclusiva Page ↔ site, conta ou gestor: uma mesma Page pode ser usada em contas de sites diferentes quando o pedido/contrato e as permissões reais permitirem. Em duplicação/clone, a campanha exata solicitada determina a Page a preservar. Uma campanha amostrada não fixa default eterno. Em criação do zero, resolver a Page escolhida/aprovada para o pedido e validar o acesso; ausência de campanha não prova ausência de Page ou indisponibilidade da conta.
- Para inventariar nomes/IDs de Páginas, a fonte primária é a seção Pages da BM. AdsPower é uma forma autorizada de abrir a sessão correta e consultar essa BM/interface, não a regra que vincula Page a site/gestor. Mapeamento visual é leitura: não autoriza gerar/trocar tokens, mudar permissões ou executar campanha por caminho alternativo.
- Ausência da Page no token corporativo ou erro em leitura é evidência de limitação daquela consulta, não prova isolada de falha de criação/clone. Distinguir Page observada na interface, acesso de leitura, tarefa de anúncio e serving. Não anunciar bloqueio geral ou pedir mudança de delegação antes de diagnóstico suficiente.

## Fontes e resolução rápida

- Nome exato/ID → gestor/canal: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json`.
- Parâmetros e prontidão de cada conta: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json`.
- Registro dos modos e guardrails: `data/ares/meta-ads/engine-v3/config.json`.
- Autoridade: `authorized-users.json`, `permissions-matrix.md` e `SHEIN-US-DIRECT.json#/manager_channels`.

O catálogo não prova que uma Page está delegada nem que uma conta vazia já possui parâmetros de criação aprovados. Não confundir `LIVE_SOURCE_READY` (modelo Meta/Page/pixel acessível) com mídia nova disponível ou serving validado. `PAGE_ACCESS_PENDING` e `NEEDS_ACCOUNT_REFERENCE` são pré-requisitos materiais aplicáveis igualmente a Rodolfo e ao gestor, não versões diferentes de procedimento.

## Comando normal único

```text
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input <request.json> --confirm-execute
```

O comando faz preflight vivo, seleção da fonte na conta exata, compiler, prevalidation/plan, conciliação de numeração antes do write, delegação ao Engine central e readback. Sem confirmação ou com `--dry-run`, não entra no writer. `single-clone` é alias de compatibilidade, não rota privilegiada; `prepare-live/materialize` G005 de três modos fica apenas legado/rollback, não intake rotineiro.

JSON interno de intenção (não formulário obrigatório ao gestor):

```json
{
  "request_id": "shein-MESSAGE_ID",
  "account": "NOME EXATO OU ID DO CATALOGO",
  "mode": "pure_clone",
  "source_number": 110,
  "quantity": 1,
  "budget_usd": "30",
  "start_time": "2026-10-08T00:00:00-04:00",
  "status": "PAUSED",
  "authorized_by": "DISCORD_SENDER_ID",
  "source_channel_id": "CANONICAL_PARENT_CHANNEL_ID",
  "source_thread_id": "ACTUAL_THREAD_OR_CHANNEL_ID",
  "source_message_id": "ACTUAL_GATEWAY_MESSAGE_ID"
}
```

Resolver todos os IDs de origem pela metadata real do gateway. Não confiar no nome exibido do usuário/canal. Em threads de gestores, `source_channel_id` é o pai canônico. Source message ID é a mensagem, nunca o ID da thread: o snowflake mede mensagem → readback. Se metadata não estiver disponível, declarar medição parcial, sem inventar timestamp. Data/hora/budget/quantidade/status são somente os do pedido atual, não defaults do exemplo.

Modos suportados pelo compiler/core:

- `pure_clone`: preservar posts/mídia/copy e lineage; tracking e números novos; Page token direto para contadores.
- `clone_prestaged`: copiar shell e anúncios por lineage, com assets novos pre-stageados na conta exata; 1–5 ads por campanha.
- `from_zero_prestaged`: shell do zero nos edges diretos; três ads por campanha; source campaign/adset IDs proibidos no executor; somente lineage de ad quando exigida pela conta. Uma referência interna de copy/estratégia pode ser lida sem transformar o modo em clone.

Quantidade 1–100: um manifest, números sequenciais e bundles 2+2+…+1 pelo core. Budget é por campanha. Não montar manifests ad hoc ou pesquisar scripts durante o pedido; materializar apenas intenção e usar o runner.

## Mídia nova

A seleção visual/semântica, liberação, sanitização, reserva e pre-stage continuam no fluxo canônico de Creative Ops antes do manifest. `asset_refs` são IDs/checksums internos resolvidos desse fluxo, não dados exigidos ao gestor. O handoff só aceita assets da língua correta, sanitizados, em READY, sem uso conhecido, reservados pelo request exato, associados à conta, processados e com título de lineage/checksum verificável. Credencial Google somente a Service Account canônica e Shared Drive MGS-AGENTS. Não consumir upload humano reservado em silêncio. Preservar original e registry de pre-stage.

Depois de readback Meta completo, o mesmo pipeline valida vídeo final por lineage, move somente o tratado de READY para TESTING com readback e registra ads/creative/post/history no inventário sob lock. Falha mantém IDs e POSTPROCESS_PENDING; repetir apenas a camada ausente com o mesmo request, sem recriar campanhas nem excluir mídia. Conte upload e tratamento no tempo total, não prometer o tempo de uma duplicação sem mídia nova.

## Prova, limites e recovery

- Fonte na mesma conta, evento fixo Add to Wishlist, Page/pixel/task vivos, URL de destino autorizada, moeda e timezone vivos.
- Tokens históricos válidos como `c01`/`c0101` são capturados literalmente; números/tracking canônicos novos não reescrevem a fonte. Nome antigo US-EN não prova idioma de mídia; novo nome usa idioma do catálogo, preservando posts/copy no pure clone. Qualidade/compatibilidade de mídia continua exigindo evidência no intake criativo.
- Budget/status/start explícitos; sem ativação presumida. ACTIVE exige horário futuro válido. Guardrails, quotas e bloqueios reais permanecem.
- Mesmo sender/account/channel gera os mesmos parâmetros que Rodolfo para o pedido equivalente; cross-manager/channel é recusado antes de credencial ou API write.
- State persistido antes do Engine, per-account lock/context, IDs/checkpoint do core, retomada readback-first. Nenhuma credencial ou Page token persistida/impressa.
- Flags age/gender normalizados pela Meta são ressalva, não cópia 100% idêntica; não repetir writes já comprovadamente ineficazes. Sem-base/contadores ausentes não viram zero.
- Somente resumo final curto; interromper com mensagem apenas por decisão necessária, bloqueio/falha real. `tool_progress: all` permanece.

## Calibração

Testes offline: `test_shein_general_runtime.py`, `test_shein_single_clone_route.py`, `test_ares_shein_campaigns_v3.py`. Usar fake transport somente explicitamente offline. Dry-run live não cria campanha nem valida serving. Ganho E2E real exige próximo pedido humano autorizado; aprovação desta arquitetura não autoriza canários Meta por si só.
