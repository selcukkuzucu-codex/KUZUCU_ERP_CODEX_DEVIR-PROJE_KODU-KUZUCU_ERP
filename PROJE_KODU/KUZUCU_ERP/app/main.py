import asyncio
from contextlib import asynccontextmanager
from datetime import date
import io
import uuid
from decimal import Decimal
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field as PField, ConfigDict, model_validator, field_validator
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Pen, Animal, Weighing, Field, CropSeason, Item, StockMovement, Firm, StockMovementRevision
from .import_preview import router as import_router
from .reports import router as reports_router
from .receiving import router as receiving_router
from .document_preview import router as documents_router
from .agenda import router as agenda_router
from .animal_health import router as animal_health_router, daily_worker
from .calf import router as calves_router
from .security import router as security_router, auth_middleware, creator_map, AuditEvent, allowed, current_user
from .translations import FIELD_LABELS as DISPLAY_FIELD_LABELS
from .finance import router as finance_router
from .personnel import router as personnel_router
from .animal_operations import router as animal_operations_router
from .camera_documents import router as capture_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy.orm import sessionmaker
    from .backup import backup_db
    # Backup of the old DB BEFORE any schema change.
    backup_path=backup_db(engine, force=True, label="once-acilis-oncesi")
    if engine.dialect.name=='sqlite' and engine.url.database and Path(engine.url.database).is_file() and backup_path is None:
        raise RuntimeError('Açılış öncesi yedek alınamadı. Yedek klasörünün erişimini ve boş alanı kontrol edin; mevcut kayıtlarda geçiş yapılmadı.')
    app.state.auth_session_factory=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    app.state.db_engine=engine
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == 'sqlite':
        with engine.begin() as conn:
            # Denetim kayıtları program API'sinden silinmez; SQLite tetikleyicileri de korur.
            conn.execute(text('''CREATE TRIGGER IF NOT EXISTS erp_audit_prevent_update
                BEFORE UPDATE ON erp_audit_events BEGIN
                SELECT RAISE(ABORT,'Audit records cannot be updated'); END'''))
            conn.execute(text('''CREATE TRIGGER IF NOT EXISTS erp_audit_prevent_delete
                BEFORE DELETE ON erp_audit_events BEGIN
                SELECT RAISE(ABORT,'Audit records cannot be deleted'); END'''))
    # Önceki Mac/Windows SQLite veritabanlarında yeni sütunları veri silmeden ekle.
    # create_all mevcut tabloları değiştirmez; bu küçük geçiş bu nedenle gerekli.
    if engine.dialect.name == 'sqlite':
        with engine.begin() as conn:
            existing = {row[1] for row in conn.execute(text('PRAGMA table_info(fields)'))}
            if 'ada_no' not in existing:
                conn.execute(text('ALTER TABLE fields ADD COLUMN ada_no VARCHAR(40)'))
            if 'satellite_image' not in existing:
                conn.execute(text('ALTER TABLE fields ADD COLUMN satellite_image VARCHAR(150)'))
            animal_columns = {row[1] for row in conn.execute(text('PRAGMA table_info(animals)'))}
            for col, sqltype in (('farm_ear_tag','VARCHAR(60)'),('birth_date','DATE'),('sex','VARCHAR(10)')):
                if col not in animal_columns:
                    conn.execute(text(f'ALTER TABLE animals ADD COLUMN {col} {sqltype}'))
            conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_animals_farm_ear_tag ON animals(farm_ear_tag)'))
            health_columns = {row[1] for row in conn.execute(text('PRAGMA table_info(health_cases)'))}
            if 'treatment_name' not in health_columns:
                conn.execute(text("ALTER TABLE health_cases ADD COLUMN treatment_name VARCHAR(180) NOT NULL DEFAULT ''"))
            if 'repeat_review_confirmed' not in health_columns:
                conn.execute(text('ALTER TABLE health_cases ADD COLUMN repeat_review_confirmed BOOLEAN NOT NULL DEFAULT 0'))
            calf_columns = {row[1] for row in conn.execute(text('PRAGMA table_info(calves)'))}
            if 'exit_group_no' not in calf_columns:
                conn.execute(text("ALTER TABLE calves ADD COLUMN exit_group_no VARCHAR(80) NOT NULL DEFAULT ''"))
            stock_columns = {row[1] for row in conn.execute(text('PRAGMA table_info(stock_movements)'))}
            if 'movement_date' not in stock_columns:
                conn.execute(text('ALTER TABLE stock_movements ADD COLUMN movement_date DATE'))
                # Eski hareketlerde giris tarihi bilinmiyorsa olusturulma tarihini kullan.
                conn.execute(text("UPDATE stock_movements SET movement_date = substr(created_at, 1, 10) WHERE created_at IS NOT NULL"))
    from .agenda import migrate_v015 as migrate_agenda
    from .animal_health import migrate_v015 as migrate_health
    from .calf import migrate_v015 as migrate_calves
    migrate_agenda(engine)
    migrate_health(engine)
    migrate_calves(engine)
    from .backup import periodic_backup
    worker = asyncio.create_task(daily_worker(engine))
    backup_worker = asyncio.create_task(periodic_backup(engine))
    try:
        yield
    finally:
        backup_worker.cancel()
        try: await backup_worker
        except asyncio.CancelledError: pass
        backup_db(engine, force=True, label="normal-kapanis")
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass

