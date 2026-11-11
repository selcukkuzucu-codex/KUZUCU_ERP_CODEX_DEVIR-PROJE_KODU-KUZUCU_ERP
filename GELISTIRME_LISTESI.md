# KUZUCU ERP — Codex Geliştirme Listesi

## İş akışı
Yeni talep geldikçe buraya ekle; kullanıcı **“Son sürümü hazırla”** demeden uygulama sürümü üretme.

## 10 Kasım 2026 — v0.15 güncel durum

Kullanıcı **Son sürümü hazırla** talimatını verdi ve 10 Kasım'da yineledi. Aşağıdaki işlevler kaynakta uygulandı; son birleşik kabul ve ZIP durumu `SURUM_DOGRULAMA.md` belgesinde izlenir. Tarihî talep bölümlerindeki kutular ve “henüz yapılmadı” ifadeleri, talebin ilk kaydedildiği zamana aittir; güncel durum için bu bölüm ve kaynak esas alınır.

| Alan | Güncel kapsam | Açık doğrulama / sınır |
|---|---|---|
| Türkçe metinler | İşlem geçmişi bölüm/alan/durum açıklamaları, ortak ağ/doğrulama mesajları | 26 menü, Türkçe denetim/CSV ve 42 yerleşim kontrolü geçti |
| Parsel | Yeni kayıtla isteğe bağlı görsel, önizleme, atomik kaydetme, eski görselleri koruma | Fiziksel cihaz kabulü |
| Kullanıcılar | Kullanıcı adını düzenleme, hedef hesabın parolasıyla silme, oturum/taslak iptali, geçmişi koruma | Birleşik yetki testleri geçti; Mac'teki eski giriş reddi gerçek DB'de tanılanmadı |
| Buzağı | Grup No, TL/baş alış fiyatı, açık süt dönemi; toplu mama litre/yem kg; çoklu küpeyle numarasız çıkış; ara tartım/tekil tüketim formunu kaldırma | Eski kg kayıtları korunur, eksik grup/fiyat/süt durumu tahmin edilmez |
| Sağlık | Süreli sade form, kayıt gününden başlayan günlük liste/PDF, Sağlık etiketi | Plan gerçek uygulama veya verilmiş veteriner onayı sayılmaz |
| Genel bakış | Yetkili aktif erkek/dişi/ırk ve süt içen buzağı sayımı; aynı TR'yi çift saymama | Eski bilinmeyen süt/cinsiyet bilgileri kullanıcı tarafından tamamlanmalı |
| Toplu hayvan | Çoklu küpe, tartım/grup değişimi/yeni giriş ve kesim/ölüm/satış çıkışı | Hatalı satırda kısmi kayıt yok; fiziksel veri kabulü |
| Stok | Stok Girişi, ürün sınıfı/eşik, kalıcı uyarılar ve onaydan sonra 24 saat; incelenmiş Excel `.xlsx` aktarımı | İşletim sistemi/SMS/e-posta bildirimi yok; eski `.xls` desteklenmez |
| Fatura/cari | KDV hariç fiyat, KDV/toplamlar, taslak/onay/düzeltme/iptal; stok/cari/kasa/banka hareketleri | Resmî muhasebe/e-fatura veya otomatik banka bağlantısı değil |
| Maliyet | Ağırlıklı KDV hariç alış ortalaması, fiyatı bilinmeyen stok ayrımı | Tam yem/ilaç/tarım-besi maliyet dağıtımı yok |
| Personel | Kart, işe giriş/çıkış, mesai, haftalık/yıllık izin ve kullanıcı tanımlı hak/bakiye, raporlar | Bordro/maaş veya hukuki hak otomatik hesabı yok |
| Ajanda | Her N gün/hafta/takvim ayında bir; eski kayıtlar aralık1 | Program kapalıyken dış bildirim yok |
| Kamera/belge | Küpe adaylarını düzeltip kayıtla eşleştirme; belgeden kontrollü fatura kaydı/firmaya belge/mevcut hayvan tartımı aktarma | Gerçek 3 örnekte tam TR kimliği 0/3; bir örnekte belirsiz sayısal aday bulundu, elle kontrol/giriş gerekir. Fiziksel telefon/HTTPS kabulü ve Tesseract kurulumu ayrıca |
| Yerel başlatma/kurtarma | Doğru sunucu/klasör kontrolü; hazır olduktan sonra tarayıcı; yedekli yerel parola yenileme | Mac/Windows fiziksel kurulum denenmeli; yabancı süreç zorla durdurulmaz |

- [x] Son birleşik test: 182 geçti; geçiş/geri yükleme ve kaynak/paket tarayıcı sonucu `SURUM_DOGRULAMA.md` içine işlendi.
- [x] Son ZIP ayrı klasöre açıldı; içerik/manifest, özel veri dışlaması ve paket içinden çalıştırma doğrulandı. SHA256 dosyası yanında hazırlandı.
- [ ] Fiziksel Mac/Windows cihazında kullanıcı kabulü ve gerçek eski kayıt/dosya sayısı kontrolü.
- [ ] Gerçek telefonda kamera izni, güvenli bağlantı ve okunamayan küpede düzeltme kontrolü. Bu madde internet/özel ağ yayını izni değildir.
- [ ] iPad'de aynı Codex hesap/sohbet erişiminin kullanıcı tarafından denenmesi.

## Öncelikli inceleme / doğrulama
- [x] Aktarılan v0.13 uygulaması koddan incelendi; başlangıçtaki 23 test yeniden geçti.
- [ ] Parsel kaydında karşılaşılan hata için yeniden üretilebilir test ve kök neden analizi.
- [ ] Stokta Türkçe sayı biçimleme ve eski yanlış miktarlar için güvenli düzeltme akışı.
- [ ] Kullanıcı bazlı yetkilerin tüm API/rapor/CSV uç noktalarında güvenlik denetimi.
- [ ] Kayıt/yedeklerin geri yüklenebilirliği, kapanış/elektrik kesintisi senaryoları.
- [ ] Toplu buzağı çıkışında transaction, aynı hayvanın iki kez eklenmesi ve performans hesapları.
- [ ] Tablet/iPad duyarlı tasarım ve ileride güvenli uzaktan erişim (şimdilik kurulum ertelendi).

## Daha uzun vadeli ürün işleri
- [ ] DelPro gerçek CSV formatlarıyla güvenli içe aktarma, Grup No eşleştirmesi.
- [ ] Kantar-fatura e-posta/PDF/görüntü iş akışı ve gözden geçirilen fatura taslakları.
- [ ] İlaç/tedavi etken maddesi eşleştirme ve maliyet dağıtımı; veteriner onay akışı.
- [ ] Yem üretimi, reçeteler, tüketim, tarım-besi iç maliyet transferleri.
- [ ] Personel, maaş, izin, günlük işler, toplu giriş. Personel/mesai/haftalık-yıllık izin/işe giriş-çıkış ve raporlar için kullanıcının yeni somut talepleri aşağıda ayrıca ayrıntılandırıldı; henüz geliştirilmiş sayılmasın.
- [ ] Muhasebe, banka, hesap bilgileri, hassas rapor yetkileri. Alış/satış faturası, KDV, cari bakiye ve maliyetler için güncel talepler aşağıdadır; yeni kayıt ve hesap altyapısı gerektirir.
- [ ] NAS yedek, PostgreSQL, migration, eşzamanlı işlem bütünlüğü, izole bulut üretim sistemi.

**Not:** Önceki tüm kullanıcı taleplerinin kapsamı `KUZUCU_ERP_PROJE_DEVIR_NOTLARI.md` dosyasındadır. Bu liste, kodda mevcut olduğu iddia edilen işlevlerin doğrulandığı anlamına gelmez.

## 6 Kasım 2026 — v0.14.0 pilot düzeltme sürümü

- [x] Açık kullanıcı talimatıyla yeni pilot sürüm hazırlandı; proje ön test ve geliştirme aşamasında.
- [x] Parsel görseli yüklemede eksik CSRF başlığı düzeltildi. Genel parsel kaydı hatasının bütün olasılıkları çözülmüş sayılmıyor.
- [x] Ajanda silmenin güvenli ortak istek yolunu kullanması sağlandı.
- [x] Teknik alan adları yerine Türkçe doğrulama ve mükerrer kayıt mesajları eklendi.
- [x] Tablet yerleşimi ve statik dosya sürümleme iyileştirildi; ayrıntılı tarayıcı sonucu `SURUM_DOGRULAMA.md` içinde.
- [x] Kurulum sürüm kısıtları, Mac güncelleme ve iPad/Codex devam rehberi eklendi.
- [x] Özel veri içermeyen, bütünlük listeli kaynak paketi oluşturmak için paketleyici ve testleri eklendi.
- [ ] Gerçek Mac/Windows cihazında yeni ZIP'in kullanıcı kabul testi.
- [ ] Kullanıcının iPad'inde aynı Codex hesabı/sohbet ile devam edebildiğinin cihaz üzerinde kontrolü.

iPad tercihi: **yalnızca Codex'te geliştirme**. ERP'yi evden erişime açma veya Tailscale kurulumu bu sürüm için istenmiyor. Ortam/GitHub/web yayımlaması yapılmayacak. Sonraki yeni talepleri listelemeye devam edin.

## v0.14 sonrası talep kayıtları ve kabul ölçütleri (tarihî başlangıç durumu)

Bu bölüm taleplerin ilk kaydedildiği durumu korur. Kullanıcının açık sürüm talimatı sonrasında güncel uygulama durumu üstteki v0.15 tablosuna taşınmıştır; buradaki eski bekleme ifadeleri yeniden uygulama talimatı değildir.

### Öncelikli: kullanıcıya görünen bütün uygulama metinleri Türkçe

