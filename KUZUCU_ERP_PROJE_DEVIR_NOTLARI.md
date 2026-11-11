# KUZUCU ERP — Codex Proje Devir Notları

**Güncel devir tarihi:** 10.11.2026 (ilk devir: 05.11.2026)  
**Güncel kaynak sürümü:** v0.15.0; test ve paket durumu `SURUM_DOGRULAMA.md` içinde  
**Proje:** Tek şirketin tarım, besi sığırcılığı ve kendi yem üretimini yönetmek için web ERP.

## Güncel Codex devri — v0.15.0

- Kullanıcı **Son sürümü hazırla** talimatını verdi ve 10 Kasım'da yineledi. Birikmiş v0.14 sonrası talepler için kod geliştirildi; birleşik doğrulama ve ZIP sonucu `SURUM_DOGRULAMA.md` içindedir. Bu komut sonraki sürümler için sürekli izin sayılmaz.
- Güncel kurulum `PROJE_KODU/KUZUCU_ERP/MAC_GUNCELLEME_V15.md`, Windows rehberi ve `SURUM_NOTLARI_V15.md` içindedir. Aşağıdaki v0.14/v0.13 anlatımları **tarihî bağlamdır**; güncel v0.15 modül durumu için kaynak ve testleri okuyun.
- Kullanıcı adı düzenleme, hedef kullanıcının parolasıyla silme, Türkçe denetim görünümü, yeni parselde atomik görsel kaydı; buzağı Grup No/fiyat/süt dönemi, litre ve kg ayrımıyla toplu tüketim, çoklu küpe çıkışı; süreli sağlık ve güncellenen günlük PDF geliştirildi.
- Genel bakış sayımları, toplu hayvan işlemleri/çıkışı, Stok Girişi/kalıcı uyarılar/Excel `.xlsx`, fatura-KDV-stok-cari/kasa/banka hareketleri, açıklamalı tahmini maliyet, personel/mesai/izin ve N dönemli ajanda eklendi. Tam maaş bordrosu, maliyet dağıtım motoru ve resmî muhasebe/e-fatura/banka entegrasyonu değildir.
- Kamera/belge önizlemesi insan kontrolünden sonra mevcut kayda aktarılır. Kapalı küpe rakamları tahmin edilmez; örnek fotoğraflar işletme görüntüleridir ve kaynak/ZIP/GitHub'a katılmaz. Üç özgün fotoğrafta tam TR kimliği otomatik çıkarılamadı (0/3); bir örnekte belirsiz `20013` sayısal adayı bulundu. Sentetik net örnek okuması geçti. Bu örnekler için elle giriş gerekir. Fiziksel telefon bağlantısı ve OCR doğruluğu garantisi verilmez; Tesseract dil dosyaları ek gereksinimdir.
- SQLite'a eklemeli geçişler vardır; açılış öncesi yedek alınır. `ciftlik.db`, `data/parcel_images`, **`data/documents`**, `raporlar` ve eski klasör ayrı korunmalıdır. SQLite yedeği fotoğraf/belge arşivini kapsamaz. Mac'in gerçek veritabanı bu buluta aktarılmadı.
- Eski buzağı süt/mama kg verisi litreye çevrilmez. Bilinmeyen fiziksel grup, hayvan başı fiyat ve süt dönemi boş kalır. Eski sağlık onayı/klinik bilgi/arınma tarihleri form sadeleştiği için silinmez, onay uydurulmaz.
- Mac'teki eski giriş reddinin kök nedeni gerçek veritabanında doğrulanmış değildir; kullanıcı adı ve doğru klasör kontrolü gerekir. Program kapalıyken kullanılabilen yerel parola kurtarma aracı açık operatör onayı ve yedekle çalışır; parolalar sohbetten alınmaz. Yeni başlatıcı doğru klasör sunucusunu tanır, yabancı süreci zorla kapatmaz.
- iPad tercihi hâlâ Codex'te geliştirmedir. Kaynak ZIP'i hazırlamak veya indirme için GitHub dalı oluşturmak ERP/ortam yayını değildir. Ana GitHub dalı, ortamın yayını veya telefon erişimi kendiliğinden yapılmaz. Son teslim bağlantısını ve gerçek Git durumunu ayrıca kontrol edin.

