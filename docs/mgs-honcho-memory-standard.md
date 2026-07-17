# MGS Honcho Memory Standard

> Status: decisão canônica aprovada
> Dono executivo: Rodolfo Mattei
> Vigência: 2026-07-17
> Origem: Discord thread `1527558141397700618`, mensagem `1527673289781153803`

## Decisão

Honcho deve ser integrado nativamente a todos os agentes MGS atuais e futuros como camada de memória entre sessões, perfil do usuário e conclusões derivadas.

A integração deve usar o memory provider nativo do Hermes, e não apenas um copilot externo ou execução manual sob demanda.

## Papel e precedência

Honcho é uma camada de contexto, recuperação semântica e hipóteses. Ele não substitui as fontes canônicas MGS.

A precedência permanece:

1. runtime, APIs, bancos e dashboards para estado real;
2. MGS OS, registros e dados canônicos para política, ownership e decisões;
3. audit/Git para rastreabilidade;
4. USER/MEMORY como cache pequeno e sempre ativo;
5. Honcho para continuidade, perfil, contexto e conclusões que ainda exigem validação antes de ação operacional.

Credenciais nunca são memória e permanecem exclusivamente no 1Password.

## Escopo

A regra cobre Zeus, Atena, Ares e todo novo agente MGS. Cada agente deve manter peer/perfil isolado e receber apenas o contexto compatível com sua função e seus usuários autorizados.

## Relação com USER/MEMORY

USER/MEMORY continuam sempre ativos e limitados a preferências e invariantes que precisam estar presentes em todo turno. Honcho atua diretamente sobre o perfil do usuário a partir das conversas persistidas e absorve a pressão de crescimento causada por histórico, contexto longitudinal e conclusões derivadas.

No provider nativo atual, um `add` bem-sucedido no alvo `user` também é espelhado como conclusão Honcho. Isso não é sincronização bidirecional: `replace`/`remove` de USER e gravações em MEMORY não são espelhados por esse hook. USER/MEMORY permanecem a camada exata e sempre ativa; Honcho é a camada longitudinal e semântica.

O autocompactor de USER/MEMORY deixa de ser a solução principal. O monitor de 90% permanece como proteção residual até a integração Honcho estar implantada e validada em cada agente.

## Estado verificado na decisão

Em 2026-07-17, os profiles operacionais (`zeus`, `atena`, `ares`) foram migrados para o provider Honcho nativo após o baseline inicial sem `memory.provider`.

## Gate de implantação

A decisão de integrar todos os agentes e usar Honcho managed com persistência das conversas operacionais foi confirmada por Rodolfo em 2026-07-17. Isso não autoriza o envio de credenciais nem altera a precedência das fontes canônicas.

A implantação ocorre por agente, com backup, configuração nativa, isolamento de peer, orçamento de contexto, canário real, rollback e readback. A chave permanece protegida nos ambientes locais dos profiles e nunca entra em Git, logs ou chat.
