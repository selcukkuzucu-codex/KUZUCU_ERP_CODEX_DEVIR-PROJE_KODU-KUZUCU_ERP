/* Kuzucu ERP v0.13 — kullanıcı girişi, yetki ekranı, taslak otomatik koruma. */
let erpSession=null;
let erpCsrf='';
let erpModules={};
let draftTimer=null;
let draftDirty=new Set();
let draftSaved=new Set();
let submittedForm=null;
let registeredDraftForms=new WeakSet();
const navScopes={dashboard:'dashboard.view',pens:'hayvanlar.padok.view',animals:'hayvanlar.kart.view',
  calves:'hayvanlar.buzagi.view','animal-health':'hayvanlar.saglik.view',weighings:'hayvanlar.tartim.view',
  fields:'tarim.parseller.view',seasons:'tarim.uretim.view',items:'stok.urun.view',stock:'stok.hareket.view',
  firms:'firmalar.view',reminders:'ajanda.view',integrations:'entegrasyon.view',documents:'belge.view',stokgiris:'stok.hareket.create',uyarilar:'stok.hareket.view',faturalar:'muhasebe.fatura.view',hesaplar:'hesap.cari.view',maliyetler:'reports.cost.view',personel:'personel.view',hayvancikis:'hayvanlar.kart.edit',belgeaktarim:'belge.view'};
function right(scope){return !!erpSession&&(erpSession.is_admin||erpSession.permissions.includes(scope))}
function sectionAllowed(s){if(s==='users')return !!erpSession?.is_admin;if(s==='audit')return right('audit.view');if(s==='topluhayvan')return ['hayvanlar.kart.create','hayvanlar.kart.edit','hayvanlar.tartim.create'].some(right);
 if(s==='reports')return !!erpSession&&(erpSession.is_admin||erpSession.permissions.some(x=>x.startsWith('reports.')&&x.endsWith('.view')));
 return right(navScopes[s]||'!unknown')}
