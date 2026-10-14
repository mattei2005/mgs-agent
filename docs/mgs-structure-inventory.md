# Inventário Classificado — MGS OS

> Status: inventário v0.4 — Ares unificado  
> Data original: 2026-06-07 01:28 EDT; atualização: 2026-07-12  
> Escopo: `/root/mgs-agent`  
> Regra: este documento classifica a estrutura e registra a migração autorizada; runtime real e manifests vencem para estado técnico.

---

## Growth vigente — leitor externo pós-resposta, fila PC1 e 10s (2026-10-14)

- Rodolfo reafirmou na mensagem `1559969789164920903`: o pedido não muda até o final; só depois vem o acompanhamento autorizado. Fonte única schema 3: `data/ares/meta-ads/policies/direct-traffic-landing-followup.json`, agora `ACTIVE_FOR_NEW_REQUESTS`. O hold técnico anterior do Ares foi encerrado por validação do gatilho externo, não por nova aprovação exigida ao operador.
- Gatilho: novo `scripts/ares_campaign_v3/landing_intake.py` lê `delivery_obligations` delivered e a resposta final do mesmo turno por SQLite `mode=ro/query_only`, confirma a resposta via GET Discord, reutiliza manifest/readback salvo e grava somente fila/provas próprias. CAR autônomo usa audit COMPLETE + resposta nativa final já existente; um ID de resposta PARCIAL nunca substitui a conclusão. Zero writes no banco nativo ou no estado/audit da campanha, zero POST da conclusão original e zero chamadas Meta.
- A rota de criação continua sem callbacks/wrappers/stage e o diário permanece byte a byte igual à baseline anterior ao acompanhamento. O consumidor aguarda enquanto existir lease de turno Discord nativa ativa, sem adicionar trava ao criador. Pedidos podem continuar paralelos; apenas PC1 usa FIFO global de uma tarefa, lease física cross-agent, aba nova/fechamento confirmado, 10s reais de anúncio visível e retry silencioso após60s. Problemas somente no destino canônico; sucesso integral usa o texto aprovado de10s.
- Runtime: `ares-landing-intake.{service,timer}` e `ares-landing-followup.{service,timer}` próprios, enabled/active e saída somente local. Intake CPU10%/256MiB; worker CPU20%/1GiB; Nice19, CPUWeight1 e IO idle. Limites não foram aplicados a gateway/engine/contas. Marco de ativação persiste na SQLite própria e impede backfill; nenhuma campanha teste ou navegação histórica foi executada.
- Validação real: GET de resposta nativa entregue; parsers de layout exercitados com provas CAR3/SHEIN1 já salvas, sem jobs/navegação e com fontes intactas; unidades instaladas conferidas por hash/propriedades; prioridade de foreground devolveu WAITING_NATIVE_TURN. Regressão selecionada208 pass, duas verificações CPV legadas separadas; testes cobrem RO mecânico, chunks, resets/cursor, crash entre stage/recibo, cancelamento de alerta obsoleto, exclusão BOT/backfill, concorrência global e10s/9s. A observação real de anúncio/GAM permanece exclusivamente para o primeiro pedido natural de gestor, como Rodolfo definiu.
- Evidência vigente: `data/ares/meta-ads/audit/landing-followup-1559951763019145247/independent-intake/verification.json`. Skills próprias e mirrors atualizados com o gatilho independente; registro/checkpoint mantêm supersessão das versões acoplada e held. Não reintroduzir o wrapper aposentado como fallback.

## Histórico — correção de isolamento e fila única PC1 (supersedido pelo leitor externo acima)

- Rodolfo determinou que o acompanhamento não pode misturar-se à rota de pedidos nem comprometer velocidade/performance; reafirmou fila global entre G001/G006 simultâneos na mensagem `1559963300844933141`. A mensagem `1559964027264962702` supersede o tempo de 20s por **10s contínuos**, inclusive no validador e no aviso de sucesso. Fonte única atual: `data/ares/meta-ads/policies/direct-traffic-landing-followup.json`, schema 2. Esta correção supersede expressamente o desenho acoplado descrito no histórico abaixo.
- Retirado o callback de `daily_cpv.py`; arquivo confirmado byte a byte idêntico à baseline anterior à instalação do acompanhamento. Removida das quatro skills a obrigação de stage/publish-creation/preparo na sessão de pedidos; nenhuma referência de acompanhamento é carregada na rota de criação. O transporte nativo de resposta continua intacto.
- Somente o acompanhamento está `HELD_FOR_FULL_ASYNC_ISOLATION`: timer próprio disabled/inactive, serviço sem processo, fila real vazia, comandos stage/tick/publish-creation bloqueados pelo contrato. Nenhum scheduler/hold de campanha, gateway, credencial, budget, início ou estratégia foi alterado. Reativação exige gatilho externo pós-resposta e isolamento de recursos validados, nunca restaurar wrapper/callback.
- A fila de acompanhamento é global FIFO, não por gestor/canal: uma tarefa ativa no PC1, espera de retry preserva o predecessor, fechamento incerto bloqueia somente acompanhamento. Duas conexões concorrentes para contas/canais distintos foram testadas; apenas uma ganhou o claim, e o segundo gestor aguardou inclusive a retentativa do primeiro. Criação de campanhas não foi serializada.
- Validação: 181 testes selecionados aprovados, duas divergências CPV anteriores separadas; mirror somente das skills próprias Ares reconciliado por hash, sem alteração de outros profiles. Provas e baseline: `data/ares/meta-ads/audit/landing-followup-1559951763019145247/isolation-correction/`. A igualdade de código comprova remoção do acréscimo síncrono, não um benchmark geral de latência. Histórico anterior preservado, mas não representa o estado ativo.

