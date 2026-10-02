# Roteador MGS — rotas com interface administrativa

## Decisão vigente (v2)

Dono: Rodolfo Mattei. Responsável: Zeus.
Fonte: thread Discord 1555381168894115912; painel/interface incluído explicitamente na mensagem 1555605972049862688. Hospedagem inicial na VPS atual mantida conforme mensagem 1555601880795713569.

- Software próprio, sem Keitaro/licença/dependência dele.
- Rotas e redirecionamentos com preservação dos parâmetros de entrada.
- Interface/painel para administrar as rotas incluído no escopo.
- Sem tracking, estatísticas, banco de cliques, relatórios ou postbacks; incluir interface não autoriza esses extras.
- Wantabrand primeiro, extensível a outros sites.
- Começar na VPS atual com limites de recursos para preservar os agentes; migrar se houver pressão, mediante gates aplicáveis. Sem contratação/custo novo agora.

## Interface mínima incluída no escopo

- Selecionar site/domínio e listar/pesquisar suas rotas.
- Cadastrar rota com caminho público e URL de destino; editar o destino sem alterar o link público.
- Copiar link público e testar o redirecionamento.
- Salvar/aplicar configuração validada, rejeitando caminhos duplicados e destinos inválidos.
- Definir autenticação e proteção do painel antes da exposição pública; alterações de credenciais ou acesso obedecem ao AGENT.md.
- Interface separada do caminho do redirect: consulta pública usa rotas em memória, não depende de renderizar painel ou consultar banco a cada clique.

Detalhes visuais e campos definitivos serão validados com Rodolfo no protótipo. Esta proposta não autoriza controles funcionais novos como pesos, geo-filtros ou pausa global de rotas.

## Próxima etapa e estado

O estado de implantação é mantido em `docs/mgs-router-public-deployment.md` e nos dados de validação apontados por ela. Este documento define o escopo, não é a fonte de estado runtime. Cadastro/importação de rotas reais e cutover DTR/SB continuam separados da publicação do painel.

## Supersessão

Esta decisão substitui MGS-ROUTER-SCOPE-HOSTING-20261002 na chave mgs.router.scope-and-hosting. Fonte anterior preservada em docs/mgs-router-scope-and-hosting.md como histórica. A restrição anterior 'sem painel' foi substituída pela mensagem 1555605972049862688; as demais restrições e a hospedagem foram mantidas.
