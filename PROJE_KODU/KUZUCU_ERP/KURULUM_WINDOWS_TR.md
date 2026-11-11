# KUZUCU ERP — Windows yerel pilot v0.14.0

Bu yazılım ön test ve geliştirme sürümüdür. Kullanıcı girişi, bölüm/rapor yetkileri, işlem geçmişi ve yerel SQLite yedeği vardır. Bulut sunucu, cihazlar arası veri eşitleme ve üretim güvenliği kurulmuş sayılmaz. Güncel değişiklikler `SURUM_NOTLARI_V14.md` dosyasındadır.

## Açılış (Windows 10/11)

1. ZIP dosyasını indirin, dosyaya sağ tıklayıp **Tümünü Ayıkla** deyin. `PROJE_KODU` içindeki `KUZUCU_ERP` klasörünü ağ sürücüsü yerine örneğin `C:\KUZUCU_ERP` konumuna alın. Eski klasörün üzerine birleştirmeyin; program kapalıyken eski klasörün tamamını yedekleyin ve koruyun.
2. Bilgisayarınızda **Python 3.11 veya 3.12** kurulu değilse https://www.python.org/downloads/windows/ adresinden yükleyin. Kurulumda **Add Python to PATH** kutusunu işaretleyin.
3. Klasörde `BASLAT_WINDOWS.bat` dosyasına çift tıklayın. Python bağımlılıkları `requirements.txt` ve test edilen sürümleri koruyan `requirements.constraints.txt` kullanılarak kurulur. İlk seferde internet gerekir.
4. Tarayıcıda http://127.0.0.1:8000 açılır. Açılmazsa adresi kendiniz yazın. Siyah komut penceresini **kapatmayın**; kapandığında pilot durur.
5. Yeni kurulum boş SQLite veritabanı ile açılır; ilk yönetici hesabınızı oluşturun. Önceki v0.13 DB'sini program kapalıyken yedekleyip taşıdıysanız aynı hesap ve kayıtlar korunur. Parsel görselleri için `data/parcel_images`, raporlar için `raporlar` klasörünü de ayrıca koruyun.

## Yerel veri yedeği (yalnızca pilot SQLite)

`YEDEK_AL_WINDOWS.bat` dosyasına çift tıklayın. Dosya `Belgeler\KUZUCU_ERP_Yedekler` içine SQLite güvenli yedekleme API'si ile kaydedilir; bütünlük kontrolü yapılır.

**Bu işlem bulut yedeği değildir.** Bulut PostgreSQL kurulmadığından şirket verilerinin otomatik sunucu yedeği henüz yapılamaz. Gerçek Windows otomatik bulut yedeği için ayrı güvenli indirilebilir yedek uç noktası, kimlik doğrulama, şifreleme ve Windows Görev Zamanlayıcı kurulumu gerekecektir. Yerel pilotun yedeği sadece bu pilot veritabanıdır.

## Paket kapsamı

- Hayvan, Grup No (arayüzde eski padok ifadesi görülebilir), tartım, parsel, ürün, stok kayıtları
- Kural tabanlı Türkçe rapor sorguları / CSV alma
- DelPro CSV önizleme (gerçek aktarım yapmaz)
- Kantar ve fatura miktar eşleştirme API'si (uygulama ekranları henüz tamamlanmadı)
- SAP mimari planı (SAP bağlantısı yok)

**Tamamlanmamış alanlar:** Yapay zekâ model bağlantısı, personel/izin/bordro, gerçek fatura e-postası alma, maliyet merkezi/işletmeler arası transferler ve bulut PostgreSQL altyapısı. Görsel belge önizlemesinde OCR için bilgisayara Tesseract ve Türkçe dil dosyası ayrıca kurulmalıdır; taranmış PDF için OCR yoktur.

Bu sürümün otomatik testleri Linux/Python 3.12 üzerinde yapıldı; fiziksel Windows kurulumu bu bulut ortamında denenmedi. iPad'de yalnızca Codex'te geliştirmeye devam etmek için paket kökündeki `IPAD_ILE_DEVAM.md` dosyasını izleyin.

## Teknik

Python/FastAPI + SQLAlchemy + SQLite (yerel pilot). Tarayıcı arabirimi: `http://127.0.0.1:8000`; API açıklaması `http://127.0.0.1:8000/docs`.