## Histórico Growth — acompanhamento pós-resposta inicial (supersedido pelo isolamento acima)

- Autoridade: Rodolfo `1559951763019145247`, thread `1559932317861158993`, handoff Zeus ao Ares. Escopo: todo tráfego direto CAR/SHEIN/futuros nichos; exclui BOT/Messenger. Fonte única `data/ares/meta-ads/policies/direct-traffic-landing-followup.json`.
- Runtime novo: `scripts/ares-direct-traffic-followup.py`, módulos `ares_campaign_v3/landing_followup.py` e `landing_followup_adapters.py`, SQLite WAL/FULL em `data/ares/meta-ads/landing-followup/`. Fila imutável/idempotente, barreira de resposta ao gestor com GET de autor/thread/conteúdo, consumidor global limitado, lease PC1 cross-agent obrigatória e verificada por ID real de sessão, outbox com ID/nonce/readback. Evidências revisadas ficam protegidas em artifacts do Ares, sem anexos automáticos.
- Integração: wrapper comum de conclusão para pedidos naturais CAR/SHEIN/futuros nichos; callback mínimo no `daily_cpv.py` somente após a resposta normal/readback do runner autônomo. Nenhum browser no campaign writer, nenhum write Meta/GAM/Router/WordPress, alteração de orçamento/estratégia/início/credencial ou restart de gateway. Falha do acompanhamento preserva a criação e reporta exclusivamente na thread de autoridade; primeira ausência de anúncio não alerta, espera 60s e tenta em aba nova. Somente o lote integral aprovado visualmente gera o texto de sucesso ao gestor, sem PC1/GAM.
- Agendamento: `systemd/ares-landing-followup.{service,timer}` instalado em `/etc/systemd/system/`; timer enabled/active, oneshot a cada 15s após inatividade, stdout/journal exclusivamente local. Sem jobs pendentes não abre navegador nem inicia modelo. Não é cron Hermes origin/all e não altera root crontab, gateway, outros profiles ou scheduler de campanhas.
- Skills próprias atualizadas: `direct-traffic-cbo-operations` + `references/landing-followup.md`, SHEIN, Vehicle Finance e Engine v3 com ponteiros para a fonte comum. Audit/baseline/verificação: `data/ares/meta-ads/audit/landing-followup-1559951763019145247/`. Testes novos e regressão sem writes; duas divergências históricas da suíte diária CPV reproduzidas com o backup anterior (referência de token antiga e reader gate legado), não corrigidas fora do escopo.
- Validação viva sem campanha/anúncio de teste: consumidor CLI OAuth respondeu ao smoke isolado, timer retornou sucesso/zero, fila de produção vazia, lease PC1 livre; abertura/fechamento de janela técnica confirmados, Chrome original preservado. Observação real de anúncio por 20s e integração do primeiro pedido de gestor permanecem deliberadamente para o teste natural de Rodolfo; nenhuma alegação de cadastro GAM.

## Atualização editorial — lote SEO multilíngue Raquel (2026-10-14)