## Önceki devir — v0.14.0 (tarihî)


- Kullanıcı projenin **ön test ve geliştirme** aşamasında olduğunu belirtti ve 6 Kasım'da açıkça son sürümün hazırlanıp indirilmesini istedi. Bu komutla v0.14.0 pilot düzeltme paketi hazırlandı; yeni talepler için yeniden açık sürüm talimatını bekleyin.
- iPad'deki güncel ihtiyaç **yalnızca Codex'te geliştirmeye devam etmek**. ERP'ye evden bağlantı/özel ağ kurulumu bu çalışmanın kapsamında değil. Aynı hesap ve sohbetle devam veya yeni göreve ZIP aktarımı için `IPAD_ILE_DEVAM.md` ve `CODEXTE_BASLAT.md` okuyun.
- Parsel görseli yükleme ve ajanda silmede eksik güvenlik başlıkları düzeltildi. Form doğrulamaları, mükerrer kayıt ve stok yönü uyarıları Türkçeleştirildi; tablet yerleşimi ve tarayıcı önbelleği sürümlendi.
- Veritabanı modeli değiştirilmedi; gerçek Mac verileri aktarılmadı. Yeni sürüme geçişte DB, parsel görselleri ve raporları ayrı koruyun.
- Ayrıntılı test kanıtı ve sınırlar `SURUM_DOGRULAMA.md` içindedir. Başlangıç v0.13 için 23 test geçmişti; yeni sürüm sonucunu o belgeden okuyun.
- Kaynaklar yüklenen ZIP'ten çalışma alanına alındı. GitHub'a commit/push, ortamı yeniden yayımlama, canlı sunucu veya alan adı kurulumu yapılmadı. Kaynakların yeni Codex görevinde bulunduğunu doğrulayın.
- Aşağıdaki v0.13 devir bilgileri geçmiş bağlamı korur; güncel dosyalar ve v0.14 sürüm notları önceliklidir.

## 1. Kodun durumu ve önemli sınırlar

- `PROJE_KODU/KUZUCU_ERP/` klasöründe v0.13'ten ilerletilen **v0.14.0 pilot kaynak kodu**, HTML/CSS/JavaScript arayüzü, FastAPI/SQLAlchemy uygulaması ve testler bulunur.
- Bu ZIP, kullanıcı Mac bilgisayarındaki canlı **`ciftlik.db` dosyasını, gerçek verileri, fotoğraf arşivini veya şifrelerini** içermez. Bunları aktarılmış gibi varsayma. Mac'teki eski dosyaları silme.
- Koddaki mevcut işlevler için `MAC_GUNCELLEME_V13.md`, `MAC_GUNCELLEME_V12.md`, `MAC_GUNCELLEME_V11.md`, `README.md` oku. README'nin eski sürüm açıklamaları eskimiş olabilir; güncel gerçek durum için kodu ve testleri incele.
- v0.13, localhost (`127.0.0.1:8000`) Mac yerel pilotudur; halka açık / çok kullanıcılı üretim için hazır olduğu iddia edilmemeli.
- `pytest -q` testi çalıştır. Önceki sohbette 23 testin geçtiği belirtilmişti; bu ortamda tekrar doğrula.

## 2. İşletme ve hedef mimari

- İş birimleri: **Tarım/bitkisel üretim** (yaklaşık 1.000–5.000 dekar), **Besi sığırcılığı** (yaklaşık 2.000–5.000 baş) ve **kendi hayvanlarına yem üretimi**. Tek şirket içinde tarım ve besi maliyet merkezleri ayrı izlenmeli, iç transferlerde çift sayım yapılmamalı.
- 21–50 civarı personel, aylık maaşlar, izin/mesai, günlük işler; Excel/manual kayıtlar. DeLaval **DelPro FarmManager** kullanılıyor; DelPro'daki Grup alanı fiziksel **Grup No / padok** anlamına gelir.
- Kullanım: Mac ve Windows tarayıcı, iPad/iPhone. Kullanıcı ofiste çalışıp evden iPad ile aynı veriye ulaşmak istiyor. Yerel pilot sonrasında güvenli özel ağ veya uygun sertleştirilmiş bulut sunucu; alan adı planı `erp.kuzucusut.com` ancak henüz kurulu canlı sistem değil. Veri tabanı ileride bulut, yerel yedek NAS/ofis PC.
- İleride SAP Business One/S/4HANA uyumlu entegrasyon mimarisi; **SAP şu anda kullanılmıyor**.
- Kullanıcının görünüm tercihi: boğa kafası logosu, **KUZUCU / ERP System**, yeşil-altın palet.

