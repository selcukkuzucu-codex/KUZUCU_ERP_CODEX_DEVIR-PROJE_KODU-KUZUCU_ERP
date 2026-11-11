# KUZUCU ERP v0.15.0 — doğrulama raporu

Tarih: 10 Kasım 2026. Aşama: ön test ve geliştirme. Geliştirme/test ortamı Linux ve Python 3.12; fiziksel Mac, Windows veya telefon kurulumu bu ortamda doğrulanmaz.

## Güncel doğrulama durumu

**v0.15.0 pilot paketi hazır. 182 otomatik test geçti; kaynak ve ZIP içinden tarayıcı akışları doğrulandı. Fiziksel cihaz kabulü aşağıdaki açık sınırlar içinde ayrıca yapılmalıdır.**

- Değişiklik öncesi regresyon: **44 test geçti**.
- Birleşik regresyon: **182 test geçti**, başarısız veya atlanan test yok; 78,15 saniye. API, yetki, oturum güvenliği, atomik toplu kayıt, tarih/birim, eski veri koruma ve paketleme kontrolleri kapsandı. Bir mevcut Starlette/httpx kullanımdan kaldırma uyarısı var; bağımlılık çakışması bulunmadı.
- Kaynak ve geliştirme veritabanının değişiklik öncesi yedeği alındı. Gerçek Mac/Windows `ciftlik.db` dosyası bu ortama yüklenmedi.
- Yeni SQLite geçişleri buzağı/sağlık/ajanda alanları ve yeni tablolar ekler. Eski mama kg, boş fiyat/grup/süt dönemi ve geçmiş tıbbi bilgiler tahminle değiştirilmez.
- Paket ayrı klasöre açıldı; sürüm/manifest, özel veri dışlaması, çalıştırılabilir Mac başlatıcı bilgisi ve kaynak byte eşleşmesi doğrulandı. Son teslim ZIP’i aynı test edilmiş uygulama dosyalarını içerir; son değişiklikler doğrulama belgeleridir.

<!-- V015_FINAL_RESULTS_START -->
- **182/182 Python testi geçti**. Çalıştırma: `bash /workspace/kuzucu-cloud/test.sh`; kanıt çalışma dizini `/workspace/kuzucu-cloud/checks/pytest-yrO8F5Vk`. Ayrı deneme veritabanları kullanıldı.
- Eski v0.14 SQLite şemasından **iki açılış** ile eklemeli geçiş, geçmiş mama kg/tıbbi metadata koruması, geçiş öncesi yedekten ayrı SQLite geri yükleme ve bütünlük kontrolü geçti. Yedek alınamayan hedefte geçiş yapılmadan durma doğrulandı.
- Hedef parola ile kullanıcı silme, silinen kullanıcının oturum/taslak iptali, SQLite kullanıcı kimliği yeniden kullanılsa bile eski özel belgeye erişimin reddi ve eşzamanlı işlemlerde son aktif yöneticinin korunması doğrulandı.
- Kaynaktan Chromium/Playwright: **12 akış**, **26 menü**, **42 duyarlı yerleşim kontrolü** geçti. JavaScript hatası veya eksik statik dosya yok. Kanıt: `/workspace/kuzucu-cloud/v015/browser-1ddv5f1u/evidence/ui-result.json`.
- ZIP ayrı klasöre açılıp uygulama **paketin içinden** çalıştırıldı: **13 akış**, aynı 26 menü ve 42 yerleşim kontrolü geçti. Ek kontrol geciken eski ekran isteğinin son menü seçimini bozmamasını doğrular. Kanıt: `/workspace/kuzucu-cloud/v015/browser-u0yoa9mv/evidence/ui-result.json`.
- Görsel parsel kaydı, kullanıcı adı/silme, iki haftalık hatırlatma ve 204 yanıtıyla silme, 30.000 stok, uyarı onayı, her buzağıya 3,5 litre mama/1,25 kg yem, ayrı çıkış kiloları, üç günlük sağlık planı, 10.000 TL ara toplam + 2.000 TL KDV = 12.000 TL fatura/cari, 1,5 saat mesai, Türkçe denetim/CSV ve rapordan fotoğraf alanı tarayıcıyla sınandı.
- Yerleşimler: **768×1024**, **1024×768**, **390×844**; her birinde 14 ekran. Geniş tablolar kendi alanında kayar, sayfa taşmaz.
- ZIP: **97 dosya**, manifestte **96 SHA256 girdisi**; CRC/manifest, uygulama kaynak eşleşmesi ve veri/özel fotoğraf/günlük dışlama kontrolleri geçti. ZIP’in özeti yanında `KUZUCU_ERP_v0.15.0.zip.sha256` olarak teslim edilir. Gerçek kullanıcı veritabanı pakette yok.
<!-- V015_FINAL_RESULTS_END -->