APP_VERSION = '0.16.0'
app = FastAPI(title='KUZUCU ERP - Pilot', version=APP_VERSION, lifespan=lifespan)
app.include_router(reports_router)
app.include_router(import_router)
app.include_router(receiving_router)
app.include_router(documents_router)
app.include_router(agenda_router)
app.include_router(animal_health_router)
app.include_router(calves_router)
app.include_router(security_router)
app.include_router(finance_router)
app.include_router(personnel_router)
app.include_router(animal_operations_router)
app.include_router(capture_router)
from .v16 import router as v16_router
app.include_router(v16_router)
app.middleware('http')(auth_middleware)

FIELD_LABELS = {
    'code':'Kod', 'ada_no':'Ada No', 'name':'Ad / İsim', 'area_decare':'Alan (dekar)',
    'field_id':'Parsel', 'year':'Üretim yılı', 'crop':'Ürün', 'capacity':'Grup kapasitesi',
    'ear_tag':'TR Küpe No', 'tr_ear_tag':'TR Küpe No', 'farm_ear_tag':'İşletme Küpe No',
    'animal_id':'Hayvan', 'pen_id':'Padok', 'breed':'Irk', 'sex':'Cinsiyet',
    'birth_date':'Doğum tarihi', 'arrival_date':'Giriş tarihi', 'entry_date':'Giriş tarihi',
    'entry_kg':'Giriş kilosu', 'entry_weight_kg':'Giriş kilosu', 'exit_kg':'Çıkış kilosu',
    'exit_date':'Çıkış tarihi', 'exit_group_no':'Toplu Çıkış No', 'entries':'Çıkış listesi',
    'calf_id':'Buzağı', 'planned_days':'Planlanan büyütme günü', 'batch_code':'Alım grubu',
    'consumed_on':'Tüketim tarihi', 'milk_kg':'Süt / mama miktarı', 'feed_kg':'Yem miktarı',
    'measured_at':'Tartım tarihi', 'measured_on':'Tartım tarihi', 'weight_kg':'Tartım kilosu',
    'item_id':'Stok ürünü', 'unit':'Birim', 'type':'Hareket türü', 'quantity':'Miktar',
    'movement_date':'Hareket tarihi', 'reference':'Belge / Referans', 'reason':'Düzeltme nedeni',
    'tax_no':'Vergi numarası', 'phone':'Telefon', 'address':'Adres',
    'title':'Başlık', 'notes':'Açıklama', 'category':'Bölüm', 'frequency':'Tekrar sıklığı',
    'start_date':'Başlangıç tarihi', 'remind_time':'Hatırlatma saati', 'is_active':'Aktiflik durumu',
    'record_type':'İşlem türü', 'condition_name':'Hastalık / durum adı', 'symptoms':'Belirtiler',
    'product_name':'İlaç / aşı adı', 'treatment_name':'Tedavi / protokol adı',
    'repeat_review_confirmed':'Tekrar uygulama onayı', 'dosage_text':'Doz / uygulama',
    'veterinarian':'Veteriner hekim', 'vet_approved':'Veteriner onayı',
    'applications_per_day':'Günlük uygulama sayısı', 'planned_end_date':'Planlanan bitiş tarihi',
    'withdrawal_end_date':'Arınma / kesim kısıtı bitişi', 'performed_on':'Uygulama tarihi',
    'performed_by':'Uygulayan kişi', 'observation':'Gözlem', 'response':'Uygulama sonucu',
    'outcome':'Tedavi sonucu', 'outcome_notes':'Sonuç açıklaması', 'closed_date':'Kapanış tarihi',
    'daily_time':'Günlük çıktı saati', 'auto_generate':'Otomatik rapor oluşturma',
    'auto_print':'Otomatik yazdırma', 'printer_name':'Yazıcı adı', 'kind':'Belge / kayıt türü',
    'supplier_tax_id':'Firma vergi numarası', 'weigh_ticket_no':'Kantar fişi numarası',
    'delivery_note_no':'İrsaliye numarası', 'vehicle_plate':'Araç plakası',
    'gross_kg':'Brüt kilo', 'tare_kg':'Dara kilosu', 'invoice_no':'Fatura numarası',
    'line_no':'Fatura satırı', 'quantity_kg':'Miktar (kg)', 'receipt_id':'Kantar kaydı',
    'invoice_line_id':'Fatura satırı', 'tolerance_kg':'Miktar toleransı (kg)',
    'tolerance_percent':'Tolerans yüzdesi', 'query':'Rapor isteği', 'on':'Liste tarihi',
    'username':'Kullanıcı adı', 'password':'Şifre', 'new_password':'Yeni şifre',
    'display_name':'Ad Soyad', 'department':'Departman', 'is_admin':'Yönetici yetkisi',
    'permissions':'Yetkiler', 'values':'Taslak bilgileri', 'file':'Dosya',
}
FIELD_LABELS.update(DISPLAY_FIELD_LABELS)

@app.exception_handler(RequestValidationError)
async def turkish_validation_error(request:Request,exc:RequestValidationError):
    fields=[]
    for row in exc.errors():
        # İç içe listelerde veya sözlüklerde teknik yol, sıra ve kullanıcı
        # tarafından verilen anahtarlar yerine en yakın tanınan alanı göster.
        label=next((FIELD_LABELS[key] for key in reversed(row.get('loc',()))
                    if isinstance(key,str) and key in FIELD_LABELS), 'Girilen bilgiler')
        if label not in fields:
            fields.append(label)
        if len(fields)==5:
            break
    if not fields:
        fields.append('Girilen bilgiler')
    return JSONResponse({'detail':'Eksik veya geçersiz bilgi: '+', '.join(fields)+'. Alanları kontrol edin.'},status_code=422)