- [ ] Kullanıcının kesin dil isteği: uygulamanın ürettiği hiçbir ekran, uyarı, hata, başarı, doğrulama, işlem ayrıntısı veya raporda İngilizce cümle, ham teknik alan/tablo/durum kodu görünmesin.
- [ ] Kullanıcı İşlem Geçmişi'nde bölüm adları Türkçe gösterilsin: `erp_users #1` → **Kullanıcılar / Kayıt No: 1**; `health_print_runs #1` → **Günlük Sağlık Çıktıları / Kayıt No: 1**. Diğer tüm kayıt türleri de kapsansın.
- [ ] “İncele” ayrıntısı ham veri dökümü göstermesin. Alan adları, önceki/yeni değer başlıkları, evet/hayır ve durumlar anlaşılır Türkçe sunulsun; `new`, `is_active`, `active`, `male`, `female` gibi sistem anahtarları doğrudan görünmesin.
- [ ] Eski işlem geçmişi kayıtları da yeni Türkçe gösterimden yararlansın. Teknik tablo adları ve mevcut denetim verileri değiştirilmeden, kayıt bütünlüğü ve yetki kontrolleri korunarak sunum katmanı düzenlensin.
- [ ] Yeni/bilinmeyen bir alan veya durum için ham İngilizce koda geri dönüş olmasın; Türkçe genel açıklama kullanılsın. Gerekli teknik hata bilgileri hassas veri açığa çıkarmadan günlükte tutulabilsin.
- [ ] Arayüz yanında rapor ekranı, CSV/Excel ve PDF çıktıları da denetlensin. Hayvan raporunda `active`, buzağı çıkış CSV'sinde `male/female` Türkçe karşılıklarıyla gösterilsin.
- [ ] Ağ kesintisi, bozuk sunucu yanıtı, dosya okuma ve yazıcı hatalarında ham tarayıcı/sistem İngilizcesi kullanıcıya yansıtılmasın. Uygun Türkçe açıklama ve yapılacak işlem sunulsun.
- [ ] “Parsel ID” gibi teknik etiketler “Parsel” veya “Parsel kayıt numarası” olarak sadeleştirilsin. Uygulama tarafından üretilen metinler çevrilirken kullanıcıların girdiği kişi/firma/ırk/ilaç adları ve özgün belge içerikleri değiştirilmesin.
- [ ] Kabul kontrolleri: örnek ve eski işlem kayıtları, “İncele”, bilinmeyen kayıt türü/durum, rapor/çıktı, ağ hatası ve yazıcı hatası için Türkçe gösterim testleri; Türkçe karakter, sayı ve tarih görünümü de korunsun.

İncelemede doğrulanan kaynaklar: `app/static/security-ui.js` içindeki `auditScreenHtml` ham `entity` ve değişiklik verisini gösteriyor; `app/reports.py` hayvanın ham durumunu rapora veriyor; `app/calf.py` çıkış CSV'sine ham cinsiyeti yazıyor. Tarayıcı hata aktarımları ve yazıcı hata gösterimi de kapsamda.

### Yeni parsel formunda arazi görseli seçme/yükleme

- [ ] Kullanıcının Parseller ekranındaki **Yeni parsel** bölümüne, mevcut alanların yanında anlaşılır Türkçe **Arazi Görseli Seç** alanı eklensin. Fotoğraf veya uydu ekran görüntüsü parsel oluşturulurken seçilebilsin; görsel isteğe bağlı olsun.
- [ ] Seçilen görselin önizlemesi, dosyayı değiştirme ve seçimi kaldırma seçenekleri bulunsun. Desteklenen biçim/boyut bilgileri Türkçe gösterilsin; mevcut JPEG/PNG/WEBP ve boyut/çözünürlük doğrulamaları korunsun.
- [ ] **Parsel Kaydet** akışı bilgileri ve seçilen görseli doğru parsel kaydıyla ilişkilendirsin. Dosya doğrulama/yükleme hatasında tam başarı mesajı verilmesin; form ve seçim mümkün olduğunca korunsun, yeniden denemede mükerrer parsel oluşmasın.
- [ ] Kaydın listesinde görsel açma/değiştirme ve mevcut kayıtlar için **Görsel Ekle** işlevleri korunsun. Yetki, oturum güvenlik başlığı, görsel işleme ve mevcut dosyaları koruma kuralları sürsün.
- [ ] Kabul kontrolleri: görselsiz kayıt, geçerli görselle yeni parsel, geçersiz/aşırı büyük görsel, hata sonrası yeniden deneme ve doğru parselin görselini açma/değiştirme.

Mevcut v0.14 davranışı: yeni parsel formunda dosya seçimi yoktur; önce parsel kaydedildikten sonra oluşan liste satırındaki **Görsel Ekle** ile yükleme yapılabilir. Kullanıcının görüntüsünde henüz kayıt olmadığından bu satır düğmesi görünmüyor. Talep, mevcut özelliği kaldırmak yerine yeni kayıt sırasında daha görünür ve birleşik bir yükleme akışı eklemektir.

### Mac'te ana ekran açılırken genel sunucu hatası — tanı bekliyor

- [ ] Kullanıcı daha önce Mac'te v0.14'ü açabildiğini gösterdi; 6 Kasım'daki sonraki açılışta `127.0.0.1:8000/` ana adresinde uygulamanın genel hata yanıtı görüntülendi. Tarayıcı sunucuya ulaşabiliyor; bu görüntü tek başına kök nedeni kanıtlamıyor.
- [ ] Programı başlatan Mac Terminal'indeki son hata ayrıntısı alınarak dosya yolu/erişim, çalışan süreç ve diğer olasılıklar ayırt edilsin. Klasör taşınması veya iCloud dosya erişimi olasılıktır; doğrulanmış neden olarak sunulmasın. Önce veri kaybettirmeyen çalışma/başlatma kontrolleri yapılsın.
- Tanı güncellemesi: Terminal görüntüsünde yeni başlatmanın 8000 bağlantı noktası kullanımda olduğu için durduğu görüldü. Kullanıcının salt okunur kontrolleriyle Python 5949 işleminin KUZUCU ERP uygulama klasöründen çalıştığı doğrulandı; bu sürece düzgün kapanış sinyali verip aynı klasörden yeniden başlatma adımları iletildi. Bu, önceki ana sayfa 500 yanıtının iç nedenini tek başına kanıtlamaz.
- [ ] Kod düzeltmesi gerekirse yeniden üretilebilir hata ve test ile sonraki açık sürüm talimatında uygulansın. Mevcut kaynak, kurulum belgeleri ve kayıtlar tanı için korunmalı; veritabanını silme/sıfırlama önerilmemeli.

### 7 Kasım 2026 — kullanıcı girişi reddediliyor (tanı sürüyor)

- [ ] Mac'teki v0.14 giriş ekranında **Kullanıcı adı veya şifre hatalı.** yanıtı görüldü. Kaynakta aynı mesaj bulunamayan kullanıcı, pasif hesap veya eşleşmeyen şifre için kullanılıyor; bu görüntü tek başına kod hatasını kanıtlamıyor.
- [ ] Önce çalışan uygulamanın veritabanındaki kullanıcı adları ve aktiflik durumu salt okunur sorguyla kontrol edilsin. Şifre/şifre özeti istenmesin, gösterilmesin veya sohbetten alınmasın; ad-soyad ile kullanıcı adının farklı olabileceği dikkate alınsın.
- [ ] Sonuca göre doğru hesap ve veritabanı yolu doğrulansın. Kullanıcı kayıtlarını silme, boş veritabanıyla değiştirme veya giriş denetimini kaldırma yoluna gidilmesin. Gerekirse yerel, yedekli hesap kurtarma adımları ayrı değerlendirilir.

### 7 Kasım 2026 — kullanıcı silme ve kullanıcı adını değiştirme

Yeni özellik talepleridir; henüz uygulanmadı. **“Son sürümü hazırla”** talimatında diğer birikmiş taleplerle birlikte uygulanıp test edilecek. Bu istekler mevcut giriş hatasının nedenini kanıtlamaz veya belirli bir hesabın şu anda silinmesi için talimat sayılmaz.

#### Silinecek kullanıcının parolasıyla silme

- [ ] **Kullanıcılar ve Yetkiler** listesindeki her uygun hesap için **Kullanıcıyı Sil** düğmesi eklensin. Mevcut yönetici yetkisi denetimi korunsun.
- [ ] Kullanıcı 7 Kasım'da açıkça **silmek istediği kullanıcının kendi parolasının** doğrulanmasını seçti. İşlemi yapan yöneticinin parolasıyla karıştırılmasın; kullanıcıya **Silinecek kullanıcının parolasını girin** açıklaması gösterilsin.
- [ ] Silme hedefi açıkça gösterilsin. Parola girilmeden veya hedef hesabın parolası sunucuda doğrulanmadan silme yapılmasın. Yanlış/eksik parola anlaşılır Türkçe uyarıyla reddedilsin; hiçbir kısmi değişiklik kalmasın.
- [ ] Yetki ve oturum güvenlik doğrulaması yalnızca ekrandaki düğmeye bağlı kalmasın; sunucuda da denetlensin. Parola form taslağına, tarayıcı saklama alanına, işleme geçmişine veya günlüğe yazılmasın; şifre/şifre özeti kullanıcıya gösterilmesin.
- [ ] Mevcut kendi yönetici hesabını kapatma ve son aktif yöneticiyi koruma kuralları silmede de korunsun. Kullanıcının oluşturduğu işletme kayıtları ve geçmiş denetim kayıtları silinmesin; kaydeden bilgileri korunmalı. Hedef hesabın açık oturumları ve kişisel taslakları tutarlı biçimde ele alınsın; silinen hesap yeniden giriş yapamasın.
- [ ] Kabul testleri: doğru hedef parolasıyla silme, başka hesabın/yanlış/boş parolayla reddetme, yetkisiz/oturumsuz ve güvenlik başlıksız istek, son yönetici/kendi hesabı koruması, eski işlem kayıtlarının ve işletme verilerinin korunması, silinen hesabın oturumunun iptali.

#### Kullanıcı adını değiştirme

- [ ] Yönetici, **Yetkileri Düzenle** ekranında mevcut kullanıcının **Kullanıcı adı** alanını değiştirebilsin; mevcut pasif alan kısıtı kaldırılıp sunucu güncelleme desteği eklensin.
- [ ] Kullanıcı adı Ad Soyad alanından ayrı kalmalı. Boşluk, uzunluk ve benzersizlik doğrulaması; hesap oluşturma ve girişteki mevcut normalleştirme kurallarıyla tutarlı olmalı. Başka bir hesapta kullanılan ad Türkçe uyarıyla reddedilsin.
- [ ] Kullanıcı adı değişince aynı hesabın kimliği, parolası, yetkileri ve işletme kayıtları korunmalı. İşlem geçmişine kimin hangi kullanıcı adını değiştirdiği kaydedilsin; eski denetim kayıtları geriye dönük yeniden yazılmasın.
- [ ] Kabul testleri: değişen kullanıcı adıyla aynı parolayla giriş, eski adla girişin reddi, mükerrer/geçersiz adın reddi, yetkisiz değişikliğin reddi ve kayıt/yetki/geçmiş bütünlüğünün korunması.