- Autoridade: Rodolfo na mensagem `1559935269535486005`, após receber o bloqueio técnico do lote na thread `1559930384852979796`; pedido original de Raquel, exclusivamente 30 rascunhos SEO.
- Configuração: dez registros editoriais mínimos adicionados a `data/sites.json`, somente para os dez alvos allowlisted do briefing; identidade Atena/editor e IDs reais, URLs e categorias confirmados por REST. Registros anteriores preservados. Transporte apenas REST; nenhum webroot inferido e nenhuma operação de filesystem remoto, plugin, credencial, gateway ou dashboard.
- Fonte/backup/evidência: `data/atena/seo-mass-1559930384852979796/decision.json` e `/root/.hermes/profiles/atena/work/seo-mass-1559930384852979796/`; confirmação de autoridade recorrente da Raquel capturada como candidato `KCI-9b42b77250e3ba5c`, sem alteração do registro global de usuários.
- Conteúdo: três novos artigos por portal, mínimo de 1.000 palavras, categoria/idioma do briefing, mesma mídia após a primeira frase e como destaque, fontes externas confiáveis. Writes editoriais continuam sujeitos a QA e readback por ID; integração não declara o lote pronto nem autoriza publicação.
- Fechamento validado: 30/30 posts em `draft`, três por portal, e 30 mídias; leitura autenticada independente comparou corpo raw exato, título/slug/autor, categoria única, tags por IDs diretos, metadados Yoast, links renderizados, alt e posição da imagem após a primeira frase. Faixa final 1.187–1.469 palavras, 39.887 no lote. Contagem publicada de cada categoria preservada; zero publicação. Resultado auditável em `data/atena/seo-mass-1559930384852979796/final-verification.json`. Conflito `SEO`/`seo` retornou `400 term_exists`, reconciliado por GET do termo canônico e retomada do mesmo ID de mídia, sem post/imagem duplicados. Três QAs independentes mais correção da referência legal para CMN 5.004 art.7; cinco imagens regeneradas após QA visual. Nenhum helper global produtivo alterado.

## Atualização operacional — Escalatepower contas e Pages (2026-10-14)

- Autoridade: Rodolfo, mensagem `1559929154030276730`, thread `1559928644149841971`, para configurar o mapeamento das seis contas Escalatepower SHEIN e as seis Pages indicadas; sem criar/ativar campanhas.
- Meta: seis contas saudáveis com ADVERTISE, USD e timezone live `America/New_York`; pixel existente `1049581090103163` associado às seis. As seis Pages estavam na BM mas sem tarefas para o System User corporativo; atribuídos somente ADVERTISE + ANALYZE, com GET administrativo e GET corporativo de cada Page confirmados. Credencial, ownership, billing e campanhas preservados.
- Dados: contrato `SHEIN-US-DIRECT.json#/escalatepower_asset_onboarding` é fonte da autorização e dos bindings explícitos; catálogo de contas, catálogo independente de Pages, profiles e somente seis registros do Engine reconciliados. `ASSETS_ACCESS_READY_CAMPAIGN_SPEC_REQUIRED` distingue acesso pronto de parâmetros/fonte da campanha ainda necessários; não autoriza fabricar referência para contas vazias. Nenhum script, cron, gateway ou arquitetura de credencial alterado.
- Evidência e backups: `data/ares/meta-ads/audit/shein/escalatepower-onboarding-1559929154030276730/`. Observação read-only: campanha existente G006 `120252795396560042` tem token de nome `b01fb06c01`, mas conjunto/destinos `b01fb02c01`; não alterada por este pedido de onboarding.
- Procedimento: skill própria `direct-traffic-shein-operations`, sem nova autorização por falta de cadastro quando o binding já está aprovado; preservar guards materiais de criação e fonte. Validação scoped: contagem e unicidade dos seis bindings, GETs Meta, lookups do runner, igualdade profile × Engine e isolamento dos demais registros.

## Atualização operacional — SHEIN prefixo de campanha NNN (2026-10-09)

- Pedido: Rodolfo na thread `1558159785843499109`, corrigir o prefixo visível da campanha `120249566052890724` de `7` para `007` e prevenir recorrência. POST mínimo somente `name`, seguido de GET: campanha permanece ACTIVE, USD100/dia, COST_CAP80 centavos, mesmo início/conjunto/ads; tracking e resto do nome preservados. Nenhuma outra campanha renomeada.
- Runtime: `scripts/ares_campaign_v3/shein_naming.py` gera prefixo `:03d` em todos os modos SHEIN; faixa 001–999, sem truncar/reciclar. Fonte legada curta continua aceita. Os 36 validators SHEIN em `engine-v3/config.json` exigem prefixo de três dígitos; comparação estrutural provou que somente `campaign_policy.name_regex` mudou nessas contas, nenhum campo de outra operação.
- Fontes: contrato `SHEIN-US-DIRECT.json#/campaign_naming_policy/visible_campaign_number`, registry supersedido na mesma chave `ares.shein.campaign-naming-pattern`, skill própria SHEIN main/general route, novo `tests/test_shein_number_padding.py`. Manifests históricos permanecem imutáveis; recibo de correção separado.
- Evidência/backups/readback: `data/ares/meta-ads/audit/shein/number-padding-120249566052890724/`; regressão red→green do padding em formatter, três modos, fontes legadas e validação antes do write. Sem novas cópias, alteração de budget/lance/schedule/status/UTM, credencial ou gateway.

## Atualização operacional — Geizian SHEIN e review tardio (2026-10-09)