@app.exception_handler(Exception)
async def safe_unexpected_error(request:Request,exc:Exception):
    import logging
    logging.getLogger('kuzucu.erp').exception('Beklenmeyen sunucu hatası: %s %s',request.method,request.url.path,exc_info=exc)
    return JSONResponse({'detail':'Beklenmeyen bir sorun oluştu. İşlemi tekrar deneyin; devam ederse yöneticinize bildirin.'},status_code=500)

@app.exception_handler(StarletteHTTPException)
async def turkish_http_error(request:Request,exc:StarletteHTTPException):
    defaults={'Not Found':'İstenen kayıt veya sayfa bulunamadı.','Method Not Allowed':'Bu işlem bu sayfada kullanılamaz.',
              'Unauthorized':'Önce kullanıcı girişi yapın.','Forbidden':'Bu işlem için yetkiniz bulunmuyor.'}
    detail=defaults.get(exc.detail,exc.detail) if isinstance(exc.detail,str) else exc.detail
    return JSONResponse({'detail':detail},status_code=exc.status_code,headers=exc.headers)

static_dir = Path(__file__).parent / 'static'
app.mount('/static', StaticFiles(directory=static_dir), name='static')

class PenIn(BaseModel):
    code: str = PField(min_length=1, max_length=40)
    capacity: int = PField(gt=0)
class AnimalIn(BaseModel):
    # Eski istemciler ear_tag gonderebilir. Yeni arayuz TR kupe no adini kullanir.
    ear_tag: str | None = PField(default=None, max_length=60)
    tr_ear_tag: str | None = PField(default=None, max_length=60)
    farm_ear_tag: str | None = PField(default=None, max_length=60)
    sex: str | None = None
    birth_date: date | None = None
    breed: str = 'Belirtilmedi'
    arrival_date: date
    entry_weight_kg: Decimal = PField(gt=0)
    pen_id: int

    @model_validator(mode='after')
    def validated(self):
        tag = (self.tr_ear_tag or self.ear_tag or '').strip()
        if not tag or (self.tr_ear_tag and self.ear_tag and self.tr_ear_tag.strip()!=self.ear_tag.strip()):
            raise ValueError('TR küpe numarası zorunlu ve tutarlı olmalı')
        self.ear_tag=tag
        self.tr_ear_tag=tag
        self.farm_ear_tag=(self.farm_ear_tag or '').strip() or None
        if self.sex not in (None,'male','female'):
            raise ValueError('Cinsiyet erkek veya dişi olmalı')
        if self.birth_date and self.birth_date > self.arrival_date:
            raise ValueError('Doğum tarihi alım tarihinden sonra olamaz')
        return self
class WeightIn(BaseModel):
    measured_at: date
    weight_kg: Decimal = PField(gt=0)
class FieldIn(BaseModel):
    code: str = PField(min_length=1, max_length=40)
    ada_no: str | None = PField(default=None, max_length=40)
    name: str = PField(min_length=1, max_length=120)
    # Veritabanı sütunu Numeric(12,3): fazla ondalık sessizce yuvarlanmasın.
    area_decare: Decimal = PField(gt=0, max_digits=12, decimal_places=3)

    @field_validator('code', 'ada_no', 'name', mode='before')
    @classmethod
    def strip_text(cls, value):
        # Baştaki/sondaki boşluklar ayrı parsel kodu oluşturmasın; boş Ada No saklanmasın.
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator('ada_no')
    @classmethod
    def empty_ada_is_none(cls, value):
        return value or None
class SeasonIn(BaseModel):
    field_id: int
    year: int = PField(ge=2000, le=2200)
    crop: str = PField(min_length=1)
class ItemIn(BaseModel):
    code: str = PField(min_length=1, max_length=50)
    name: str = PField(min_length=1, max_length=120)
    unit: str = PField(default='kg', max_length=12)

    @field_validator('code', 'name', 'unit', mode='before')
    @classmethod
    def strip_item_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('unit')
    @classmethod
    def known_unit(cls, value):
        # Fatura ve stok raporları bu birimleri tanır; birimler birbirine çevrilmez.
        value = {'litre': 'lt', 'l': 'lt'}.get(value.casefold(), value.casefold())
        if value not in ('kg', 'ton', 'adet', 'lt'):
            raise ValueError('Birim kg, ton, adet veya litre olmalı')
        return value
class MovementIn(BaseModel):
    item_id: int
    type: str
    quantity: Decimal = PField(gt=0)
    movement_date: date = PField(default_factory=date.today)
    reference: str = PField(default='', max_length=100)
class MovementUpdateIn(MovementIn):
    reason: str = PField(min_length=3, max_length=300)
class FirmIn(BaseModel):
    name: str = PField(min_length=1, max_length=180)
    tax_no: str | None = PField(default=None, max_length=20)
    phone: str = PField(default='', max_length=40)
    address: str = PField(default='', max_length=600)

def as_dict(row):
    output = {c.name: (str(getattr(row,c.name)) if isinstance(getattr(row,c.name),Decimal) else getattr(row,c.name)) for c in row.__table__.columns}
    if isinstance(row, Animal):
        output['tr_ear_tag']=row.ear_tag
        if row.birth_date:
            today=date.today()
            output['age_days']=(today-row.birth_date).days
            output['age_months']=max(0, (today.year-row.birth_date.year)*12+today.month-row.birth_date.month-(today.day<row.birth_date.day))
        else:
            output['age_days']=None
            output['age_months']=None
    return output