Mevcut kaynak incelemesi: `app/static/security-ui.js` kullanıcı düzenlerken kullanıcı adı alanını devre dışı bırakıyor ve güncelleme isteğinden çıkarıyor; `app/security.py` içindeki kullanıcı güncelleme modeli kullanıcı adı kabul etmiyor. Mevcut sürümde hesap silme işlemi bulunmuyor; yalnızca pasifleştirme var. Bu nedenle iki istek de arayüz ve sunucu tarafını kapsamalı.

### 7 Kasım 2026 — Grup No ile buzağılara toplu yem/mama girişi

Kullanıcı tek tek günlük tüketim girişi yerine grup üzerinden toplu giriş istedi. Miktar anlamı ayrıca soruldu ve **seçilen her buzağıya aynı miktar uygulansın** yanıtı alındı. İsimlendirme için **Padok No → Grup No** talimatı verildi. Henüz kod değiştirilmedi; sonraki açık **“Son sürümü hazırla”** talimatında uygulanıp test edilecek.

- [ ] Buzağılar bölümündeki mevcut hayvan bazlı **Günlük tüketim** giriş arayüzü yerine **Grup No ile Toplu Yem ve Mama Girişi** akışı yapılsın. Önceki tüketim kayıtları silinmesin; geçmişe ve raporlara erişim korunsun.
- [ ] Kullanıcının gördüğü **Padok No** alan adı ilgili form, liste, arama, uyarı ve raporlarda **Grup No** olarak gösterilsin. Bu yalnızca teknik tablo adlarını yeniden adlandırma işi değildir; numaranın mevcut fiziksel grup/padok anlamı korunmalı.
- [ ] Fiziksel **Grup No**, eski alım/parti kodu ve geçmiş **Toplu Çıkış No** verileriyle karıştırılmasın. Kullanıcının sonraki talebiyle yeni çıkışta numara girişi kaldırılacak; bu talep fiziksel grup numarasını kaldırmaz. Mevcut buzağı modelinde fiziksel grup alanı yok; kullanıcıların grup üyeliğini tanımlayabildiği uygun giriş/düzenleme alanı ve veri ilişkisi geliştirmeye dahil edilsin. Eski kayıtların grubu tahminle atanmasın.
- [ ] Grup No girildiğinde o gruptaki buzağıların tamamı alt listede görünsün. Örneğin grupta 20 uygun buzağı varsa 20'si de listelensin; küpe bilgileriyle tanınabilsin. Bireysel seçim, **Tümünü Seç**, **Seçimi Temizle** ve seçilen buzağı sayısı bulunsun. Başka gruptaki veya işlem için uygun olmayan hayvanlar sessizce eklenmesin.
- [ ] Kullanıcının son belirlediği alan sırası **Tarih seçimi → Mama (litre) → Yem tüketimi (kg) → Grup No** olsun. Geniş ekranda soldan sağa, dar ekranda üstten alta aynı sıra korunsun. Tarih başlangıçta bugün olsun ve değiştirilebilsin. Grup No ile getirilen buzağı listesi bu alanların altında gösterilsin.
- [ ] Mama ve yem alanlarının seçilen **her buzağı başına** miktar olduğu Türkçe açıklamayla belli edilsin. Kullanıcının seçimine göre girilen miktarlar seçili her buzağıya aynen uygulansın; grup toplamı sanılarak bölünmesin veya hayvan başına miktar yeniden çarpılmasın.
- [ ] Kaydetmeden önce seçilen hayvan sayısı, hayvan başına miktarlar ve hesaplanan grup toplamları açıkça gösterilsin. Örnek: 20 seçili buzağıya kişi başı 1 kg yem ve 3 litre mama girilirse her buzağı 1 kg/3 litre, toplam 20 kg yem/60 litre mama olarak kaydedilsin.
- [ ] **Toplu Kaydet** işlemi tek işlem bütünlüğünde yürüsün: boş seçim, hatalı miktar/tarih, uygun olmayan hayvan veya mevcut mükerrer kayıt gibi bir sorun varsa hiçbir kısmi tüketim kaydı oluşmasın. Yeniden gönderim/çift tıklamada aynı kayıtlar çoğalmasın. Oturum, yetki, işlem geçmişi ve Türkçe uyarılar korunsun.
- [ ] Mevcut veri modeli mama/sütü `milk_kg`, yemi `feed_kg` olarak tutuyor. Eski kilogram verileri sadece etiketi değiştirilerek litreye çevrilmiş sayılmasın. Yeni mama litre kayıtları ile eski kilogram kayıtları birim bakımından ayrı ve açık tutulmalı; yedek ve uyumlu veri geçişi sağlanmalı. Kg ve litre raporlarda birbirine eklenmesin, dönüşüm katsayısı uydurulmasın.
- [ ] Her kayıtta seçilen hayvanlar, işlem tarihi, grup ve miktar/birimler doğru bağlansın; sonraki grup üyeliği değişiklikleri geçmiş tüketim atfını değiştirmesin. Bu talep tek başına otomatik stok düşümü veya yeni bir yem üretim/maliyet sistemi talebi sayılmasın.
- [ ] Kabul testleri: 20 hayvanlı grubun eksiksiz listelenmesi, alt küme/tümünü seçme, aynı miktarın her seçili hayvana uygulanması, toplamların doğruluğu, farklı grupların ayrımı, uygunsuz/mükerrer kayıtta tüm işlemin reddi, eski kg verisinin korunması ve yeni litre kayıtlarının doğru raporlanması, tüm ilgili alanlarda Grup No gösterimi.

El yazısı notun önceki aktarımındaki **ara tartımı kaldırma** isteği kullanıcı tarafından 7 Kasım'da ayrıca açıkça doğrulandı; aşağıdaki madde uygulanacak. Buzağı çıkışı alan sırası ve çoklu küpe girişi de sonraki açık mesajlarla netleştirildi; aşağıdaki yeni çıkış talebi esas alınacak. El yazısının belirsiz son satırları için doğrulanmamış ek davranış türetilmesin.

### 7 Kasım 2026 — buzağılarda ara tartımı kaldırma

- [ ] Buzağılar bölümündeki **Ara tartım** kısmı ve buzağıya yeni ara tartım girmek için kullanılan form/bağlantılar kaldırılsın. Tek tek günlük tüketimi kaldırıp grup bazlı girişe geçme talebiyle ekran bütünlüğü sağlansın; kalan düğmeler kaldırılan işlevi vaat etmesin.
- [ ] Bu istek yalnızca **buzağı ara tartımına** ilişkindir. Buzağının **giriş kilosu** ve **çıkış kilosu**, bunlara dayanan günlük canlı ağırlık artışı/çıkış performans raporları korunsun. Ayrı Hayvanlar/Besi **Tartımlar** bölümünün kaldırıldığı varsayılmasın.
- [ ] Daha önce kaydedilmiş ara tartım verileri, geçmiş kayıtlar ve yedekler silinmesin. Kabul kontrolleri: buzağı ekranında ara tartım girişi bulunmaması, eski verilerin korunması, giriş/çıkış kilo akışı ve performans hesaplarının doğru çalışması.

Durum: geliştirme listesine kaydedildi; uygulama kodu değiştirilmedi, yeni sürüm oluşturulmadı. Sonraki açık **“Son sürümü hazırla”** talimatında diğer birikmiş taleplerle birlikte uygulanacak.

### 7 Kasım 2026 — buzağı çıkışında alan sırası ve çoklu küpe numarası

- [ ] Kullanıcının istediği çıkış alanı sırası **Tarih → TR ve İşletme Küpe Numaraları → Grup No → Buzağı çıkış kilosu (kg)** olsun. Liste alanların altında oluşsun; liste kontrol edildikten sonra toplu kayıt yapılsın.
- [ ] TR küpe ve işletme küpe girişlerinde birden fazla numara yazılabilsin. Kullanıcının istediği biçim, ilk numaradan sonra **virgül ve boşluk** ekleyerek devam etmektir; örneğin `1001, 1002, 1003`. Çevre boşluklar ayıklansın; küpe başındaki sıfırlar, TR ön eki ve gerçek numaranın karakterleri sayı dönüşümüyle kaybolmasın.
- [ ] Girilen numara uygulamadaki kayıtlarla kontrol edilsin; eşleşen hayvan gösterilsin. Tamamlanan numara bulunamazsa, birden fazla hayvanla belirsiz eşleşme varsa, çıkışı zaten yapılmışsa veya başka nedenle uygun değilse anlaşılır Türkçe ikaz verilsin. Kısmi eşleşmeyle yanlış hayvan kendiliğinden seçilmesin; bu doğrulama dış kurum kayıtlarına erişim kurulmuş anlamına gelmesin.
- [ ] Her geçerli numara, doğru buzağı ve karşılık gelen iki küpe bilgisiyle aşağıdaki toplu çıkış listesinde gösterilsin. Geçersiz numara sessizce atlanıp işlem başarılı sayılmasın; düzeltilebilsin. Aynı hayvan tekrar yazılırsa veya hem TR hem işletme küpesiyle eklenirse iki kez listeye/kayda alınmasın; uyarı verilsin.
- [ ] Alt listeden yanlış seçilen buzağı çıkarılabilsin, yeni numaralar eklenebilsin ve seçilen hayvan sayısı görülsün. Her buzağının çıkış kilosu ayrı korunabilsin; yem/mama için seçilmiş **her hayvana aynı miktar** kuralı çıkış kilosuna kendiliğinden uygulanmasın. Önceki ayrı çıkış kilosu gereksinimi geçerlidir.
- [ ] Grup No, hayvanın fiziksel grubuyla tutarlı gösterilsin/doğrulansın; numara eşleşmesi veya grup girişi hayvanın grubunu sessizce değiştirmesin. **Güncel talep:** kullanıcı yeni mesajında Toplu Çıkış No girişini kaldırdı; yeni işlemde bu numara sorulmayacak. Fiziksel Grup No ve geçmiş çıkış numarası verileri ayrı kavramlar olarak korunsun.
- [ ] Küpe numarasıyla hayvan seçilen giriş alanlarında çoklu numara yazma biçimi tutarlı olsun. Bu talep, bir hayvanın kartındaki benzersiz tek küpe değerine virgüllü liste kaydetmek şeklinde uygulanmasın; her listelenen buzağı ayrı kayıt kimliğiyle seçilmeli.
- [ ] **Toplu Kaydet** sırasında tarih, kilolar, hayvanların son durumu, yinelenme ve yetki sunucuda tekrar kontrol edilsin. Tek kayıtta hata varsa hiçbir buzağıya kısmi çıkış yapılmasın. Birden fazla gönderimde mükerrer çıkış oluşmasın; kayıtlar ve performans hesapları aynı işlem bütünlüğünde korunsun.
- [ ] Kabul testleri: birden fazla TR/işletme küpesi, virgül/boşlukla giriş, geçerli-geçersiz karışık numaralar, aynı hayvanın iki küpesiyle yinelenmesi, eksik numara/belirsiz eşleşme, çıkmış hayvan, yanlış grup, farklı bireysel kilolar, hatada tüm işlemin geri alınması ve doğru alan sırası.