- Autoridade: Rodolfo, mensagem `1558225355930861649`, thread `1558159785843499109`; referência da recusa `1558217596346835120`. Geizian tem Campaign Ops nos seis canais SHEIN e threads, incluindo review explícito de continuação tardia.
- Correção scoped: `shein_continuation.py` usa a mesma autorização live/forçada do canal para review humano na origem, em vez de somente CEO; contrato `channel_authorization_policy.late_recovery_review`, matriz, registry supersedido e duas skills próprias atualizados. SLA/relógio E2E, QA/mídia, manifests/IDs, budget/bid e Critical Subset preservados; zero alteração em `activation.py`/SLA.
- Config Ares: somente os seis `discord.channel_prompts` SHEIN reconciliados via CLI canônica, com readback e comparação do restante inalterado. Removidos drift de solicitante exclusivo, bloqueio de relatório on-demand pela fase e arquitetura histórica de tokens; sem mudanças de credencial/Discord overwrites/cron ou restart.
- Evidência: `data/ares/meta-ads/audit/shein/geizian-authority-1558217596346835120/`; regressão de 167 testes offline aprovada, incluindo permissão revogada, origem/conta/policy errada, bot e mensagem adulterada. Geizian confirmado live em 6/6 canais e origem G002. Retomada central do request `shein-1558212072054071429` concluída: C007 `120249566052890724`, conjunto `120249566055190724`, anúncios `120249566058720724` e `120249566058710724`, todos ACTIVE por GET; USD100/dia, COST_CAP80 centavos, mesmos IDs, QA completo. C006 `120249530169740724` preservada por comparação semântica completa (somente URLs de imagem assinadas rotativas ignoradas com image_hash igual). Relógio E2E original preservado e `e2e_target_met=false`; sem nova cópia.

## Atualização operacional — SHEIN horário vencido e recovery delegado (2026-10-09)

- Autoridade: Rodolfo, mensagem `1558142161659105342` nesta thread `1557274000680288307`; delegação Ares→Zeus aprovada em `1558142033774776411`, thread `1558141425541980203`, já registrada por Zeus em `context/routes.md` / `zeus.ares.manager-authorized-technical-recovery`.
- Horário explícito vencido do próprio dia no timezone verificado da conta resolve NOW após QA, com audit do horário original, sem nova autorização apenas pelo atraso; futuro, PAUSED expresso e próxima meia-noite omitida são preservados. Data anterior ao dia da conta não muda automaticamente.
- Runtime desta correção: novo `scripts/ares_campaign_v3/shein_schedule.py`, hook somente de intake/preflight em `shein_single_clone.py`, testes `test_shein_elapsed_schedule.py`; contrato `SHEIN-US-DIRECT.json#/request_defaults/expired_explicit_start_policy` e skill própria SHEIN (main/general route/standard requests). Snapshots PREPARED vencidos são rematerializados somente antes de write, preservando clock; estados de recovery e manifests/IDs já criados não são reescritos por esta tarefa.
- Comunicação: Geizian avisado na origem e Zeus coordenado com mention/readback, sem writer concorrente; recuperação parcial de C106/CBO segue com Zeus técnico e Ares funcional. A normalização de tempo não corrige a rejeição Meta de CBO e não comprova conclusão da campanha.
- Evidência: `data/ares/meta-ads/audit/shein/schedule-and-recovery-permission-20261009/verification-final.json`; red→green e regressão offline registrados. Zero writes Meta/replay/cópias/restart nesta tarefa. Permissão de recovery não altera billing, credenciais ou Critical Subset.

## Atualização operacional — thread de relatórios YOLO G002 retirada (2026-10-09)

- Pedido explícito de Rodolfo na thread `1557274000680288307`: deletar somente `1558138059344576593` (`Yolokfx Conta 01 Intraday`, pai G002 `1548149300826079333`). DELETE 200 e GET posterior 404 confirmados.
- Rota retirada em `context/ares-operational-map.md`; registro de escopo anterior supersedido por `ARES-THREAD-1558138059344576593-DELETED-BY-RODOLFO`. Histórico canônico preservado; não recriar/publicar na thread. Rodolfo criará o canal substituto; ID ainda não informado.
- Evidência: `data/ares/discord/thread-deletions/1558138059344576593.json`. Sem novo canal, alterações Meta, gateway, cron ou permissões Discord; nenhum job do profile Ares aponta para o ID retirado.

## Atualização operacional — SHEIN lance e autorização por canal (2026-10-09)

