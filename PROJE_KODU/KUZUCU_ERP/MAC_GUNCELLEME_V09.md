# KUZUCU ERP v0.9 — Mac güncellemesi

## Bu sürümde eklenenler

- **Ajanda / Hatırlatmalar**: Genel, Tarım, Besi, Buzağı, Stok, Personel, Finans başlıkları altında görev ekleme; başlık, açıklama, başlangıç tarihi, saat, tek sefer/günlük/haftalık/aylık tekrar. Liste, düzenleme, durdurma/etkinleştirme, silme ve tamamlandı işaretleme.
- Tekrar eden görevler tamamlandıktan sonra sonraki tekrar günü otomatik hesaplanır. Aylık tekrar 31'in olmadığı aylarda ayın son gününe denk gelir.
- Saati gelmiş hatırlatmalar, **program açıkken** üst bantta gösterilir; yaklaşık dakikada bir kontrol edilir. Program kapalıyken, Mac uyurken veya tarayıcı kapalıyken sistem bildirimi/e-posta/SMS gönderilmez. Bu işlev için ileride ayrı arka plan sunucu ve bildirim entegrasyonu gerekir.
- Hata/uyarı iyileştirmeleri: aynı stok ürünü, hareket türü, miktarı, tarih ve dolu belge numarasıyla mükerrer yeni hareket girişinin engellenmesi; 1.000.000 ve üzeri stok miktarı ile ileri tarihli stok girişlerinde kullanıcı onayı; eksik/hatalı girişlerde daha anlaşılır uyarılar; geçersiz vergi no ve hatırlatma tarih/saat/tekrar doğrulamaları.
- Önceki sürümdeki stok hareketi **Düzenle**, düzeltme geçmişi, firma kartları, Türkçe binlik ayırıcı ve ürün/tarih bazlı stok görünümü korunur.

## Mac'te güncelleme

1. Açık Terminal'de `Control + C` ile KUZUCU ERP'yi kapatın.
2. Masaüstündeki eski `KUZUCU_ERP` klasörünü `KUZUCU_ERP_ESKI` olarak saklayın. Eski verileriniz bu klasördedir.
3. Yeni ZIP'i açın ve içindeki `KUZUCU_ERP` klasörünü Masaüstüne koyun.
4. **Mevcut Mac verileri korunacaksa** eski klasördeki `ciftlik.db` dosyasını yeni `KUZUCU_ERP` klasörünün içine kopyalayın. Önce yedek alın. Veritabanı içinde yeni `reminders` tablosu program açıldığında otomatik oluşturulur.
5. `BASLAT_MAC.command` dosyasını çift tıklayın; gerekirse Terminal'den `bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"` çalıştırın. Programı `http://127.0.0.1:8000` adresinden açın.
6. Ajanda menüsünde tekrar eden bir hatırlatma oluşturun ve liste/düzeltme işlevlerini deneyin.

**Uyarı:** Bu sürüm yalnızca yerel pilot. Henüz kullanıcı hesabı/yetkileri, çok kullanıcılı tutarlılık, üretim ortamı güvenliği veya Mac kapalıyken bildirim hizmeti yoktur. Gerçek üretimde ve internete açık sunucuda kullanmayın.

**Sonraki kapsamlı sürüme kalan önceki istekler:** Parsel uydu görüntüsü ve ada/parsel araması; hayvanlarda TR ve işletme küpe no, doğum tarihi, cinsiyet ve alış kilosu; ayrı buzağı kabul/çıkış ve mama/süt/yem tüketim modülü. Bunlar v0.9'da uygulanmadı.