## 3. Kullanım akışı ve en kritik iş kuralı

Kullanıcı özellikleri sohbet içinde parça parça bildirir. **Açıkça “Son sürümü hazırla” demeden her istekte sürüm yapma, kodlama ya da paket üretme.** Yeni talepleri `GELISTIRME_LISTESI.md` içine ekle. Birikmiş talepleri birlikte değerlendirin. Kullanıcı açıkça sürümü istediğinde geliştirme + test + sağlam yedek/migration + tek paket yap.

Önceki v0.13'ten Codex'e ilk geçiş yalnızca proje aktarımıydı. Ardından kullanıcı 6 Kasım'da açık sürüm talimatı verdiği için v0.14.0 hazırlandı. Bu geçmiş komutu sonraki her görev için devam eden sürüm/paketleme veya yayınlama izni saymayın.

## 4. Mevcut / planlanan modüller ve gereksinimler

### Tarım / Parseller
- Ada No, Parsel No/Kodu, tarla adı, alan/dekar, ada-parsel araması. Parsel kartına **uydu fotoğrafı** yükleme/gösterme ve aramada görüntü erişimi. İleride il, ilçe, köy/mahalle, harita, uydu parsel sınırları.
- Ekim, hasat, maliyet, üretim, ayrı tarım maliyet merkezi.

### Hayvanlar / Besi
- **TR Küpe No** ve **İşletme Küpe No** farklı alanlar; doğum tarihi, yaş **gün ve ay**, cinsiyet, ırk (yazdıkça aranan liste, yeni ırk eklenebilmesi), giriş kg, giriş tarihi, fiziksel Grup No/padok.
- Hayvan girişi, çıkış, tartım, padok hareketi, DelPro/Excel CSV aktarım önizleme/ileride güvenli içe aktarma.

### Buzağılar
- Besiden ayrı buzağı giriş/çıkış akışı: satın alım giriş kilosu, cinsiyet, tarih, açıklama (**Parti/Alım Grubu değil**), isteğe bağlı yaklaşık 30–60 gün veya farklı gün süreli süt/mama dönemi.
- Günlük süt/mama ve yem tüketimi kg; her buzağının çıkış kilosu ve süresi.
- Toplu buzağı çıkışı: **“Parti seçin” yok**. **İşletme Küpe No** yazıldıkça eşleşen buzağı önerilir; seçileni geçici alt listeye ekle; listeden çıkarabilme; aynı buzağıyı ikinci kez eklememe; her hayvana ayrı **çıkış kg**; ortak çıkış tarihi; kullanıcı tanımlı **Toplu Çıkış No**; **Toplu Kaydet**. Bir kayıtta hata varsa tüm işlemi iptal et (transaction/atomic).
- Rapor: giriş kg, çıkış kg, fark, gün sayısı, ortalama **günlük canlı ağırlık artışı (kg/gün)**, **çıkış/giriş kilo oranı (kat)**; toplu numara ve tarihe göre karşılaştırma; Excel/PDF/CSV (yetkiye tabi).
- İPTAL EDİLMİŞ İSTEK: "Toplu Buzağı Çıkış Kaydı" ekranında iki tarih aralığı girip çıkış yapılmış buzağıları getirerek seçme. **Bu ayrı eski isteği uygulama.** Geçmiş çıkışların raporunda tarih filtresi geçerli olabilir.

