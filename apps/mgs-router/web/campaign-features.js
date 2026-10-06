'use strict';
function updateEqualButton() { $('equal-weights').disabled = $('targets').children.length < 2; }
function equalWeights() {
  const weights = [...document.querySelectorAll('#targets .target-weight')];
  if (weights.length < 2) return;
  editorRelative = true;
  const value = Number((100 / weights.length).toFixed(12));
  weights.forEach(w => { w.value = value; w.max = '1000000'; w.closest('label').firstChild.textContent = 'Peso relativo'; });
  $('weight-notice').textContent = `Distribuição igual: ${weights.length} destinos, ${(100 / weights.length).toLocaleString('pt-BR', {maximumFractionDigits:4})}% para cada um. Arredondamento visual; pesos idênticos garantem a mesma chance. Clique em Salvar e aplicar para ativar.`;
}
function todayEastern() { const parts = new Intl.DateTimeFormat('en-US', {timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()); const v = type => parts.find(p=>p.type===type).value; return `${v('year')}-${v('month')}-${v('day')}`; }
function shiftDay(day,delta) { const d = new Date(day+'T12:00:00Z'); d.setUTCDate(d.getUTCDate()+delta); return d.toISOString().slice(0,10); }
function clickDatesPreset() {
  const range = $('click-range').value, today = todayEastern();
  if (range === 'custom') return;
  if (range === 'all') { $('click-from').value = ''; $('click-to').value = ''; }
  else { $('click-from').value = range === 'yesterday' ? shiftDay(today,-1) : range === 'today' ? today : shiftDay(today,1-Number(range)); $('click-to').value = range === 'yesterday' ? shiftDay(today,-1) : today; }
}
async function loadClicks() {
  const id = ++clickRequest, from = $('click-from').value, to = $('click-to').value;
  if ((!!from !== !!to) || (from && from > to)) { message('Informe as duas datas; a data inicial não pode ser posterior à final.',true); return; }
  $('apply-click-dates').disabled = true;
  clickCounts = null;
  try {
    const query = from ? '?'+new URLSearchParams({from,to}) : '';
    const result = await api('/api/clicks'+query);
    if (id !== clickRequest) return;
    clickCounts = result.counts;
    const since = new Date(result.since).toLocaleString('pt-BR',{timeZone:'America/New_York'});
    $('click-period-notice').textContent = `Fuso: America/New_York (US Eastern). Contagem desde ${since}; sem histórico anterior. Cliques totais, incluindo repetições e robôs; HEAD não conta.` + (result.failed_writes ? ` Atenção: ${result.failed_writes} acessos não puderam ser gravados neste processo.` : '');
  } catch(error) {
    if (id !== clickRequest) return;
    $('click-period-notice').textContent = 'Contagem indisponível. “—” não significa zero.';
    message(error.message,true);
  } finally { if (id === clickRequest) { $('apply-click-dates').disabled=false; render(); } }
}
window.addEventListener('DOMContentLoaded',()=>{
  $('equal-weights').onclick=equalWeights;
  $('sort-clicks').onclick=()=>{clickDescending=routeSort==='clicks'?!clickDescending:true;routeSort='clicks';pages.routes=1;render();};
  $('click-range').onchange=()=>{clickDatesPreset();if($('click-range').value!=='custom')loadClicks();};
  $('click-from').onchange=$('click-to').onchange=()=>{$('click-range').value='custom';};
  $('apply-click-dates').onclick=()=>{loadClicks();};
  clickDatesPreset();
});