- Autoridade: Rodolfo, confirmação explícita na thread `1557274000680288307`; nenhum pedido de campanha ou replay autorizado nesta mudança.
- Regras: `SHEIN-US-DIRECT.json#/bid_strategy_change_policy` e `#/channel_authorization_policy`; matriz, mapa operacional e parity reconciliados. Qualquer participante humano com permissão efetiva de comunicação no canal/thread pode solicitar sobre contas/perfis do canal; gestor titular deixa de ser filtro exclusivo.
- Runtime: `shein_general.py`, `shein_single_clone.py`, novo `shein_channel_authority.py`, `schema.py`, leitura consolidada `engine.py`, proteção `activation.py` e `shell_recovery.py`. Troca de lance é delta somente no alvo, com cap exato/reset, naming coerente e QA antes de ativação; nenhuma mudança em targeting/credenciais/billing. Permissões Discord consultadas read-only por Ares e relidas antes dos writes.
- Procedimento: skills próprias `direct-traffic-shein-operations` (main, general fast route e standard requests) e regra 21 de `meta-campaign-engine-v3`. Dois asserts legados de formulários 1.0 foram reconciliados com o modelo 3.0 já aprovado e o estado técnico real, sem restaurar o formulário antigo.
- Evidência: `data/ares/meta-ads/audit/shein/rules-bid-channel-20261009/` contém backups/inventário, red→green, regressão offline e proof Discord de Geizian nos seis canais e thread `1558126286826774711` (pai G005). Testes offline não provam aceitação Meta/serving; readback live permanece obrigatório no próximo pedido real.
- Sem writes Meta, sem alterações de permissões Discord/cadastro global de usuários, sem cron/gateway/restart. Histórico dos registros anteriores preservado por supersessão; fontes canônicas e checkpoint registrados pelo controle institucional.

## Atualização operacional — CPV13 relatórios isolados (2026-10-08)

- Autoridade: Rodolfo, thread `1557763617578033172`; chave `growth.creditoparaveiculo.account13.reporting.read-only-isolation` no contrato CPV.
- Runtime: wrappers Diário/Intraday da conta 13 e `creditoparaveiculo-fixed-reports.py` no profile Ares. Relatórios usam somente leitura, sem gate persistente de recovery de campanha; checkpoints de ações preservam gates próprios. Lock físico tem espera limitada e aviso idempotente; readback de entrega diferido não é sucesso.
- Auditoria: `data/ares/meta-ads/audit/reporting/Creditoparaveiculo-BR-CAR-BR/intraday-recovery-20261008/verification-final.json`; inventário global dos 49 jobs Hermes, root crontab, systemd timers e gates internos coletado antes/depois. Nenhum schedule/enabled/paused/root crontab alterado.
- Verificação: 111 testes passaram; Intraday live publicado em três partes com GET/conteúdo confirmado, seguido de execução do wrapper automático com duplicação suprimida; zero ações Meta e lease da duplicação pendente preservada.
- Procedimento: `meta-ads-intraday-operations/references/current-operational-pitfalls.md`, conferido após atualização. Pausas históricas CPV/Eggbev autorizadas não foram reativadas.

## Atualização operacional — SMS CHAT (2026-10-05)

- Fonte/auditoria: `data/ares/sms-funnel/audit/creditoparaveiculo/chat-url-1556643119515172927.json`.
- Registro: `growth.creditoparaveiculo.sms-funnel.chat-destination-attribution`, autorizado por Rodolfo na thread `1556643119515172927`.
- Escopo: seis sequências CHAT G001–G006, incluindo TOPFEED G004; destino `https://creditoparaveiculo.com/rec-br-sem-entrada-mesmo-com-nome-restrito` e `utm_campaign=s01c01g00x-chat`, com os demais parâmetros preservados.
- Evidência: seis URLs e destinos dos encurtadores validados; 36 sequências fora do escopo e 42 configurações de campanha inalteradas; seis probes HTTP 200 sem telefone.
- Procedimento atualizado: referência `sms-funnel-wordpress-routing/references/sms-funnel-api-readback.md` registra validação do `external_id` do provedor e comparação consistente entre respostas de sequência e inventário.

## Resumo executivo

Atualização estrutural de 2026-07-12:

```text
Componente                              Estado atual
--------------------------------------  ---------------------------------------------------------
Ares                                    agente ativo unificado Creative Ops + Growth/Media Buying
data/ares/creative-ops/                  dados e inventário unificado de Creative Operations
profiles/ares-skills/growth/             Creative Ops, taxonomia, Meta Library e Campaign Ops
scripts/ares-meta-library-*              runtime criativo migrado para Ares
browser-profiles Ares                    Meta Library/YouTube copiados com origem preservada
authorized-users.json                    7 usuários permanentes no Ares
```

O snapshot de contagens abaixo é histórico de 2026-06-07 e não deve ser usado como contagem atual.