def unique(db, model, field, val):
    if db.scalar(select(model.id).where(getattr(model,field)==val)) is not None:
        label={(Pen,'code'):'Grup No', (Field,'code'):'Parsel kodu',
               (Item,'code'):'Ürün kodu', (Animal,'ear_tag'):'TR küpe numarası',
               (Firm,'tax_no'):'Vergi numarası'}.get((model,field),'Bu bilgi')
        raise HTTPException(409, f'{label} zaten kayıtlı.')

@app.get('/')
def home(): return FileResponse(static_dir / 'index.html')
@app.get('/api/breeds')
def breeds(request:Request,db:Session=Depends(get_db)):
    from .security import need, allowed, current_user
    u=current_user(request)
    if not (allowed(u,'hayvanlar.kart.view') or allowed(u,'hayvanlar.buzagi.view')):
        raise HTTPException(403,'Irk listesini görme yetkiniz yok.')
    from .models import Calf
    defaults={'Simental','Holstein','Montofon','Angus','Şarole','Limuzin','Hereford','Belçika Mavisi','Jersey','Yerli Kara','Melez'}
    names=defaults | set(db.scalars(select(Animal.breed).distinct()).all()) | set(db.scalars(select(Calf.breed).distinct()).all())
    return sorted([x for x in names if x and x!='Belirtilmedi'],key=str.casefold)

@app.get('/api/health')
def health():
    import hashlib
    return {'status':'ok','version':APP_VERSION,'instance_id':hashlib.sha256(str(Path(__file__).resolve().parent.parent).encode('utf-8')).hexdigest()}
@app.get('/api/dashboard')
def dashboard(request:Request,db: Session = Depends(get_db)):
    from .models import Calf
    from .calf import today_local
    user=current_user(request)
    can_animals=allowed(user,'hayvanlar.kart.view')
    can_calves=allowed(user,'hayvanlar.buzagi.view')
    # Aynı TR küpesi iki bölümde de varsa tek hayvan sayılır. İzin verilmeyen bölümün verisi kullanılmaz.
    visible={}
    if can_animals:
        visible.update({a.ear_tag:a for a in db.scalars(select(Animal).where(Animal.status=='active'))})
    calves=list(db.scalars(select(Calf).where((Calf.exit_date==None)|(Calf.exit_date>today_local())))) if can_calves else []
    for calf in calves:
        visible.setdefault(calf.tr_ear_tag,calf)
    sexes={key:sum(a.sex==key for a in visible.values()) for key in ('male','female')}
    breeds={}
    for animal in visible.values():breeds[animal.breed or 'Belirtilmedi']=breeds.get(animal.breed or 'Belirtilmedi',0)+1
    milk=[c for c in calves if c.milk_phase is True]
    total_animals=db.scalar(select(func.count()).select_from(Animal).where(Animal.status=='active')) or 0
    total_fields=db.scalar(select(func.coalesce(func.sum(Field.area_decare),0))) or 0
    total_pens=db.scalar(select(func.count()).select_from(Pen)) or 0
    return {'active_animals':total_animals if allowed(user,'hayvanlar.kart.view') else None,
            'area_decare':str(total_fields) if allowed(user,'tarim.parseller.view') else None,
            'pens':total_pens if allowed(user,'hayvanlar.padok.view') else None,
            'active_total':len(visible) if can_animals or can_calves else None,
            'male_total':sexes['male'] if can_animals or can_calves else None,
            'female_total':sexes['female'] if can_animals or can_calves else None,
            'unknown_sex_total':len(visible)-sum(sexes.values()) if can_animals or can_calves else None,
            'breeds':[{'breed':name,'total':count} for name,count in sorted(breeds.items())] if can_animals or can_calves else None,
            'milk_calves':{'male':sum(c.sex=='male' for c in milk),'female':sum(c.sex=='female' for c in milk),
                           'unknown_sex':sum(c.sex not in ('male','female') for c in milk),
                           'phase_unknown':sum(c.milk_phase is None for c in calves)} if can_calves else None}

@app.post('/api/pens',status_code=201)
def add_pen(data: PenIn,db:Session=Depends(get_db)):
    unique(db,Pen,'code',data.code)
    obj=Pen(**data.model_dump());db.add(obj);db.commit();db.refresh(obj);return as_dict(obj)
@app.get('/api/pens')
def get_pens(db:Session=Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(Pen).order_by(Pen.code))]

@app.post('/api/animals',status_code=201)
def add_animal(data:AnimalIn,request:Request,db:Session=Depends(get_db)):
    from .checks import LIMITS, require_confirmation, tr_kg
    from .calf import today_local
    unique(db,Animal,'ear_tag',data.ear_tag)
    if data.arrival_date>today_local():raise HTTPException(422,'Giriş tarihi ileri bir tarih olamaz.')
    if data.birth_date and data.birth_date>today_local():raise HTTPException(422,'Doğum tarihi ileri bir tarih olamaz.')
    if data.entry_weight_kg<LIMITS['animal_min_kg'] or data.entry_weight_kg>LIMITS['animal_max_kg']:
        require_confirmation(request,[f'Giriş kilosu {tr_kg(data.entry_weight_kg)} kg; besi hayvanı için olağandışı.'])
    pen=db.get(Pen,data.pen_id)
    if pen is None: raise HTTPException(404,'Grup bulunamadı')
    current=db.scalar(select(func.count()).select_from(Animal).where(Animal.pen_id==pen.id,Animal.status=='active')) or 0
    if current >= pen.capacity: raise HTTPException(409,'Grup kapasitesi dolu')
    if data.farm_ear_tag and db.scalar(select(Animal.id).where(Animal.farm_ear_tag==data.farm_ear_tag)) is not None:
        raise HTTPException(409,'İşletme küpe numarası zaten kayıtlı')
    payload=data.model_dump(exclude={'tr_ear_tag'})
    obj=Animal(**payload);db.add(obj);db.commit();db.refresh(obj);return as_dict(obj)