### 7 Kasım 2026 — ilk buzağı kaydında ortalama fiyat

- [ ] Yeni buzağı giriş/kayıt kartına **Ortalama fiyat** alanı eklensin; düzenleme ve kaydedilmiş değerlerin gösterimi de tutarlı ele alınsın.
- [ ] **Birim kesinleşti:** kullanıcı **“Adet hayvan başı TL”** yanıtını verdi. Alan **Ortalama alış bedeli (TL/baş)** olarak gösterilsin; girilen tutar bir buzağının toplam alış bedelidir, kilogram başına fiyat değildir. Giriş kilosuyla çarpılarak tekrar alış bedeli hesaplanmasın.
- [ ] Fiyat Türkçe sayı biçimiyle girilsin ve gösterilsin; kuruş/ondalık hassasiyeti kaybolmasın, negatif/geçersiz değer Türkçe uyarıyla reddedilsin. Seçilen fiyat birimi alan etiketinde açık yazılsın.
- [ ] Eski buzağı kayıtlarına fiyat tahmin edilmesin; bilinmeyen fiyat otomatik olarak sıfır maliyet sayılmasın. Mevcut kayıtları koruyan yedekli veri geçişi sağlansın; yetki ve işlem geçmişi korunsun.
- [ ] Kabul testleri: fiyatın doğru birimle kaydedilmesi/düzenlenmesi/gösterilmesi, Türkçe sayı biçimi, geçersiz değerlerin reddi ve fiyatı olmayan eski kayıtların korunması. Bu alanın eklenmesi tam muhasebe/maliyet modülü geliştirmesi olarak genişletilmesin.

Bu iki bölüm de birikmiş taleptir; henüz uygulama koduna işlenmedi. Sonraki açık **“Son sürümü hazırla”** talimatında birim netliği ve mevcut testler kontrol edilerek uygulanacak.

### Cep telefonunda kamerayla küpe okuma — örnekler incelendi, uygulama bekliyor

Kullanıcı, hayvan kaydı ile tedavi/ilaç/aşı girişinde küpe numarası alanının yanında **Kamerayı Kullan** veya **Küpe Okut** düğmesi istedi. Bazı hayvanlarda TR ve işletme küpesi birlikte bulunuyor; ikisi de incelenebilsin, hangisi net okunursa numarası doğru alana yazılsın ve kayıt akışı bu kimlikle sürdürülsün. Üç örnek fotoğraf ulaştı ve özgün görseller incelendi: `IMG_5701_kucuk.jpg`, `IMG_5699_kucuk.jpg`, `IMG_5700_kucuk.jpg`. Kullanıcının telefon modeli/tarayıcısı henüz netleşmedi; fotoğraf yükleme engeli örneklerin iletilmesi bakımından aşıldı.

- [ ] Hayvan giriş formundaki küpe alanlarına ve sağlık/tedavi/ilaç/aşı girişindeki hayvan seçimine anlaşılır Türkçe **Küpe Okut** düğmesi eklensin. Telefonda kamerayı açıp küpe fotoğrafından numara okuma akışı olsun; desteklenen cihazlarda arka kamera tercih edilsin. Kamera izni yoksa fotoğraf seçme ve elle giriş yolu bulunsun.
- [ ] Çift küpeli hayvanda **TR Küpe No** ve **İşletme Küpe No** birbirinden ayrı tespit edilip gösterilsin. İkisi de netse ayrı alanlara, yalnız biri netse yalnız o kimliğin doğru alanına yazılsın. Tek okunan numara iki alana birden kopyalanmasın; küpe türü belirsizken sessizce karar verilmesin.
- [ ] Başındaki sıfırlar, TR ön eki ve gerçek numaranın karakterleri metin olarak korunsun. Okunamayan rakamlar tahminle tamamlanmasın. Görsel/ışık/yansıma/açı veya kir nedeniyle okuma belirsizse Türkçe açıklama, yeniden çekme ve düzeltme sunulsun. Örnek fotoğraflar denenmeden okuma doğruluğu veya başarı oranı iddia edilmesin.
- [ ] Okunan numara ve eşleşen hayvan kullanıcıya gösterilsin; normal kayıt akışına bu kimlikle devam edilsin. Tedavi/ilaç/aşı kaydı için ham okuma metni yerine doğru mevcut hayvan kaydı seçilsin. Otomatik küpe okuma tek başına tedavi uygulaması, reçete veya eksik zorunlu alanlarla yeni hayvan kaydı oluşturmasın.
- [ ] Mevcut hayvan TR veya işletme küpesinden sunucuda aranabilsin. Bulunamayan/birden fazla eşleşen numara için kullanıcı bilgilendirilsin. İki küpe farklı mevcut hayvanlara çıkarsa yanlış hayvana kayıt yapılmasın; eşleşme doğrulanmadan küpeler otomatik birleştirilmesin. Aynı karede iki küpe olması tek başına aynı hayvana ait olduklarının kanıtı sayılmasın.
- [ ] Eşleştirme yalnızca tarayıcıya önceden yüklenen son 500 hayvanla sınırlanmasın; sunucudaki uygun ve yetkili kayıtların tamamında iki kimlik üzerinden arama yapılabilsin. Daha önce kayıtlı hayvan yeniden oluşturulmasın; yeni kayıt ve mevcut hayvanla işlem akışları ayrıştırılsın.
- [ ] Mevcut yeni hayvan kaydında TR küpe zorunlu, işletme küpesi isteğe bağlıdır. Sadece işletme küpesi okununca bu değer TR alanına taşınmasın veya sahte TR üretilmesin. TR eksikse kullanıcıya doğru alanın tamamlanması gerektiği açıklansın; TR zorunluluğunu değiştirme ihtiyacı doğarsa bu ayrı iş kuralı olarak netleştirilsin.
- [ ] Fotoğraf boyut/biçim doğrulaması, kullanıcı/hayvan erişim yetkileri ve oturum güvenlik kontrolleri korunsun. Numaranın görüntülenmesi ile kaydın kalıcı oluşturulması birbirine karıştırılmasın; yanlış/tekrarlı okumada mükerrer kayıt oluşmasın. Teknik hatalar kullanıcıya Türkçe gösterilsin.
- [ ] Mobil kamera için izin ve uygun güvenli bağlantı koşulları test edilsin. Telefonun Mac pilotuna erişimi ayrı bir gereksinimdir: telefondaki `127.0.0.1` Mac'i göstermez. Kullanıcının önceki iPad isteği yalnızca Codex geliştirmesiydi; yeni kamera talebi telefon üzerinden ERP kullanım hedefi ekler, kendiliğinden internet/özel ağ/alan adı/yayın kurma yetkisi vermez. Gerçek cihaz bağlantısı kurulmuş sayılmasın.
- [ ] Alınan fotoğraflar ve gerektiğinde eklenecek örneklerle tek TR, tek işletme, aynı hayvanda çift küpe, yalnız birinin net okunması, belirsiz karakter/ışık/açı, iki farklı hayvana eşleşme ve hiç eşleşmeme durumları doğrulansın. İzin reddi, dosya hatası, elle düzeltme, eski kayıtların bulunması, yetkisiz erişim ve mükerrer kayıt kontrolleri de kapsansın.

Salt okunur kaynak incelemesi: hayvan formu `app/static/index.html` içinde; sağlık hayvan seçimi `app/static/health.js` içinde ve `animal_id` ile kayıt yapılıyor. `app/document_preview.py` mevcut fatura/kantar önizlemesi için genel görsel metin okuma içeriyor; bu özellik küpe tanıma/kimlik ayırma veya hayvan eşleştirmesi sağlamıyor. Arayüzde kamera akışı henüz yok.

Örnek incelemesi: ilk karede iki farklı küpe var ve biri diğerini kısmen örtüyor; ikinci karede işletme numarası netken TR küpesinin üst kısmı örtülü; üçüncü karede tek TR küpesi görünüyor. Son haneleri, kapalı üst satırı veya işletme küpesinin örtülen bölümünü tahminle tamamlama kabul edilmez. Bir örnekte görülen TR ön eki/üst kod diğer örneğe kopyalanamaz; renk tek başına küpe türü sayılmaz. Görünen parçalar ile tam ve kayıtla doğrulanmış kimlik ayrıştırılmalı.

Mevcut genel metin okuma yöntemi için üç özgün fotoğrafta `tur+eng` ile iki sayfa düzeni ayarında toplam altı tam kare denemesi yapıldı; güvenilir küpe numarası üretmedi. Komutların başarılı çıkış kodu doğru okuma kanıtı sayılmadı. Küpe bölgesini ayırma, eğim/örtülme ve iki numarayı sınıflandırma için ayrı çözüm gereklidir; bu ön inceleme bir kamera uygulaması veya başarı oranı testi değildir.

Özgün fotoğraflar, dosya bütünlük özetleri ve görünen parçalara ilişkin inceleme notları yalnızca `/workspace/kuzucu-cloud/kupe-ornekleri/` altında tutuldu. Örnekler işletme görüntüleri olduğundan kaynak checkout'a, yeni sürüm ZIP'ine veya GitHub'a kendiliğinden eklenmesin. Hayvan veritabanına fotoğraftan kayıt oluşturulmadı. Tam numara beklenen sonuç olarak kullanılacaksa kullanıcı teyidi veya doğrulanmış kayıt eşleştirmesi gerekir.

