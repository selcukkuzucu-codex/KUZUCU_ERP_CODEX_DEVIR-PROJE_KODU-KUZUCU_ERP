# KUZUCU ERP v0.8 — Mac kurulumu / güncellemesi

## Yeni işlevler

- Stok Hareketleri: her satırdaki **Düzenle** butonuyla ürün, işlem türü, miktar, tarih ve referans bilgisi düzeltilebilir.
- Düzeltme nedeni zorunludur; eski/yeni değerler `stock_movement_revisions` tablosuna yazılır. Düzeltme geçmişi ilgili hareketin düzenleme panelinden görülebilir.
- Negatif stok yaratacak düzeltmeler reddedilir. Diğer ürünlere aktarımda eski ve yeni ürün stokları kontrol edilir.
- Firmalar / Cariler: firma adı, vergi no (10 veya 11 rakam; boş bırakılabilir), telefon ve adres alanları; yeni kayıt, arama ve düzenleme.
- v0.7'deki Türkçe binlik gösterim, tarih sıralı ürün stok hareketleri ve toplamlar korunur.

## Kurulum / yükseltme

1. Mac'teki KUZUCU ERP çalışan Terminal penceresinde `Control + C` ile uygulamayı durdurun.
2. Masaüstündeki `KUZUCU_ERP` klasörünün bir yedeğini alın ve `KUZUCU_ERP_ESKI` adıyla saklayın.
3. ZIP dosyasını açın, içindeki yeni `KUZUCU_ERP` klasörünü Masaüstüne yerleştirin.
4. **Mevcut Mac kayıtları korunacaksa:** eski klasördeki `ciftlik.db` dosyasını **yeni klasörün kök dizinine** kopyalayın. Var olan bir dosyanın üzerine yazmadan önce dosyaları yedekleyin. Windows verisi aktarmanız gerekmez.
5. Yeni klasördeki `BASLAT_MAC.command` dosyasını çalıştırın ve tarayıcıda `http://127.0.0.1:8000` adresini açın.
6. `Firmalar / Cariler` menüsünden firma kaydı; `Stok Hareketleri` listesinden `Düzenle` işlemini deneyin.

## Önemli uyarılar

- Var olan miktar yanlış kaydedilmişse, ekranda düzelmesi **otomatik** değildir: ilgili hareketi `Düzenle` aracılığıyla gerçek değerine değiştirin.
- Bu yazılım **yerel pilot** sürümdür. Henüz kullanıcı oturumu, rol/yetki, çok kullanıcılı eşzamanlı stok koruması, yasal muhasebe entegrasyonu ve tüm sistem için değişmez denetim kaydı yoktur. İnternete doğrudan açmayın ve kurumsal canlı üretimde kullanmayın.
- Önceki konuşmalarda istenen uydu parsel görseli, TR/işletme küpe no, doğum tarihi, buzağı kabul/ayrı tüketim bölümü bu pakette henüz yoktur; sonraki kapsamlı sürümde ele alınmalıdır.
