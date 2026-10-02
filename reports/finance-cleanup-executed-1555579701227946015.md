# Limpeza financeira executada e validada

Autoridade: Rodolfo `1555579701227946015`; diagnóstico e escopo na thread `1555572634228490283`. Manifesto confirmado SHA-256 `c9056f83c9571ad5e9f741093e8588d9cd501881fac56c24fe5ef1f86bf19993`.

## Resultado

- Exatamente 28 árvores inativas `candidate/stage` removidas, contendo 196.416 arquivos; todos os alvos estão ausentes por readback.
- Recuperação inode-aware estimada: 52.963.414.016 bytes. Ganho efetivo de espaço livre medido: 52.911.996.928 bytes (52,91 GB decimais).
- Antes: 35.488.223.232 bytes disponíveis, 82,85% de uso. Depois da operação: 88.400.220.160 bytes disponíveis, 57,27% de uso.
- Nenhum alvo adicional foi removido. O candidato ativo `persistent-session-1555570216912560151/candidate` permaneceu intacto e fora do manifesto.

## Integridade financeira e operacional

- Banco PostgreSQL produtivo, serviço da dash e socket permaneceram ativos, com os mesmos PIDs e WorkingDirectory.
- Controles remotos permaneceram idênticos: 344 cenários, revisão máxima 961, 215 locked, 40 históricos e 28 lançamentos no ledger.
- Zero escrita financeira durante a limpeza.
- Readback autenticado posterior: health produtivo aprovado; dashboard de outubro carregou em 1440px e 390px na revisão 91, sem erro JavaScript e sem POST financeiro.
- Zero unidades systemd locais falhadas.

## Preservação

- Relatórios financeiros, evidências nos diretórios-pai e journals/backups de release separados permaneceram presentes.
- O candidato financeiro em execução foi excluído do escopo.
- Fontes, regras, automações, perfis Hermes, banco de produção, credenciais e configurações não foram alterados.

## Evidência

- Manifesto: `work/finance-cleanup-audit-1555576722907201710/deletion-manifest.json`.
- Executor: `work/finance-cleanup-audit-1555576722907201710/execute-confirmed.py`.
- Resultado, journal e smoke: `work/finance-cleanup-audit-1555576722907201710/`.
- Audit log: eventos `finance_cleanup_delete_started` e `finance_cleanup_delete_completed` em `logs/events-audit.jsonl`.

A remoção tratou resíduos históricos; a prevenção de nova recorrência exige corrigir os produtores/retention dos testes em escopo separado.