Durum: talep ve örnek bulguları geliştirme listesine kaydedildi. Yeni açık **“Son sürümü hazırla”** talimatı bekleniyor; uygulama kodu, paket veya yayın oluşturulmadı. Örnekler alınmış olsa da otomatik okuma/kamera özelliği henüz uygulanmış değildir.

### Güncel talep — toplu buzağı çıkışında numara girişi kaldırılacak

- [ ] Kullanıcı toplu buzağı çıkarırken artık **Toplu Çıkış No** vermek istemiyor. Formdaki numara alanı kaldırılsın; numara boş diye uyarı verilmesin, işlemi tamamlamak için kullanıcıdan ad/numara istenmesin.
- [ ] Çıkış düzeni **Tarih → TR/İşletme Küpe Numaraları → Grup No → Buzağı çıkış kilosu (kg)** olarak sürsün. Grup No fiziksel gruptur; kaldırılan çıkış numarasının yerine geçirilmesin.
- [ ] Yeni çıkış raporlarının kullanımı elle verilen çıkış numarasına bağlı olmasın; mevcut tarih/grup ve hayvan bilgileriyle sonuçlara erişilebilsin. Eski çıkış numarası dolu kayıtların değerleri, geçmiş raporları ve işlem kayıtları silinmesin. İşlem bütünlüğü için gerekebilecek iç kayıt kimliği kullanıcıya zorunlu çıkış numarası olarak sunulmasın.
- [ ] Kabul kontrolleri: numara girişi olmadan tekli/toplu çıkış, doğru bireysel kilo ve performans sonuçları, tarih/grup üzerinden rapor erişimi, geçmiş numaralı kayıtların korunması ve hatalı satırda tüm işlemin geri alınması.

### Güncel talep — sağlık formunu sadeleştirme ve süreye göre günlük çıktı

Bu talep sağlık/tedavi planı girişini düzenler. Kullanıcı yeni bir **“Son sürümü hazırla”** talimatı vermedi; burada yalnızca gereksinimler kaydedildi.

- [ ] Sağlık giriş formundan **Belirtiler / klinik durum** alanı kaldırılsın. Bu talep ayrı **Hastalık / durum adı** alanını kendiliğinden kaldırmak olarak genişletilmesin.
- [ ] **Veteriner hekim** giriş alanı ve **Veteriner tarafından onaylandı** seçeneği kaldırılsın; yeni kaydı tamamlamak için bu bilgiler istenmesin. Arayüz, sunucu doğrulaması, günlük uygulama ve listeleme kuralları bu yeni iş akışıyla birlikte ele alınsın. Alanları yalnızca gizleyip işlemi arka planda eski onay koşuluna kilitlemek çözüm sayılmasın.
- [ ] Formdaki elle seçilen **Başlangıç / Planlanan bitiş** tarih aralığı kaldırılsın. Yerine **Tedavi Süresi (gün)** alanı eklensin. Tedavi ilk kaydedildiğinde başlangıç tarihi Türkiye saatine göre o gün olsun; bitiş, başlangıç + süre − 1 gün olarak hesaplansın. Süre pozitif tam gün olmalı; 1 gün aynı gün başlayıp bitmeli.
- [ ] Tedavi, başlangıç günü dahil verilen süre boyunca her gün **günlük tedavi/otomatik çıktı listesinde** yer alsın. Örneğin 3 günlük tedavi kayıt günü ve sonraki 2 gün listelensin; süre dışında planlanmış günlük iş olarak devam etmesin. Sürenin dolması hayvanın iyileştiği veya uygulamaların yapıldığına dair otomatik sonuç kaydı oluşturmasın.
- [ ] Otomatik günlük PDF/çıktı listesi de aynı süre hesabını kullansın. O günün dosyası daha önce hazırlanmış olsa bile yeni tedavi eklenmesi veya planın değiştirilmesi listeyi eski bırakmasın. Gerçek günlük uygulamalar kullanıcı tarafından kaydedilmeye devam etsin; plan listesine eklemek **uygulandı** kaydı sayılmasın. Mevcut fiziksel yazdırma ayarı bu taleple kendiliğinden açılmasın.
- [ ] **Arınma / kesim kısıtı bitişi** giriş alanı kaldırılsın. Kullanıcıdan yeni formda arınma tarihi istenmesin; eski kayıtlardaki tarih veya diğer tıbbi bilgiler silinmesin ve yeni bilgi uydurulmasın.
- [ ] **Plan notları** alanının görünen adı **Sağlık** olsun. Mevcut açıklama içeriği korunsun; diğer modüllerin açıklama/not etiketleri bu değişiklikle topluca değiştirilmesin.
- [ ] Kaldırılan belirtiler/veteriner/onay/tarih/arınma girişleri, eski bir kayıt düzenlenirken varsayılan boş değerlerle geçmiş verileri silmesin. Eski kaydın başlangıcı her düzenlemede bugüne taşınmasın. Gerçek uygulama geçmişi yeni hesaplanan tarihlerle çelişiyorsa veri koruyan, Türkçe açıklamalı düzenleme kuralı uygulansın.
- [ ] Verilmemiş veteriner onayı varmış gibi `vet_approved=True` yazılarak arayüz engeli aşılmasın; geçmiş onayların anlamı geriye dönük değiştirilmesin. Bu istek otomatik reçete, ilaç veya doz önerme talebi değildir. Aynı ilacın son 10 gündeki tekrarı uyarısı korunarak kaldırılan alanlara bağımlılığı giderilsin.
- [ ] Kabul kontrolleri: belirtilen alanların formdan kalkması, **Sağlık** etiketinin görünmesi, başlangıcın kayıt günü olması, 1/3 gün ve ay-yıl sınırlarında doğru günlük liste/PDF kapsamı, aynı gün sonradan eklenen kaydın çıktıya yansıması, yanlış sürenin reddi, geçmiş veri/uygulamaların korunması ve yetki/işlem geçmişi denetimleri.

Kaynak incelemesi: `app/animal_health.py` şu an başlangıç/bitişi zorunlu alıyor; veteriner onayı uygulama, tekrar ilaç uyarısı, günlük durumlar ve geçmiş sonuç raporlarıyla bağlantılı. Günlük listede süre sonu aşılmış açık kayıtlar da bulunabiliyor; otomatik çıktı mevcut günlük PDF'yi yeniden üretmeyebiliyor. Bu nedenle gelecek uygulama hem arayüzü hem ilgili iş kurallarını kapsamalı; bir kayıt alanını gizleme değişikliğine indirgenmemeli.

### Yeni talepler — ana sayfa sayımları

- [ ] Ana sayfada **Toplam Erkek**, **Toplam Dişi** ve **Irklara Göre Hayvan Sayıları** gösterilsin. Sayımlar kayıtlardan hesaplansın; hayvan ile buzağı modelleri arasında aynı fiziksel hayvan varsa çift sayılmasın. Aktif/çıkışı yapılmış ve cinsiyeti/ırkı bilinmeyen kayıtların kapsamı açık olsun; bilinmeyen değerler tahmin edilmesin.
- [ ] Ana sayfa/ana menüde **Süt İçen Erkek Buzağı** ve **Süt İçen Dişi Buzağı** sayıları ayrı gösterilsin. Süt/mama dönemindeki aktif buzağıyı tanımlayan açık kayıt/durum gereklidir; sadece geçmişte tüketim girilmesi veya o gün kayıt girilmemesi süt dönemini kesinleştirmez. Kullanıcı buzağının süt/mama durumunu uygun kart alanından tanımlayabilsin; çıkışı yapılmış hayvanlar bu aktif sayıya alınmasın.
- [ ] Sayı kartları ve ırk listeleri ilgili hayvan/buzağı/rapor erişim yetkilerini korusun; yetkisiz kullanıcıya özet sayı üzerinden hassas veri açılmasın. Kaydetme/düzenleme/çıkış sonrası sayımlar güncellensin.

### Yeni talepler — Stok Girişi, alarm seviyesi ve Uyarılar

- [ ] Menüye doğrudan erişilen **Stok Girişi** bölümü eklensin. Mevcut stok hareket altyapısıyla tutarlı çalışsın; aynı giriş ayrı ekranlar nedeniyle iki kez yazılmasın. Stok ürünleri ve hareket geçmişi korunmalı.
- [ ] Stok girişinde ürün için **Stok Alarm Seviyesi** tanımlanabilsin; değer aynı ürünün sonraki hareketlerinde kullanılacak şekilde saklansın ve düzenlenebilsin. Eşik ürünün stok birimiyle açıkça gösterilsin. Kg, litre ve adet birbirine karıştırılmasın; eşik tanımlanmamış eski ürüne değer uydurulmasın.
- [ ] Hammadde ve ilaç stokları için eşik/bakiye kontrolü yapılsın; alarm seviyesine ulaşma veya altına inme durumları Türkçe uygulama içi bildirim ve **Uyarılar** bölümünde gösterilsin. Ürün adı/türü, birim, mevcut bakiye, eşik ve uyarı zamanı görülsün; ürünün hammadde/ilaç sınıfı sadece adından tahmin edilmesin.
- [ ] Kullanıcının kuralı: uyarı **onaylanmadıkça listeden silinmesin**. Onaylandıktan sonra da onay anından itibaren **24 saat** listede kalsın; onaylayan kullanıcı ve zaman kaydedilsin. Onay bildirimin görüldüğü anlamına gelir; stok hareketini onaylamak veya stok düzeltmekle karıştırılmasın.
- [ ] Stok yükselse veya uygulama kapanıp açılsa bile onaysız uyarı kaybolmasın. Onay sonrası bekleme süresi ve durum bilgisi yeniden açılışta korunsun. Aktif listeden çıkan uyarının geçmiş/rapor kaydı korunabilsin; aynı olay her yenilemede mükerrer uyarı üretmesin. Eşik koşulu yeniden oluştuğunda yeni olayı takip edebilsin.
- [ ] Bildirimi görme/onaylama işlemleri sunucuda da yetkilendirilsin. Bu istek tek başına dış SMS/e-posta, telefon işletim sistemi bildirimi veya program kapalıyken çalışan sunucu kurulumu anlamına gelmez.
- [ ] Kabul kontrolleri: ürün/birim bazında doğru eşik, hammadde/ilaç ayrımı, onaysız uyarının kalması, onay + 24 saat sınırı, uygulama yeniden açılışı, uyarı çoğalmaması ve yetkisiz onayın reddi.

### Yeni talepler — stok girişine Excel'den aktarma

