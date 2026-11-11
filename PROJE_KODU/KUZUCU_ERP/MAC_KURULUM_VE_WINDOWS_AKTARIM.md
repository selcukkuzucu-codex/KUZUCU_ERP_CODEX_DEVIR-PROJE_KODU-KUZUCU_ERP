> **Tarihî v0.5 rehberi:** Güncel v0.15 kurulumu için `MAC_GUNCELLEME_V15.md` ve `KURULUM_WINDOWS_TR.md` dosyalarını kullanın. Kullanıcı Windows verilerini Mac'e taşımayı istemedi; aşağıdaki aktarımı kendiliğinden yapmayın. Bu belgedeki eski eksik özellik açıklamaları güncel durumu göstermez.

# KUZUCU ERP — Mac Kurulum ve Windows Veri Tasima

## Dikkat: Pilot test surumu
Bu paket Windows'taki KUZUCU ERP v0.5 kodunu temel alir, Mac icin baslatma ve yedek aktarim araclari ekler. Bulut servisi, hesap sifresi/MFA, HTTPS ve yetkilendirme icermez. Yalnizca guvenilir bilgisayarinizda `127.0.0.1` uzerinde **deneme verileriyle** kullanin. Mac ve Windows ayni anda ortak veritabanina yazmaz; tasima tek seferlik bir kopyadir.

## 1 — Once Windows kayitlarini koruyun
1. Windows'taki KUZUCU ERP'yi normal sekilde durdurun; varsa devam eden kayit islerini bitirin.
2. Windows'ta mevcut KUZUCU_ERP klasorundeki `YEDEK_AL_WINDOWS.bat` dosyasini kullanin (veya yeni paketteki `WINDOWS_VERI_YEDEKLE.bat` dosyasini eski program klasorune kopyalayin). `tools/backup_sqlite.py` ile birlikte calisir.
3. Yedek normalde `C:\Users\<kullanici>\Documents\KUZUCU_ERP_Yedekler\kuzucu_erp_local_YYYYMMDD_HHMMSS.sqlite3` icine yazilir.
4. Program `Yedek:` yazip dosyayi raporlayinca dosyayi USB bellek, AirDrop, veya guvenli dosya transferiyle Mac'e tasiyin. Windows'taki orijinal klasoru ve veritabani dosyasini silmeyin.
5. Windows'ta eski surumde `ciftlik.db` dosyasi uygulama klasorundedir. Eger herhangi bir farkli klasorden calistirdiysaniz bu yedeğin dogru veritabanindan alindigini sayilarla kontrol edin.

## 2 — Mac'te ilk kurulum
1. Zip'i Finder'da cift tiklayip acin; `KUZUCU_ERP` klasorunu Belgeler veya Masaustu'ne tasiyin.
2. https://www.python.org/downloads/macos/ adresinden Python 3.12 yukleyin. Mac Terminal'de `python3 --version` calistirin, 3.11–3.13 surumlerinden biri olmali.
3. Finder'da `BASLAT_MAC.command` dosyasina cift tiklayin; terminal penceresini acik tutun. Ilk calismada internet gerekir.
4. Eger macOS guvenlik engeli cikarsa sadece bu pakete guveniyorsaniz Sistem Ayarlari > Gizlilik ve Guvenlik uzerinden onay verin; Terminal'de `chmod +x BASLAT_MAC.command YEDEK_AL_MAC.command WINDOWS_YEDEGINI_MAC_E_AKTAR.command` ile yetki verebilirsiniz.
5. Safari'de `http://127.0.0.1:8000` acin. Port baska uygulama tarafindan kullaniliyorsa onun durdurulmasi gerekir.

## 3 — Windows yedegini Mac'e tasima (Mac'te yeni kayit girmeden once)
**En guvenli sira:** Windows veritabaninin yedegini Mac'e tasidiktan sonra Mac uygulamasini ilk kez acin. Mac'te ilk acilis yapildiysa bos `ciftlik.db` olusur: araci calistirmadan once Mac'in kendi `YEDEK_AL_MAC.command` araciyla yedekleyin, Mac uygulamasini kapatin, sonra bos veritabanini yeniden adlandirin (`ciftlik_mac_bos.db` gibi). Gercek kayit varsa baska veritabanina gecis yapmadan destek alin; birlestirme otomatik yapilmaz.

1. Finder'da Windows yedegi `.sqlite3` dosyasini bulun.
2. Mac KUZUCU_ERP klasorunden `WINDOWS_YEDEGINI_MAC_E_AKTAR.command` dosyasini calistirin.
3. Yedek dosyasinin tam yolunu girin (Finder'dan surukleyip birakabilirsiniz; yol bosluk iceriyorsa gerekirse tam yolu tirnak icinde yazin).
4. Arac eski dosyayi kontrol eder ve **sadece `ciftlik.db` yoksa** aktarir; uzerine yazmaz.
5. `BASLAT_MAC.command` ile uygulamayi acin. Windows'taki Grup No/padok, hayvan, parsel, stok sayilarini karsilastirin.

## 4 — Mac yedekleme
`YEDEK_AL_MAC.command` uygulama klasorundeki SQLite kaydini macOS Belgeler / `KUZUCU_ERP_Yedekler` klasorune anlik olarak kopyalar ve butunluk testini yapar. Bu **manuel** pilot yedegidir; otomatik zamanlama ve farkli disk kopyasi henuz yoktur.

## Sinirlar
- Windows ve Mac veritabanlari otomatik eslesmez; bundan sonra birini ana deneme ortami secin. Gercek ortak kullanim icin daha sonra merkezi veritabani + kimlik dogrulama/yetkilendirme gerekir.
- Fotoğraf OCR icin Tesseract ayrica Mac'e kurulmalidir; PDF'deki secilebilir metinler icin pypdf kullanilir.
- Yerel program internete veya ofis LAN'ina acik degildir. Yetkisiz erisime karsi bunun degistirilmemesi onerilir.
