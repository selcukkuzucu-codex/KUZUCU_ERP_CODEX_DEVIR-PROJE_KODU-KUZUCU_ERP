"""Pilot yerel ajanda: uygulama açık olduğunda hatırlatır, arka planda bildirim göndermez."""
import calendar
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field as PField, field_validator
from sqlalchemy import select, inspect, text
from sqlalchemy.orm import Session
from .db import get_db
from .models import Reminder

router=APIRouter(prefix='/api/reminders',tags=['Ajanda'])
LOCAL_TZ=ZoneInfo('Europe/Istanbul')
ALLOWED_CATEGORIES={'Genel','Tarım','Besi','Buzağı','Stok','Personel','Finans'}
FREQUENCIES={'once','daily','weekly','monthly'}

class ReminderIn(BaseModel):
    title: str = PField(min_length=1,max_length=180)
    notes: str = PField(default='',max_length=1000)
    category: str = PField(default='Genel')
    frequency: str = PField(default='once')
    interval_count: int = PField(default=1, ge=1, le=1000, strict=True)
    start_date: date
    remind_time: str = PField(default='09:00',pattern=r'^([01]\d|2[0-3]):[0-5]\d$')

    @field_validator('title')
    @classmethod
    def title_not_blank(cls,v):
        if not v.strip(): raise ValueError('Hatırlatma başlığı boş olamaz')
        return v.strip()

    @field_validator('category')
    @classmethod
    def category_allowed(cls,v):
        if v not in ALLOWED_CATEGORIES: raise ValueError('Geçerli kategori seçiniz')
        return v

    @field_validator('frequency')
    @classmethod
    def frequency_allowed(cls,v):
        if v not in FREQUENCIES: raise ValueError('Tekrar günlük, haftalık, aylık veya tek seferlik olmalı')
        return v

def month_at(start:date,n:int)->date:
    total=start.year*12+(start.month-1)+n
    year,month=divmod(total,12)
    month+=1
    day=min(start.day,calendar.monthrange(year,month)[1])
    return date(year,month,day)

def migrate_v015(engine):
    """Eski hatırlatmaları aralık 1 olarak koruyan, yeniden çalıştırılabilir geçiş."""
    schema=inspect(engine)
    if not schema.has_table('reminders'):
        return
    if 'interval_count' not in {column['name'] for column in schema.get_columns('reminders')}:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE reminders ADD COLUMN interval_count INTEGER NOT NULL DEFAULT 1'))

def next_due_date(row:Reminder)->date|None:
    if not row.is_active: return None
    if row.frequency=='once':
        return None if row.last_completed_date else row.start_date
    earliest=max(row.start_date,row.last_completed_date+timedelta(days=1)) if row.last_completed_date else row.start_date
    interval=getattr(row,'interval_count',1) or 1
    if row.frequency in ('daily','weekly'):
        stride=interval*(7 if row.frequency=='weekly' else 1)
        delta=(earliest-row.start_date).days
        return row.start_date + timedelta(days=max(0,(delta+stride-1)//stride)*stride)
    if row.frequency=='monthly':
        elapsed=max(0,(earliest.year-row.start_date.year)*12+earliest.month-row.start_date.month)
        periods=elapsed//interval
        result=month_at(row.start_date,periods*interval)
        while result<earliest:
            periods+=1
            result=month_at(row.start_date,periods*interval)
        return result
    return None

def serialize(row:Reminder,now:datetime|None=None):
    now=now or datetime.now(LOCAL_TZ)
    next_date=next_due_date(row)
    next_dt=datetime.combine(next_date,time.fromisoformat(row.remind_time),tzinfo=LOCAL_TZ) if next_date else None
    due=bool(next_dt and next_dt<=now)
    status='paused' if not row.is_active else ('completed' if row.frequency=='once' and row.last_completed_date else ('due' if due else 'upcoming'))
    return {'id':row.id,'title':row.title,'notes':row.notes,'category':row.category,
            'frequency':row.frequency,'interval_count':getattr(row,'interval_count',1) or 1,'start_date':row.start_date.isoformat(),
            'remind_time':row.remind_time,'is_active':row.is_active,
            'last_completed_date':row.last_completed_date.isoformat() if row.last_completed_date else None,
            'next_due_date':next_date.isoformat() if next_date else None,
            'due':due,'status':status}

def fetch_or_404(db:Session,id:int)->Reminder:
    row=db.get(Reminder,id)
    if not row: raise HTTPException(404,'Hatırlatma bulunamadı')
    return row

@router.get('')
def list_reminders(db:Session=Depends(get_db)):
    now=datetime.now(LOCAL_TZ)
    data=[serialize(r,now) for r in db.scalars(select(Reminder).order_by(Reminder.id.desc()))]
    return sorted(data,key=lambda x:(x['next_due_date'] is None,x['next_due_date'] or '9999',x['remind_time'],x['id']))

@router.get('/due')
def due_reminders(db:Session=Depends(get_db)):
    now=datetime.now(LOCAL_TZ)
    return [r for row in db.scalars(select(Reminder)) if (r:=serialize(row,now))['due']]

@router.post('',status_code=201)
def create_reminder(data:ReminderIn,db:Session=Depends(get_db)):
    row=Reminder(**data.model_dump())
    db.add(row);db.commit();db.refresh(row)
    return serialize(row)

@router.put('/{reminder_id}')
def edit_reminder(reminder_id:int,data:ReminderIn,db:Session=Depends(get_db)):
    row=fetch_or_404(db,reminder_id)
    previous=(row.start_date,row.frequency,row.remind_time,row.interval_count)
    for k,v in data.model_dump().items():setattr(row,k,v)
    # Bir hatırlatmanın programı değişirse yeni zaman çizelgesi başlasın.
    if previous!=(data.start_date,data.frequency,data.remind_time,data.interval_count):row.last_completed_date=None
    db.commit();db.refresh(row)
    return serialize(row)

@router.post('/{reminder_id}/complete')
def complete_reminder(reminder_id:int,db:Session=Depends(get_db)):
    row=fetch_or_404(db,reminder_id)
    if not row.is_active: raise HTTPException(409,'Pasif hatırlatma tamamlanamaz')
    if row.frequency=='once' and row.last_completed_date: raise HTTPException(409,'Bu hatırlatma zaten tamamlandı')
    today=datetime.now(LOCAL_TZ).date()
    if row.last_completed_date==today: raise HTTPException(409,'Bu hatırlatma bugün tamamlandı')
    if row.start_date>today: raise HTTPException(409,'Başlangıç tarihi henüz gelmedi')
    if next_due_date(row)>today: raise HTTPException(409,'Sıradaki hatırlatma tarihi henüz gelmedi')
    row.last_completed_date=today
    db.commit();db.refresh(row)
    return serialize(row)

class ActiveIn(BaseModel):
    is_active: bool

@router.patch('/{reminder_id}/active')
def toggle_reminder(reminder_id:int,data:ActiveIn,db:Session=Depends(get_db)):
    row=fetch_or_404(db,reminder_id)
    row.is_active=data.is_active
    db.commit();db.refresh(row)
    return serialize(row)

@router.delete('/{reminder_id}',status_code=204)
def delete_reminder(reminder_id:int,db:Session=Depends(get_db)):
    row=fetch_or_404(db,reminder_id)
    db.delete(row);db.commit()