- [ ] Stok girişinde **Excel'den Aktar** düğmesi olsun. Desteklenen Excel biçimleri açıkça belirtilsin; dosya satırları ürün, miktar, birim, tarih ve varsa belge/fiyat bilgileriyle önizlensin ve alan eşleştirmesi yapılabilsin.
- [ ] Ürün adları mevcut ürün kartlarıyla eşleştirilsin; bulunmayan/karışan ürün sessizce yanlış karta bağlanmasın. Boş/hatalı/tekrarlı satırlar ve birim uyuşmazlıkları Türkçe gösterilsin. Türkçe sayı/tarih biçimleri doğru ayrıştırılsın.
- [ ] Önizleme stok bakiyesini değiştirmesin. Kullanıcı kontrol edip kaydettiğinde tüm seçili satırlar tek işlem bütünlüğüyle aktarılsın; aynı dosyanın tekrar gönderilmesiyle mükerrer stok oluşmasın. Aktaran kullanıcı ve kaynak dosya/işlem izi korunsun.

### Yeni talepler — Personel bölümü ve raporları

- [ ] İşlevsel **Personel** bölümü oluşturulsun; sadece mevcut gelecek-yetki etiketi olarak kalmasın. Personel kartı, işe yeni başlayanların kaydı, işe giriş tarihi ve işten çıkış bilgisi/durumu tutulup listelenebilsin.
- [ ] Personel bazında **Mesai**, **Haftalık İzin** ve **Yıllık İzin** giriş/listeleme ekranları olsun. Tarihler, mesai süresi, izin türü ve açıklaması personele bağlansın; hatalı/çakışan dönemler kontrol edilsin. Aktif ve ayrılmış personelin geçmişi silinmesin.
- [ ] Yıllık izin hakkı/kullanılan/kalan bilgileri doğru dayanağa bağlı hesaplanabilsin; şirket kuralı veya hukuki hak ediş verisi belirlenmeden hak/ücret tahmin edilmesin. Mesai saatleri ile parasal ücret hesapları birbirine karıştırılmasın.
- [ ] Personel, mesai, haftalık/yıllık izin ve işe giriş/çıkış listeleri; personel, durum ve tarih aralığıyla rapor ekranından sorgulanabilsin. İlgili dışa aktarımlar ve bölüm/rapor yetkileri sunucuda korunsun; genel rapor araması personel gizliliğini aşmasın.

### Yeni talepler — hayvanlarda çoklu küpe ve işleme göre satır formları

- [ ] Hayvanlar bölümündeki toplu veri girişinde küpe numaraları **numara, boşluk, sonraki numara** biçimiyle girilebilsin (`1001, 1002, 1003`). Önceki TR/işletme küpesi doğrulama, metin olarak saklama ve tek hayvanı iki kez seçmeme kuralları bu genel akışta da uygulansın.
- [ ] Girilen hayvanlar aşağıdaki toplu listeye gelsin. Kullanıcı **İşlem Adı** seçtiğinde o işleme uygun bilgi pencereleri/alanları her hayvanın yanında açılsın; her satırda ilgili hayvanın bilgileri girilebilsin. Listeden çıkarma ve seçilen hayvan sayısı olsun.
- [ ] İşlem seçimi mevcut desteklenen/yetkili hayvan işlevlerine bağlı olsun; yeni hayvan girişi ile mevcut hayvana işlem ekleme aynı sayılmasın. İşleme göre bulunması gereken/kaydolmamış küpeler doğru değerlendirilip Türkçe açıklansın; yanlışlıkla yeni hayvan açılmasın.
- [ ] Zorunlu alanlar, tarih/miktar, hayvanın son durumu, tekrar kayıt ve yetki her satır için doğrulansın. Toplu işlemde hata varsa kısmi kayıt kalmasın. Kaydeden ve önceki/yeni değerler işlem geçmişine yansısın.

### Yeni talepler — sayılı aralıklarla hatırlatma

- [ ] Kullanıcı açıklaması kesinleşti: **her 1 günde, her 2 haftada, her 5 ayda bir** hatırlatma istiyor. Bu, bir haftada 2 veya bir ayda 5 ayrı kez hatırlatma değildir.
- [ ] Hatırlatma girişine **Her [pozitif sayı] [gün/hafta/ay]** aralık alanları eklensin; başlangıç tarihi ve saat ile birlikte çalışsın. Mevcut tek seferlik ve günlük/haftalık/aylık kayıtların davranışı korunarak eski tekrarlar aralık 1 ile uyumlu ele alınsın.
- [ ] Haftalar 7 günün katı, aylar takvim ayı olarak hesaplansın; 5 ay rastgele 150 güne çevrilmesin. Ayın 29/30/31'i, artık yıl ve ayın son gününde doğru sonraki tarih üretimi test edilsin. Tamamlandı işaretleme, gecikmiş işler ve yeniden açılışta tekrar hesabı tutarlı olsun.

### Yeni talepler — alış/satış faturaları ve KDV toplamları

- [ ] **Fatura Girişi (Alış)** ve **Fatura Çıkışı (Satış)** için kayıt/liste/düzenleme ekranları olsun. Tarih, ilgili firma, belge bilgileri ve ürün satırları kaydedilsin; mevcut kg bazlı kantar-fatura mutabakatı tam fatura muhasebesi sanılmasın.
- [ ] Kullanıcının satır alanları: **Tarih / Ürün Adı / Miktar / Miktar Birimi (adet, kg, litre)**. Hesap için satıra **Birim Fiyat** ve **KDV Oranı** da eklensin. Ürün/birim mevcut stok kartıyla uyumlu olsun.
- [ ] Kullanıcı fiyat düzenini kesinleştirdi: **KDV hariç birim fiyat** girilecek, KDV ayrıca hesaplanacak. Satır tutarı = miktar × KDV hariç birim fiyat; satır KDV'si oranla hesaplansın. Belge altında **Ara Toplam**, **KDV Toplamı** ve **Genel Toplam** ayrı gösterilsin. Kullanıcının tekrar ettiği KDV toplamı ifadesi aynı vergiyi iki kez eklemek şeklinde uygulanmasın.
- [ ] Türkçe sayı biçimi, parasal ondalık hassasiyet ve kuruş yuvarlama tutarlı olsun. Farklı ürün/miktar birimleri ve KDV oranları aynı belgede doğru işlensin; hatalı miktar/fiyat/oran ve mükerrer belge reddedilsin.
- [ ] Onaylanan fatura, stok ve cari hareketlerine uygun tek etki oluştursun. Önce kantar/depo kabulünden stok girilmişse fatura geldiğinde ikinci kez aynı miktar stok oluşturulmasın. Düzenleme/iptal geçmişi ve eski bakiyeler korunarak hesaplar yeniden tutarlı hale gelsin.

### Yeni talepler — maliyetler, hesaplar, bakiyeler ve ortak rapor araması

- [ ] Girilen ürünler, miktar/birim, fiyat, KDV, fatura, stok hareketi, firma/cari ve varsa ödeme/tahsilat ilişkileri arka planda tutarlı hesap kayıtlarında izlensin. Borç/alacak, bakiye ve maliyetler gerçek hareketlerden üretilebilsin; sadece görünen toplam yazısı veya firma kartı tutulması yeterli sayılmasın.
- [ ] Aynı işlem farklı ekranlarda raporlandığı için mükerrer stok/borç/maliyet oluşmasın. İptal/düzeltme/aktarımı tekrar gönderme durumları izlenebilir olsun; eski yanlış kayıtlar otomatik tahminle düzeltilmesin. Maliyet değerleme yöntemi ve KDV'nin maliyete etkisi açık iş kuralı olmadan uydurulmasın.
- [ ] Ürün, firma, tarih, fatura, stok, maliyet, bakiye, personel ve hayvan işlemleri ilgili raporlardan bulunabilsin. Kullanıcı, girilen verileri farklı raporlarda arayabilsin; desteklenmeyen rapor henüz yapılmış gibi sunulmasın.
- [ ] Ortak/Türkçe rapor araması mevcut bölüm, işlem, rapor ve dışa aktarım yetkilerinin tamamını korusun. Muhasebe/personel gibi hassas veriler doğal dil rapor veya dosya aktarımı yoluyla yetkisiz kullanıcıya sızmasın. Rapor/CSV/PDF içindeki uygulama etiketleri Türkçe olsun.

### Yeni talepler — rapordan fotoğrafla fatura/firma ve hayvan tartımı aktarımı

- [ ] **Raporlar** bölümüne fotoğraf yükleme alanı eklensin; fotoğraf analizinin yanında tanınan belge türü, çıkarılan alanlar ve düzeltilebilir önizleme bulunsun. Mevcut fatura/kantar fotoğraf önizlemesi geliştirilerek gerçek kayıt akışına bağlansın; önizleme tek başına kayıt oluşturmasın.
- [ ] Kullanıcının istediği **Faturayı Kaydet** ve **Firmaya Ekle** işlemleri yanında bulunsun. Firma doğru kartla eşleştirilsin, eklenen belge o firmaya bağlanabilsin. Firma bulunamazsa otomatik rastgele kart açılmasın; uygun kullanıcı eylemiyle yeni kart oluşturulabilsin. Fatura işlemi belge satırlarını, miktar/birim/fiyat/KDV bilgilerini kullanıcı kontrolünden sonra kaydetsin.
- [ ] Hayvan kg/tartım fişi için kullanıcı kesin yanıtı: **kayıtlı hayvanlara tartım kaydı eklensin**. Fotoğraftan yeni hayvan giriş kartı oluşturulması bu akışın kapsamında değildir. Küpe ve kilo/tarih satırları çıkarılıp mevcut hayvanlarla eşleştirilsin; bulunamayan/belirsiz küpe, yinelenen satır veya okunamayan kilo kontrolsüz kayda dönüşmesin.
- [ ] Küpe fotoğrafı okuma talebindeki TR/işletme ayrımı, kapalı rakamları tahmin etmeme ve baştaki sıfırları koruma ilkeleri tartım fişindeki kimliklerde de geçerli olsun. Aynı belgeyi ikinci kez yükleyip kaydetmek mükerrer fatura/tartım/hesap hareketi üretmesin.
- [ ] Kullanıcı önizlemeyi kontrol edip hedef işlemi seçtikten sonra kayıt yapılsın; dosya, belge ve kaynak ilişkisi izlenebilsin. Görsel analizi başarısızsa Türkçe açıklama ve elle düzeltme yolu sunulsun. Gerçek belge/fotoğraflar kaynak kod ZIP'ine veya GitHub'a kendiliğinden eklenmesin.
- [ ] Kabul kontrolleri: alış/satış faturası ve hayvan kilo fişi türleri, yanlış firma/hayvan eşleşmesi, birim ve Türkçe sayılar, KDV hariç hesap, bulanık/eksik belge, tekrarlı yükleme, yetki ve toplu kayıt bütünlüğü.

