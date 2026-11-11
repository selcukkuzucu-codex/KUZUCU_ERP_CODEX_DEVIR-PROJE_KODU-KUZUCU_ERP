/* KUZUCU ERP: çoklu küpe ile işlem seçimi ve hayvan bazında toplu kayıt. */
(() => {
  const prefix = '/api/animal-operations';
  let rows = [], warnings = [], groups = [], requestSerial = 0, lookupTimer = null, saving = false;
  const e = value => escapeHTML(value ?? '');
  const parts = value => String(value).split(/[,;\n]+/).map(x => x.trim()).filter(Boolean);
  const reasonNames = { slaughter: 'Kesim', death: 'Ölüm', sale: 'Satış' };
  const can = scope => right(scope);
  function modes() {
    return [
      ...(can('hayvanlar.tartim.create') ? [['weighing', 'Tartım Ekle']] : []),
      ...(can('hayvanlar.kart.edit') ? [['transfer', 'Grup Değiştir'], ['exit', 'Hayvan Çıkışı']] : []),
      ...(can('hayvanlar.kart.create') ? [['create', 'Yeni Hayvan Girişi']] : []),
    ];
  }
  const selectedMode = () => document.getElementById('animalOpsMode')?.value || 'exit';
  function groupOptions(value = '') {
    return '<option value="">Grup seçin</option>' + groups.map(p => `<option value="${p.id}" ${String(p.id) === String(value) ? 'selected' : ''}>${e(p.code)}</option>`).join('');
  }
  function paintRows() {
    const mode = selectedMode(), target = document.getElementById('animalOpsRows');
    if (!target) return;
    document.getElementById('animalOpsTagLabel').textContent = mode === 'create' ? 'Yeni hayvanların TR küpe numaraları' : 'TR veya işletme küpe numaraları';
    document.getElementById('animalOpsExitFields').style.display = mode === 'exit' ? '' : 'none';
    document.getElementById('animalOpsDateLabel').textContent = mode === 'create' ? 'Giriş tarihi' : mode === 'exit' ? 'Çıkış tarihi' : mode === 'transfer' ? 'Grup değişim tarihi' : 'Tartım tarihi';
    document.getElementById('animalOpsWarnings').innerHTML = warnings.map(w => `<p class="warn">${e(w.tag ? w.tag + ': ' : '')}${e(w.message)}</p>`).join('');
    const extraHeaders = mode === 'create' ? '<th>İşletme Küpe No</th><th>Grup No</th><th>Giriş kilosu (kg)</th><th>Irk</th><th>Cinsiyet</th><th>Doğum tarihi</th>'
      : mode === 'transfer' ? '<th>Yeni Grup No</th>' : '<th>' + (mode === 'exit' ? 'Çıkış kilosu (kg)' : 'Tartım kilosu (kg)') + '</th>';
    target.innerHTML = `<p><strong>${rows.length} hayvan listede</strong></p><div class="scroll"><table><thead><tr><th>TR Küpe No</th>${mode === 'create' ? '' : '<th>İşletme Küpe No</th><th>Grup No</th>'}${extraHeaders}<th>İşlem</th></tr></thead><tbody>${rows.map((row, index) => {
      let fields;
      if (mode === 'create') fields = `<td><input data-row="${index}" data-field="farm_ear_tag" value="${e(row.farm_ear_tag)}" maxlength="60" aria-label="İşletme Küpe No"></td><td><select data-row="${index}" data-field="pen_id" aria-label="Grup No">${groupOptions(row.pen_id)}</select></td><td><input data-row="${index}" data-field="entry_weight_kg" value="${e(row.entry_weight_kg)}" inputmode="decimal" aria-label="Giriş kilosu"></td><td><input data-row="${index}" data-field="breed" value="${e(row.breed || 'Belirtilmedi')}" maxlength="80" aria-label="Irk"></td><td><select data-row="${index}" data-field="sex" aria-label="Cinsiyet"><option value="">Belirtilmedi</option><option value="male" ${row.sex === 'male' ? 'selected' : ''}>Erkek</option><option value="female" ${row.sex === 'female' ? 'selected' : ''}>Dişi</option></select></td><td><input data-row="${index}" data-field="birth_date" type="date" value="${e(row.birth_date)}" aria-label="Doğum tarihi"></td>`;
      else if (mode === 'transfer') fields = `<td><select data-row="${index}" data-field="new_pen_id" aria-label="Yeni Grup No">${groupOptions(row.new_pen_id)}</select></td>`;
      else fields = `<td><input data-row="${index}" data-field="operation_weight" value="${e(row.operation_weight)}" inputmode="decimal" placeholder="Örn. 350,5" aria-label="${mode === 'exit' ? 'Çıkış' : 'Tartım'} kilosu"></td>`;
      return `<tr><td>${e(row.tr_ear_tag)}</td>${mode === 'create' ? '' : `<td>${e(row.farm_ear_tag || '—')}</td><td>${e(row.group_no || '—')}</td>`}${fields}<td><button type="button" class="secondary-action" data-animal-ops-remove="${index}">Listeden Çıkar</button></td></tr>`;
    }).join('') || `<tr><td colspan="9">Küpe numaralarını girip hayvanları listeleyin.</td></tr>`}</tbody></table></div>`;
    target.querySelectorAll('[data-field]').forEach(input => {
      const update = () => { rows[+input.dataset.row][input.dataset.field] = input.value; };
      input.oninput = update; input.onchange = update;
    });
    target.querySelectorAll('[data-animal-ops-remove]').forEach(button => button.onclick = () => {
      const removed = rows.splice(+button.dataset.animalOpsRemove, 1)[0];
      const aliases = [removed.tr_ear_tag, removed.farm_ear_tag, removed.input_tag].filter(Boolean).map(value => value.toLowerCase());
      const input = document.getElementById('animalOpsTags');
      input.value = parts(input.value).filter(value => !aliases.includes(value.toLowerCase())).join(', ');
      ++requestSerial; paintRows();
    });
  }
  async function resolveList() {
    const serial = ++requestSerial, mode = selectedMode();
    const text = document.getElementById('animalOpsTags').value.trim();
    if (!text) { rows = []; warnings = []; paintRows(); return true; }
    try {
      const result = await api(prefix + '/lookup', { method: 'POST', body: JSON.stringify({ tags: text, active_only: mode !== 'create' }) });
      if (serial !== requestSerial) return false;
      const previous = rows;
      if (mode === 'create') {
        const tokens = parts(text), seen = new Set();
        warnings = [];
        rows = [];
        for (const tag of tokens) {
          const key = tag.toLowerCase();
          if (seen.has(key)) { warnings.push({ tag, message: 'Bu numara listede yineleniyor.' }); continue; }
          seen.add(key);
          const match = result.rows.find(a => [a.tr_ear_tag, a.farm_ear_tag].some(x => x?.toLowerCase() === key));
          const ambiguity = result.warnings.find(w => w.tag === tag && w.code !== 'unknown');
          if (match || ambiguity) { warnings.push({ tag, message: 'Bu küpe zaten kullanılıyor veya belirsiz; yeni hayvan için kullanılamaz.' }); continue; }
          const old = previous.find(a => a.tr_ear_tag === tag);
          rows.push(old || { tr_ear_tag: tag, farm_ear_tag: '', breed: 'Belirtilmedi' });
        }
      } else {
        warnings = result.warnings;
        rows = result.rows.map(a => ({ ...a, ...(previous.find(old => old.id === a.id) || {}), id: a.id }));
      }
      paintRows();
      return true;
    } catch (error) {
      if (serial === requestSerial) { warnings = [{message: 'Küpe listesi doğrulanamadı. Yeniden listeleyin.'}]; paintRows(); message(error.message, true); }
      return false;
    }
  }
  async function loadHistory() {
    const target = document.getElementById('animalOpsExitHistory');
    if (!target || !can('reports.animals.view')) return;
    const form = document.getElementById('animalOpsHistoryForm');
    const query = new URLSearchParams([...new FormData(form)].filter(([, value]) => value));
    const result = await api(prefix + '/exits?' + query);
    target.innerHTML = `<p>${result.count} çıkış kaydı</p><div class="scroll"><table><thead><tr><th>Tarih</th><th>TR Küpe No</th><th>İşletme Küpe No</th><th>Grup No</th><th>Çıkış Nedeni</th><th>Nereye Gittiği</th><th>Çıkış kg</th></tr></thead><tbody>${result.rows.map(r => `<tr><td>${dateTr(r.exit_date)}</td><td>${e(r.tr_ear_tag)}</td><td>${e(r.farm_ear_tag || '—')}</td><td>${e(r.group_no)}</td><td>${e(r.reason_label)}</td><td>${e(r.destination || 'Belirtilmedi')}</td><td>${r.exit_kg == null ? 'Bilinmiyor' : fmtDbQuantity(r.exit_kg)}</td></tr>`).join('') || '<tr><td colspan="7">Çıkış kaydı yok.</td></tr>'}</tbody></table></div>`;
  }
  async function html(exitOnly) {
    clearTimeout(lookupTimer); ++requestSerial; rows = []; warnings = [];
    groups = can('hayvanlar.kart.create') || can('hayvanlar.kart.edit') ? await api(prefix + '/groups') : [];
    const available = exitOnly ? modes().filter(([key]) => key === 'exit') : modes();
    if (!available.length) return '<h1>Toplu Hayvan İşlemleri</h1><p>Bu işlemler için yetkiniz bulunmuyor.</p>';
    const options = available.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
    return `<h1>${exitOnly ? 'Toplu Hayvan Çıkışı' : 'Toplu Hayvan İşlemleri'}</h1><p class="sub">Küpe numaralarını virgül ve boşlukla yazın. Her hayvanı ve bilgilerini alt listede kontrol ettikten sonra toplu kaydedin.</p><div class="panel"><label>İşlem Adı<select id="animalOpsMode">${options}</select></label><form id="animalOpsForm"><label><span id="animalOpsDateLabel">Tarih</span><input type="date" id="animalOpsDate" value="${localToday()}" required></label><div id="animalOpsExitFields" style="display:none"><label>Çıkış nedeni<select id="animalOpsReason"><option value="slaughter">Kesim</option><option value="death">Ölüm</option><option value="sale">Satış</option></select></label><label>Nereye gittiği<input id="animalOpsDestination" maxlength="240" placeholder="Firma, kesimhane veya açıklama"></label><p class="muted">Ölümde bilinmeyen kilo boş bırakılabilir; kesim ve satışta her hayvanın çıkış kilosu gereklidir.</p></div><label style="flex:1 1 100%"><span id="animalOpsTagLabel">TR veya işletme küpe numaraları</span><textarea id="animalOpsTags" rows="2" placeholder="TR001, TR002, 0003"></textarea></label><button type="button" class="secondary-action" id="animalOpsLookup">Hayvanları Listele</button><div id="animalOpsWarnings" style="flex-basis:100%"></div><div id="animalOpsRows" style="width:100%;min-width:0"></div><button type="submit">Toplu Kaydet</button></form></div>${can('reports.animals.view') ? `<div class="panel"><h2>Hayvan Çıkış Geçmişi</h2><form id="animalOpsHistoryForm"><label>Başlangıç<input name="date_from" type="date"></label><label>Bitiş<input name="date_to" type="date"></label><label>Çıkış nedeni<select name="reason"><option value="">Tümü</option>${Object.entries(reasonNames).map(([value, label]) => `<option value="${value}">${label}</option>`).join('')}</select></label><button>Sorgula</button>${can('reports.animals.export') ? '<button type="button" class="secondary-action" id="animalOpsCsv">CSV / Excel İndir</button>' : ''}</form><div id="animalOpsExitHistory"></div></div>` : ''}`;
  }
  async function bind() {
    const form = document.getElementById('animalOpsForm');
    if (!form) return;
    form.noValidate = true;
    const modeSelect = document.getElementById('animalOpsMode');
    modeSelect.onchange = async () => { ++requestSerial; rows = []; warnings = []; paintRows(); if (document.getElementById('animalOpsTags').value.trim()) await resolveList(); };
    document.getElementById('animalOpsLookup').onclick = resolveList;
    document.getElementById('animalOpsTags').oninput = () => { ++requestSerial; clearTimeout(lookupTimer); lookupTimer = setTimeout(resolveList, 550); };
    form.onsubmit = async event => {
      event.preventDefault(); clearTimeout(lookupTimer);
      if (saving) return;
      saving = true;
      const saveButton = form.querySelector('button[type="submit"]');
      saveButton.disabled = true;
      try {
        if (!await resolveList()) return;
        if (!rows.length) throw Error('Önce en az bir hayvanı listeye ekleyin.');
        if (warnings.length) throw Error('Küpe listesindeki uyarıları düzeltmeden toplu kayıt yapılamaz.');
        const mode = selectedMode(), date = document.getElementById('animalOpsDate').value;
        if (!date) throw Error('İşlem tarihini seçin.');
        let endpoint, payload;
        if (mode === 'create') {
          endpoint = '/bulk-create'; payload = { arrival_date: date, entries: rows.map(r => ({ tr_ear_tag: r.tr_ear_tag, farm_ear_tag: r.farm_ear_tag || null, birth_date: r.birth_date || null, sex: r.sex || null, breed: r.breed || 'Belirtilmedi', entry_weight_kg: canonicalQuantity(r.entry_weight_kg || ''), pen_id: Number(r.pen_id) })) };
        } else if (mode === 'transfer') {
          endpoint = '/bulk-transfer'; payload = { transferred_on: date, entries: rows.map(r => ({ animal_id: r.id, pen_id: Number(r.new_pen_id) })) };
        } else if (mode === 'exit') {
          endpoint = '/bulk-exit'; payload = { exit_date: date, reason: document.getElementById('animalOpsReason').value, destination: document.getElementById('animalOpsDestination').value, entries: rows.map(r => ({ animal_id: r.id, exit_kg: String(r.operation_weight || '').trim() ? canonicalQuantity(r.operation_weight) : null })) };
        } else {
          endpoint = '/bulk-weighings'; payload = { measured_at: date, entries: rows.map(r => ({ animal_id: r.id, weight_kg: canonicalQuantity(r.operation_weight || '') })) };
        }
        if (!confirm(`${rows.length} hayvan için işlemler birlikte kaydedilsin mi?`)) return;
        const result = await api(prefix + endpoint, { method: 'POST', body: JSON.stringify(payload) });
        message(result.message); ++requestSerial; rows = []; warnings = []; document.getElementById('animalOpsTags').value = ''; paintRows(); await loadHistory();
      } catch (error) { message(error.message, true); }
      finally { saving = false; saveButton.disabled = false; }
    };
    const history = document.getElementById('animalOpsHistoryForm');
    if (history) history.onsubmit = async event => { event.preventDefault(); try { await loadHistory(); } catch (error) { message(error.message, true); } };
    const csv = document.getElementById('animalOpsCsv');
    if (csv) csv.onclick = () => { const query = new URLSearchParams([...new FormData(history)].filter(([, value]) => value)); window.open(prefix + '/exits.csv?' + query, '_blank', 'noopener'); };
    paintRows(); await loadHistory();
  }
  window.v15Screens = { ...(window.v15Screens || {}), topluhayvan: { html: () => html(false), bind }, hayvancikis: { html: () => html(true), bind } };
})();
