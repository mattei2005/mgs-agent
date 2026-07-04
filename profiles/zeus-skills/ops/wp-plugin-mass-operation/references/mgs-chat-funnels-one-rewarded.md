# MGS Chat Funnels — rewarded ads: 1 chamada, não loop de 5

## Quando usar

Use esta referência ao operar, revisar ou debugar o plugin `MGS Chat Funnels` em rotas públicas `/chat/...` que usam wrapper JBF/Ciro (`window.jbftag`, `gpt.js`, `assets.jbfdigital.com.br`).

## Lição operacional

Um `index.html` legado do Ciro/JBF tinha este padrão:

```js
window.jbftag = window.jbftag || { cmd: [] };
for (let i = 0; i < 5; i++) {
  window.jbftag.cmd.push(() => {
    if (window.jbftag.requestRewardAds) {
      window.jbftag.requestRewardAds();
    }
  });
}
```

Isso chama `requestRewardAds()` 5 vezes. Em runtime, o GAM cria slots `..._rewarded/1` até `..._rewarded/5`.

Quando Ciro/JBF disser que o correto é “puxar 1 só”, a implementação deve ser:

```js
window.jbftag = window.jbftag || { cmd: [] };
window.jbftag.cmd.push(() => {
  if (window.jbftag.requestRewardAds) {
    window.jbftag.requestRewardAds();
  }
});
```

Manter `showRewardedAds()` no CTA final do gate; a correção é apenas remover o loop de background.

## Validação runtime

Após deploy, validar HTML e browser:

```bash
curl -sS -A 'Mozilla/5.0' -L 'https://SITE/chat/.../?cb=TIMESTAMP' | grep -F 'for (let i = 0; i < 5; i++)'
# esperado: 0 ocorrências
```

No browser console:

```js
new Promise(resolve => setTimeout(() => resolve({
  htmlLoop5: document.documentElement.innerHTML.includes('for (let i = 0; i < 5; i++)'),
  slots: window.googletag && googletag.pubads
    ? googletag.pubads().getSlots().map(s => ({ id: s.getSlotElementId(), path: s.getAdUnitPath() }))
    : null
}), 3000))
```

Esperado:

```text
htmlLoop5 = false
slots     = apenas ..._rewarded/1 antes do CTA, não /1 a /5
```

## Pitfall

Paridade literal com `index.html` é útil para estrutura, IDs, wrapper e callbacks, mas não deve congelar comportamento de ads que o dono do wrapper corrigiu depois. Se a orientação atual do Ciro/JBF conflitar com o `index.html` legado, a orientação atual vence; registre a diferença e valide por slots reais.
