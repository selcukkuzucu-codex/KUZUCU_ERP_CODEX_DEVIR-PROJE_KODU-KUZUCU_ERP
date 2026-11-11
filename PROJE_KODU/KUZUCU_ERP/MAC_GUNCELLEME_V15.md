# KUZUCU ERP v0.15.0 — Mac'te güvenli güncelleme

10 Kasım 2026. Ön test ve geliştirme sürümü. Bu paket yeni alanlar ve tablolar ekler; eski buzağı kilogram kayıtlarını litreye dönüştürmez, eski fiyat/grup/süt dönemi bilgilerine tahmin yazmaz.

## Önce kayıtları koruyun

1. Açık KUZUCU ERP'nin Terminal penceresinde **Control + C** yapın ve kapanmasını bekleyin. Tarayıcıyı kapatmak programı durdurmaz.
2. Eski program klasörünün **tamamını** ayrı bir yere kopyalayın. `ciftlik.db`, varsa `ciftlik.db-wal`, `ciftlik.db-shm`, `data/parcel_images`, `data/documents` ve `raporlar` birlikte korunsun. Program düzgün kapandıysa yan veritabanı dosyaları kalmayabilir.
3. `Belgeler/KUZUCU_ERP_Yedekler` içindeki yedekleri de koruyun. Otomatik SQLite yedeği fotoğrafları ve rapor dosyalarını içermez; klasör kopyası bu yüzden ayrıca gerekir.
4. Eski program klasörünü örneğin `KUZUCU_ERP_ESKI_V14` diye yeniden adlandırın. Aynı ad varsa farklı bir yedek adı seçin. Eski klasörü silmeyin, yeni dosyalarla birleştirmeyin.

## Yeni sürümü açın

5. `KUZUCU_ERP_v0.15.0.zip` dosyasına çift tıklayın. Açılan paketin içindeki `PROJE_KODU/KUZUCU_ERP` klasörünü Masaüstüne kopyalayın.
6. Mevcut kayıtları sürdürmek için, program kapalıyken eski klasördeki `ciftlik.db`, `data/parcel_images`, `data/documents` ve `raporlar` klasörlerini yeni `KUZUCU_ERP` içine kopyalayın. `.venv` klasörünü kopyalamayın. Windows verilerini Mac'e aktarmanız gerekmiyor. Özel bir veritabanı veya dosya yolu ayarladıysanız aynı yolu koruyun.
7. Terminal'i açın ve şu komutu çalıştırın:

   ```bash
   bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"
   ```

8. İlk kurulumda Python 3.11–3.13 ve internet gerekir. Program hazır olduktan sonra tarayıcıda `http://127.0.0.1:8000` açılır. Terminal penceresini açık bırakın.
9. Ekranda **v0.15** yazdığını kontrol edin. Eski görünüm varsa **Command + Shift + R** yapın. Eski sürüm hâlâ 8000 bağlantı noktasını kullanıyorsa eski Terminal'de Control + C yapın; başka programı zorla kapatmayın.
10. Eski veritabanını taşıdıysanız aynı kullanıcı adı ve parolayla giriş yapın. Yeni/boş kurulumda kendi ilk yönetici hesabınızı oluşturun; hazır parola yoktur.

## İlk kontrol

- Hayvan, buzağı, parsel ve stok kayıt sayılarınızı eski sürümle karşılaştırın.
- Eski buzağı kartlarında **Grup No**, **Süt içme durumu** ve **Hayvan başı fiyat** bilinmiyorsa boş kalır. Doğru bilgiyi karttan girin. Süt içen sayımı yalnız açıkça işaretlenen aktif buzağıları kapsar.
- Eski süt/mama kayıtları kilogram olarak korunur; yeni toplu girişte mama **litre**, yem **kg** alınır. Eski kilogramı litre gibi yorumlamayın.
- Yeni bölüm ve rapor yetkilerini yönetici hesabından gereken personele verin. Önce deneme kaydıyla yeni akışları kontrol edin.
- Fatura taslağı stok/cariyi etkilemez; kontrol edip **Onayla ve İşle** dediğinizde işler. Önceden kantardan girilmiş stoğu doğru hareketle ilişkilendirin.

Açılış öncesi, normal kapanış ve program açıkken dönemsel SQLite yedeği alınır. Mevcut veritabanının açılış öncesi yedeği alınamazsa program geçiş yapmadan Türkçe uyarıyla durur; yedek hedefinin erişimini kontrol edin. İlk açılışta yedek dosyasının oluştuğunu da doğrulayın. Eski sürüme dönüşte yeni veritabanını eski kaynakla açmayın: yeni kayıtlar girdiyseniz üzerlerine eski yedek yazmayın, iki kopyayı koruyup destek alın.

## Giriş sorunu

Kullanıcı adı, görünen Ad Soyad'dan farklı olabilir. Önce doğru klasörü ve hesabı kontrol edin; şifrenizi sohbete yazmayın. Başka bir yöneticiniz varsa Kullanıcılar bölümünden parola yenileyebilir. Gerekirse program kapalıyken yerel, yedek alan kurtarma aracı kullanılabilir:

```bash
cd "$HOME/Desktop/KUZUCU_ERP"
.venv/bin/python tools/reset_password.py
```

Araç mevcut kullanıcı adını ve yeni parolayı yalnız o bilgisayarın Terminal'inde sorar; boş veritabanı oluşturmaz. İşlemi hedef hesabı ve veritabanı yolunu gördükten sonra onaylayın.

## Fotoğraf okuma ve cihaz sınırı

Fotoğraftan metin/küpe okuma için bilgisayarda **Tesseract**, Türkçe ve İngilizce dil dosyaları ayrıca gerekir. Bulanık veya örtülü rakamlar güvenilir okunmayabilir; fotoğrafla karşılaştırıp düzeltmeden kaydetmeyin. Bu paket telefonun Mac'e bağlantısını kurmaz. Telefonda `127.0.0.1` Mac'i göstermez; telefon erişimi ve gerekli güvenli bağlantı ayrı kurulumdur. iPad'de Codex geliştirmesi için kökteki `IPAD_ILE_DEVAM.md` dosyasını okuyun.

Bu bulut çalışmasında fiziksel Mac/Windows/iPhone kurulumu doğrulanmaz; test kanıtları kökteki `SURUM_DOGRULAMA.md` dosyasındadır.

Başlatma/kurulumun teknik ayrıntıları uygulama klasöründeki `gunlukler/kurulum.log` ve `gunlukler/baslatma.log` dosyalarında tutulur. Bunlar kaynak ZIP'e alınmaz; destek için paylaşmadan önce dosyada işletme bilgisi bulunup bulunmadığını kontrol edin.
