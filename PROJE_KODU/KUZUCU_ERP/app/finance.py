"""Pilot stock alerts, reviewed Excel imports and reversible TL invoice ledger.

Prices are exclusive of VAT. Cost reporting is a simple weighted purchase-price
estimate, not a statutory stock valuation or a replacement for accounting.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO, StringIO
import csv
import hashlib
import json
import re
import unicodedata

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, get_db
from .models import Firm, Item, StockMovement
from .security import allowed, current_user, need

router = APIRouter(prefix='/api/finance', tags=['Stok, fatura ve hesaplar'])
MONEY = Decimal('0.01')
QTY = Decimal('0.001')
# Review receipts are intentionally process-local and expire. Re-opening an
# Excel after a restart regenerates the review; committed imports are persistent.
_previews = {}

def _rows_hash(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()

def now_utc():
    return datetime.now(timezone.utc)

def local_today():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo('Europe/Istanbul')).date()

def amount(value):
    if abs(Decimal(value)) >= Decimal('10000000000000000'):
        raise HTTPException(422,'Tutar desteklenen kayıt sınırını aşıyor. Miktar ve fiyatı kontrol edin.')
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)

def unit_key(value):
    value = str(value).strip().lower()
    return {'l':'lt', 'litre':'lt', 'liter':'lt', 'adet':'adet', 'kg':'kg', 'lt':'lt', 'ton':'ton'}.get(value, value)

def balance(db, item_id):
    return sum((m.quantity if m.type == 'IN' else -m.quantity
                for m in db.scalars(select(StockMovement).where(StockMovement.item_id == item_id))), Decimal(0))

def _lock(db):
    if db.get_bind().dialect.name == 'sqlite':
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')

def _commit(db):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Bu belge veya işlem daha önce kaydedildi. Kayıtları yenileyip kontrol edin.') from exc

class ItemSettings(Base):
    __tablename__ = 'finance_item_settings'
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'), primary_key=True)
    category: Mapped[str] = mapped_column(String(20), default='other')
    alarm_threshold: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True)
    low_active: Mapped[bool] = mapped_column(Boolean, default=False)

class StockAlert(Base):
    __tablename__ = 'finance_stock_alerts'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'), index=True)
    threshold: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    balance_at_creation: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(180), nullable=True)

class ImportRun(Base):
    __tablename__ = 'finance_import_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class Invoice(Base):
    __tablename__ = 'finance_invoices'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(12))
    firm_id: Mapped[int] = mapped_column(ForeignKey('firms.id'), index=True)
    invoice_no: Mapped[str] = mapped_column(String(100))
    invoice_key: Mapped[str] = mapped_column(String(240), unique=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    source_document: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(12), default='draft')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    vat_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class InvoiceLine(Base):
    __tablename__ = 'finance_invoice_lines'
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('finance_invoices.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))
    unit: Mapped[str] = mapped_column(String(12))
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    vat_total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    linked_movement_id: Mapped[int | None] = mapped_column(ForeignKey('stock_movements.id'), nullable=True)
    posted_movement_id: Mapped[int | None] = mapped_column(ForeignKey('stock_movements.id'), nullable=True)

class Account(Base):
    __tablename__ = 'finance_accounts'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(12))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

class LedgerEntry(Base):
    __tablename__ = 'finance_ledger_entries'
    id: Mapped[int] = mapped_column(primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey('firms.id'), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey('finance_accounts.id'), nullable=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey('finance_invoices.id'), nullable=True)
    entry_date: Mapped[date] = mapped_column(Date)
    direction: Mapped[str] = mapped_column(String(20))
    signed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    cash_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    source_key: Mapped[str] = mapped_column(String(160), unique=True)
    note: Mapped[str] = mapped_column(String(500), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

def sync_stock_alerts(db, now=None):
    """Flush, observe threshold crossings, append one episode; caller commits.

    Acknowledgement hides an episode after 24 hours. Replenishing stock never
    dismisses unacknowledged episodes. No repeat episode until stock recovers.
    """
    db.flush()
    for setting in db.scalars(select(ItemSettings)).all():
        low = setting.alarm_threshold is not None and balance(db, setting.item_id) <= setting.alarm_threshold
        if low and not setting.low_active:
            db.add(StockAlert(item_id=setting.item_id, threshold=setting.alarm_threshold,
                              balance_at_creation=balance(db, setting.item_id), created_at=now or now_utc()))
        setting.low_active = bool(low)
    db.flush()

def _catalog(db):
    settings = {s.item_id:s for s in db.scalars(select(ItemSettings))}
    return {'items':[{'id':i.id, 'code':i.code, 'name':i.name, 'unit':i.unit,
                      'category':settings[i.id].category if i.id in settings else 'other',
                      'alarm_threshold':str(settings[i.id].alarm_threshold) if i.id in settings and settings[i.id].alarm_threshold is not None else None}
                     for i in db.scalars(select(Item).order_by(Item.code))],
            'firms':[{'id':f.id,'name':f.name} for f in db.scalars(select(Firm).order_by(Firm.name))]}

@router.get('/catalog')
def catalog(request: Request, db: Session = Depends(get_db)):
    u=current_user(request)
    if not any(allowed(u,p) for p in ('stok.urun.view','stok.hareket.view','muhasebe.fatura.view','hesap.cari.view','reports.cost.view')):
        raise HTTPException(403,'Ürün ve firma listesini görme yetkiniz bulunmuyor.')
    data=_catalog(db)
    if not any(allowed(u,p) for p in ('muhasebe.fatura.view','hesap.cari.view')):
        data['firms']=[]
    return data

class SettingsIn(BaseModel):
    category: str = 'other'
    alarm_threshold: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=3)
    @field_validator('category')
    @classmethod
    def category_valid(cls,v):
        if v not in ('rawmaterial','medicine','other'):raise ValueError('Hammadde, ilaç veya diğer ürün türünü seçin')
        return v

@router.put('/items/{item_id}/settings')
def settings_update(item_id:int, data:SettingsIn, request:Request, db:Session=Depends(get_db)):
    need(request,'stok.urun.edit'); _lock(db)
    if not db.get(Item,item_id):raise HTTPException(404,'Ürün bulunamadı.')
    obj=db.get(ItemSettings,item_id)
    if obj is None:obj=ItemSettings(item_id=item_id);db.add(obj)
    obj.category=data.category;obj.alarm_threshold=data.alarm_threshold
    sync_stock_alerts(db);_commit(db)
    return {'item_id':item_id,**data.model_dump(mode='json')}

def _aware(v):
    return v.replace(tzinfo=timezone.utc) if v and v.tzinfo is None else v

def alert_dict(obj,db):
    item=db.get(Item,obj.item_id)
    hide=_aware(obj.acknowledged_at)+timedelta(hours=24) if obj.acknowledged_at else None
    return {'id':obj.id,'item_id':obj.item_id,'item_name':item.name,'unit':item.unit,
            'balance':str(balance(db,obj.item_id)),'threshold':str(obj.threshold),
            'created_at':_aware(obj.created_at).isoformat(),
            'acknowledged_at':_aware(obj.acknowledged_at).isoformat() if obj.acknowledged_at else None,
            'acknowledged_by':obj.acknowledged_by,'hide_at':hide.isoformat() if hide else None}

@router.get('/alerts')
def alerts(request:Request, db:Session=Depends(get_db)):
    need(request,'stok.hareket.view');_lock(db);sync_stock_alerts(db);_commit(db)
    now=now_utc()
    return [alert_dict(a,db) for a in db.scalars(select(StockAlert).order_by(StockAlert.id.desc()))
            if not a.acknowledged_at or now < _aware(a.acknowledged_at)+timedelta(hours=24)]

@router.post('/alerts/{alert_id}/ack')
def acknowledge(alert_id:int,request:Request,db:Session=Depends(get_db)):
    user=need(request,'stok.hareket.edit');_lock(db)
    obj=db.get(StockAlert,alert_id)
    if obj is None:raise HTTPException(404,'Uyarı bulunamadı.')
    if obj.acknowledged_at is None:
        obj.acknowledged_at=now_utc();obj.acknowledged_by=f'{user.display_name} ({user.username})'
    _commit(db);return alert_dict(obj,db)

def _norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(s).lower().replace('ı','i')) if not unicodedata.combining(c)).strip()

def sheet_number(value):
    if isinstance(value,(int,float,Decimal)):return Decimal(str(value))
    value=str(value or '').strip().replace(' ','')
    if not re.fullmatch(r'\d+(?:\.\d{3})*(?:,\d{1,4})?',value):
        raise ValueError('Miktarı Excel sayısı veya Türkçe sayı biçiminde yazın; örnek: 12.500,5')
    return Decimal(value.replace('.','').replace(',','.'))

class ImportRow(BaseModel):
    code:str=Field(min_length=1,max_length=50)
    name:str=Field(default='',max_length=120)
    unit:str=Field(min_length=1,max_length=12)
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=3)
    movement_date:date
    reference:str=Field(default='',max_length=100)

class ImportIn(BaseModel):
    source_key:str=Field(min_length=16,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    rows:list[ImportRow]=Field(min_length=1,max_length=500)

def validate_import_rows(rows,db):
    seen={}
    for row in rows:
        item=db.scalar(select(Item).where(Item.code==row.code))
        if unit_key(row.unit) not in ('kg','lt','adet','ton'):raise HTTPException(422,'Birim kg, litre, adet veya ton olmalıdır.')
        if item and unit_key(item.unit)!=unit_key(row.unit):raise HTTPException(409,f'{row.code}: birim ürün kartıyla uyuşmuyor.')
        if not item and not row.name.strip():raise HTTPException(422,f'{row.code}: yeni ürün için ad gereklidir.')
        if row.movement_date>local_today():raise HTTPException(422,'İleri tarihli stok aktarımı yapılamaz.')
        fingerprint=(row.name,unit_key(row.unit))
        if row.code in seen and seen[row.code]!=fingerprint:raise HTTPException(409,f'{row.code}: aynı ürün için farklı ad veya birim var.')
        seen[row.code]=fingerprint

@router.post('/stock-import/preview')
async def import_preview(request:Request,file:UploadFile=File(...),mapping:str=Form('{}'),db:Session=Depends(get_db)):
    need(request,'stok.hareket.create')
    if not (file.filename or '').lower().endswith('.xlsx'):raise HTTPException(422,'Excel dosyasını .xlsx biçiminde seçin.')
    raw=await file.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise HTTPException(413,'Excel dosyası 8 MB sınırını aşıyor.')
    try:
        import zipfile
        with zipfile.ZipFile(BytesIO(raw)) as z:
            if sum(i.file_size for i in z.infolist())>32*1024*1024:raise ValueError('Excel içeriği çok büyük')
        from openpyxl import load_workbook
        wb=load_workbook(BytesIO(raw),read_only=True,data_only=False)
        sheet=wb.active
        iterator=sheet.iter_rows(values_only=True)
        headers=[str(v or '').strip() for v in next(iterator)]
        supplied=json.loads(mapping)
        if not isinstance(supplied,dict):raise ValueError('Sütun eşleştirmesi geçersiz')
        aliases={'code':('urun kodu','kod','code'),'name':('urun adi','urun','name'),
                 'unit':('birim','unit'),'quantity':('miktar','quantity'),
                 'movement_date':('tarih','hareket tarihi','movement_date'),'reference':('belge','referans','reference')}
        indexes={}
        for key,options in aliases.items():
            if supplied.get(key):
                if supplied[key] not in headers:raise ValueError('Seçilen sütun bulunamadı')
                indexes[key]=headers.index(supplied[key])
            else:indexes[key]=next((i for i,h in enumerate(headers) if _norm(h) in options),None)
        if any(indexes[k] is None for k in ('code','unit','quantity')):raise ValueError('Ürün Kodu, Birim ve Miktar sütunları gerekli')
        rows=[];errors=[]
        for no,values in enumerate(iterator,start=2):
            if no>501:raise ValueError('Bir aktarım en fazla 500 satır olabilir')
            if not any(v is not None for v in values):continue
            try:
                def cell(k,default=''):
                    i=indexes[k]
                    return values[i] if i is not None and i<len(values) and values[i] is not None else default
                if any(isinstance(v,str) and v.startswith('=') for v in values):raise ValueError('Formül içeren satır desteklenmiyor; değerleri yapıştırın')
                day=cell('movement_date',local_today())
                if isinstance(day,datetime):day=day.date()
                if not isinstance(day,date):day=date.fromisoformat(str(day))
                row=ImportRow(code=str(cell('code')).strip(),name=str(cell('name')).strip(),unit=unit_key(cell('unit')),
                              quantity=sheet_number(cell('quantity')),movement_date=day,reference=str(cell('reference')).strip())
                validate_import_rows([row],db)
                rows.append(row.model_dump(mode='json'))
            except (ValueError,InvalidOperation,HTTPException) as exc:
                errors.append({'row':no,'message':exc.detail if isinstance(exc,HTTPException) else 'Satır bilgileri geçersiz. Kod, birim, miktar ve tarihi kontrol edin.'})
        wb.close()
        if not rows and not errors:errors.append({'row':2,'message':'Aktarılacak satır bulunamadı.'})
        source_key=hashlib.sha256(raw).hexdigest()
        while len(_previews)>=100:
            _previews.pop(next(iter(_previews)))
        _previews[(current_user(request).id,source_key)]=(_rows_hash(rows),bool(errors),now_utc())
        return {'source_key':source_key,'rows':rows,'errors':errors,'columns':headers}
    except HTTPException:raise
    except Exception as exc:raise HTTPException(422,'Excel okunamadı. .xlsx biçimini ve Ürün Kodu, Birim, Miktar sütunlarını kontrol edin.') from exc

@router.post('/stock-import/commit')
def import_commit(data:ImportIn,request:Request,db:Session=Depends(get_db)):
    need(request,'stok.hareket.create');_lock(db)
    digest=_rows_hash([r.model_dump(mode='json') for r in data.rows])
    previous=db.scalar(select(ImportRun).where(ImportRun.source_key==data.source_key))
    if previous:
        if previous.content_hash!=digest:raise HTTPException(409,'Bu dosya daha önce farklı bilgilerle aktarıldı.')
        return {'count':previous.row_count,'duplicate':True}
    receipt=_previews.get((current_user(request).id,data.source_key))
    if not receipt or receipt[1] or receipt[0]!=digest or now_utc()-receipt[2]>timedelta(hours=1):
        raise HTTPException(409,'Önce dosyanın hatasız ve güncel önizlemesini açıp kontrol edin. Değişen dosyayı yeniden yükleyin.')
    validate_import_rows(data.rows,db)
    for row in data.rows:
        item=db.scalar(select(Item).where(Item.code==row.code))
        if item is None:
            need(request,'stok.urun.create')
            item=Item(code=row.code,name=row.name.strip(),unit=unit_key(row.unit));db.add(item);db.flush()
        db.add(StockMovement(item_id=item.id,type='IN',quantity=row.quantity,movement_date=row.movement_date,reference=row.reference))
    db.add(ImportRun(source_key=data.source_key,content_hash=digest,row_count=len(data.rows)))
    sync_stock_alerts(db);_commit(db)
    return {'count':len(data.rows),'duplicate':False}

class InvoiceLineIn(BaseModel):
    item_id:int=Field(gt=0)
    unit:str
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=3)
    unit_price:Decimal=Field(ge=0,max_digits=16,decimal_places=4)
    vat_rate:Decimal=Field(ge=0,le=100,max_digits=6,decimal_places=3)
    linked_movement_id:int|None=Field(default=None,gt=0)

class InvoiceIn(BaseModel):
    kind:str
    firm_id:int=Field(gt=0)
    invoice_no:str=Field(min_length=1,max_length=100)
    invoice_date:date
    source_document:str|None=Field(default=None,max_length=160)
    lines:list[InvoiceLineIn]=Field(min_length=1,max_length=200)
    @field_validator('kind')
    @classmethod
    def valid_kind(cls,v):
        if v not in ('purchase','sale'):raise ValueError('Alış veya satış faturasını seçin')
        return v
    @field_validator('invoice_no')
    @classmethod
    def clean_no(cls,v):
        if not v.strip():raise ValueError('Fatura numarası boş olamaz')
        return v.strip()

def _invoice_lines(obj,db):
    return db.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id==obj.id,InvoiceLine.revision==obj.revision).order_by(InvoiceLine.id)).all()

def invoice_dict(obj,db):
    return {'id':obj.id,'kind':obj.kind,'firm_id':obj.firm_id,'firm_name':db.get(Firm,obj.firm_id).name,
            'invoice_no':obj.invoice_no,'invoice_date':obj.invoice_date.isoformat(),'source_document':obj.source_document,
            'status':obj.status,'revision':obj.revision,'subtotal':str(obj.subtotal),'vat_total':str(obj.vat_total),'total':str(obj.total),
            'lines':[{'id':l.id,'item_id':l.item_id,'item_name':db.get(Item,l.item_id).name,'unit':l.unit,
                      'quantity':str(l.quantity),'unit_price':str(l.unit_price),'vat_rate':str(l.vat_rate),
                      'subtotal':str(l.subtotal),'vat_total':str(l.vat_total),'total':str(l.total),
                      'linked_movement_id':l.linked_movement_id} for l in _invoice_lines(obj,db)]}

def _invoice_or_404(id,db):
    obj=db.get(Invoice,id)
    if obj is None:raise HTTPException(404,'Fatura bulunamadı.')
    return obj

def _invoice_data(obj,data,db):
    if not db.get(Firm,data.firm_id):raise HTTPException(404,'Firma bulunamadı. Önce firma kartını oluşturun.')
    if data.invoice_date>local_today():raise HTTPException(422,'İleri tarihli fatura işlenemez.')
    key=f'{data.kind}:{data.firm_id}:{data.invoice_no.casefold()}'
    same=db.scalar(select(Invoice).where(Invoice.invoice_key==key,Invoice.id!=(obj.id or -1)))
    if same:raise HTTPException(409,'Aynı firmaya ait bu fatura numarası zaten kayıtlı.')
    source=(data.source_document or '').strip() or None
    if source and db.scalar(select(Invoice.id).where(Invoice.source_document==source,Invoice.id!=(obj.id or -1))):
        raise HTTPException(409,'Bu belge daha önce bir faturaya bağlandı.')
    for row in data.lines:
        item=db.get(Item,row.item_id)
        if not item:raise HTTPException(404,'Fatura ürünlerinden biri bulunamadı.')
        if unit_key(row.unit) not in ('kg','adet','lt') or unit_key(item.unit)!=unit_key(row.unit):
            raise HTTPException(422,'Fatura birimi kg, adet veya litre olmalı ve ürün kartıyla aynı olmalıdır.')
    obj.kind=data.kind;obj.firm_id=data.firm_id;obj.invoice_no=data.invoice_no
    obj.invoice_key=key;obj.invoice_date=data.invoice_date;obj.source_document=source
    db.add(obj);db.flush()
    obj.subtotal=obj.vat_total=obj.total=Decimal(0)
    for row in data.lines:
        subtotal=amount(row.quantity*row.unit_price);vat=amount(subtotal*row.vat_rate/100)
        line=InvoiceLine(invoice_id=obj.id,revision=obj.revision,**row.model_dump(exclude={'unit'}),unit=unit_key(row.unit),
                         subtotal=subtotal,vat_total=vat,total=subtotal+vat)
        db.add(line);obj.subtotal+=subtotal;obj.vat_total+=vat;obj.total+=subtotal+vat
    amount(obj.total)
    db.flush()

def _post(obj,db):
    if obj.status!='draft':raise HTTPException(409,'Yalnızca taslak fatura onaylanabilir.')
    rows=_invoice_lines(obj,db);used=set()
    for row in rows:
        if row.linked_movement_id:
            if row.linked_movement_id in used:raise HTTPException(409,'Aynı stok hareketi iki satıra bağlanamaz.')
            used.add(row.linked_movement_id)
            old=db.get(StockMovement,row.linked_movement_id)
            expected='IN' if obj.kind=='purchase' else 'OUT'
            if not old or old.item_id!=row.item_id or old.type!=expected or old.quantity!=row.quantity:
                raise HTTPException(409,'Bağlanan stok hareketinin ürünü, yönü veya miktarı faturayla uyuşmuyor.')
            if (old.reference or '').startswith('FATURA:'):
                raise HTTPException(409,'Başka bir faturanın oluşturduğu stok hareketi tekrar kullanılamaz.')
            if (old.reference or '').startswith('RECEIPT:'):
                from .receiving import GoodsReceipt
                try:
                    receipt=db.get(GoodsReceipt,int(old.reference.split(':')[1]))
                except (ValueError,IndexError):
                    receipt=None
                firm=db.get(Firm,obj.firm_id)
                if not receipt or not firm.tax_no or receipt.supplier_tax_id!=firm.tax_no:
                    raise HTTPException(409,'Kantar/depo kabulünün firması faturanın firmasıyla uyuşmuyor.')
            links=db.execute(select(InvoiceLine,Invoice).join(Invoice,Invoice.id==InvoiceLine.invoice_id).where(
                InvoiceLine.linked_movement_id==old.id,Invoice.status=='posted',Invoice.id!=obj.id,
                InvoiceLine.revision==Invoice.revision)).all()
            if links:raise HTTPException(409,'Bu stok hareketi başka bir onaylı faturaya bağlı.')
        else:
            if obj.kind=='sale' and balance(db,row.item_id)<row.quantity:
                raise HTTPException(409,'Satış için stok yetersiz. Hiçbir fatura veya cari hareketi işlenmedi.')
            move=StockMovement(item_id=row.item_id,type='IN' if obj.kind=='purchase' else 'OUT',quantity=row.quantity,
                               movement_date=obj.invoice_date,reference=f'FATURA:{obj.id}:R{obj.revision}')
            db.add(move);db.flush();row.posted_movement_id=move.id
    db.add(LedgerEntry(firm_id=obj.firm_id,invoice_id=obj.id,entry_date=obj.invoice_date,
                       direction=obj.kind,signed_amount=obj.total if obj.kind=='sale' else -obj.total,
                       cash_amount=0,source_key=f'INV:{obj.id}:R{obj.revision}',note=f'Fatura {obj.invoice_no}'))
    obj.status='posted';db.flush();sync_stock_alerts(db)

def _reverse(obj,db):
    # Owned stock movements are reversed, never deleted. Explicit external links
    # represent goods already received elsewhere and do not get another posting.
    for row in _invoice_lines(obj,db):
        if row.posted_movement_id:
            movement=db.get(StockMovement,row.posted_movement_id)
            if movement.type=='IN' and balance(db,row.item_id)<row.quantity:
                raise HTTPException(409,'Fatura iptali stok bakiyesini eksiye düşürür. Önce ilgili hareketleri kontrol edin.')
            db.add(StockMovement(item_id=row.item_id,type='OUT' if movement.type=='IN' else 'IN',quantity=row.quantity,
                                  movement_date=local_today(),reference=f'FATURA:{obj.id}:R{obj.revision}:TERS'))
            db.flush()
    db.add(LedgerEntry(firm_id=obj.firm_id,invoice_id=obj.id,entry_date=local_today(),direction='reversal',
                       signed_amount=-obj.total if obj.kind=='sale' else obj.total,cash_amount=0,
                       source_key=f'INV:{obj.id}:R{obj.revision}:REV',note=f'Fatura ters kaydı {obj.invoice_no}'))
    db.flush()

@router.get('/invoices')
def invoices(request:Request,search:str='',kind:str='',firm_id:int|None=None,date_from:date|None=None,date_to:date|None=None,db:Session=Depends(get_db)):
    need(request,'muhasebe.fatura.view')
    q=select(Invoice).order_by(Invoice.invoice_date.desc(),Invoice.id.desc())
    if kind:q=q.where(Invoice.kind==kind)
    if firm_id:q=q.where(Invoice.firm_id==firm_id)
    if date_from:q=q.where(Invoice.invoice_date>=date_from)
    if date_to:q=q.where(Invoice.invoice_date<=date_to)
    rows=[invoice_dict(i,db) for i in db.scalars(q)]
    if search:rows=[r for r in rows if _norm(search) in _norm(r['invoice_no']+' '+r['firm_name'])]
    return rows

@router.post('/invoices',status_code=201)
def create_invoice(data:InvoiceIn,request:Request,db:Session=Depends(get_db)):
    need(request,'muhasebe.fatura.create');_lock(db)
    obj=Invoice(revision=1,status='draft');_invoice_data(obj,data,db);_commit(db)
    return invoice_dict(obj,db)

@router.put('/invoices/{invoice_id}')
def edit_invoice(invoice_id:int,data:InvoiceIn,request:Request,db:Session=Depends(get_db)):
    need(request,'muhasebe.fatura.edit');_lock(db);obj=_invoice_or_404(invoice_id,db)
    if obj.status=='cancelled':raise HTTPException(409,'İptal edilmiş fatura değiştirilemez.')
    posted=obj.status=='posted'
    if posted:_reverse(obj,db)
    obj.status='draft';obj.revision+=1;_invoice_data(obj,data,db)
    if posted:_post(obj,db)
    sync_stock_alerts(db);_commit(db);return invoice_dict(obj,db)

@router.post('/invoices/{invoice_id}/post')
def post_invoice(invoice_id:int,request:Request,db:Session=Depends(get_db)):
    need(request,'muhasebe.fatura.create');_lock(db);obj=_invoice_or_404(invoice_id,db)
    if obj.status=='posted':return invoice_dict(obj,db)
    _post(obj,db);_commit(db);return invoice_dict(obj,db)

@router.post('/invoices/{invoice_id}/cancel')
def cancel_invoice(invoice_id:int,request:Request,db:Session=Depends(get_db)):
    need(request,'muhasebe.fatura.delete');_lock(db);obj=_invoice_or_404(invoice_id,db)
    if obj.status=='cancelled':return invoice_dict(obj,db)
    if obj.status=='posted':_reverse(obj,db)
    obj.status='cancelled';sync_stock_alerts(db);_commit(db);return invoice_dict(obj,db)

class AccountIn(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    kind:str
    opening_balance:Decimal=Field(default=Decimal(0),ge=0,max_digits=18,decimal_places=2)
    @field_validator('name')
    @classmethod
    def name_clean(cls,v):
        if not v.strip():raise ValueError('Hesap adı boş olamaz')
        return v.strip()
    @field_validator('kind')
    @classmethod
    def kind_clean(cls,v):
        if v not in ('cash','bank'):raise ValueError('Kasa veya banka seçin')
        return v

class PaymentIn(BaseModel):
    firm_id:int=Field(gt=0)
    account_id:int=Field(gt=0)
    direction:str
    amount:Decimal=Field(gt=0,max_digits=18,decimal_places=2)
    paid_on:date
    note:str=Field(default='',max_length=500)
    source_key:str=Field(min_length=8,max_length=100)
    @field_validator('direction')
    @classmethod
    def direction_clean(cls,v):
        if v not in ('payment','collection'):raise ValueError('Ödeme veya tahsilat seçin')
        return v

@router.post('/accounts',status_code=201)
def add_account(data:AccountIn,request:Request,db:Session=Depends(get_db)):
    need(request,'hesap.cari.create');_lock(db)
    obj=Account(**data.model_dump());db.add(obj);_commit(db)
    return {'id':obj.id,'name':obj.name,'kind':obj.kind,'balance':str(obj.opening_balance)}

@router.post('/payments',status_code=201)
def payment(data:PaymentIn,request:Request,db:Session=Depends(get_db)):
    need(request,'hesap.cari.create');_lock(db)
    if data.paid_on>local_today():raise HTTPException(422,'İleri tarihli ödeme/tahsilat kaydedilemez.')
    if not db.get(Firm,data.firm_id) or not db.get(Account,data.account_id):raise HTTPException(404,'Firma veya hesap bulunamadı.')
    key='PAY:'+data.source_key
    old=db.scalar(select(LedgerEntry).where(LedgerEntry.source_key==key))
    if old:
        if (old.firm_id,old.account_id,old.direction,abs(old.signed_amount),old.entry_date,old.note)!=(data.firm_id,data.account_id,data.direction,data.amount,data.paid_on,data.note):
            raise HTTPException(409,'Aynı işlem anahtarı farklı ödeme bilgileriyle kullanılamaz.')
        return {'id':old.id,'duplicate':True}
    cash=data.amount if data.direction=='collection' else -data.amount
    if data.direction=='payment':
        cash_balance=db.get(Account,data.account_id).opening_balance+sum((r.cash_amount for r in db.scalars(select(LedgerEntry).where(LedgerEntry.account_id==data.account_id))),Decimal(0))
        if cash_balance<data.amount:raise HTTPException(409,'Seçilen kasa/banka hesabının bakiyesi ödeme için yetersiz.')
    obj=LedgerEntry(firm_id=data.firm_id,account_id=data.account_id,entry_date=data.paid_on,direction=data.direction,
                    signed_amount=-cash,cash_amount=cash,source_key=key,note=data.note)
    db.add(obj);_commit(db);return {'id':obj.id,'duplicate':False}

@router.get('/accounts')
def accounts(request:Request,firm_id:int|None=None,date_from:date|None=None,date_to:date|None=None,db:Session=Depends(get_db)):
    need(request,'hesap.cari.view')
    entries=db.scalars(select(LedgerEntry).order_by(LedgerEntry.entry_date,LedgerEntry.id)).all()
    firms={f.id:f for f in db.scalars(select(Firm))};accts={a.id:a for a in db.scalars(select(Account))}
    sums={id:sum((e.signed_amount for e in entries if e.firm_id==id),Decimal(0)) for id in firms}
    return {'currency':'TL','accounts':[{'id':a.id,'name':a.name,'kind':a.kind,
           'opening_balance':str(a.opening_balance),
           'balance':str(a.opening_balance+sum((e.cash_amount for e in entries if e.account_id==a.id),Decimal(0)))} for a in accts.values()],
           'firms':[{'id':f.id,'name':f.name,'balance':str(sums[f.id]),'receivable':str(max(sums[f.id],Decimal(0))),
                     'payable':str(max(-sums[f.id],Decimal(0)))} for f in firms.values() if not firm_id or firm_id==f.id],
           'entries':[{'id':e.id,'date':e.entry_date.isoformat(),'firm_name':firms[e.firm_id].name,
                       'account_name':accts[e.account_id].name if e.account_id else 'Cari hesap',
                       'direction':e.direction,'amount':str(abs(e.signed_amount)),'signed_amount':str(e.signed_amount),
                       'note':e.note} for e in entries if (not firm_id or firm_id==e.firm_id)
                      and (not date_from or e.entry_date>=date_from) and (not date_to or e.entry_date<=date_to)]}

@router.get('/costs')
def costs(request:Request,db:Session=Depends(get_db)):
    need(request,'reports.cost.view')
    pairs=db.execute(select(InvoiceLine,Invoice).join(Invoice,InvoiceLine.invoice_id==Invoice.id).where(
        Invoice.status=='posted',Invoice.kind=='purchase',InvoiceLine.revision==Invoice.revision)).all()
    rows=[]
    for item in db.scalars(select(Item).order_by(Item.code)):
        lines=[l for l,i in pairs if l.item_id==item.id]
        qty=sum((l.quantity for l in lines),Decimal(0));net=sum((l.subtotal for l in lines),Decimal(0))
        average=net/qty if qty else None
        priced={l.posted_movement_id or l.linked_movement_id for l in lines}
        # Reversal entries are not new purchases and must not look like unpriced receipts.
        unpriced=sum((m.quantity for m in db.scalars(select(StockMovement).where(StockMovement.item_id==item.id,StockMovement.type=='IN'))
                      if m.id not in priced and not (m.reference or '').startswith('FATURA:')),Decimal(0))
        stock=balance(db,item.id)
        rows.append({'item_id':item.id,'name':item.name,'unit':item.unit,'purchased_quantity':str(qty),'purchase_net':str(net),
                     'average_net_price':str(average.quantize(Decimal('0.0001'))) if average is not None else None,
                     'stock_balance':str(stock),'estimated_stock_cost':str(amount(stock*average)) if average is not None and not unpriced else None,
                     'unpriced_incoming':str(unpriced)})
    return {'currency':'TL','method':'Onaylı alış faturalarının KDV hariç miktar ağırlıklı ortalama birim fiyatı. '
            'KDV maliyete eklenmez. Fiyatı bilinmeyen stok girişi varsa stok maliyeti hesaplanmaz. '
            'Bu pilot tahmini, dönemsel muhasebe veya FIFO değerlemesi değildir.','rows':rows}

@router.get('/reports/invoices.csv')
def invoices_csv(request:Request,db:Session=Depends(get_db)):
    need(request,'reports.finance.view');need(request,'reports.finance.export');need(request,'muhasebe.fatura.view')
    def safe(v):
        s=str(v or '')
        return "'"+s if s[:1] in ('=','+','-','@','\t','\r') else s
    out=StringIO();out.write('\ufeff');writer=csv.writer(out)
    writer.writerow(['Fatura No','Tarih','Tür','Firma','Durum','KDV Hariç Tutar (TL)','KDV (TL)','Genel Toplam (TL)'])
    for i in db.scalars(select(Invoice).order_by(Invoice.invoice_date,Invoice.id)):
        writer.writerow([safe(i.invoice_no),i.invoice_date.strftime('%d.%m.%Y'),'Alış' if i.kind=='purchase' else 'Satış',
                         safe(db.get(Firm,i.firm_id).name),{'draft':'Taslak','posted':'Onaylandı','cancelled':'İptal'}[i.status],
                         str(i.subtotal).replace('.',','),str(i.vat_total).replace('.',','),str(i.total).replace('.',',')])
    return StreamingResponse(iter([out.getvalue().encode('utf-8')]),media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition':'attachment; filename="fatura_raporu.csv"'})

def _csv(headers,rows,filename):
    out=StringIO();out.write('\ufeff');writer=csv.writer(out);writer.writerow(headers)
    for row in rows:
        values=[]
        for value in row:
            s=str(value if value is not None else 'Bilinmiyor')
            values.append("'"+s if s[:1] in ('=','+','-','@','\t','\r') else s)
        writer.writerow(values)
    return StreamingResponse(iter([out.getvalue().encode('utf-8')]),media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition':f'attachment; filename="{filename}"'})

@router.get('/reports/costs.csv')
def cost_csv(request:Request,db:Session=Depends(get_db)):
    need(request,'reports.cost.view');need(request,'reports.cost.export')
    data=costs(request,db=db)
    def tr(v):return str(v).replace('.',',') if v is not None else 'Bilinmiyor'
    return _csv(['Ürün','Birim','Faturalı Alış Miktarı','KDV Hariç Alış (TL)','Ortalama Birim Fiyat (TL)',
                 'Stok','Fiyatı Bilinmeyen Giriş','Tahmini Stok Maliyeti (TL)'],
                [[r['name'],r['unit'],*[tr(r[k]) for k in ('purchased_quantity','purchase_net','average_net_price',
                  'stock_balance','unpriced_incoming','estimated_stock_cost')]] for r in data['rows']],'maliyet_raporu.csv')

@router.get('/reports/accounts.csv')
def account_csv(request:Request,db:Session=Depends(get_db)):
    need(request,'reports.finance.view');need(request,'reports.finance.export');need(request,'hesap.cari.view')
    data=accounts(request,db=db,firm_id=None,date_from=None,date_to=None)
    return _csv(['Firma','Alacağımız (TL)','Borcumuz (TL)','Net Bakiye (TL)'],
                [[r['name'],r['receivable'].replace('.',','),r['payable'].replace('.',','),r['balance'].replace('.',',')]
                 for r in data['firms']],'cari_bakiye_raporu.csv')