@app.get('/api/animals')
def get_animals(db:Session=Depends(get_db)):
    animals=db.scalars(select(Animal).order_by(Animal.id.desc()).limit(500)).all()
    actors=creator_map(db,'animals',[x.id for x in animals])
    return [{**as_dict(x),'created_by':actors.get(x.id,'Eski kayıt')} for x in animals]
@app.put('/api/animals/{animal_id}')
def update_animal(animal_id:int,data:AnimalIn,db:Session=Depends(get_db)):
    obj=db.get(Animal,animal_id)
    if obj is None:raise HTTPException(404,'Hayvan bulunamadı')
    if obj.status!='active':raise HTTPException(409,'Çıkışı yapılan hayvanın kimlik ve giriş bilgileri değiştirilemez. Çıkış geçmişini inceleyin.')
    if data.ear_tag!=obj.ear_tag:unique(db,Animal,'ear_tag',data.ear_tag)
    if data.farm_ear_tag and db.scalar(select(Animal.id).where(Animal.farm_ear_tag==data.farm_ear_tag, Animal.id!=animal_id)) is not None:
        raise HTTPException(409,'İşletme küpe numarası zaten kayıtlı')
    if db.get(Pen,data.pen_id) is None:raise HTTPException(404,'Grup bulunamadı')
    for k,v in data.model_dump(exclude={'tr_ear_tag'}).items():setattr(obj,k,v)
    db.commit();db.refresh(obj);return as_dict(obj)

@app.post('/api/animals/{animal_id}/weighings',status_code=201)
def add_weight(animal_id:int,data:WeightIn,request:Request,db:Session=Depends(get_db)):
    from .checks import weighing_warnings, require_confirmation
    from .calf import today_local
    animal=db.get(Animal,animal_id)
    if not animal: raise HTTPException(404,'Hayvan bulunamadı')
    if animal.status!='active':raise HTTPException(409,'Çıkışı yapılmış hayvana tartım girilemez.')
    if data.measured_at>today_local():raise HTTPException(422,'Tartım tarihi ileri bir tarih olamaz.')
    if data.measured_at<animal.arrival_date:raise HTTPException(422,'Tartım tarihi hayvanın giriş tarihinden önce olamaz.')
    previous=[(animal.arrival_date,animal.entry_weight_kg)]+[(w.measured_at,w.weight_kg) for w in db.scalars(select(Weighing).where(Weighing.animal_id==animal_id))]
    require_confirmation(request,weighing_warnings(animal,data.weight_kg,data.measured_at,previous))
    obj=Weighing(animal_id=animal_id,**data.model_dump());db.add(obj);db.commit();db.refresh(obj);return as_dict(obj)
@app.get('/api/animals/{animal_id}/weighings')
def get_weights(animal_id:int,db:Session=Depends(get_db)):
    if not db.get(Animal,animal_id):raise HTTPException(404,'Hayvan bulunamadı')
    rows=db.scalars(select(Weighing).where(Weighing.animal_id==animal_id).order_by(Weighing.measured_at)).all()
    authors=creator_map(db,'weighings',[r.id for r in rows])
    return [{**as_dict(x),'created_by':authors.get(x.id,'Eski kayıt')} for x in rows]

def parcel_code_key(code:str)->str:
    # Türkçe I/İ/ı/i ve büyük/küçük harf farkı aynı parseli ikinci kez açtırmasın.
    return ''.join(code.translate(str.maketrans({'İ':'i','I':'i','ı':'i'})).casefold().split())

def ensure_parcel_code_free(db,code:str,exclude_id:int|None=None):
    key=parcel_code_key(code)
    for other_id,other_code in db.execute(select(Field.id,Field.code)).all():
        if other_id!=exclude_id and parcel_code_key(other_code or '')==key:
            raise HTTPException(409,f'Parsel kodu zaten kayıtlı: {other_code}. Aynı parseli ikinci kez açmayın; gerekiyorsa farklı bir kod yazın.')

def field_area_warnings(area):
    from .checks import LIMITS, tr_kg
    return [f'Alan {tr_kg(area)} dekar; tek parsel için çok büyük. Binlik nokta / ondalık virgül yazımını kontrol edin.'] if area>LIMITS['field_max_decare'] else []

@app.post('/api/fields',status_code=201)
def add_field(data:FieldIn,request:Request,db:Session=Depends(get_db)):
    from .checks import require_confirmation
    ensure_parcel_code_free(db,data.code)
    require_confirmation(request,field_area_warnings(data.area_decare))
    obj=Field(**data.model_dump());db.add(obj);db.commit();db.refresh(obj);return as_dict(obj)
@app.get('/api/fields')
def get_fields(search:str='', db:Session=Depends(get_db)):
    rows=db.scalars(select(Field).order_by(Field.code)).all()
    if search.strip():
        term=search.strip().casefold()
        rows=[x for x in rows if any(term in str(v or '').casefold() for v in (x.ada_no,x.code,x.name))]
    return [as_dict(x) for x in rows]

PARCEL_IMAGE_DIR = Path(__file__).resolve().parents[1] / 'data' / 'parcel_images'
from fastapi import Form


