# SHEIN — revisão de anúncios e ativação seletiva

## Escopo e autoridade

Use somente após pedido explícito de revisão e/ou de habilitar os anúncios permitidos de um lote já criado. Uma ordem posterior de gestão parcial não é autorização para trocar mídia/copy, criar cópias, reenviar anúncio como novo, mudar budget/lance/início ou relaxar a barreira de criação. Preserve request/IDs, os manifests selados, clock e QA renderizada. Registre o novo escopo em recibo de gestão separado; não marque o runner antigo COMPLETE integral se anúncios continuam pausados/reprovados.

## Ativação status-only dos objetos existentes

Revalide conta, saúde, moeda/fuso, autoridade e writer lease do mesmo request. Faça pre-read dos IDs confirmados e confira QA, targeting, budget, cap e início. Habilite somente ads sem reprovação/issues no instante da leitura, depois conjuntos e campanhas autorizados; pule os já corretos. Cada tentativa usa apenas `status=ACTIVE`, journal anterior ao write, `graph_post_once` e GET do mesmo ID após sucesso, erro ou incerteza. Não use o runner de criação como teste de disponibilidade, nem interprete ACTIVE do pai como aprovação de todos os filhos. Conte separadamente campanhas/conjuntos configurados ACTIVE, ads configurados ACTIVE, estados efetivos e anúncios que permanecem bloqueados. ACTIVE com início futuro continua programado, não prova gasto.

## Solicitar revisão na interface

A documentação de Appeals APIs de Business Asset Management cobre contas/BMs banidos; não enviá-la como apelo de anúncios individuais. `ad_review_feedback` é leitura e não oferece criação/update de revisão. Use Business Support Home/Account Quality na conta exata, por sessão corporativa autorizada, sem importar cookies/tokens ou criar identidade alternativa.

Sob a lease PC1, reconcilie a disponibilidade do AdsPower e a sessão permitida. Se a rota MCP estiver indisponível, a interface já autenticada pode ser inspecionada pelo CUA dentro da mesma autorização, mas exija nome e ID exatos da conta antes de agir. Tela de login segue browser_vault; sem vault disponível, não digite credencial nem peça senha no chat.

Congele os ad IDs reprovados do pedido e seus campaign IDs. Em Available for review, filtre SOMENTE as campanhas afetadas: esse seletor é multiseleção. Confira a quantidade filtrada contra os IDs da API antes de Select All; o total global da conta pode conter reprovações antigas alheias. Preserve screenshots/árvores e intent antes de Request review → Submit. O modal avisa que os ads podem começar conforme o agendamento anterior: confira a cobertura da autoridade antes de confirmar. Não envie novamente após resposta incerta ou processamento em curso.

Exija confirmação real `We've received your request` e faça leitura posterior da conta/IDs. Se a API apontar anúncios com `2490468`, mas a conta exata na interface continuar com `Available for review = 0` após conferir os filtros, registre `review_submitted=false`: a divergência não comprova revisão prévia, aprovação ou inelegibilidade permanente. Não clique em envio desabilitado, invente apelo por API ou recrie anúncios; uma abertura de atendimento é outra ação e depende da autorização específica correspondente.

O contador In review pode continuar zero enquanto os anúncios saem de Available for review; isso não autoriza novo envio nem prova aprovação/rejeição. Registre a confirmação recebida e a limitação atual sem inventar protocolo ou status. A decisão posterior da Meta permanece externa. Troca de materiais depende do pedido específico do gestor, não da autorização de apelo.

## Leitura e input remotos

AX de menus pode incluir bounds de conteúdo fora do viewport. Não clicar no centro de item cortado: use pixels da captura real ou a barra de rolagem interna e releia o estado. Confira o enquadramento de coordenadas pelo resultado efetivo: o wrapper pode escalar `coordinate` a partir da imagem reduzida, apesar do rodapé sugerir bounds nativos. Evite aplicar escala duas vezes. Em Chrome, `set_value` no endereço via UIA ValuePattern seguido de Return foreground foi verificado quando teclas/texto sintéticos não alteraram a URL. Conte falhas e troque de rota; não repita input sem readback. Libere a lease ao sair e preserve os navegadores do usuário.
