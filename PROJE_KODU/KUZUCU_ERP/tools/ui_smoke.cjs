/* Yalnız yeni, boş, yerel DENEME veritabanında çalıştırın. Playwright gerekir. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

async function run() {
  const base = process.argv[2], evidence = process.argv[3];
  if (!base || !evidence || !['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) throw Error('Ayrı, boş bir yerel deneme sunucusu ve çıktı klasörü belirtin.');
  await fs.mkdir(evidence, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH || undefined });
  const report = { version: '0.15.0', checks: [], viewports: [], javascriptErrors: [], failedResources: [], draftRequests: [] };
  let page;
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR' });
    page = await context.newPage();page.setDefaultTimeout(15000);
    const watch = p => { p.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/auth/drafts/'))report.draftRequests.push(new URL(r.url()).pathname)});p.on('pageerror', e => report.javascriptErrors.push(e.message));p.on('dialog', d => d.accept());p.on('response', r => {if(r.status()>=400&&new URL(r.url()).pathname.startsWith('/static/'))report.failedResources.push({url:r.url(),status:r.status()})}); };
    watch(page);
    const health = await (await context.request.get(base + '/api/health')).json();
    assert.equal(health.status,'ok');assert.equal(health.version,'0.15.0');assert.match(health.instance_id,/^[a-f0-9]{64}$/);
    assert.equal((await (await context.request.get(base + '/api/auth/setup')).json()).needs_setup, true, 'Bu test mevcut kullanıcı veritabanında çalıştırılamaz.');
    const responseFor = (route, method) => page.waitForResponse(r => new URL(r.url()).pathname === route && r.request().method() === method);
    async function settled(){await page.waitForTimeout(100);await page.waitForLoadState('networkidle');}
    async function nav(key,ready){await page.locator(`nav [data-key=${key}]`).click();await page.locator(ready||'#content h1').first().waitFor();await settled();assert.equal(await page.getByText('İşlem açılamadı',{exact:true}).count(),0);}
    async function fill(form,values){for(const [name,value]of Object.entries(values))await page.locator(`${form} [name=${name}]`).fill(value);}
    async function submit(selector,route,method='POST',expected=201){const p=responseFor(route,method);await page.locator(selector).click();const r=await p;if(r.status()!==expected)assert.equal(r.status(),expected,await r.text());const d=r.status()===204?null:await r.json();await settled();return d;}
    const today=new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Istanbul'}),yesterday=new Date(Date.now()-86400000).toLocaleDateString('sv-SE',{timeZone:'Europe/Istanbul'});
    await page.goto(base);
    await fill('#authForm',{display_name:'Tarayıcı Denemesi',username:'arayuzdenemesi',password:crypto.randomBytes(24).toString('base64url')});
    await page.locator('#authForm button').click();await page.locator('nav [data-key=fields]').waitFor();await settled();assert.match(await page.title(), /v0\.15/);
    report.checks.push('Boş veritabanında ilk yönetici oluşturma ve v0.15 açılışı');

    await nav('fields','#parcelEntryForm');
    await fill('#parcelEntryForm',{ada_no:'101',code:'UI-1',name:'Deneme Tarlası',area_decare:'35,5'});
    const image=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=32;c.height=32;const p=c.getContext('2d');p.fillStyle='#347844';p.fillRect(0,0,32,32);return c.toDataURL('image/png').split(',')[1]});
    await page.locator('#parcelNewImage').setInputFiles({name:'deneme.png',mimeType:'image/png',buffer:Buffer.from(image,'base64')});
    await page.locator('#parcelNewImagePreview').waitFor({state:'visible'});
    const field=await submit('#parcelEntryForm button[type=submit]','/api/fields/with-image');
    await page.locator(`[data-parcel-preview="${field.id}"]`).click();
    await page.locator('#parcelPreviewImage').evaluate(img=>img.complete&&img.naturalWidth?true:new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=reject}));
    report.checks.push('Yeni parselde görsel seçme, önizleme, birleşik kayıt ve doğru görseli açma');

    await nav('users','#erpUserForm');
    const userPassword=crypto.randomBytes(24).toString('base64url');
    await fill('#erpUserForm',{username:'silinedeneme',display_name:'Silinecek Deneme',department:'Deneme',password:userPassword});
    const user=await submit('#erpUserForm button[type=submit]','/api/auth/users');
    await page.locator(`[data-user-edit="${user.id}"]`).click();
    assert.equal(await page.locator('#erpUserForm [name=username]').isEnabled(),true);
    await page.locator('#erpUserForm [name=username]').fill('degisendeneme');
    await submit('#erpUserForm button[type=submit]',`/api/auth/users/${user.id}`,'PUT',200);
    await page.getByText('degisendeneme',{exact:true}).waitFor();
    await page.locator(`[data-user-delete="${user.id}"]`).click();
    await page.locator('#deleteUserConfirm [name=password]').fill('yanlisparola');
    await submit('#deleteUserConfirm button[type=submit]',`/api/auth/users/${user.id}`,'DELETE',403);
    assert.match(await page.locator('#deleteUserError').innerText(),/şifresi hatalı/);
    await page.locator('#deleteUserConfirm [name=password]').fill(userPassword);
    await submit('#deleteUserConfirm button[type=submit]',`/api/auth/users/${user.id}`,'DELETE',200);
    await page.waitForFunction(id=>!document.querySelector(`[data-user-delete="${id}"]`),user.id);
    report.checks.push('Kullanıcı adı düzenleme; yanlış hedef şifresinde red, doğru hedef şifresinde silme');

    await nav('reminders','#reminderForm');
    await fill('#reminderForm',{title:'İki haftada bir deneme işi',interval_count:'2',remind_time:'09:00'});
    await page.locator('#reminderForm [name=frequency]').selectOption('weekly');
    const reminder=await submit('#reminderForm button[type=submit]','/api/reminders');
    assert.equal(reminder.interval_count,2);assert.match(await page.locator('#content').innerText(),/Her 2 haftada bir/);
    await submit(`[data-delete-reminder="${reminder.id}"]`,`/api/reminders/${reminder.id}`,'DELETE',204);
    await page.waitForFunction(id=>!document.querySelector(`[data-delete-reminder="${id}"]`),reminder.id);await page.waitForFunction(()=>!document.querySelector('#reminderBanner').textContent.includes('İki haftada bir deneme işi'));assert.ok(!(await page.locator('#message').getAttribute('class')||'').includes('error'));
    report.checks.push('Her iki haftada bir hatırlatma ve güvenlik başlıklı silme');

    await nav('items','#entry');await fill('#entry',{code:'UI-ARPA',name:'Deneme Arpası'});await page.locator('#entry [name=unit]').selectOption('kg');
    const item=await submit('#entry button','/api/items');
    await nav('stock','#entry');await page.locator('#entry [name=quantity]').fill('30000');assert.equal(await page.locator('#entry [name=quantity]').inputValue(),'30.000');
    const movement=await submit('#entry button','/api/stock-movements');assert.equal(movement.quantity,'30000.000');
    await page.waitForFunction(()=>document.querySelector('.stock-item-group')?.textContent.includes('30.000'));
    await nav('stokgiris','#finSettings');await page.locator('#finSettings [name=category]').selectOption('rawmaterial');await page.locator('#finSettings [name=alarm_threshold]').fill('50.000');
    await submit('#finSettings button',`/api/finance/items/${item.id}/settings`,'PUT',200);
    await nav('uyarilar','[data-fin-ack]');await page.locator('[data-fin-ack]').click();await settled();assert.match(await page.locator('#content').innerText(),/Onaylandı/);
    report.checks.push('Türkçe stok miktarı, hammadde alarm seviyesi, kalıcı uyarı ve onay sonrası görünürlük');

    await nav('calves','#calfForm');
    for(const [tag,sex]of [['UI-CALF-1','male'],['UI-CALF-2','female']]){
      await fill('#calfForm',{tr_ear_tag:tag,farm_ear_tag:tag==='UI-CALF-1'?'C01':'C02',group_no:'C-GRUP',entry_date:yesterday,entry_kg:'45,5',purchase_price_tl:'12.500,50'});
      await page.locator('#calfForm [name=sex]').selectOption(sex);await page.locator('#calfForm [name=milk_phase]').selectOption('true');
      const c=await submit('#calfSave','/api/calves');assert.equal(c.purchase_price_tl,'12500.50');
    }
    assert.equal(await page.locator('#calfConsumeForm,#calfWeighForm').count(),0);
    await fill('#calfBulkConsumeForm',{group_no:'C-GRUP',milk_litres:'3,5',feed_kg:'1,25'});await page.locator('#calfFeedLoad').click();await page.locator('[data-feed-calf]').first().waitFor();await page.locator('#calfFeedAll').click();
    assert.match(await page.locator('#calfFeedSummary').innerText(),/2 buzağı seçildi/);
    const feed=await submit('#calfFeedSave','/api/calves/bulk-consumptions','POST',201);assert.equal(feed.count,2);
    await fill('#calfBulkForm',{tr_ear_tags:'UI-CALF-1, UI-CALF-2',group_no:'C-GRUP'});await page.locator('#calfBulkAdd').click();await page.locator('[data-bulk-weight]').first().waitFor();assert.equal(await page.locator('[data-bulk-weight]').count(),2);
    await page.locator('[data-bulk-weight]').nth(0).fill('85,5');await page.locator('[data-bulk-weight]').nth(1).fill('86');
    const exits=await submit('#calfBulkSave','/api/calves/bulk-exit','POST',200);assert.equal(exits.count,2);
    report.checks.push('Buzağı başına TL fiyatı ve süt dönemi; Grup No ile aynı miktarda toplu mama/yem; çoklu küpeyle ayrı kg çıkış');

    await nav('pens','#entry');await fill('#entry',{code:'UI-GRUP',capacity:'20'});const pen=await submit('#entry button','/api/pens');
    await nav('animals','#animalForm');await fill('#animalForm',{tr_ear_tag:'UI-ANIMAL-1',farm_ear_tag:'A01',arrival_date:yesterday,entry_weight_kg:'100'});await page.locator('#animalForm [name=sex]').selectOption('male');await page.locator('#animalForm [name=pen_id]').selectOption(String(pen.id));
    const animal=await submit('#animalSave','/api/animals');
    await nav('animal-health','#healthCaseForm');assert.equal(await page.locator('#healthCaseForm [name=symptoms],#healthCaseForm [name=veterinarian],#healthCaseForm [name=start_date],#healthCaseForm [name=planned_end_date],#healthCaseForm [name=withdrawal_end_date],#healthCaseForm [name=vet_approved]').count(),0);
    await fill('#healthCaseForm',{condition_name:'Deneme kontrol',duration_days:'3',notes:'Sağlık deneme açıklaması'});
    const healthCase=await submit('#healthCaseSave','/api/animal-health/cases');assert.equal(healthCase.duration_days,3);assert.equal(healthCase.start_date,today);
    report.checks.push('Sağlık formunda kaldırılan alanlar yok; üç günlük tedavi kayıt gününden başlıyor');

    await nav('firms','#firmEntryForm');await fill('#firmEntryForm',{name:'Deneme Firması',phone:'5550000000'});const firm=await submit('#firmEntryForm button','/api/firms');
    await nav('faturalar','#finInvoice');await fill('#finInvoice',{invoice_no:'UI-FATURA-1'});await page.locator('#finInvoice [name=firm_id]').selectOption(String(firm.id));await page.locator('#finInvoiceAdd').click();
    await page.locator('[data-fin-line="0"][data-field=quantity]').fill('10');await page.locator('[data-fin-line="0"][data-field=unit_price]').fill('1.000');await page.locator('[data-fin-line="0"][data-field=vat_rate]').fill('20');
    const invoice=await submit('#finInvoiceSave','/api/finance/invoices');assert.equal(invoice.subtotal,'10000.00');assert.equal(invoice.vat_total,'2000.00');assert.equal(invoice.total,'12000.00');
    await submit(`[data-fin-post="${invoice.id}"]`,`/api/finance/invoices/${invoice.id}/post`,'POST',200);
    await nav('hesaplar','#finLedger');assert.match(await page.locator('#content').innerText(),/12\.000/);
    report.checks.push('KDV hariç fiyatla fatura taslağı; KDV/toplam doğrulama, onay ve cari bakiye');

    await nav('personel','#personnelEmployeeForm');await fill('#personnelEmployeeForm',{employee_no:'UI-P01',full_name:'Deneme Personeli',start_date:yesterday});
    const employee=await submit('#personnelCardSave','/api/personnel/employees');
    await fill('#personnelOvertimeForm',{hours:'1,5'});await page.locator('#personnelOvertimeForm [name=employee_id]').selectOption(String(employee.id));
    const overtime=await submit('#personnelOvertimeForm button[type=submit]','/api/personnel/overtime');assert.equal(overtime.hours,'1.50');
    report.checks.push('Personel kartı ve Türkçe ondalıkla mesai kaydı');

    await nav('audit','details');await page.locator('details').first().locator('summary').click();const auditText=await page.locator('#content').innerText();assert.ok(!/erp_users|health_print_runs|permissions_json|is_active|"new"/.test(auditText));
    assert.match(auditText,/Önceki|Yeni/);report.checks.push('İşlem geçmişi bölüm, alan, önceki ve yeni değerlerinin Türkçe gösterimi');
    const error=await page.evaluate(()=>turkishError('Failed to fetch'));assert.ok(!/Failed|fetch/.test(error));
    await nav('reports','#reportForm');await page.locator('#reportQuery').fill('aktif hayvanları listele');
    const animalReport=await submit('#reportForm button[type=submit]','/api/reports/query','POST',200);assert.equal(animalReport.scope,'reports.animals');assert.ok(!animalReport.rows.flat().includes('active'));await page.locator('#reportPhotoArea #photoDocumentForm').waitFor();
    const downloadPromise=page.waitForEvent('download');await page.locator('#reportExport').click();const download=await downloadPromise;const csvPath=path.join(evidence,'hayvan_raporu.csv');await download.saveAs(csvPath);const csv=await fs.readFile(csvPath,'utf8');assert.match(csv,/Aktif/);assert.ok(!/\bactive\b/.test(csv));report.checks.push('Ortak hayvan raporu ve CSV Türkçe; rapor ekranında belge fotoğrafı alanı');

    const ready={dashboard:'.cards',pens:'#entry',animals:'#animalForm',calves:'#calfForm','animal-health':'#healthCaseForm',topluhayvan:'#animalOpsForm',hayvancikis:'#animalOpsForm',weighings:'#entry',fields:'#parcelEntryForm',seasons:'#entry',items:'#entry',stokgiris:'#finExcel',stock:'#stockItemFilter',uyarilar:'#content table',faturalar:'#finInvoice',hesaplar:'#finLedger',maliyetler:'#content table',personel:'#personnelEmployeeForm',firms:'#firmEntryForm',reminders:'#reminderForm',reports:'#reportForm',integrations:'#content h1',belgeaktarim:'#photoDocumentForm',documents:'#documentForm',users:'#erpUserForm',audit:'details'};
    for(const key of Object.keys(ready)){await nav(key,ready[key]);}
    report.checks.push('Yöneticide 26 menü ekranının açılması');
    // Geç biten bir ekran isteği, kullanıcının son seçtiği ekranı değiştiremez.
    await page.route('**/api/personnel/employees*',async route=>{await new Promise(resolve=>setTimeout(resolve,250));await route.continue()});
    const oldRequest=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/personnel/employees');
    await page.evaluate(()=>{window.pendingScreenTest=navigate('personel')});await oldRequest;
    await page.evaluate(()=>navigate('audit'));await page.evaluate(()=>window.pendingScreenTest);await settled();
    assert.match(await page.locator('#content h1').innerText(),/Kullanıcı İşlem Geçmişi/);
    await page.unroute('**/api/personnel/employees*');report.checks.push('Geciken önceki ekran isteği son menü seçimini değiştirmiyor');
    const state=await context.storageState();
    for(const [width,height]of [[768,1024],[1024,768],[390,844]]){
      const tablet=await browser.newContext({viewport:{width,height},isMobile:true,hasTouch:true,locale:'tr-TR',storageState:state});const screen=await tablet.newPage();screen.setDefaultTimeout(15000);watch(screen);await screen.goto(base);await screen.locator('nav').waitFor();
      const measurements=[];
      for(const key of ['fields','calves','users','stock','reminders','animal-health','stokgiris','uyarilar','faturalar','hesaplar','personel','topluhayvan','hayvancikis','belgeaktarim']){
        await screen.locator(`nav [data-key=${key}]`).click();await screen.locator(ready[key]).first().waitFor();await screen.waitForLoadState('networkidle');assert.equal(await screen.getByText('İşlem açılamadı',{exact:true}).count(),0);
        const size=await screen.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));if(size.page>width+1||size.viewport>width+1){await screen.screenshot({path:path.join(evidence,`${width}x${height}-${key}-overflow.png`),fullPage:true});report.overflow={width,height,key,...size};report.overflowElements=await screen.evaluate(width=>[...document.querySelectorAll('#content *')].filter(el=>el.getBoundingClientRect().width>width).slice(0,20).map(el=>({tag:el.tagName,id:el.id,class:el.className,width:el.getBoundingClientRect().width,parent:el.parentElement?.id})),width)}assert.ok(size.page<=width+1&&size.viewport<=width+1,`${width}x${height} ${key}: sayfa taştı ${JSON.stringify(size)}`);measurements.push({section:key,...size});
        if(['fields','faturalar','personel'].includes(key))await screen.screenshot({path:path.join(evidence,`${width}x${height}-${key}.png`),fullPage:true});
      }
      report.viewports.push({width,height,measurements});await tablet.close();
    }
    assert.ok(!report.draftRequests.some(p=>p.includes('object_HTMLInputElement')||p.includes('/users_')),'Kullanıcı formu veya çakışan taslak anahtarı');assert.deepEqual(report.javascriptErrors,[],'Tarayıcı JavaScript hatası');assert.deepEqual(report.failedResources,[],'Eksik statik dosya');
    await fs.writeFile(path.join(evidence,'ui-result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  }catch(error){report.failure=error.message;await fs.writeFile(path.join(evidence,'ui-result.json'),JSON.stringify(report,null,2));if(page)await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true}).catch(()=>{});throw error;
  }finally{await browser.close();}
}
run().catch(error=>{console.error(error);process.exitCode=1;});