### Yeni talepler — hayvanlarda kesim/ölüm/satış türünde toplu çıkış

Kullanıcı ilk mesajının son satırını düzeltti; güncel tam talep aşağıdadır. Bu, önceki toplu buzağı çıkışını kaldırmak yerine Hayvanlar/Besi için ayrıca ele alınmalı.

- [ ] Alan sırası **Tarih → Çıkış Nedeni (Kesim / Ölüm / Satış) → Nereye Gittiği → Çıkış Kilosu (kg)** olsun. Birden fazla hayvan önceki çoklu küpe/liste seçimiyle işleme alınabilsin.
- [ ] Çıkış türü Türkçe seçeneklerden seçilsin; ortak tarih/neden/hedef bilgisi ile her hayvanın çıkış kilosu doğru kayda bağlansın. Kilo her hayvana ait olmalı; birden çok hayvana yanlış toplam yazılmasın. Türüne göre hedef/kilo gerekliliği belirlenirken bilinmeyen değer veya satış bedeli tahmin edilmesin.
- [ ] İşlem sonucunda hayvanın çıkış tarihi, nedeni, gittiği yer, kilosu ve durum geçmişi saklansın; genel bakış/ırk/grup/aktif hayvan raporları doğru güncellensin. Aynı hayvana tekrar çıkış yapılmasın; ölüm/kesim/satış geçmişi sadece mevcut durumu değiştiren bir metne indirgenmesin.
- [ ] Tüm satırlar doğrulanıp tek işlem bütünlüğünde kaydedilsin; yanlış küpe/uygunsuz tarih/kilo/önceden çıkış yapmış hayvan varsa kısmi çıkış oluşmasın. İşlem yetkisi ve kaydeden bilgisi korunsun. Geçmiş kayıtlar silinmesin; düzeltme gerektiğinde izi tutulabilsin.

### Bu yeni kapsamın kaynak incelemesi ve durumu

Mevcut v0.14'te dashboard yeni sayımları içermiyor; buzağıda açık süt dönemi alanı yok. Ürün kartında alarm eşiği/uyarı onayı alanları, stok Excel aktarımı, personel veri modeli/işlemleri ve N dönem aralıklı hatırlatma yok. Personel/finans/banka/kasa/cari başlıklarının bazıları yalnız **gelecek** yetki etiketleridir. Fatura altyapısı fiyat/KDV içermeyen kg bazlı alış satırı–kantar mutabakatıyla sınırlı; fotoğraf okuyucu yalnız önizleme yapıyor. Genel hayvan toplu çıkış tarih/neden/hedef/kilo alanları ve API'si mevcut değil. Bunlar yapılmış özellik gibi gösterilmemeli.

Kullanıcının üç yanıtı kaydedildi: **N günde/haftada/ayda bir**, **KDV hariç birim fiyat**, **kayıtlı hayvanlara tartım ekleme**. Diğer bütün eski talepler geçerlidir; bu liste onları silmez. Henüz uygulama kodu değiştirilmedi, yeni paket hazırlanmadı ve gönderim/yayın yapılmadı. Yeni açık **“Son sürümü hazırla”** talimatında kapsam birlikte uygulanıp test edilecek.

## 11 Kasım 2026 — Parsel kayıt hatası: inceleme ve düzeltme (v0.15.0 üzerine)

Temel: depodaki ve kullanıcının yüklediği **v0.15.0** paketi (SHA256 aynı). Yeni sürüm paketi (ZIP) **hazırlanmadı**; ekran sürümü hâlâ v0.15.0. Sonraki paket, kullanıcı "Son sürümü hazırla" dediğinde v0.16.0 olacak.

**Kök neden:** Parsel "Alan (dekar)" kutusu tarayıcının sayı kutusuydu (`type="number"`). Türkçe yazımı anlamıyordu: `12,5` → 125 dekar (virgül siliniyordu), `1.250` → 1,25 dekar. Hata mesajı da çıkmıyordu. Ayrıca `P-1` varken ` P-1 ` veya `p-1` ikinci parsel olarak kaydedilebiliyordu.

- [x] Yeni parsel (görselli/görselsiz) ve Düzenle formunda dekar kutusu Türkçe sayı kutusu oldu; binlik nokta yazarken kendiliğinden konur.
- [x] Tartımlar ekranındaki "Canlı ağırlık (kg)" kutusunda da aynı sorun vardı; düzeltildi.
- [x] Parsel kodu kırpılır; büyük/küçük harf, boşluk ve I/İ/ı/i farkı gözetilmeden mükerrer kontrolü (`/api/fields`, `/api/fields/with-image`, düzenleme). Eski mükerrer kayıtlar, kodları değişmeden düzenlenebilir.
- [x] 3'ten fazla ondalık reddedilir (sessizce yuvarlanmaz). Boş Ada No boş saklanır. Görselli kayıtta boş kod/fazla ondalık artık genel sunucu hatası değil, Türkçe uyarı verir.
- [x] Bilgi mesajı önceki mesajın zamanlayıcısıyla erken kaybolmuyor. `parcels.js` önbellek anahtarı `?v=015b`.
- [x] 10 yeni test (`tests/test_parcel_input.py`). Toplam **191 test geçti**, 1 atlandı (Tesseract kurulu değil). Gerçek Chromium ile yeni kayıt/düzenleme/mükerrer/boş/0 denendi; JavaScript hatası 0.
- [ ] Kullanıcının Mac'inde deneme; eski parsellerin dekarlarının elle gözden geçirilmesi (otomatik düzeltme yapılmaz).

### Ayrı bulgu — tarayıcı test aracı buzağı adımında takılıyor (v0.15'te de var)
- [ ] `tools/ui_smoke.cjs` parsel, kullanıcı, ajanda, stok adımlarını geçiyor; buzağı adımında takılıyor. Test buzağıyı "dün" giriş tarihiyle kaydetmeye çalışıyor ama kayıt bugünün tarihiyle oluşuyor, sonra aynı gün çıkış "çıkış tarihi giriş tarihinden sonra olmalı" ile reddediliyor. Değiştirilmemiş v0.15.0'da da aynı. Tarih kutusunun doldurulması/taslak geri yüklemesi ya da saat dilimi incelenmeli; kullanıcının gerçek buzağı girişinde tarih değişip değişmediği kontrol edilmeli.

## 11 Kasım 2026 — Yeni talepler (v0.16 için; "Son sürümü hazırla" bekleniyor)

### 1. Stok girişinde kayıtlı olmayan ürünü oradan ekleme
- [ ] Stok Girişi ekranında ürün seçerken aranan ürün yoksa **"+ Yeni Stok Ürünü"** düğmesi.
- [ ] Ayrı bir pencere açılır: ürün kodu, ürün adı, birim (kg/ton/adet/litre…), sınıf (hammadde/ilaç…), alarm seviyesi.
- [ ] Kaydet'e basınca pencere kapanır, yeni ürün **otomatik seçilir** ve stok girişine yazılmış tarih/miktar/firma bilgileri **kaybolmadan** işleme devam edilir. İptalde hiçbir şey kaydedilmez.
- [ ] Yetki: ürün ekleme ayrı yetki (`stok.urun.create`); yetkisi olmayan kullanıcı düğmeyi görmez, sunucu da reddeder.
- [ ] Aynı ürün kodu/adı tekrar açılmasın (parseldeki gibi harf/boşluk farkı gözetilmeden kontrol).
- Mevcut durum (v0.15): Stok Girişi yalnızca kayıtlı ürünleri seçtiriyor; yeni ürün için ayrı "Stok Ürünleri" sayfasına gidip dönmek gerekiyor.

### 2. "Genel Bakış" adı "Ana Sayfa" olsun
- [ ] Menü, sayfa başlığı ("İşletme Genel Bakış"), yetki ekranındaki adı ve testler güncellenecek. Yetki anahtarı (`dashboard`) değişmeyecek; mevcut kullanıcı yetkileri korunur.

### 3. Çıkışı yapılan hayvanların geçmiş raporlarda görünmesi
- Mevcut durum (v0.15, koddan incelendi): Toplu Hayvan Çıkışı (kesim/ölüm/satış) ayrı bir çıkış tablosuna kaydediliyor, hayvan kaydı silinmiyor. Akıllı Raporlar'da "kesilen hayvanlar" yazıp başlangıç/bitiş tarihi kutularını doldurunca bu kayıtlar listeleniyor. Buzağı çıkışları ise ayrı "Buzağı Çıkış Performans Raporu"nda.
- [ ] Gerçek kullanımla doğrula: çıkış yapılmış hayvan raporda ve Hayvanlar listesinde ("Çıkışı yapıldı" filtresi) gerçekten görünüyor mu.
- [ ] Ayrı, sade bir **Hayvan Çıkış Raporu** ekranı: tarih aralığı, çıkış nedeni (kesim/ölüm/satış/hepsi), grup, besi + buzağı birlikte veya ayrı; toplam baş ve toplam kg; Excel/CSV ve yazdırma (rapor yetkisine tabi).
- [ ] Akıllı Raporlar cümle içindeki tarihleri anlasın: "1 Ekim ile 31 Ekim arasında kesilen hayvanlar", "geçen ay kesilenler", "2026 Ekim".
- [ ] Hayvan kartında çıkış bilgisi (tarih, neden, gittiği yer, çıkış kg) görünsün; geçmiş tartım/sağlık kayıtları korunur.