async def _validated_parcel_image(file: UploadFile):
    """Gerçek dosya türü/boyutu doğrulanır, kullanıcı dosya adı saklanmaz."""
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, 'Görsel 10 MB sınırını aşıyor. Daha küçük bir görsel seçin.')
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise HTTPException(422, 'Arazi görseli için JPEG, PNG veya WEBP biçimini kullanın.')
            if image.width * image.height > 25_000_000:
                raise HTTPException(422, 'Görsel çözünürlüğü çok büyük. En fazla 25 milyon piksel kullanın.')
            image.load()
            image = image.convert('RGB')
            image.thumbnail((3600, 3600))
            normalized = io.BytesIO()
            image.save(normalized, format='JPEG', quality=87, optimize=True)
            return normalized.getvalue()
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(422, 'Görsel dosyası açılamadı. Geçerli bir fotoğraf seçin.') from error


def _write_new_parcel_image(content):
    """Yalnız bu istek için üretilen dosyayı oluşturur; kullanıcı dosyası üzerine yazmaz."""
    path = PARCEL_IMAGE_DIR / (uuid.uuid4().hex + '.jpg')
    created = False
    try:
        PARCEL_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as output:
            created = True
            output.write(content)
    except OSError as error:
        if created:
            _remove_failed_parcel_image(path)
        raise HTTPException(503, 'Arazi görseli kaydedilemedi. Klasör erişimini kontrol edip yeniden deneyin.') from error
    return path


def _remove_failed_parcel_image(path):
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        import logging
        logging.getLogger('kuzucu.erp').exception('Tamamlanamayan parsel işleminin yeni görseli temizlenemedi.')


@app.post('/api/fields/with-image', status_code=201)
async def add_field_with_image(code: str = Form(..., min_length=1, max_length=40),
                               name: str = Form(..., min_length=1, max_length=120),
                               area_decare: Decimal = Form(..., gt=0),
                               ada_no: str | None = Form(default=None, max_length=40),
                               file: UploadFile | None = File(default=None),
                               request: Request = None,
                               db: Session = Depends(get_db)):
    """Form ve fotoğraf birlikte doğrulanır; hata olduğunda parsel kaydı oluşmaz."""
    from sqlalchemy.exc import IntegrityError
    from pydantic import ValidationError
    try:
        data = FieldIn(code=code, name=name, area_decare=area_decare, ada_no=ada_no or None)
    except ValidationError as error:
        # Boşluktan ibaret kod veya fazla ondalık: Türkçe 422 mesajı, genel sunucu hatası değil.
        raise RequestValidationError(error.errors()) from error
    ensure_parcel_code_free(db, data.code)
    from .checks import require_confirmation
    require_confirmation(request, field_area_warnings(data.area_decare))
    content = await _validated_parcel_image(file) if file and file.filename else None
    new_path = None
    try:
        parcel = Field(**data.model_dump())
        db.add(parcel)
        db.flush()
        if content is not None:
            new_path = _write_new_parcel_image(content)
            parcel.satellite_image = new_path.name
        db.commit()
    except IntegrityError as error:
        db.rollback()
        _remove_failed_parcel_image(new_path)
        raise HTTPException(409, 'Bu parsel kodu zaten kayıtlı. Mevcut kaydı kontrol edin.') from error
    except Exception:
        db.rollback()
        _remove_failed_parcel_image(new_path)
        raise
    db.refresh(parcel)
    return as_dict(parcel)


@app.post('/api/fields/{field_id}/satellite-image')
async def upload_satellite_image(field_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    parcel = db.get(Field, field_id)
    if parcel is None:
        raise HTTPException(404, 'Parsel bulunamadı')
    content = await _validated_parcel_image(file)
    new_path = _write_new_parcel_image(content)
    try:
        parcel.satellite_image = new_path.name
        db.commit()
    except Exception:
        db.rollback()
        _remove_failed_parcel_image(new_path)
        raise
    # Önceki kullanıcı görseli silinmez; görsel değişimi geçmiş kayıtlarda izlenebilir.
    return {'field_id': field_id, 'image_url': f'/api/fields/{field_id}/satellite-image'}

@app.get('/api/fields/{field_id}/satellite-image')
def get_satellite_image(field_id:int,db:Session=Depends(get_db)):
    parcel=db.get(Field,field_id)
    if parcel is None or not parcel.satellite_image:
        raise HTTPException(404,'Bu parselde uydu görseli yok')
    path=PARCEL_IMAGE_DIR/Path(parcel.satellite_image).name
    if not path.is_file():raise HTTPException(404,'Parsel görseli dosyası bulunamadı')
    return FileResponse(path,media_type='image/jpeg')
@app.put('/api/fields/{field_id}')
def update_field(field_id:int,data:FieldIn,request:Request,db:Session=Depends(get_db)):
    from .checks import require_confirmation
    obj = db.get(Field,field_id)
    if obj is None:
        raise HTTPException(404,'Parsel bulunamadı')
    if data.area_decare!=obj.area_decare:require_confirmation(request,field_area_warnings(data.area_decare))
    # Yalnızca kod gerçekten değiştiyse kontrol et; eski mükerrer kayıtlar düzenlenebilsin.
    if parcel_code_key(data.code) != parcel_code_key(obj.code or ''):
        ensure_parcel_code_free(db,data.code,exclude_id=obj.id)
    for k,v in data.model_dump().items():
        setattr(obj,k,v)
    db.commit()
    db.refresh(obj)
    return as_dict(obj)
@app.post('/api/seasons',status_code=201)
def add_season(data:SeasonIn,db:Session=Depends(get_db)):
    if not db.get(Field,data.field_id):raise HTTPException(404,'Parsel bulunamadı')
    if db.scalar(select(CropSeason.id).where(CropSeason.field_id==data.field_id,CropSeason.year==data.year)) is not None:
        raise HTTPException(409,'Parselin bu yıl için sezonu zaten var')
    obj=CropSeason(**data.model_dump());db.add(obj);db.commit();db.refresh(obj);return as_dict(obj)
@app.get('/api/seasons')
def get_seasons(db:Session=Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(CropSeason).order_by(CropSeason.year.desc()))]

