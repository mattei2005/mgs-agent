'use strict';
window.MGSPeriodPreview=(()=>{
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const table=(headers,rows)=>'<div class="scroll" tabindex="0" role="region" aria-label="Prévia: deslize para os lados"><table><thead><tr>'+headers.map(h=>'<th>'+esc(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>'<td>'+v+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
 const label=x=>({month:'Somente no mês',range:'Prazo limitado',from:'Desde a competência',permanent:'Permanente',active:'Dentro da vigência',expired:'Fora da vigência',future:'Ainda não vigente',consult:'Consultar cadastro',do_not_carry:'Não transportar',confirm:'Confirmar continuidade',unchanged:'Igual nos dois meses',changed:'Cadastro diferente',added:'Só no destino',absent:'Só na origem',pass:'Consistente',fail:'Requer revisão'})[x]||x||'—';
 const auth=id=>id?'<a target="_blank" rel="noopener noreferrer" href="https://discord.com/channels/1185714635991679006/1545426987756298340/'+esc(id)+'">Ver decisão</a>':'Sem decisão vinculada neste cadastro';
 const values=v=>v?Object.entries(v).map(([k,x])=>esc(k)+': '+esc(typeof x==='object'?JSON.stringify(x):x)).join('<br>'):'Não cadastrado';
 async function load(review){
  const host=document.querySelector('#periodPreview');if(!host)return;
  try{
   const response=await fetch('/api/period-preview?'+new URLSearchParams({period:review.period.id,revision:String(review.revision)}));
   if(response.status===401){location.replace('/login');return;}
   const r=await response.json();if(!response.ok)throw Error(r.error||'Prévia indisponível');if(!host.isConnected)return;
   const ruleRows=r.rules.map(x=>['<strong>'+esc(x.title)+'</strong><br>'+esc(x.description),esc(label(x.scope))+'<br>'+esc(x.from)+' → '+esc(x.until||'sem término definido'),esc(label(x.current_state))+' → '+esc(label(x.next_state))+'<br><strong>'+esc(label(x.action))+'</strong>',auth(x.authority)+'<br><small>'+esc(x.source)+'</small>']);
   const cadRows=r.cadastros.map(x=>['<strong>'+esc(x.label)+'</strong><br>'+esc(x.kind),esc(label(x.state))+(x.changes.length?'<br>'+x.changes.map(esc).join(', '):''),'<details><summary>Comparar registros</summary><p><strong>Origem:</strong><br>'+values(x.before)+'</p><p><strong>Destino:</strong><br>'+values(x.after)+'</p></details>',auth(x.authority)]);
   host.innerHTML='<p><strong>'+esc(r.period.label)+' → '+esc(r.next_label||'Fim do horizonte cadastrado')+'</strong> · origem revisão '+esc(r.revision)+' · destino '+esc(r.target?'revisão '+r.target.revision:'indisponível')+'</p><div class="summary-note">Somente leitura: nenhuma regra ou valor é aplicado. '+esc(r.coverage)+'</div><p>'+r.counts.rules+' decisões mapeadas · '+r.counts.cadastros+' cadastros comparados · '+r.counts.changes+' diferenças cadastrais · '+r.counts.pending+' pendências documentais</p>'+
    '<details open><summary><strong>Validade das regras e exceções</strong></summary>'+table(['Regra documentada','Vigência','Origem → destino','Autoridade / fonte'],ruleRows)+'</details>'+
    '<h3>Confirmações e controles</h3>'+(r.pending.length?'<ul>'+r.pending.map(x=>'<li><strong>'+esc(x.title)+':</strong> '+esc(x.reason)+'</li>').join('')+'</ul>':'<p>Nenhuma pendência adicional identificada neste catálogo. Isso não equivale a aprovação de fechamento.</p>')+
    (r.controls.length?table(['Controle','Resultado','Registros'],r.controls.map(x=>[esc(x.label),esc(label(x.status)),x.items.map(esc).join(', ')||'—'])):'')+
    '<details><summary><strong>Cadastros já existentes nos dois meses</strong></summary><p>Comparação de sites, despesas e contas. Não copia nem confirma recorrência, pagamento ou mudança de gestor. Valores calculados em USD/BRL ficam fora desta comparação.</p>'+table(['Cadastro','Comparação','Antes / depois','Decisão registrada'],cadRows)+'</details>'+
    '<details><summary><strong>O que não deve ser transportado como novo lançamento</strong></summary><ul>'+r.excluded.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></details><div class="summary-note">'+r.notes.map(esc).join('<br>')+'</div>';
   host.dataset.loaded=r.period.id;
  }catch(e){if(host.isConnected){host.textContent='Prévia indisponível: '+e.message+'. Nenhum dado foi alterado.';host.dataset.error='true';}}
 }
 return {load};
})();
