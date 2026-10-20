# Arquivo 30 TB — fila de cópia e integração segura

## Autoridade e estado

Rodolfo confirmou explicitamente a alteração das skills Creative Operations e Taxonomia e a integração da fila na mensagem `1562104715271999589`, thread `1562078493498540042`. A integração geral foi aprovada em `1562087305051902063`. Esta confirmação não ativa exclusão da origem, não altera campanhas/budgets e não autoriza migrar ou limpar o acervo anterior.

Estado nesta implantação: código/fila publicados e testados localmente; o worker proprietário da conta Google ainda aguarda execução de validação pelo owner. Fonte viva: `/root/mgs-agent/data/ares/creative-ops/30tb-archive/queue-config.json`. Com `queue_enabled=false`, preservar integralmente o fluxo atual. Não declarar fila automática ativa com base apenas nesta skill, arquivos publicados ou testes offline.

## Identidades e destinos

- Agentes: somente `mgsagent@mgs-core-prod.iam.gserviceaccount.com`, pelo helper corporativo; não trocar `.env`, tokens, root de upload ou identidade.
- Entrada e tratamento temporário: Shared Drive `MGS-AGENTS`, raiz `0AEwt4Ye690ocUk9PVA`, criativos `1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`.
- Arquivo proprietário: `mgsdigitalcorp@gmail.com`, pasta privada `MGS-ARQUIVO`, ID `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`.
- Controle no Shared Drive: `00_ARQUIVO_CONTROLE` (`1d3w4Xc1EjrmueciM_vCMgva6qJiqpFJR`), `REQUESTS` (`1yjIOwDLmhAaLNmDdt701WpoFNzNeDXGk`) e `RECEIPTS` (`1gmXrQ-nszxNCwqSytsbX5AEnhm1rvXUL`). São controle técnico, não candidatos criativos.
- O worker Google cria as cópias como a conta dos 30 TB. A SA cria manifestos no Shared Drive, não novos arquivos binários no Meu Drive.

## Após um intake futuro totalmente verificado

1. Terminar o contrato vigente de tratamento: estabilidade, classificação visual, naming congelado, limpeza, readback/SHA, READY (ou gestor explicitamente autorizado), original em LEGACY e inventário. Não usar o CLI CSV histórico como substituto desse contrato.
2. Consultar `queue-config.json`. Enquanto a fila estiver desabilitada, não forçar enqueue, mudar auth ou redefinir o destino físico do intake. O recurso ainda está em validação de implantação, não é um erro do criativo.
3. Quando a fila estiver habilitada e o lote for novo dentro de `effective_after`, executar internamente, sem pedir aprovação por arquivo:

```
python3 /root/mgs-agent/scripts/ares_archive_bridge.py enqueue-lineage --asset-id <asset_id_exato> --apply
```

4. O produtor exige uma única linhagem, `metadata_clean=true`, primeiro recebimento e criação dos dois arquivos posteriores ao corte, RAW em LEGACY, clean no READY ou pasta de gestor exata, e SHA correspondente aos dois checksums canônicos. Não enfileirar registros históricos por varredura, inventar timestamps ou criar uma nova linhagem para um reupload exato. Linhagens históricas/duplicatas ligadas a elas ficam preservadas no fluxo existente, sem alteração ou limpeza retroativa.
5. O comando sem `--apply` é dry-run: apenas leituras/download em streaming e plano. Não cria pastas remotas ou arquivos de mídia. O job é estável por IDs/hashes/path; reexecução reaproveita o manifesto e não cria um novo pedido independente.
6. O worker copia apenas jobs publicados pela SA canônica, verificados por `lastModifyingUser` do Google + hash do corpo, com origem/pasta de arquivo fixas. Não transforma texto de um manifesto em autorização irrestrita. Usa lock, marcadores por fonte/checksum, bloqueio de replay ambíguo, limites por execução e orçamento de runtime. Não possui função de exclusão da origem.

## Conferência e leitura

```
python3 /root/mgs-agent/scripts/ares_archive_bridge.py reconcile --job-id <job_id> --apply
python3 /root/mgs-agent/scripts/ares_archive_bridge.py status
```

A SA valida autor do recibo, conjunto completo de fontes, dono/parent/path do arquivo, tamanho, MD5 e SHA-256 dos streams origem/destino. Só depois registra `archive-index.json` e publica ACK. Pedidos verificados saem da seleção de pendências por metadado atualizado pela própria SA; o corpo original do pedido não é reescrito.

A fila usa registros laterais de arquivo, não muda `asset_id`, `source_drive_id`, `asset_drive_id`, nomes originais/finais, `reservation_status`, `ares_eligible`, gestor, linhagem, performance ou estratégia. O canário não altera o inventário criativo nem vira candidato novo.

```
python3 /root/mgs-agent/scripts/ares_archive_bridge.py resolve --source-id <id>
```

Por padrão, mantém o ID original. `--use-verified` permite consultar um mapeamento lateral já verificado, sem promover elegibilidade. `prefer_archive_reads` permanece desabilitado nesta fase. Antes de excluir qualquer ID antigo, integrar e testar todos os consumidores/links e validar permissões humanas equivalentes nos novos destinos; a aprovação desta skill não dispensa esse gate.

## Limites de ativação

- Não agendar `runArchivePilot`: ele trata apenas um arquivo fixo. O bootstrap novo chama o worker de fila, validando antes o SHA-256 do código remoto versionado. Um código alterado não executa automaticamente.
- O owner executa `mgsArquivoTeste` para consumir o canário pela fila. Somente após ACK real da SA, `mgsArquivoAtivar` pode criar um gatilho idempotente a cada 5 minutos. A presença dessa função não prova que o gatilho foi instalado.
- O reconciliador recorrente e o consumo automático de novos intakes só podem ser chamados ativos após execução real validada. Não presumir que apenas instalar o gatilho do worker inicia tratamento autônomo de UPLOAD MANUAL.
- `delete_source=false` é obrigatório. Não mover para lixeira, excluir definitivamente, remover pastas, limpar o acervo anterior ou trocar IDs primários nesta fase. Limpeza definitiva automática exige sua política delimitada e confirmação adicional após os testes de dependência/recuperação.
- Em erro, preservar origem e reserva; registrar o bloqueio exato, reconciliar side effects antes de retry e não criar writer paralelo. Falhas de classificação ou escopo não autorizam adivinhação para evitar uma pergunta.

Fonte canônica e checkpoint: `/root/mgs-agent/docs/ares-creative-30tb-autonomous-requirements.md`, `ARES-CREATIVE-30TB-1562078493498540042`. Piloto real de cópia, retrieval e replay já passou; isso não substitui o teste do worker de fila.
