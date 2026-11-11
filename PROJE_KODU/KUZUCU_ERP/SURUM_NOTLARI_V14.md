# KUZUCU ERP v0.14.0 — 6 Kasım 2026

Ön test ve geliştirme için pilot düzeltme sürümü.

- Parsel görseli ekleme/değiştirme isteğine oturum güvenlik doğrulaması eklendi. Oturumlu kullanıcıdaki 403 hatasının bu nedeni düzeltildi.
- Ajanda kaydı silme işlemi ortak güvenli istek yoluna alındı; sunucu hatası anlaşılır Türkçe gösterilir.
- Geçersiz/eksik alanlar ve tekrar eden kayıt uyarılarında teknik alan adlarının kullanıcıya görünmesi azaltıldı; bilinmeyen alanlarda güvenli Türkçe açıklama kullanılır.
- Tablet boyutlarında menü, başlık, kullanıcı bilgileri, formlar ve tablo kaydırması düzenlendi. Küçük dokunmatik ekranlarda kontrol boyutları iyileştirildi.
- Ekrandaki sürüm bilgisi v0.14 oldu. CSS/JavaScript adresleri sürümlendi; eski tarayıcı önbelleğinin yeni dosyaları gizlemesi önlendi.
- Test edilen Python paket sürümleri `requirements.constraints.txt` ile kurulumda korunur. Yeni Mac/Windows kurulum rehberi ve iPad/Codex devam rehberi eklendi.
- Kaynak paketine veri tabanı, işletme görselleri, şifreler, sanal ortam ve test çıktılarını almayan paketleyici ve paket bütünlük listesi eklendi.

Bu sürüm veri modelini değiştirmez. Önceki v0.13 açılış/yedekleme/geçiş davranışı korunur. Genel parsel kayıt hatasının her olası nedeni çözüldü veya eski yanlış stok değerleri düzeltildi iddiası yoktur. Eski miktarlar tahminle değiştirilmez.

Bu paket uzak sunucu, özel ağ veya gerçek iPad bağlantısı kurmaz. Muhasebe/personel gibi planlanan modülleri, canlı SAP bağlantısını ya da tam üretim güvenliğini tamamlanmış saymayın. Ayrıntılı test sonucu paket kökündeki `SURUM_DOGRULAMA.md` dosyasındadır.