function authScreen(setup=false,notice=''){
 document.querySelector('#nav').innerHTML='';document.querySelector('#reminderBanner').style.display='none';document.querySelector('#stockAlertBanner').style.display='none';
 const c=document.querySelector('#content');
 c.innerHTML=`<div class="auth-card"><h1>${setup?'İlk Yönetici Hesabı':'KUZUCU ERP — Kullanıcı Girişi'}</h1>
 <p class="sub">${setup?'Bu bilgisayardaki ilk yönetici hesabını oluşturun. Kullanıcı yetkileri buradan yönetilecektir.':'Size verilen kullanıcı bilgileriyle giriş yapın.'}</p>
 ${notice?`<p class="warn">${escapeHTML(notice)}</p>`:''}
 <form id="authForm" autocomplete="on">${setup?`<label>Ad Soyad<input name="display_name" required minlength="2" autocomplete="name"></label>`:''}
 <label>Kullanıcı Adı<input name="username" required minlength="3" maxlength="80" autocomplete="username"></label>
 <label>Şifre<input type="password" name="password" required minlength="10" autocomplete="${setup?'new-password':'current-password'}"></label>
 <button>${setup?'Yöneticiyi Oluştur':'Giriş Yap'}</button></form><p class="muted">Güvenliğiniz için şifrenizi kimseyle paylaşmayın.</p></div>`;
 document.getElementById('authForm').onsubmit=async e=>{e.preventDefault();const f=e.target,d=Object.fromEntries(new FormData(f));
  try{const r=await fetch(setup?'/api/auth/bootstrap':'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
   const x=await r.json();if(!r.ok)throw Error(humanError(x));
   erpSession=x.user;erpCsrf=x.csrf_token;await initAuthorized();
  }catch(err){authScreen(setup,turkishError(err.message))}
 };
}
async function initERP(){
 try{const info=await (await fetch('/api/auth/setup')).json();if(info.needs_setup){authScreen(true);return}
 const me=await fetch('/api/auth/me');if(!me.ok){authScreen(false);return}
 const d=await me.json();erpSession=d.user;erpCsrf=d.csrf_token;erpModules=d.modules||{};await initAuthorized()}
 catch(err){authScreen(false,'Programa bağlanılamadı. Başlatma penceresini kontrol edin.')}
}
async function initAuthorized(){
 if(!Object.keys(erpModules).length){try{const r=await fetch('/api/auth/me');const x=await r.json();erpModules=x.modules||{};erpSession=x.user;erpCsrf=x.csrf_token}catch(_e){}}
 let tools=document.getElementById('erpAccountBar');
 if(!tools){tools=document.createElement('div');tools.id='erpAccountBar';tools.className='erp-account';document.querySelector('header').appendChild(tools)}
 tools.innerHTML=`<span class="erp-user">${escapeHTML(erpSession.display_name)}<small>${erpSession.is_admin?'Yönetici':escapeHTML(erpSession.department||'Kullanıcı')}</small></span><button type="button" id="erpLogout" class="secondary-action">Çıkış Yap</button>`;
 tools.querySelector('#erpLogout').onclick=async()=>{if(draftDirty.size&&!confirm('Henüz sunucuya gönderilmemiş taslak değişiklikleri var. Yine de çıkış yapılsın mı?'))return;
 await fetch('/api/auth/logout',{method:'POST',headers:{'X-CSRF-Token':erpCsrf}});erpSession=null;erpCsrf='';tools.remove();authScreen(false)};
 if(!sectionAllowed(active))active=sections.find(([k])=>sectionAllowed(k))?.[0]||(erpSession.is_admin?'users':'');
 if(active)await render();else document.querySelector('#content').innerHTML='<h2>Henüz erişim yetkiniz yok.</h2><p>Yöneticinizden bölüm yetkisi isteyin.</p>';
 if(right('ajanda.view'))refreshDue();if(typeof refreshStockAlerts==='function')refreshStockAlerts().catch(()=>{});
}
function authHeaders(headers={}){return {...headers,'X-CSRF-Token':erpCsrf}}
function permissionRowsHtml(selected=[]){
 const groups={};for(const [key,label] of Object.entries(erpModules)){const g=label.includes('/')?label.split('/')[0].trim():label;
   (groups[g]??=[]).push([key,label])}
 return Object.entries(groups).map(([group,entries])=>`<div class="perm-group"><h4>${escapeHTML(group)}</h4>
 <table><thead><tr><th>Bölüm / Rapor</th><th>Gör</th><th>Yeni / Sorgu</th><th>Düzenle</th><th>Sil</th><th>Excel / PDF</th></tr></thead><tbody>
 ${entries.map(([key,label])=>`<tr><td>${escapeHTML(label)}</td>${['view','create','edit','delete','export'].map(op=>`<td><input type="checkbox" class="permission-box" value="${escapeHTML(key+'.'+op)}" ${selected.includes(key+'.'+op)?'checked':''} aria-label="${escapeHTML(label+' '+({view:'Görüntüleme',create:'Oluşturma veya sorgulama',edit:'Düzenleme',delete:'Silme',export:'Dosyaya aktarma'}[op]))}"></td>`).join('')}</tr>`).join('')}</tbody></table></div>`).join('')}

let adminUsers=[];
async function usersScreenHtml(){adminUsers=await api('/api/auth/users');return `<h1>Kullanıcılar ve Yetkiler</h1><p class="sub">Her bölüm, işlem ve rapor türü için yetkileri ayrı ayrı seçin. Yetki vermediğiniz bilgiler görünmez.</p>
 <div class="panel"><h3>Kullanıcılar</h3><div class="scroll"><table><thead><tr><th>Kullanıcı</th><th>Ad Soyad</th><th>Departman</th><th>Rol</th><th>Durum</th><th></th></tr></thead><tbody>
 ${adminUsers.map(u=>`<tr><td>${escapeHTML(u.username)}</td><td>${escapeHTML(u.display_name)}</td><td>${escapeHTML(u.department)}</td><td>${u.is_admin?'Yönetici':'Yetkili kullanıcı'}</td><td>${u.is_active?'Aktif':'Pasif'}</td><td><button type="button" class="secondary-action" data-user-edit="${u.id}">Düzenle</button> ${u.id!==erpSession.id?`<button type="button" class="secondary-action" data-user-delete="${u.id}">Kullanıcıyı Sil</button>`:""}</td></tr>`).join('')}</tbody></table></div></div>
 <div class="panel"><h3 id="userFormTitle">Yeni Kullanıcı Ekle</h3><form id="erpUserForm" class="erp-user-form"><input name="id" type="hidden">
 <label>Kullanıcı adı<input name="username" minlength="3" maxlength="80" required autocomplete="off"></label>
 <label>Ad Soyad<input name="display_name" minlength="2" maxlength="120" required></label>
 <label>Departman<input name="department" maxlength="100" placeholder="Örn. Besi"></label>
 <label>Şifre (yeni kullanıcıda zorunlu)<input name="password" type="password" minlength="10" autocomplete="new-password"></label>
 <label class="erp-checkline"><input name="is_active" type="checkbox" checked> Aktif kullanıcı</label>
 <label class="erp-checkline"><input name="is_admin" type="checkbox"> Tam yetkili yönetici</label>
 <div class="permission-table"><h3>Bölüm ve Rapor Yetkileri</h3><p class="muted">Raporların görüntüleme ve dosyaya aktarma izinleri bağımsızdır. Oluştur/Sorgu izni yalnızca rapor türünü görme izniyle birlikte kullanılır.</p>
 ${permissionRowsHtml()}</div><div class="erp-actions"><button type="submit">Yetkileri Kaydet</button><button type="button" class="secondary-action" id="resetUserForm">Yeni Kullanıcı</button></div></form></div>`}
function bindUsersScreen(){const f=document.getElementById('erpUserForm');if(!f)return;
 document.querySelectorAll('[data-user-delete]').forEach(b=>b.onclick=()=>showUserDelete(adminUsers.find(u=>u.id===Number(b.dataset.userDelete))));
 const clean=()=>{f.reset();f.elements.namedItem('id').value='';f.elements.namedItem('username').disabled=false;f.elements.namedItem('password').required=true;
 document.getElementById('userFormTitle').textContent='Yeni Kullanıcı Ekle';document.querySelectorAll('.permission-box').forEach(b=>b.checked=false)};
 document.getElementById('resetUserForm').onclick=clean;clean();
 document.querySelectorAll('[data-user-edit]').forEach(button=>button.onclick=()=>{let u=adminUsers.find(x=>x.id===+button.dataset.userEdit);if(!u)return;
 f.elements.namedItem('id').value=u.id;f.elements.namedItem('username').value=u.username;f.elements.namedItem('username').disabled=false;
 f.elements.namedItem('display_name').value=u.display_name;f.elements.namedItem('department').value=u.department;
 f.elements.namedItem('password').value='';f.elements.namedItem('password').required=false;
 f.elements.namedItem('is_active').checked=u.is_active;f.elements.namedItem('is_admin').checked=u.is_admin;
 document.querySelectorAll('.permission-box').forEach(b=>b.checked=u.permissions.includes(b.value));
 document.getElementById('userFormTitle').textContent='Kullanıcı Düzenle: '+u.display_name;f.scrollIntoView({behavior:'smooth'})
 });
 f.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(f)),id=d.id;delete d.id;
 d.is_active=f.elements.namedItem('is_active').checked;d.is_admin=f.elements.namedItem('is_admin').checked;
 d.permissions=[...document.querySelectorAll('.permission-box:checked')].map(b=>b.value);
 if(d.is_admin&&!confirm('Bu kullanıcıya bütün bölümlere tam yönetici erişimi verilecek. Onaylıyor musunuz?'))return;
 try{if(id){d.new_password=d.password||null;delete d.password}else if(!d.password)throw Error('Yeni kullanıcı için şifre girin.');
 await api('/api/auth/users'+(id?'/'+id:''),{method:id?'PUT':'POST',body:JSON.stringify(d)});
 message('Kullanıcı ve yetkileri kaydedildi.');await render()}catch(err){message(err.message,true)}
 }
}
function showUserDelete(user){
 if(!user)return;
 const dialog=document.createElement('dialog');dialog.style.maxWidth='540px';dialog.style.borderRadius='12px';
 dialog.innerHTML=`<h2>Kullanıcıyı Sil</h2><p><strong>${escapeHTML(user.display_name)} (${escapeHTML(user.username)})</strong> silinecek. Geçmiş işlem kayıtları korunur.</p><form id="deleteUserConfirm" method="dialog"><label>Silinecek kullanıcının şifresi<input type="password" name="password" required autocomplete="off" maxlength="200"></label><p class="warn" id="deleteUserError" hidden></p><button type="submit">Kullanıcıyı Sil</button><button type="button" class="secondary-action" id="cancelUserDelete">Vazgeç</button></form>`;
 document.body.appendChild(dialog);dialog.onclose=()=>dialog.remove();dialog.querySelector('#cancelUserDelete').onclick=()=>dialog.close();
 dialog.querySelector('form').onsubmit=async e=>{e.preventDefault();const password=e.target.elements.password.value;
 try{await api('/api/auth/users/'+user.id,{method:'DELETE',body:JSON.stringify({password})});dialog.close();message('Kullanıcı silindi. Geçmiş işlem kayıtları korundu.');await render()}
 catch(err){const p=dialog.querySelector('#deleteUserError');p.hidden=false;p.textContent=turkishError(err.message);e.target.elements.password.value=''}};
 dialog.showModal();dialog.querySelector('input').focus();
}
async function auditScreenHtml(){const r=await api('/api/auth/audit?limit=250');return `<h1>Kullanıcı İşlem Geçmişi</h1><p class="sub">Kim hangi kaydı ne zaman oluşturdu veya değiştirdi? Eski ve yeni değerleri İncele bölümünde görebilirsiniz.</p><div class="panel scroll"><table><thead><tr><th>Tarih / Saat</th><th>İşlemi yapan</th><th>İşlem</th><th>Bölüm / Kayıt</th><th>Değişen bilgiler</th></tr></thead><tbody>${r.map(x=>`<tr><td>${escapeHTML(new Date(/[zZ]|[+-]\d\d:\d\d$/.test(x.when)?x.when:x.when+'Z').toLocaleString('tr-TR'))}</td><td>${escapeHTML(x.actor)}</td><td>${escapeHTML(x.action_label||'Kayıt işlemi')}</td><td>${escapeHTML(x.entity_label||'Diğer kayıtlar')} · Kayıt ${escapeHTML(x.record_id)}</td><td><details><summary>İncele</summary>${table(x.display_changes||[],[['field','Bilgi'],['before','Önceki'],['after','Yeni']])}</details></td></tr>`).join('')||'<tr><td colspan="5">Henüz işlem yok.</td></tr>'}</tbody></table></div>`}
// Drafts saved server-side for each authenticated user. No browser password storage.
function draftKey(form){return form.dataset.erpDraftKey||`${active}_${form.getAttribute('id')}`.replace(/[^a-zA-Z0-9_-]/g,'_').slice(0,100)}
function draftValues(form){const result={};for(const el of Array.from(form.elements)){
 if(!el.name||el.type==='password'||el.type==='file'||el.type==='submit'||el.type==='button'||el.type==='checkbox')continue;
 if(el.name==='id'&& !el.value)continue;
 result[el.name]=String(el.value||'')}
 return result}
