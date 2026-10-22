# Recuperação do câmbio — alerta 1562630806940418121

Estado: recuperado e validado em 2026-10-22 UTC / noite de 21-10 Eastern.
Origem: https://discord.com/channels/1185714635991679006/1498132022634483894/1562630806940418121
Job: `685397627b29`.
Autoridade: pedido de recuperação segura do monitor; migração integral `1562459803186626571` e confirmação do movimento das três Sheets `1562626527206838275`.

## Problema, causa e correção

O coletor interrompeu com `drive_preflight_failed_quotes_200`: o Drive retornava HTTP 200 e a Sheet não estava na lixeira, mas o código exigia o driveId anterior `0AEwt4Ye690ocUk9PVA`. A mesma Sheet `1Zk-b8OoaDHrvFtuerf5IuO2jx-phVWXMYi79yqVTZX4` havia sido movida por Rodolfo para o parent corporativo `16fP9b4bp3inB1Gze95znQLYq3rdtTEhp`, sem driveId, sob owner nativo `03783617840924670288` / `mgsdigitalcorp@gmail.com`. A API confirmou canEdit e a permissão writer da SA canônica `07414359829876449782`. Sheets API HTTP 200. Audit/checkpoint e `docs/mgs-whole-drive-30tb-migration.md` reconciliam o movimento como autorizado, não anomalia.

Mudança limitada a `apps/finance-system/sync-quotes.py` e `tests/test_quote_source.py`: aceitar a localização corporativa somente para esse mesmo SID, parent, owner nativo/email e permissão SA writer exatos, com canEdit=true. Arquivo na lixeira, destino diferente ou identidade divergente continuam bloqueados. Mantida a rota histórica Shared Drive já existente; não introduzido fallback genérico My Drive, credencial pessoal ou alteração de ACL. A configuração, fonte/células/fórmulas, spread e lifecycle de taxas fixas não mudaram. O worker manual importa o mesmo coletor, cobrindo ambos os caminhos sem implementação paralela.

## Checks executados

- Coleta real pelo candidato com SA canônica: três fórmulas GOOGLEFINANCE exatas, números finitos positivos e zero escrita Google.
- Regressão RED reproduziu o mesmo erro HTTP200 no destino corporativo; GREEN passou 17 testes específicos. Casos negativos cobrem parent, owner ID/email, acesso/ID SA, arquivo, lixeira, canEdit, outra unidade e outra Sheet.
- Gate completo Node: 279/279, zero skips/falhas.
- Gate completo Python: 242 testes, OK, zero skips. Primeiro transporte foreground encerrou aos 420s; repetição completa silenciosa finalizou em 698,34246s, exit0. Nenhum teste foi ignorado. Preparação inicial excedeu o limite de96MiB e foi refeita antes de criar o candidato: fixtures históricas foram copiadas em suplemento fechado/hashes sob admissão compartilhada, conforme contrato canônico; nenhuma ampliação do limite.
- `finance_release.py check/publish`: release `quotes-location-1562630806940418121` committed, cutover3,952s, backups exatos e readback dos dois arquivos. Somente worker financeiro auxiliar recarregado; aplicação financeira, PostgreSQL e gateways não reiniciados.
- Execução agendada já adquiriu o lock após o cutover e publicou a fonte às `2026-10-22T01:26:59.835339+00:00`. Primeira chamada manual respeitou esse lock; não forçou segundo writer. Setembro chegou à revisão1656 e outubro860; agosto565 preservado.
- Wrapper canônico `mgs-finance-quotes.py --now` executado novamente após liberar o lock: nova coleta publicada às `2026-10-22T01:28:05.146949+00:00`, changed=false, comprovando retry sem reaplicar fatos.
- Estado final: ok=true, consecutive_failures=0; alerta reported=0/open=false. JSON remoto live-quotes relido e timestamp idêntico ao estado local.
- Comparação dos snapshots que delimitam o retry: entradas nominais/additions, overrides não cambiais, ledger, histórico e1.006 taxas fixas (incluindo overrides efetivos) iguais. O snapshot pré-retry foi capturado enquanto a execução agendada já atualizava as cotações provisórias; essa comparação não é apresentada como baseline integral anterior à publicação do código. Revisões/resultados autoFX mudaram legitimamente somente pelo fluxo já autorizado.
- Serviço financeiro, socket e PostgreSQL remotos ativos; login por socket200 validado pelo controlador.
- Worker auxiliar estava parado após cinco erros de transporte, o último TimeoutExpired. A recarga exigida pelo protocolo recuperou o consumidor: ciclo real `2026-10-22T01:28:32.791965+00:00`, ok=true, pending=0, notificações delivered=0. Não foi atribuída causa interna não observável aos erros antigos.

## Evidência e rollback

Evidência protegida: `apps/finance-system/private/quotes-location-1562630806940418121/` — preparação/suplemento, real-source-stage, gates, manifest, check/publish, snapshots runtime-before/after, recovery-verification e lookup-worker-readback.
Backups/journal: `apps/finance-system/private/releases/quotes-location-1562630806940418121/` (`000.before`, `001.before`). Rollback deve usar o protocolo de release e validar hashes; não executar `recover` para desfazer uma release já committed.

Documentação canônica recebeu supersessão explícita da localização em `docs/finance-system-product-direction.md`. Inventário/audit/checkpoint vinculam este relatório. REPORT-INFRA deve usar exclusivamente o helper canônico, com readback da mensagem, sem cópia operacional direta. Nenhum cron, credencial, permissão, cobrança, fórmula Google, dado financeiro nominal ou arquivo foi excluído/alterado fora do fluxo cambial aprovado. Candidato/logs/backups permanecem preservados; nenhuma retenção destrutiva foi executada.
