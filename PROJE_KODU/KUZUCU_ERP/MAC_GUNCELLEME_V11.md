# KUZUCU ERP — Mac v0.11 Güncellemesi

Bu pakette **eski veritabanı veya demo verisi yoktur**. Mac bilgisayarınızdaki var olan verileri silmeyin.

## Kurulum / mevcut Mac sürümünü güncelleme

1. Açık ERP varsa Terminal penceresinde `Control + C` ile uygulamayı durdurun.
2. Masaüstündeki `KUZUCU_ERP` klasörünü **silmeden** `KUZUCU_ERP_ESKI` olarak yeniden adlandırın.
3. Bu ZIP'i açarak çıkan **KUZUCU_ERP** klasörünü Masaüstüne yerleştirin.
4. Mevcut **Mac** kayıtlarınızı korumak isterseniz, eski klasördeki `ciftlik.db` dosyasını yeni `KUZUCU_ERP` klasörüne kopyalayın. Yeni pakette aynı isimde veritabanı bulunmadığından dosyanın üzerine yazılmaz.
5. Parsellere önceden resim yüklediyseniz `data/parcel_images` klasörünü de eskiden yeniye kopyalayın. Eski günlük PDF kayıtlarınız için `raporlar` klasörünü saklayın.
6. Yeni klasörde `BASLAT_MAC.command` dosyasını çalıştırın. Gerekirse Terminal ile: `bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"`.
7. Chrome adresi: `http://127.0.0.1:8000`.

**Mac için Python 3.12** kurulu olmalı. Bu başlatıcı uygun Python'u kendisi arar.

**Windows kayıtları aktarılmıyor.** İsterseniz Mac'te tamamen yeni veritabanıyla başlayabilirsiniz: yeni klasöre eski `ciftlik.db` dosyasını kopyalamayın.

## v0.11 özellikler

- **Hayvanlar:** TR küpe no, işletme küpe no, doğum tarihi, yaş gün/ay, erkek/dişi, alım/giriş kg; kayıt düzenleme.
- **Parseller:** Ada no + parsel kodu ve arama; parsel kartına JPG/PNG/WEBP uydu ekran görüntüsü yükleme, aramada görsel açma. Harita servisinden otomatik görüntü çekilmez.
- **Buzağılar:** ayrı giriş/çıkış kartı, parti kodu, cinsiyet, doğum tarihi, giriş ve çıkış kg, planlanan 30-60 veya farklı gün sayısı, günlük mama/süt ve yem tüketimi (kg), ara tartımlar, günlük tüketim düzeltme, tekil ve toplu çıkış.
- **Buzağı toplu çıkış:** parti ve tarih filtresi, CSV dışa aktarma ve yazdırma, gün, kg artışı, günlük ortalama canlı ağırlık artışı `(çıkış kg - giriş kg) / gün`, çıkış / giriş katsayısı `çıkış kg / giriş kg`, artış yüzdesi, toplam ve ağırlıklı günlük artış. Aynı partiden çoklu çıkış işlemi tümüyle başarılı ya da tümüyle reddedilir.
- **Hayvan Sağlığı:** veterinerin onayladığı tedavi ve aşı planı, hayvan bazlı günlük kayıt, uygulama sonuçları, kapanış/iyileşme, geçmiş sonuçların yalnızca karar destek amaçlı gösterilmesi. Sistem kendiliğinden ilaç veya doz önermez.
- **Günlük sağlık çıktısı:** açık tedaviler + Ajanda işlerinin A4 PDF raporu. Program çalışırken saatine göre otomatik PDF üretimi; otomatik fiziksel yazdırma varsayılan kapalıdır, Sağlık ekranında açıkça etkinleştirilebilir ve macOS yazıcısı gerektirir.
- **v0.9 özellikleri korunur:** stok giriş/çıkış/düzeltme geçmişi, 30.000 sayısal biçimi, firmalar, ajanda, giriş uyarıları.

## Veri ve güvenlik sınırları

Bu sürüm **yerel pilot uygulamadır**. Çok kullanıcılı canlı ERP, bulut sunucu, kimlik doğrulama ve çalışan rolleri, ticari sistem yedekleme politikası ve stok/mama entegrasyonu henüz üretime hazır değildir. İnternete açmayın ve gerçek hassas kayıtları yüklemeden önce erişim, yedekleme ve veri güvenliğini tamamlayın.

- Günlük buzağı mama/yem kayıtları **otomatik stok düşümü yapmaz**; stok hareketini ayrı yönetin.
- Bir parsel görüntüsü ayrı `data/parcel_images` klasöründe saklanır. Sadece veritabanını yedeklemek resimleri yedeklemez.
- `ciftlik.db` dosyanızın güncellemeden önce bir kopyasını saklayın. İlk çalıştırmada yeni sütunlar eski SQLite kayıtlarını silmeden eklenir.
- Günlük fiziksel yazdırma yalnızca program açık, saat ayarlı ve yazıcı erişilebilir olduğunda gerçekleşir. Mac kapalıyken rapor veya çıktı alınamaz.
