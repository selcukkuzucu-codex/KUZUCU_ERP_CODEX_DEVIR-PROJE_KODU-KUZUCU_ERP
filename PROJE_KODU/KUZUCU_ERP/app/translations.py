"""Kullanıcıya gösterilen denetim alanları için ortak Türkçe sözlük."""
import json
from datetime import datetime

TABLE_LABELS = {
 'pens':'Gruplar','animals':'Hayvanlar','weighings':'Hayvan Tartımları','fields':'Parseller',
 'crop_seasons':'Üretim Sezonları','items':'Stok Ürünleri','firms':'Firmalar',
 'stock_movements':'Stok Hareketleri','stock_movement_revisions':'Stok Düzeltmeleri',
 'reminders':'Hatırlatmalar','health_cases':'Sağlık Kayıtları',
 'health_catalog_entries':'İlaç ve Tedavi Listeleri','health_daily_logs':'Günlük Sağlık Uygulamaları',
 'health_print_settings':'Sağlık Çıktı Ayarları','health_print_runs':'Günlük Sağlık Çıktıları',
 'calves':'Buzağılar','calf_consumptions':'Buzağı Tüketimleri','calf_weighings':'Geçmiş Buzağı Tartımları',
 'erp_users':'Kullanıcılar','erp_login_sessions':'Kullanıcı Oturumları',
 'erp_audit_events':'İşlem Geçmişi','erp_form_drafts':'Form Taslakları',
 'personnel_employees':'Personel Kartları','personnel_overtime':'Personel Mesaileri',
 'personnel_leaves':'Personel İzinleri','personnel_allowances':'Yıllık İzin Hakları',
 'animal_exits':'Hayvan Çıkışları','animal_group_transfers':'Hayvan Grup Değişiklikleri',
 'captured_documents':'Yüklenen Belgeler','document_firm_links':'Firma Belgeleri',
 'document_weighing_runs':'Belgeden Tartım Aktarımları',
 'finance_item_settings':'Stok Alarm Ayarları','finance_stock_alerts':'Stok Uyarıları',
 'finance_invoices':'Faturalar','finance_invoice_lines':'Fatura Satırları',
 'finance_accounts':'Hesap Kartları','finance_ledger_entries':'Hesap Hareketleri',
 'finance_payments':'Ödeme ve Tahsilatlar','finance_import_runs':'Excel Aktarımları',
 'goods_receipts':'Depo Kabulleri','purchase_invoice_lines':'Kantar Fatura Satırları',
 'receipt_invoice_matches':'Kantar Fatura Eşleştirmeleri',
}
FIELD_LABELS = {
 'id':'Kayıt numarası','name':'Ad','code':'Kod','username':'Kullanıcı adı',
 'display_name':'Ad soyad','department':'Bölüm','is_admin':'Yönetici yetkisi',
 'is_active':'Aktiflik','permissions_json':'Yetkiler','created_at':'Oluşturulma zamanı',
 'updated_at':'Güncellenme zamanı','ear_tag':'TR küpe numarası','tr_ear_tag':'TR küpe numarası',
 'farm_ear_tag':'İşletme küpe numarası','tr_ear_tags':'TR küpe numaraları','farm_ear_tags':'İşletme küpe numaraları',
 'sex':'Cinsiyet','breed':'Irk','pen_id':'Grup','group_no':'Grup No','group_no_snapshot':'İşlemdeki Grup No',
 'capacity':'Grup kapasitesi','birth_date':'Doğum tarihi','arrival_date':'Giriş tarihi',
 'entry_date':'Giriş tarihi','entry_weight_kg':'Giriş ağırlığı (kg)','entry_kg':'Giriş ağırlığı (kg)',
 'exit_date':'Çıkış tarihi','exit_kg':'Çıkış ağırlığı (kg)','exit_group_no':'Eski toplu çıkış numarası',
 'exit_group_snapshot':'Çıkıştaki Grup No','status':'Durum','animal_id':'Hayvan','calf_id':'Buzağı',
 'calf_ids':'Seçilen buzağılar','batch_code':'Alım grubu','planned_days':'Planlanan büyütme günü',
 'purchase_price_tl':'Hayvan başı alış fiyatı (TL)','milk_phase':'Süt içen buzağı',
 'milk_kg':'Eski süt / mama miktarı (kg)','milk_litres':'Mama miktarı (litre)','feed_kg':'Yem miktarı (kg)',
 'consumed_on':'Tüketim tarihi','measured_at':'Tartım tarihi','measured_on':'Tartım tarihi','weight_kg':'Ağırlık (kg)',
 'ada_no':'Ada No','area_decare':'Alan (dekar)','satellite_image':'Arazi görseli','field_id':'Parsel',
 'year':'Yıl','crop':'Ürün','item_id':'Stok ürünü','unit':'Birim','type':'Hareket türü',
 'quantity':'Miktar','movement_date':'Hareket tarihi','reference':'Belge / açıklama','reason':'İşlem nedeni',
 'title':'Başlık','notes':'Açıklama','category':'Bölüm','frequency':'Tekrar birimi','interval_count':'Tekrar aralığı',
 'start_date':'Başlangıç tarihi','remind_time':'Hatırlatma saati','next_due_at':'Sıradaki hatırlatma',
 'last_completed_at':'Son tamamlanma zamanı','record_type':'Sağlık işlemi','condition_name':'Hastalık / durum',
 'symptoms':'Eski belirtiler','product_name':'İlaç / aşı adı','treatment_name':'Tedavi adı',
 'duration_days':'Tedavi süresi (gün)','dosage_text':'Doz / uygulama','veterinarian':'Eski veteriner bilgisi',
 'vet_approved':'Geçmiş veteriner onayı','applications_per_day':'Günlük uygulama sayısı',
 'planned_end_date':'Planlanan bitiş','withdrawal_end_date':'Geçmiş arınma tarihi',
 'repeat_review_confirmed':'Tekrar uygulama kontrolü','performed_on':'Uygulama tarihi',
 'performed_by':'Uygulayan kişi','observation':'Gözlem','response':'Uygulama sonucu',
 'outcome':'Sonuç','outcome_notes':'Sonuç açıklaması','closed_date':'Kapanış tarihi',
 'daily_time':'Günlük çıktı saati','auto_generate':'Otomatik liste oluşturma','auto_print':'Otomatik yazdırma',
 'printer_name':'Yazıcı adı','report_date':'Çıktı tarihi','generated_at':'Oluşturulma zamanı',
 'printed_at':'Yazdırılma zamanı','print_error':'Yazdırma durumu','pdf_path':'Sağlık çıktı dosyası',
 'kind':'Kayıt türü','tax_no':'Vergi numarası','phone':'Telefon','address':'Adres','firm_id':'Firma',
 'invoice_no':'Fatura numarası','invoice_date':'Fatura tarihi','unit_price':'KDV hariç birim fiyat',
 'vat_rate':'KDV oranı','subtotal':'Ara toplam','vat_total':'KDV toplamı','grand_total':'Genel toplam',
 'total':'Toplam','amount':'Tutar','balance':'Bakiye','currency':'Para birimi','account_id':'Hesap',
 'opening_balance':'Açılış bakiyesi','alarm_threshold':'Stok alarm seviyesi','acknowledged_at':'Onay zamanı',
 'employee_id':'Personel','employee_no':'Personel numarası','full_name':'Ad soyad',
 'end_date':'Bitiş / işten ayrılma tarihi','worked_on':'Mesai tarihi','hours':'Mesai saati',
 'starts_on':'İzin başlangıcı','ends_on':'İzin bitişi','days':'Gün sayısı','leave_kind':'İzin türü',
 'destination':'Gittiği yer','transferred_on':'Grup değişikliği tarihi','source_document':'Kaynak belge',
 'source_key':'Belge doğrulaması','source_hash':'Belge doğrulaması',
 'supplier_tax_id':'Tedarikçi vergi numarası','weigh_ticket_no':'Kantar fişi numarası',
 'delivery_note_no':'İrsaliye numarası','vehicle_plate':'Araç plakası','gross_kg':'Brüt ağırlık (kg)',
 'tare_kg':'Dara ağırlığı (kg)','net_kg':'Net ağırlık (kg)','quantity_kg':'Miktar (kg)',
 'line_no':'Satır numarası','receipt_id':'Depo kabul kaydı','invoice_line_id':'Fatura satırı',
 'difference_kg':'Miktar farkı (kg)','note':'Açıklama','movement_id':'Stok hareketi',
 'changed_at':'Düzenlenme zamanı','old_pen_id':'Önceki Grup No','new_pen_id':'Yeni Grup No',
 'invoice_id':'Fatura kaydı','revision':'Düzenleme sırası','linked_movement_id':'Bağlı stok hareketi',
 'posted_movement_id':'İşlenen stok hareketi','direction':'Hesap işlem türü','signed_amount':'Cari tutarı (TL)',
 'cash_amount':'Hesap tutarı (TL)','threshold':'Alarm seviyesi','balance_at_creation':'Uyarıdaki bakiye',
 'acknowledged_by':'Onaylayan kullanıcı','row_count':'Satır sayısı','low_active':'Düşük stok durumu',
 'original_name':'Belge adı','suffix':'Dosya biçimi','owner_id':'Belgeyi ekleyen kullanıcı',
 'document_id':'Belge kaydı','case_id':'Sağlık kaydı','application_no':'Uygulama sırası',
 'last_completed_date':'Son tamamlanma tarihi',
}
for _key in ('item_id','type','quantity','movement_date','reference'):
    FIELD_LABELS['old_'+_key]='Önceki '+FIELD_LABELS[_key].lower()
    FIELD_LABELS['new_'+_key]='Yeni '+FIELD_LABELS[_key].lower()