### 4. Sol menünün yeniden düzenlenmesi
Mevcut: 26 menü maddesi tek, uzun liste. Öneri (profesyonel ERP'lerdeki gibi açılır gruplar):

| Ana başlık | Altındaki sayfalar |
|---|---|
| **Ana Sayfa** | (tek sayfa) |
| **Hayvanlar** | Hayvanlar · Gruplar · Buzağı Giriş / Çıkış · Sağlık / Tedaviler · Tartımlar · Toplu Hayvan İşlemleri · Toplu Hayvan Çıkışı |
| **Tarım** | Parseller · Üretim Sezonları |
| **Stok** | Stok Girişi · Stok Hareketleri · Stok Ürünleri · Uyarılar |
| **Muhasebe** | Faturalar · Cariler (birleşik) · Kasa / Banka · Maliyetler |
| **Personel** | Personel |
| **Raporlar** | Akıllı Raporlar · Hayvan Çıkış Raporu (yeni) |
| **Ajanda** | Ajanda / Hatırlatmalar |
| **Belgeler** | Fotoğraf / Belge Aktarma · Belge Metni Okuma · Entegrasyonlar |
| **Yönetim** | Kullanıcılar ve Yetkiler · İşlem Geçmişi |

- [ ] Ana başlığa tıklayınca alt sayfalar açılır/kapanır; açık sayfanın grubu açık ve vurgulu kalır; son açık gruplar hatırlanır.
- [ ] Her ana başlıkta simge (ikon); yeşil-altın KUZUCU görünümü korunur.
- [ ] Yetkisi olmayan sayfalar gizlenir; içinde hiç izinli sayfa olmayan ana başlık da gizlenir (sunucu yetki denetimi aynen sürer).
- [ ] Tablet/telefonda menü bir düğmeyle açılır-kapanır (☰).
- [ ] Menüde arama kutusu (sayfa adını yazarak bulma) — isteğe bağlı.
- [x] **Kullanıcı onayı (11.11.2026):** Yukarıdaki gruplama aynen uygulanacak.
- [ ] **Kullanıcı kararı (11.11.2026): "Hesaplar / Cariler" ve "Firmalar / Cariler" tek "Cariler" sayfasında birleşecek.** Firma kartı (ad, vergi no, telefon, adres) ve borç-alacak/ödeme-tahsilat hareketleri aynı sayfada; kasa/banka hesap kartları Muhasebe altında kalır. Eski firma ve hesap kayıtları silinmez, eşleştirme tahminle yapılmaz; yetkiler (`firmalar.*`, hesap yetkileri) korunur ve testle doğrulanır.

## 11 Kasım 2026 — Araştırma önerileri kabul edildi (ayrıntı: `ARASTIRMA_GLOBAL_PROGRAMLAR.md`)

Kullanıcı kararı: **A3 (arınma / kesim yasağı koruması) hariç tüm öneriler eklensin.** Arınma koruması uygulanmayacak; mevcut sağlık kayıtlarındaki eski arınma bilgileri v0.15'teki gibi korunur, yeni engel/uyarı eklenmez.

Önerilen sıra (kullanıcı farklı karar vermedikçe):

### v0.16 (mevcut listeye ek)
- [ ] **F1** Ana Sayfa gösterge kartları: aktif baş, ortalama günlük artış, yem stoğu kaç gün yeter, bugünkü tedavi/işler, ödenecek/tahsil edilecekler (her kart yetkiye tabi).

### v0.17
- [ ] **A2** Rasyon ve günlük yemleme: rasyon tarifi ve kg maliyeti, padok bazlı günlük yem ve yemlik okuma, mikser yükleme listesi, stoktan otomatik düşüm, maliyetin padok/partiye yazılması, tarımdan besiye iç transfer (çift sayım yok).

### v0.18
- [ ] **A1** Parti kapanış raporu: giriş baş/kg/bedel, yem ve ilaç maliyeti, ölüm-hastalık oranı, günlük canlı ağırlık artışı, yem dönüşüm oranı, 1 kg artış maliyeti, baş başı ve parti kâr/zarar.
- [ ] **D1** Tarla işlemleri günlüğü: ekim, gübre, ilaç, sulama, hasat; girdinin stoktan düşümü; dekar başı maliyet ve verim; münavebe geçmişi.

### Altyapı çalışması
- [ ] **C1** Güvenli uzaktan erişim (özel ağ), çok kullanıcılı veritabanı (PostgreSQL), otomatik dış yedek ve geri yükleme denemesi.
- [ ] **C2** Bildirimler (e-posta/SMS/WhatsApp): ajanda, stok alarmı, geciken tedavi.

### Sonraki sürümler
- [ ] **B1** Tablet/telefon saha ekranı (büyük düğmeler; tartım, tedavi, padok değişikliği). C1'e bağlı.
- [ ] **B2** Tartı ve elektronik küpe okuyucu dosyalarını içe aktarma (kontrol edip kaydetme).
- [ ] **B3** DelPro güvenli içe aktarma (önceki listede de var; öncelik yükseltildi).
- [ ] **D2** Sezon bütçesi ile gerçekleşenin karşılaştırması.
- [ ] **D3** Parselleri harita üzerinde gösterme.
- [ ] **E1** e-Fatura / e-Arşiv / e-Müstahsil (GİB entegratörü üzerinden; kontrolsüz otomatik kayıt yok).
- [ ] **E2** Logo / Mikro / Luca gibi muhasebe programlarına aktarım dosyası.
- [ ] **E3** TÜRKVET küpe listesi ile aktif hayvanların karşılaştırılması (dosya ile; eksik/fazla küpe listesi).
- [ ] **F2** Personele görev atama, tamamlama ve ajandaya bağlama.
- [ ] **F3** Tüm listelerde tek tip arama, filtre, Excel/PDF aktarımı ve yazdırma.
- [x] ~~A3 Arınma / kesim yasağı koruması~~ — **kullanıcı istemedi, uygulanmayacak.**

## 11 Kasım 2026 — Ek öneriler ve yeni talepler (kullanıcı: "hepsini ekleyelim")

### Claude'un önerileri (kabul edildi)
- [ ] **G1 Şüpheli kayıtları bulma ekranı:** eski hatalardan kalmış olabilecek kayıtları listeler (ör. 30.000.000 kg stok, olağandışı dekar, harf/boşluk farkıyla aynı parsel kodu, aynı küpe). Kullanıcı her kayıt için "Düzelt" veya "Doğru, uyarma" der. Otomatik değişiklik yapılmaz; düzeltmeler işlem geçmişine yazılır.
- [ ] **G2 Kesim ve satış geliri:** çıkışta karkas kg, karkas randımanı (%), kg fiyatı, toplam bedel, alıcı. A1 parti kâr/zarar raporunun ön koşulu (A1 ile aynı sürümde veya önce).
- [ ] **G3 Makine, yakıt ve bakım:** traktör/ekipman kartı, mazot alımı ve tüketimi, bakım/tamir/muayene tarihleri; masrafın tarla/padok maliyetine yazılması; bakım günlerinin ajandaya düşmesi.
- [ ] **G4 Ölüm kaydı ve hayvan sigortası:** ölüm nedeni, veteriner raporu, TARSİM dosya durumu (başvuruldu/ödendi/reddedildi), ölüm oranı raporu.
- [ ] **G5 Yedek ekranı:** son yedeğin zamanı ve yeri, elle "Şimdi Yedek Al", yönetici onayıyla yedekten geri yükleme (önce mevcut durumun yedeği alınır).
- [ ] **G6 Kolay güncelleme:** Mac/Windows'ta tek dosyaya çift tıklayarak yeni sürüm: eski programı kapat → yedek al → kur → ekranda "vX kuruldu". Eski sürümün açık kalması sorununu önler.
- [ ] **G7 Deneme modu:** gerçek veriden ayrı, örnek verili deneme veritabanı; ekranda belirgin "DENEME" etiketi; eğitim için.
- [ ] **G8 Ekran içi yardım:** her ekranda "?" düğmesi ve kısa Türkçe açıklama.

### Kullanıcının yeni talepleri
- [ ] **G9 Her çıkışta otomatik yedek.** Mevcut durum (v0.15): program açılırken, düzgün kapanırken ve çalışırken belirli aralıklarla yedek alınıyor. Eklenecek: **kullanıcı "Çıkış Yap" dediğinde** de yedek; pencere/terminal kapatılırken yedek alındığının doğrulanması; yedek başarısızsa ekranda Türkçe uyarı; eski yedeklerin düzenli silinmesi (ör. son 30 gün + her ayın son yedeği) ki disk dolmasın. Elektrik kesintisinde son anın yedeği garanti edilemez.
- [ ] **G10 Girişte hatalı / olağandışı değer uyarısı** (kaydetmeden önce "Emin misiniz?" veya engel). Örnekler:
  - tarih gelecekte ya da çok eski; çıkış tarihi giriş tarihinden önce
  - hayvan tartımı makul aralık dışında (ör. besi < 50 kg veya > 1.200 kg; buzağı > 300 kg); son tartıma göre ani büyük kayıp/artış (günlük artış < −1 veya > 3 kg/gün)
  - giriş kilosu çıkış kilosundan büyük
  - dekar, stok miktarı, fiyat, KDV oranı olağandışı (ürünün geçmiş ortalamasından çok farklı birim fiyat)
  - stok çıkışı mevcut bakiyeden fazla (stok eksiye düşüyor)
  - aynı gün aynı hayvana ikinci tartım, aynı belgenin tekrar girilmesi
  - Engel ile uyarı ayrılacak: kesin hatalar engellenir; olağandışı ama mümkün değerler için "Yine de kaydet" seçeneği. Sınırlar ayarlardan değiştirilebilir olacak.
- [ ] **G11 Diğer bölümlerde anlamsız durum uyarıları** (Ana Sayfa'da "Kontrol edilmesi gerekenler" kutusu + G1 ekranında):
  - çıkışı yapılmış/ölmüş hayvana yeni tartım, tedavi veya padok değişikliği
  - padokta kapasiteden fazla hayvan; grubu/padoku olmayan aktif hayvan
  - uzun süredir tartılmamış aktif hayvan; bitiş tarihi geçmiş ama kapanmamış tedavi
  - eksiye düşmüş stok; uyarı seviyesinin altındaki ürünler
  - stoğu olan ama faturası/fiyatı olmayan giriş; toplamı tutmayan fatura; vadesi geçmiş ödeme/tahsilat
  - hasadı girilmemiş geçmiş sezon; parsel alanından fazla ekim
  - izin ve mesai çakışması (izindeki personele mesai)
  - Her uyarı tıklanınca ilgili kayda gider; "Doğru, uyarma" ile kapatılabilir (kim kapattığı kaydedilir).

**Önerilen sıra:** G9, G10 ve G6 → v0.16'ya (güvenlik ve veri doğruluğu). G1, G5, G11 → v0.17. G2 → A1 ile birlikte v0.18. G3, G4, G7, G8 → sonraki sürümler.
