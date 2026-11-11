# KUZUCU ERP — Pilot v0.16.0

Tarım, hayvancılık, stok, fatura/cari ve personel kayıtları için ön test ve geliştirme sürümü. Tüm uygulama metinleri Türkçedir. Güncel kurulum: `MAC_GUNCELLEME_V16.md` (Mac), `KURULUM_WINDOWS_TR.md` (Windows); kolay güncelleme `GUNCELLE_MAC.command` / `GUNCELLE_WINDOWS.bat`. Değişiklikler: `SURUM_NOTLARI_V16.md`. Paket kökündeki devir ve doğrulama belgeleriyle birlikte kullanın.

## Çalıştırma

Mac'te `BASLAT_MAC.command`, Windows'ta `BASLAT_WINDOWS.bat` başlatıcısını kullanın. Önceki verileri taşımadan önce eski programı kapatıp bütün klasörü yedekleyin. Python 3.11–3.13 gerekir; test edilen bağımlılıklar `requirements.constraints.txt` içindedir.

Geliştirici kurulumu:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -c requirements.constraints.txt
python tools/start_local.py
```

Windows sanal ortamı `.venv\Scripts\python.exe` yolundadır. Yerel adres `http://127.0.0.1:8000`; veritabanı varsayılan `ciftlik.db` dosyasıdır. `DATABASE_URL` özel yol tanımlıyorsa güncellemede aynı kaynağı koruyun.

## Mevcut işlevler

- Grup, hayvan kartı, tartım; atomik toplu giriş/grup değişimi/tartım ve kesim/ölüm/satış çıkışı.
- Buzağı giriş/fiyat/süt dönemi, grup bazında mama litre/yem kg, çoklu küpeyle çıkış ve performans.
- Süreli sağlık planı, gerçek uygulama kaydı, ilaç-tekrar uyarısı ve günlük PDF.
- Parsel/sezon, yeni parselde görsel seçme ve mevcut görselleri koruma.
- Stok giriş/çıkış/düzeltme, alarm/kalıcı uyarılar, incelenmiş Excel `.xlsx` aktarımı.
- Alış/satış faturası, KDV hariç fiyat ve ayrı vergi toplamı; onaylı stok/cari etkisi, düzeltme/iptal izleri; kasa/banka hesap kartı ve ödeme/tahsilat.
- Faturalı alışlardan ağırlıklı ortalama fiyat ve tahmini stok maliyeti; fiyatı bilinmeyen miktarın ayrımı.
- Personel, mesai, haftalık/yıllık izin ve işe giriş/çıkış; kullanıcı tarafından girilen izin hakkına göre bakiye.
- N gün/hafta/takvim ayında bir hatırlatma; bölüm/işlem/rapor yetkileri, oturum doğrulaması, Türkçe denetim geçmişi ve SQLite yedeği.
- Fotoğrafla küpe adaylarını kontrol etme, belge önizleme ve kontrol edilerek kontrollü fatura kaydı/firma belgesi/mevcut hayvan tartımına aktarma. Görsel okuma için Tesseract ek kurulumu gerekir.

## Veri koruma ve sınırlar

Kaynak ZIP özel veritabanı, işletme fotoğrafı, parola, rapor çıktısı veya sanal ortam içermez. `ciftlik.db`, `data/parcel_images`, `data/documents`, `raporlar` ve yedek klasörlerinizi ayrı koruyun. SQLite yedeği dosya arşivini kapsamaz. Geçmiş mama kg verisi litreye çevrilmez; bilinmeyen fiyat/grup/süt dönemi tahmin edilmez.

Bu sürüm yerel pilottur. Fiziksel Mac/Windows/telefon kabul testi, bağımsız üretim güvenliği, çok kullanıcılı PostgreSQL geçişi, NAS, tam maliyet dağıtımı, maaş bordrosu ve gerçek SAP/banka/e-posta/e-fatura bağlantıları ayrı çalışmalardır. Bu paket ERP'yi veya Codex ortamını internete açmaz. Telefonun Mac'e erişimi ayrıca kurulmalıdır; `127.0.0.1` yalnız o cihazdır. OCR sonucunu insan kontrolü olmadan kaydetmeyin.

## Test ve geliştirme

Gerçek kayıtları kullanmadan ayrı geçici `DATABASE_URL`, `KUZUCU_BACKUP_DIR`, `KUZUCU_REPORT_DIR` ve `KUZUCU_DOCUMENT_DIR` seçip `python -m pytest -q` çalıştırın. Son birleşik test sonucu kökteki `SURUM_DOGRULAMA.md` içindedir. Playwright/Chromium ile tarayıcı denemeleri isteğe bağlı geliştirme araçlarıdır.

`AGENTS.md`, kökteki `GELISTIRME_LISTESI.md` ve `KUZUCU_ERP_PROJE_DEVIR_NOTLARI.md` çalışma kurallarını taşır. Yeni talepleri listeleyin; yeni açık **Son sürümü hazırla** komutu gelmeden kod/sürüm üretmeyin. iPad'de geliştirme için kökteki `IPAD_ILE_DEVAM.md` dosyasını izleyin.

## Önceki sürümlerin tarihçesi

Aşağıdaki notlar tarihîdir; eski sürüm sınırlamalarını güncel v0.16 durumu gibi yorumlamayın.

## Sürüm 0.2: DelPro / Excel için CSV içe aktarma önizlemesi

DelPro'nun hangi veri dışa aktarma seçeneklerini desteklediği kurulum/sürüme bağlı olduğundan **doğrudan API bağlantısı kurulmadı**. Bunun yerine Excel'den UTF-8 CSV olarak kaydedilen dosyaların okunmasını ve kontrol edilmesini sağlayan *salt-okunur önizleme* uç noktası eklendi. Bu uç nokta veritabanına yazmaz.

