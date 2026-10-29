# Contagem diária de campanhas SHEIN — produto independente

Use para contar campanhas novas por gestor/site, não para performance ou receita. Fonte ativa: `/root/mgs-agent/data/ares/meta-ads/policies/shein-campaign-creation-daily.json`; executor `/root/.hermes/profiles/ares/scripts/shein-campaign-creation-daily.py`; wrapper `shein-campaign-creation-cron.py`.

- Resolva os 36 vínculos pelo catálogo SHEIN canônico e valide seis sites × seis gestores, unicidade e scopes de domínio/conta antes da Meta. Leia a identidade e BM live de cada conta; não amplie por capacidade do token.
- Conte IDs únicos por `created_time` convertido para Eastern, não por data no nome ou início da veiculação. Inclua clones/duplicações e estados aceitos. O edge rejeita `DELETED` como filtro; use os estados aprovados do contrato, sem prometer os objetos não expostos pela API.
- Separe gestor responsável pela conta da pessoa que executou a criação. Autor desconhecido não deve ser inventado a partir de ownership.
- Preserve snapshot/corte e cursores por conta para retomar somente o restante. Dados ausentes são `n/d`, nunca zero. Reconcilie totais de gestores, sites e IDs únicos.
- Este produto usa o dia corrente até o corte fixo de 18h08 Eastern, não fechamento de 24 horas. Inclui Yolo e Mavroa: exclusões dos relatórios financeiros D-1/Intraday não se aplicam automaticamente.
- Publique na thread registrada via bot Ares com outbox/nonce e GET exato. Não usar renderer financeiro, anexos, nova thread ou footer de scheduler; não alterar Meta nem D-1/Intraday.
- Antes de mexer na agenda, inventariar oito datas globais, excluir só o próprio job no pós-write e manter lock/deadline/quotas. O root cron é determinístico, sem LLM; não criar cópia no cron Hermes.

Validação: `python3 /root/mgs-agent/tests/test_ares_shein_creation_daily.py`; coleta sem postagem: `python3 /root/.hermes/profiles/ares/scripts/shein-campaign-creation-cron.py --validate-live`. `--scheduled` protege horário e deduplica publicação diária. `--publish-test` publica uma prévia real na thread e exige intenção de envio.
