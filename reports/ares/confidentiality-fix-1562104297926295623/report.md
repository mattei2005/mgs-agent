# Correção de consultas — Ares / Digital Trust / SB

## Estado

Correções locais de consultas aplicadas e verificadas. **A confidencialidade ponta a ponta permanece ABERTA**: o processo Ares continua como root e tem ferramentas e credenciais de alcance amplo. Não declarar que o isolamento foi concluído.

## Aplicado

- Gate Meta valida nó numérico, origem dos objetos, descoberta global, query, batch e body antes do transporte. `account_id` declarado pelo chamador não prova a conta de um objeto. Metadados mínimos do app técnico continuam permitidos; não há liberação do portfólio proprietário.
- O próprio transporte persiste apenas proveniência originada de resposta account-scoped autorizada. IDs de filhos desconhecidos são bloqueados até descoberta pelo edge permitido; em retomadas frias é preciso obter essa proveniência antes da leitura por ID.
- A resposta Meta com conta contraditória é retida. O helper mantém os controles de quota/backoff e faz a observação da resposta sem armazenar credenciais.
- O catálogo SB usado por Ares agora é uma projeção local positiva de 52 hosts, obtida por leitura de duas companies corporativas explicitamente autorizadas. Não se usa GET remoto global /company para relatórios. Registros sem URL operacional não foram promovidos nem reproduzidos.
- Relatórios SB exigem publishers positivos e rota de leitura reconhecida antes de obter credencial/HTTP. Aliases de seletores em GET/POST são verificados, inclusive no transporte de nível inferior. Respostas contraditórias por domínio/publisher ou por conta Meta são retidas.
- Chamadas Graph diretas localizadas em dois runners legados receberam o mesmo gate. Isso não equivale a cobertura de todo transporte alternativo possível nem impede HTTP arbitrário com um token fora do helper.
- Referências de procedimento atualizadas nas skills Meta Intraday e Paid Acquisition; readback efetuado.

## Verificação real

- Suite dirigida no Python da instalação Hermes: **64 testes e 18 subtestes aprovados**.
- As 10 provas da auditoria, antes com seis falhas, agora atendem às expectativas; nenhuma prova negativa faz HTTP ou usa credencial real.
- Smoke live read-only em duas contas corporativas: leitura de conta/campos financeiros, campanhas, filho com conta comprovada e atividades retornou **HTTP 200**. Isso é teste amostral, não auditoria live de todas as contas nem conciliação de todas as faturas.
- Metadados do app técnico: **HTTP 200**.
- Catálogo SB local: **52 publishers / zero HTTP global**.
- Performance SB para dois publishers autorizados, em 19/10/2026: **HTTP 201**, 344 linhas; receita Domain: **HTTP 200**, 4 linhas. São verificações de transporte/escopo, não relatório financeiro publicado, e a janela pode refletir a semântica diária da fonte.
- Nenhuma campanha, orçamento, permissão, token, dashboard ou serviço foi alterado. Houve mudanças locais de código, dados positivos de escopo, proveniência e documentação.

## Pendência crítica — não executada

A segregação completa não pode ser obtida apagando fontes compartilhadas necessárias a outras operações. É preciso separar a execução Ares e a entrega de credenciais/fontes; o terminal local root pode contornar um helper.

Proposta para confirmação específica com Rodolfo e execução por Zeus:

1. Migrar o serviço `ares-gateway.service` de root para identidade exclusiva sem sudo/privilégios administrativos, com workspace/profile próprios e sem acesso aos perfis, inventários, logs, backups ou dados privados externos ao Ares.
2. Expor somente projeções positivas de dados/documentação. Retirar do ambiente Ares o acesso direto ao cofre amplo e aos tokens de alcance maior; fornecer acesso operacional por intermediário que valide conta/publisher antes de credencial e HTTP. Preservar o app e as permissões Meta existentes — não revogar ou trocar tokens de produção nesta etapa sem aprovação separada.
3. Alterar a unidade de serviço/configuração de isolamento do servidor e efetuar ativação/restart controlado fora da sessão ativa. Isso envolve `/etc/`, protegido pelo Critical Subset; a autorização genérica de correção não substitui a confirmação específica dessa ação.
4. Zeus deve validar dependências de Drive/Meta/SB/browser/crons no ambiente isolado, testar tentativas negativas de filesystem/cofre/HTTP alternativo e verificar relatório genérico completo antes do cutover. Se a compatibilidade não passar, não ativar o serviço novo. Não usar rollback que volte silenciosamente a divulgar dados privados.

Até esse isolamento ser comprovado, não fechar o critério de confidencialidade E2E. Não confundir '64 testes passaram' com 'todas as ferramentas e fontes estão isoladas'.