def ensure_item_free(db,code:str,name:str):
    # Stok Girişi ekranından hızlı ürün eklemede aynı ürün ikinci kez açılmasın.
    code_key=parcel_code_key(code);name_key=parcel_code_key(name)
    for other_code,other_name,other_unit in db.execute(select(Item.code,Item.name,Item.unit)).all():
        if parcel_code_key(other_code or '')==code_key:
            raise HTTPException(409,f'Ürün kodu zaten kayıtlı: {other_code} ({other_name}).')
        if parcel_code_key(other_name or '')==name_key:
            raise HTTPException(409,f'Bu adla ürün zaten kayıtlı: {other_name} ({other_unit}). Listeden seçin.')

@app.post('/api/items',status_code=201)
def add_item(data:ItemIn,db:Session=Depends(get_db)):
    ensure_item_free(db,data.code,data.name)
    obj=Item(**data.model_dump());db.add(obj);db.commit();db.refresh(obj);return as_dict(obj)
@app.get('/api/items')
def get_items(db:Session=Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(Item).order_by(Item.code))]
@app.post('/api/stock-movements',status_code=201)
def add_movement(data:MovementIn,db:Session=Depends(get_db)):
    if db.get_bind().dialect.name=='sqlite' and not db.in_transaction():db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    if data.type not in ('IN','OUT'):raise HTTPException(422,'Hareket türü Giriş veya Çıkış olmalı.')
    if not db.get(Item,data.item_id):raise HTTPException(404,'Ürün bulunamadı')
    moves=db.scalars(select(StockMovement).where(StockMovement.item_id==data.item_id)).all()
    balance=sum((m.quantity if m.type=='IN' else -m.quantity for m in moves), Decimal('0'))
    if data.type=='OUT' and Decimal(str(balance or 0)) < data.quantity:
        from .checks import tr_kg
        raise HTTPException(409,f'Stok yetersiz: elde {tr_kg(balance)}, çıkış {tr_kg(data.quantity)}. Stok eksiye düşeceği için kaydedilmedi; önce eksik girişi kontrol edin.')
    if data.reference.strip():
        duplicate=db.scalar(select(StockMovement.id).where(StockMovement.item_id==data.item_id, StockMovement.type==data.type, StockMovement.quantity==data.quantity, StockMovement.movement_date==data.movement_date, StockMovement.reference==data.reference.strip()))
        if duplicate is not None: raise HTTPException(409,'Aynı ürün, tarih, miktar ve belge numarasıyla stok hareketi zaten var. Mükerrer kaydı kontrol edin')
    from .finance import sync_stock_alerts
    obj=StockMovement(**data.model_dump());db.add(obj);sync_stock_alerts(db);db.commit();db.refresh(obj);return as_dict(obj)
def stock_effect(movement):
    return movement.quantity if movement.type == 'IN' else -movement.quantity

@app.put('/api/stock-movements/{movement_id}')
def edit_movement(movement_id: int, data: MovementUpdateIn, db: Session = Depends(get_db)):
    if db.get_bind().dialect.name=='sqlite' and not db.in_transaction():db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    movement = db.get(StockMovement, movement_id)
    if movement is None:
        raise HTTPException(404, 'Stok hareketi bulunamadı')
    from .finance import InvoiceLine, Invoice, sync_stock_alerts
    attached=db.scalar(select(InvoiceLine.id).join(Invoice,Invoice.id==InvoiceLine.invoice_id).where(
        ((InvoiceLine.posted_movement_id==movement_id)|(InvoiceLine.linked_movement_id==movement_id)),Invoice.status=='posted'))
    if movement.reference.startswith('FATURA:') or attached:
        raise HTTPException(409,'Bu hareket faturaya bağlı. Stok ve hesapların tutarlı kalması için Faturalar bölümünden düzeltin.')
    if data.type not in ('IN', 'OUT'):
        raise HTTPException(422, 'Hareket türü Giriş veya Çıkış olmalı.')
    if not db.get(Item, data.item_id):
        raise HTTPException(404, 'Ürün bulunamadı')
    if not data.reason.strip() or len(data.reason.strip()) < 3:
        raise HTTPException(422, 'Düzeltme nedeni en az üç karakter olmalı')
    before = {
        'item_id': movement.item_id, 'type': movement.type,
        'quantity': movement.quantity, 'movement_date': movement.movement_date,
        'reference': movement.reference or '',
    }
    # Degisiklik yapildiktan sonra etkilenen tum urunlerde negatif bakiye olusmamali.
    affected = {movement.item_id, data.item_id}
    for item_id in affected:
        others = db.scalars(select(StockMovement).where(
            StockMovement.item_id == item_id, StockMovement.id != movement_id)).all()
        balance = sum((stock_effect(x) for x in others), Decimal('0'))
        if item_id == data.item_id:
            balance += data.quantity if data.type == 'IN' else -data.quantity
        if balance < 0:
            raise HTTPException(409, 'Düzeltme negatif stok oluşturuyor; miktarı veya ürünü kontrol edin')
    for key in ('item_id','type','quantity','movement_date','reference'):
        setattr(movement, key, getattr(data, key))
    revision = StockMovementRevision(
        movement_id=movement_id,
        old_item_id=before['item_id'], new_item_id=data.item_id,
        old_type=before['type'], new_type=data.type,
        old_quantity=before['quantity'], new_quantity=data.quantity,
        old_movement_date=before['movement_date'], new_movement_date=data.movement_date,
        old_reference=before['reference'], new_reference=data.reference,
        reason=data.reason.strip(),
    )
    db.add(revision)
    sync_stock_alerts(db)
    db.commit()
    db.refresh(movement)
    return as_dict(movement)

