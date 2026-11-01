# Padrão aprovado de armazenamento criativo por gestor

## Autoridade e estado

- Dono: Rodolfo Mattei (`344196393512075265`).
- Thread: `1562078493498540042`.
- Aprovação nova: `1566496381001146440`, em resposta ao padrão explicado em `1566496283479252993` e `1566495685820424293`.
- Requisitos de origem: `1566493713373462549`.
- Confirmação adicional do conjunto, incluindo as duas skills Ares e seus espelhos: `1566497527719661640`, após delimitação em `1566497081265365043` (REPORT-INFRA) e explicação na thread. Isto supersede a pendência de autorização do desenho inicial, sem autorizar exclusões, ACL, credenciais ou campanhas.
- Estado de execução: **binding ativo e aceitação técnica verificada**; 228 combinações operação/formato/gestor e 456 destinos Exclusivos/Usados relidos por SA, cobrindo 19 operações, IMG/VID e seis gestores. Código e duas skills Ares foram atualizados, com três arquivos live/mirror iguais. O estado produtivo verificável é `data/ares/creative-ops/manager-storage-standard.json#/phase`, não apenas este texto. Não confundir canário técnico com o primeiro pedido real de campanha.

## Escopo funcional aprovado

Aplicar o mesmo padrão a todos os gestores registrados da operação correspondente, não apenas Nicolas. Resolver a lista vigente em `scripts/ares_upload_context_layout.py` e `data/ares/creative-ops/30tb-archive/upload-context-layout.json`; não inferir novos gestores, operações ou permissões. No preflight foram identificados Ícaro, Geizian, Isliago, Joe, Kelly e Nicolas.

Entrada permanece o mesmo `UPLOAD MANUAL` no Drive MGS (`1ARBvLammWUHuAclNmcriwkkgeedKryBd`); agentes continuam exclusivamente com a Service Account canônica. O executor owner de 30 TB permanece isolado e aprovado, sem fallback de autenticação dos agentes.

Destino de trabalho: `MGS-ARQUIVO/CRIATIVOS/<OPERACAO>/<IMG|VID>/`:

- `01_READY`: estoque comum, tecnicamente tratado e disponível para distribuição, respeitando o inventário de elegibilidade.
- `<NOME> - Exclusivos`: reservado ao gestor, ainda sem utilização confirmada. Não disponibilizar automaticamente no pool comum.
- `<NOME> - Usados`: peças com utilização confirmada nas campanhas do gestor. O nome da pasta, isoladamente, não é prova suficiente para inventar uso Meta ou preencher IDs de campanha.

Manter originais e histórico fora do pool disponível, com linhagem e hashes preservados. Não presumir que todo conteúdo de `99_LEGACY` seja exclusivamente original.

## Dois fluxos

1. Kelly envia arquivos na entrada MGS e avisa o Ares: tratar, arquivar original e tratado nos 30 TB, separar operação e formato e disponibilizar o tratado em `01_READY`, salvo destinação específica expressa. O nome do remetente não deve, sozinho, substituir a intenção do pedido.
2. Gestor envia na mesma entrada e solicita entrega própria, podendo também pedir campanhas no mesmo pedido: Ares trata, arquiva e entrega em `<NOME> - Exclusivos`, sem exposição ao estoque comum; executa campanhas somente pela autoridade e pedido válidos da origem. Após readback do uso real, somente os membros utilizados passam para `<NOME> - Usados`. Falha, bloqueio e saldo não utilizado permanecem exclusivos, com o mesmo request e reserva.

Essa organização não autoriza criar campanhas agora, alterar budgets/estratégias/início, reutilizar material usado entre gestores, trocar credenciais, ACL, excluir arquivos ou reprocessar criativos já entregues.

## Preflight confirmado e bloqueio de implantação

As fontes atuais ainda exigem outra topologia e outra semântica:

