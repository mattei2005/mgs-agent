# Reauditoria de confidencialidade do Ares

Conclusão: **não está comprovado nem tecnicamente fechado o isolamento exigido**. Cadastro e instruções estão corretos; permanecem brechas locais reproduzíveis e fontes compartilhadas acessíveis. Auditoria solicitada por Rodolfo na thread 1562104297926295623; nenhuma correção produtiva está implícita neste relatório.

## Cobertura e evidência

- 160.742 arquivos regulares únicos inventariados; 121.001 arquivos sem cabeçalho binário lidos para busca textual (11.962 no profile Ares e 109.039 nas fontes compartilhadas selecionadas).
- 76 bancos SQLite identificados; um cache de favicons do navegador permanece parcialmente ilegível por SQLITE_CORRUPT. 30 compactados examinados, com 37.188 membros; nenhum membro foi ignorado pelo limite de tamanho.
- 39 erros de caminho foram reconciliados: links simbólicos quebrados em scratch, não documentos omitidos por falha de permissão. Mídia/binários não equivalem a análise visual/OCR.
- Excluídos: Git histórico, dependências, perfis privados externos ao Ares, bancos privados de aplicações, Discord remoto, memória externa e backups externos. A seleção de fontes compartilhadas não equivale a auditoria completa de todo o servidor.

## O que está correto

- Registro ativo e validado: 351 contas Digital Trust e 52 hosts SB para Ares. O total geral de domínios de outro consumidor não redefine o recorte Ares.
- Nos 15 contratos JSON atuais de contas/operações, 102 referências de conta e 44 de domínio verificadas pelos campos explícitos não apresentaram itens fora do registro. Não é uma afirmação sobre todos os IDs soltos em históricos.
- 21 testes existentes passaram. Os bloqueios de conta explícita e batch com act_ foram confirmados localmente.
- Nenhum dos termos privados pesquisados foi encontrado nos arquivos textuais lidos do profile; o banco de sessões contém duas mensagens de usuário com contexto desta conversa. Índices FTS repetem essas mensagens e não foram contados como mensagens adicionais. Referências legítimas ao proprietário do app não foram classificadas automaticamente como contas externas.

## Lacunas comprovadas

1. **Fontes compartilhadas:** os termos privados pesquisados permanecem em 70 arquivos compartilhados: inventários, relatórios, audit e backups; outros 8 membros de compactado também contêm referências. Busca textual indica vestígio, não quantidade de ativos, contas ou lançamentos financeiros. Os dados correspondentes não foram reproduzidos na evidência.
2. **Cobertura Meta:** 10 provas offline, com dados sintéticos e nenhuma rede/credencial, tiveram 6 resultados contrários ao sigilo exigido. O gate deixa passar nó numérico sem proveniência, descoberta global de contas/BMs, edge de contas de business não comprovado, objeto filho sem conta validada e conta embutida em query de batch. Isso prova insuficiência do gate, não que a Meta concederia acesso ao ID sintético.
3. **Smart Bidding:** o helper retorna /company sem impor o cadastro local de hosts; resposta sintética fora do recorte passou integralmente no teste mockado. A referência de ROI ainda prevê consulta global seguida de filtro em memória. Não foi consultado payload real externo, nem foi validada a extensão real da credencial na SB.
4. **Isolamento:** serviço e terminal local executam como root; ProtectHome/ProtectSystem/NoNewPrivileges desativados, sem InaccessiblePaths. Separação por profile e política não impede tecnicamente leitura das fontes compartilhadas.
5. **Transportes alternativos:** há chamadas Graph diretas em runners legados, além do helper. A presença do import do helper não prova cobertura de todas as chamadas. Não foi executado write nem tráfego externo para exercitá-las.

## Tratamento e continuidade

- Preservados app, tokens, permissões, campanhas, orçamento, serviços e dashboards. Nenhum dado de origem foi apagado ou redigido nesta auditoria.
- Persistidos somente relatório/evidência sanitizados, inventário da entrega, checkpoint e procedimento de auditoria na skill Meta Intraday.
- Próxima ação necessária com Zeus: separar fontes/identidades de execução, impor seleção positiva antes das consultas e validar a proveniência de cada objeto/rota; testar pedidos genéricos ponta a ponta, incluindo financeiro, sem descoberta de operações externas. Mudanças críticas de credencial/serviço precisam de desenho e autorização exatos, preservando a dependência técnica do app.
- O pedido de auditoria está concluído; a pendência de confidencialidade permanece aberta, não resolvida.