### Hayvan Sağlığı / Tedavi / Aşı
- Hayvan bazlı hastalık/belirti, durum, aşı, tedavi, ilaç, veteriner protokolü, doz, gün, tarih, uygulayan, sonuç. Tedavi ve ilaç adları kayıtlar arttıkça **seçilebilir ve yazdıkça aranabilir kalıcı listede** biriksin.
- Aynı hayvana son **10 gün** içinde farklı tedavi kaydında **aynı ilaç** uygulanmışsa uyarı. Aynı devam eden tedavide planlı günlük dozlar gereksiz uyarı üretmesin. İlaç adı üzerinden kontrol etken madde eşdeğerliği değildir; veri modelini güçlendirmek ileri gereksinim.
- Günlük devam eden tedaviler, aşılar, günlük görev/ajanda birleşik listesi, A4/PDF/isteğe bağlı otomatik yazdırma.
- Sonuç veren/uzayan tedavilerin geçmiş kayıtlarından veteriner karar desteği; otomatik reçete/dose veya kesin etkinlik vaadi yok. İlaç, aşı, premiks, vitamin maliyetlerini gerçek fatura birim fiyatlarından hayvan/grup/tüm hayvanlara dağıtma planı.

### Stok, Yem, Kantar, Firmalar
- Stok giriş/çıkış hareketlerinde `30000` ve `30.000` girildiğinde **30.000** görünmeli, asla 30.000.000'a dönüşmemeli. Binlik ayırıcı nokta, ondalık virgül. Hem veri girişi hem DB hem liste doğru olmalı; yanlış eski DB kaydı otomatik tahminle düzeltilmemeli.
- Her ürün ayrı ve tarih sıralı hareket listesi; her ürünün toplam giriş/çıkış/bakiye altta. Kg, ton, adet gibi farklı birimler birbirine karıştırılmamalı. Eski hareketleri **Düzenle** ile düzeltebilme ve değişiklik geçmişi.
- Firma kartları: firma adı, vergi no, telefon, adres. Kantar fişi ve sonradan gelen alış/satış faturası arasında miktar-fiyat-mutabakatı ve uyarı.
- Özel şirket mail sunucusuna PDF/fotoğraf faturalar gelir. Gelecekte güvenli mail bağlanması + OCR/evrak çıkarımı + kontrol edilmiş taslak cari, stok, fatura ve hareket; otomatik kontrolsüz kayıt oluşturma önerilmez.
- Yem üretim reçetesi, tüketim, maliyet dağıtımı; tarım iç transferleri.

### Ajanda / Hatırlatmalar
- Tek seferlik, günlük, haftalık, aylık tekrar; günlük yapılacak işler, tamamlanınca sonraki tekrar, sağlık günlük listesiyle birleşme. Program kapalıyken bildirim gönderebilmek için gelecekte sunucu/mesaj altyapısı gerekir; yerel pilot çalışırken bildirim.

### Kullanıcı Girişi, Rol / Yetki ve Rapor Güvenliği
- Yönetici kullanıcı oluşturur, kullanıcı adı/güvenli şifre, aktif/pasif ve bölüm/işlem bazlı yetki tanımlar.
- Bölümler: Tarım, Hayvanlar/Besi/Buzağı/Sağlık, Stok/Yem/Kantar, Raporlar (her rapor **ayrı yetki**), Muhasebe/Finans, Hesap Bilgileri (banka/kasa/cari/borç alacak), Personel, Ajanda, Ayarlar.
- Gör, Oluştur, Düzenle, Sil, Rapor Sorgula, PDF/Excel/CSV Dışa Aktar gibi yetkiler. Sadece menüyü gizleme yeterli değil: **sunucu/API/CSV/PDF/natural language raporları** için de denetim. Her rapor türüne ayrı izin; yetkisiz veriye doğal dil raporla erişim yok. İlk varsayılan yetki kapalı.
- İşlem/hareket listelerinde **Kaydeden / İşlemi Yapan** sütunu. Oturumdan otomatik alınır; kayıt tarih-saat. Düzenleyen/silen ve önce/sonra değerleri ayrıca audit log. Geçmiş kayıtların bilinmeyen kullanıcısını uydurma. Üretimde değiştirilemez merkezi kayıt sistemi gerekir.
- Muhasebe/banka/maaş gibi henüz geliştirilmemiş bölümlerin sadece yetki taslakları var; canlı modül sanma.

