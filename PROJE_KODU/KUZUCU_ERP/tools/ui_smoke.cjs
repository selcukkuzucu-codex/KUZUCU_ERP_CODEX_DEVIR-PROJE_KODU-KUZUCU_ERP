/* Sadece yeni, boş, yerel DENEME veritabanında çalıştırın. Playwright gerekir. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

async function run() {
  const base = process.argv[2];
  const evidence = process.argv[3];
  if (!base || !evidence || !['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) {
    throw Error('Ayrı, boş bir yerel deneme sunucusu ve çıktı klasörü belirtin.');
  }
  await fs.mkdir(evidence, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH || undefined });
  const errors = [];
  const report = { version: '0.14.0', checks: [], viewports: [] };
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR' });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept());
    const health = await context.request.get(base + '/api/health');
    assert.deepEqual(await health.json(), { status: 'ok', version: '0.14.0' });
    const setup = await context.request.get(base + '/api/auth/setup');
    assert.equal((await setup.json()).needs_setup, true, 'Bu test mevcut kullanıcı veritabanında çalıştırılamaz.');
    await page.goto(base);
    await page.locator('#authForm [name=display_name]').fill('Tarayıcı Denemesi');
    await page.locator('#authForm [name=username]').fill('arayuzdenemesi');
    await page.locator('#authForm [name=password]').fill(crypto.randomBytes(24).toString('base64url'));
    await page.locator('#authForm button').click();
    await page.locator('nav [data-key=fields]').waitFor();
    assert.match(await page.title(), /v0\.14/);

    const responseFor = (route, method) => page.waitForResponse(r => new URL(r.url()).pathname === route && r.request().method() === method);
    await page.locator('nav [data-key=fields]').click();
    for (const [name, value] of Object.entries({ ada_no: '101', code: 'UI-1', name: 'Deneme Tarlası', area_decare: '35,5' })) {
      await page.locator(`#entry [name=${name}]`).fill(value);
    }
    let pending = responseFor('/api/fields', 'POST');
    await page.locator('#entry button').click();
    let response = await pending;
    assert.equal(response.status(), 201, await response.text());
    const field = await response.json();
    await page.locator(`[data-parcel-upload="${field.id}"]`).click();
    const image = await page.evaluate(() => {
      const canvas = document.createElement('canvas'); canvas.width = 32; canvas.height = 32;
      const painter = canvas.getContext('2d'); painter.fillStyle = '#347844'; painter.fillRect(0, 0, 32, 32);
      return canvas.toDataURL('image/png').split(',')[1];
    });
    await page.locator('#parcelUploadForm [name=file]').setInputFiles({ name: 'deneme.png', mimeType: 'image/png', buffer: Buffer.from(image, 'base64') });
    pending = responseFor(`/api/fields/${field.id}/satellite-image`, 'POST');
    await page.locator('#parcelUploadForm button[type=submit]').click();
    response = await pending;
    assert.equal(response.status(), 200, await response.text());
    assert.ok(response.request().headers()['x-csrf-token']);
    await page.locator(`[data-parcel-preview="${field.id}"]`).click();
    await page.locator('#parcelPreviewImage').evaluate(img => img.complete && img.naturalWidth ? true : new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; }));
    report.checks.push('Tarayıcıdan parsel kaydı, güvenlik başlıklı görsel yükleme ve görsel açma');

    await page.locator('nav [data-key=reminders]').click();
    await page.locator('#reminderForm [name=title]').fill('Silinecek deneme işi');
    await page.locator('#reminderForm [name=remind_time]').fill('09:00');
    pending = responseFor('/api/reminders', 'POST');
    await page.locator('#reminderForm button[type=submit]').click();
    response = await pending;
    assert.equal(response.status(), 201, await response.text());
    const reminder = await response.json();
    pending = responseFor(`/api/reminders/${reminder.id}`, 'DELETE');
    await page.locator(`[data-delete-reminder="${reminder.id}"]`).click();
    response = await pending;
    assert.ok([200, 204].includes(response.status()), await response.text());
    assert.ok(response.request().headers()['x-csrf-token']);
    await page.waitForFunction(id => !document.querySelector(`[data-delete-reminder="${id}"]`), reminder.id);
    report.checks.push('Tarayıcıdan ajanda oluşturma ve güvenlik başlıklı silme');

    await page.locator('nav [data-key=items]').click();
    for (const [name, value] of Object.entries({ code: 'UI-ARPA', name: 'Deneme Arpası' })) {
      await page.locator(`#entry [name=${name}]`).fill(value);
    }
    await page.locator('#entry [name=unit]').selectOption('kg');
    pending = responseFor('/api/items', 'POST');
    await page.locator('#entry button').click();
    assert.equal((await pending).status(), 201);
    await page.locator('nav [data-key=stock]').click();
    await page.locator('#entry [name=quantity]').fill('30000');
    assert.equal(await page.locator('#entry [name=quantity]').inputValue(), '30.000');
    pending = responseFor('/api/stock-movements', 'POST');
    await page.locator('#entry button').click();
    response = await pending;
    assert.equal(response.status(), 201, await response.text());
    assert.equal((await response.json()).quantity, '30000.000');
    await page.waitForFunction(() => document.querySelector('.stock-item-group')?.textContent.includes('30.000'));
    report.checks.push('Stok: 30000 girişi → 30.000 görünümü → 30000.000 kalıcı kayıt');

    const state = await context.storageState();
    for (const [width, height] of [[768, 1024], [1024, 768], [390, 844]]) {
      const tablet = await browser.newContext({ viewport: { width, height }, isMobile: true, hasTouch: true, locale: 'tr-TR', storageState: state });
      const screen = await tablet.newPage();
      screen.setDefaultTimeout(15000);
      screen.on('pageerror', error => errors.push(error.message));
      screen.on('dialog', dialog => dialog.accept());
      await screen.goto(base);
      const measurements = [];
      const ready = { fields: '#parcelSearch', calves: '#calfForm', users: '#erpUserForm', stock: '#stockItemFilter', reminders: '#reminderForm', documents: '#documentForm' };
      for (const section of ['fields', 'calves', 'users', 'stock', 'reminders', 'documents']) {
        await screen.locator(`nav [data-key=${section}]`).click();
        await screen.locator(ready[section]).waitFor();
        assert.equal(await screen.getByText('İşlem açılamadı', { exact: true }).count(), 0);
        const size = await screen.evaluate(() => ({ viewport: window.innerWidth, page: document.documentElement.scrollWidth }));
        assert.ok(size.page <= width + 1 && size.viewport <= width + 1, `${width}x${height} ${section}: sayfa taştı ${JSON.stringify(size)}`);
        measurements.push({ section, ...size });
        if (section === 'fields' || section === 'users') await screen.screenshot({ path: path.join(evidence, `${width}x${height}-${section}.png`), fullPage: true });
      }
      report.viewports.push({ width, height, measurements });
      await tablet.close();
    }
    assert.deepEqual(errors, [], 'Tarayıcı JavaScript hatası');
    report.javascriptErrors = errors;
    await fs.writeFile(path.join(evidence, 'ui-result.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}
run().catch(error => { console.error(error); process.exitCode = 1; });
