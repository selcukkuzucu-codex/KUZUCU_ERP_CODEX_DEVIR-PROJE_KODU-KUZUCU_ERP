# KUZUCU ERP — Dünyadaki başarılı programlarla karşılaştırma ve öneriler

**Tarih:** 11 Kasım 2026 · **Temel:** KUZUCU ERP v0.15.0 (+ v0.16 listesindeki talepler)
**Durum:** Kullanıcı 11.11.2026'da **A3 hariç tüm önerileri** kabul etti; `GELISTIRME_LISTESI.md` dosyasına taşındı. A3 (arınma koruması) uygulanmayacak. Hiçbiri henüz kodlanmadı.

## 1. İncelenen programlar ve öne çıkan yönleri

| Program | Alan | Öne çıkan yönü |
|---|---|---|
| Turnkey (AMS) | Büyük besi işletmesi (feedlot) | Yem yönetimi; yem fabrikası ve mikser/tartı bağlantısı; yemlik okuma (bunk call) internetsiz veya kâğıtla da girilebiliyor; hayvan sağlığı sistemiyle birleşik |
| Performance Beef, Micro Technologies, CattleXpert | Besi | Padok/parti bazlı günlük iş akışı, dönem sonu kapanış (close-out) raporu, kayıtların denetime dayanıklı olması |
| Folio3 AgTech, Maximix | Besi + yem fabrikası | Rasyon hesaplama, yem hazırlama, hammadde fiyatı ve stoku, yem maliyeti raporları; muhasebe programına bağlantı |
| Herdwatch | Sığır/koyun (İrlanda, İngiltere) | Telefondan hızlı kayıt, ilaç ve arınma süresi takibi, resmî bildirimlere hazır kayıtlar |
| AgriWebb | Büyük hayvancılık işletmesi | Hayvan, padok ve mera kayıtları; sahada mobil kullanım |
| Farmbrite | Karma işletme (tarım + hayvan) | Hayvan, tarla, stok, görev ve satış tek programda |
| Agrivi, FarmERP, Granular | Bitkisel üretim | Tarla bazında plan ve uygulama kaydı; ürün/tarla/dekar başına maliyet; bütçe ile gerçekleşenin karşılaştırılması; hava ve harita |
| DeLaval DelPro (işletmede kullanılıyor) | Süt/sürü | Grup/padok yapısı; tartı, okuyucu ve cihaz verileri |
| Logo, Mikro, Zirve + GİB entegratörleri | Türkiye muhasebe | e-Fatura, e-Arşiv, **e-Müstahsil makbuzu** (çiftçiden alım) |
| TÜRKVET (Bakanlık) | Türkiye hayvan kayıt | Küpe ile hayvan sorgulama, sevk uygunluğu. Aramada çiftlik programlarına açık bir bağlantı (API) **bulunamadı** |

Not: Kaynakların çoğu satıcı tanıtımları ve karşılaştırma siteleri. Rakamsal iddialar (ör. "%15–25 daha az yem israfı") bağımsız olarak doğrulanmış değil.

## 2. KUZUCU ERP'de zaten olanlar (v0.15)

Hayvan kartı, gruplar, buzağı giriş/çıkış ve performansı, toplu hayvan işlemleri ve kesim/ölüm/satış çıkışı, tartım, sağlık/tedavi ve tekrar ilaç uyarısı, parseller ve görselleri, üretim sezonu, stok ve uyarılar, Excel'den stok aktarma, fatura/cari/kasa-banka, maliyet tahmini, personel/izin/mesai, ajanda, rapor asistanı, kullanıcı yetkileri ve işlem geçmişi, belge/fotoğraf okuma.

**Sonuç:** Temel modüller var. Dünyadaki iyi programlardan farkımız, bu verileri **birbirine bağlayıp parti/padok bazında kâr-zarar ve verim** göstermekte ve **sahada (ahırda, tarlada) hızlı kayıt** almakta.