- `scripts/ares_manager_delivery.py::exact_folder` exige pasta homônima do gestor como filha direta do estoque `CRIATIVOS`; `verify_delivered` também fixa o caminho anterior.
- `scripts/ares_campaign_v3/shein_grouped_media.py::manager_folder` valida o modelo anterior e não reconhece a nova combinação operação/formato/Exclusivos.
- `scripts/ares_campaign_v3/shein_media_handoff.py::finalize_ready_assets` preserva fisicamente a pasta do gestor, sem a transição Exclusivos para Usados.
- `creative-operations-mgs/references/manager-folder-delivery.md` instrui explicitamente o destino antigo.
- `direct-traffic-shein-operations/references/general-campaign-fast-route.md` instrui pasta direta sob CRIATIVOS e preservação física após uso.

As condições acima descrevem o preflight anterior à implementação; preservadas como diagnóstico, não como regras ativas concorrentes. A confirmação específica chegou em `1566497527719661640`. A nova rota reconhece exclusivamente os IDs do binding, preserva compatibilidade de pedidos legados em andamento, integra o finalizador SHEIN e fornece `confirm-use` com leitura Meta real para as demais rotas. Código, canário, fase ativa e primeiro uso produtivo são provas distintas.

## Critérios de aceite e fronteiras de conclusão

- Inventário e snapshot atuais, sem writer paralelo e com locks canônicos.
- Preparar/validar tabela de pastas exatas por operação, formato e gestor; criação idempotente pelo componente owner existente, sem ownership SA indevido.
- Preservar IDs, atalhos, providers, hashes, reservas, pedidos e ACKs; não mesclar binários e atalhos apenas pelo nome.
- Não reclassificar o histórico como Usados/Exclusivos sem evidência; registrar exceções não resolvidas.
- Testes de entrega e consumo de Exclusivos, uso parcial, falha de campanha, replay e isolamento entre gestores/operações.
- Canário real de leitura/entrega e readback pelos consumidores autorizados, sem criar campanha de teste ou mídia artificial produtiva.
- Atualização do catálogo e verificadores em conjunto; nenhum green slice encerra incidentes fora de sua cobertura.
- Fechamento com resultado real e pendências separadas. Limpeza de pilotos/pastas vazias, atribuição de movimentos e deduplicação de cron permanecem trabalhos distintos e não podem ser declarados resolvidos por este documento.

## Provas de implantação

- `data/ares/creative-ops/30tb-archive/manager-standard/native-preflight.json`: membership integral e owner/ancestria nativos.
- `manager-standard/native-canary.json`: atalho técnico preexistente passou por Exclusivos e Usados, manteve IDs/provider/hashes e voltou ao parent original; zero campanha ou mídia produtiva criada/movida.
- `manager-standard/active-readback.json`: releitura dos 456 destinos ativos e 24 probes reais de validação de pastas SHEIN (seis gestores × EN/ES × IMG/VID). Não representa seleção de mídia ou campanha produtiva.
- `manager-standard/activation.json`: ativação e limites. A migração dos conteúdos históricos NÃO foi executada por esta implantação aditiva; os dois layouts legados e incidentes anteriores não estão automaticamente conciliados.
- `/root/.hermes/profiles/zeus/artifacts/manager-storage-standard-1566497527719661640/closure-tests-final.json`: 156 testes focados em dez módulos passaram, com hashes do código; não é a suíte inteira do repositório.
- `manager-standard/first-production-use.json`: será gravado pelo helper somente após atribuição de campanha real e readback do mesmo stock ID no novo fluxo. Não existe no fechamento técnico inicial, porque nenhuma linhagem produtiva está ainda nos destinos novos. A validação do primeiro pedido real continua distinta e não exige upload artificial do Rodolfo.

Recuperações de validação preservadas nos artefatos: módulo novo ausente no RED inicial; interpretador sem dependência do renderer; fixture histórica acoplada à flag de layout viva; isolamento de módulos e imports de fixtures irmãos no PYTHONPATH. Foram corrigidos implementação/harness/fixture, sem relaxar guards produtivos ou instalar pacotes. Releitura mostrou espelho em revisão intermediária da própria alteração autorizada; sincronizado somente o parágrafo faltante e igualdade final conferida.
