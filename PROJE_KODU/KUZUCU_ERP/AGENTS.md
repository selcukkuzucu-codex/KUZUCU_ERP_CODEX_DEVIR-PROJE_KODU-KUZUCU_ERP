# Codex çalışma yönergesi — KUZUCU ERP

ÖNCE `../../KUZUCU_ERP_PROJE_DEVIR_NOTLARI.md`, `../../GELISTIRME_LISTESI.md`, `MAC_GUNCELLEME_V14.md` ve `SURUM_NOTLARI_V14.md` dosyalarını oku. Bu iki üst dizindeki belge bulunmuyorsa kullanıcıdan aktarım paketinin kökündeki devir notları ve geliştirme listesini iste; geçmiş bağlamı uydurma.

- Güncel aşama: ön test ve geliştirme; son hazırlanan pilot v0.14.0. Kullanıcı iPad'de **yalnızca Codex'te geliştirmeye devam etmek** istiyor; bu talebi ERP'ye uzaktan erişim veya yayınlama izni sayma. Aynı hesap/sohbet ya da ZIP aktarımıyla devam et; ortam durumunu ayrıca kontrol et.

- Dil: Kullanıcının gördüğü her ekran, hata, uyarı, başarı ve doğrulama mesajı sade ve anlaşılır Türkçe olmalı. Teknik ayrıntılar logda kalmalı.
- Proje adı KUZUCU ERP; yeşil/altın boğa başlı görsel kimlik korunmalı.
- Kullanıcı yeni özellik istediğinde **kodu değiştirme veya sürüm paketi üretme**. İstekleri backlog dosyasına ekle; yalnızca kullanıcı açıkça **“Son sürümü hazırla”** dediğinde birikmiş değişiklikleri uygula, test et ve sürümle.
- Mevcut `ciftlik.db` ve `data/parcel_images` üretim verilerine zarar verme. Önce yedek al, migration'ları geriye dönük uyumlu yaz. ZIP içinde gerçek kullanıcı veritabanı bulunmaz.
- Pilot uygulamayı kullanıcı açıkça istemedikçe internete açma. Kimlik doğrulaması, yetkiler, rapor yetkileri, CSRF, audit ve veri gizliliği sunucuda doğrulanmalı.
- Araç/ilaç önerilerini veteriner onayı gerektiren karar desteği olarak sun, otomatik reçeteleme yapma.
- Miktarlar Türkçe biçimlendirilmeli: 30000 -> 30.000, 12500.5 -> 12.500,5. Görünen nokta ondalık ayırıcı olarak yorumlanmamalı.
- Toplu işlemler atomik yapılmalı, olası hatada hiçbir kısmi kayıt kalmamalı.
- Kod değişikliği öncesinde mevcut testleri çalıştır, yeni davranış için test yaz. Kodda var olduğu varsayılan tüm özellikleri ayrıca doğrula.
- Mac kullanıcısı terminal adımlarında tek tek, kısa ve net Türkçe yönerge ister.
