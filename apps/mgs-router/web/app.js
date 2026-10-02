'use strict';
const $ = id => document.getElementById(id);
let cfg = { revision: 0, routes: [] }, csrf = '', editing = -1;
let domains = { revision: 0, domains: [], dns: {} };
const checks = new Map();
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : 'success'; }
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...(options.headers || {}) } });
  if (response.status === 401) { location.assign('/login'); throw new Error('Sessão expirada.'); }
  const value = await response.json(); if (!response.ok) throw new Error(value.error || 'Não foi possível concluir.'); return value;
}
function element(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
function switchView(view) {
  const isDomain = view === 'dominios'; $('view-domains').hidden = !isDomain; $('view-routes').hidden = isDomain;
  $('nav-domains').classList.toggle('active', isDomain); $('nav-routes').classList.toggle('active', !isDomain);
  $('nav-domains').setAttribute('aria-current', isDomain ? 'page' : 'false'); $('nav-routes').setAttribute('aria-current', isDomain ? 'false' : 'page');
}
$('nav-domains').onclick = () => { location.hash = 'dominios'; switchView('dominios'); };
$('nav-routes').onclick = () => { location.hash = 'rotas'; switchView('rotas'); };
window.addEventListener('hashchange', () => switchView(location.hash.slice(1)));
switchView(location.hash.slice(1));
function routeTargets(route) { return route.destinations?.length ? route.destinations : [{ url: route.destination, weight: 100 }]; }
function render() {
  const filter = $('domain').value, query = $('search').value.toLowerCase(); $('routes').replaceChildren();
  cfg.routes.forEach((route, index) => {
    const targets = routeTargets(route), searchable = `${route.name || ''} ${route.host}${route.path} ${targets.map(t => t.url).join(' ')}`;
    if ((filter && route.host !== filter) || !searchable.toLowerCase().includes(query)) return;
    const row = element('article', undefined, 'route'), info = element('div', undefined, 'route-info'), source = `https://${route.host}${route.path}`;
    info.append(element('strong', route.name || route.host), element('div', route.host, 'hint'), element('div', route.path, 'path'));
    targets.forEach(t => info.append(element('div', `${targets.length > 1 ? `${t.weight}% — ` : ''}${t.url}`, 'destination')));
    const actions = element('div', undefined, 'actions'), edit = element('button', 'Editar destino', 'secondary'); edit.onclick = () => openEditor(index);
    const copy = element('button', 'Copiar link', 'secondary'); copy.onclick = async () => { try { await navigator.clipboard.writeText(source); message('Link copiado.'); } catch { message('Não foi possível copiar pelo navegador.', true); } };
    const test = element('a', 'Testar', 'button secondary'); test.href = source; test.target = '_blank'; test.rel = 'noopener noreferrer';
    actions.append(edit, copy, test); row.append(info, actions); $('routes').append(row);
  });
  if (!$('routes').children.length) $('routes').append(element('div', cfg.routes.length ? 'Nenhuma rota corresponde ao filtro.' : 'Nenhuma rota cadastrada. Comece em Nova rota.', 'empty'));
  $('route-count').textContent = `${cfg.routes.length} rotas cadastradas.`;
}
function showDNS(host) { $('dns-instructions').hidden = false; $('dns-host').textContent = `Domínio: ${host}`; const d = domains.dns; $('dns-record').textContent = `Tipo: ${d.type} | Nome: ${host} | Conteúdo: ${d.value} | TTL: ${d.ttl} | Proxy: ${d.proxy}`; $('dns-notice').textContent = d.notice; }
function updateDomains() {
  const selected = $('domain').value, hosts = [...new Set([...domains.domains, ...cfg.routes.map(r => r.host)])].sort();
  $('domain').replaceChildren(new Option('Todos os domínios', '')); hosts.forEach(d => $('domain').add(new Option(d, d))); $('domain').value = selected; $('domain-list').replaceChildren();
  hosts.forEach(host => {
    const row = element('article', undefined, 'route'), info = element('div', undefined, 'route-info'), status = checks.get(host);
    info.append(element('strong', host), element('div', status ? `${status.verified ? 'Verificado' : 'Pendente'} — ${status.message}` : 'Ainda não verificado', status?.verified ? 'domain-status verified' : 'domain-status pending'));
    if (status?.checked_at) info.append(element('div', `Última verificação: ${new Date(status.checked_at).toLocaleString('pt-BR')}`, 'hint'));
    const actions = element('div', undefined, 'actions'), dns = element('button', 'Ver instruções DNS', 'secondary'); dns.onclick = () => showDNS(host);
    const verify = element('button', 'Verificar', status?.verified ? 'verified' : 'secondary');
    verify.onclick = async () => {
      verify.disabled = true; verify.textContent = 'Verificando…';
      try { const result = await api('/api/domains/check', { method: 'POST', body: JSON.stringify({ host }) }); if (result.host !== host || typeof result.verified !== 'boolean') throw new Error('Resposta de verificação não corresponde ao domínio.'); checks.set(host, result); updateDomains(); }
      catch (error) { message(error.message, true); verify.disabled = false; verify.textContent = 'Verificar'; }
    };
    actions.append(dns, verify); row.append(info, actions); $('domain-list').append(row);
  });
  if (!hosts.length) $('domain-list').append(element('p', 'Nenhum domínio cadastrado.', 'hint'));
}
$('domain-form').onsubmit = async event => {
  event.preventDefault(); $('add-domain').disabled = true;
  try { const added = $('new-domain').value.split(',').map(v => v.trim().toLowerCase()); if (added.some(v => !v)) throw new Error('Informe domínios válidos, sem itens vazios.'); const next = [...new Set([...domains.domains, ...cfg.routes.map(r => r.host), ...added])]; domains = await api('/api/domains', { method: 'POST', body: JSON.stringify({ revision: domains.revision, domains: next }) }); $('new-domain').value = ''; updateDomains(); showDNS(added[0]); message('Domínio cadastrado. Configure o DNS; nenhum DNS foi alterado automaticamente.'); }
  catch (error) { message(error.message, true); } finally { $('add-domain').disabled = false; }
};
function addTarget(url = '', weight = 50) {
  const row = element('div', undefined, 'target-row'), uLabel = element('label', 'URL de destino'), u = element('input'), wLabel = element('label', 'Percentual (%)'), w = element('input'), remove = element('button', 'Remover', 'secondary');
  u.type = 'url'; u.className = 'target-url'; u.value = url; u.placeholder = 'https://wantabrand.com/...'; w.type = 'number'; w.className = 'target-weight'; w.min = '1'; w.max = '100'; w.step = '1'; w.value = weight;
  u.required = w.required = $('weighted').checked; remove.type = 'button'; remove.onclick = () => row.remove(); uLabel.append(u); wLabel.append(w); row.append(uLabel, wLabel, remove); $('targets').append(row);
}
function toggleWeighted() { const active = $('weighted').checked; $('weighted-destinations').hidden = !active; $('single-destination').hidden = active; $('destination').required = !active; document.querySelectorAll('.target-url,.target-weight').forEach(i => { i.required = active; }); if (active && !$('targets').children.length) { addTarget($('destination').value, 50); addTarget('', 50); } }
$('weighted').onchange = toggleWeighted; $('add-target').onclick = () => addTarget();
function openEditor(index = -1) {
  editing = index; const r = index >= 0 ? cfg.routes[index] : { host: $('domain').value, path: '', destination: '', name: '' };
  $('host').value = r.host; $('path').value = r.path; $('route-name').value = r.name || ''; $('destination').value = r.destination || ''; $('host').readOnly = $('path').readOnly = index >= 0;
  $('targets').replaceChildren(); $('weighted').checked = !!r.destinations?.length; if (r.destinations) r.destinations.forEach(t => addTarget(t.url, t.weight)); toggleWeighted();
  $('editor-title').textContent = index >= 0 ? 'Editar destino' : 'Nova rota'; $('editor').hidden = false; (index >= 0 ? ($('weighted').checked ? document.querySelector('.target-url') : $('destination')) : $('host')).focus();
}
$('new').onclick = () => openEditor(); $('cancel').onclick = () => { $('editor').hidden = true; }; $('search').oninput = render; $('domain').onchange = render;
$('route-form').onsubmit = async event => {
  event.preventDefault(); $('save').disabled = true;
  try {
    const route = { host: $('host').value.trim().toLowerCase(), path: $('path').value.trim(), name: $('route-name').value.trim() };
    if ($('weighted').checked) {
      route.destinations = [...$('targets').children].map(row => ({ url: row.querySelector('.target-url').value.trim(), weight: Number(row.querySelector('.target-weight').value) }));
      if (!route.destinations.length || route.destinations.some(t => !t.url || !Number.isInteger(t.weight) || t.weight < 1 || t.weight > 100) || route.destinations.reduce((sum, t) => sum + t.weight, 0) !== 100) throw new Error('Informe os destinos e percentuais inteiros com soma de 100%.');
    } else route.destination = $('destination').value.trim();
    const routes = cfg.routes.map(r => ({ ...r })); if (editing >= 0) routes[editing] = route; else routes.push(route);
    cfg = await api('/api/routes', { method: 'POST', body: JSON.stringify({ revision: cfg.revision, routes }) }); $('editor').hidden = true; updateDomains(); render(); message('Rota salva e aplicada. O link público foi preservado.');
  } catch (error) { message(error.message + ' Se outro usuário alterou as rotas, recarregue antes de salvar.', true); } finally { $('save').disabled = false; }
};
$('logout').onclick = async () => { try { await api('/logout', { method: 'POST', body: '{}' }); location.assign('/login'); } catch (error) { message(error.message, true); } };
(async () => { try { const me = await api('/api/me'); csrf = me.csrf; $('username').textContent = me.username; [cfg, domains] = await Promise.all([api('/api/routes'), api('/api/domains')]); updateDomains(); render(); } catch (error) { message(error.message, true); } })();
