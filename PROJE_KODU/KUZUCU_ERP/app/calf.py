"""Buzagi giris/cikis, mama-yem takibi ve toplu performans analizi.

ADG (gunluk ortalama canli agirlik artisi) = (cikis kg - giris kg) / gun.
Katsayi = cikis kg / giris kg; bu yalnizca agirlik oranidir,
biyolojik ya da tedavi tavsiyesi degildir.
"""
import csv
import io
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import Calf, CalfConsumption, CalfWeighing
from .security import creator_map

router = APIRouter(prefix='/api/calves', tags=['Buzağılar'])

class CalfIn(BaseModel):
    tr_ear_tag: str = Field(min_length=1,max_length=60)
    farm_ear_tag: str | None = Field(default=None,max_length=60)
    sex: str
    breed: str = Field(default='Belirtilmedi',max_length=80)
    birth_date: date | None = None
    entry_date: date
    entry_kg: Decimal = Field(gt=0)
    planned_days: int = Field(default=45,ge=1,le=365)
    batch_code: str = Field(default='',max_length=80)
    notes: str = Field(default='',max_length=1200)

    @model_validator(mode='after')
    def check(self):
        if self.sex not in ('male','female'):
            raise ValueError('Cinsiyet erkek veya dişi olmalı')
        self.tr_ear_tag = self.tr_ear_tag.strip()
        if not self.tr_ear_tag:
            raise ValueError('TR küpe no boş olamaz')
        self.farm_ear_tag = (self.farm_ear_tag or '').strip() or None
        self.batch_code = self.batch_code.strip()
        if self.birth_date and self.birth_date > self.entry_date:
            raise ValueError('Doğum tarihi giriş tarihinden sonra olamaz')
        return self

class ConsumptionIn(BaseModel):
    consumed_on: date
    milk_kg: Decimal = Field(default=Decimal('0'),ge=0)
    feed_kg: Decimal = Field(default=Decimal('0'),ge=0)
    notes: str = Field(default='',max_length=400)

    @model_validator(mode='after')
    def check(self):
        if self.milk_kg == 0 and self.feed_kg == 0:
            raise ValueError('Mama/süt veya yem tüketiminden en az biri sıfırdan büyük olmalı')
        return self

class ExitIn(BaseModel):
    exit_date: date
    exit_kg: Decimal = Field(gt=0)

class WeighingIn(BaseModel):
    measured_on: date
    weight_kg: Decimal = Field(gt=0)

class BulkExitRow(BaseModel):
    calf_id: int = Field(gt=0)
    exit_kg: Decimal = Field(gt=0)

class BulkExitIn(BaseModel):
    exit_group_no: str = Field(default='',max_length=80)
    exit_date: date
    entries: list[BulkExitRow] = Field(min_length=1,max_length=500)

def dec(v):
    return str(v) if v is not None else None

def round3(v):
    return str(Decimal(v).quantize(Decimal('.001'),rounding=ROUND_HALF_UP))

def case_metrics(c: Calf):
    if not c.exit_date or c.exit_kg is None:
        return {'days':None,'gain_kg':None,'adg_kg_day':None,'exit_entry_ratio':None,'gain_percent':None}
    days=(c.exit_date-c.entry_date).days
    gain=c.exit_kg-c.entry_kg
    return {'days':days,'gain_kg':round3(gain),
            'adg_kg_day':round3(gain/Decimal(days)) if days else None,
            'exit_entry_ratio':round3(c.exit_kg/c.entry_kg),
            'gain_percent':round3(gain/c.entry_kg*Decimal(100))}

