# KUZUCU ERP — Codex Geliştirme Listesi

## İş akışı
Yeni talep geldikçe buraya ekle; kullanıcı **“Son sürümü hazırla”** demeden uygulama sürümü üretme.

## Öncelikli inceleme / doğrulama
- [x] Aktarılan v0.13 uygulaması koddan incelendi; başlangıçtaki 23 test yeniden geçti.
- [ ] Parsel kaydında karşılaşılan hata için yeniden üretilebilir test ve kök neden analizi.
- [ ] Stokta Türkçe sayı biçimleme ve eski yanlış miktarlar için güvenli düzeltme akışı.
- [ ] Kullanıcı bazlı yetkilerin tüm API/rapor/CSV uç noktalarında güvenlik denetimi.
- [ ] Kayıt/yedeklerin geri yüklenebilirliği, kapanış/elektrik kesintisi senaryoları.
- [ ] Toplu buzağı çıkışında transaction, aynı hayvanın iki kez eklenmesi ve performans hesapları.
- [ ] Tablet/iPad duyarlı tasarım ve ileride güvenli uzaktan erişim (şimdilik kurulum ertelendi).

## Daha uzun vadeli ürün işleri
- [ ] DelPro gerçek CSV formatlarıyla güvenli içe aktarma, Grup No eşleştirmesi.
- [ ] Kantar-fatura e-posta/PDF/görüntü iş akışı ve gözden geçirilen fatura taslakları.
- [ ] İlaç/tedavi etken maddesi eşleştirme ve maliyet dağıtımı; veteriner onay akışı.
- [ ] Yem üretimi, reçeteler, tüketim, tarım-besi iç maliyet transferleri.
- [ ] Personel, maaş, izin, günlük işler, toplu giriş.
- [ ] Muhasebe, banka, hesap bilgileri, hassas rapor yetkileri.
- [ ] NAS yedek, PostgreSQL, migration, eşzamanlı işlem bütünlüğü, izole bulut üretim sistemi.

**Not:** Önceki tüm kullanıcı taleplerinin kapsamı `KUZUCU_ERP_PROJE_DEVIR_NOTLARI.md` dosyasındadır. Bu liste, kodda mevcut olduğu iddia edilen işlevlerin doğrulandığı anlamına gelmez.

## 6 Kasım 2026 — v0.14.0 pilot düzeltme sürümü

- [x] Açık kullanıcı talimatıyla yeni pilot sürüm hazırlandı; proje ön test ve geliştirme aşamasında.
- [x] Parsel görseli yüklemede eksik CSRF başlığı düzeltildi. Genel parsel kaydı hatasının bütün olasılıkları çözülmüş sayılmıyor.
- [x] Ajanda silmenin güvenli ortak istek yolunu kullanması sağlandı.
- [x] Teknik alan adları yerine Türkçe doğrulama ve mükerrer kayıt mesajları eklendi.
- [x] Tablet yerleşimi ve statik dosya sürümleme iyileştirildi; ayrıntılı tarayıcı sonucu `SURUM_DOGRULAMA.md` içinde.
- [x] Kurulum sürüm kısıtları, Mac güncelleme ve iPad/Codex devam rehberi eklendi.
- [x] Özel veri içermeyen, bütünlük listeli kaynak paketi oluşturmak için paketleyici ve testleri eklendi.
- [ ] Gerçek Mac/Windows cihazında yeni ZIP'in kullanıcı kabul testi.
- [ ] Kullanıcının iPad'inde aynı Codex hesabı/sohbet ile devam edebildiğinin cihaz üzerinde kontrolü.

iPad tercihi: **yalnızca Codex'te geliştirme**. ERP'yi evden erişime açma veya Tailscale kurulumu bu sürüm için istenmiyor. Ortam/GitHub/web yayımlaması yapılmayacak. Sonraki yeni talepleri listelemeye devam edin.
