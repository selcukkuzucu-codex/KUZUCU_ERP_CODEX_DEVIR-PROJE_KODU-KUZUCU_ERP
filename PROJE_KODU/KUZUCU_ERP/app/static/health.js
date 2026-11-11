/* Health module front-end. API is defined by the existing KUZUCU ERP shell. */
let healthReportDate='';
let healthCaseFilter='';
let healthLastCases=[];
let healthLastCatalog={medications:[],treatments:[]};
const healthTypeNames={treatment:'Tedavi',vaccination:'Aşı',observation:'Gözlem'};
const healthOutcomes={recovered:'İyileşti',improved:'İyileşme var',unchanged:'Değişmedi',worsened:'Kötüleşti',unknown:'Belirsiz'};
const healthStatuses={active:'Devam ediyor',closed:'Kapandı'};
const healthDailyStatuses={due:'Yapılacak',done:'Uygulandı',partially_done:'Kısmen uygulandı',awaiting_approval:'Veteriner onayı bekleniyor',review_expired:'Plan süresi doldu / kontrol gerekli'};
const healthResponseLabels={improved:'İyileşme var',unchanged:'Değişiklik yok',worsened:'Kötüleşme var',not_evaluated:'Değerlendirilmedi'};
const hu=v=>escapeHTML(v??'');
function healthCaseRows(items){
 if(!items.length)return '<tr><td colspan="9" class="muted">Henüz sağlık kaydı bulunmuyor.</td></tr>';
 return items.map(r=>`<tr><td>${hu(r.ear_tag)}${r.farm_ear_tag?`<div class="health-small">İşletme: ${hu(r.farm_ear_tag)}</div>`:''}<div class="health-small">Grup: ${hu(r.pen||'—')}</div></td><td>${hu(healthTypeNames[r.record_type]||'Sağlık kaydı')}</td><td><strong>${hu(r.condition_name)}</strong><div class="health-small">${r.treatment_name?'Tedavi: '+hu(r.treatment_name)+' · ':''}${hu(r.symptoms)}</div></td><td>${hu(r.product_name||'—')}<div class="health-small">${hu(r.dosage_text)}</div></td><td>${dateTr(r.start_date)} - ${dateTr(r.planned_end_date)}</td><td>${r.vet_approved?'Kayıtlı veteriner onayı':r.duration_days!=null?'Süreli sağlık planı':'Eski kayıt: onay bekliyor'}<div class="health-small">${hu(r.veterinarian)}</div></td><td><span class="health-tag ${r.status==='closed'?'':'warning'}">${hu(healthStatuses[r.status]||'Durum bilgisi yok')}</span><div class="health-small">${hu(healthOutcomes[r.outcome]||'')}</div></td><td>${hu(r.created_by||'Eski kayıt')}</td><td><div class="health-actions">${r.status==='active'?`<button class="secondary-action" data-health-edit="${r.id}">Düzenle</button><button class="secondary-action" data-health-log="${r.id}">Uygulama</button><button class="secondary-action" data-health-close="${r.id}">Sonuç / Kapat</button>`:''}<button class="secondary-action" data-health-history="${r.id}">Günlük Geçmiş</button></div></td></tr>`).join('');
}
function healthDailyTable(data){
 const counts=data.totals;
 const stat=(n,v)=>`<div class="stat"><strong>${v}</strong><span>${n}</span></div>`;
 const rows=data.cases.map(r=>`<tr><td>${hu(r.ear_tag)}${r.farm_ear_tag?`<div class="health-small">İşletme: ${hu(r.farm_ear_tag)}</div>`:''}<div class="health-small">Grup: ${hu(r.pen||'—')}</div></td><td>${hu(healthTypeNames[r.record_type]||'Sağlık kaydı')}</td><td>${hu(r.condition_name)}</td><td>${r.treatment_name?hu(r.treatment_name)+'<div class="health-small">':''}${hu(r.product_name||'—')}${r.treatment_name?'</div>':''}</td><td><span class="health-tag ${r.status==='review_expired'?'danger':r.status==='awaiting_approval'?'warning':''}">${hu(healthDailyStatuses[r.status]||'Durum bilgisi yok')} (${r.performed_count}/${r.applications_per_day})</span>${r.performed_by?`<div class="health-small">${hu(r.performed_by)}</div>`:''}</td><td>${['due','partially_done'].includes(r.status)?`<button type="button" class="secondary-action" data-health-log="${r.case_id}">Uygulama kaydet</button>`:'—'}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">Bu gün için açık sağlık takibi bulunmuyor.</td></tr>';
 const reminders=data.reminders.map(r=>`<tr><td>${hu(r.remind_time)}</td><td>${hu(r.category)}</td><td>${hu(r.title)}<div class="health-small">${hu(r.notes)}</div></td><td>${r.overdue?`<span class="health-tag warning">Gecikmiş (${dateTr(r.scheduled_for)})</span>`:'Bugün'}</td></tr>`).join('')||'<tr><td colspan="4" class="muted">Bu gün için bekleyen ajanda işi yok.</td></tr>';
 return `<div class="health-stats">${stat('Yapılacak',counts.due)}${stat('Uygulandı',counts.done)}${stat('Kısmen uygulandı',counts.partially_done)}${stat('Veteriner kontrolü',counts.review)}${stat('Onay bekleyen',counts.awaiting_approval)}${stat('Ajanda işi',counts.reminders)}</div><h4>Günlük sağlık uygulamaları</h4><div class="scroll"><table><thead><tr><th>Küpe / Grup</th><th>Tür</th><th>Hastalık / Durum</th><th>Plan / Ürün</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>${rows}</tbody></table></div><h4>Ajanda / Günlük işler</h4><div class="scroll"><table><thead><tr><th>Saat</th><th>Bölüm</th><th>Yapılacak iş</th><th>Durum</th></tr></thead><tbody>${reminders}</tbody></table></div>`;
}
function healthCatalogMarkup(catalog){
 const block=(kind,title,arr)=>`<div class="health-catalog-column"><h4>${title} (${arr.length})</h4><div class="health-catalog-tags">${arr.length?arr.map((n,i)=>`<button type="button" class="secondary-action" data-health-pick="${kind}" data-catalog-index="${i}" title="Forma seç">${hu(n)}</button>`).join(''):'<span class="muted">Henüz kayıt yok.</span>'}</div></div>`;
 return `<div class="health-catalog-columns">${block('treatment','Tedavi / protokoller',catalog.treatments)}${block('medication','İlaç / aşı adları',catalog.medications)}</div>`;
}
function healthCatalogOptions(arr){return arr.map(x=>`<option value="${hu(x)}"></option>`).join('')}
function bindHealthCatalogPicks(){
 document.querySelectorAll('[data-health-pick]').forEach(b=>b.onclick=()=>{
  const kind=b.dataset.healthPick,idx=Number(b.dataset.catalogIndex);
  const val=(kind==='medication'?healthLastCatalog.medications:healthLastCatalog.treatments)[idx];
  const form=document.getElementById('healthCaseForm');if(!form||!val)return;
  form.elements.namedItem(kind==='medication'?'product_name':'treatment_name').value=val;
  form.scrollIntoView({behavior:'smooth',block:'center'});
  document.getElementById('healthRepeatNotice').textContent='';
 });
}
async function refreshHealthCatalog(){
 healthLastCatalog=await api('/api/animal-health/catalog');
 const list=document.getElementById('healthCatalogItems');if(list)list.innerHTML=healthCatalogMarkup(healthLastCatalog);
 const meds=document.getElementById('healthMedicationNames');if(meds)meds.innerHTML=healthCatalogOptions(healthLastCatalog.medications);
 const treatments=document.getElementById('healthTreatmentNames');if(treatments)treatments.innerHTML=healthCatalogOptions(healthLastCatalog.treatments);
 bindHealthCatalogPicks();
}
function healthRepeatMessage(result){
 if(!result.warning)return '';
 const details=result.matches.map(x=>`${dateTr(x.last_application)} (${x.days_ago} gün önce), kayıt no ${x.case_id}, ${x.product_name}`).join(' · ');
 return `UYARI: Aynı hayvana son 10 gün içinde aynı ilaç uygulanmış! ${details}. Tekrar uygulamadan önce veteriner değerlendirmesi gereklidir.`;
}
async function checkHealthRepeat(data,exclude){
 if(!data.animal_id||!data.product_name||!data.start_date||data.record_type==='observation')return {warning:false,matches:[]};
 const q=new URLSearchParams({animal_id:String(data.animal_id),product_name:data.product_name,on:data.start_date});
 if(exclude)q.set('exclude_case_id',String(exclude));
 return await api('/api/animal-health/repeat-check?'+q);
}
function healthToday(){
 const parts=new Intl.DateTimeFormat('en-US',{timeZone:'Europe/Istanbul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
 const get=type=>parts.find(p=>p.type===type).value;return `${get('year')}-${get('month')}-${get('day')}`;
}
function healthPlanStart(form){const id=Number(form.elements.namedItem('case_id').value);return healthLastCases.find(r=>r.id===id)?.start_date||healthToday()}
function updateHealthPlanDates(form){
 const target=document.getElementById('healthPlanDates');if(!target)return;
 const start=healthPlanStart(form),days=Number(form.elements.namedItem('duration_days').value);
 if(!Number.isInteger(days)||days<=0){target.textContent='Tedavi süresini sıfırdan büyük tam gün olarak girin.';return}
 const end=new Date(start+'T00:00:00Z');end.setUTCDate(end.getUTCDate()+days-1);
 if(Number.isNaN(end.getTime())){target.textContent='Tedavi süresi geçerli tarih sınırlarını aşıyor.';return}
 target.textContent=`Başlangıç: ${dateTr(start)} · Bitiş: ${dateTr(end.toISOString().slice(0,10))} · ${days} gün. Gerçek uygulamaları ayrıca kaydedin.`;
}
async function healthScreenHtml(){
 if(!healthReportDate)healthReportDate=healthToday();
 const [animals,cases,settings,catalog]=await Promise.all([api('/api/animals'),api('/api/animal-health/cases'),api('/api/animal-health/print-settings'),api('/api/animal-health/catalog')]);
 healthLastCatalog=catalog;
 healthLastCases=cases;
 const animalOptions=animals.map(a=>`<option value="${Number(a.id)}">TR: ${hu(a.ear_tag)}${a.farm_ear_tag?' · İşletme: '+hu(a.farm_ear_tag):''}</option>`).join('');
 const visible=cases.filter(r=>[r.ear_tag,r.farm_ear_tag,r.condition_name,r.product_name,r.pen].some(x=>String(x||'').toLocaleLowerCase('tr-TR').includes(healthCaseFilter.toLocaleLowerCase('tr-TR'))));
 return `<h1>Hayvan Sağlığı / Tedavi ve Aşı Takibi</h1><p class="sub">Küpe bazlı sağlık geçmişi, günlük uygulamalar, veteriner kontrolü ve yazdırılabilir A4 iş listesi.</p>
 <div class="health-info"><strong>Sağlık planı ve uygulama kaydı ayrıdır:</strong> Yeni plan kayıt günü başlar ve girilen gün kadar listelenir. Listeye eklenmesi uygulamanın yapıldığı veya veteriner onayı verildiği anlamına gelmez. İlaç, doz ve süreyi program önermez; veteriner talimatına göre girin.</div>
 <div class="panel"><h3>İlaç ve Tedavi Seçim Listeleri</h3><p class="health-small">İsimler kaydettikçe otomatik birikir. İsterseniz önceden de ekleyebilirsiniz. Kayıtlı adların üzerine tıklayarak sağlık formuna seçebilirsiniz.</p><div id="healthCatalogItems">${healthCatalogMarkup(catalog)}</div><form id="healthCatalogAddForm" class="health-form"><label>Kategori<select name="kind"><option value="medication">İlaç / Aşı</option><option value="treatment">Tedavi / Protokol</option></select></label><label class="wide">Yeni ad<input name="name" maxlength="180" required placeholder="Kayıtlı listesine eklenecek ad"></label><button type="submit">Seçim Listesine Ekle</button></form></div>
 <div class="panel"><h3>Sağlık Kaydı / Tedavi Planı</h3>${!animals.length?'<p class="warn">Sağlık kaydı açmak için önce Padoklar ve Hayvanlar bölümünde en az bir hayvan oluşturun.</p>':`<form id="healthCaseForm" class="health-form"><input type="hidden" name="case_id"><label>TR / İşletme Küpe No<select name="animal_id" required aria-label="Sağlık kaydı için hayvan seçin">${animalOptions}</select></label><label>İşlem türü<select name="record_type"><option value="treatment">Tedavi</option><option value="vaccination">Aşı</option><option value="observation">Durum / gözlem</option></select></label><label>Hastalık / durum adı<input name="condition_name" maxlength="140" required placeholder="Örn. Solunum belirtileri"></label><label>Tedavi / protokol adı<input name="treatment_name" maxlength="180" list="healthTreatmentNames" autocomplete="off" placeholder="Kayıtlı tedaviyi seç veya yeni yaz"><datalist id="healthTreatmentNames">${healthCatalogOptions(catalog.treatments)}</datalist></label><label>İlaç / aşı adı<input name="product_name" maxlength="180" list="healthMedicationNames" autocomplete="off" placeholder="Kayıtlı ilacı seç veya yeni yaz"><datalist id="healthMedicationNames">${healthCatalogOptions(catalog.medications)}</datalist></label><label>Veterinerin yazdığı doz / uygulama<input name="dosage_text" maxlength="120" placeholder="Onaylı talimat"></label><label>Günlük uygulama sayısı<input type="number" name="applications_per_day" min="1" max="6" value="1" required></label><label>Tedavi Süresi (gün)<input type="number" name="duration_days" min="1" step="1" value="1" required aria-describedby="healthPlanDates"></label><p id="healthPlanDates" class="health-small health-plan-dates" aria-live="polite">Başlangıç kayıt günü, bitiş girilen süreye göre hesaplanır.</p><label class="wide">Sağlık<textarea name="notes" maxlength="1500" rows="2"></textarea></label><div id="healthRepeatNotice" class="health-repeat-notice" role="alert" aria-live="polite" style="display:none"></div><button id="healthCaseSave" type="submit">Sağlık Kaydını Oluştur</button><button id="healthCaseCancel" type="button" class="secondary-action" style="display:none">Düzenlemeyi iptal et</button></form>`}<p class="health-small">İlaç, doz ve süreyi veteriner talimatına göre girin. Planlanan günlük liste, gerçek uygulama kaydının yerine geçmez. Eski kayıtlardaki tıbbi bilgiler korunur.</p></div>
 <div class="panel"><h3>Sağlık Kayıtları</h3><div class="health-filters"><label>TR / İşletme Küpe No, hastalık veya ürün ara<input id="healthSearch" type="search" value="${hu(healthCaseFilter)}" placeholder="TR veya işletme küpesi, hastalık veya ürün"></label><label>Durum<select id="healthStatusFilter"><option value="">Tümü</option><option value="active">Devam edenler</option><option value="closed">Tamamlananlar</option></select></label></div><div class="scroll"><table><thead><tr><th>Küpe / Grup</th><th>Tür</th><th>Hastalık / durum</th><th>İlaç / aşı</th><th>Tarih</th><th>Plan bilgisi</th><th>Sonuç</th><th>Kaydeden</th><th>İşlem</th></tr></thead><tbody id="healthCaseRows">${healthCaseRows(visible)}</tbody></table></div><div id="healthLogPanel" class="health-panel" style="display:none"><h3 id="healthLogTitle">Günlük Uygulama Kaydı</h3><form id="healthLogForm" class="health-form"><input type="hidden" name="case_id"><label>Uygulama tarihi<input name="performed_on" type="date" required></label><label>Uygulayan personel<input name="performed_by" required maxlength="120"></label><label>Günlük durum<select name="response"><option value="not_evaluated">Değerlendirilmedi</option><option value="improved">İyileşme var</option><option value="unchanged">Değişiklik yok</option><option value="worsened">Kötüleşme var</option></select></label><label class="wide">Yapılan işlem / gözlem<textarea name="observation" maxlength="1200" rows="2" placeholder="Gerçekte yapılan uygulama ve gözlem"></textarea></label><button type="submit">Uygulamayı Kaydet</button><button type="button" class="secondary-action" id="healthLogCancel">Kapat</button></form><div id="healthLogHistory"></div></div><div id="healthClosePanel" class="health-panel" style="display:none"><h3>Tedavi / Sağlık Kaydını Kapat</h3><form id="healthCloseForm" class="health-form"><input type="hidden" name="case_id"><label>Sonuç<select name="outcome"><option value="recovered">İyileşti</option><option value="improved">İyileşme var</option><option value="unchanged">Değişmedi</option><option value="worsened">Kötüleşti</option><option value="unknown">Belirsiz</option></select></label><label>Kapanış tarihi<input type="date" name="closed_date" required></label><label class="wide">Tedavi sonucu / değerlendirme<textarea name="outcome_notes" maxlength="1500" rows="2" placeholder="Hayvanın son durumu"></textarea></label><button type="submit">Sonucu Kaydet ve Kapat</button><button type="button" class="secondary-action" id="healthCloseCancel">İptal</button></form></div></div>
 <div class="panel"><h3>Günlük Tedavi, Aşı ve Hatırlatma Listesi</h3><form id="healthDailyForm" class="health-form"><label>Liste tarihi<input type="date" name="on" required value="${healthReportDate}"></label><button type="submit">Listeyi Göster</button><button type="button" class="secondary-action" id="healthPdfBtn">A4 PDF İndir / Yazdır</button><button type="button" class="secondary-action" id="healthPrintNowBtn">Şimdi Yazıcıya Gönder</button></form><div id="healthDailyList" class="health-daily-preview"><p class="muted">Günlük liste hazırlanıyor...</p></div><p class="health-small">PDF dosyası Mac'te KUZUCU_ERP/raporlar/saglik klasörüne de kaydedilir. Fiziksel yazdırma için Mac'e tanıtılmış bir yazıcı gerekir.</p>
 <div class="health-panel"><h3>Otomatik Günlük Çıktı Ayarları</h3><form id="healthPrintSettings" class="health-form"><label>Her gün saat<input type="time" name="daily_time" required value="${hu(settings.daily_time)}"></label><label class="health-approval"><input type="checkbox" name="auto_generate" ${settings.auto_generate?'checked':''}> Günlük PDF'yi otomatik hazırla</label><label class="health-approval"><input type="checkbox" name="auto_print" ${settings.auto_print?'checked':''}> Yazıcıya her gün otomatik gönder</label><label>Yazıcı adı (boşsa varsayılan)<input name="printer_name" maxlength="180" value="${hu(settings.printer_name||'')}" placeholder="Örn. Ofis-Yazici"></label><button type="submit">Çıktı Ayarlarını Kaydet</button></form><div class="health-small" id="healthPrintLast">Son yazdırma durumu yükleniyor...</div><p class="health-small">Otomatik işlemler yalnızca ERP'nin çalıştığı Mac açıkken ve program çalışırken yapılır. Otomatik yazdırma başlangıçta kapalıdır; etkinleştirdiğinizde günlük tek iş gönderilir.</p></div></div>
 <div class="panel"><h3>Geçmiş Tedavi Sonuçlarını Karşılaştır</h3><p class="health-small">Aynı hastalık / durum adıyla tamamlanmış, veteriner onaylı kayıtlar karşılaştırılır. İyileşme oranı ilaç etkinliğini kanıtlamaz ve otomatik reçete değildir.</p><form id="healthInsightForm"><label style="flex:1">Hastalık / durum<input id="healthInsightCondition" type="search" minlength="2" maxlength="140" placeholder="Kayda girilen hastalık adını yazın" style="max-width:none" required></label><button type="submit">Geçmiş Sonuçları Göster</button></form><div id="healthInsightResult"></div></div>`;
}
function bindHealthLogButtons(){
 document.querySelectorAll('[data-health-log]').forEach(b=>b.onclick=async()=>{
  const r=healthLastCases.find(x=>x.id===Number(b.dataset.healthLog));if(!r)return;
  const p=document.getElementById('healthLogPanel'),f=document.getElementById('healthLogForm');
  p.style.display='block';document.getElementById('healthClosePanel').style.display='none';
  document.getElementById('healthLogTitle').textContent=`Günlük uygulama: ${r.ear_tag} · ${r.condition_name}`;
  f.elements.namedItem('case_id').value=r.id;f.elements.namedItem('performed_on').value=healthToday();
  f.elements.namedItem('performed_on').min=r.start_date;
  f.elements.namedItem('performed_on').max=r.planned_end_date<healthToday()?r.planned_end_date:healthToday();
  try{const logs=await api(`/api/animal-health/cases/${r.id}/logs`);document.getElementById('healthLogHistory').innerHTML=logs.length?`<h4>Geçmiş uygulamalar</h4><div class="scroll"><table><thead><tr><th>Tarih</th><th>Uygulama</th><th>Uygulayan</th><th>Gözlem</th><th>Durum</th></tr></thead><tbody>${logs.map(l=>`<tr><td>${dateTr(l.performed_on)}</td><td>${Number(l.application_no)}</td><td>${hu(l.performed_by)}</td><td>${hu(l.observation)}</td><td>${hu(healthResponseLabels[l.response]||'Değerlendirilmedi')}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">Henüz günlük uygulama yok.</p>';}catch(e){message(e.message,true)}
  p.scrollIntoView({behavior:'smooth',block:'center'});
 });
 document.querySelectorAll('[data-health-history]').forEach(b=>b.onclick=()=>{document.querySelector(`[data-health-log="${b.dataset.healthHistory}"]`)?.click()});
}
function bindHealthCaseButtons(){
 document.querySelectorAll('[data-health-edit]').forEach(b=>b.onclick=()=>{
  const r=healthLastCases.find(x=>x.id===Number(b.dataset.healthEdit));if(!r)return;
  const f=document.getElementById('healthCaseForm');
  for(const k of ['animal_id','record_type','condition_name','product_name','treatment_name','dosage_text','applications_per_day','notes'])f.elements.namedItem(k).value=r[k]??'';
  f.elements.namedItem('duration_days').value=r.duration_days??Math.max(1,Math.round((Date.parse(r.planned_end_date+'T00:00:00Z')-Date.parse(r.start_date+'T00:00:00Z'))/86400000)+1);
  document.getElementById('healthRepeatNotice').textContent='';document.getElementById('healthRepeatNotice').style.display='none';
  f.elements.namedItem('case_id').value=r.id;updateHealthPlanDates(f);
  document.getElementById('healthCaseSave').textContent='Sağlık Kaydını Güncelle';document.getElementById('healthCaseCancel').style.display='inline-block';
  f.scrollIntoView({behavior:'smooth',block:'center'});
 });
 document.querySelectorAll('[data-health-close]').forEach(b=>b.onclick=()=>{
  const r=healthLastCases.find(x=>x.id===Number(b.dataset.healthClose));if(!r)return;
  document.getElementById('healthLogPanel').style.display='none';
  document.getElementById('healthClosePanel').style.display='block';
  document.getElementById('healthCloseForm').elements.namedItem('case_id').value=r.id;
  document.getElementById('healthCloseForm').elements.namedItem('closed_date').value=healthToday();
  document.getElementById('healthClosePanel').scrollIntoView({behavior:'smooth',block:'center'});
 });
 bindHealthLogButtons();
}
async function loadHealthDaily(){
 const target=document.getElementById('healthDailyList');if(!target)return;
 try{const data=await api('/api/animal-health/daily?on='+encodeURIComponent(healthReportDate));target.innerHTML=healthDailyTable(data);bindHealthLogButtons()}catch(e){target.textContent=e.message}
}
async function bindHealthScreen(){
 const addCatalog=document.getElementById('healthCatalogAddForm');
 addCatalog.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(addCatalog));
  try{await api('/api/animal-health/catalog',{method:'POST',body:JSON.stringify(d)});addCatalog.reset();await refreshHealthCatalog();message('İlaç / tedavi adı seçim listesine eklendi.')}catch(err){message(err.message,true)}
 };
 bindHealthCatalogPicks();
 const search=document.getElementById('healthSearch');
 const status=document.getElementById('healthStatusFilter');
 function doFilter(){healthCaseFilter=search.value;document.getElementById('healthCaseRows').innerHTML=healthCaseRows(healthLastCases.filter(r=>[r.ear_tag,r.farm_ear_tag,r.condition_name,r.product_name,r.pen].some(x=>String(x||'').toLocaleLowerCase('tr-TR').includes(healthCaseFilter.toLocaleLowerCase('tr-TR')))&&(!status.value||r.status===status.value)));bindHealthCaseButtons()}
 search.oninput=doFilter;status.onchange=doFilter;
 const cf=document.getElementById('healthCaseForm');
 if(cf){
  cf.elements.namedItem('record_type').onchange=()=>{if(cf.elements.namedItem('record_type').value!=='treatment')cf.elements.namedItem('applications_per_day').value='1'};
  cf.elements.namedItem('duration_days').oninput=()=>updateHealthPlanDates(cf);
  updateHealthPlanDates(cf);
  const repeatBox=document.getElementById('healthRepeatNotice');
  const showRepeat=s=>{repeatBox.textContent=s;repeatBox.style.display=s?'block':'none'};
  let repeatSerial=0;
  const previewRepeat=async()=>{
   const serial=++repeatSerial;
   const d=Object.fromEntries(new FormData(cf));d.animal_id=Number(d.animal_id);d.start_date=healthPlanStart(cf);
   if(!d.product_name){showRepeat('');return}
   try{const result=await checkHealthRepeat(d,d.case_id);if(serial===repeatSerial)showRepeat(healthRepeatMessage(result))}
   catch(err){if(serial===repeatSerial)showRepeat('Tekrar ilaç kontrolü yapılamadı. Bağlantıyı kontrol edip yeniden deneyin.')}
  };
  for(const name of ['animal_id','product_name','record_type'])cf.elements.namedItem(name).addEventListener('change',previewRepeat);
  const reset=()=>{cf.reset();cf.elements.namedItem('case_id').value='';updateHealthPlanDates(cf);document.getElementById('healthCaseSave').textContent='Sağlık Kaydını Oluştur';document.getElementById('healthCaseCancel').style.display='none';showRepeat('')};
  document.getElementById('healthCaseCancel').onclick=reset;
  cf.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(cf));const id=d.case_id;delete d.case_id;d.animal_id=Number(d.animal_id);d.applications_per_day=Number(d.applications_per_day);d.duration_days=Number(d.duration_days);
   if(!Number.isInteger(d.duration_days)||d.duration_days<=0){message('Tedavi süresini sıfırdan büyük tam gün olarak girin.',true);return}
   try{
    const repeat=await checkHealthRepeat({...d,start_date:healthPlanStart(cf)},id);
    if(repeat.warning){const warn=healthRepeatMessage(repeat);showRepeat(warn);
      if(!confirm(warn+'\n\nÖnceki kayıt ve tekrar uygulama gereği veterinerle değerlendirildi mi? Değerlendirme yapıldıysa devam edin.'))return;
      d.repeat_review_confirmed=true;
    }
    await api('/api/animal-health/cases'+(id?'/'+Number(id):''),{method:id?'PUT':'POST',body:JSON.stringify(d)});message(id?'Sağlık kaydı güncellendi.':'Sağlık kaydı oluşturuldu.');await render();
   }catch(err){message(err.message,true)}
  };
 }
 const logForm=document.getElementById('healthLogForm');
 document.getElementById('healthLogCancel').onclick=()=>document.getElementById('healthLogPanel').style.display='none';
 logForm.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(logForm));const id=Number(d.case_id);delete d.case_id;
  const originalCase=healthLastCases.find(x=>x.id===id);
  try{
   if(originalCase&&!originalCase.repeat_review_confirmed&&originalCase.record_type!=='observation'){
    const prev=await api(`/api/animal-health/cases/${id}/logs`);
    if(!prev.length){const repeat=await checkHealthRepeat({animal_id:originalCase.animal_id,product_name:originalCase.product_name,start_date:d.performed_on,record_type:originalCase.record_type},id);
     if(repeat.warning){const warn=healthRepeatMessage(repeat);
      if(originalCase.duration_days==null&&!originalCase.vet_approved){message('Bu eski planın uygulama kaydı için kayıtlı veteriner onayı gerekir.',true);return}
      if(!confirm(warn+'\n\nVeterinerle tekrar uygulama kontrol edildi mi? Onaylıysa devam edin.'))return;
      d.repeat_review_confirmed=true;
     }
    }
   }
   if(!confirm('Bu tedavi / aşı uygulamasının gerçekten yapıldığını onaylıyor musunuz?'))return;
   await api(`/api/animal-health/cases/${id}/logs`,{method:'POST',body:JSON.stringify(d)});message('Günlük uygulama kaydedildi.');await render();
  }catch(err){message(err.message,true)}
 };
 const closeForm=document.getElementById('healthCloseForm');
 document.getElementById('healthCloseCancel').onclick=()=>document.getElementById('healthClosePanel').style.display='none';
 closeForm.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(closeForm));const id=Number(d.case_id);delete d.case_id;
  if(!confirm('Sağlık kaydı kapanacak ve sonucu arşive işlenecek. Onaylıyor musunuz?'))return;
  try{await api(`/api/animal-health/cases/${id}/close`,{method:'POST',body:JSON.stringify(d)});message('Tedavi / sağlık kaydı kapatıldı.');await render()}catch(err){message(err.message,true)}
 };
 document.getElementById('healthDailyForm').onsubmit=async e=>{e.preventDefault();healthReportDate=e.target.elements.namedItem('on').value;await loadHealthDaily()};
 document.getElementById('healthPdfBtn').onclick=()=>{healthReportDate=document.getElementById('healthDailyForm').elements.namedItem('on').value;window.open('/api/animal-health/daily.pdf?on='+encodeURIComponent(healthReportDate),'_blank','noopener')};
 document.getElementById('healthPrintNowBtn').onclick=async()=>{if(!confirm('Bugünkü sağlık ve ajanda listesini Mac varsayılan veya seçilen yazıcıya göndermek istiyor musunuz?'))return;try{const d=await api('/api/animal-health/print-today',{method:'POST'});message(d.message);await showHealthPrintStatus()}catch(e){message(e.message,true)}};
 document.getElementById('healthPrintSettings').onsubmit=async e=>{e.preventDefault();const f=e.target;const d={daily_time:f.elements.namedItem('daily_time').value,auto_generate:f.elements.namedItem('auto_generate').checked,auto_print:f.elements.namedItem('auto_print').checked,printer_name:f.elements.namedItem('printer_name').value};
  if(d.auto_print&&!confirm('Program her gün belirtilen saatte Mac yazıcısına otomatik çıktı gönderecek. Yazıcı açık, kağıt dolu ve seçili olmalıdır. Etkinleştirilsin mi?'))return;
  try{await api('/api/animal-health/print-settings',{method:'PUT',body:JSON.stringify(d)});message('Otomatik rapor ve yazdırma ayarları kaydedildi.')}catch(err){message(err.message,true)}
 };
 document.getElementById('healthInsightForm').onsubmit=async e=>{e.preventDefault();const q=document.getElementById('healthInsightCondition').value.trim();const target=document.getElementById('healthInsightResult');
  try{const d=await api('/api/animal-health/insights?condition='+encodeURIComponent(q));target.innerHTML=`<p><strong>${d.completed_vet_approved_cases}</strong> tamamlanan veteriner onaylı vaka bulundu.</p>${d.past_protocols.length?`<div class="scroll"><table><thead><tr><th>Geçmişte kullanılan ürün / plan</th><th>Vaka</th><th>Olumlu sonuç</th><th>Olumsuz</th><th>Veteriner(ler)</th></tr></thead><tbody>${d.past_protocols.map(r=>`<tr><td>${hu(r.product_name)}</td><td>${r.total}</td><td>${r.positive}</td><td>${r.worsened}</td><td>${hu(r.veterinarians.join(', ')||'—')}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">Bu hastalık adında tamamlanmış kayıt bulunamadı.</p>'}<p class="health-info">${hu(d.warning)}</p>`;}catch(err){target.textContent=err.message}
 };
 bindHealthCaseButtons();await loadHealthDaily();await showHealthPrintStatus();
}
async function showHealthPrintStatus(){try{const d=await api('/api/animal-health/print-status');const e=document.getElementById('healthPrintLast');if(!e)return;e.textContent=d.report_date?`Son oluşturulan: ${dateTr(d.report_date)} · ${d.printed_at?'Yazıcıya gönderildi':'Yazıcıya gönderilmedi'}${d.print_error?' · Hata: '+d.print_error:''}`:'Henüz günlük PDF oluşturulmadı.'}catch(e){/* optional */}}