def calf_dict(c:Calf, db:Session|None=None, totals=None):
    d={'id':c.id,'tr_ear_tag':c.tr_ear_tag,'farm_ear_tag':c.farm_ear_tag,'sex':c.sex,
       'breed':c.breed,'birth_date':c.birth_date.isoformat() if c.birth_date else None,
       'entry_date':c.entry_date.isoformat(), 'entry_kg':dec(c.entry_kg),
       'planned_days':c.planned_days,'expected_exit':date.fromordinal(c.entry_date.toordinal()+c.planned_days).isoformat(),
       'batch_code':c.batch_code,'exit_group_no':c.exit_group_no,'notes':c.notes,
       'exit_date':c.exit_date.isoformat() if c.exit_date else None,'exit_kg':dec(c.exit_kg),
       'status':'exited' if c.exit_date else 'active',**case_metrics(c)}
    if totals is not None:
        d['milk_total_kg'],d['feed_total_kg']=dec(totals[0]),dec(totals[1])
    elif db is not None:
        total=db.execute(select(func.coalesce(func.sum(CalfConsumption.milk_kg),0),
                                func.coalesce(func.sum(CalfConsumption.feed_kg),0)).where(CalfConsumption.calf_id==c.id)).one()
        d['milk_total_kg'],d['feed_total_kg']=dec(total[0]),dec(total[1])
    return d

def bulk_consumption_totals(db, ids):
    if not ids:return {}
    results=db.execute(select(CalfConsumption.calf_id,func.sum(CalfConsumption.milk_kg),
                   func.sum(CalfConsumption.feed_kg)).where(CalfConsumption.calf_id.in_(ids))
                   .group_by(CalfConsumption.calf_id)).all()
    return {row[0]:(row[1],row[2]) for row in results}


def get_calf(db,calf_id):
    calf=db.get(Calf,calf_id)
    if not calf:raise HTTPException(404,'Buzağı bulunamadı')
    return calf

def validate_unique(db, data, exclude_id=None):
    for attr,label in [('tr_ear_tag','TR küpe'),('farm_ear_tag','İşletme küpe')]:
        val=getattr(data,attr)
        if val and db.scalar(select(Calf.id).where(getattr(Calf,attr)==val,Calf.id!=exclude_id)) is not None:
            raise HTTPException(409,f'{label} numarası zaten kayıtlı')

@router.post('',status_code=201)
def add(data:CalfIn, db:Session=Depends(get_db)):
    validate_unique(db,data)
    obj=Calf(**data.model_dump());db.add(obj);db.commit();db.refresh(obj)
    return calf_dict(obj,db)

@router.get('')
def list_calves(search:str='',status:str='',batch_code:str='',db:Session=Depends(get_db)):
    if status not in ('','active','exited'):raise HTTPException(422,'Geçersiz durum')
    q=select(Calf).order_by(Calf.entry_date.desc(),Calf.id.desc())
    if batch_code:q=q.where(Calf.batch_code==batch_code)
    if status=='active':q=q.where(Calf.exit_date.is_(None))
    if status=='exited':q=q.where(Calf.exit_date.is_not(None))
    rows=db.scalars(q.limit(10000)).all()
    if search.strip():
        s=search.strip().casefold()
        rows=[r for r in rows if any(s in str(x or '').casefold() for x in (r.tr_ear_tag,r.farm_ear_tag,r.batch_code,r.breed))]
    totals=bulk_consumption_totals(db,[r.id for r in rows])
    actors=creator_map(db,'calves',[r.id for r in rows])
    return [{**calf_dict(r,totals=totals.get(r.id,(Decimal(0),Decimal(0)))),'created_by':actors.get(r.id,'Eski kayıt')} for r in rows]

@router.put('/{calf_id}')
def edit(calf_id:int,data:CalfIn,db:Session=Depends(get_db)):
    obj=get_calf(db,calf_id)
    validate_unique(db,data,exclude_id=calf_id)
    if obj.exit_date and data.entry_date >= obj.exit_date:
        raise HTTPException(409,'Giriş tarihi mevcut çıkış tarihinden önce olmalı')
    if db.scalar(select(CalfConsumption.id).where(CalfConsumption.calf_id==calf_id,
                                        CalfConsumption.consumed_on<data.entry_date)) is not None:
        raise HTTPException(409,'Yeni giriş tarihi mevcut tüketim kayıtlarını dışarıda bırakıyor')
    for k,v in data.model_dump().items():setattr(obj,k,v)
    db.commit();db.refresh(obj);return calf_dict(obj,db)

