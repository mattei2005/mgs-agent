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

A regra cobre Zeus, Atena, Ares, Hera e todo novo agente MGS. Cada agente deve manter peer/perfil isolado e receber apenas o contexto compatível com sua função e seus usuários autorizados.

## Relação com USER/MEMORY

USER/MEMORY continuam limitados a preferências e invariantes que precisam estar presentes em todo turno. Honcho absorve a pressão de crescimento causada por histórico, contexto longitudinal e conclusões derivadas.

O autocompactor de USER/MEMORY deixa de ser a solução principal. O monitor de 90% permanece como proteção residual até a integração Honcho estar implantada e validada em cada agente.

## Estado verificado na decisão

Em 2026-07-17, os quatro profiles existentes (`zeus`, `atena`, `ares`, `hera`) estavam com `memory.provider` vazio e sem `honcho.json`. A MGS possuía apenas o wrapper externo `scripts/mgs-memory-copilot`, portanto a integração nativa ainda não estava ativa em nenhum deles.

## Gate de implantação

A decisão de integrar todos os agentes está aprovada. A implantação deve ocorrer por agente, com backup, configuração nativa, isolamento de peer, orçamento de contexto, canário real, rollback e readback.

Antes de enviar conversas operacionais não sanitizadas a um serviço gerenciado externo, deve existir decisão explícita de tratamento de dados. Sob a política vigente, managed Honcho recebe somente dados sintéticos ou sanitizados; uso integral de histórico operacional requer uma solução de hospedagem/política compatível.