async function writeDraft(form){if(!erpSession||!form?.isConnected)return;
 const key=draftKey(form);if(!draftDirty.has(key))return;
 const r=await fetch(`/api/auth/drafts/${key}`,{method:'PUT',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify({values:draftValues(form)}),keepalive:true});
 if(r.ok){draftDirty.delete(key);draftSaved.add(key)}
}
async function clearSubmittedDraft(){if(!submittedForm)return;
 const key=submittedForm;submittedForm=null;draftDirty.delete(key);draftSaved.delete(key);
 if(draftTimer){clearTimeout(draftTimer);draftTimer=null}
 await fetch(`/api/auth/drafts/${key}`,{method:'DELETE',headers:authHeaders({})});
}
async function mountDrafts(){
 for(const form of document.querySelectorAll('#content form[id]')){
 const formId=form.getAttribute('id');
 if(formId==='reportForm'||formId==='calfReportForm'||formId==='erpUserForm')continue;
 const key=draftKey(form);form.dataset.erpDraftKey=key;
 // restore only when user actually has a stored draft.
 try{const r=await fetch(`/api/auth/drafts/${key}`);if(r.ok){const x=await r.json();const saved=x.values||{};
  if(Object.keys(saved).length){for(const [name,value] of Object.entries(saved)){
   const el=form.elements.namedItem(name);if(el&&el.type!=='password'&&el.type!=='file')el.value=value;
  }draftSaved.add(key)}
 }}catch(_e){}
 if(registeredDraftForms.has(form))continue;registeredDraftForms.add(form);
 form.addEventListener('input',()=>{draftDirty.add(key);if(draftTimer)clearTimeout(draftTimer);
   draftTimer=setTimeout(()=>writeDraft(form).catch(()=>{}),1200) });
 form.addEventListener('change',()=>{draftDirty.add(key);if(draftTimer)clearTimeout(draftTimer);
   draftTimer=setTimeout(()=>writeDraft(form).catch(()=>{}),800) });
 }
}
document.addEventListener('submit',e=>{if(e.target?.getAttribute('id')&&!['reportForm','calfReportForm','authForm','erpUserForm','deleteUserConfirm'].includes(e.target.getAttribute('id')))submittedForm=draftKey(e.target)},true);
window.addEventListener('beforeunload',e=>{if(draftDirty.size){e.preventDefault();e.returnValue=''}});
window.addEventListener('pagehide',()=>{for(const key of draftDirty){const form=[...document.querySelectorAll('#content form[id]')].find(f=>draftKey(f)===key);
 if(form)fetch(`/api/auth/drafts/${key}`,{method:'PUT',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify({values:draftValues(form)}),keepalive:true}).catch(()=>{})}});
