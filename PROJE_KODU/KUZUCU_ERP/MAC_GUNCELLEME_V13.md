# KUZUCU ERP v0.13 — Mac güncelleme ve güvenli açılış

## Kurmadan önce

Bu paket **yerel pilot** sürümdür. İnternete açık bir işletme sunucusunda kullanılmak üzere güvenlik denetiminden geçmemiştir. Mac'teki eski kayıtlarınızı silmeyin.

1. KUZUCU ERP açıksa Terminal'de **Control + C** ile düzgün kapatın. Normal kapanışta ayrıca otomatik yedek alınır.
2. Masaüstünde **KUZUCU_ERP** klasörünün adını **KUZUCU_ERP_ESKI** yapın; klasörü silmeyin.
3. Bu ZIP dosyasını çift tıklayarak açın ve içindeki **KUZUCU_ERP** klasörünü Masaüstüne taşıyın.
4. Mac'te önceden girilmiş kayıtlarınız varsa eski klasördeki **ciftlik.db** dosyasını yeni **KUZUCU_ERP** klasörüne kopyalayın. Eski klasörde `data/parcel_images` varsa, aynı klasör yoluyla yeni sürüme taşıyın. Henüz kayıt yoksa bu adım gerekmez. **Windows'tan veri aktarmak gerekmiyor.**
5. Terminal'de şu komutu çalıştırın:

   ```bash
   bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"
   ```

6. Chrome'da **http://127.0.0.1:8000** adresini açın. Terminal'de **Mac yerel pilot v0.13** yazmalıdır.
7. İlk açılışta **İlk Yönetici Hesabı** oluşturun. Kullanıcı adı ve güçlü şifrenizi güvenli yerde tutun; hazır varsayılan şifre yoktur. Varsa mevcut v0.13 kullanıcı hesabınızı kullanın.
8. **Kullanıcılar ve Yetkiler** bölümünden çalışanları ekleyin; her bölüm ve rapor türü için izinleri kutucuklarla verin.

## Neler değişti?

- Hayvan ve buzağı girişi: Irk adını yazarken eşleşen seçeneklerden seçme.
- Buzağı kaydı: Parti / Alım Grubu yerine **Açıklama** alanı. Eski parti değerleri veritabanında korunur.
- Toplu buzağı çıkışı: İşletme Küpe No ile teker teker listeye ekleme; her buzağıya ayrı çıkış kilosu, ortak çıkış tarihi ve **Toplu Çıkış No**; **Toplu Kaydet**. Herhangi bir hayvan hatalıysa hiçbiri kaydedilmez.
- Toplu çıkış performans raporu: Verdiğiniz Toplu Çıkış No ve tarih aralığıyla filtre; giriş/çıkış kg, gün, günlük ortalama canlı ağırlık artışı, çıkış/giriş oranı; yetki varsa CSV.
- Giriş ve yetki: Yönetici hesap açar; bölüm bazında görüntüleme, oluşturma, düzeltme, silme ve dışa aktarım izinleri.
- Raporlar: Stok, hayvan, tartım, parsel, sağlık ve buzağı raporları için ayrı sunucu tarafı erişim kontrolü; yetkisiz kullanıcı doğrudan API/CSV üzerinden aşamaz.
- Hareket kayıtları: Stok ve hayvan/buzağı/sağlık tablolarında Kaydeden bilgisi; tarih, kullanıcı, eski ve yeni değişiklikler İşlem Geçmişi'nde. Eski kayıtlarda işlemi yapan kişi bilinmiyorsa **Eski kayıt** gösterilir.
- Form taslakları: Kullanıcı bazında otomatik taslak, kaydedilmemiş bilgilerde sayfadan çıkış uyarısı.
- Güvenlik: Şifreler düz metin olarak tutulmaz; giriş çerezi ve form güvenlik doğrulaması kullanılır.
- Otomatik yedek: Önceki kayıtları güncellemeden önce, her 30 dakikada bir program açıkken ve düzgün kapanışta SQLite yedeği alınır.

## Otomatik yedekler

Yedekler `~/Documents/KUZUCU_ERP_Yedekler` klasöründe tutulur. Program kapatılırken bilgisayarın elektriği kesilirse son taslak dosyasının tamamını kaydetmek mümkün olmayabilir; bu nedenle kayıtlar program çalışırken korunur. Şifreli harici/NAS yedeği ve güvenli bulut çok kullanıcılı kullanım için daha sonra kurulmalıdır.

## Güvenlik ve sınırlar

- Bu paket bir Mac üzerinde **127.0.0.1** adresinde çalışan tek bilgisayarlı pilot uygulamadır. Çok kullanıcılı canlı işletme verisi için henüz uygun değildir.
- Muhasebe, banka, kasa, maaş ve henüz geliştirilmemiş rapor türleri yetki listesinde **gelecek** olarak işaretlidir; bu sürüm bunları işlevsel olarak eklemez.
- Eskiden girilmiş kayıtların hangi kullanıcı tarafından oluşturulduğunu geriye dönük öğrenmek mümkün değildir.
- Uygulama içinden denetim geçmişi silinemez. Ancak yerel veritabanı dosyasını elinde bulunduran yetkili bir kişi, dosya düzeyinde değişiklik yapabilir; üretim için ayrı, değiştirilemez merkezi log sistemi gerekir.
- Sağlık geçmişindeki örnekler veteriner onayının yerine geçmez; 10 gün içindeki aynı adlı ilaç uyarısı korunur.
- Otomatik yedek alma başarısız olursa Terminal'de uyarı görünür. Yedeklerin arada bir açılarak doğrulanması önerilir.
