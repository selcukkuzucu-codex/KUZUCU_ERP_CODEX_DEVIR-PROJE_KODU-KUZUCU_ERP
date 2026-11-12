# Codex çalışma yönergesi — KUZUCU ERP

ÖNCE `../../KUZUCU_ERP_PROJE_DEVIR_NOTLARI.md`, `../../GELISTIRME_LISTESI.md`, `MAC_GUNCELLEME_V16.md` ve `SURUM_NOTLARI_V16.md` dosyalarını oku (`../../ARASTIRMA_GLOBAL_PROGRAMLAR.md` sonraki sürümlerin yol haritasıdır). Bu iki üst dizindeki belge bulunmuyorsa kullanıcıdan aktarım paketinin kökündeki devir notları ve geliştirme listesini iste; geçmiş bağlamı uydurma.

- Güncel aşama: ön test ve geliştirme; güncel kaynak pilotu v0.16.0 (12.11.2026); birleşik test/paket durumu kökteki `SURUM_DOGRULAMA.md` belgesinde. Kullanıcı iPad'de **yalnızca Codex'te geliştirmeye devam etmek** istiyor; bu talebi ERP'ye uzaktan erişim veya yayınlama izni sayma. Aynı hesap/sohbet ya da ZIP aktarımıyla devam et; ortam durumunu ayrıca kontrol et.

- Dil: Kullanıcının gördüğü her ekran, hata, uyarı, başarı ve doğrulama mesajı sade ve anlaşılır Türkçe olmalı. Teknik ayrıntılar logda kalmalı.
- Bu dil kuralı işlem geçmişindeki bölüm/alan/durum adlarını, “İncele” ayrıntılarını ve rapor/CSV/PDF çıktılarını da kapsar. Ham teknik kod veya İngilizce tarayıcı/sistem hatası kullanıcıya aktarılmamalı; bilinmeyen değerlerde Türkçe genel açıklama kullanılmalı. Kullanıcının özgün özel ad ve belge metinlerini çeviri amacıyla değiştirme. v0.16 gruplu menü, yeni tema, Ana Sayfa, Cariler, Hayvan Çıkış Raporu, olağandışı giriş onayı, çıkışta yedek ve kolay güncellemeyi içerir; eski talepleri yeniden uygulama. Güncel kapsam ve açık fiziksel kabul kontrolleri üst dizindeki geliştirme listesinde.
- Proje adı KUZUCU ERP; yeşil/altın boğa başlı görsel kimlik korunmalı.
- Kullanıcı yeni özellik istediğinde **kodu değiştirme veya sürüm paketi üretme**. İstekleri backlog dosyasına ekle; yalnızca kullanıcı açıkça **“Son sürümü hazırla”** dediğinde birikmiş değişiklikleri uygula, test et ve sürümle.
- Mevcut `ciftlik.db`, `data/parcel_images`, `data/documents` ve `raporlar` üretim verilerine zarar verme. Önce yedek al, migration'ları geriye dönük uyumlu yaz. ZIP içinde gerçek kullanıcı veritabanı bulunmaz.
- Pilot uygulamayı kullanıcı açıkça istemedikçe internete açma. Kimlik doğrulaması, yetkiler, rapor yetkileri, CSRF, audit ve veri gizliliği sunucuda doğrulanmalı.
- Araç/ilaç önerilerini veteriner onayı gerektiren karar desteği olarak sun, otomatik reçeteleme yapma.
- Miktarlar Türkçe biçimlendirilmeli: 30000 -> 30.000, 12500.5 -> 12.500,5. Görünen nokta ondalık ayırıcı olarak yorumlanmamalı.
- Toplu işlemler atomik yapılmalı, olası hatada hiçbir kısmi kayıt kalmamalı.
- Kod değişikliği öncesinde mevcut testleri çalıştır, yeni davranış için test yaz. Kodda var olduğu varsayılan tüm özellikleri ayrıca doğrula.
- Mac kullanıcısı terminal adımlarında tek tek, kısa ve net Türkçe yönerge ister.

- v0.15 geçişleri eklemelidir: buzağı `group_no`, `purchase_price_tl`, `milk_phase`, tüketimde yeni `milk_litres`, sağlıkta `duration_days`, ajandada `interval_count` ve yeni modül tabloları. Eski mama kg kayıtlarını litreye çevirmiş sayma; bilinmeyen fiyat/grup/süt dönemi bilgilerini doldurma.
- Yeni tedavi planının günlük listede görünmesi gerçek uygulama veya veteriner onayı değildir. Kaldırılan eski alanları düzenlemede sıfırlama; geçmiş günlük kayıtları koru.
- Fatura taslağı stok/cariyi etkilemez; kesinleştirme tek etki üretir. Faturaya bağlı stok hareketini doğrudan değiştirme; ters kayıt ve kaynak ilişkisini koru. Maliyet raporu KDV hariç ağırlıklı alış ortalamasından tahmindir; kapsamlı maliyet dağıtımı değildir.
- Personel izin hakkı kullanıcı tarafından tanımlanır; hukuki hak veya maaş/mesai ücretini tahmin etme. Yerel parola kurtarma aracı yalnız operatörün o bilgisayardaki açık onayı ve doğrulanmış yedekle çalıştırılır; parolayı sohbette isteme.
- Küpe/belge fotoğrafları özel veridir; gerçek görselleri kaynak ZIP veya GitHub'a katma. OCR rakamları kapalıysa tamamlamaz; kullanıcı fotoğrafla karşılaştırıp hedef kaydı doğrular. Tesseract ve dil dosyaları ek kurulumdur. Telefon/Mac bağlantısı kurulmuş sayılmaz.

- v0.16 kuralları: logo (`kuzucu_logo.png`) değiştirilmez. Menü grupları `app/static/v16.js` içindedir; yeni sayfa eklerken `sections` (index.html) + `GROUPS` (v16.js) + `navScopes`/`sectionAllowed` (security-ui.js) birlikte güncellenir.
- Olağandışı değer uyarıları `app/checks.py`: kesin hata 422; onaylanabilir uyarı 409 `{"code":"unusual"}` ve ekranda onay sonrası `?onay=1` ile yinelenir. Sınırlar `LIMITS` sözlüğündedir.
- Tarih/gün hesapları Türkiye saatiyle (`today_local`) yapılır; `date.today()` kullanma.
- Kullanıcı arınma (kesim yasağı) korumasını istemedi; ekleme.
