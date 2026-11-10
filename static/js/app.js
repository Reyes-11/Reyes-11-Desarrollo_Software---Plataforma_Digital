const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let naps = [];

async function api(url, opt = {}) {
  const r = await fetch(url, {headers: {'Content-Type': 'application/json'}, ...opt});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || 'Error del servidor');
  return d;
}
function say(text, ok = false) { const m = $('#msg'); m.textContent = text; m.className = ok ? 'good' : 'err'; }
const run = fn => async (...a) => { try { await fn(...a); } catch (e) { say(e.message); } };
const tag = s => s ? `<span class="tag ${esc(s)}">${esc(s)}</span>` : '<span class="tag">Sin auditar</span>';
const form = f => Object.fromEntries(new FormData(f));

document.querySelectorAll('nav button').forEach(b => b.onclick = run(async () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('main > section').forEach(s => s.hidden = s.id !== b.dataset.tab);
  say('');
  await load(b.dataset.tab);
}));

async function load(tab) {
  naps = await api('/api/naps');
  if (tab === 'dash') {
    const s = await api('/api/stats');
    const occ = s.ports_total ? Math.round(100 * s.ports_used / s.ports_total) : 0;
    $('#stats').innerHTML = [['', s.naps, 'NAP registradas'], ['', occ + '%', 'Ocupación de puertos'], ['', s.audits, 'Auditorías'],
      ['ok', s.ok, 'NAP en estado OK'], ['warn', s.alerta, 'NAP en alerta'], ['crit', s.critico, 'NAP críticas']]
      .map(([c, v, l]) => `<div class="stat ${c}"><b>${v}</b>${l}</div>`).join('');
  } else if (tab === 'naps') renderNaps();
  else if (tab === 'audit') $('#auditNap').innerHTML = naps.map(n => `<option value="${n.id}">${esc(n.code)} · ${esc(n.sector)}</option>`).join('');
  else if (tab === 'hist') await renderHist();
}

function renderNaps() {
  const q = $('#q').value.toLowerCase();
  const rows = naps.filter(n => (n.code + n.sector).toLowerCase().includes(q));
  $('#napTable').innerHTML = rows.length ? `<tr><th>Código</th><th>Sector</th><th>Splitter</th><th>Puertos</th><th>OLT dBm</th><th>Km</th><th>Estado</th><th>Última auditoría</th><th></th></tr>` +
    rows.map(n => `<tr><td>${esc(n.code)}</td><td>${esc(n.sector)}</td><td>${n.splitter}</td><td>${n.ports_used}/${n.ports_total}</td><td>${n.olt_tx_dbm}</td><td>${n.distance_km}</td><td>${n.state}</td><td>${tag(n.last_status)}</td>
    <td><button data-edit="${n.id}">Editar</button> <button data-del="${n.id}">Eliminar</button></td></tr>`).join('')
    : '<tr><td class="empty">No hay NAP que coincidan. Registra una con el botón “Registrar NAP”.</td></tr>';
}
$('#q').oninput = renderNaps;

$('#napTable').onclick = run(async e => {
  const t = e.target;
  if (t.dataset.edit) {
    const n = naps.find(x => x.id == t.dataset.edit), f = $('#napForm');
    for (const k in n) if (f.elements[k]) f.elements[k].value = n[k];
    f.hidden = false; f.scrollIntoView();
  }
  if (t.dataset.del && confirm('¿Eliminar esta NAP y todas sus auditorías?')) {
    await api('/api/naps/' + t.dataset.del, {method: 'DELETE'});
    say('NAP eliminada', true); await load('naps');
  }
});
$('#newNap').onclick = () => { $('#napForm').reset(); $('#napForm').elements.id.value = ''; $('#napForm').hidden = false; };
$('#cancelNap').onclick = () => $('#napForm').hidden = true;
$('#napForm').onsubmit = run(async e => {
  e.preventDefault();
  const d = form(e.target), id = d.id;
  await api(id ? '/api/naps/' + id : '/api/naps', {method: id ? 'PUT' : 'POST', body: JSON.stringify(d)});
  e.target.hidden = true; say(id ? 'NAP actualizada' : 'NAP registrada', true); await load('naps');
});

async function showResult(r, saved) {
  const box = $('#result');
  box.hidden = false; box.className = 'result ' + (r.status || '');
  box.innerHTML = `<p><b>Potencia esperada:</b> ${r.expected_dbm} dBm${r.loss_db != null ? ` (pérdida teórica ${r.loss_db} dB)` : ''}</p>` +
    (saved ? `<p>${tag(r.status)} ${esc(r.diagnosis)}</p>` : '');
}
$('#calcBtn').onclick = run(async () => {
  const d = form($('#auditForm'));
  showResult(await api('/api/calc', {method: 'POST', body: JSON.stringify(d)}), false);
});
$('#auditForm').onsubmit = run(async e => {
  e.preventDefault();
  const r = await api('/api/audits', {method: 'POST', body: JSON.stringify(form(e.target))});
  showResult(r, true); say('Auditoría guardada', true);
});

async function renderHist() {
  const st = $('#fStatus').value;
  const rows = await api('/api/audits' + (st ? '?status=' + st : ''));
  $('#histTable').innerHTML = rows.length ? `<tr><th>Fecha</th><th>NAP</th><th>Sector</th><th>Técnico</th><th>Rx dBm</th><th>Esperada</th><th>Estado</th><th>Diagnóstico</th></tr>` +
    rows.map(a => `<tr><td>${a.created_at}</td><td>${esc(a.code)}</td><td>${esc(a.sector)}</td><td>${esc(a.technician)}</td><td>${a.rx_dbm}</td><td>${a.expected_dbm}</td><td>${tag(a.status)}</td><td class="wrap">${esc(a.diagnosis)}</td></tr>`).join('')
    : '<tr><td class="empty">Aún no hay auditorías. Registra la primera en “Nueva auditoría”.</td></tr>';
}
$('#fStatus').onchange = run(renderHist);
run(load)('dash');