@app.get('/api/stock-movements/{movement_id}/revisions')
def get_movement_revisions(movement_id: int, db: Session = Depends(get_db)):
    if db.get(StockMovement, movement_id) is None:
        raise HTTPException(404, 'Stok hareketi bulunamadı')
    revisions = db.scalars(select(StockMovementRevision).where(
        StockMovementRevision.movement_id == movement_id).order_by(StockMovementRevision.id.desc())).all()
    authors=creator_map(db,'stock_movement_revisions',[r.id for r in revisions])
    return [{**as_dict(x),'changed_by':authors.get(x.id,'Eski kayıt')} for x in revisions]

@app.post('/api/firms', status_code=201)
def add_firm(data: FirmIn, db: Session = Depends(get_db)):
    values = data.model_dump()
    values['name'] = values['name'].strip()
    values['tax_no'] = (values['tax_no'] or '').strip() or None
    if not values['name']:
        raise HTTPException(422, 'Firma adı boş olamaz')
    if values['tax_no'] and (not values['tax_no'].isdigit() or len(values['tax_no']) not in (10, 11)):
        raise HTTPException(422, 'Vergi no 10 veya 11 rakamdan oluşmalı')
    if values['tax_no']:
        unique(db, Firm, 'tax_no', values['tax_no'])
    obj = Firm(**values)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return as_dict(obj)

@app.get('/api/firms')
def get_firms(db: Session = Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(Firm).order_by(Firm.name, Firm.id))]

@app.put('/api/firms/{firm_id}')
def update_firm(firm_id: int, data: FirmIn, db: Session = Depends(get_db)):
    obj = db.get(Firm, firm_id)
    if obj is None:
        raise HTTPException(404, 'Firma bulunamadı')
    values = data.model_dump()
    values['name'] = values['name'].strip()
    values['tax_no'] = (values['tax_no'] or '').strip() or None
    if not values['name']:
        raise HTTPException(422, 'Firma adı boş olamaz')
    if values['tax_no'] and (not values['tax_no'].isdigit() or len(values['tax_no']) not in (10, 11)):
        raise HTTPException(422, 'Vergi no 10 veya 11 rakamdan oluşmalı')
    if values['tax_no'] and values['tax_no'] != obj.tax_no:
        unique(db, Firm, 'tax_no', values['tax_no'])
    for key, value in values.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return as_dict(obj)

@app.get('/api/stock-movements/history')
def get_stock_movement_history(db: Session = Depends(get_db)):
    # Sayisallari Decimal olarak hesaplar: gorsel binlik ayirici maliyet/stok miktarini degistirmez.
    items = db.scalars(select(Item).order_by(Item.name, Item.code)).all()
    groups = []
    unit_summaries = {}
    for item in items:
        moves = db.scalars(select(StockMovement).where(StockMovement.item_id == item.id).order_by(
            StockMovement.movement_date.desc(), StockMovement.id.desc())).all()
        incoming = sum((m.quantity for m in moves if m.type == 'IN'), Decimal('0'))
        outgoing = sum((m.quantity for m in moves if m.type == 'OUT'), Decimal('0'))
        actors = creator_map(db, 'stock_movements', [m.id for m in moves])
        groups.append({
            'item_id': item.id, 'code': item.code, 'name': item.name, 'unit': item.unit,
            'incoming': str(incoming), 'outgoing': str(outgoing), 'balance': str(incoming - outgoing),
            'movements': [{
                'id': m.id,
                'movement_date': m.movement_date.isoformat() if m.movement_date else (m.created_at.date().isoformat() if m.created_at else None),
                'type': m.type, 'quantity': str(m.quantity), 'reference': m.reference,
                'created_by': actors.get(m.id, 'Eski kayıt'),
            } for m in moves],
        })
        agg = unit_summaries.setdefault(item.unit, {'unit': item.unit, 'incoming': Decimal('0'), 'outgoing': Decimal('0')})
        agg['incoming'] += incoming
        agg['outgoing'] += outgoing
    return {
        'groups': groups,
        'unit_totals': [{
            'unit': r['unit'], 'incoming': str(r['incoming']),
            'outgoing': str(r['outgoing']), 'balance': str(r['incoming'] - r['outgoing']),
        } for r in sorted(unit_summaries.values(), key=lambda v: v['unit'])],
    }

@app.get('/api/stock')
def get_stock(db:Session=Depends(get_db)):
    items=db.scalars(select(Item).order_by(Item.code)).all()
    result=[]
    for item in items:
        moves=db.scalars(select(StockMovement).where(StockMovement.item_id==item.id)).all()
        balance=sum((m.quantity if m.type=='IN' else -m.quantity for m in moves),Decimal('0'))
        result.append({'item_id':item.id,'code':item.code,'name':item.name,'unit':item.unit,'balance':str(balance)})
    return result
