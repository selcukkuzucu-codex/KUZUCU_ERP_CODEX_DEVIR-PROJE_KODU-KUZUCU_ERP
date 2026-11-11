"""Yetkiye bağlı, salt okunur Türkçe raporlar; serbest SQL çalıştırılmaz."""
import csv
import io
import re
import unicodedata
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import Animal, Pen, Field as LandField, Item, StockMovement, Weighing
from .security import allowed, current_user, need

router=APIRouter(prefix='/api/reports', tags=['Raporlar'])
class ReportRequest(BaseModel):
    query: str = Field(min_length=2,max_length=500)
    date_from: date | None = None
    date_to: date | None = None
    item_id: int | None = Field(default=None,gt=0)
    firm_id: int | None = Field(default=None,gt=0)
    employee_id: int | None = Field(default=None,gt=0)
    status: str = Field(default='',max_length=30)
    year: int | None = Field(default=None,ge=2000,le=2200)
    search: str = Field(default='',max_length=120)

def norm(s):
    s=str(s or '').lower().replace('ı','i')
    return ''.join(ch for ch in unicodedata.normalize('NFKD',s) if not unicodedata.combining(ch))

def tr_number(value):
    if value is None:return 'Bilinmiyor'
    number=Decimal(str(value))
    text=format(number,',.4f').rstrip('0').rstrip('.')
    return text.translate(str.maketrans(',.','.,'))

def display_unit(value):
    return {'kg':'kg','ton':'ton','adet':'adet','lt':'litre','l':'litre','litre':'litre','pcs':'adet'}.get(str(value or '').lower(),'Özel birim')

def tr_date(value):
    if not value:return '—'
    if isinstance(value,str):value=date.fromisoformat(value[:10])
    return value.strftime('%d.%m.%Y')

def selected_kind(query):
    q=norm(query)
    if any(x in q for x in ('personel','mesai','izin','ise giris','ise basla','isten ayril','isten cik')):return 'personnel'
    if any(x in q for x in ('fatura','kdv')):return 'invoices'
    if any(x in q for x in ('hayvan','besi','kupe','sigir')) and any(x in q for x in ('cikis','kesim','olum','satis')):return 'exits'
    if 'maliyet' in q:return 'costs'
    if any(x in q for x in ('cari','bakiye','borc','alacak','banka','kasa','hesap hareket','tahsilat','odeme')) and not any(x in q for x in ('stok','depo')):return 'accounts'
    if any(x in q for x in ('tum','butun','hepsi','genel','ozet')) and any(x in q for x in ('isletme','durum','rapor')):return 'summary'
    if any(x in q for x in ('stok','depo','hammadde','arpa','misir','silaj','yem')):return 'stock'
    if any(x in q for x in ('tarla','parsel','dekar','arazi')):return 'fields'
    if any(x in q for x in ('tartim','kilo','agirlik')):return 'weighings'
    if any(x in q for x in ('hayvan','besi','kupe','padok','grup','sigir')):return 'animals'
    raise HTTPException(422,'Bu isteği henüz rapora dönüştüremiyorum. Örnekler: aktif hayvanları listele, stok durumunu göster, faturaları listele, cari bakiyeler, maliyetler, personel mesaileri, hayvan çıkışları.')

SCOPES={'summary':'reports.summary','stock':'reports.stock','fields':'reports.fields',
        'weighings':'reports.weighings','animals':'reports.animals','exits':'reports.animals',
        'invoices':'reports.finance','accounts':'reports.finance','costs':'reports.cost','personnel':'reports.payroll'}

def authorize_report(request,kind,export=False):
    scope=SCOPES[kind]
    need(request,scope+'.view')
    if export:need(request,scope+'.export')
    if kind=='invoices':need(request,'muhasebe.fatura.view')
    if kind=='accounts':need(request,'hesap.cari.view')
    return scope

def report_scope(result):
    return result['scope']

