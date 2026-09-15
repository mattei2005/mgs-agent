# Meta Media Library e staging por conta

## Regra de resposta sobre capacidade

1. Consulte a documentação oficial atual antes de afirmar limites, porque tamanho por arquivo e fluxos de upload mudam.
2. Separe três classes de limite:
   - **capacidade agregada da biblioteca** — se a Meta não publicar cota em GB ou quantidade total, responda “não há teto agregado público encontrado”, nunca “é ilimitado”;
   - **limite por arquivo** — informe imagem e vídeo somente com fonte oficial vigente;
   - **limite do fluxo** — bulk import, formulário, API e asset feed podem ter limites próprios que não representam a capacidade total da biblioteca.
3. Não transforme limite de um importador em limite global. Um fluxo de planilha que aceita poucos vídeos por operação não prova que a Media Library comporte apenas aquela quantidade.

## Papel operacional da biblioteca

- Mantenha `MGS-AGENTS` como fonte canônica de original, tratado, taxonomia, checksum, linhagem e auditoria.
- Trate a Meta Media Library como cache/staging dos assets efetivamente selecionados para anúncios, não como arquivo-mestre nem destino de upload indiscriminado.
- Faça upload somente depois de resolver a conta exata, reservar o asset e reconciliar Drive × inventário × Meta.

## Escopo por conta

- Imagem publicitária pertence à conta que possui o `image_hash`; para reutilização entre contas, use a rota de cópia suportada e valide acesso às duas contas.
- Vídeo publicitário precisa estar associado à conta exata no edge `act_{AD_ACCOUNT_ID}/advideos`; um vídeo visível em uma Page ou pasta da Media Library não prova associação à conta.
- Indexe o registry por `account_id + asset_id + checksum`. O mesmo arquivo pode gerar IDs Meta diferentes em contas diferentes.
- Nunca prometa que um único `video_id` ou `image_hash` funcionará em todas as contas só porque as pastas da Media Library permitem permissões para várias contas.

## Upload eficiente

1. Reutilize um registro `ready` da conta exata antes de baixar, renderizar ou enviar novamente.
2. Para itens ausentes, reconcilie títulos determinísticos uma vez por coorte.
3. Suba somente as variantes exigidas pelo contrato da operação.
4. Agrupe o wait-ready em batches permitidos e faça uma única varredura de associação por coorte.
5. Não apague mídia da Meta como consequência automática de excluir campanha ou devolver asset ao Drive; reconcilie dependências e obtenha autorização própria.

## Fontes oficiais a consultar

- Media Library: https://www.facebook.com/business/help/201810921904951
- Troubleshoot image uploads: https://www.facebook.com/business/help/755224297893936
- Troubleshoot video uploads: https://www.facebook.com/business/help/1596868350601716
- Ad Image API: https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/ad-image
- Video Ads API: https://developers.facebook.com/docs/marketing-api/guides/videoads/
