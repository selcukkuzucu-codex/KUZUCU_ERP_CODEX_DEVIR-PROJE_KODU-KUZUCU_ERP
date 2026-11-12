# KUZUCU ERP Mac v0.7 — Stok hareketi listesi ve sayı düzeltmesi

Bu bir **yerel pilot** sürümdür; üretim/canlı işletme verileri için henüz güvenli değildir.

## Güncelleme
1. Chrome ve KUZUCU ERP açık olabilir; Terminal penceresinde `Control + C` ile durdurun.
2. Eski `KUZUCU_ERP` klasörünün adını `KUZUCU_ERP_ESKI` yapın. **Klasörü silmeyin.**
3. Bu ZIP'i açın ve içindeki `KUZUCU_ERP` klasörünü masaüstüne çıkarın.
4. Eski kayıtlara devam etmek istiyorsanız, sunucu kapalıyken eski klasördeki `ciftlik.db` dosyasının **ayrı bir yedeğini alın**, ardından bu veritabanını yeni `KUZUCU_ERP` klasörüne kopyalayın. `.venv` klasörünü kopyalamayın.
5. Terminal: `bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"`.
6. Chrome: `http://127.0.0.1:8000` → **Stok Hareketleri**.

## Yeni işlevler
- Stok hareketleri ürün bazında ayrı bölümlerde listelenir.
- Tarih sıralama: yeni/eski; hareket tarihi ayrıca kaydedilir.
- Ürün bazında toplam giriş, çıkış ve kalan stok en alttadır.
- Genel toplamlar birimlere göre (kg, ton, adet) ayrılır.
- Girilen `30000` / `30.000` → veritabanına **30000**, ekrana **30.000**.
- Ekranda yanlışlıkla `30.000.000` gösteren `30000.000` API değeri artık **30.000** görüntülenir.

**Önemli:** Önceden yanlış büyüklükte kaydedilmiş bir veritabanı hareketi otomatik düzeltilemez. Önce veritabanını yedekleyin ve miktarın gerçekten yanlış kaydedilip kaydedilmediğini stok hareketi geçmişinde kontrol edin.

Önceden kaydedilmiş hareketlerde yeni **Hareket Tarihi** alanı, varsa kayıt oluşturulma tarihiyle doldurulur. Yeni kayıtlar kendi işlem tarihini kullanır.
