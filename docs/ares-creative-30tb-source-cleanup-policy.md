# Política delimitada — limpeza das origens novas do arquivo 30 TB

Status atual: CONFIRMADA E ATIVA. Rodolfo determinou concluir o restante em `1562233890716786830`, após a explicação e solicitação explícita da exclusão definitiva, na thread `1562078493498540042`. Esta seção supersede o estado de proposta inativa; o texto original foi preservado no snapshot `retirement-1562233890716786830/cleanup-policy.original.md`. Autorização congelada: `data/ares/creative-ops/30tb-archive/retirement-authorization-1562233890716786830.json`.

Controlador: `scripts/ares_archive_retirement.py`, chamado pelo tick SA já existente, com `queue-config.json.delete_source=true` e hash da autorização fixado. O worker Google continua copy-only (`deleteSource:false` nos requests/ACKs/heartbeat); não foi alterado ou reimplantado. O intake Ares não executa exclusão: só o controlador SA dentro dos gates abaixo.

## Escopo aprovado

- Somente binários de novas linhagens recebidas após `queue-config.json.effective_after`, identificadas por IDs de arquivo congelados nos requests e verificadas no `archive-index.json` de produção.
- Origem fixa: Shared Drive `0AEwt4Ye690ocUk9PVA`, raiz de criativos `1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`; apenas os arquivos RAW/clean congelados em caminhos operacionais de mídia `OP/IMGouVID/99_LEGACY` e `OP/IMGouVID/01_READY` aprovados no request. Não aceitar substitutos por nome.
- Destino obrigatório: cópia privada com proprietário `mgsdigitalcorp@gmail.com`, sob `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`, com os nove acessos humanos já aprovados e SA canônica.
- Retenção aprovada: pelo menos 24 horas depois do ACK e da liberação completa do batch de intake; até dois pares RAW+clean por execução, serializados pelo lock canônico. A política cobre novos arquivos futuros apenas dentro desses mesmos gates, sem aprovação rotineira por arquivo.
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

Ativação real verificada em `retirement-activation-1562233890716786830.json`: controlador ativo, ciclo saudável e zero mappings/elegíveis. Nenhuma exclusão real foi executada, pois as provas existentes são técnicas e explicitamente inelegíveis. Não criar candidatos ou mappings fictícios, não apagar canários e não furar as 24h para demonstrar limpeza. Zeus monitora a primeira exclusão elegível e sua prova de destino/consumidores sem tarefa para Rodolfo.

O controlador congela a intenção na pasta técnica `RETIREMENTS`, valida o publisher nativo e usa ETag forte da API Drive v2 com `If-Match` no DELETE, mantendo a mesma SA canônica. A leitura/metadados/cópias normais continuam v3. Resposta aceita (HTTP 200/204) e ausência 404 são registradas literalmente, sem fabricar código de resposta. Timeout/ambiguidade/precondição rejeitada não são repetidos cegamente; preservam recibos/estado e bloqueiam a continuação para recuperação segura.

## Operação e limites de rollback

Não há aprovação rotineira por arquivo. Nova ampliação de escopo, redução da retenção, histórico ou remoção do arquivo Gmail exigem nova decisão. Para interromper novas exclusões, desativar somente o controlador; manter a leitura pelo arquivo para IDs físicos já aposentados. Não é possível restaurar o mesmo ID físico de uma origem definitivamente apagada. Cópias, atalhos, IDs lógicos e registros de negócio devem permanecer íntegros.
