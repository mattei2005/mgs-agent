# Entrada simples MGS e organização definitiva nos 30 TB

## Estado vigente e autoridade

**Implantado e ativo em 2026-11-02.** Resolver `data/ares/creative-ops/30tb-archive/flat-intake-binding.json` e `queue-config.json` para estado vivo; aprovação não substitui esses consumidores. Ativação: `flat-intake-1566814476626563115/activation.json`. O preflight bloqueado abaixo foi supersedido pela confirmação e pelo cutover validado, não permanece uma decisão pendente.

- Dono: Rodolfo Mattei, Discord `344196393512075265`, thread `1562078493498540042`.
- Redesenho confirmado em `1566814476626563115`, após proposta/pergunta `1566814035171868805` / `1566814036144685211`; evidência nativa em `authority.json`.
- Preservação/reaplicação dos mesmos acessos confirmada em `1566825959645253764`, em resposta a `1566816697044959233`; escopo congelado em `access-authority.json`.
- Permitido: mesmos usuários, leitura/edição equivalentes somente nos itens movidos e contêineres confinados; mesmos IDs, bytes e links; adaptar consumidores, intake e as duas skills Ares e espelhos já especificados.
- Proibido: exclusão/trash, novos usuários, membership/acesso geral aos 30 TB, ampliação para material não relacionado, credenciais/identidades alternativas, campanhas, budget, estratégia ou início. Regras de backup corporativo são outro escopo e não foram alteradas.

## Topologia e uso

- **Drive MGS** (`0AEwt4Ye690ocUk9PVA`): apenas `UPLOAD MANUAL` (`1ARBvLammWUHuAclNmcriwkkgeedKryBd`) na raiz ativa.
- **UPLOAD MANUAL**: arquivos enviados diretamente; sem pastas permanentes de operações/gestores. `_PROCESSAMENTO` (`1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`) é a única pasta técnica, interna e temporária; não é uma instrução para usuários separarem material ali.
- **30 TB / MGS-ARQUIVO** (`1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`): `CRIATIVOS`, organização permanente por operação/formato/gestor e `_MGS_CONTROLE`. As árvores de entrada antigas foram retidas como legado técnico controlado, não uma segunda entrada/pool.
- **30 TB / MGS-CORPORATIVO** (`16fP9b4bp3inB1Gze95znQLYq3rdtTEhp`): relatórios, referências e backups, com ACL por objeto; não herdar indiscriminadamente o acesso amplo dos criativos.

O pedido humano informa operação, gestor e destino; Ares registra a mensagem/autor/canal nativos e os IDs exatos via `scripts/ares_flat_intake.py register` (plano; depois `--apply`). O mesmo job `528c5710269d` consome o lote estável, sem writer paralelo. Upload sozinho não autoriza campanha. Fonte operacional Ares: `creative-operations-mgs/references/flat-upload-intake.md` e `direct-traffic-shein-operations`.

Tratamento conserva gates de IMG/VID, classificação factual, naming, sanitização, SHA/dedupe, inventário e reservas. Destino `common` organiza em `01_READY` sem liberar elegibilidade/reservas; `exclusive` entrega em `<NOME> - Exclusivos` depois do ACK. Somente uso de campanha comprovado passa a `<NOME> - Usados`; reupload exato preserva linhagem, reserva, uso e destino anteriores. Material sem contexto permanece intacto, não é atribuído ao gestor por adivinhação.

## Implementação e preservação

- `mgs_flat_layout.py`: manifesto congelado/CAS, permissões normalizadas por capacidade, ancestrais limitados, intents sem replay mutante ambíguo; PATCH/DELETE genérico do owner continua fechado.
- `mgs_flat_cutover.py`: 29 raízes e 247 objetos históricos relocados, incluindo 91 mídias com streams completos verificados antes/depois. Duas fontes pendentes foram normalizadas à entrada sem tratamento/classificação novos. `source-relocation-state.json` e snapshot/receipt publicados pelo controle SA preservam a prova e os mesmos IDs.
- Quatro itens permanentes da raiz (três Sheets / sete abas e um ZIP) movidos aos 30 TB com mesmos IDs/ACLs, fórmulas/valores/bytes e canário SA de escrita/leitura/restauração. Evidência `reports-state.json` e provas individuais.
- `mgs_flat_source_compat.py` valida snapshots/receipts nativos publicados por SA, associação exata de source ID e estado atual; consumidores históricos continuam lendo as fontes retidas sem reprocessar.
- `ares_archive_retirement.py` bloqueia DELETE no binding flat de preservação; `queue-config.json.delete_source=false`. Aprovações destrutivas antigas ficam como histórico, não são reaproveitadas neste modo.
- `mgs_flat_maintenance.py`: executado como subprocesso privado pelo monitor **existente**; arquiva gerações concluídas do staging por mesmo ID somente após conclusão/bytes/stock/ACK e encaminha relatórios permanentes que reapareçam na raiz. Limits técnicos: uma geração e até dois relatórios por ciclo; locks intake → queue, sem credencial owner no processo agente, sem novo cron e sem DELETE/trash.
- Prompt nativo do job e seis arquivos das duas skills/espelhos foram atualizados por rota autorizada; horário, modelo, delivery e demais settings do job preservados. Prova `ares-procedure-activation.json`.

## Validação e limite da aceitação

- Canário nativo não vazio: mesmo ID/bytes e mesmos 12 principais com capacidades equivalentes. A primeira diferença de herança em descendente foi retida como diagnóstico; propagação do Drive foi reconciliada antes de repetir a verificação, sem repetir movimento já realizado.
- Canário de entrada flat: mensagem humana nativa, plano sem writes de produção, arquivo técnico real, três polls em janela real de estabilidade, descoberta/contexto/claim local isolado e saída por mesmo ID. Zero linhagens/campanhas de produção criadas.
- Canário de manutenção: geração técnica e relatório na raiz encaminhados, bytes/ACL/ancestrais/receipts nativos validados, zero delete.
- 44/44 jobs históricos relacionados reconciliados com ACK/streams; nenhum bloqueio na aceitação. Testes focados e readbacks finais em `flat-intake-1566814476626563115/`.
- Primeiro novo pedido **real** após o cutover permanece observação operacional interna de Zeus/Ares, distinta de canário técnico. Não pedir a Rodolfo upload artificial nem declarar campanha validada por teste técnico.
- Readback da raiz fonte: `final-native-root-readback.json`. Na ativação havia 15 imagens sem contexto registrado, preservadas diretamente em UPLOAD MANUAL; não foram tratadas nem atribuídas implicitamente por esta autorização de organização. `_PROCESSAMENTO` estava vazio.

## Histórico supersedido do preflight

Antes da confirmação específica, foram auditados 268 objetos e identificados 263 descendentes cujo acesso de `geizianp@gmail.com` era herdado de UPLOAD MANUAL e inexistente no destino. Roles organizer/fileOrganizer do Shared Drive não têm os mesmos nomes no My Drive; a equivalência autorizada é de pessoas e capacidades de leitura/edição, não administração/propriedade idênticas. Os quatro relatórios também exigiam ACL por objeto. Nenhum move/write de permissão ocorreu naquele preflight; o bloqueio foi resolvido exclusivamente pela confirmação `1566825959645253764`, seguida dos canários e manifestos confinados acima. Fontes imutáveis: `whole-source-native-acl-snapshot.json`, `access-preservation-proposal.json` e diagnósticos em `flat-intake-1566814476626563115/`.
