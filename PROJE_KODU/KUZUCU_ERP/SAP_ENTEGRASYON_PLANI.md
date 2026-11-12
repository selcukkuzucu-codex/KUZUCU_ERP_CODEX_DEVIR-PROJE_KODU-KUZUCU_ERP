# KZC ERP — SAP entegrasyon sözleşmesi (taslak)

## Hedef
KZC ERP bağımsız çalışır. SAP ile bağlantı ayrı, devre dışı başlayan adaptör katmanında yapılır. SAP sertifikasyonu veya hazır bağlantı iddiası yoktur.

## SAP sistem tipleri
- **SAP Business One 10:** Service Layer, OData v4; erişim ve yetkiler müşteri sistemi üzerinden doğrulanır.
- **SAP S/4HANA:** Sürüm ve kurulum tipine uygun yayımlanmış OData/SOAP API'leri. API kapsamı SAP Business Accelerator Hub üzerinden nesne bazında doğrulanır.
- İleri aşama: SAP Integration Suite üzerinden ara katman.

## Kanonik veri sözleşmesi
- Ürün/hammadde: `external_system`, `external_id`, `material_code`, `name`, `base_uom`.
- İş ortağı: `external_id`, `name`, `partner_type`.
- Depo hareketi: `reference`, `material_code`, `quantity`, `uom`, `movement_type`, `event_time`, `source_system`.
- Maliyet merkezi: `external_id`, `code`, `description`.
- Finans belgesi: `external_id`, `document_date`, `currency`, `amount`, `cost_center`.

## Koruma ve tutarlılık
1. İlk faz sadece salt-okunur aktarım ve veri eşleştirme.
2. Sonraki fazda yetki onaylı çift yönlü entegrasyon; otomatik SAP belge gönderimi varsayılan kapalı.
3. Kalıcı kaynak kimliği ve idempotency key ile mükerrer belgeyi önleme.
4. Tarih/saat, TL/para birimi, ölçü birimi ve malzeme kodu eşleştirme.
5. İşlem ve hata günlüğü; başarısız istekler için tekrar deneme ve mutabakat.
6. Güvenli gizli anahtar saklama, TLS, en az ayrıcalık, API çağrısı denetimi.

## Açık sorular
Kullanılan SAP ürünü, sürümü, bulut/on-prem tipi, entegrasyon yetkileri, öncelikli modüller, özelleştirilmiş malzeme ve maliyet merkezi kodları.

## Referanslar
- https://help.sap.com/docs/SAP_BUSINESS_ONE/f110a154dd0f4c20bf7f3ebca9eeb794/60c7a0b745bd486589f05a1da77041f3.html
- https://help.sap.com/docs/sap_s4hana_cloud/0f69f8fb28ac4bf48d2b57b9637e81fa/1e60f14bdc224c2c975c8fa8bcfd7f3f.html
