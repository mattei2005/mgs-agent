# MGS Router — histórico de cliques Keitaro

## Autoridade e supersessão

Rodolfo pediu recuperar/preencher o histórico na mensagem `1556908028450836511`, thread `1555381168894115912`. Esta fonte sucede apenas a ausência de histórico/importação em `docs/mgs-router-campaign-clicks-equal-distribution.md`; preserva divisão igual, navegação, calendário US Eastern, hosting/contas e todas as funcionalidades anteriores. Não autoriza tracking de visitantes, conversões, postbacks, mutações no Keitaro ou reimportação de campanhas aposentadas.

## Resultado ativo

- `data/mgs-router-keitaro-click-history-validation-1556908028450836511.json`: `complete_verified`.
- Fonte autenticada: `https://mattei-keitaro.xyz`, endpoint interno `reports.build`, agrupamento `day,campaign_id`, métrica `clicks`, timezone `America/New_York`. Snapshot fechado até `2026-10-06 01:37:48`, antes da coleta nativa Router. Nenhum IP, cookie, referrer, query de visitante, log individual ou segredo foi exportado.
- 31 páginas reconciliadas:30.678 pares únicos dia/campanha, soma2.623.191 igual ao summary da origem. Disponibilidade efetiva da origem:22/01/2026–04/10/2026.
- Todas as445 campanhas atuais correspondem por host+alias a um único ID Keitaro.444 têm histórico;1 não tem eventos disponíveis. Não inventar eventos para esta campanha.
- Importados **2.575.829 cliques**, **27.433 registros diários**, das444 campanhas com histórico.47.362 cliques de3.245 pares referentes a campanhas fora da lista atual não foram adicionados; nenhuma rota aposentada foi recriada.
- Fonte sanitizada persistente: `data/mgs-router-keitaro-click-history-source-1556908028450836511.json`, SHA-256 `7454cddc53ade123008a0cc326960064bc7b488156d2dabc159cbcf50cad132d`.
- Os10 cliques nativos observados na validação final foram preservados; total combinado observado2.575.839. Esse total pode crescer normalmente e não é um snapshot permanente do painel.

## Importação e integridade

`scripts/mgs-router-keitaro-history-import.py` prepara tabela TEMP em memória antes de tomar lock do writer; a transação única adiciona históricos aos totais, grava `click_imports` com ID/hash/total/rows/proveniência e metadado `history_keitaro`. Fonte não pode mudar num replay, e uma importação anterior diferente ou históricos preexistentes bloqueiam duplicação. Histórico diário está inteiramente antes do dia nativo no fuso Eastern; não misturar dias de sobreposição sem nova reconciliação granular.

O ID `keitaro-history-1556908028450836511` permanece estável. Segunda execução real retornou `already_applied`, sem adicionar novamente. Importação manteve `since=2026-10-06T05:37:49Z` para a coleta Router, sem fingir que o Router coletou os eventos passados.

API `/api/clicks` fornece `history` com origem, datas e totais; painel informa o período Keitaro importado e o início Router separadamente. Filtros de datas aplicam-se aos registros diários reais. A tabela continua mostrando total de cliques, não visitantes únicos/humanos.

Backup online SQLite antes/probe/depois e binário anterior ficam somente em `/root/.local/share/mgs-router-rollbacks/1556908028450836511/`. Probe validou exatidão, preservação nativa e idempotência dentro do orçamento de lock200ms; backup integrity_check=ok. Não restaurar o banco inteiro por cima de novos cliques. Falha após COMMIT deve reconciliar metadado/ledger antes de qualquer retry ou rollback.

Executor `scripts/mgs-router-keitaro-history-deploy.py` é single-use, vinculado ao pedido e aos hashes da fonte/candidato. Não replayar mudando sua aprovação/receipt. Coleta nativa continua somando; manutenção no Keitaro permanece somente leitura.

## Validação

87 testes Go, race/vet/JS/build e4 testes Python. Dois testes novos observaram RED antes da implementação de metadados. Ambas as contas reais compararam os444 totais completos, primeiro dia e setembro com a fonte, calendário/UI/sort/mobile, sem POSTs/configuração. Restart real preservou histórico e início nativo.890 HEADs das445 rotas com/sem parâmetros passaram; zero GETs técnicos de tráfego nesta entrega. Arquivos de rotas/domínios/usuários/cache, unidade e redes Cloudflare conservaram hashes; PIDs Zeus/Atena/Ares preservados. Login Keitaro usou o fluxo protegido; relay temporário criptografado removido e restantezero.

## Limite

O primeiro dia disponível é22/01/2026 e o último é04/10/2026. Não há comprovação/recuperação de dias anteriores, dados removidos ou visitas que passaram pelo Router antes da ativação de sua contagem e não chegaram ao Keitaro. Não preencher lacunas com estimativas. Para visualizar o histórico, usar **Todo o período** ou De/Até; **Hoje** mostra somente o dia atual.