VALUE_LABELS = {
 'male':'Erkek','female':'Dişi','active':'Aktif','exited':'Çıkışı yapıldı','closed':'Kapalı','open':'Açık',
 'draft':'Taslak','posted':'Kesinleştirildi','cancelled':'İptal edildi','IN':'Giriş','OUT':'Çıkış',
 'once':'Tek sefer','daily':'Gün','weekly':'Hafta','monthly':'Ay','treatment':'Tedavi','vaccination':'Aşı',
 'observation':'Gözlem','medication':'İlaç','improved':'İyileşti','unchanged':'Değişmedi',
 'worsened':'Kötüleşti','recovered':'İyileşti','ongoing':'Devam ediyor','unknown':'Belirtilmedi',
 'slaughter':'Kesim','death':'Ölüm','sale':'Satış','annual':'Yıllık izin','raw_material':'Hammadde',
 'rawmaterial':'Hammadde','medicine':'İlaç','other':'Diğer','purchase':'Alış','payment':'Ödeme',
 'receipt':'Tahsilat','collection':'Tahsilat','TRY':'TL','TL':'TL','kg':'kg','lt':'litre','l':'litre',
 'pcs':'adet','piece':'adet','ton':'ton','adet':'adet','success':'Başarılı','failed':'Başarısız',
 'cash':'Kasa','bank':'Banka','reversal':'Fatura ters kaydı','not_evaluated':'Değerlendirilmedi',
 'no_change':'Değişmedi','completed':'Tamamlandı','due':'Zamanı geldi','upcoming':'Yaklaşıyor',
}
ACTION_LABELS = {'EKLE':'Ekleme','DUZENLE':'Düzenleme','SIL':'Silme'}
HIDDEN_FIELDS={'password','new_password','password_hash','token_hash','csrf_token','data_json',
               'source_key','source_hash','invoice_key','content_hash','name_key','weighing_ids'}

