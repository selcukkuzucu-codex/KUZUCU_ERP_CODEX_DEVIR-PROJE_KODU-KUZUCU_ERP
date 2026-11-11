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

## 11 Kasım 2026 — Parsel kayıt hatası incelemesi (kod değiştirilmedi)

Boş deneme veritabanında, gerçek Chromium tarayıcıyla (Türkçe bölge ayarı) Parseller ekranından kayıt denendi.

**Kök neden:** "Alan (dekar)" kutusu tarayıcının sayı kutusu (`type="number"`). Bu kutu Türkçe sayı biçimini (ondalık virgül, binlik nokta) tanımıyor. Stok miktarındaki aynı sorun v0.14'te düzeltilmişti; parsel alanı o düzeltmeye dahil edilmemiş.

- [ ] **Virgül yok sayılıyor (veri bozuluyor):** klavyeyle `12,5` yazılınca kutu `125` oluyor ve 125 dekar kaydediliyor. `35,5` → 355 dekar. Hata mesajı çıkmıyor.
- [ ] **Binlik nokta ondalık sanılıyor:** `1.250` (bin iki yüz elli) → 1,25 dekar kaydediliyor. `1.250,5` → 1,2505.
- [ ] **Tarayıcı uyarıları programın değil, tarayıcının dilinde:** boş/0 alan için "Please fill out this field", "Value must be greater than or equal to 0.001" gibi mesajlar çıkabiliyor. Kullanıcının gördüğü İngilizce uyarının olası kaynağı.
- [ ] **Aynı parsel iki kez kaydedilebiliyor:** `P-1` varken ` P-1 ` (boşluklu) ve `p-1` (küçük harf) ayrı parsel olarak kabul ediliyor. Kod kaydedilmeden önce boşluklar temizlenmeli ve büyük/küçük harf farkı gözetilmeden kontrol edilmeli.
- [ ] Üçten fazla ondalık sessizce yuvarlanıyor (`3,12345` → 3,123). Kullanıcı uyarılmalı.
- [ ] Ada No boş bırakılınca veritabanına boş metin yazılıyor; "boş" olarak saklanmalı (düzenleme ekranı zaten böyle yapıyor).
- [ ] Ekrandaki bilgi mesajı, önceki mesajın 5 saniyelik zamanlayıcısı yüzünden erken kaybolabiliyor; ardışık kayıtta "Kaydedildi" görünmeyebilir.
- Doğru çalışanlar: normal kayıt, Ada No'suz kayıt, aynı kodla tekrar kayıtta Türkçe "Parsel kodu zaten kayıtlı." uyarısı, 0 dekarın engellenmesi. Sunucu günlüğünde hata yok.

**Önerilen düzeltme (sürüm talimatı bekleniyor):** Alan kutusunu stok miktarındaki gibi Türkçe metin kutusu + `canonicalQuantity` dönüşümüyle değiştir; düzenleme formuna da uygula; sunucuda kodu kırp ve harf duyarsız tekrar kontrolü yap; tarayıcı uyarıları yerine Türkçe mesaj göster; regresyon testleri ekle.

**Mevcut veriler:** Eski kayıtlarda alanı 10 kat büyük (virgül kaybı) veya 1000 kat küçük (binlik nokta) parseller olabilir. Otomatik tahminle düzeltilmeyecek; kullanıcı listeyi gözden geçirip "Düzenle" ile düzeltmeli.

**Sınır:** Test, başsız Chromium ile yapıldı; Mac'teki Türkçe Chrome'da virgül davranışı farklı olabilir. Kullanıcının Mac'inde `12,5` yazıp sonucu kontrol etmesi önerilir.
