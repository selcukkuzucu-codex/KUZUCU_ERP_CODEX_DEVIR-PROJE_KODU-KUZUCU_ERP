/* KUZUCU ERP v0.16 — gruplu menü, Ana Sayfa, Cariler, Kasa / Banka, Hayvan Çıkış Raporu, Yedekler. */
(()=>{
const h=escapeHTML;
const ICON={
 home:'M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
 hayvan:'M5 9c0-3 3-5 7-5s7 2 7 5v3c0 4-3 8-7 8s-7-4-7-8zM3 7l3 2M21 7l-3 2M10 16h4',
 tarim:'M12 21V10M12 10c0-4 3-6 7-6 0 4-3 6-7 6zM12 14c0-3-2-5-6-5 0 3 2 5 6 5z',
 stok:'M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8',
 muhasebe:'M3 7h18v12H3zM3 11h18M7 15h4',
 personel:'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-4 3-6 7-6s7 2 7 6M17 11a3 3 0 1 0 0-6M22 21c0-3-2-5-5-5',
 rapor:'M4 20V10M10 20V4M16 20v-7M22 20H2',
 ajanda:'M4 5h16v16H4zM4 10h16M9 3v4M15 3v4',
 belge:'M6 3h9l5 5v13H6zM15 3v5h5M9 13h8M9 17h6',
 yonetim:'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z'
};
const GROUPS=[
 {id:'ana',name:'Ana Sayfa',icon:'home',keys:['dashboard']},
 {id:'hayvanlar',name:'Hayvanlar',icon:'hayvan',keys:['animals','pens','calves','animal-health','weighings','topluhayvan','hayvancikis']},
 {id:'tarim',name:'Tarım',icon:'tarim',keys:['fields','seasons']},
 {id:'stok',name:'Stok',icon:'stok',keys:['stokgiris','stock','items','uyarilar']},
 {id:'muhasebe',name:'Muhasebe',icon:'muhasebe',keys:['faturalar','cariler','kasabanka','maliyetler']},
 {id:'personel',name:'Personel',icon:'personel',keys:['personel']},
 {id:'raporlar',name:'Raporlar',icon:'rapor',keys:['reports','cikisraporu']},
 {id:'ajanda',name:'Ajanda',icon:'ajanda',keys:['reminders']},
 {id:'belgeler',name:'Belgeler',icon:'belge',keys:['belgeaktarim','documents','integrations']},
 {id:'yonetim',name:'Yönetim',icon:'yonetim',keys:['users','audit','yedekler']}
];
const icon=name=>`<svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICON[name]}"></path></svg>`;
const store={get(k,d){try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(_e){return d}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(_e){}}};
let openGroups=new Set(store.get('kzcNavOpen',[]));let navQuery='';let backupInfo=null,backupFetched=0;
const label=k=>(sections.find(([key])=>key===k)||[k,k])[1];
const fold=s=>String(s||'').toLocaleLowerCase('tr-TR').normalize('NFKD').replace(/[̀-ͯ]/g,'').replace(/ı/g,'i');

function backupText(){if(!backupInfo)return 'Yedek bilgisi alınıyor…';if(backupInfo.ok===false)return '⚠ Son yedek alınamadı';if(!backupInfo.latest_at)return 'Henüz yedek yok';const d=new Date(backupInfo.latest_at);return 'Son yedek: '+d.toLocaleDateString('tr-TR')+' '+d.toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'})}
async function refreshBackupInfo(force=false){if(!erpSession)return;if(!force&&Date.now()-backupFetched<300000)return;backupFetched=Date.now();try{backupInfo=await api('/api/backups/status')}catch(_e){backupInfo=null}const el=document.getElementById('navBackup');if(el){el.textContent=backupText();el.classList.toggle('bad',backupInfo?.ok===false)}}
window.refreshBackupInfo=refreshBackupInfo;

window.renderNav=function(activeKey){
 const nav=document.querySelector('#nav');if(!nav)return;
 const allowed=new Set(sections.filter(([k])=>sectionAllowed(k)).map(([k])=>k));
 const groups=GROUPS.map(g=>({...g,keys:g.keys.filter(k=>allowed.has(k))})).filter(g=>g.keys.length);
 const active=groups.find(g=>g.keys.includes(activeKey));if(active&&active.keys.length>1)openGroups.add(active.id);
 const item=(k,top)=>`<button type="button" class="nav-item${top?' nav-top':''}${k===activeKey?' active':''}" data-key="${h(k)}"${k===activeKey?' aria-current="page"':''}>${top?icon(top):''}<span>${h(label(k))}</span></button>`;
 let body='';
 if(navQuery.trim()){
  const q=fold(navQuery);const hits=groups.flatMap(g=>g.keys.map(k=>({k,g}))).filter(x=>fold(label(x.k)).includes(q)||fold(x.g.name).includes(q));
  body=hits.length?hits.map(x=>item(x.k,x.g.icon)).join(''):'<p class="nav-empty">Eşleşen sayfa yok.</p>';
 }else body=groups.map(g=>{
  if(g.keys.length===1&&(g.keys[0]==='dashboard'||g.name===label(g.keys[0])||['personel','ajanda'].includes(g.id)))return item(g.keys[0],g.icon);
  const open=openGroups.has(g.id);
  return `<div class="nav-group${open?' open':''}${g===active?' has-active':''}"><button type="button" class="nav-group-head" data-group="${g.id}" aria-expanded="${open}">${icon(g.icon)}<span>${h(g.name)}</span><span class="chev" aria-hidden="true">${open?'▾':'▸'}</span></button><div class="nav-sub"${open?'':' hidden'}>${g.keys.map(k=>item(k)).join('')}</div></div>`}).join('');
 nav.innerHTML=`<label class="nav-search">Menüde ara<input id="navSearch" type="search" placeholder="Sayfa adı yazın" value="${h(navQuery)}" autocomplete="off"></label><div class="nav-list" role="list">${body}</div><div class="nav-footer"><span id="navBackup"${backupInfo?.ok===false?' class="bad"':''}>${h(backupText())}</span><span>Sürüm v0.16 · Yerel pilot</span></div>`;
 nav.querySelectorAll('[data-key]').forEach(b=>b.onclick=()=>{navQuery='';document.body.classList.remove('nav-open');document.getElementById('navToggle')?.setAttribute('aria-expanded','false');navigate(b.dataset.key)});
 nav.querySelectorAll('[data-group]').forEach(b=>b.onclick=()=>{const id=b.dataset.group;openGroups.has(id)?openGroups.delete(id):openGroups.add(id);store.set('kzcNavOpen',[...openGroups]);renderNav(activeKey)});
 const search=nav.querySelector('#navSearch');search.oninput=()=>{navQuery=search.value;renderNav(activeKey);const s=document.getElementById('navSearch');s.focus();s.setSelectionRange(s.value.length,s.value.length)};
 search.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();nav.querySelector('.nav-list [data-key]')?.click()}if(e.key==='Escape'){navQuery='';renderNav(activeKey)}};
 refreshBackupInfo();
};
document.getElementById('navToggle')?.addEventListener('click',()=>{const open=document.body.classList.toggle('nav-open');document.getElementById('navToggle').setAttribute('aria-expanded',String(open))});

// ---------------- Ana Sayfa ----------------
const toneClass={warn:'tone-warn',good:'tone-good',neutral:''};
const go=(key,text,cls='link-action')=>sectionAllowed(key)?`<button type="button" class="${cls}" data-go="${h(key)}">${text}</button>`:'';
async function dashboardHtml(){
 const [ins,d]=await Promise.all([api('/api/dashboard/insights'),api('/api/dashboard')]);
 const today=new Date(ins.today+'T12:00:00').toLocaleDateString('tr-TR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
 const quick=[right('hayvanlar.tartim.create')&&go('weighings','+ Tartım Gir','primary-action'),right('stok.hareket.create')&&go('stokgiris','+ Stok Girişi','primary-action'),right('hayvanlar.saglik.create')&&go('animal-health','+ Tedavi Kaydı','add-action')].filter(Boolean).join('');
 const cards=ins.cards.map(c=>`<div class="kpi ${toneClass[c.tone]||''}"><span class="kpi-label">${h(c.label)}</span><strong class="kpi-value">${h(c.value)}</strong><span class="kpi-note">${h(c.note)}</span>${go(c.target,'Aç')}</div>`).join('');
 const checks=ins.checks.length?ins.checks.map(c=>`<div class="check-row ${c.level==='error'?'is-error':'is-warn'}"><span class="dot" aria-hidden="true"></span><div><strong>${h(c.title)}</strong><span>${h(c.detail)}</span></div>${go(c.target,'Kayda git')}</div>`).join(''):'<p class="muted">Şu an kontrol edilmesi gereken bir durum yok.</p>';
 const todos=ins.todos.length?ins.todos.map(t=>`<li><span>${h(t.title)}</span><small>${h(t.tag)}</small></li>`).join(''):'<li class="muted">Bugün için zamanı gelen hatırlatma yok.</li>';
 const val=v=>v==null?'Yetki yok':fmtDbQuantity(v);const m=d.milk_calves;
 const stat=(n,v)=>`<div class="mini-stat"><span>${n}</span><strong>${val(v)}</strong></div>`;
 return `<div class="page-head"><div><span class="muted">${h(today)}</span><h1>Ana Sayfa</h1></div><div class="quick-actions">${quick}</div></div>
 ${cards?`<section class="kpi-grid" aria-label="Özet göstergeler">${cards}</section>`:''}
 <div class="two-col"><section class="panel"><div class="panel-head"><h2>Kontrol edilmesi gerekenler</h2>${ins.checks.length?`<span class="count-pill">${ins.checks.length}</span>`:''}</div>${checks}</section>
 ${right('ajanda.view')?`<section class="panel"><div class="panel-head"><h2>Bugün yapılacaklar</h2></div><ul class="todo-list">${todos}</ul>${go('reminders','Ajandayı aç')}</section>`:''}</div>
 <section class="panel"><div class="panel-head"><h2>Hayvan ve işletme durumu</h2></div><div class="mini-grid">${stat('Toplam aktif hayvan',d.active_total)}${stat('Erkek',d.male_total)}${stat('Dişi',d.female_total)}${stat('Süt içen erkek buzağı',m?.male)}${stat('Süt içen dişi buzağı',m?.female)}${stat('Kayıtlı tarla alanı (dekar)',d.area_decare)}${stat('Grup sayısı',d.pens)}</div>
 ${m?.phase_unknown?`<p class="warn">${m.phase_unknown} eski buzağı kaydında süt dönemi belirtilmemiş. Kartı düzenleyerek belirtin; bu hayvanlar süt içen sayısına tahminen eklenmez.</p>`:''}${d.unknown_sex_total?`<p class="muted">Cinsiyeti belirtilmeyen ${d.unknown_sex_total} hayvan var.</p>`:''}
 ${d.breeds&&d.breeds.length?`<h3>Irk toplamları</h3>${table(d.breeds,[['breed','Irk'],['total','Adet']])}`:''}</section>`;
}
function bindGo(){document.querySelectorAll('#content [data-go]').forEach(b=>b.onclick=()=>navigate(b.dataset.go))}

// ---------------- Cariler (firma kartı + cari hesap) ve Kasa / Banka ----------------
async function carilerHtml(){
 let html='<h1>Cariler</h1><p class="sub">Tedarikçi ve müşteri firmaların kart bilgileri, cari bakiyeleri, ödeme / tahsilatları ve hesap hareketleri tek sayfada.</p>';
 if(right('firmalar.view')){const rows=await api('/api/firms');window.__firmRows=rows;html+=`<section class="cari-section"><h2>Firma kartları</h2>${firmsScreenHtml(rows,false)}</section>`}
 if(right('hesap.cari.view'))html+=`<section class="cari-section"><h2>Cari hesaplar</h2>${await window.financeFeatures.accountsHtml('cariler')}</section>`;
 return html;
}
async function carilerBind(){
 if(document.getElementById('firmEntryForm')){bindFirmsScreen();if(!right('firmalar.create'))document.getElementById('firmEntryForm').style.display='none';if(!right('firmalar.edit'))document.querySelectorAll('[data-edit-firm]').forEach(b=>b.style.display='none')}
 if(right('hesap.cari.view'))await window.financeFeatures.accountsBind();
}

// ---------------- Hayvan Çıkış Raporu ----------------
const iso=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
function ranges(){const t=new Date();const first=new Date(t.getFullYear(),t.getMonth(),1);const prevEnd=new Date(t.getFullYear(),t.getMonth(),0);const prevStart=new Date(prevEnd.getFullYear(),prevEnd.getMonth(),1);const d30=new Date(t);d30.setDate(t.getDate()-29);
 return {month:[iso(first),iso(t)],prev:[iso(prevStart),iso(prevEnd)],d30:[iso(d30),iso(t)],year:[`${t.getFullYear()}-01-01`,iso(t)]}}
let exitQuery=null;
async function exitsHtml(){const r=ranges();exitQuery=exitQuery||{date_from:r.month[0],date_to:r.month[1],reason:'',section:'all'};
 const sel=(v,cur)=>v===cur?' selected':'';
 return `<h1>Hayvan Çıkış Raporu</h1><p class="sub">Kesilen, ölen, satılan besi hayvanları ve çıkışı yapılan buzağılar. Çıkışı yapılan hayvanların kayıtları silinmez; geçmiş her tarih aralığı için aranabilir.</p>
 <div class="panel"><form id="exitForm" class="report-filters"><label>Başlangıç<input type="date" name="date_from" value="${h(exitQuery.date_from)}"></label><label>Bitiş<input type="date" name="date_to" value="${h(exitQuery.date_to)}"></label>
 <label>Çıkış nedeni<select name="reason"><option value=""${sel('',exitQuery.reason)}>Tümü</option><option value="slaughter"${sel('slaughter',exitQuery.reason)}>Kesim</option><option value="death"${sel('death',exitQuery.reason)}>Ölüm</option><option value="sale"${sel('sale',exitQuery.reason)}>Satış</option><option value="calf"${sel('calf',exitQuery.reason)}>Buzağı çıkışı</option></select></label>
 <label>Bölüm<select name="section"><option value="all"${sel('all',exitQuery.section)}>Besi + buzağı</option><option value="cattle"${sel('cattle',exitQuery.section)}>Yalnızca besi</option><option value="calf"${sel('calf',exitQuery.section)}>Yalnızca buzağı</option></select></label><button type="submit">Listele</button></form>
 <div class="chip-row" aria-label="Hazır tarih aralıkları"><button type="button" class="chip" data-range="month">Bu ay</button><button type="button" class="chip" data-range="prev">Geçen ay</button><button type="button" class="chip" data-range="d30">Son 30 gün</button><button type="button" class="chip" data-range="year">Bu yıl</button><button type="button" class="chip" data-range="all">Tüm zamanlar</button></div>
 <div id="exitResult"></div></div>`}
async function loadExits(){const box=document.getElementById('exitResult');const qs=new URLSearchParams(Object.entries(exitQuery).filter(([,v])=>v));
 try{const r=await api('/api/reports/animal-exits?'+qs);const t=r.totals;
  const kg=v=>fmtDbQuantity(v);
  const range=(exitQuery.date_from?dateTr(exitQuery.date_from):'İlk kayıt')+' – '+(exitQuery.date_to?dateTr(exitQuery.date_to):'Bugün');
  box.innerHTML=`<div class="kpi-grid compact"><div class="kpi"><span class="kpi-label">Toplam</span><strong class="kpi-value">${t.count} baş</strong><span class="kpi-note">${h(range)}</span></div><div class="kpi"><span class="kpi-label">Toplam çıkış kilosu</span><strong class="kpi-value">${kg(t.total_kg)} kg</strong><span class="kpi-note">Kilosu girilenler</span></div>${t.by_reason.map(b=>`<div class="kpi"><span class="kpi-label">${h(b.label)}</span><strong class="kpi-value">${b.count} baş</strong><span class="kpi-note">${kg(b.kg)} kg</span></div>`).join('')}</div>
  <div class="table-tools">${(right('reports.animals.export')||right('reports.calves.export'))?'<button type="button" class="secondary-action" id="exitCsv">Excel / CSV İndir</button>':''}<button type="button" class="secondary-action" id="exitPrint">Yazdır</button></div>
  <div class="scroll"><table><thead><tr><th>Tarih</th><th>Bölüm</th><th>TR Küpe No</th><th>İşletme Küpe No</th><th>Grup No</th><th>Çıkış nedeni</th><th>Nereye gittiği</th><th class="num">Çıkış kg</th></tr></thead><tbody>${r.rows.length?r.rows.map(x=>`<tr><td>${dateTr(x.exit_date)}</td><td>${h(x.section)}</td><td>${h(x.tr_ear_tag)}</td><td>${h(x.farm_ear_tag||'—')}</td><td>${h(x.group_no||'—')}</td><td><span class="tag tag-${h(x.reason)}">${h(x.reason_label)}</span></td><td>${h(x.destination||'—')}</td><td class="num">${x.exit_kg?kg(x.exit_kg):'—'}</td></tr>`).join(''):'<tr><td colspan="8" class="muted">Seçilen aralıkta çıkış kaydı yok.</td></tr>'}</tbody></table></div>`;
  document.getElementById('exitPrint').onclick=()=>window.print();
  const csv=document.getElementById('exitCsv');if(csv)csv.onclick=async()=>{try{const resp=await fetch('/api/reports/animal-exits.csv?'+qs);if(!resp.ok)throw Error('Rapor indirilemedi. Yetkinizi kontrol edin.');const blob=await resp.blob(),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='hayvan_cikis_raporu.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)}catch(e){message(e.message,true)}};
 }catch(e){box.innerHTML=`<p class="warn">${h(e.message)}</p>`}}
async function exitsBind(){const f=document.getElementById('exitForm');
 f.onsubmit=e=>{e.preventDefault();exitQuery=Object.fromEntries(new FormData(f));if(exitQuery.date_from&&exitQuery.date_to&&exitQuery.date_from>exitQuery.date_to){message('Başlangıç tarihi bitiş tarihinden sonra olamaz.',true);return}loadExits()};
 document.querySelectorAll('[data-range]').forEach(b=>b.onclick=()=>{const r=ranges()[b.dataset.range]||['',''];f.elements.namedItem('date_from').value=r[0];f.elements.namedItem('date_to').value=r[1];f.requestSubmit()});
 await loadExits()}

// ---------------- Yedekler (yönetici) ----------------
async function backupsHtml(){const s=await api('/api/backups/status');const at=v=>v?new Date(v).toLocaleString('tr-TR'):'—';
 return `<h1>Yedekler</h1><p class="sub">Program açılırken, her 30 dakikada bir, her "Çıkış Yap"ta ve düzgün kapanırken veritabanının güvenli yedeğini alır.</p>
 <div class="kpi-grid compact"><div class="kpi ${s.ok===false?'tone-warn':'tone-good'}"><span class="kpi-label">Son yedek</span><strong class="kpi-value">${h(at(s.latest_at))}</strong><span class="kpi-note">${h(s.ok===false?s.message:(s.latest_file||'Henüz yedek yok'))}</span></div><div class="kpi"><span class="kpi-label">Saklanan yedek sayısı</span><strong class="kpi-value">${Number(s.count||0)}</strong><span class="kpi-note">Saklama kuralına göre</span></div></div>
 <div class="panel"><h3>Yedek klasörü</h3><p><code>${h(s.directory||'')}</code></p><button type="button" id="backupNow" class="primary-action">Şimdi Yedek Al</button>
 <h3>Saklama kuralı</h3><ul><li>Son 2 gündeki bütün yedekler saklanır.</li><li>30 güne kadar her günün son yedeği saklanır.</li><li>Daha eski dönemlerde her ayın son yedeği saklanır.</li><li>Her durumda en yeni 20 yedek silinmez.</li></ul>
 <p class="warn">Veritabanı yedeği; parsel görsellerini, belgeleri ve raporları kapsamaz. <code>data</code> ve <code>raporlar</code> klasörlerini ayrıca harici diske veya NAS'a kopyalayın. Elektrik kesintisinde son anın yedeği garanti edilemez.</p></div>`}
async function backupsBind(){document.getElementById('backupNow').onclick=async e=>{e.target.disabled=true;try{await api('/api/backups/now',{method:'POST'});message('Yedek alındı.');await refreshBackupInfo(true);await render()}catch(err){message(err.message,true)}finally{e.target.disabled=false}}}

window.v15Screens={...(window.v15Screens||{}),
 dashboard:{html:dashboardHtml,bind:async()=>bindGo()},
 cariler:{html:carilerHtml,bind:carilerBind},
 kasabanka:{html:()=>window.financeFeatures.accountsHtml('kasa'),bind:()=>window.financeFeatures.accountsBind()},
 cikisraporu:{html:exitsHtml,bind:exitsBind},
 yedekler:{html:backupsHtml,bind:backupsBind}};
})();
