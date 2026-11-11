/* Personel, mesai ve izinler. Ücret veya hukuki hak tahmini yapılmaz. */
let personnelPeople = [], personnelOvertime = [], personnelLeaves = [];
let personnelFilters = {employee_id:'',status:'',date_from:'',date_to:'',year:String(new Date().getFullYear())};
let personnelReport = null;
const personnelEscape = value => escapeHTML(value ?? '');
const personnelStatuses = {active:'Çalışıyor',left:'İşten ayrıldı',planned:'Ayrılışı planlandı',not_started:'İşe başlamadı'};

function personnelOptions() {
  return personnelPeople.map(row => `<option value="${row.id}" ${String(row.id)===personnelFilters.employee_id?'selected':''}>${personnelEscape(row.employee_no+' · '+row.full_name)}</option>`).join('');
}
function personnelParams(extra={}) {
  return new URLSearchParams(Object.entries({...personnelFilters,...extra}).filter(([,value])=>value!==''&&value!==null&&value!==undefined)).toString();
}
function personnelTable(headers,rows) {
  return `<div class="scroll"><table><thead><tr>${headers.map(label=>`<th>${personnelEscape(label)}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${headers.length}">Seçilen koşullarda kayıt bulunamadı.</td></tr>`}</tbody></table></div>`;
}
function personnelReportHtml(report) {
  return `<h3>${personnelEscape(report.title)} (${report.row_count} kayıt)</h3><p class="muted">${personnelEscape(report.notice)}</p>${personnelTable(report.columns,report.rows.map(row=>row.map(personnelEscape)))}`;
}
async function personnelScreenHtml() {
  personnelPeople = await api('/api/personnel/employees');
  [personnelOvertime,personnelLeaves] = await Promise.all([
    api('/api/personnel/overtime?'+personnelParams()),api('/api/personnel/leaves?'+personnelParams())]);
  const people = personnelPeople.filter(row=>(!personnelFilters.employee_id||String(row.id)===personnelFilters.employee_id)&&(!personnelFilters.status||row.status===personnelFilters.status)&&(!personnelFilters.date_from||!row.end_date||row.end_date>=personnelFilters.date_from)&&(!personnelFilters.date_to||row.start_date<=personnelFilters.date_to));
  const opts = personnelOptions();
  const canCreate=right('personel.create'),canEdit=right('personel.edit'),canDelete=right('personel.delete');
  const balances = right('reports.payroll.view')?await api('/api/personnel/balances?'+personnelParams()):[];
  const buttons = (kind,row) => `${canEdit?`<button type="button" class="secondary-action" data-personnel-edit-${kind}="${row.id}">Düzenle</button>`:''} ${canDelete?`<button type="button" class="secondary-action" data-personnel-delete-${kind}="${row.id}">Sil</button>`:''}`;
  return `<h1>Personel, Mesai ve İzinler</h1><p class="sub">İşe giriş ve ayrılış, mesai saatleri, haftalık ve yıllık izin kayıtları. Geçmiş personel kartları korunur.</p>
  <div class="panel"><h3>Liste ve rapor koşulları</h3><form id="personnelFilterForm">
  <label>Personel<select name="employee_id"><option value="">Tüm personel</option>${opts}</select></label>
  <label>Durum<select name="status"><option value="">Tüm durumlar</option>${Object.entries(personnelStatuses).map(([key,label])=>`<option value="${key}" ${personnelFilters.status===key?'selected':''}>${label}</option>`).join('')}</select></label>
  <label>Başlangıç tarihi<input name="date_from" type="date" value="${personnelEscape(personnelFilters.date_from)}"></label>
  <label>Bitiş tarihi<input name="date_to" type="date" value="${personnelEscape(personnelFilters.date_to)}"></label>
  <label>Yıllık izin yılı<input name="year" type="number" min="2000" max="2200" step="1" required value="${personnelEscape(personnelFilters.year)}"></label>
  <button type="submit">Listele</button><button type="button" class="secondary-action" id="personnelClearFilter">Koşulları Temizle</button></form></div>
  <div class="panel"><h3>Personel kartları</h3>${personnelTable(['Personel No','Ad Soyad','Bölüm','İşe giriş','İşten ayrılış','Durum','Kaydeden','İşlem'],people.map(row=>[personnelEscape(row.employee_no),personnelEscape(row.full_name),personnelEscape(row.department),dateTr(row.start_date),row.end_date?dateTr(row.end_date):'—',personnelEscape(row.status_label),personnelEscape(row.created_by),canEdit?`<button type="button" class="secondary-action" data-personnel-card="${row.id}">Düzenle / Ayrılış</button>`:'—']))}</div>
  ${canCreate||canEdit?`<div class="panel"><h3 id="personnelCardTitle">Personel Kartı</h3><form id="personnelEmployeeForm"><input type="hidden" name="id">
  <label>Personel No<input name="employee_no" maxlength="40" required></label><label>Ad Soyad<input name="full_name" minlength="2" maxlength="120" required></label>
  <label>Bölüm<input name="department" maxlength="120"></label><label>Telefon<input name="phone" maxlength="40" type="tel"></label>
  <label>İşe giriş tarihi<input name="start_date" type="date" value="${localToday()}" required></label><label>İşten ayrılış tarihi<input name="end_date" type="date"></label>
  <label>Açıklama<input name="notes" maxlength="1000"></label><button type="submit" id="personnelCardSave" ${canCreate?'':'disabled'}>Personeli Kaydet</button><button type="button" class="secondary-action" id="personnelCardReset">Yeni Kart</button></form><p class="muted">Ayrılan personeli silmek yerine ayrılış tarihini girin. Geçmiş mesai ve izinler korunur. Kayıtlı işlemlerle çelişen işe giriş/ayrılış tarihi reddedilir.</p></div>`:''}
  <div class="panel"><h3>Mesai</h3>${canCreate||canEdit?`<form id="personnelOvertimeForm"><input name="id" type="hidden"><label>Personel<select name="employee_id" required>${opts}</select></label><label>Tarih<input name="worked_on" type="date" value="${localToday()}" required></label><label>Mesai süresi (saat)<input name="hours" type="text" inputmode="decimal" placeholder="Örn. 1,5" required></label><label>Açıklama<input name="notes" maxlength="1000"></label><button type="submit" ${canCreate?'':'disabled'}>Mesaiyi Kaydet</button><button type="button" class="secondary-action" data-personnel-reset="personnelOvertimeForm">Yeni Kayıt</button></form>`:''}
  ${personnelTable(['Personel','Tarih','Mesai saati','Açıklama','İşlem'],personnelOvertime.map(row=>[personnelEscape(row.full_name),dateTr(row.worked_on),fmtDbQuantity(row.hours),personnelEscape(row.notes),buttons('overtime',row)]))}<p class="muted">Mesai saat olarak izlenir; bu kayıt otomatik ücret veya maaş hesabı oluşturmaz.</p></div>
  <div class="panel"><h3>Haftalık ve Yıllık İzin</h3>${canCreate||canEdit?`<form id="personnelLeaveForm"><input name="id" type="hidden"><label>Personel<select name="employee_id" required>${opts}</select></label><label>İzin türü<select name="kind"><option value="weekly">Haftalık izin</option><option value="annual">Yıllık izin</option></select></label><label>Başlangıç<input name="starts_on" type="date" value="${localToday()}" required></label><label>Bitiş<input name="ends_on" type="date" value="${localToday()}" required></label><label>Açıklama<input name="notes" maxlength="1000"></label><button type="submit" ${canCreate?'':'disabled'}>İzni Kaydet</button><button type="button" class="secondary-action" data-personnel-reset="personnelLeaveForm">Yeni Kayıt</button></form>`:''}
  ${personnelTable(['Personel','İzin türü','Başlangıç','Bitiş','Gün','Açıklama','İşlem'],personnelLeaves.map(row=>[personnelEscape(row.full_name),personnelEscape(row.kind_label),dateTr(row.starts_on),dateTr(row.ends_on),String(row.days),personnelEscape(row.notes),buttons('leaves',row)]))}
  <p class="muted">Başlangıç ve bitiş dahil takvim günleri sayılır. Çakışan izin veya mesai kaydı kabul edilmez. Yıllık izin için ilgili yılın hakkını önce tanımlayın.</p></div>
  ${canEdit?`<div class="panel"><h3>Yıllık İzin Hakkını Tanımla</h3><form id="personnelAllowanceForm"><label>Personel<select name="employee_id" required>${opts}</select></label><label>Yıl<input name="year" type="number" min="2000" max="2200" value="${personnelEscape(personnelFilters.year)}" required></label><label>Yıllık izin hakkı (gün)<input name="days" type="number" min="0" step="1" required></label><button type="submit">İzin Hakkını Kaydet</button></form><p class="muted">Hak işletme tarafından yıl bazında girilir; kanuni hak ediş veya devir otomatik tahmin edilmez. Kayıtlı izinlerden daha az hak tanımlanamaz.</p></div>`:''}
  ${right('reports.payroll.view')?`<div class="panel"><h3>${personnelEscape(personnelFilters.year)} Yıllık İzin Durumu</h3>${personnelTable(['Personel','Tanımlanan hak','Kullanılan gün','Planlanan gün','Kalan gün'],balances.map(row=>[personnelEscape(row.full_name),row.allocated_days===null?'Tanımlanmadı':String(row.allocated_days),String(row.used_days),String(row.planned_days),row.remaining_days===null?'Tanımlanmadı':String(row.remaining_days)]))}<p class="muted">Kalan gün, kullanılan ve gelecekte planlanan yıllık izinler düşülerek hesaplanır. Haftalık izinler yıllık haktan düşmez.</p></div>
  <div class="panel"><h3>Personel Raporları</h3><p class="muted">Üstteki personel, durum ve tarih koşulları rapora da uygulanır. Yıllık hak bilgileri seçilen yıla aittir.</p><form id="personnelReportForm"><label>Rapor türü<select name="kind"><option value="summary">Genel durum / izin bakiyesi</option><option value="employees">Personel listesi</option><option value="overtime">Mesai listesi</option><option value="leaves">İzin listesi</option><option value="employment">İşe giriş / ayrılış listesi</option></select></label><button type="submit">Raporu Göster</button>${right('reports.payroll.export')?'<button type="button" class="secondary-action" id="personnelCsv">Excel / CSV İndir</button>':''}</form><div id="personnelReportResult">${personnelReport?personnelReportHtml(personnelReport):'Rapor türünü seçerek sorgulayın.'}</div></div>`:''}`;
}

