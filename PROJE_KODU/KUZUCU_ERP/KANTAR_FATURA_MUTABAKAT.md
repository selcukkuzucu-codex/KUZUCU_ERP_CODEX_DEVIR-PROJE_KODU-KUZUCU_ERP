# KZC ERP v0.4 - Kantar, Depo ve Fatura Mutabakatı

## İş kuralı
- **Fiziki stok** yalnızca net kantar fişinin depo kabulüyle artar; e-postayla gelen fatura stok hareketi oluşturmaz.
- Fatura önce de sonra da gelebilir. Her iki kayıt bağımsız açılır, ardından eşleştirilir.
- Eşleştirmede firma vergi kimliği, malzeme ve varsa irsaliye numarası doğrulanır; fark kg ve yüzde olarak hesaplanır.
- Miktar farkında kayıtlar değiştirilmez; `DISCREPANCY` kaydı ve uyarı oluşur.
- Bir kantar kaydından çift depo girişi engellenir. Fatura satırının tekrarlı girilmesi engellenir.
- Birden fazla kantar fişi / tek fatura satırı gibi **çoklu eşleştirme ve kısmi sevkiyat** henüz desteklenmez; canlı kullanım öncesi gereklidir.
- İskonto, nem, fire, tolerans, kalibrasyon ve birim dönüşümü işletmeye özgü kararlaştırılmalıdır.

## API
- `POST /api/receiving/weighings` (brüt, dara, plaka, irsaliye, ürün, firma)
- `POST /api/receiving/weighings/{id}/accept` (depo kabulü; tek stok girişi)
- `POST /api/receiving/invoices` (fatura satırı taslak kaydı; stok girişi yok)
- `POST /api/receiving/compare` (kantara karşı fatura miktarını karşılaştır)
- `GET /api/receiving/alerts` (miktar farkları)
- `GET /api/receiving/pending` (faturası/kantarı henüz eşleşmeyenler)

## Canlıya almadan önce yapılacaklar
- Gerçek kullanıcı hesabı, rol bazlı depo kabul / mutabakat onayı, işlem günlüğü ve idempotent API.
- PostgreSQL ile satır kilidi ve transaction eşzamanlılık garantileri.
- Bir faturanın birden fazla tartımla, tek kantarın birden fazla fatura satırıyla eşleştirilmesi için miktar paylaştırma ve aşırı eşleştirmeye karşı kilitleme.
- Firmaların vergi no üzerinden cari kartlara, ürünlerin kod üzerinden stok kartlarına bağlanması; olmayanların taslak açılması.
- Şirket özel e-posta sunucusu için TLS'li salt-okunur IMAP erişimi; ek güvenliği, PDF/e-fatura UBL/XML çözümleme ve resimler için OCR (gözden geçirme şartıyla).
- Gerçek bildirim kanalı, denetim izi, belge saklama ve mali/muhasebe onayı.
- SAP'ye ileride aktarılmak üzere belge ve fiş özgün kimlikleri saklanmalı.

Bu sürüm çalışan bir yerel API prototipidir. **E-postaları otomatik okumaz**, gerçek kantara bağlanmaz, üretimde kullanılmamalıdır.
