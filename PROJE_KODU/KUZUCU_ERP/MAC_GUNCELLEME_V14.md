# KUZUCU ERP v0.14.0 — Mac'te güvenli güncelleme

Bu sürüm ön test ve geliştirme içindir. Veritabanı modelinde yeni değişiklik yoktur; mevcut açılış yedeği ve eski SQLite sütunlarını tamamlayan geçiş korunur. Gerçek Mac kayıtları bu ZIP'te bulunmaz.

1. Açık KUZUCU ERP penceresinin Terminal'inde **Control + C** yapın ve kapanmasını bekleyin.
2. Masaüstündeki eski `KUZUCU_ERP` klasörünün bir kopyasını güvenli bir yere alın. Kopya; `ciftlik.db`, varsa `data/parcel_images` ve `raporlar` klasörlerini birlikte içersin. Eski klasörü silmeyin.
3. Eski masaüstü klasörünün adını `KUZUCU_ERP_ESKI_V13` yapın. Aynı isimde klasör varsa üzerine yazmayın; farklı bir yedek adı kullanın.
4. Yeni ZIP'i açın. İçindeki `PROJE_KODU/KUZUCU_ERP` klasörünü Masaüstüne kopyalayın. Üst üste dosya birleştirmeyin.
5. Kayıtlarınızı sürdürmek istiyorsanız, program kapalıyken eski klasörden `ciftlik.db`, varsa `data/parcel_images` ve `raporlar` içeriğini yeni klasöre kopyalayın. Boş deneme ortamı istiyorsanız bu adımı atlayın. Windows verilerini aktarmanız gerekmiyor.
6. Terminal'i açın ve yalnızca şu komutu çalıştırın:

   ```bash
   bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"
   ```

7. Terminal'de **Mac yerel pilot v0.14** yazdığını kontrol edin. Mac'in tarayıcısında `http://127.0.0.1:8000` adresini açın. Önceki sürüm görünürse **Command + Shift + R** ile yenileyin.
8. v0.13 veritabanını taşıdıysanız mevcut kullanıcı hesabınızla giriş yapın. Boş veritabanıyla başladıysanız kendi ilk yönetici hesabınızı oluşturun; hazır şifre yoktur.
9. Önce kayıt sayılarınızı kontrol edin. Deneme parselinde görsel eklemeyi ve gereksiz bir deneme ajandasını silmeyi deneyin. Kullanılan veritabanını karıştırmamak için eski uygulamayı aynı anda açmayın.

Beklenmeyen bir sorun olursa programı kapatın; eski klasörü ve yedeklerinizi koruyun. Yeni veriler girdiyseniz eski veritabanıyla üzerlerine yazmayın. Sorunu ve ekrandaki Türkçe uyarıyı Codex'e iletin.

Mac/Windows üzerinde fiziksel kurulum bu bulut oturumunda denenemez; paketin Python testleri Linux/Python 3.12 üzerinde çalıştırılır. Görsel fatura OCR'si için Tesseract ve Türkçe dil dosyaları bilgisayarda ayrıca gerekir. iPad'de Codex ve ERP kullanımı için paket kökündeki `IPAD_ILE_DEVAM.md` dosyasını okuyun.