@router.post('/bulk-exit')
def bulk_exit(data:BulkExitIn,db:Session=Depends(get_db)):
    if data.exit_date>date.today():
        raise HTTPException(422,'Gelecek tarihli toplu çıkış tamamlanmış olarak kaydedilemez')
    ids=[x.calf_id for x in data.entries]
    if len(ids)!=len(set(ids)):
        raise HTTPException(422,'Toplu çıkışta aynı buzağı birden çok kez seçildi')
    calves={x.id:x for x in db.scalars(select(Calf).where(Calf.id.in_(ids)))}
    if len(calves)!=len(ids):
        raise HTTPException(404,'Seçilen buzağılardan biri bulunamadı; hiçbir kayıt değiştirilmedi')
    last_consumptions=dict(db.execute(select(CalfConsumption.calf_id,func.max(CalfConsumption.consumed_on))
                                .where(CalfConsumption.calf_id.in_(ids)).group_by(CalfConsumption.calf_id)).all())
    last_weighings=dict(db.execute(select(CalfWeighing.calf_id,func.max(CalfWeighing.measured_on))
                                .where(CalfWeighing.calf_id.in_(ids)).group_by(CalfWeighing.calf_id)).all())
    for row in data.entries:
        obj=calves[row.calf_id]
        if obj.exit_date:
            raise HTTPException(409,f'{obj.tr_ear_tag} zaten çıkış yapmış; hiçbir kayıt değiştirilmedi')
        if data.exit_date<=obj.entry_date:
            raise HTTPException(422,f'{obj.tr_ear_tag} için çıkış tarihi girişten sonra olmalı')
        if (last_consumptions.get(obj.id) and data.exit_date<last_consumptions[obj.id]) or \
           (last_weighings.get(obj.id) and data.exit_date<last_weighings[obj.id]):
            raise HTTPException(409,f'{obj.tr_ear_tag} için çıkış tarihi kaydedilmiş tartım/tüketimden önce')
    for row in data.entries:
        calves[row.calf_id].exit_date=data.exit_date
        calves[row.calf_id].exit_kg=row.exit_kg
        calves[row.calf_id].exit_group_no=data.exit_group_no.strip()
    db.commit()
    return {'count':len(data.entries),'exit_date':data.exit_date.isoformat(),'exited_ids':ids}


@router.post('/{calf_id}/exit')
def exit_calf(calf_id:int,data:ExitIn,db:Session=Depends(get_db)):
    obj=get_calf(db,calf_id)
    if data.exit_date<=obj.entry_date:
        raise HTTPException(422,'Çıkış tarihi giriş tarihinden en az bir gün sonra olmalı')
    if data.exit_date>date.today():
        raise HTTPException(422,'Gelecek tarihli çıkış tamamlanmış olarak kaydedilemez')
    latest=db.scalar(select(func.max(CalfConsumption.consumed_on)).where(CalfConsumption.calf_id==calf_id))
    latest_weight=db.scalar(select(func.max(CalfWeighing.measured_on)).where(CalfWeighing.calf_id==calf_id))
    if (latest and data.exit_date<latest) or (latest_weight and data.exit_date<latest_weight):
        raise HTTPException(409,'Çıkış tarihi kayıtlı tüketim veya tartımdan önce olamaz')
    obj.exit_date=data.exit_date;obj.exit_kg=data.exit_kg
    db.commit();db.refresh(obj);return calf_dict(obj,db)

