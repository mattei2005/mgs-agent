'use strict';
const $ = id => document.getElementById(id);
let cfg = { revision: 0, routes: [], catalog: [], groups: [] }, csrf = '', editing = -1, editingDestination = '', editingGroup = '';
let domains = { revision: 0, domains: [], dns: {} }, routeAscending = true, destinationAscending = true;
const checks = new Map();
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : 'success'; }
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...(options.headers || {}) } });
  if (response.status === 401) { location.assign('/login'); throw new Error('Sessão expirada.'); }
  const value = await response.json(); if (!response.ok) throw new Error(value.error || 'Não foi possível concluir.'); return value;
}
function element(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
function button(text, action, cls = 'secondary') { const e = element('button', text, cls); e.type = 'button'; e.onclick = action; return e; }
function cell(row, text, cls) { const td = element('td', text, cls); row.append(td); return td; }
function emptyRow(parent, text, columns) { const row = element('tr'); const td = cell(row, text, 'empty'); td.colSpan = columns; parent.append(row); }
function switchView(view) {
  const keys = { rotas: 'routes', destinos: 'destinations', grupos: 'groups', dominios: 'domains' }, active = keys[view] || 'routes';
  Object.values(keys).forEach(key => { $('view-' + key).hidden = key !== active; $('nav-' + key).classList.toggle('active', key === active); $('nav-' + key).setAttribute('aria-current', key === active ? 'page' : 'false'); });
}
[['routes','rotas'],['destinations','destinos'],['groups','grupos'],['domains','dominios']].forEach(([id, hash]) => { $('nav-' + id).onclick = () => { location.hash = hash; switchView(hash); }; });
window.addEventListener('hashchange', () => switchView(location.hash.slice(1))); switchView(location.hash.slice(1));
function routeTargets(route) { return route.destinations?.length ? route.destinations : [{ url: route.destination, weight: 100, destination_id: route.destination_id }]; }
function catalogByID(id) { return (cfg.catalog || []).find(d => d.id === id); }
function usage(id) { return cfg.routes.filter(r => routeTargets(r).some(t => t.destination_id === id)); }
function choices(select, options, label) { const value = select.value; select.replaceChildren(new Option(label, '')); options.forEach(([text, id]) => select.add(new Option(text, id))); select.value = value; }
function updateGroups() {
  const options = (cfg.groups || []).slice().sort().map(g => [g, g]);
  ['route-group-filter','destination-group-filter'].forEach(id => choices($(id), options, 'Todos os grupos'));
  ['route-group','catalog-group'].forEach(id => choices($(id), options, 'Sem grupo'));
}
function fillPicker(select, id = '') { choices(select, (cfg.catalog || []).slice().sort((a,b) => a.name.localeCompare(b.name, 'pt-BR', {numeric:true})).map(d => [`${d.name}${d.group ? ' · ' + d.group : ''}`, d.id]), 'URL manual'); select.value = id; }
function render() {
  const filter = $('domain').value, group = $('route-group-filter').value, query = $('search').value.toLowerCase(); $('routes').replaceChildren(); let count = 0;
  cfg.routes.map((route,index) => ({route,index})).sort((a,b) => (routeAscending ? 1 : -1) * (a.route.name || a.route.path).localeCompare(b.route.name || b.route.path, 'pt-BR', {numeric:true})).forEach(({route,index}) => {
    const targets = routeTargets(route), searchable = `${route.name || ''} ${route.group || ''} ${route.host}${route.path} ${targets.map(t => `${t.url} ${catalogByID(t.destination_id)?.name || ''}`).join(' ')}`;
    if ((filter && route.host !== filter) || (group && route.group !== group) || !searchable.toLowerCase().includes(query)) return;
    count++; const row = element('tr', undefined, 'route'), source = `https://${route.host}${route.path}`;
    cell(row).append(button(route.name || route.path, () => openEditor(index), 'text-link'));
    cell(row, route.group || '—'); const link = element('a', source, 'path'); link.href = source; link.target = '_blank'; link.rel = 'noopener noreferrer'; cell(row).append(link);
    const details = element('details'), summary = element('summary', targets.length === 1 ? (catalogByID(targets[0].destination_id)?.name || '1 destino') : `${targets.length} destinos`); details.append(summary);
    targets.forEach(t => details.append(element('div', `${targets.length > 1 ? `${t.weight}% — ` : ''}${t.url}`, 'destination'))); cell(row).append(details);
    const actions = element('div', undefined, 'actions'); const edit = button('Editar destino', () => openEditor(index));
    const copy = button('Copiar link', async () => { try { await navigator.clipboard.writeText(source); message('Link copiado.'); } catch { message('Não foi possível copiar pelo navegador.', true); } });
    actions.append(edit, copy); cell(row).append(actions); $('routes').append(row);
  });
  if (!count) emptyRow($('routes'), cfg.routes.length ? 'Nenhuma rota corresponde ao filtro.' : 'Nenhuma rota cadastrada. Comece em Nova rota.', 5);
  $('route-count').textContent = `${count} de ${cfg.routes.length} rotas.`;
}
function renderCatalog() {
  const query = $('destination-search').value.toLowerCase(), group = $('destination-group-filter').value; $('destinations').replaceChildren(); let count = 0;
  (cfg.catalog || []).slice().sort((a,b) => (destinationAscending ? 1 : -1) * a.name.localeCompare(b.name, 'pt-BR', {numeric:true})).forEach(d => {
    if ((group && group !== d.group) || !`${d.name} ${d.url} ${d.group || ''} ${d.id}`.toLowerCase().includes(query)) return;
    count++; const row = element('tr'); cell(row, d.id, 'hint'); cell(row).append(button(d.name, () => openDestination(d.id), 'text-link')); cell(row, d.group || '—'); const url = element('a', d.url, 'path'); url.href = d.url; url.target = '_blank'; url.rel = 'noopener noreferrer'; cell(row).append(url); cell(row, String(usage(d.id).length)); cell(row).append(button('Editar', () => openDestination(d.id))); $('destinations').append(row);
  });
  if (!count) emptyRow($('destinations'), 'Nenhum destino corresponde ao filtro.', 6);
  $('destination-count').textContent = `${count} de ${(cfg.catalog || []).length} destinos cadastrados.`;
}
function renderGroups() {
  $('groups').replaceChildren(); (cfg.groups || []).slice().sort().forEach(g => { const row = element('tr'); cell(row, g); cell(row, String(cfg.routes.filter(r => r.group === g).length)); cell(row, String((cfg.catalog || []).filter(d => d.group === g).length)); const actions = cell(row); actions.append(button('Editar nome', () => openGroup(g)), button('Ver rotas', () => { $('route-group-filter').value = g; render(); location.hash = 'rotas'; switchView('rotas'); }), button('Ver destinos', () => { $('destination-group-filter').value = g; renderCatalog(); location.hash = 'destinos'; switchView('destinos'); })); $('groups').append(row); });
  if (!cfg.groups?.length) emptyRow($('groups'), 'Nenhum grupo cadastrado.', 4);
}
function refresh() { updateGroups(); updateDomains(); render(); renderCatalog(); renderGroups(); }
async function saveConfig(next) { cfg = await api('/api/routes', { method: 'POST', body: JSON.stringify(next) }); refresh(); }
function showDNS(host) { $('dns-instructions').hidden = false; $('dns-host').textContent = `Domínio: ${host}`; const d = domains.dns; $('dns-record').textContent = `Tipo: ${d.type} | Nome: ${host} | Conteúdo: ${d.value} | TTL: ${d.ttl} | Proxy: ${d.proxy}`; $('dns-notice').textContent = d.notice; }
function updateDomains() {
  const selected = $('domain').value, hosts = [...new Set([...domains.domains, ...cfg.routes.map(r => r.host)])].sort();
  $('domain').replaceChildren(new Option('Todos os domínios', '')); hosts.forEach(d => $('domain').add(new Option(d, d))); $('domain').value = selected; $('domain-list').replaceChildren();
  hosts.forEach(host => {
    const row = element('article', undefined, 'domain-card'), info = element('div', undefined, 'route-info'), status = checks.get(host);
    info.append(element('strong', host), element('div', status ? `${status.verified ? 'Verificado' : 'Pendente'} — ${status.message}` : 'Ainda não verificado', status?.verified ? 'domain-status verified' : 'domain-status pending'));
    if (status?.checked_at) info.append(element('div', `Última verificação: ${new Date(status.checked_at).toLocaleString('pt-BR')} — resultado salvo; Verificar consulta online novamente.`, 'hint'));
    const actions = element('div', undefined, 'actions'), dns = button('Ver instruções DNS', () => showDNS(host));
    const verify = button('Verificar', async () => {
      verify.disabled = true; verify.textContent = 'Verificando…';
      try { const result = await api('/api/domains/check', { method: 'POST', body: JSON.stringify({ host }) }); if (result.host !== host || typeof result.verified !== 'boolean') throw new Error('Resposta de verificação não corresponde ao domínio.'); checks.set(host, result); updateDomains(); }
      catch (error) { message(error.message, true); verify.disabled = false; verify.textContent = 'Verificar'; }
    }, status?.verified ? 'verified' : 'secondary');
    actions.append(dns, verify); row.append(info, actions); $('domain-list').append(row);
  });
  if (!hosts.length) $('domain-list').append(element('p', 'Nenhum domínio cadastrado.', 'hint'));
}
$('domain-form').onsubmit = async event => {
  event.preventDefault(); $('add-domain').disabled = true;
  try { const added = $('new-domain').value.split(',').map(v => v.trim().toLowerCase()); if (added.some(v => !v)) throw new Error('Informe domínios válidos, sem itens vazios.'); const next = [...new Set([...domains.domains, ...cfg.routes.map(r => r.host), ...added])]; domains = await api('/api/domains', { method: 'POST', body: JSON.stringify({ revision: domains.revision, domains: next }) }); $('new-domain').value = ''; updateDomains(); showDNS(added[0]); message('Domínio cadastrado. Configure o DNS; nenhum DNS foi alterado automaticamente.'); }
  catch (error) { message(error.message, true); } finally { $('add-domain').disabled = false; }
};
function addTarget(url = '', weight = 50, id = '') {
  const row = element('div', undefined, 'target-row'), pickerLabel = element('label', 'Destino cadastrado'), picker = element('select'), uLabel = element('label', 'URL de destino'), u = element('input'), wLabel = element('label', 'Percentual (%)'), w = element('input');
  picker.className = 'target-picker'; fillPicker(picker, id); picker.onchange = () => { const d = catalogByID(picker.value); if (d) u.value = d.url; u.readOnly = !!d; }; pickerLabel.append(picker);
  u.type = 'url'; u.className = 'target-url'; u.value = url; u.readOnly = !!id; u.placeholder = 'https://wantabrand.com/...'; w.type = 'number'; w.className = 'target-weight'; w.min = '1'; w.max = '100'; w.step = '1'; w.value = weight;
  u.required = w.required = $('weighted').checked; const remove = button('Remover da rota', () => row.remove()); uLabel.append(u); wLabel.append(w); row.append(pickerLabel, uLabel, wLabel, remove); $('targets').append(row);
}
function toggleWeighted() { const active = $('weighted').checked; $('weighted-destinations').hidden = !active; $('single-destination').hidden = active; $('destination').required = !active; document.querySelectorAll('.target-url,.target-weight').forEach(i => { i.required = active; }); if (active && !$('targets').children.length) { addTarget($('destination').value, 50, $('destination-picker').value); addTarget('', 50); } }
$('weighted').onchange = toggleWeighted; $('add-target').onclick = () => addTarget();
$('destination-picker').onchange = () => { const d = catalogByID($('destination-picker').value); if (d) $('destination').value = d.url; $('destination').readOnly = !!d; };
function openEditor(index = -1) {
  editing = index; const r = index >= 0 ? cfg.routes[index] : { host: $('domain').value, path: '', destination: '', name: '' };
  $('host').value = r.host; $('path').value = r.path; $('route-name').value = r.name || ''; $('route-group').value = r.group || ''; $('destination').value = r.destination || ''; fillPicker($('destination-picker'), r.destination_id || ''); $('destination').readOnly = !!r.destination_id; $('host').readOnly = $('path').readOnly = index >= 0;
  $('targets').replaceChildren(); $('weighted').checked = !!r.destinations?.length; if (r.destinations) r.destinations.forEach(t => addTarget(t.url, t.weight, t.destination_id)); toggleWeighted();
  $('editor-title').textContent = index >= 0 ? 'Editar rota' : 'Nova rota'; $('editor').hidden = false; $('editor').scrollIntoView({block:'nearest'}); (index >= 0 ? $('route-name') : $('host')).focus();
}
$('new').onclick = () => openEditor(); $('cancel').onclick = () => { $('editor').hidden = true; }; $('search').oninput = render; $('domain').onchange = render; $('route-group-filter').onchange = render;
$('sort-routes').onclick = () => { routeAscending = !routeAscending; render(); };
$('route-form').onsubmit = async event => {
  event.preventDefault(); $('save').disabled = true;
  try {
    const route = { host: $('host').value.trim().toLowerCase(), path: $('path').value.trim(), name: $('route-name').value.trim(), group: $('route-group').value };
    if ($('weighted').checked) {
      route.destinations = [...$('targets').children].map(row => ({ url: row.querySelector('.target-url').value.trim(), weight: Number(row.querySelector('.target-weight').value), destination_id: row.querySelector('.target-picker').value }));
      if (!route.destinations.length || route.destinations.some(t => !t.url || !Number.isInteger(t.weight) || t.weight < 1 || t.weight > 100) || route.destinations.reduce((sum, t) => sum + t.weight, 0) !== 100) throw new Error('Informe os destinos e percentuais inteiros com soma de 100%.');
    } else { route.destination = $('destination').value.trim(); route.destination_id = $('destination-picker').value; }
    const routes = cfg.routes.map(r => ({ ...r })); if (editing >= 0) routes[editing] = route; else routes.push(route);
    await saveConfig({ ...cfg, routes }); $('editor').hidden = true; message('Rota salva e aplicada. O link público foi preservado.');
  } catch (error) { message(error.message + ' Se outro usuário alterou a configuração, recarregue antes de salvar.', true); } finally { $('save').disabled = false; }
};
function openDestination(id = '') {
  editingDestination = id; const d = catalogByID(id); $('destination-name').value = d?.name || ''; $('catalog-url').value = d?.url || ''; $('catalog-group').value = d?.group || ''; $('destination-impact').textContent = id ? `Usado em ${usage(id).length} rota(s). Alterar a URL atualiza todas essas rotas; será solicitada confirmação.` : 'Pode ser reutilizado nas rotas. Cadastrar não altera rotas existentes.'; $('destination-title').textContent = id ? 'Editar destino' : 'Novo destino'; $('destination-editor').hidden = false; $('destination-name').focus();
}
$('new-destination').onclick = () => openDestination(); $('cancel-destination').onclick = () => { $('destination-editor').hidden = true; }; $('destination-search').oninput = renderCatalog; $('destination-group-filter').onchange = renderCatalog;
$('sort-destinations').onclick = () => { destinationAscending = !destinationAscending; renderCatalog(); };
$('destination-form').onsubmit = async event => {
  event.preventDefault(); $('save-destination').disabled = true;
  try {
    const old = catalogByID(editingDestination), d = { id: editingDestination || 'd-' + crypto.randomUUID(), name: $('destination-name').value.trim(), url: $('catalog-url').value.trim(), group: $('catalog-group').value }, affected = old && old.url !== d.url ? usage(d.id).length : 0;
    if (affected && !window.confirm(`Alterar esta URL atualizará ${affected} rota(s). Os links públicos e percentuais serão preservados. Confirma?`)) return;
    const catalog = (cfg.catalog || []).map(item => item.id === d.id ? d : item); if (!old) catalog.push(d);
    const routes = cfg.routes.map(r => { const next = {...r}; if (r.destination_id === d.id) next.destination = d.url; if (r.destinations) next.destinations = r.destinations.map(t => t.destination_id === d.id ? {...t, url:d.url} : {...t}); return next; });
    await saveConfig({...cfg, catalog, routes}); $('destination-editor').hidden = true; message('Destino salvo.' + (affected ? ` ${affected} rota(s) atualizada(s).` : ''));
  } catch (error) { message(error.message + ' Recarregue se a configuração foi alterada por outro usuário.', true); } finally { $('save-destination').disabled = false; }
};
function openGroup(name = '') {
  editingGroup = name; $('group-name').value = name;
  $('group-editor-title').textContent = name ? 'Editar nome do grupo' : 'Criar grupo';
  $('save-group').textContent = name ? 'Salvar nome' : 'Criar grupo';
  $('cancel-group').hidden = $('group-impact').hidden = !name;
  $('group-impact').textContent = name ? `O novo nome será aplicado a ${cfg.routes.filter(r => r.group === name).length} rota(s) e ${(cfg.catalog || []).filter(d => d.group === name).length} destino(s), sem mudar links ou percentuais.` : '';
  if (name) { $('group-form').scrollIntoView({block:'nearest'}); $('group-name').focus(); }
}
$('cancel-group').onclick = () => openGroup();
$('group-form').onsubmit = async event => {
  event.preventDefault(); $('save-group').disabled = true;
  try {
    const name = $('group-name').value.trim(), old = editingGroup;
    if (!name) throw new Error('Informe o nome do grupo.');
    if (cfg.groups?.includes(name) && name !== old) throw new Error('Já existe um grupo com esse nome.');
    if (old && !cfg.groups?.includes(old)) throw new Error('Grupo alterado por outro usuário. Recarregue antes de salvar.');
    if (old === name) { openGroup(); message('Nome mantido.'); return; }
    const groups = old ? cfg.groups.map(g => g === old ? name : g) : [...(cfg.groups || []), name];
    const routes = cfg.routes.map(r => r.group === old && old ? {...r, group:name} : r);
    const catalog = (cfg.catalog || []).map(d => d.group === old && old ? {...d, group:name} : d);
    const selectedGroups = ['route-group-filter','destination-group-filter','route-group','catalog-group'].map(id => [id, $(id).value]);
    await saveConfig({...cfg, groups, routes, catalog});
    if (old) { selectedGroups.forEach(([id,value]) => { if (value === old) $(id).value = name; }); render(); renderCatalog(); }
    openGroup(); message(old ? 'Nome do grupo atualizado. Links, destinos e percentuais preservados.' : 'Grupo criado.');
  } catch (error) { message(error.message, true); } finally { $('save-group').disabled = false; }
};
$('logout').onclick = async () => { try { await api('/logout', { method: 'POST', body: '{}' }); location.assign('/login'); } catch (error) { message(error.message, true); } };
(async () => { try { const me = await api('/api/me'); csrf = me.csrf; $('username').textContent = me.username; [cfg, domains] = await Promise.all([api('/api/routes'), api('/api/domains')]); Object.entries(domains.checks || {}).forEach(([host, result]) => { if (result.host === host && typeof result.verified === 'boolean') checks.set(host, result); }); refresh(); } catch (error) { message(error.message, true); } })();
