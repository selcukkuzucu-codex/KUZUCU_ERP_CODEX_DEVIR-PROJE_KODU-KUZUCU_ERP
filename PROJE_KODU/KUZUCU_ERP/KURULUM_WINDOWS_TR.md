# KUZUCU ERP — Windows yerel pilot v0.16.0

Ön test ve geliştirme sürümü. Değişiklikler `SURUM_NOTLARI_V16.md` dosyasındadır. v0.16 veritabanına yeni tablo/sütun eklemez; kayıtlarınız yerinde kalır.

## Güncelleme — kolay yol (önerilen)

1. Eski programın açık komut penceresinde **Control + C** yapıp kapanmasını bekleyin. Tarayıcıyı kapatmak yeterli değildir.
2. Yeni ZIP'e sağ tıklayıp **Tümünü Ayıkla** deyin (örneğin İndirilenler'e). Eski `KUZUCU_ERP` klasörüne dokunmayın.
3. Açılan klasörde `PROJE_KODU\KUZUCU_ERP` içindeki **GUNCELLE_WINDOWS.bat** dosyasına çift tıklayın. "Windows bilgisayarınızı korudu" uyarısında **Ek bilgi → Yine de çalıştır** deyin.
4. Program eski kurulumu Masaüstünde veya `C:\KUZUCU_ERP` içinde arar. Bulamazsa eski `KUZUCU_ERP` klasörünü pencereye sürükleyip Enter'a basın.
5. Onay için **E** yazıp Enter'a basın. Güncelleme: eski program açıksa durur; mevcut klasörün **tam yedeğini** `Belgeler\KUZUCU_ERP_Yedekler\surum_oncesi_...` içine alır; yalnız program dosyalarını yeniler (`ciftlik.db`, `data`, `raporlar` yerinde kalır); sonra programı açar.
6. Ekranda **Pilot v0.16** yazmalıdır; gerekirse **Control + Shift + R** ile yenileyin. Mevcut hesabınızla giriş yapın.

## İlk kurulum veya elle güncelleme

1. Mevcut `KUZUCU_ERP` klasörünüz varsa tamamını ayrı bir yere kopyalayın. Eski klasörü ve `Belgeler\KUZUCU_ERP_Yedekler` içindeki yedekleri silmeyin.
2. Yeni ZIP'teki `PROJE_KODU` içindeki `KUZUCU_ERP` klasörünü örneğin `C:\KUZUCU_ERP` içine alın. Ağ/eşitleme sürücüsünden çalıştırmayın.
3. Kayıtlarınızı sürdürmek için program kapalıyken eski `ciftlik.db`, `data` ve `raporlar` klasörlerini yeni klasöre kopyalayın. `.venv` klasörünü kopyalamayın.
4. Python 3.11–3.13 yoksa https://www.python.org/downloads/windows/ adresinden yükleyin; kurulumdaki Python'ı komut yoluna ekleme seçeneğini işaretleyin.
5. `BASLAT_WINDOWS.bat` dosyasına çift tıklayın. İlk kurulumda internet gerekir. Gereksinimler, test edilen sürümleri koruyan `requirements.constraints.txt` ile kurulur.
6. Program hazır olunca tarayıcıda `http://127.0.0.1:8000` açılır. Komut penceresini açık bırakın.
7. Önceki veritabanını taşıdıysanız mevcut hesabınızla giriş yapın. Boş kurulumda ilk yönetici hesabınızı oluşturun; hazır parola yoktur. Önce kayıt sayılarını ve açılış yedeğini kontrol edin.

8000 bağlantı noktası başka bir uygulamadaysa süreç zorla kapatılmaz. Eski KUZUCU ERP penceresini Control + C ile durdurup tekrar deneyin. Eski klasörünüzü ve yedeğinizi koruyun; yeni verilerin üstüne eski yedek yazmayın.

## Yedek ve yerel parola kurtarma

Program her **Çıkış Yap**'ta ve 30 dakikada bir de yedek alır; **Yönetim → Yedekler** sayfasında son yedek saati görünür. `YEDEK_AL_WINDOWS.bat` mevcut SQLite veritabanını `Belgeler\KUZUCU_ERP_Yedekler` içine bütünlüğü kontrol edilerek yedekler. Açılış/kapanış ve program çalışırken dönemsel yedek de vardır. SQLite yedeği **görsel ve belge dosyalarını içermez**; `data` ve `raporlar` klasörlerini ayrıca yedekleyin. Farklı diske yedek kopyalamak ayrıca gerekir.

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