- `POST /api/imports/animals/preview`: `Content-Type: text/csv` ile UTF-8 CSV gövdesi gönderilir.
- Algılanabilen eşanlamlı sütunlar: küpe, ırk, giriş tarihi, giriş kilosu ve padok.
- Kontroller: boş/tekrar eden hayvan numaraları, mevcut veritabanıyla çakışmalar, tarih ve pozitif kilo doğrulaması.
- Örnek şablon: `templates/delpro_hayvan_ornek.csv`.
- İsteği komut satırından denemek için:
  `curl -X POST http://127.0.0.1:8000/api/imports/animals/preview -H 'Content-Type: text/csv' --data-binary @templates/delpro_hayvan_ornek.csv`
- İlk 100 soruna kadar raporlanır, dosya boyutu 2MB ve kayıt sınırı 10.000'dur.

**Not:** `giris_tarihi` ISO `YYYY-MM-DD` biçimindedir. DelPro'dan gelen gerçek dosyadaki kolon adlarını görmeden birebir eşleşme garanti edilmez. Excel arayüzündeki CSV tarih/bölgesel biçimleri dönüştürülmelidir. Herhangi bir gerçek toplu içe aktarma işlemi için yetkilendirme, eşleştirme, işlem günlüğü ve geri dönüş senaryoları henüz geliştirilmedi.

## KZC ERP v0.3: Türkçe rapor sorguları ve SAP uyumlu tasarım

- Tarayıcı başlığı ve ana ekran adı **KZC ERP** oldu.
- **Akıllı Raporlar** menüsünden Türkçe arama yapılır. Şu anda kural tabanlı ve yalnızca desteklenen sorguları çalıştırır; ChatGPT/LLM bağlantısı yoktur.
- Hayvan, padok, stok, parsel ve tartım raporları ekranda listelenir ve Excel ile açılabilen UTF-8 CSV olarak indirilir.
- `POST /api/reports/query` gövdesi: `{"query":"aktif hayvanları listele"}`.
- `POST /api/reports/export.csv` aynı gövdeyi alır.
- **Entegrasyonlar** ekranında SAP Business One / S/4HANA mimari durumu açıklanır. Canlı SAP bağlantısı **henüz yoktur**.
- Bağlantı ve veri eşleştirme yaklaşımı `SAP_ENTEGRASYON_PLANI.md` dosyasında.
- Güvenlik notu: Pilot uygulamada kurumsal kullanıcı giriş ve yetkilendirme sistemi henüz olmadığı için internete açık canlı kullanım **uygun değildir**.

## v0.4 Kantar / Fatura Mutabakatı
API üzerinden kantar fişi, depo kabulü, fatura satırı ve miktar farkı karşılaştırma özelliği eklendi.
Bkz. `KANTAR_FATURA_MUTABAKAT.md`. E-posta otomatik toplama bu sürümde yer almaz.


## v0.7 Stok hareketleri
Ürün bazında tarih sıralı hareket geçmişi, ürün ve birim bazında son toplamlar, Türkçe binlik ayırıcı. Mac güncelleme adımları: `MAC_GUNCELLEME_V07.md`.

## v0.8 Firmalar ve stok düzeltme
- Firma kayıtları: ad, vergi numarası, telefon, adres; arama ve düzenleme.
- Stok hareketi düzeltme: tarih, ürün, miktar, giriş/çıkış, referans; düzeltme nedeni ve geçmişi.
- Negatif bakiye engeli ve kaydedilen geçmiş değişiklik kayıtları.
- Mac güncelleme rehberi: `MAC_GUNCELLEME_V08.md`.

## v0.9 — Ajanda ve giriş uyarıları

- Tek seferlik, günlük, haftalık ve aylık hatırlatmalar için `Ajanda / Hatırlatmalar` menüsü eklendi. Hatırlatma saati geldiğinde program açıkken üst çubukta uyarı gösterilir. Program kapalıyken işletim sistemi, e-posta veya SMS bildirimi **yoktur**.
- Aşırı stok miktarı ve ileri tarihli hareket girişine kullanıcı onayı istendi; aynı ürün ve belgeyle mükerrer hareket engellenir; yanlış verilerde anlaşılır alan uyarıları gösterilir.
- Ayrıntılar için `MAC_GUNCELLEME_V09.md` dosyasını okuyun.


## v0.11 — Hayvan Sağlığı, Buzağı büyütme ve Parsel görseli

Kurulum, yeni menüler, günlük PDF çıktısı, toplu çıkış hesaplamaları ve veri aktarımı adımları için `MAC_GUNCELLEME_V11.md` dosyasını okuyun.

## Mac pilot v0.13 (04.11.2026)

**Başlamadan önce `MAC_GUNCELLEME_V13.md` dosyasını okuyun.**

Bu sürüm ilk yönetici oluşturma, oturum açma, bölüm ve rapor erişim denetimi, işlem geçmişi,
otomatik taslak ve çevrim içi SQLite yedeği, aramalı ırk seçimi ve işletme küpesiyle
bireysel seçimden toplu buzağı çıkışı içerir. Eski `ciftlik.db` dosyasını önceden
yedekleyip yeni klasöre kopyalayarak kayıtlarınızı koruyabilirsiniz.

Çalışan yazılım **yerel pilot** olduğundan, canlı çok kullanıcılı işletme sunucusuna
bağlamadan önce bağımsız güvenlik, veritabanı, yedek geri yükleme ve kullanım testi gereklidir.
