# KUZUCU ERP — Windows yerel pilot v0.15.0

Ön test ve geliştirme sürümü. Değişiklikler `SURUM_NOTLARI_V15.md` dosyasındadır. Yeni sürüm mevcut SQLite'a alan ve tablolar ekler; geçiş öncesinde kayıtları koruyun.

## Güncelleme / ilk açılış

1. Eski programın açık komut penceresinde **Control + C** yapıp kapanmasını bekleyin. Tarayıcıyı kapatmak yeterli değildir.
2. Mevcut `KUZUCU_ERP` klasörünün tamamını ayrı bir yere kopyalayın. Eski klasörü ve `Belgeler\KUZUCU_ERP_Yedekler` içindeki yedekleri silmeyin.
3. Yeni ZIP'e sağ tıklayıp **Tümünü Ayıkla** deyin. `PROJE_KODU` içindeki `KUZUCU_ERP` klasörünü örneğin `C:\KUZUCU_ERP` içine alın. Eski klasörle birleştirmeyin; ağ/eşitleme sürücüsünden çalıştırmayın.
4. Kayıtlarınızı sürdürmek için program kapalıyken eski `ciftlik.db`, `data/parcel_images`, `data/documents` ve `raporlar` klasörlerini yeni klasöre kopyalayın. `.venv` klasörünü kopyalamayın. Özel yol ayarlarınız varsa aynı veritabanı/görsel/belge yollarını koruyun.
5. Python 3.11–3.13 yoksa https://www.python.org/downloads/windows/ adresinden yükleyin; kurulumdaki Python'ı komut yoluna ekleme seçeneğini işaretleyin.
6. `BASLAT_WINDOWS.bat` dosyasına çift tıklayın. İlk kurulumda internet gerekir. Gereksinimler, test edilen sürümleri koruyan `requirements.constraints.txt` ile kurulur.
7. Program hazır olunca tarayıcıda `http://127.0.0.1:8000` açılır. Komut penceresini açık bırakın. Ekranda **v0.15** yazmalıdır; gerekirse **Control + Shift + R** ile yenileyin.
8. Önceki veritabanını taşıdıysanız mevcut hesabınızla giriş yapın. Boş kurulumda ilk yönetici hesabınızı oluşturun; hazır parola yoktur. Önce kayıt sayıları ve açılış yedeğini kontrol edin.

8000 bağlantı noktası başka bir uygulamadaysa süreç zorla kapatılmaz. Eski KUZUCU ERP penceresini Control + C ile durdurup tekrar deneyin. Eski klasörünüzü ve yedeğinizi koruyun; yeni verilerin üstüne eski yedek yazmayın.

## Yedek ve yerel parola kurtarma

`YEDEK_AL_WINDOWS.bat` mevcut SQLite veritabanını `Belgeler\KUZUCU_ERP_Yedekler` içine bütünlüğü kontrol edilerek yedekler. Açılış/kapanış ve program çalışırken dönemsel yedek de vardır. SQLite yedeği **görsel ve belge dosyalarını içermez**; `data` ve `raporlar` klasörlerini ayrıca yedekleyin. Farklı diske yedek kopyalamak ayrıca gerekir.

Parolayı unuttuysanız önce doğru kullanıcı adını ve klasörü kontrol edin; şifreyi sohbete yazmayın. Başka bir yönetici parola değiştirebilir. Gerektiğinde program kapalıyken uygulama klasöründeki komut penceresinde şu yerel aracı çalıştırın:

```bat
.venv\Scripts\python.exe tools\reset_password.py
```

Araç mevcut kullanıcı adını ve yeni parolayı yalnız bu bilgisayarda sorar, işlem öncesi yedek alır; hedef hesap ve veritabanı yolu kontrol edilerek onaylanmalıdır. Yeni/boş veritabanı üretmez.

## Fotoğraf okuma ve kapsam

Görsel metin/küpe okuma için **Tesseract**, Türkçe ve İngilizce dil dosyaları ayrıca kurulmalıdır. Okunan rakamları belge/fotoğrafla karşılaştırın; kapalı rakam tamamlanmaz, otomatik başarı garantisi yoktur. Seçilebilir metin içeren PDF'ler doğrudan okunabilir; taranmış PDF'yi bu sürümde destekleniyor saymayın.

Yeni stok/fatura/cari, personel/mesai/izin ve fotoğraftan kontrollü aktarım işlevleri pilot kapsamındadır; maaş bordrosu, resmî muhasebe/e-fatura, banka/e-posta/SAP bağlantısı ve tarım-besi maliyet dağıtımı tamamlanmış değildir. Kaynaklar gerçek işletme DB/fotoğraf/şifrelerini içermez.

Fiziksel Windows kurulumu bu Linux bulut ortamında doğrulanmaz. ERP'ye telefon/iPad bağlantısı, internet yayını veya cihazlar arası eşitleme kurulmaz. iPad'de Codex geliştirmesi için kökteki `IPAD_ILE_DEVAM.md` dosyasını okuyun.

Başlatma/kurulumun teknik ayrıntıları uygulama klasöründeki `gunlukler/kurulum.log` ve `gunlukler/baslatma.log` dosyalarında tutulur. Bunlar kaynak ZIP'e alınmaz; destek için paylaşmadan önce dosyada işletme bilgisi bulunup bulunmadığını kontrol edin.
