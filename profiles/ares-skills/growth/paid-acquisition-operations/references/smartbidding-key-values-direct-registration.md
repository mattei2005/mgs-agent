# SB Key Values — cadastro direto explicitamente autorizado

## Escopo desta receita

**Regra permanente aprovada por Rodolfo em `1573494030010941596`:** todo fechamento autorizado de criação/duplicação/clone, em tráfego direto e BOT, inclui cadastro direto na SB por Ares, sem mensagem para Iris nem nova aprovação por cadastro. O pedido autorizado de campanha cobre esta etapa no mesmo escopo. Fonte única da política: `paid-acquisition-operations/SKILL.md`, seção `Fechamento de campanhas — cadastro direto de key values na SB`, chave histórica `ares.campaigns.completion.iris-adops-key-values`. A restrição anterior a teste pontual está supersedida.

Tráfego direto cadastra `utm_campaign` e `utm_adgroup`; BOT cadastra `utm_campaign` literal do contrato, sem fabricar `utm_adgroup`. Ao terminar, comunicar somente a confirmação desta etapa, preservando o resumo obrigatório da campanha e as ressalvas reais. Falha ou sincronização pendente não recebe confirmação integral. Este procedimento não altera campanhas Meta, budgets, permissões, tracking nem configurações AdOps.

## Descoberta e execução

- Descubra o bundle atual de `/inventory/key-values` a partir do HTML e dos imports vivos, sem fixar hashes de assets.
- O formulário observado chama `POST /keyvalues/preregister` no backend oficial `https://api.jbfdigital.com.br`, com JSON explícito `{publisher, field, values}`. Reconfirme o contrato vivo antes de usar.
- Resolva o domínio monetizado pelo binding canônico e pelo receipt do pedido; aplique o checker corporativo antes de consultar ou escrever. Resolva `publisherId` apenas pelo catálogo positivo `ares-smartbidding-common.py` → `api_request('GET','/company')`, que projeta catálogo local autorizado. Não enumerar o catálogo remoto global.
- Extraia os valores do `final_readback` do mesmo pedido. A árvore possui `tree['campaign']['id']`, e anúncios em `tree['ads']['data']`; não pressupor `tree['id']`. Deduplicate por chave na ordem da primeira ocorrência e não inclua UTMs exclusivas da fonte clonada.
- Aceite somente `utm_campaign`/`utm_adgroup`, até 200 valores por chamada. Confirme que a normalização anunciada pela UI não mudará os identificadores: lowercase, trim, corte de 40 caracteres e remoção de caracteres especiais. Se mudaria o tracking literal, não altere Meta nem confirme igualdade; resolva a divergência.
- Autentique pela identidade SB canônica já existente. O helper geral é deliberadamente read-only: não remova, amplie ou monkeypatch seus guards para acomodar a nova rota. Sob autorização explícita deste write, uma requisição restrita ao endpoint exato pode reutilizar internamente `get_access_token()` sem exibir token nem credencial. Não usar outra identidade como fallback.
- O navegador requer `browser_vault` para senha. Se o vault estiver indisponível, não digite senha por browser, CDP ou ferramenta alternativa. Uma chamada autorizada à API oficial é uma execução por API, não prova de login ou conferência visual na dash; declare a proveniência corretamente.
- Preserve request, domínio, publisher, campanha, listas literais, timestamps e resposta sem credenciais em um único recibo durável antes/depois de cada chave. Não repita POST após resultado ambíguo; reconcilie efeitos primeiro. Retome somente a chave realmente ausente.

## Confirmação e limite de readback

- O retorno de sucesso observado inclui `publisherId`, `networkCode`, `field`, `values` e `gamInsert`. Exija igualdade literal do publisher/chave/lista solicitados; confira HTTP e tipos.
- `gamInsert='ok'` é a confirmação retornada pelo serviço de criação no GAM. Qualquer outro valor corresponde ao badge da UI `Pending hourly sync`; cadastro SB aceito não deve ser descrito como criação GAM confirmada nesse caso.
- Não confunda resposta POST com leitura independente posterior. O componente observado exibe apenas `lastResult` retornado pelo POST e não fornece listagem persistida. GETs de `/keyvalues` e `/keyvalues/preregister` não estavam implementados no teste; não inventar endpoint de consulta nem tratar relatório de impressões como catálogo de valores recém-criados.
- Após um write, busque readback independente do alvo quando houver rota autorizada documentada. Se não existir acesso seguro para isso, preserve a resposta exata e informe `serviço retornou sucesso; reconferência independente/visual pendente`, sem declarar verificação integral. Não repetir o save só para fabricar readback; resalvar renova a proteção de 90 dias e continua sendo write.
- A comunicação normal desta etapa é curta, sem bloco para encaminhamento à Iris quando o cadastro direto foi solicitado; falhas e limitações de verificação continuam explícitas. Não alegar execução por navegador quando ela ocorreu pela API.

## Teste vivo de aceitação

No teste explicitamente autorizado da campanha nova, foram confrontadas as UTMs dos dois anúncios do receipt com as duas listas únicas, o publisher positivo e as respostas do serviço; cada chave retornou HTTP 201 e `gamInsert='ok'`, com igualdade literal de todos os campos. GET independente não disponível e sessão de navegador não autenticada são limitações separadas, não falhas de criação reportadas pelo serviço. A evidência concreta fica no recibo operacional, não nesta receita.