```text
Bloco                         Classe principal        Veredito
----------------------------- ---------------------- ---------------------------------------------
context/                      canônico/conceitual     manter; base Company OS atual
profiles/                     config/skills agentes   manter; versiona SOUL/config/skills próprios
data/                         runtime/operacional     não tocar sem plano específico
scripts/                      automação produtiva     não mexer em massa; validar por script
skills/                       procedimentos globais    manter; revisar só quando skill for usada
docs/                         histórico/planos        manter; atualizar docs de controle
patches/                      patch local Hermes      não tocar sem entender impacto runtime
api/                          API/runtime             não tocar sem plano técnico
tools/                        ferramenta auxiliar      revisar quando entrar em fluxo operacional
backups/                      backup                  preservar último por família; arquivar depois
experiments/                  experimento             baixo risco, mas não limpar ainda
logs/                         audit/runtime           não editar; consultar com filtros
.env / auth / credenciais     sensível/não-versionar   nunca expor; não versionar
```

---

## Contagem estrutural atual

```text
Path                         Arquivos detectados     Observação
---------------------------- ---------------------- ---------------------------------------------
context/                     15                     camada canônica/conceitual MGS OS
data/                        102                    runtime, states, caches e bancos locais
docs/                        28                     planos, changelog, CRONS, inventários
scripts/                     2689                   inclui yoast-scorer/ com muitos arquivos
skills/                      118                    skills globais Content/WordPress
profiles/                    142                    SOUL/config/skills versionadas dos agentes
patches/                     32                     patches Hermes/MGS
backups/                     34                     backups manuais e safety snapshots
experiments/                 584                    spike Honcho/experimentos
tools/                       13                     automações auxiliares
api/                         5                      API local + usage.db
logs/                        543                    logs rotacionados/audit/runtime
```

---

## Inventário principal — context/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
context/                                  canônico      Executive / MGS OS          ativo         manter
context/company-current-operating-model.md canônico     Executive / MGS OS          revisado      manter como fonte CEO
context/company-os.md                     canônico      Executive / MGS OS          proposta atual manter
context/areas.md                          canônico      Executive / MGS OS          auditado      manter
context/agent-map.md                      canônico      Executive / MGS OS          auditado      manter
context/routes.md                         canônico      Executive / MGS OS          auditado      manter
context/sources-of-truth.md               canônico      Executive / MGS OS          auditado      manter
context/permissions-matrix.md             canônico      Security / Access           auditado      manter
context/ares-operational-map.md           canônico      Creative + Growth / Ares     ativo         fonte operacional HOT
context/company.md                        canônico      Empresa                    legado ativo   revisar em bloco conceitual
context/sites.md                          canônico      Sites / Verticais           legado ativo   revisar em bloco conceitual
context/team.md                           canônico      Equipe / Access             legado ativo   revisar em bloco conceitual
context/processes.md                      canônico      Processos                   legado ativo   revisar em bloco conceitual
context/monetization.md                   canônico      Revenue / AdOps             legado ativo   revisar em bloco conceitual
context/acquisition.md                    canônico      Growth / Media Buying       legado ativo   revisar em bloco conceitual
context/security-policies.md              canônico      Security / Access           ativo         revisar depois
```

---

## Inventário principal — profiles/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
profiles/                                 versão agente Agents / Hermes            ativo         manter; não editar em massa
profiles/zeus-soul.md                     config        Executive / Zeus            ativo         manter; ajustar só por governança
profiles/zeus-config.yaml                 config        Executive / Zeus            ativo         não tocar sem plano Hermes
profiles/zeus-skills/                     skill         Zeus / Ops                  ativo         manter; commitar mudanças úteis
profiles/atena-soul.md                    config        Content / Atena             ativo         manter; ajustar depois de Company OS
profiles/atena-config.yaml                config        Content / Atena             ativo         não tocar sem plano Hermes
profiles/atena-skills/                    skill         Content / Atena             ativo         manter
profiles/ares-soul.md                     config        Growth / Ares               ativo         revisar quando Ares avançar
profiles/ares-config.yaml                 config        Growth / Ares               ativo         não tocar sem plano Hermes
profiles/ares-skills/                     skill         Growth / Ares               ativo         manter
profiles/ares-skills/growth/direct-traffic-vehicle-finance-operations/ skill Growth / Ares ativo contrato CPV/Diário; manter em paridade com runtime
profiles/ares-skills/growth/direct-traffic-vehicle-finance-operations/references/creative-cut-24h-strategy.md procedure Growth / Ares ativo estratégia CREATIVE_CUT_24H documentada para conta 05; ativação depende de onboarding/readback
profiles/*bak*                            backup        Agents / Hermes             histórico     manter por enquanto
```

---