## Paket ve veri koruma

Paketleyici kaynak, test, başlatıcı, şablon, uygulama amblemi ve devir belgelerini seçer. `.env`, veritabanı, özel parsel/evrak/küpe fotoğrafı, ekran görüntüleri, rapor çıktıları, `gunlukler` teknik günlükleri, sanal ortam, önbellek ve Git kimlik bilgileri pakete alınmaz. Özgün ekran referansları kaynak çalışma alanında korunur; yeni ZIP'e katılmaz.

`DOSYA_DOGRULAMA.sha256` içerideki kaynak dosyaların SHA256 listesidir. `PAKET_BILGILERI.json` sürümü, eklemeli şema değişikliği ve özel veri içermediği bilgisini taşır. ZIP'in SHA256'sı ayrı `.zip.sha256` dosyasıdır. Manifest bütünlüğü, işlevsel doğrulamanın yerine geçmez.

Otomatik SQLite yedeği veritabanını kapsar; `data/parcel_images`, `data/documents` ve `raporlar` ayrıca kopyalanmalıdır. Yeni sürüm geçişinde eski program kapatılmalı, bütün eski klasör ve ayrı yedekler korunmalıdır. Yeni kayıtların üstüne eski yedek yazılmaz.

## Açık fiziksel kabul ve ürün sınırları

- Mac/Windows başlatıcılarının fiziksel kurulum ve kullanıcı kabulü; eski gerçek veriyle kayıt sayısı, hesap ve dosya yolu kontrolü yapılmalıdır.
- Üç özgün kullanıcı küpe fotoğrafında bölge ayırma/döndürme ile gerçek Tesseract denemesi tam TR kimliği otomatik çıkarılamadı: **0/3**. Bir örnekte `20013` sayısal adayı bulundu; türü/tamlığı doğrulanmış sayılmaz. Bu örneklerde elle giriş veya daha yakın/düz yeniden çekim gerekir. Sentetik net Türkçe örnekte okuma geçti; gerçek fotoğraf başarı oranı sayılmaz. Kamera/belge API testleri **10/10** geçti; bunlar örtülü rakamı okuduğu iddiası değildir. Özgün görseller ve sonuç JSON'u yalnız özel çalışma dizininde tutulur, kaynak ZIP'e katılmaz.
- Gerçek telefon kamera izni, Safari/iOS, güvenli bağlantı ve Mac'e erişim ayrıca denenmelidir. Telefonun `127.0.0.1` adresi Mac değildir. Bu sürüm internet/özel ağ/alan adı kurulumu yapmaz.
- Personel mesai/izin kaydı bordro değildir; yıllık hak kullanıcı beyanıdır. Finans pilotu resmî muhasebe/e-fatura veya banka bağlantısı değildir. Maliyet ağırlıklı KDV hariç alış fiyatına dayalı tahmindir; fiyatı bilinmeyen stok ayrıca belirtilir.
- Bağımsız üretim güvenliği, çok kullanıcılı veri katmanı, NAS/harici yedek, kapsamlı tarım-besi/yem/ilaç maliyet dağıtımı, gerçek SAP/e-posta/banka bağlantıları ayrı çalışmalardır.
- iPad'de aynı Codex hesap/sohbet erişimi cihaz üzerinde kullanıcı tarafından denenmelidir. Kaynak indirmesi ERP/ortam yayını anlamına gelmez.

## Önceki sürümün doğrulaması — v0.14.0 (tarihî)

Aşağıdaki sonuçlar yalnız v0.14 içindir; v0.15'in doğrulandığı anlamına gelmez.

# KUZUCU ERP v0.14.0 — doğrulama raporu

Tarih: 6 Kasım 2026. Aşama: ön test ve geliştirme. Ortam: Linux, Python 3.12.14.

## Otomatik testler

- Değişiklik öncesi v0.13: **23 test geçti**.
- v0.14 birleşik regresyon: **44 test geçti**, başarısız veya atlanan test yok.
- Eklenenler: 19 Türkçe doğrulama/mükerrer kayıt/sürüm testi, 2 kaynak paketi/veri dışlama/bütünlük testi.
- Bir mevcut Starlette/httpx kullanım dışı bırakma uyarısı var; test başarısızlığı değil.
- `pip check`: çakışan bağımlılık yok. Mac başlatıcısı Bash sözdizimi kontrolünden geçti.
- Mevcut eski SQLite geçişi, yetki/CSRF/rapor ayrımı, toplu buzağı çıkışı ve diğer regresyon testleri bu 44 testin içinde.