@router.get('/{calf_id}/consumptions')
def get_consumptions(calf_id:int,db:Session=Depends(get_db)):
    get_calf(db,calf_id)
    return [{'id':r.id,'consumed_on':r.consumed_on.isoformat(),'milk_kg':dec(r.milk_kg),
             'feed_kg':dec(r.feed_kg),'notes':r.notes} for r in db.scalars(select(CalfConsumption)
             .where(CalfConsumption.calf_id==calf_id).order_by(CalfConsumption.consumed_on.desc()))]

def check_consumption_date(obj, consumed_on):
    if consumed_on<obj.entry_date or (obj.exit_date and consumed_on>obj.exit_date):
        raise HTTPException(422,'Tüketim günü buzağının giriş–çıkış aralığında olmalı')
    if consumed_on>date.today():
        raise HTTPException(422,'Gelecek günün tüketimi gerçekleşmiş olarak kaydedilemez')

@router.post('/{calf_id}/consumptions',status_code=201)
def add_consumption(calf_id:int,data:ConsumptionIn,db:Session=Depends(get_db)):
    obj=get_calf(db,calf_id);check_consumption_date(obj,data.consumed_on)
    if db.scalar(select(CalfConsumption.id).where(CalfConsumption.calf_id==calf_id,
             CalfConsumption.consumed_on==data.consumed_on)) is not None:
        raise HTTPException(409,'Bu gün için kayıt var; Düzenle işlemini kullanın')
    r=CalfConsumption(calf_id=calf_id,**data.model_dump())
    db.add(r);db.commit();db.refresh(r);return {'id':r.id,'consumed_on':r.consumed_on.isoformat()}

@router.put('/{calf_id}/consumptions/{row_id}')
def update_consumption(calf_id:int,row_id:int,data:ConsumptionIn,db:Session=Depends(get_db)):
    obj=get_calf(db,calf_id);check_consumption_date(obj,data.consumed_on)
    r=db.get(CalfConsumption,row_id)
    if not r or r.calf_id!=calf_id:raise HTTPException(404,'Tüketim kaydı bulunamadı')
    dupe=db.scalar(select(CalfConsumption.id).where(CalfConsumption.calf_id==calf_id,
                     CalfConsumption.consumed_on==data.consumed_on,CalfConsumption.id!=row_id))
    if dupe is not None:raise HTTPException(409,'Bu gün için başka bir tüketim kaydı var')
    for k,v in data.model_dump().items():setattr(r,k,v)
    db.commit();return {'id':r.id,'consumed_on':r.consumed_on.isoformat()}

@router.get('/{calf_id}/weighings')
def get_weighings(calf_id:int,db:Session=Depends(get_db)):
    get_calf(db,calf_id)
    return [{'id':r.id,'measured_on':r.measured_on.isoformat(),'weight_kg':dec(r.weight_kg)} for r in
            db.scalars(select(CalfWeighing).where(CalfWeighing.calf_id==calf_id)
                       .order_by(CalfWeighing.measured_on.desc()))]

@router.post('/{calf_id}/weighings',status_code=201)
def add_weighing(calf_id:int,data:WeighingIn,db:Session=Depends(get_db)):
    obj=get_calf(db,calf_id)
    if data.measured_on<obj.entry_date or (obj.exit_date and data.measured_on>obj.exit_date) or data.measured_on>date.today():
        raise HTTPException(422,'Tartım tarihi buzağının kayıtlı döneminde ve bugün veya öncesinde olmalı')
    if db.scalar(select(CalfWeighing.id).where(CalfWeighing.calf_id==calf_id,
               CalfWeighing.measured_on==data.measured_on)) is not None:
        raise HTTPException(409,'Bu gün için tartım zaten var')
    obj2=CalfWeighing(calf_id=calf_id,**data.model_dump());db.add(obj2);db.commit();db.refresh(obj2)
    return {'id':obj2.id,'measured_on':obj2.measured_on.isoformat(),'weight_kg':dec(obj2.weight_kg)}


