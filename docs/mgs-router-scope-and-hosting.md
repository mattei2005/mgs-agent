# Roteador MGS — escopo e hospedagem

> Documento histórico (v1), supersedido por `docs/mgs-router-scope-and-hosting-v2.md` após Rodolfo incluir interface/painel na mensagem `1555605972049862688`. A restrição abaixo de não ter painel não é mais vigente; o conteúdo original permanece para rastreabilidade.

## Decisões históricas

Dono: Rodolfo Mattei. Responsável técnico: Zeus.
Fonte: thread Discord 1555381168894115912; escopo somente rotas confirmado na mensagem 1555596916794982564; hospedagem inicial na VPS atual decidida na mensagem 1555601880795713569.

- Produto próprio, sem instalação, licença ou dependência de Keitaro.
- Somente rotas e redirecionamento, preservando parâmetros de entrada.
- Sem painel, tracking, banco de cliques, relatórios ou postbacks.
- Wantabrand como primeiro site; extensível a futuros sites.
- Começar na VPS atual dos agentes. Não contratar nova VPS agora.
- Se houver pressão de recursos, planejar migração para VPS dedicada. Contratação/cobrança continua sujeita à confirmação crítica; a decisão não autoriza custo novo automaticamente.

## Salvaguardas propostas para implementação

- Processo próprio, com limites de CPU/memória e concorrência para priorizar os agentes; limites exatos serão definidos por teste.
- Configuração simples de rotas, independente do IP/host de execução, para permitir migração mantendo os links públicos.
- Testes iniciais em localhost, sem alterar DNS, DTR ou SB.
- Medir latência e consumo sob carga antes de tráfego real; a observação momentânea de memória disponível não comprova capacidade de produção.
- Migração preventiva baseada em pressão sustentada, piora de latência e impacto nos agentes, não apenas depois de uma indisponibilidade.

## Estado e limites de autorização

Decisão de escopo e hospedagem registrada. Não há implantação ou código validado por este registro. Pedido atual define a hospedagem; não é declaração de sucesso do protótipo nem autorização para alterar arquivos protegidos do sistema, firewall, credenciais ou cobrança. A etapa seguinte é mapear rotas e produzir o protótipo local dentro do escopo autorizado, com qualquer gate crítico tratado separadamente.

## Histórico

A decisão de começar na VPS atual substitui a recomendação anterior de exigir VPS dedicada desde o início. Os recursos extras do plano inicial foram rejeitados por Rodolfo; não fazem parte de fases futuras implícitas.