function personnelFill(formId,record) {
  const form=document.getElementById(formId);if(!form)return;
  for(const element of form.elements){if(element.name&&element.name in record)element.value=element.name==='hours'?fmtDbQuantity(record[element.name]):record[element.name]??'';}
  form.querySelector('button[type=submit]').disabled=false;
  form.scrollIntoView({behavior:'smooth',block:'center'});
}
function personnelReset(form) {
  form.reset();if(form.elements.namedItem('id'))form.elements.namedItem('id').value='';
  form.querySelector('button[type=submit]').disabled=!right('personel.create');
}
async function bindPersonnelScreen() {
  const filter=document.getElementById('personnelFilterForm');
  filter.onsubmit=async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(filter));if(values.date_from&&values.date_to&&values.date_to<values.date_from){message('Bitiş tarihi başlangıçtan önce olamaz.',true);return}personnelFilters=values;personnelReport=null;await render()};
  document.getElementById('personnelClearFilter').onclick=async()=>{personnelFilters={employee_id:'',status:'',date_from:'',date_to:'',year:String(new Date().getFullYear())};personnelReport=null;await render()};
  const cards=document.getElementById('personnelEmployeeForm');
  if(cards){cards.onsubmit=async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(cards)),id=data.id;delete data.id;data.end_date=data.end_date||null;try{await api('/api/personnel/employees'+(id?'/'+id:''),{method:id?'PUT':'POST',body:JSON.stringify(data)});personnelReport=null;message(id?'Personel kartı güncellendi.':'Personel kaydedildi.');await render()}catch(error){message(error.message,true)}};
  document.getElementById('personnelCardReset').onclick=()=>personnelReset(cards);}
  document.querySelectorAll('[data-personnel-card]').forEach(button=>button.onclick=()=>personnelFill('personnelEmployeeForm',personnelPeople.find(row=>row.id===Number(button.dataset.personnelCard))));
  document.querySelectorAll('[data-personnel-reset]').forEach(button=>button.onclick=()=>personnelReset(document.getElementById(button.dataset.personnelReset)));
  for(const [type,id,rows] of [['overtime','personnelOvertimeForm',personnelOvertime],['leaves','personnelLeaveForm',personnelLeaves]]){
    const form=document.getElementById(id);
    if(form)form.onsubmit=async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(form)),recordId=data.id;delete data.id;data.employee_id=Number(data.employee_id);try{
      if(type==='overtime'){data.hours=String(data.hours).trim().replace(',','.');if(!/^\d+(?:\.\d{1,2})?$/.test(data.hours)||+data.hours<=0||+data.hours>24)throw Error('Mesai süresi 0’dan büyük, en fazla 24 saat olmalı. Örnek: 1,5');}
      await api('/api/personnel/'+type+(recordId?'/'+recordId:''),{method:recordId?'PUT':'POST',body:JSON.stringify(data)});personnelReport=null;message(type==='overtime'?'Mesai kaydedildi.':'İzin kaydedildi.');await render()
    }catch(error){message(error.message,true)}};
    document.querySelectorAll(`[data-personnel-edit-${type}]`).forEach(button=>button.onclick=()=>personnelFill(id,rows.find(row=>row.id===Number(button.getAttribute('data-personnel-edit-'+type)))));
    document.querySelectorAll(`[data-personnel-delete-${type}]`).forEach(button=>button.onclick=async()=>{if(!confirm('Seçilen deneme veya hatalı kayıt silinsin mi? İşlem geçmişi korunacaktır.'))return;try{await api('/api/personnel/'+type+'/'+button.getAttribute('data-personnel-delete-'+type),{method:'DELETE'});personnelReport=null;message('Kayıt silindi. İşlem geçmişi korundu.');await render()}catch(error){message(error.message,true)}});
  }
  const allowance=document.getElementById('personnelAllowanceForm');
  if(allowance)allowance.onsubmit=async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(allowance));try{await api(`/api/personnel/allowances/${Number(data.employee_id)}/${Number(data.year)}`,{method:'PUT',body:JSON.stringify({days:Number(data.days)})});personnelReport=null;message('Yıllık izin hakkı kaydedildi.');await render()}catch(error){message(error.message,true)}};
  const report=document.getElementById('personnelReportForm');
  if(report){report.onsubmit=async event=>{event.preventDefault();try{personnelReport=await api('/api/personnel/reports?'+personnelParams({kind:report.elements.namedItem('kind').value}));document.getElementById('personnelReportResult').innerHTML=personnelReportHtml(personnelReport)}catch(error){message(error.message,true)}};
    const csv=document.getElementById('personnelCsv');if(csv)csv.onclick=async()=>{try{const response=await fetch('/api/personnel/reports.csv?'+personnelParams({kind:report.elements.namedItem('kind').value}));if(!response.ok)throw Error('Rapor alınamadı.');const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');link.href=url;link.download='personel_mesai_izin.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(_error){message('Personel raporu indirilemedi. Bağlantınızı ve rapor dışa aktarma yetkinizi kontrol edin.',true)}};
  }
}
window.v15Screens=window.v15Screens||{};
window.v15Screens.personel={html:personnelScreenHtml,bind:bindPersonnelScreen};