def build_exit_report(db:Session, batch_code:str='', exit_from:date|None=None,exit_to:date|None=None,exit_group_no:str=''):
    if exit_from and exit_to and exit_from>exit_to:raise HTTPException(422,'Başlangıç tarihi bitiş tarihinden sonra olamaz')
    q=select(Calf).where(Calf.exit_date.is_not(None)).order_by(Calf.exit_date.desc(),Calf.id.desc())
    if batch_code:q=q.where(Calf.batch_code==batch_code)
    if exit_group_no:q=q.where(Calf.exit_group_no==exit_group_no)
    if exit_from:q=q.where(Calf.exit_date>=exit_from)
    if exit_to:q=q.where(Calf.exit_date<=exit_to)
    all_rows=db.scalars(q.limit(10000)).all()
    totals=bulk_consumption_totals(db,[r.id for r in all_rows])
    rows=[calf_dict(r,totals=totals.get(r.id,(Decimal(0),Decimal(0)))) for r in all_rows]
    total_in=sum((r.entry_kg for r in all_rows),Decimal(0))
    total_out=sum((r.exit_kg for r in all_rows),Decimal(0))
    animal_days=sum((r.exit_date-r.entry_date).days for r in all_rows)
    total_gain=total_out-total_in
    summary={'count':len(rows),'total_entry_kg':round3(total_in),'total_exit_kg':round3(total_out),
             'total_gain_kg':round3(total_gain),'total_animal_days':animal_days,
             'weighted_adg_kg_day':round3(total_gain/Decimal(animal_days)) if animal_days else None,
             'overall_exit_entry_ratio':round3(total_out/total_in) if total_in else None,
             'overall_gain_percent':round3(total_gain/total_in*100) if total_in else None}
    return {'batch_code':batch_code,'exit_group_no':exit_group_no,'exit_from':str(exit_from) if exit_from else None,
            'exit_to':str(exit_to) if exit_to else None,'rows':rows,'summary':summary}

@router.get('/exit-report')
def exit_report(batch_code:str='',exit_from:date|None=None,exit_to:date|None=None,exit_group_no:str='',db:Session=Depends(get_db)):
    return build_exit_report(db,batch_code,exit_from,exit_to,exit_group_no)

@router.get('/exit-report.csv')
def exit_report_csv(batch_code:str='',exit_from:date|None=None,exit_to:date|None=None,exit_group_no:str='',db:Session=Depends(get_db)):
    result=build_exit_report(db,batch_code,exit_from,exit_to,exit_group_no)
    buffer=io.StringIO();writer=csv.writer(buffer,delimiter=';')
    writer.writerow(['Toplu Çıkış No','TR Küpe','İşletme Küpe','Cinsiyet','Giriş Tarihi','Çıkış Tarihi','Gün','Giriş kg','Çıkış kg','Artış kg','Günlük Artış kg/gün','Çıkış/Giriş Katsayı','Artış %','Mama/Süt kg','Yem kg'])
    def safe(s):
        # CSV formül enjeksiyonunu engelle: Excel hücrelerinde baştaki işaretler.
        s=str(s or '')
        return "'"+s if s[:1] in '=+-@\t\r' else s
    for r in result['rows']:
        writer.writerow([safe(r['exit_group_no']),safe(r['tr_ear_tag']),safe(r['farm_ear_tag']),r['sex'],r['entry_date'],r['exit_date'],r['days'],
                         r['entry_kg'],r['exit_kg'],r['gain_kg'],r['adg_kg_day'],r['exit_entry_ratio'],r['gain_percent'],r['milk_total_kg'],r['feed_total_kg']])
    s=result['summary'];writer.writerow(['GENEL TOPLAM','','','','','','',s['total_entry_kg'],s['total_exit_kg'],s['total_gain_kg'],s['weighted_adg_kg_day'],s['overall_exit_entry_ratio'],s['overall_gain_percent']])
    data='\ufeff'+buffer.getvalue()
    return StreamingResponse(iter([data.encode('utf-8')]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="buzagi_toplu_cikis.csv"'})