### Kayıt güvenliği / Yedek
- Kaydet ile anında kalıcı kayıt, formlarda güvenli otomatik taslak, kaydedilmemiş değişikliklerde kapanış uyarısı, beklenmedik kapanışta mümkün olduğunca kurtarma.
- Veritabanı sürüm geçişinde yedek ve migration. Kapanışta yedek, çalışırken periyodik yedek, mümkünse NAS/harici yedek ve geri yükleme denemesi. Elektrik kesintisinde %100 son an kaydı garanti edilemez.
- Mac v0.13 otomatik yedek yolu: `~/Documents/KUZUCU_ERP_Yedekler`; gerçek canlı DB genellikle proje kökünde `ciftlik.db`.

### Raporlama / Personel / Muhasebe
- Türkçe doğal dil akıllı rapor isteği; mevcut pilot kural tabanlıdır, LLM entegrasyonu yoktur. Tarım, hayvan hareketi, buzağı performansı, tedavi, stok, maliyet, finans, personel raporları; tümünde satır/sütun ve rapor yetkileri.
- Personel kartları, izin (yıllık/haftalık), mesai, puantaj Excel/manüel, günlük not, toplu giriş, maaş; ileride geliştirilecek.
- Muhasebe/finans, banka, cari, hesap bilgileri: kullanıcı bazlı hassas yetki, faturaların stok/kantar bağlantısı; modüller henüz tam uygulanmış değil.

## 5. Bilinen sorunlar ve geliştirme prensipleri

- Kullanıcı özellikle **Parseller ekranında kayıt hatası** ve İngilizce/teknik uyarı gördüğünü bildirdi. Kök neden inceleme/test gerektirir; yalnızca hata mesajını Türkçeye çevirmek yeterli değil.
- Mac'te eski sürümün çalışıp son değişikliklerin görünmemesi yaşandı; doğru klasör, sürüm göstergesi, çalışan süreç, Chrome `Command+Shift+R` kontrol edilmeli.
- Miktar biçimi bug'ı eski verileri bozmuş olabilir: görüntü düzeltmesi kaydedilmiş yanlış `30000000` miktarı kendiliğinden `30000` yapmaz. Veri düzeltme araçları açık onay + yedek gerektirir.
- Veri korumak için kullanıcı istemedikçe eski Windows verilerini Mac'e aktarma. Kullanıcı bu aktarımı istemediğini söylemişti.
- Python 3.12.10 macOS'a yüklenmişti. Mac başlangıç: `bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"`; Chrome `http://127.0.0.1:8000`. Yeni Mac taşınmasında bu yol örnektir.
- iPad evden bağlantısı **henüz yapılmadı**; ileride Tailscale/özel ağ veya sertleştirilmiş bulut, çok kullanıcılı veri katmanı değerlendirmesi. `127.0.0.1` yalnızca aynı cihazda çalışır; portu doğrudan internete açma.
- İşletim sistemleri Mac ve Windows. Önce yerel pilot; güvenlik ve veri bütünlüğü testi sonrası çok kullanıcılı üretim mimarisi.

## 6. Codex ile ilk çalışma sırası

1. Bu notları, `AGENTS.md`, `MAC_GUNCELLEME_V13.md`, kod dosyalarını oku.
2. Mevcut Python uygulamasını kurup **`pytest -q`** çalıştır; eksik bağımlılıkları belirle. Bu belgeyi uygulamanın gerçekten çalıştığının kanıtı sayma.
3. Mevcut modüller ve yapılmamış işler için gerçeğe uygun durum envanteri çıkar; `GELISTIRME_LISTESI.md` güncelle.
4. Kullanıcı yeni talep verdikçe sadece backlog'a ekle. **“Son sürümü hazırla”** komutunda uygulama, migrasyon, regresyon testleri, güvenlik kontrolleri ve yeni ZIP oluştur.
5. Gerçek `ciftlik.db` Codex'te gerekli olursa kullanıcıdan ayrı dosya aktarımı iste; gizli bilgi/kişisel veri içerebileceğini hatırla, yedek al ve hassas verileri kod deposuna commit etme.
