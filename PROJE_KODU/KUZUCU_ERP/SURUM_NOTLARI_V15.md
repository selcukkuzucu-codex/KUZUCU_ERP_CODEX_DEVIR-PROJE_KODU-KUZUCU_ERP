# KUZUCU ERP v0.15.0 — 10 Kasım 2026

Ön test ve geliştirme sürümü. Kullanıcının açık **Son sürümü hazırla** talimatıyla birikmiş talepler uygulandı. Doğrulama durumu paket kökündeki `SURUM_DOGRULAMA.md` dosyasındadır.

- **Türkçe arayüz:** İşlem geçmişinin bölüm, işlem, alan ve durum açıklamaları Türkçe gösterilir; ham denetim verisi veritabanında korunur. Ağ ve doğrulama sorunlarında anlaşılır Türkçe mesaj kullanılır.
- **Parseller:** Yeni parselde isteğe bağlı arazi görseli seçme, önizleme, değiştirme ve kaldırma vardır. Hatalı dosyada yarım parsel kaydı bırakılmaz; mevcut görseller korunur.
- **Kullanıcılar:** Yönetici kullanıcı adını değiştirebilir. Kullanıcı silerken silinecek hesabın kendi parolası doğrulanır; kendi hesabını/son aktif yöneticiyi silme engellenir. Geçmiş işletme ve denetim kayıtları korunur.
- **Buzağılar:** Fiziksel Grup No, süt içme durumu ve hayvan başı alış bedeli (TL/baş) eklenir. Toplu tüketim sırası **Tarih → Mama litre → Yem kg → Grup No**; seçilen her buzağıya aynı miktar uygulanır, toplamlar gösterilir. Tekil günlük tüketim ve ara tartım girişleri kaldırılır; geçmiş kayıtlar korunur. Çıkışta çoklu TR/işletme küpesi kontrolü, alt liste, hayvan başı kilo ve Grup No vardır; yeni çıkışta elle çıkış numarası istenmez.
- **Sağlık:** Sade formda tedavi süresi ve **Sağlık** açıklaması vardır. Başlangıç kayıt günüdür; süre içindeki günlük liste/PDF güncellenir. Kaldırılan eski veteriner/onay/belirti/arınma bilgileri düzenlemede silinmez; verilmemiş onay varmış gibi yazılmaz. Günlük gerçek uygulama ayrı kaydedilir; plan eklemek uygulanmış sayılmaz.
- **Genel bakış:** Aktif erkek/dişi ve ırk toplamları, süt içen erkek/dişi buzağı sayıları yetkiye göre hesaplanır. Aynı TR küpesi iki bölümdeyse bir kez sayılır; bilinmeyen cinsiyet/süt dönemi tahmin edilmez.
- **Toplu hayvan işlemleri:** Virgülle çoklu küpe arama, satır bazında tartım, grup değişimi veya yeni giriş; kesim/ölüm/satış çıkışı ve geçmişi vardır. Hatalı satırda kısmi işlem yapılmaz.
- **Stok:** Doğrudan Stok Girişi, hammadde/ilaç sınıfı, ürün biriminde alarm seviyesi ve kalıcı Uyarılar bölümü eklenir. Onaysız uyarı kalır; onaylanan uyarı 24 saat görünür. Excel `.xlsx` dosyaları eşleştirilip incelendikten sonra topluca aktarılır; aynı kaynak tekrar stoğu çoğaltmaz.
- **Fatura ve hesaplar:** Alış/satış faturası, KDV hariç birim fiyat, satır KDV'si, ara/KDV/genel toplam, taslak/onay/iptal akışı; cari, kasa/banka hesap kartı ve ödeme/tahsilat hareketleri vardır. Onaylı düzeltmeler ters kayıtla izlenir. Faturaya bağlı stok hareketi doğrudan değiştirilmez. Otomatik banka bağlantısı veya resmî muhasebe/e-fatura entegrasyonu değildir.
- **Maliyet:** Faturalı alışların KDV hariç ağırlıklı ortalama birim fiyatı ve tahmini stok maliyeti raporlanır. Fiyatı bilinmeyen giriş ayrıca görünür; tam tarım/besi maliyet merkezi veya ilaç/yem dağıtım motoru değildir.
- **Personel:** Kart, işe giriş/çıkış, mesai, haftalık/yıllık izin, kullanıcı tarafından belirlenen yıllık izin hakkı ve raporlar eklenir. Hak ve ücret hukuki kuralla otomatik tahmin edilmez; bordro/maaş hesaplama yoktur.
- **Hatırlatmalar:** Her N günde/haftada/ayda bir tekrar; takvim ayı ve ay sonu korunur. Yerel program kapalıyken dış bildirim gönderilmez.
- **Fotoğraf ve belge aktarımı:** Küpe fotoğrafında numara adaylarını inceleme ve kayıtla eşleştirme; rapordan belge önizleme, kontrollü fatura kaydı, firmaya belge bağlama, mevcut hayvanlara tartım ekleme akışı vardır. Kullanıcı kontrolü olmadan kayıt yapılmaz. Örtülü rakamlar tamamlanmaz; okuma başarısı garanti edilmez. Üç özgün kullanıcı fotoğrafında tam TR kimliği otomatik çıkarılamadı (**0/3**). Bir fotoğrafta `20013` sayısal adayı bulundu; türü/tamlığı doğrulanmış sayılmaz. Fotoğrafla karşılaştırma ve gerekirse elle giriş gerekir. Sentetik net örnekte okuma doğrulandı; bu sonuç gerçek fotoğraf başarısı sayılmaz. Tesseract ek kurulumu ve gerçek telefon erişimi ayrı gereksinimlerdir.
- **Başlatma:** Yerel sunucunun doğru klasörden çalıştığı kontrol edilir; hazır olmadan tarayıcı açılmaz. Başka/kimliği doğrulanamayan süreç zorla kapatılmaz. Yerel parola kurtarma aracı işlem öncesi yedek alır.

## Veri geçişi ve sınırlar

Yeni SQLite tabloları ve buzağı/sağlık/hatırlatma alanları açılışta eklenir; açılış öncesinde mevcut veritabanı yedeklenir. Önce eski programı kapatıp tüm klasörü ayrıca yedekleyin. Yeni kurulum adımları `MAC_GUNCELLEME_V15.md` ve `KURULUM_WINDOWS_TR.md` içindedir.

Gerçek `ciftlik.db`, parsel/evrak fotoğrafları, şifreler, sanal ortam ve çalışma çıktıları ZIP'e alınmaz. Yeni alanlar eski veriyi tahminle değiştirmez. Geçmiş kilogram mama litreye çevrilmez. Kamera okuma, resmî küpe doğrulaması veya otomatik veteriner önerisi değildir.

Fiziksel Mac/Windows/telefon kabulü, bağımsız üretim güvenliği, NAS yedeği, PostgreSQL çok kullanıcılı geçiş, e-posta/SAP/banka bağlantısı, maaş bordrosu ve kapsamlı işletme maliyet dağıtımı ayrı çalışmalardır. ERP veya Codex ortamı bu paketle internete yayımlanmaz.