## Inventário principal — data/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
data/                                     runtime       Operação                   ativo         não tocar em massa
data/sites.json                          runtime       Tech / WordPress           ativo         fonte técnica; não tocar sem plano
data/authorized-users.json               sensível      Security / Access           ativo         fonte autorização; exige confirmação
data/article-tracker.db                  runtime       Content                    ativo         não tocar
data/card-cache.db                       runtime/cache Content                    ativo         não tocar
data/rec-fingerprints.db                 runtime       Content                    ativo         não tocar
data/wp-term-cache.json                   runtime/cache Content / WordPress        ativo         não tocar
data/lazyblock-*.json                    runtime/config Content / WordPress        ativo         revisar só com pipeline
data/*-state.json                        runtime       Monitores / crons           ativo         não tocar sem plano
data/infra-inventory.json                inventário    Tech / Infra                ativo         manter; atualizar via script
data/knowledge-registry.json             registro      MGS OS / conhecimento       ativo         ponteiro canônico; validar via mgs-knowledge-control
data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json runtime/config Growth / Ares ativo fonte canônica da operação CPV G006
data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR-05-CREATIVE-CUT-24H.json runtime/config Growth / Ares documentado não ativo contrato da estratégia 24h na conta 05; sem writes/crons até gates
data/pendencias.db.json                  runtime       Executive / Ops             ativo         não tocar sem plano
data/discord-thread-imports/             histórico     Agents / Discord            histórico     manter
data/chat-logs/                          histórico     Agents / Discord            histórico     manter
data/card-images-cache/                  cache         Content                    cache         não tocar agora
data/backups/                            backup        Tech / Infra                histórico     manter; arquivar depois
data/deprecated/                         legado        variável                   legado        revisar depois
```

---

## Inventário principal — scripts/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
scripts/                                  automação     Tech / Infra                ativo         não mexer em massa
scripts/cron-control-plane.py             automação     Tech / Infra                ativo         manter; controlar via dry-run/teste
scripts/cron-smoke-test.sh                automação     Tech / Infra                ativo         manter
scripts/housekeeping-bak-cleanup.sh       automação     Tech / Infra                ativo         manter; já preserva último backup
scripts/mgs-safety-backup.sh              automação     Tech / Infra                ativo         manter; backup periódico seguro
scripts/monitor-*.sh                      automação     Tech / Monitoring           ativo         revisar só por incidente
scripts/mgs-rec-runner.py                 automação     Content                    ativo         não tocar agora
scripts/mgs-p1-runner.py                  automação     Content                    ativo         não tocar agora
scripts/mgs-rec-p1-orchestrator.py        automação     Content                    ativo         não tocar agora
scripts/mgs-ops-control-plane.py          automação     Executive / Ops             ativo         não tocar agora
scripts/mgs-ops-briefing.py               automação     Executive / Ops             ativo         não tocar agora
scripts/sync-souls.sh                     automação     Agents / Hermes             ativo         alterar só com validação completa
/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py automação Growth / Ares ativo renderer Diário/Intraday CPV, incluindo Lucro Líquido USD; teste e dry-run obrigatórios
scripts/pendencia-*.sh                    automação     Ops                         ativo         manter
scripts/mu-plugins/                       automação     WordPress                   ativo         não tocar sem plano
scripts/yoast-scorer/                     automação     Content / SEO               ativo         não tocar agora
scripts/deprecated/                       legado        Tech / Infra                legado        revisar depois
```

---

## Inventário principal — docs/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
docs/                                     histórico     Executive / Tech            ativo         manter
docs/mgs-os-restructure-plan.md           plano         Executive / MGS OS          atualizado    manter
docs/mgs-structure-inventory.md           inventário    Executive / MGS OS          v0.2          manter; base Fase 3
docs/CRONS.md                             operacional   Tech / Infra                ativo         revisar sem alterar runtime
docs/PENDENCIAS.md                        operacional   Executive / Ops             ativo         manter; revisar depois
docs/PENDENCIAS-HISTORICO.md              histórico     Executive / Ops             histórico     manter
docs/CHANGELOG.md                         histórico     Tech / Infra                histórico     manter
docs/changelog/                           histórico     Tech / Infra                histórico     manter
docs/security/                            segurança     Security / Access           ativo         revisar depois
docs/rec-p1-*                             histórico     Content                    ativo/legado   revisar depois
docs/rule-classification.md               doc           Tech / Ops                  ativo         revisar depois
docs/site-counting.md                     doc           Sites / BI                  ativo         revisar depois
docs/skills-naming-convention.md          doc           Skills / Ops                ativo         revisar depois
docs/CHECKPOINT-FASE-3.md                 histórico     Content / antigo            legado        revisar/arquivar depois
```

---

## Inventário principal — skills, patches, api, tools

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
skills/                                   skill         Agents                     ativo         manter
skills/content-generate-rec-p1/              skill         Content / Atena             ativo         não tocar agora
skills/content-publish-wordpress/         skill         Content / WordPress         ativo         não tocar agora
patches/                                  patch local   Tech / Hermes              ativo         não tocar sem plano
patches/hermes/                           patch local   Tech / Hermes              ativo         não tocar sem plano
api/                                      runtime/API   Tech / Content              ativo         não tocar sem plano
api/generate-rec-api.py                   runtime/API   Content / WordPress         ativo         não tocar agora
api/usage.db                              runtime       API                         ativo         não tocar
tools/                                    ferramenta    Tech / Creative             auxiliar      revisar quando necessário
tools/canva-local-automation/             ferramenta    Creative / Ares             auxiliar      revisar antes de usar
```

---

## Inventário principal — backups, experiments, logs e raiz

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
backups/                                  backup        Tech / Infra                histórico     manter; arquivar depois
backups/safety/                           backup        Tech / Infra                ativo         manter último snapshot válido
experiments/                              experimento   variável                   baixo risco    manter; revisar depois
experiments/honcho-spike/                 experimento   AI / memória               legado/aux     revisar depois
logs/                                     logs          Audit / Runtime             ativo         não editar; consultar só
logs/events-audit.jsonl                   audit log     Security / Ops              ativo         append-only/consulta
logs/*.log                                runtime       Tech / Infra                ativo         consultar com filtros
.env                                      sensível      Security / Access           ativo         não versionar; nunca expor
AGENT.md / CLAUDE.md                      prompt/doc    Agents / Legacy             ativo         revisar só com plano
*.bak / *~ raiz                           backup        Tech / Infra                histórico     housekeeping controla
inventario-webapps.json                   inventário    WordPress / Infra           histórico     revisar depois
```

---

## Arquivos que exigem cuidado especial

```text
Path                                      Motivo
---------------------------------------- -------------------------------------------------------
.env / auth.json / tokens / credentials   Segredos; nunca expor em chat nem versionar.
data/authorized-users.json                Fonte operacional de autorização; exige Rodolfo.
data/sites.json                           Fonte técnica dos sites; alteração pode quebrar pipeline.
profiles/*-config.yaml                    Config Hermes/gateway; risco de agente offline.
profiles/*-soul.md                        Comportamento de agente; alterar um agente por vez.
scripts/monitor-*                         Monitores/crons; risco de spam/loop se mal editado.
scripts/mgs-*-runner.py                   Pipeline de conteúdo; risco operacional.
scripts/sync-souls.sh                     Sincroniza SOUL/config/skills versionadas; risco de sujeira.
patches/hermes/                           Patch runtime Hermes/MGS; risco sistêmico.
api/                                      Pode estar ligado a runtime/API.
logs/events-audit.jsonl                   Audit trail; append-only/consulta.
logs/*.log                                Runtime; consultar com filtros, não editar.
```

---

## Ações recomendadas por classe

```text
Classe                  Regra
----------------------- -------------------------------------------------------
canônico/context        revisar por bloco pequeno e cascata semântica
runtime/data            não tocar sem plano específico, backup e validação
config/profile          alterar um agente por vez, validar gateway/logs
script/automação        dry-run/bash -n/teste real controlado antes de commitar
skill                   editar quando usada ou quando bug operacional aparecer
patch local             só mexer com plano técnico e rollback
backup                  não apagar agora; arquivar depois preservando último
experimento             baixo risco, mas classificar antes de remover
logs                    consulta/read-only; nunca limpar sem política aprovada
sensível                não versionar, não expor, não colar em chat
```

---

## Próximos blocos recomendados para Fase 4

```text
Ordem   Bloco                         Motivo
------  ----------------------------- --------------------------------------------------
1       context/company.md             Alinhar visão geral antiga com MGS OS novo.
2       context/team.md                Atualizar equipe, gestores/códigos e agentes.
3       context/acquisition.md         Alinhar Ares, Facebook/Google, ChatPion, quiz/SMS.
4       context/monetization.md        Alinhar Smart Bidding, ActiveView, AdOps/AdX.
5       context/processes.md           Consolidar rotas operacionais revisadas.
6       context/sites.md               Revisar sites/verticais depois do modelo de áreas.
7       docs/CRONS.md                  Revisar inventário de crons sem alterar crontab.
9       profiles/ares-*                Revisar quando Ares avançar operacionalmente.
10      backups/                       Arquivar/limpar só após política aprovada.
```

---

## Gate para Fase 4

A Fase 4 só deve começar depois de Rodolfo aprovar este inventário como base de trabalho.

```text
Regra de migração
-----------------
1. Começar por arquivos context/*.md conceituais.
2. Depois docs operacionais.
3. Depois skills, se necessário.
4. Profiles de agentes só um por vez.
5. Scripts/runtime/data só com plano específico, backup, dry-run e validação.
6. Remoção/limpeza só depois de classificar e preservar rollback.
```
