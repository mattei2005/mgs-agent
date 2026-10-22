# Política delimitada — limpeza das origens novas do arquivo 30 TB

Status atual: CONFIRMADA E ATIVA com retenção de **0 segundos após todas as validações**, pela confirmação adicional `1562848227944955935` (Rodolfo respondeu “sim” à troca24h→retirada imediata). Autorização vigente: `data/ares/creative-ops/30tb-archive/retirement-authorization-1562848227944955935.json`, fixada em queue-config por ID/hash. Esta decisão supersede SOMENTE a espera24h da autorização `1562233890716786830`; original preservado e ainda interpretável para recibos antigos/rollback. Mantêm-se o limite de dois pares por ciclo e TODOS os gates abaixo. O código de retirada histórica não foi ativado por atalho: precisa de cópia/consumidores próprios comprovados, sem fabricar liberação de intake.

Histórico de autoridade: Rodolfo confirmou a primeira política de24h em `1562233890716786830`, após a pergunta explícita na thread `1562078493498540042`; baseline preservado no snapshot `retirement-1562233890716786830/cleanup-policy.original.md`. Rollback da mudança0s e fontes/config anteriores em `/root/.hermes/profiles/zeus/artifacts/immediate-retention-1562848227944955935/`.

Controlador: `scripts/ares_archive_retirement.py`, chamado pelo tick SA já existente, com `queue-config.json.delete_source=true` e hash da autorização fixado. O worker Google continua copy-only (`deleteSource:false` nos requests/ACKs/heartbeat); não foi alterado ou reimplantado. O intake Ares não executa exclusão: só o controlador SA dentro dos gates abaixo.

## Escopo aprovado

- Somente binários de novas linhagens recebidas após `queue-config.json.effective_after`, identificadas por IDs de arquivo congelados nos requests e verificadas no `archive-index.json` de produção.
- Origem fixa: Shared Drive `0AEwt4Ye690ocUk9PVA`, raiz de criativos `1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`; apenas os arquivos RAW/clean congelados em caminhos operacionais de mídia `OP/IMGouVID/99_LEGACY` e `OP/IMGouVID/01_READY` aprovados no request. Não aceitar substitutos por nome.
- Destino obrigatório: cópia privada com proprietário `mgsdigitalcorp@gmail.com`, sob `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`, com os nove acessos humanos já aprovados e SA canônica.
- Retenção vigente: **nenhuma espera artificial após o ACK e a liberação comprovada do batch de intake** (0s, confirmação adicional `1562848227944955935`). A regra anterior24h foi supersedida, não os demais gates. Até dois pares RAW+clean por execução, serializados pelo lock canônico; novos arquivos futuros dentro desses mesmos gates não exigem aprovação por arquivo.
- Ação proposta é exclusão DEFINITIVA dos binários de staging selecionados, não apenas mover para a lixeira. O arquivo Gmail, os atalhos de estoque e as evidências permanecem. Exclusão na origem é irreversível: o ID Google físico antigo não pode ser recriado; o ID lógico de negócio é preservado pelo catálogo.

## Gates antes de cada arquivo — todos obrigatórios

1. Confirmar autoridade adicional rastreável de Rodolfo e política ativa exata; sem confirmação, plano somente leitura.
2. Validar request imutável, publisher canônico, receipt proprietário, ACK da SA, par completo RAW+clean, dono, parent/path e SHA-256/MD5/tamanho dos streams de origem e cópia.
3. Readback recente de acesso humano privado e SA; nenhum `anyone` ou domínio público. Não ampliar permissões para passar o gate.
4. Validar catálogo de produção e atalho real por ID/alvo/parent; canários, fixtures e jobs `validationOnly` nunca são elegíveis.
5. Confirmar batch de intake completo, ausência de writer/lease ativo e preservação dos fingerprints de linhagem/reserva/IDs. Checar consumidores, links e referências ao ID físico antigo; referência não mediada pelo catálogo bloqueia aquela origem.
6. Testar leitura pelo arquivo e mudança reversível do estado do atalho, sem mover os bytes Gmail. Manter os IDs de campanhas, performance, reservas e elegibilidade intactos.
7. Reconciliação/cache/alias repair usam recibo nativo de aposentadoria da SA. Um 404 não comprovado continua sendo erro; nunca tratar origem ausente como exclusão autorizada sem receipt exato e leitura íntegra da cópia. Desativar futuras exclusões não pode redirecionar IDs lógicos já aposentados à origem ausente.
8. Congelar manifesto do lote por IDs, metadados, hashes e alvo proprietário; registrar intenção exclusiva antes do DELETE; reconciliar resposta ambígua lendo o mesmo ID, sem repetir cegamente.
9. Após DELETE, verificar ausência real da origem, permanência e hash da cópia e funcionamento do consumidor/estoque; registrar receipt de aposentadoria e auditar a redução de bytes. Falha parcial bloqueia o lote e preserva o restante.

## Exclusões absolutas desta proposta

Acervo histórico, linhagens históricas reaproveitadas, fontes duplicadas sem mapping próprio, todos os canários/fixtures, pastas, atalhos, requests/receipts/ACKs, Sheets, Apps Script, credenciais, mídias sem prova completa, arquivos fora dos roots/caminhos aprovados e qualquer campanha/budget/Meta. Não esvaziar lixeira global nem executar limpeza genérica.

## Execução e prova

**Readback da mudança0s:** `ares_archive_retention_policy.py activate` retornouactive e o replayalready_active; `verify` e o configloader real confirmaramretention_seconds0/autorização1562848227944955935. Ciclo real somenteleitura do controlador:13pares examinados, zeroelegíveis/zeroDELETE, esperando liberação comprovada do intake, sem remover esse gate. Prova `immediate-retention-validation-1562848227944955935.json`. Não equivale à primeira exclusão de produção e não declara migração integral concluída. O ownerworker permanece no mesmo ID/hash/cadência, sem novo consentimento ou Run.

**Histórico da ativação inicial24h:**
Ativação real verificada em `retirement-activation-1562233890716786830.json`: controlador ativo, ciclo saudável e zero mappings/elegíveis. Nenhuma exclusão real foi executada, pois as provas existentes são técnicas e explicitamente inelegíveis. Não criar candidatos ou mappings fictícios, não apagar canários e não furar os gates para demonstrar limpeza; a espera24h deixou de existir SOMENTE após a confirmação0s acima. Zeus monitora a primeira exclusão elegível e sua prova de destino/consumidores sem tarefa para Rodolfo.

O controlador congela a intenção na pasta técnica `RETIREMENTS`, valida o publisher nativo e usa ETag forte da API Drive v2 com `If-Match` no DELETE, mantendo a mesma SA canônica. A leitura/metadados/cópias normais continuam v3. Resposta aceita (HTTP 200/204) e ausência 404 são registradas literalmente, sem fabricar código de resposta. Timeout/ambiguidade/precondição rejeitada não são repetidos cegamente; preservam recibos/estado e bloqueiam a continuação para recuperação segura.

## Operação e limites de rollback

Não há aprovação rotineira por arquivo. Nova ampliação de escopo, redução da retenção, histórico ou remoção do arquivo Gmail exigem nova decisão. Para interromper novas exclusões, desativar somente o controlador; manter a leitura pelo arquivo para IDs físicos já aposentados. Não é possível restaurar o mesmo ID físico de uma origem definitivamente apagada. Cópias, atalhos, IDs lógicos e registros de negócio devem permanecer íntegros.