Uygulama klasöründe `python -m pytest -q` çalıştırılabilir. Test çalışmasında gerçek `ciftlik.db` yerine ayrı deneme veritabanı ve çıktı dizinleri kullanılmalıdır. Test edilen bağımlılıklar `requirements.constraints.txt` dosyasındadır.

## Gerçek tarayıcı kontrolü

Aday ZIP ayrı bir klasöre açıldı; kendi yeni SQLite veritabanı olan yerel sunucu Chromium/Playwright ile çalıştırıldı. Kod yalnızca kaynak klasöründen okunarak test edilmiş sayılmadı.

- İlk yönetici ekranından deneme hesabı oluşturma ve oturum açma.
- Ekrandan parsel oluşturma, görsel yükleme ve yüklenen görseli açma. Yüklemedeki oturum güvenlik başlığı kontrol edildi.
- Ekrandan ajanda kaydı oluşturma ve silme. Silme isteğinin güvenlik başlığı ve başarılı yanıtı kontrol edildi.
- Stokta `30000` yazıldığında `30.000` görünmesi ve veritabanına `30000.000` olarak kaydedilmesi.
- 768×1024, 1024×768 ve 390×844 ölçülerinde Parseller, Buzağılar, Kullanıcılar/Yetkiler, Stok, Ajanda, Belge Okuma ekranları: sayfa düzeyinde yatay taşma yok. Geniş tablolar kendi kutularında kaydırılır.
- Yakalanan JavaScript çalışma hatası: **0**.

Bu test fiziksel iPad veya Safari testi değildir. Kullanıcının iPad ihtiyacı yalnızca Codex'te geliştirmeye devam etmektir; cihaz üzerinde aynı hesap/sohbet erişimi kullanıcı tarafından denenmelidir.

Tarayıcı kontrolünün kaynağı `PROJE_KODU/KUZUCU_ERP/tools/ui_smoke.cjs` dosyasındadır. Playwright/Chromium bağımlılığı isteğe bağlı geliştirme aracıdır; Python testlerini çalıştırmak için gerekli değildir.

## Paket ve veri koruma

- Paketleyici yalnızca kaynak, test, başlatıcı, şablon, görsel kimlik ve devir belgelerini seçer. `.env`, `ciftlik.db`, özel parsel görselleri, rapor çıktıları, sanal ortam ve Git kimlik bilgileri pakete alınmaz.
- ZIP bütünlüğü ve kaynakla byte eşleşmesi kontrol edilir. Paket içindeki `DOSYA_DOGRULAMA.sha256` dosyası dosya bazında SHA256 listesidir; ZIP'in SHA256'sı ayrı `.zip.sha256` dosyasında verilir.
- Bu sürümde veri modeli değişmedi. v0.13 açılış yedeği ve geriye uyumlu mevcut SQLite sütun geçişleri korunur.
- Bulut geliştirme veritabanının sürüm öncesi yedeği alındı; SQLite bütünlüğü doğrulandı. Gerçek Mac/Windows veritabanı bu ortama aktarılmadı.
- v0.14 koduyla ayrı bir deneme veritabanında parsel/stok kaydı, çıkış-giriş sonrası kalıcılık, Türkçe görsel OCR önizlemesi ve kapanış yedeğinin ayrı dosyaya geri yüklenmesi de geçti. Geri yüklenen SQLite'ta bütünlük ve beklenen kayıtlar kontrol edildi; veritabanı yedeği görsel dosyasını kapsıyor iddiası yoktur.

## Sınırlar

Mac ve Windows başlatıcıları fiziksel cihazda çalıştırılmadı. Gerçek iPad/Codex hesabı erişimi bu oturumdan denenmedi. Tüm işletme senaryoları ve üretim güvenliği için bağımsız denetim yapılmış sayılmaz. Eski yanlış stok miktarları tahminle değiştirilmez; internet/özel ağ/alan adı kurulumu yoktur.

Kod GitHub'a gönderilmedi, Codex ortamı yeniden yayımlanmadı ve ERP canlı kullanıma alınmadı. ZIP'i indirmek kaynakların GitHub'a kaydedilmesiyle aynı şey değildir.
