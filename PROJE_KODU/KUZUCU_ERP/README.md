# KUZUCU ERP — Pilot v0.14.0

Tarla, besi, stok ve yem altyapısı için ön test ve geliştirme sürümü. Arayüz Türkçedir. Güncel kurulum için `MAC_GUNCELLEME_V14.md`, değişiklikler için `SURUM_NOTLARI_V14.md` okuyun. Paket kökündeki `CODEXTE_BASLAT.md` ve `IPAD_ILE_DEVAM.md` geliştirmeye başka cihazdan devam etme adımlarını içerir.

## Kurulum (Python 3.11+)

```bash
cd ciftlik-erp
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt -c requirements.constraints.txt
uvicorn app.main:app --reload
```

Tarayıcıda http://127.0.0.1:8000 açın. API dokümantasyonu: http://127.0.0.1:8000/docs

Veriler varsayılan olarak proje klasöründeki `ciftlik.db` SQLite dosyasında saklanır. Demo veri otomatik oluşturulmaz. PostgreSQL için `DATABASE_URL` ortam değişkenine uygun SQLAlchemy bağlantı adresi verin ve ilgili DB sürücüsünü kurun.

## Mevcut işlevler
- Padok oluşturma ve kapasite kontrolü
- Küpe numarası benzersizliği ile hayvan girişi
- Hayvan bazlı tartım kaydı
- Tarla/parsel kaydı ve yıllık ürün sezonu
- Stok ürünü ve giriş-çıkış hareketi; negatif stok engeli
- Gerçek kayıtlardan yönetici özeti

## Sınırlar — üretim kullanımı için hazır değildir
- Kullanıcı girişi, bölüm/rapor yetkileri, işlem geçmişi, taslak ve SQLite yedekleme vardır. Bağımsız üretim güvenliği denetimi, tam migration sistemi, maliyet motoru, yem reçete/üretim ve gerçek veri içe aktarımı tamamlanmamıştır.
- Stok örneğinde ürünün kendi biriminde işlem yapılır; otomatik kg/ton çevrimi yoktur.
- Aynı anda birden çok operatörün stok çıkışı için satır kilidi ve işlem izolasyonu eklenmelidir.
- İnternet erişimine açmayın; gerçek kişisel/kurumsal üretim verileri ile kullanmayın.
- PostgreSQL için uygulamayı çok kullanıcılı canlı ortama çıkarmadan önce şema migration (Alembic), roller, güvenlik, yedekleme ve yük testleri gerekir.

## Test
```bash
pytest -q
```

## Geliştirme planı
Paket kökündeki `GELISTIRME_LISTESI.md` güncel doğrulama ve geliştirme işlerini içerir. Aşağıdaki bölümler geçmiş sürümlerin tarihçesidir; eski sürümlerdeki eksik özellik açıklamaları güncel durumun tamamı değildir.

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