## 3. Öneriler (önem sırasıyla)

### A. En yüksek değer — besi kârlılığı

**A1. Padok / parti bazlı besi takibi ve dönem sonu kapanış raporu**
Bir parti hayvan girişten kesime kadar tek dosyada izlenir:
- giriş baş sayısı ve kilosu, alış bedeli
- tüketilen yem (kg ve TL), ilaç/aşı maliyeti, işçilik/genel gider payı
- ölüm ve hastalık oranı
- ortalama günlük canlı ağırlık artışı (kg/gün)
- **yem dönüşüm oranı** (1 kg canlı ağırlık için kaç kg yem)
- **1 kg canlı ağırlık artışının maliyeti**
- baş başına ve parti toplamında kâr/zarar

Turnkey ve Performance Beef gibi besi programlarının ana raporu budur.

**A2. Rasyon ve günlük yemleme**
- Rasyon (reçete) tanımı: hangi hammaddeden yüzde kaç. Kuru madde ve fiyat girildiğinde rasyonun kg maliyeti otomatik hesaplanır.
- Her padoka günlük verilen yem kaydı ve yemlik okuma (yemlikte kalan yem: boş / az / çok).
- **Mikser yükleme listesi:** "Bugün A padoku için 2.400 kg: 1.200 kg silaj, 600 kg arpa…"
- Verilen yem stoktan otomatik düşer, maliyeti padoka ve partiye yazılır.
- Kendi ürettiğiniz silaj ve arpa, tarımdan besiye **iç transfer** olarak maliyetiyle geçer; çift sayılmaz.

**A3. Sağlıkta arınma (kesim yasağı) koruması**
- Tedavi kaydında ilaç arınma süresi girilir. Süre dolmadan o hayvan **kesim çıkışına eklenemez**; en azından açık uyarı verilir.
- Hastalık ve ölüm oranı raporu (padok, parti, ay). İlaç bazında tedavi sonucu istatistiği; karar veterinerde kalır.

### B. Sahada hızlı kayıt

**B1. Tablet/telefon saha ekranı**
Büyük düğmeli sade ekranlar: küpe okut/yaz → tartım, tedavi, padok değiştir. Herdwatch ve AgriWebb'in gücü budur.
Ön koşul: ERP'ye ofis dışından güvenli bağlantı (C1).

**B2. Tartı ve elektronik küpe okuyucu bağlantısı**
Tartı ve RFID okuyucu cihazlarından (ör. Gallagher, Tru-Test) gelen dosyayı içe aktarma. Hayvanlar küpeyle otomatik eşleşir, sonuç ekranda kontrol edilip kaydedilir.

**B3. DelPro'dan güvenli içe aktarma**
Listede zaten var, öncelik verilmeli.

### C. Altyapı (diğerlerinin ön koşulu)

**C1. Güvenli uzaktan erişim ve çok kullanıcı**
Önce Tailscale gibi özel ağ, ardından PostgreSQL veritabanı ve otomatik dış yedek (NAS/bulut).
iPad'den ve sahadan kullanım bununla mümkün olur.

**C2. Bildirimler**
Ajanda, stok alarmı, arınma bitişi, geciken tedavi için e-posta, SMS veya WhatsApp bildirimi. Program kapalıyken de çalışması sunucu gerektirir.

### D. Tarım

**D1. Tarla işlemleri günlüğü**
Her parsel için ekim, gübreleme, ilaçlama, sulama ve hasat kayıtları tutulur:
- kullanılan girdi stoktan düşer, makine ve işçilik süresi kaydedilir
- **dekar başı maliyet ve verim** hesaplanır; parselin ürün geçmişi (münavebe) görünür

Agrivi ve FarmERP'nin temel özelliği budur.

**D2. Bütçe ve gerçekleşen**
Sezon başında parsel ve ürün bütçesi girilir; sezon içinde gerçekleşenle karşılaştırılır.