def display_value(field,value,modules=None):
    field=field[4:] if field.startswith(('old_','new_')) and field[4:] in FIELD_LABELS else field
    if value is None or value=='':return 'Belirtilmedi'
    if isinstance(value,bool):return 'Evet' if value else 'Hayır'
    if field not in FIELD_LABELS:return 'Kayıt bilgisi'
    if field in {'source_key','source_hash','source_document'}:return 'Kaynak belgeyle ilişkilendirildi'
    if field in {'satellite_image','pdf_path'}:return 'Kayıtlı dosya'
    if field=='permissions_json':
        try:
            permissions=json.loads(value) if isinstance(value,str) else value
            ops={'view':'Görüntüleme','create':'Oluşturma','edit':'Düzenleme','delete':'Silme','export':'Dışa aktarma'}
            labels=[]
            for permission in permissions:
                module,_,operation=permission.rpartition('.')
                labels.append(f'{(modules or {}).get(module,"Diğer bölüm")} / {ops.get(operation,"Diğer yetki")}')
            return ', '.join(labels) or 'Yetki verilmedi'
        except (TypeError,ValueError,AttributeError):return 'Yetki bilgisi'
    if isinstance(value,(dict,list)):return 'Kayıt bilgileri'
    if field=='print_error':return 'Yazdırma tamamlanamadı; yazıcı ayarlarını kontrol edin.'
    if field.endswith(('_at','_on','_date')) or field in {'birth_date','arrival_date'}:
        try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).strftime('%d.%m.%Y %H:%M' if 'T' in str(value) or ' ' in str(value) else '%d.%m.%Y')
        except ValueError:pass
    if isinstance(value,str) and value in VALUE_LABELS:return VALUE_LABELS[value]
    if field in {'status','sex','frequency','record_type','type','outcome','response','kind','leave_kind','direction'}:
        return 'Diğer durum'
    if field in {'quantity','area_decare','weight_kg','exit_kg','entry_kg','entry_weight_kg','milk_kg','milk_litres','feed_kg',
                 'purchase_price_tl','unit_price','vat_rate','subtotal','vat_total','total','grand_total','amount',
                 'balance','opening_balance','alarm_threshold','hours','quantity_kg','net_kg','gross_kg','tare_kg',
                 'difference_kg','signed_amount','cash_amount','threshold','balance_at_creation'}:
        try:
            from decimal import Decimal
            number=Decimal(str(value))
            if number.is_finite():return f'{number:,.3f}'.rstrip('0').rstrip('.').replace(',','_').replace('.',',').replace('_','.')
        except (ValueError,ArithmeticError):pass
    return str(value)

def describe_changes(changes,modules=None):
    output=[]
    for key,value in changes.items():
        if key in HIDDEN_FIELDS:continue
        old,new=(value.get('once'),value.get('new',value.get('yeni'))) if isinstance(value,dict) and ('once' in value or 'new' in value or 'yeni' in value) else (None,value)
        output.append({'field':FIELD_LABELS.get(key,'Diğer bilgi'),
                       'before':display_value(key,old,modules),'after':display_value(key,new,modules)})
    return output
