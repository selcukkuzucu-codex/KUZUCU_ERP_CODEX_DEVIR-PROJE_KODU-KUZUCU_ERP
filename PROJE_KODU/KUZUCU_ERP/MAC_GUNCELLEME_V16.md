# KUZUCU ERP v0.16.0 — Mac'te güncelleme

12 Kasım 2026. Ön test ve geliştirme sürümü. Bu sürüm veritabanına yeni tablo/sütun eklemez. Kayıtlarınız yerinde kalır.

## Kolay yol (önerilen)

1. Açık KUZUCU ERP'nin Terminal penceresinde **Control + C** yapın ve kapanmasını bekleyin. (Tarayıcıyı kapatmak programı durdurmaz.)
2. `KUZUCU_ERP_v0.16.0.zip` dosyasına çift tıklayın. **İndirilenler** klasöründe açılır. Masaüstündeki eski `KUZUCU_ERP` klasörüne dokunmayın.
3. Açılan klasörde `PROJE_KODU` → `KUZUCU_ERP` içine girin.
4. **GUNCELLE_MAC.command** dosyasına **sağ tıklayın → Aç** deyin. "Geliştiricisi doğrulanamadı" uyarısı çıkarsa yine **Aç**'ı seçin.
   - Çift tıklama çalışmazsa Terminal'e şunu yazıp Enter'a basın (`İndirilenler` farklıysa klasörü Terminal'e sürükleyebilirsiniz):

   ```bash
   bash "$HOME/Downloads/KUZUCU_ERP_v0.16.0/PROJE_KODU/KUZUCU_ERP/GUNCELLE_MAC.command"
   ```

5. Pencere sizden onay ister: **E** yazıp Enter'a basın. Program şunları sırayla yapar:
   - Eski program açıksa durur ve sizden kapatmanızı ister.
   - Masaüstündeki `KUZUCU_ERP` klasörünün **tam yedeğini** `Belgeler/KUZUCU_ERP_Yedekler/surum_oncesi_v0.15.0_...` klasörüne alır.
   - Yalnız program dosyalarını yeniler. `ciftlik.db`, `data` (parsel görselleri, belgeler) ve `raporlar` yerinde kalır.
   - Programı yeni sürümle açar.
6. Tarayıcıda ekranın üstünde **Pilot v0.16** yazdığını görün. Eski görünüm kalırsa **Command + Shift + R** yapın.
7. Aynı kullanıcı adı ve parolanızla giriş yapın.

Masaüstünde `KUZUCU_ERP` klasörü yoksa güncelleme sizden klasörün yerini ister: eski program klasörünü Terminal penceresine sürükleyip Enter'a basın.

## İlk kontroller

- Hayvan, buzağı, parsel, stok ve firma sayılarınız eskisiyle aynı mı?
- **Parseller** listesinde dekarı çok büyük (10 kat) veya çok küçük (1.000 kat) görünen tarla var mı? Varsa **Düzenle** ile doğru sayıyı yazın. Ondalık için virgül kullanın: `12,5`.
- Menüde **Muhasebe → Cariler**: eski firma kartları ve cari bakiyeler burada.
- **Yönetim → Yedekler**: son yedek saatini görün, bir kez **Şimdi Yedek Al** deyin.
- Yeni sayfalar için çalışanlarınıza yetki verin: **Hayvan Çıkış Raporu** için "Rapor / Hayvanlar" veya "Rapor / Buzağı" görme yetkisi; Stok Girişi'ndeki **+ Yeni Stok Ürünü** için "Stok Ürünleri" oluşturma yetkisi.

## Elle yol (kolay yol çalışmazsa)

1. Eski programı Control + C ile kapatın.
2. Masaüstündeki `KUZUCU_ERP` klasörünün **tamamını** ayrı bir yere kopyalayın (yedek).
3. Yeni ZIP'teki `PROJE_KODU/KUZUCU_ERP` içindeki `app`, `tools`, `tests`, `templates` klasörlerini ve üst seviyedeki dosyaları eski klasöre kopyalayıp **değiştirin**. `ciftlik.db`, `data`, `raporlar`, `.venv` klasörlerine dokunmayın.
4. Terminal'de çalıştırın:

   ```bash
   bash "$HOME/Desktop/KUZUCU_ERP/BASLAT_MAC.command"
   ```

## Geri dönüş

Sorun olursa yeni kayıt girmeden önce bize yazın. Kendiniz geri dönmeniz gerekirse: programı kapatın, Masaüstündeki klasörün adını değiştirin (örn. `KUZUCU_ERP_v016`), `Belgeler/KUZUCU_ERP_Yedekler/surum_oncesi_...` klasörünü Masaüstüne `KUZUCU_ERP` adıyla kopyalayın ve `BASLAT_MAC.command` ile açın. **Yeni sürümde kayıt girdiyseniz eski yedeği üstüne yazmayın**; iki kopyayı da koruyun.