def evaluate(req,db,request):
    if isinstance(req,str):req=ReportRequest(query=req)
    kind=selected_kind(req.query)
    scope=authorize_report(request,kind)
    if req.date_from and req.date_to and req.date_from>req.date_to:
        raise HTTPException(422,'Başlangıç tarihi bitiş tarihinden sonra olamaz.')
    q=norm(req.query)
    search=norm(req.search)
    result={'scope':scope}
    if kind=='personnel':
        from .personnel import report_data
        subkind=('overtime' if 'mesai' in q else 'leaves' if 'izin' in q else 'employment' if any(x in q for x in ('ise giris','ise basla','isten ayril','isten cik','giris cikis')) else 'summary' if 'ozet' in q else 'employees')
        result=report_data(db,req.employee_id,req.status,req.date_from,req.date_to,subkind,req.year)
        if subkind=='leaves' and ('haftalik' in q or 'yillik' in q):
            leave_label='Haftalık izin' if 'haftalik' in q and 'yillik' not in q else 'Yıllık izin' if 'yillik' in q and 'haftalik' not in q else None
            if leave_label:result['rows']=[r for r in result['rows'] if r[2]==leave_label]
        if search:result['rows']=[r for r in result['rows'] if search in norm(' '.join(str(x) for x in r[:3]))]
    elif kind=='invoices':
        from .finance import invoices
        invkind='purchase' if 'alis' in q else 'sale' if 'satis' in q else ''
        data=invoices(request,search='',kind=invkind,firm_id=req.firm_id,date_from=req.date_from,date_to=req.date_to,db=db)
        if req.status and req.status not in ('draft','posted','cancelled'):raise HTTPException(422,'Geçerli fatura durumunu seçin.')
        if req.status:data=[r for r in data if r['status']==req.status]
        labels={'draft':'Taslak','posted':'Onaylandı','cancelled':'İptal'}
        rows=[]
        for invoice in data:
            text=' '.join([invoice['invoice_no'],invoice['firm_name'],*[l['item_name'] for l in invoice['lines']]])
            if search and search not in norm(text):continue
            lines=[l for l in invoice['lines'] if not req.item_id or l['item_id']==req.item_id]
            for line in lines:
                rows.append([tr_date(invoice['invoice_date']),'Alış' if invoice['kind']=='purchase' else 'Satış',invoice['invoice_no'],invoice['firm_name'],labels.get(invoice['status'],'Diğer durum'),line['item_name'],tr_number(line['quantity']),display_unit(line['unit']),tr_number(line['unit_price']),tr_number(line['vat_rate']),tr_number(line['subtotal']),tr_number(line['vat_total']),tr_number(line['total'])])
        result|={'title':'Fatura Satırları','columns':['Tarih','Tür','Fatura No','Firma','Durum','Ürün','Miktar','Birim','KDV Hariç Birim Fiyat (TL)','KDV Oranı (%)','Ara Toplam (TL)','KDV (TL)','Genel Toplam (TL)'],'rows':rows,
                 'notice':'Tutarlar her ürün satırına aittir. Yalnızca onaylı faturalar stok ve cari hesaplara işlenir.'}
    elif kind=='accounts':
        from .finance import accounts
        data=accounts(request,firm_id=req.firm_id,date_from=req.date_from,date_to=req.date_to,db=db)
        if any(x in q for x in ('hareket','odeme','tahsilat')):
            labels={'purchase':'Alış faturası','sale':'Satış faturası','payment':'Ödeme','collection':'Tahsilat','reversal':'Fatura ters kaydı'}
            rows=[[tr_date(e['date']),e['firm_name'],e['account_name'],labels.get(e['direction'],'Diğer işlem'),tr_number(e['signed_amount']),e['note']] for e in data['entries']]
            result|={'title':'Cari Hesap Hareketleri','columns':['Tarih','Firma','Hesap','İşlem','Net Tutar (TL)','Açıklama'],'rows':rows}
        elif any(x in q for x in ('banka','kasa')):
            from .finance import Account, LedgerEntry
            entries=list(db.scalars(select(LedgerEntry)))
            if req.date_to:entries=[e for e in entries if e.entry_date<=req.date_to]
            bank_only='banka' in q and 'kasa' not in q
            cash_only='kasa' in q and 'banka' not in q
            rows=[]
            for account in db.scalars(select(Account).order_by(Account.name)):
                if bank_only and account.kind!='bank':continue
                if cash_only and account.kind!='cash':continue
                net=account.opening_balance+sum((e.cash_amount for e in entries if e.account_id==account.id),Decimal(0))
                rows.append([account.name,{'bank':'Banka','cash':'Kasa'}.get(account.kind,'Diğer hesap'),tr_number(account.opening_balance),tr_number(net)])
            result|={'title':'Banka ve Kasa Bakiyeleri','columns':['Hesap','Tür','Açılış Bakiyesi (TL)','Bakiye (TL)'],'rows':rows,
                     'notice':'Bakiyeler kullanıcı tarafından girilen açılış tutarı ve seçilen bitiş tarihine kadar hareketlerle hesaplanır; başlangıç tarihi bakiyeden düşülmez.'}
        else:
            # Balances are through the chosen end date. Start date affects movements, not opening balances.
            from .finance import LedgerEntry
            entries=list(db.scalars(select(LedgerEntry)))
            if req.date_to:entries=[e for e in entries if e.entry_date<=req.date_to]
            rows=[]
            for firm in data['firms']:
                net=sum((e.signed_amount for e in entries if e.firm_id==firm['id']),Decimal(0))
                rows.append([firm['name'],tr_number(max(net,Decimal(0))),tr_number(max(-net,Decimal(0))),tr_number(net)])
            result|={'title':'Cari Bakiyeler','columns':['Firma','Alacağımız (TL)','Borcumuz (TL)','Net Bakiye (TL)'],'rows':rows,
                     'notice':'Bakiyeler seçilen bitiş tarihine kadar tüm hareketleri kapsar; başlangıç tarihi bakiyeden düşülmez. Artı bakiye alacağımızı, eksi bakiye borcumuzu gösterir.'}
        if search:result['rows']=[r for r in result['rows'] if search in norm(' '.join(str(x) for x in r))]
    elif kind=='costs':
        from .finance import costs
        if req.date_from or req.date_to or req.firm_id:
            # A purchase-period report has no invented current-stock valuation.
            from .finance import Invoice, InvoiceLine
            query=select(InvoiceLine,Invoice).join(Invoice,Invoice.id==InvoiceLine.invoice_id).where(Invoice.status=='posted',Invoice.kind=='purchase',InvoiceLine.revision==Invoice.revision)
            if req.date_from:query=query.where(Invoice.invoice_date>=req.date_from)
            if req.date_to:query=query.where(Invoice.invoice_date<=req.date_to)
            if req.firm_id:query=query.where(Invoice.firm_id==req.firm_id)
            pairs=db.execute(query).all();rows=[]
            for item in db.scalars(select(Item).order_by(Item.code)):
                if req.item_id and item.id!=req.item_id:continue
                if search and search not in norm(item.name+' '+item.code):continue
                lines=[l for l,i in pairs if l.item_id==item.id]
                if not lines:continue
                qty=sum((l.quantity for l in lines),Decimal(0));net=sum((l.subtotal for l in lines),Decimal(0))
                rows.append([item.code,item.name,display_unit(item.unit),tr_number(qty),tr_number(net),tr_number(net/qty) if qty else 'Bilinmiyor'])
            result|={'title':'Dönemsel Alış Maliyetleri','columns':['Kod','Ürün','Birim','Alış Miktarı','KDV Hariç Alış (TL)','Ortalama Birim Fiyat (TL)'],'rows':rows,
                     'notice':'Seçilen tarih/firma kapsamındaki onaylı alış faturaları kullanılır. KDV hariç miktar ağırlıklı ortalamadır; güncel stok değerlemesi değildir.'}
        else:
            data=costs(request,db=db)
            rows=[r for r in data['rows'] if (not req.item_id or r['item_id']==req.item_id) and (not search or search in norm(r['name']))]
            result|={'title':'Maliyet Raporu','columns':['Ürün','Birim','Faturalı Alış Miktarı','KDV Hariç Alış (TL)','Ortalama Birim Fiyat (TL)','Stok','Fiyatı Bilinmeyen Giriş','Tahmini Stok Maliyeti (TL)'],
                     'rows':[[r['name'],display_unit(r['unit']),*[tr_number(r[k]) for k in ('purchased_quantity','purchase_net','average_net_price','stock_balance','unpriced_incoming','estimated_stock_cost')]] for r in rows], 'notice':data['method']}
    elif kind=='exits':
        from .animal_operations import exit_rows
        reason='slaughter' if 'kesim' in q else 'death' if 'olum' in q else 'sale' if 'satis' in q else None
        data=exit_rows(db,req.date_from,req.date_to,reason)
        result|={'title':'Hayvan Çıkışları','columns':['Tarih','TR Küpe No','İşletme Küpe No','Grup No','Çıkış Nedeni','Nereye Gittiği','Çıkış kg'],
                 'rows':[[tr_date(r['exit_date']),r['tr_ear_tag'],r['farm_ear_tag'] or '—',r['group_no'],r['reason_label'],r['destination'],tr_number(r['exit_kg'])] for r in data if not search or search in norm(' '.join(str(x) for x in r.values()))]}
    elif kind=='summary':
        user=current_user(request);rows=[]
        if allowed(user,'reports.animals.view'):
            rows.append(['Aktif hayvan',sum(a.status=='active' for a in db.scalars(select(Animal)))])
            rows.append(['Grup sayısı',len(list(db.scalars(select(Pen))))])
        if allowed(user,'reports.fields.view'):rows.append(['Parsel sayısı',len(list(db.scalars(select(LandField))))])
        result|={'title':'İşletme özeti','columns':['Gösterge','Değer'],'rows':rows,
                 'notice':'Özet yalnızca ilgili raporu görme yetkiniz olan göstergeleri içerir.'}
    elif kind=='stock':
        items=list(db.scalars(select(Item).order_by(Item.code)));mvs=list(db.scalars(select(StockMovement)));rows=[]
        dated=bool(req.date_from or req.date_to)
        for item in items:
            if req.item_id and item.id!=req.item_id:continue
            if search and search not in norm(item.name+' '+item.code):continue
            if any(x in q for x in ('arpa','misir','silaj')) and not any(x in norm(item.name) for x in ('arpa','misir','silaj') if x in q):continue
            movements=[m for m in mvs if m.item_id==item.id and (not req.date_from or (m.movement_date and m.movement_date>=req.date_from)) and (not req.date_to or (m.movement_date and m.movement_date<=req.date_to))]
            incoming=sum((m.quantity for m in movements if m.type=='IN'),Decimal(0));outgoing=sum((m.quantity for m in movements if m.type=='OUT'),Decimal(0))
            rows.append([item.code,item.name,*([tr_number(incoming),tr_number(outgoing)] if dated else []),tr_number(incoming-outgoing),display_unit(item.unit)])
        result|={'title':'Stok durumu','columns':['Kod','Ürün',*(['Dönem Giriş','Dönem Çıkış'] if dated else []),'Dönem Net Değişim' if dated else 'Bakiye','Birim'],'rows':rows}
        if dated:result['notice']='Tarih seçildiği için miktarlar seçili dönemdeki hareketleri gösterir; net değişim güncel stok bakiyesi değildir.'
    elif kind=='fields':
        rows=[[f.ada_no or '',f.code,f.name,tr_number(f.area_decare)] for f in db.scalars(select(LandField).order_by(LandField.code)) if not search or search in norm(' '.join([f.ada_no or '',f.code,f.name]))]
        result|={'title':'Parsel listesi','columns':['Ada No','Parsel Kodu','Parsel','Dekar'],'rows':rows}
    elif kind=='weighings':
        animals={a.id:a for a in db.scalars(select(Animal))};query=select(Weighing).order_by(Weighing.measured_at.desc(),Weighing.id.desc());rows=[]
        if req.date_from:query=query.where(Weighing.measured_at>=req.date_from)
        if req.date_to:query=query.where(Weighing.measured_at<=req.date_to)
        for w in db.scalars(query):
            a=animals.get(w.animal_id)
            if a and (not search or search in norm(a.ear_tag+' '+(a.farm_ear_tag or ''))):rows.append([a.ear_tag,a.farm_ear_tag or '—',tr_date(w.measured_at),tr_number(w.weight_kg)])
            if len(rows)>=500:break
        result|={'title':'Son tartımlar (en fazla 500)','columns':['TR Küpe No','İşletme Küpe No','Tarih','Ağırlık kg'],'rows':rows}
    elif kind=='animals':
        pens={p.id:p.code for p in db.scalars(select(Pen))};rows=[]
        matched=re.search(r'\b(?:padok|grup)(?:\s+no)?\s+([a-z0-9]+(?:[- ]\d+)?)\b',q)
        mentioned=[code for code in pens.values() if re.search(r'(?<![a-z0-9])'+re.escape(norm(code))+r'(?![a-z0-9])',q)] if any(x in q for x in ('padok','grup','grub')) else []
        filter_pen=mentioned[0] if len(mentioned)==1 else matched.group(1).replace(' ','-') if matched else None
        for a in db.scalars(select(Animal).order_by(Animal.ear_tag)):
            pen=pens.get(a.pen_id,'')
            if filter_pen and norm(pen)!=norm(filter_pen):continue
            if ('aktif' in q or req.status=='active') and a.status!='active':continue
            if req.status=='exited' and a.status!='exited':continue
            if req.date_from and a.arrival_date<req.date_from:continue
            if req.date_to and a.arrival_date>req.date_to:continue
            if search and search not in norm(' '.join([a.ear_tag,a.farm_ear_tag or '',a.breed,pen])):continue
            rows.append([a.ear_tag,a.farm_ear_tag or '—',a.breed,pen,tr_date(a.arrival_date),tr_number(a.entry_weight_kg),{'active':'Aktif','exited':'Çıkışı yapıldı'}.get(a.status,'Diğer durum')])
            if len(rows)>=5000:break
        result|={'title':'Hayvan listesi (en fazla 5.000)'+(f' · {filter_pen}' if filter_pen else ''),'columns':['TR Küpe No','İşletme Küpe No','Irk','Grup No','Giriş tarihi','Giriş kg','Durum'],'rows':rows}
    result['row_count']=len(result['rows'])
    result['mode']='Kural tabanlı, gerçek kayıtlar; yapay zekâ bağlantısı yok'
    return result

@router.post('/query')
def query_report(req:ReportRequest,request:Request,db:Session=Depends(get_db)):
    return evaluate(req,db,request)

@router.post('/export.csv')
def export_report(req:ReportRequest,request:Request,db:Session=Depends(get_db)):
    # Dışa aktarım izni olmadan veri hazırlamaya başlanmaz.
    authorize_report(request,selected_kind(req.query),export=True)
    result=evaluate(req,db,request)
    buf=io.StringIO();buf.write('\ufeff')
    writer=csv.writer(buf);writer.writerow(result['columns'])
    def safe_cell(value):
        value=str(value if value is not None else '')
        return "'"+value if value[:1] in ('\t','\r','\n') or value.lstrip(' \t\r\n')[:1] in ('=','+','-','@') else value
    writer.writerows([[safe_cell(x) for x in row] for row in result['rows']])
    return StreamingResponse(iter([buf.getvalue().encode('utf-8')]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="kzc_rapor.csv"'})
