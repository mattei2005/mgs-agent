## Resposta padrão quando Rodolfo pedir um chat novo

Se Rodolfo disser “cria um chat EMP-BR”, responder com uma proposta curta antes de buildar se faltarem dados críticos:

```text
Vou criar como EMP-BR em modo [cards/sequential].
Preciso só das URLs/ofertas finais ou posso usar as 3 ofertas padrão atuais?
```

Se ele já deu ofertas, agir direto: criar config/HTML/plugin conforme escopo e validar fluxo real.

## Verificação final

- [ ] Skill carregada antes de criar/auditar chat.
- [ ] Vertical-país identificado.
- [ ] Referência usada explicitamente.
- [ ] Fluxo mapeado em gate + chat + ofertas.
- [ ] UTMs preservadas.
- [ ] Rewarded tem fallback.
- [ ] Links finais testados.
- [ ] Se criou/modificou plugin/script/config/data, fazer REPORT-INFRA no canal correto de infra/alerts e manter a thread de trabalho com resumo executivo curto.
