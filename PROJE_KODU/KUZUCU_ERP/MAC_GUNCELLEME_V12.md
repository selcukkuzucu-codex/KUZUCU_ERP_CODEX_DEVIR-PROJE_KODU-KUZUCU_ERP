# KUZUCU ERP — Mac v0.12 güncellemesi

**Yeni özellikler:** Sağlık / Tedaviler sayfasında ayrı **Tedavi / Protokol Adı** ve **İlaç / Aşı Adı** alanları eklendi. Yeni ilaç ve tedavi adları her sağlık kaydından sonra **seçim sözlüğüne** otomatik eklenir. Eski sağlık kayıtlarında bulunan ilaç adları da listelenir. Yeni adları **Seçim Listesine Ekle** düğmesiyle elle ekleyebilirsiniz. Aranabilir seçim için ad yazarken çıkan önerileri veya kayıtlı adın üstüne tıklamayı kullanın.

**10 günlük ilaç tekrarı uyarısı:** Aynı hayvanda, ayrı bir sağlık dosyasına bağlı, **gerçekten uygulanmış** ilaç adını yeni dosyaya yazarken ve ilk uygulamayı kaydederken son 10 takvim günündeki önceki uygulamaları kontrol eder. Eşleşme halinde önceki uygulama tarihi ve vaka bilgisiyle uyarır. Aynı dosyanın veteriner planındaki günlük dozları gereksiz tekrarlı vaka sayılmaz. Veteriner onayı ve kullanıcının açık onayı olmadan onaylı ikinci ilaç planı açılmaz/ilk uygulama kaydedilmez. Onaysız dosyalar taslak olarak saklanabilir ancak uygulanamaz.

**Önemli sınırlama:** Karşılaştırma kayıtlardaki **aynı ilaç adına** dayanır; aynı etken maddenin farklı ticari adlarını, kombine ürünleri, farmakolojik etkileşimleri, doz ve kesim/arınma kısıtlarını otomatik algılamaz. Veteriner hekim kararı yerine geçmez. İşletme içinde gerçek hayvan sağlığı uygulamaları için veteriner yetkili protokolü gereklidir.

## Mac üzerinde v0.12'ye geçiş

1. KUZUCU ERP'yi çalıştıran Terminal'de `Control + C` ile programı durdurun.
2. Masaüstündeki eski `KUZUCU_ERP` klasörünün adını `KUZUCU_ERP_ESKI` yapın; **silmeyin**.
3. ZIP arşivinden çıkan yeni `KUZUCU_ERP` klasörünü Masaüstüne taşıyın.
4. Mac'teki kayıtlarınızı korumak isterseniz eski klasörden **`ciftlik.db`** veritabanını yeni klasöre kopyalayın. Bu ZIP'te veritabanı bulunmaz. Parsel görselleri için `data/parcel_images`, eski sağlık PDF çıktıları için `raporlar` klasörünü de ayrıca koruyun.
5. Terminal'de `bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"` çalıştırın.
6. Terminal'de `Mac yerel pilot v0.12` yazdığını doğrulayın. Chrome'da `http://127.0.0.1:8000` adresini açıp **Command + Shift + R** ile sayfayı yenileyin.

**Not:** Bu paket güvenlik/rol/yetki/güçlendirilmiş yedekleme açısından henüz üretim kullanımı için uygun olmayan yerel pilottur. Windows verileri aktarılmıyor. Pilot sürüm internete açık olarak çalıştırılmamalıdır.
