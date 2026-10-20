# Proposta delimitada — limpeza das origens novas do arquivo 30 TB

Status: PROPOSTA INATIVA. Não há autorização destrutiva adicional nem executor de exclusão habilitado. `queue-config.json.delete_source=false` continua obrigatório até confirmação específica de Rodolfo, implementação e validação independente do controlador de aposentadoria. Esta proposta não modifica o worker Google copy-only.

## Escopo proposto para a confirmação

- Somente binários de novas linhagens recebidas após `queue-config.json.effective_after`, identificadas por IDs de arquivo congelados nos requests e verificadas no `archive-index.json` de produção.
- Origem fixa: Shared Drive `0AEwt4Ye690ocUk9PVA`, raiz de criativos `1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`; apenas os arquivos RAW/clean congelados em caminhos operacionais de mídia `OP/IMGouVID/99_LEGACY` e `OP/IMGouVID/01_READY` aprovados no request. Não aceitar substitutos por nome.
- Destino obrigatório: cópia privada com proprietário `mgsdigitalcorp@gmail.com`, sob `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`, com os nove acessos humanos já aprovados e SA canônica.
- Retenção proposta: pelo menos 24 horas depois do ACK e da liberação completa do batch de intake; até dois pares RAW+clean por execução, serializados pelo lock canônico. A política cobre novos arquivos futuros apenas dentro desses mesmos gates, sem aprovação rotineira por arquivo.
- Ação proposta é exclusão DEFINITIVA dos binários de staging selecionados, não apenas mover para a lixeira. O arquivo Gmail, os atalhos de estoque e as evidências permanecem. Exclusão na origem é irreversível: o ID Google físico antigo não pode ser recriado; o ID lógico de negócio é preservado pelo catálogo.

## Gates antes de cada arquivo — todos obrigatórios

1. Confirmar autoridade adicional rastreável de Rodolfo e política ativa exata; sem confirmação, plano somente leitura.
2. Validar request imutável, publisher canônico, receipt proprietário, ACK da SA, par completo RAW+clean, dono, parent/path e SHA-256/MD5/tamanho dos streams de origem e cópia.
3. Readback recente de acesso humano privado e SA; nenhum `anyone` ou domínio público. Não ampliar permissões para passar o gate.
4. Validar catálogo de produção e atalho real por ID/alvo/parent; canários, fixtures e jobs `validationOnly` nunca são elegíveis.
5. Confirmar batch de intake completo, ausência de writer/lease ativo e preservação dos fingerprints de linhagem/reserva/IDs. Checar consumidores, links e referências ao ID físico antigo; referência não mediada pelo catálogo bloqueia aquela origem.
6. Testar leitura pelo arquivo e mudança reversível do estado do atalho, sem mover os bytes Gmail. Manter os IDs de campanhas, performance, reservas e elegibilidade intactos.
7. Antes de implementar apply: tornar reconciliação/cache/alias repair explicitamente conscientes do recibo de aposentadoria. Um 404 não comprovado deve continuar sendo erro; nunca tratar origem ausente como exclusão autorizada sem receipt exato e leitura íntegra da cópia.
8. Congelar manifesto do lote por IDs, metadados, hashes e alvo proprietário; registrar intenção exclusiva antes do DELETE; reconciliar resposta ambígua lendo o mesmo ID, sem repetir cegamente.
9. Após DELETE, verificar ausência real da origem, permanência e hash da cópia e funcionamento do consumidor/estoque; registrar receipt de aposentadoria e auditar a redução de bytes. Falha parcial bloqueia o lote e preserva o restante.

## Exclusões absolutas desta proposta

Acervo histórico, linhagens históricas reaproveitadas, fontes duplicadas sem mapping próprio, todos os canários/fixtures, pastas, atalhos, requests/receipts/ACKs, Sheets, Apps Script, credenciais, mídias sem prova completa, arquivos fora dos roots/caminhos aprovados e qualquer campanha/budget/Meta. Não esvaziar lixeira global nem executar limpeza genérica.

## Estado observado na preparação

Não há mappings operacionais de produção no cutover; as provas completas existentes são técnicas e explicitamente inelegíveis. O manifesto corrente deve permanecer vazio. Não criar candidatos ou mappings fictícios para testar exclusão.

## Decisão solicitável

Confirmar separadamente a implementação e ativação dessa exclusão definitiva automática somente para novas linhagens futuras elegíveis, com retenção de 24 horas, limite de dois pares por execução, cópias Gmail e atalhos preservados e histórico excluído. Antes dessa resposta não executar DELETE, não habilitar `delete_source` e não declarar que o staging já libera espaço automaticamente.