**D3. Harita**
Parsel sınırlarını harita üzerinde gösterme. Uydu ve bitki sağlığı görüntüsü daha sonraki bir iştir.

### E. Muhasebe ve Türkiye mevzuatı

**E1. e-Fatura, e-Arşiv ve e-Müstahsil**
Mevcut bir GİB entegratörü üzerinden. Çiftçiden yem, hayvan veya ürün alımında e-Müstahsil önemli. Kontrol edilmemiş otomatik kayıt yapılmaz.

**E2. Muhasebe programına aktarım**
Logo, Mikro, Luca gibi programlara aktarım dosyası. KUZUCU ERP resmî muhasebe yerine geçmez.

**E3. TÜRKVET küpe mutabakatı**
TÜRKVET'ten alınan hayvan listesiyle ERP'deki aktif hayvanların karşılaştırılması: eksik ve fazla küpeler listelenir. Açık bir bağlantı bulunamadığı için dosya ile yapılır.

### F. Kullanım kolaylığı

**F1. Ana Sayfa gösterge kartları**
Aktif baş sayısı, ortalama günlük artış, **yem stoğu kaç gün yeter**, bugün yapılacak tedavi ve işler, arınmadaki hayvanlar, ödenecek ve tahsil edilecekler.

**F2. Görev atama**
Personele iş atanır; tamamlanınca işaretlenir ve ajandaya bağlanır.

**F3. Her listede hızlı arama ve dışa aktarım**
Her listede filtre, Excel/PDF aktarımı ve yazdırma tek tip olur.

## 4. Önerilen sıra

1. **v0.16 (zaten listede):** menü, Ana Sayfa, stoktan ürün ekleme, çıkış raporu, cari birleştirme, parsel düzeltmeleri. F1 gösterge kartları Ana Sayfa değişikliğiyle birlikte yapılabilir.
2. **v0.17:** A2 rasyon ve yemleme, A3 arınma koruması.
3. **v0.18:** A1 parti kapanış raporu (A2'nin yem verisine dayanır), D1 tarla işlemleri günlüğü.
4. **Altyapı çalışması:** C1 uzaktan erişim ve veritabanı. Ardından B1 saha ekranı ve C2 bildirimler.
5. **Sonra:** B2 ve B3 cihaz/DelPro aktarımı, E1 ve E2 muhasebe bağlantıları, D2 ve D3, E3.

## Kaynaklar
- [Turnkey AMS — yem yönetimi](https://turnkeynet.com/software-applications/ams)
- [Turnkey AMS ürün belgesi (PDF)](https://turnkeynet.com/getmedia/c8b6c774-0e9b-42e3-9b3b-b47e942054e3/22AH322503_AMS.pdf)
- [Feedlot yazılımları 2026 listesi (Gitnux)](https://gitnux.org/best/feedlot-management-software/)
- [Folio3 — besi yazılımı ve yemleme](https://agtech.folio3.com/feedlot-management-software/cattle-feeding-software/)
- [Folio3 — hayvancılık yazılımı özellikleri](https://agtech.folio3.com/blogs/livestock-management-software-features/)
- [Herdwatch / AgriWebb / Farmbrite karşılaştırmaları (Toolradar)](https://toolradar.com/compare/agriwebb-vs-herdwatch)
- [FarmKeep — hayvancılık yazılımları rehberi](https://www.farmkeep.com/farm-guides/farm-management/best-livestock-management-software)
- [Agrivi 360 Farm Enterprise](https://agrivi.com/products/360-farm-enterprise)
- [Tarım ERP karşılaştırması (CFO Club)](https://thecfoclub.com/tools/best-agriculture-erp/)
- [e-Müstahsil makbuzu (Sovos)](https://sovos.com/tr/kdv/urunler/e-mustahsil-makbuzu/)
- [TÜRKVET uygulaması (App Store)](https://apps.apple.com/us/app/id1518222310)
