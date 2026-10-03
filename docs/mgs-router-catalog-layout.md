# MGS Router — Rotas, Destinos e Grupos

## Autoridade e fonte ativa

Rodolfo aprovou aplicar a organização visual proposta a partir das duas capturas Keitaro na mensagem `1555778254592417816`, thread `1555381168894115912`. Esta fonte sucede somente a organização de UI/menu e representação dos destinos descritas em `docs/mgs-router-domain-and-keitaro-import.md`; preserva distribuição ponderada, verificação assinada de domínios, segurança e ausência de cutover.

## Estado ativo posterior

O pedido `1555799233452314674` acrescentou **Editar nome** aos grupos e autorizou a troca DNS de `card.wantabrand.com`/`tarjeta.wantabrand.com`. Cutover real validado; fonte ativa `docs/mgs-router-group-edit-and-wantabrand-cutover.md`. As afirmações de ausência de cutover abaixo descrevem somente a publicação desta versão histórica.

## Entrega validada

- Painel: https://route.mgsdigitalcorp.com/admin.
- Navegação horizontal: **Rotas**, **Destinos**, **Grupos**, **Cadastro domínios**.
- Rotas em tabela compacta com nome clicável, grupo, link público, destinos expansíveis e ações editar/copiar. Busca por nome/link/destino; filtros por grupo e domínio; ordenação por nome.
- Destinos em catálogo separado: ID estável, nome, grupo, URL, quantidade de rotas que usam o item; criação/edição, busca e filtro por grupo.
- Grupos: criação e contagens de rotas/destinos; atalhos para as listas filtradas. Não alteram comportamento de tráfego.
- Editor da rota permite escolher um destino cadastrado ou uma URL manual, incluindo seleção por destino em distribuições ponderadas.
- Alteração de URL de um destino compartilhado informa o número de rotas afetadas e pede confirmação no painel. Atualização de catálogo e todos os snapshots de URL correspondentes ocorre em uma única revisão atômica. Alterar nome/grupo não muda redirects.
- Não foram acrescentados tracking, cliques, relatórios ou postbacks.

## Migração sem alteração de tráfego

- **41 rotas**, **117 entradas de destino**, **94 identidades de Landing Page** reutilizáveis, **3 grupos**.
- Catálogo usa `ktr-<landing_id>` da fonte Keitaro previamente extraída. Não deduplicar por URL: há 50 URLs distintas, mas páginas com IDs/nome diferentes continuam sendo itens separados.
- Grupos foram gerados dos prefixos de nome das campanhas: `WANTABRAND ES`, `WANTABRAND ES-CC-ES`, `WANTABRAND GB-CC-EN`. São organização local derivada, não cópia da atribuição de grupos interna do Keitaro nem inferência geográfica.
- O catálogo cobre somente destinos utilizados nas 41 rotas já importadas. Não é importação de todas as 134 Landing Pages mostradas na captura.
- Readback autenticado confirmou nomes, hosts, caminhos, URLs, ordem de destinos, pesos e macros originais sem mudança. Revisão passou de 1 para 2.
- DNS, Keitaro, DTR e Smart Bidding não receberam nenhuma escrita. Os dois domínios Wantabrand continuam pendentes de apontamento para o Router; isso não é falha desta entrega.

## Modelo e proteção contra concorrência

`routes.json` mantém `revision`, `routes` e acrescenta `catalog`/`groups`. Rotas e targets podem ter `destination_id`; URLs concretas permanecem nos snapshots para compatibilidade. Backend rejeita referências ausentes, URL divergente do catálogo, IDs/grupos duplicados, grupos inexistentes, destinos inseguros e payload antigo que omita um catálogo existente. Qualquer write deve preservar a configuração inteira e a revisão atual; não usar importadores antigos para sobrescrever somente `routes`.

## Evidência real

- 33 testes Go de primeiro nível passaram; race detector, vet, sintaxe JS e build passaram.
- Teste Chromium local criou grupo/destino, reutilizou em duas rotas, cancelou e confirmou edição compartilhada, recarregou a configuração e verificou as quatro abas em mobile. Dados sintéticos somente no fixture local.
- Duas contas públicas (`rodolfo`/`geizian`): login/API/logout, quatro abas, 41 rotas, 94 destinos, 3 grupos, busca/filtro e seleção de catálogo confirmados; zero erros JavaScript; nenhum overflow horizontal do documento. No mobile, a tabela tem rolagem interna horizontal.
- Transporte do formulário nativo, CSRF/origem, cookies e bloqueio de origem direta preservados; UI autenticada foi exercitada com cookies obtidos pelo login HTTP, não senha digitada pelo DOM.
- Serviço Router ativo. Apenas ele foi reiniciado; PIDs Zeus/Atena/Ares e hashes de unidade, usuários e TLS permaneceram iguais ao pre-deploy.
- Binário ativo SHA-256: `268a469bbc99452ecf9dc4efc8c4c0b397b942ec7f8eec6fe7cd2353e7a52a3b`.
- Backup privado: `/root/.local/share/mgs-router-rollbacks/1555778254592417816/`; contém binário e estado anterior, com permissões restritas. Binário anterior exercitado com o backup (`--check`): 41 rotas, 2 usuários, estado válido. Rollback completo deve restaurar binário e estado juntos e reconciliar qualquer edição posterior; não sobrescrever mudanças concorrentes.
- Receipts: `data/mgs-router-catalog-layout-receipt.json`, `data/mgs-router-catalog-migration-validation.json`, `data/mgs-router-public-validation.json`; plano: `data/mgs-router-catalog-plan.json`.
- Migração idempotente e fail-closed: `scripts/mgs-router-organize-catalog.py`, vinculada ao ID de aprovação acima.

## Falhas intermediárias recuperadas

- Teste RED confirmou ausência dos novos campos antes da implementação.
- Smoke antigo usava `.empty` global e passou a encontrar placeholders das três tabelas: seletor limitado à lista de rotas.
- Fixture novo reutilizou revisão 1 do plano num App vazio: ajustado para revisão 0 somente no fixture.
- Comandos auxiliares tiveram caminho relativo incorreto, helper Bash invocado por Python e lookup de chave `records` em registry que usa `entries`; corrigidos sem side effects produtivos.
- Ambiente do terminal não tinha token 1Password; tentativa sem env não autenticou. O wrapper canônico `mgs-op-with-service-account.sh` resolveu o acesso via `/root/mgs-agent/.env`, sem modificar credencial e sem emitir segredo.
- Aceitação integral repetida e aprovada após as correções; nenhuma falha operacional pendente.
