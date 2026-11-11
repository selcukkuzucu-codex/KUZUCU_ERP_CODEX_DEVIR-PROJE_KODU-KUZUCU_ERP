# KUZUCU ERP v0.16.0 — 12 Kasım 2026

Ön test ve geliştirme sürümü. Kullanıcının **"Son sürümü hazırla"** talimatıyla 11 Kasım'da biriken talepler uygulandı. Test sonuçları paket kökündeki `SURUM_DOGRULAMA.md` dosyasındadır.

## Görünüm ve menü
- **Yeni tema:** koyu yeşil menü, yeşil ana düğmeler, altın vurgular, beyaz kartlar. Düğmeler ve kutular en az 44 piksel yüksekliğinde (iPad'de parmakla rahat kullanım). **Logo değişmedi.**
- **Gruplu sol menü:** Ana Sayfa · Hayvanlar · Tarım · Stok · Muhasebe · Personel · Raporlar · Ajanda · Belgeler · Yönetim. Başlığa tıklayınca alt sayfalar açılır; açtığınız gruplar hatırlanır. Menüde **sayfa arama** kutusu ve en altta **son yedek saati** var.
- Tablet ve telefonda menü **☰** düğmesiyle açılıp kapanır.
- Inter yazı tipi programla birlikte gelir; internet olmadan da aynı görünür.

## Ana Sayfa (eski adı "Genel Bakış")
- Hızlı işlem düğmeleri: **+ Tartım Gir**, **+ Stok Girişi**, **+ Tedavi Kaydı** (yalnız yetkisi olana görünür).
- Özet kartlar: aktif besi hayvanı, ortalama günlük artış (son iki ölçüm), **yem stoğu kaç gün yeter** (hammadde türündeki ürünlerin son 30 günlük çıkışına göre), cari borç/alacak.
- **Kontrol edilmesi gerekenler:** eksiye düşmüş stok, onay bekleyen stok uyarıları, kapasitesi aşılan gruplar, 45 günden uzun süredir tartılmayan hayvanlar, çıkıştan sonra tartım girilmiş hayvanlar, bitiş tarihi geçmiş açık tedaviler. Her biri ilgili sayfaya götürür.
- **Bugün yapılacaklar:** zamanı gelen ajanda kayıtları.
- Her kart ve uyarı kullanıcının yetkisine göre hesaplanır; yetkisi olmayan bilgi gönderilmez.

## Stok
- **Stok Girişi ekranından yeni ürün:** "+ Yeni Stok Ürünü" penceresinde kod, ad, birim (kg / ton / adet / litre), tür ve uyarı seviyesi girilir. Kaydedince ürün otomatik seçilir; yazdığınız tarih ve miktar silinmez.
- Aynı ürün kodu veya adı (büyük/küçük harf, boşluk, I/İ farkı gözetilmeden) ikinci kez açılamaz. Birim yalnız kg, ton, adet, litre olabilir.
- Stok eksiye düşecekse mesaj artık eldeki ve istenen miktarı açıkça yazar.

## Muhasebe
- **Cariler** tek sayfa: firma kartları (ad, vergi no, telefon, adres) + ödeme/tahsilat + cari bakiyeler + hesap hareketleri. Eski "Firmalar / Cariler" ve "Hesaplar / Cariler" kayıtlarının hiçbiri silinmedi.
- **Kasa / Banka** ayrı sayfa: hesap kartları ve bakiyeler.
- Alış faturasında birim fiyat önceki onaylı alışların ortalamasının 3 katından fazla veya üçte birinden az ise ya da KDV oranı alışılmışın dışındaysa onay istenir.

## Raporlar
- **Hayvan Çıkış Raporu** (yeni sayfa): tarih aralığı, neden (kesim / ölüm / satış / buzağı çıkışı), bölüm (besi / buzağı); hazır aralıklar (bu ay, geçen ay, son 30 gün, bu yıl, tüm zamanlar); toplam baş ve kg; Excel/CSV ve yazdırma.
- Çıkışı yapılmış hayvanların kayıtları silinmez; geçmiş her tarih aralığı için aranabilir. **Buzağı çıkışları da** rapora girer.
- **Akıllı Raporlar** cümledeki tarihi anlar: "1 Ekim ile 31 Ekim arasında kesilen hayvanlar", "Ekim 2026", "geçen ay ölen hayvanlar", "bu yıl", "son 30 gün", "01.10.2026 - 15.10.2026". Anlaşılan tarih aralığı rapor başlığında görünür. Tarih kutuları doluysa onlar geçerlidir.
- "Kesilen", "ölen", "satılan" gibi yazımlar da hayvan çıkışı olarak tanınır.

## Hatalı ve olağandışı girişler
- **Kesin hatalar kaydedilmez:** ileri tarihli tartım/giriş, giriş tarihinden önceki tartım, çıkışı yapılmış hayvana tartım veya yeni sağlık kaydı, stoğu eksiye düşüren çıkış.
- **Olağandışı ama mümkün değerler onay ister** (Tamam = yine de kaydet, İptal = düzelt): besi hayvanında 30 kg altı / 1.200 kg üstü tartım veya giriş kilosu, son ölçüme göre günde 1 kg'dan fazla kayıp veya 3 kg'dan fazla artış, aynı gün ikinci tartım, 300 kg üstü buzağı girişi, 20.000 dekarı aşan parsel, fiyatı ortalamadan çok farklı alış faturası.

## Yedek
- **Her "Çıkış Yap"ta yedek** alınır. Yedek alınamazsa giriş ekranında Türkçe uyarı çıkar.
- Eski yedekler düzenli temizlenir: son 2 günün tamamı, 30 güne kadar her günün son yedeği, daha eskilerde her ayın son yedeği ve her durumda en yeni 20 yedek saklanır. Yalnız programın kendi yedek dosyaları silinir.
- **Yönetim → Yedekler** (yalnız yönetici): son yedek saati, yedek klasörü, saklanan yedek sayısı, **Şimdi Yedek Al** düğmesi.

## Kolay güncelleme
- Yeni sürüm klasöründeki **GUNCELLE_MAC.command** / **GUNCELLE_WINDOWS.bat**: eski program açıksa durur; mevcut kurulumun **tam yedeğini** (veritabanı bütünlüğü kontrol edilerek) `Belgeler/KUZUCU_ERP_Yedekler` altına alır; yalnız program dosyalarını yeniler; `ciftlik.db`, `data`, `raporlar` yerinde kalır; sonra programı açar. Eski sürüme geri yükleme yapmaz.

## Önceki düzeltmeler (11 Kasım)
- Parsel dekar kutusu Türkçe sayı kabul eder (`12,5` artık 125 olmuyor, `1.250` artık 1,25 olmuyor). Tartımdaki kg kutusu da düzeldi.
- Parsel kodu boşluk ve büyük/küçük harf farkıyla ikinci kez açılamaz; 3'ten fazla ondalık reddedilir.
- Program gün hesaplarını her yerde Türkiye saatine göre yapar.

## Veri ve sınırlar
- Bu sürüm veritabanına **yeni tablo veya sütun eklemez**; v0.15 geçişleri aynen korunur. Açılışta yine önce yedek alınır.
- Eski yanlış dekar/stok miktarları otomatik düzeltilmez; listeleri gözden geçirip **Düzenle** ile düzeltin.
- Arınma (kesim yasağı) koruması kullanıcı isteğiyle eklenmedi.
- Fiziksel Mac/Windows/iPad kurulumu bu bulut ortamında denenmedi. Resmî muhasebe, e-fatura, banka, SAP bağlantısı ve telefon erişimi bu sürümde yoktur.
