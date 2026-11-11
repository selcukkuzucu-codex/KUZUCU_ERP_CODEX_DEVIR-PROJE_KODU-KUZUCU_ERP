"""KUZUCU ERP pilot: animal health ledger, daily veterinary worklist and local printing.

This module records veterinarian-authorized protocols and observations. It never
prescribes treatment, determines dose, or changes a protocol automatically.
"""
import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
from datetime import date, datetime, timedelta
from html import escape as html_escape
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field as PField, field_validator, model_validator
from sqlalchemy import select, func, text, inspect, or_
from sqlalchemy.orm import Session

from .agenda import next_due_date
from .db import get_db
from .security import creator_map, current_user, allowed
from .models import Animal, HealthCase, HealthDailyLog, HealthCatalogEntry, HealthPrintRun, HealthPrintSettings, Pen, Reminder

router = APIRouter(prefix='/api/animal-health', tags=['Hayvan Sağlığı'])
TZ = ZoneInfo('Europe/Istanbul')
RECORD_TYPES = {'treatment', 'vaccination', 'observation'}
OUTCOMES = {'recovered', 'improved', 'unchanged', 'worsened', 'unknown'}
RESPONSES = {'improved', 'unchanged', 'worsened', 'not_evaluated'}


def today_local():
    return datetime.now(TZ).date()


def migrate_v015(engine):
    """Eski sağlık verilerini/onaylarını değiştirmeden süre alanını ekle."""
    inspector = inspect(engine)
    if not inspector.has_table('health_cases'):
        return
    if 'duration_days' not in {column['name'] for column in inspector.get_columns('health_cases')}:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE health_cases ADD COLUMN duration_days INTEGER'))


class HealthCaseIn(BaseModel):
    animal_id: int = PField(gt=0)
    record_type: str = 'treatment'
    condition_name: str = PField(min_length=1, max_length=140)
    symptoms: str = PField(default='', max_length=1500)
    product_name: str = PField(default='', max_length=180)
    treatment_name: str = PField(default='', max_length=180)
    repeat_review_confirmed: bool = False
    dosage_text: str = PField(default='', max_length=120)
    veterinarian: str = PField(default='', max_length=160)
    vet_approved: bool = False
    applications_per_day: int = PField(default=1, ge=1, le=6)
    duration_days: int | None = PField(default=None, gt=0, strict=True)
    start_date: date | None = None
    planned_end_date: date | None = None
    withdrawal_end_date: date | None = None
    notes: str = PField(default='', max_length=1500)

    @field_validator('condition_name')
    @classmethod
    def valid_name(cls, v):
        if not v.strip():
            raise ValueError('Hastalık, belirti veya kayıt adı boş olamaz')
        return v.strip()

    @field_validator('record_type')
    @classmethod
    def valid_type(cls, v):
        if v not in RECORD_TYPES:
            raise ValueError('Kayıt türü tedavi, aşı veya gözlem olmalıdır')
        return v

    @model_validator(mode='after')
    def validate_plan(self):
        if self.duration_days is None:
            if self.start_date is None or self.planned_end_date is None:
                raise ValueError('Tedavi süresini gün olarak girin')
            if self.planned_end_date < self.start_date:
                raise ValueError('Bitiş tarihi başlangıçtan önce olamaz')
            if self.withdrawal_end_date and self.withdrawal_end_date < self.start_date:
                raise ValueError('Arınma süresinin son tarihi başlangıçtan önce olamaz')
            if self.record_type != 'treatment' and self.applications_per_day != 1:
                raise ValueError('Aşı/gözlem kayıtlarında günlük uygulama sayısı 1 olmalıdır')
            if self.record_type != 'treatment' and self.planned_end_date != self.start_date:
                raise ValueError('Aşı ve gözlem kayıtları bir günlüktür; devam eden işlemleri ayrı kaydedin')
        if self.vet_approved and self.record_type in {'treatment', 'vaccination'} and not self.veterinarian.strip():
            raise ValueError('Onay veren veteriner hekimin adını girin')
        if not self.vet_approved and self.duration_days is None:
            self.repeat_review_confirmed = False
        return self


def _plan_payload(data: HealthCaseIn, original: HealthCase | None = None):
    """Süreli yeni formun gizlediği eski tıbbi bilgileri boş değerlerle silme."""
    payload = data.model_dump()
    if original is not None:
        for field in ('symptoms', 'veterinarian', 'vet_approved', 'withdrawal_end_date'):
            if field not in data.model_fields_set:
                payload[field] = getattr(original, field)
        if 'repeat_review_confirmed' not in data.model_fields_set:
            payload['repeat_review_confirmed'] = (
                original.repeat_review_confirmed
                if _name_key(original.product_name) == _name_key(data.product_name) else False)
    if data.duration_days is not None:
        payload['start_date'] = original.start_date if original is not None else today_local()
        try:
            payload['planned_end_date'] = payload['start_date'] + timedelta(days=data.duration_days - 1)
        except (OverflowError, ValueError) as exc:
            raise HTTPException(422, 'Tedavi süresi geçerli tarih sınırlarını aşıyor. Daha kısa bir süre girin.') from exc
    return payload


class HealthLogIn(BaseModel):
    performed_on: date
    performed_by: str = PField(min_length=1, max_length=120)
    observation: str = PField(default='', max_length=1200)
    response: str = 'not_evaluated'
    repeat_review_confirmed: bool = False

    @field_validator('performed_by')
    @classmethod
    def performer(cls, v):
        if not v.strip():
            raise ValueError('Uygulayan personel boş olamaz')
        return v.strip()

    @field_validator('response')
    @classmethod
    def valid_response(cls, v):
        if v not in RESPONSES:
            raise ValueError('Geçersiz günlük gözlem durumu')
        return v


class HealthCloseIn(BaseModel):
    outcome: str
    outcome_notes: str = PField(default='', max_length=1500)
    closed_date: date = PField(default_factory=today_local)

    @field_validator('outcome')
    @classmethod
    def valid_outcome(cls, v):
        if v not in OUTCOMES:
            raise ValueError('Geçerli bir sonuç seçin')
        return v


class PrintSettingsIn(BaseModel):
    daily_time: str = PField(default='07:00', pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    auto_generate: bool = True
    auto_print: bool = False
    printer_name: str = PField(default='', max_length=180)

    @field_validator('printer_name')
    @classmethod
    def safe_printer(cls, v):
        if '\x00' in v or '\n' in v:
            raise ValueError('Geçersiz yazıcı adı')
        return v.strip()


def get_case(db: Session, case_id: int):
    obj = db.get(HealthCase, case_id)
    if obj is None:
        raise HTTPException(404, 'Sağlık kaydı bulunamadı')
    return obj


def serialize_case(obj: HealthCase, db: Session | None = None):
    return {
        'id': obj.id, 'animal_id': obj.animal_id,
        'ear_tag': obj.animal.ear_tag if obj.animal else '',
        'farm_ear_tag': obj.animal.farm_ear_tag if obj.animal else None,
        'pen': obj.animal.pen.code if obj.animal and obj.animal.pen else '',
        'record_type': obj.record_type, 'condition_name': obj.condition_name,
        'symptoms': obj.symptoms, 'product_name': obj.product_name,
        'treatment_name': obj.treatment_name, 'repeat_review_confirmed': obj.repeat_review_confirmed,
        'dosage_text': obj.dosage_text, 'veterinarian': obj.veterinarian,
        'vet_approved': obj.vet_approved, 'applications_per_day': obj.applications_per_day,
        'duration_days': obj.duration_days,
        'start_date': obj.start_date.isoformat(),
        'planned_end_date': obj.planned_end_date.isoformat(),
        'withdrawal_end_date': obj.withdrawal_end_date.isoformat() if obj.withdrawal_end_date else None,
        'notes': obj.notes, 'status': obj.status, 'outcome': obj.outcome,
        'outcome_notes': obj.outcome_notes,
        'closed_date': obj.closed_date.isoformat() if obj.closed_date else None,
    }


class HealthCatalogIn(BaseModel):
    kind: str
    name: str = PField(min_length=1, max_length=180)

    @field_validator('kind')
    @classmethod
    def valid_kind(cls, v):
        if v not in {'medication', 'treatment'}:
            raise ValueError('Kayıt türü ilaç/aşı veya tedavi olmalıdır')
        return v

    @field_validator('name')
    @classmethod
    def valid_name(cls, v):
        value = ' '.join(v.split())
        if not value:
            raise ValueError('Ad boş olamaz')
        return value


def _name_key(value: str) -> str:
    # Türkçe İ / i ve metinsel boşluk değişikliklerini aynı anahtar say.
    return ' '.join(value.strip().split()).casefold().replace('\u0307', '')


def _remember_catalog(db: Session, kind: str, name: str):
    label = ' '.join((name or '').split())
    if not label:
        return None
    key = _name_key(label)
    existing = db.scalar(select(HealthCatalogEntry).where(
        HealthCatalogEntry.kind == kind, HealthCatalogEntry.name_key == key))
    if existing:
        return existing
    entry = HealthCatalogEntry(kind=kind, name=label, name_key=key)
    db.add(entry)
    # SQLite transaction içindeki diğer kayıtlarla beraber commit edilir.
    db.flush()
    return entry


def _catalog_from_case(db: Session, case: HealthCase):
    if case.record_type in {'treatment','vaccination'}:
        _remember_catalog(db, 'medication', case.product_name)
    if case.record_type == 'treatment':
        _remember_catalog(db, 'treatment', case.treatment_name)


@router.get('/catalog')
def health_catalog(db: Session = Depends(get_db)):
    stored = db.scalars(select(HealthCatalogEntry).order_by(HealthCatalogEntry.name)).all()
    result = {'medications': [], 'treatments': []}
    seen = {'medication': set(), 'treatment': set()}
    for e in stored:
        key = _name_key(e.name)
        if key not in seen[e.kind]:
            result['medications' if e.kind == 'medication' else 'treatments'].append(e.name)
            seen[e.kind].add(key)
    # Eski Mac sağlık kayıtlarında da ilaçların listede görünmesini sağla.
    for case in db.scalars(select(HealthCase)).all():
        for kind, val in (('medication', case.product_name if case.record_type in {'treatment','vaccination'} else ''),
                          ('treatment', case.treatment_name if case.record_type == 'treatment' else '')):
            name = ' '.join((val or '').split())
            if name and _name_key(name) not in seen[kind]:
                result['medications' if kind == 'medication' else 'treatments'].append(name)
                seen[kind].add(_name_key(name))
    result['medications'].sort(key=str.casefold)
    result['treatments'].sort(key=str.casefold)
    return result


@router.post('/catalog', status_code=201)
def add_health_catalog(data: HealthCatalogIn, db: Session = Depends(get_db)):
    entry = _remember_catalog(db, data.kind, data.name)
    db.commit()
    return {'kind': entry.kind, 'name': entry.name}


def _repeat_matches(db: Session, animal_id: int, product_name: str,
                    on: date, exclude_case_id: int | None = None):
    """Ayrı bir vakada GERÇEKTEN yapılan aynı isimli ilacın son 10 günü.

    Aynı tedavi planı içindeki veteriner onaylı günlük uygulamaları saymayız.
    """
    key = _name_key(product_name or '')
    if not key:
        return []
    q = (select(HealthDailyLog, HealthCase)
         .join(HealthCase, HealthDailyLog.case_id == HealthCase.id)
         .where(HealthCase.animal_id == animal_id,
                HealthCase.record_type.in_(['treatment','vaccination']),
                HealthDailyLog.performed_on >= on - timedelta(days=10),
                HealthDailyLog.performed_on <= on))
    if exclude_case_id is not None:
        q = q.where(HealthCase.id != exclude_case_id)
    matches_by_case = {}
    for log, case in db.execute(q).all():
        if _name_key(case.product_name) != key:
            continue
        prev = matches_by_case.get(case.id)
        if not prev or log.performed_on > prev['last_application']:
            matches_by_case[case.id] = dict(
                case_id=case.id, ear_tag=case.animal.ear_tag,
                product_name=case.product_name, last_application=log.performed_on,
                days_ago=(on-log.performed_on).days, treatment_name=case.treatment_name,
                veterinarian=case.veterinarian)
    return [dict(item, last_application=item['last_application'].isoformat())
            for item in sorted(matches_by_case.values(), key=lambda r: r['last_application'], reverse=True)]


def _repeat_conflict(matches):
    raise HTTPException(409, detail={
        'code': 'SAME_MEDICATION_WITHIN_10_DAYS',
        'message': 'UYARI: Bu hayvana aynı ilaç son 10 gün içinde başka bir tedavi kaydında uygulanmış. '
                   'Önceki kaydı kontrol edin; veteriner değerlendirmesi olmadan tekrar uygulamayın.',
        'matches': matches})


@router.get('/repeat-check')
def repeat_check(animal_id: int, product_name: str, on: date,
                 exclude_case_id: int | None = None, db: Session = Depends(get_db)):
    if not db.get(Animal, animal_id):
        raise HTTPException(404, 'Hayvan bulunamadı')
    matches = _repeat_matches(db, animal_id, product_name, on, exclude_case_id)
    return {'warning': bool(matches), 'matches': matches,
            'notice': 'Yalnızca aynı isimde ve kayıtlı olarak uygulanmış ilaçları karşılaştırır. '
                      'Aynı etken maddenin farklı ticari adlarını otomatik bulamaz.'}


@router.get('/cases')
def list_cases(animal_id: int | None = None, status: str | None = None,
               search: str = '', db: Session = Depends(get_db)):
    q = select(HealthCase).order_by(HealthCase.start_date.desc(), HealthCase.id.desc())
    if animal_id is not None:
        q = q.where(HealthCase.animal_id == animal_id)
    if status is not None:
        if status not in {'active', 'closed'}:
            raise HTTPException(422, 'Geçersiz durum')
        q = q.where(HealthCase.status == status)
    rows = db.scalars(q.limit(3000)).all()
    if search.strip():
        term = search.strip().casefold()
        rows = [r for r in rows if term in r.condition_name.casefold() or
                term in r.animal.ear_tag.casefold() or term in (r.animal.farm_ear_tag or '').casefold()
                or term in r.product_name.casefold()]
    actors=creator_map(db,'health_cases',[r.id for r in rows])
    return [{**serialize_case(r),'created_by':actors.get(r.id,'Eski kayıt')} for r in rows]


@router.post('/cases', status_code=201)
def add_case(data: HealthCaseIn, db: Session = Depends(get_db)):
    if not db.get(Animal, data.animal_id):
        raise HTTPException(404, 'Hayvan bulunamadı')
    payload = _plan_payload(data)
    if data.record_type in {'treatment','vaccination'}:
        repeats = _repeat_matches(db, data.animal_id, data.product_name, payload['start_date'])
        if repeats and (data.duration_days is not None or data.vet_approved) and not data.repeat_review_confirmed:
            _repeat_conflict(repeats)
    obj = HealthCase(**payload)
    db.add(obj)
    _catalog_from_case(db, obj)
    db.commit()
    db.refresh(obj)
    _refresh_existing_daily_pdf(db)
    return serialize_case(obj)


@router.put('/cases/{case_id}')
def edit_case(case_id: int, data: HealthCaseIn, db: Session = Depends(get_db)):
    obj = get_case(db, case_id)
    if obj.status != 'active':
        raise HTTPException(409, 'Kapanmış tedavi planı değiştirilemez; yeni kayıt oluşturun')
    if obj.animal_id != data.animal_id:
        raise HTTPException(409, 'Sağlık kaydı başka hayvana taşınamaz')
    payload = _plan_payload(data, obj)
    logs = db.scalars(select(HealthDailyLog).where(HealthDailyLog.case_id == case_id)).all()
    if logs:
        if any(x.application_no > data.applications_per_day for x in logs):
            raise HTTPException(409, 'Uygulama sayısı kaydedilmiş günlük uygulama numaralarından az olamaz')
        if obj.record_type != data.record_type:
            raise HTTPException(409, 'Uygulaması yapılmış kaydın türü değiştirilemez')
        if any(not(payload['start_date'] <= x.performed_on <= payload['planned_end_date']) for x in logs):
            raise HTTPException(409, 'Yeni tedavi süresi geçmiş uygulama kayıtlarını dışarıda bırakıyor. Süreyi bu kayıtları kapsayacak şekilde girin.')
    if data.record_type in {'treatment','vaccination'}:
        repeats = _repeat_matches(db, data.animal_id, data.product_name, payload['start_date'], exclude_case_id=case_id)
        if repeats and (payload['duration_days'] is not None or payload['vet_approved']) and not payload['repeat_review_confirmed']:
            _repeat_conflict(repeats)
    for k, v in payload.items():
        setattr(obj, k, v)
    _catalog_from_case(db, obj)
    db.commit()
    db.refresh(obj)
    _refresh_existing_daily_pdf(db)
    return serialize_case(obj)


@router.get('/cases/{case_id}/logs')
def get_case_logs(case_id: int, db: Session = Depends(get_db)):
    get_case(db, case_id)
    rows = db.scalars(select(HealthDailyLog).where(HealthDailyLog.case_id == case_id)
                      .order_by(HealthDailyLog.performed_on.desc())).all()
    actors=creator_map(db,'health_daily_logs',[r.id for r in rows])
    return [{'created_by':actors.get(r.id,'Eski kayıt'),'id': r.id, 'case_id': r.case_id, 'performed_on': r.performed_on.isoformat(),
             'application_no': r.application_no, 'performed_by': r.performed_by, 'observation': r.observation,
             'response': r.response, 'created_at': r.created_at.isoformat() if r.created_at else None}
            for r in rows]


@router.post('/cases/{case_id}/logs', status_code=201)
def log_daily_action(case_id: int, data: HealthLogIn, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    if case.status != 'active':
        raise HTTPException(409, 'Kapanmış sağlık kaydına uygulama girilemez')
    if data.performed_on > today_local():
        raise HTTPException(422, 'Gelecek tarihli uygulama yapılmış olarak işaretlenemez')
    if not case.start_date <= data.performed_on <= case.planned_end_date:
        raise HTTPException(409, 'Tarih veteriner planı dışında. Önce planı kontrol edip güncelleyin')
    if case.record_type != 'observation' and not case.vet_approved and case.duration_days is None:
        raise HTTPException(409, 'Tedavi/aşı için veteriner onayı kaydedilmeden uygulandı işaretlenemez')
    # Bir vakadaki planlı tekrar dozlar ayrı tedavi sayılmaz; sadece ilk uygulamada kontrol et.
    already_applied_here = db.scalar(select(HealthDailyLog.id).where(HealthDailyLog.case_id == case_id).limit(1))
    if not already_applied_here and case.record_type in {'treatment','vaccination'}:
        repeats = _repeat_matches(db, case.animal_id, case.product_name, data.performed_on,
                                  exclude_case_id=case_id)
        reviewed = data.repeat_review_confirmed and (case.vet_approved or case.duration_days is not None)
        if repeats and not (case.repeat_review_confirmed or reviewed):
            _repeat_conflict(repeats)
        if repeats and reviewed:
            case.repeat_review_confirmed = True
    day_logs = db.scalars(select(HealthDailyLog).where(
        HealthDailyLog.case_id == case_id, HealthDailyLog.performed_on == data.performed_on)).all()
    if len(day_logs) >= case.applications_per_day:
        raise HTTPException(409, 'Seçilen gün için sağlık planında tanımlı uygulama sayısına ulaşıldı')
    used = {x.application_no for x in day_logs}
    next_no = next(i for i in range(1,case.applications_per_day+1) if i not in used)
    log = HealthDailyLog(case_id=case_id, application_no=next_no, **data.model_dump(exclude={'repeat_review_confirmed'}))
    db.add(log)
    db.commit()
    db.refresh(log)
    _refresh_existing_daily_pdf(db)
    return {'id': log.id, 'case_id': case_id, 'performed_on': log.performed_on.isoformat(), 'application_no': log.application_no}


@router.post('/cases/{case_id}/close')
def close_case(case_id: int, data: HealthCloseIn, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    if case.status != 'active':
        raise HTTPException(409, 'Bu sağlık kaydı zaten kapalı')
    if data.closed_date < case.start_date or data.closed_date > today_local():
        raise HTTPException(422, 'Kapanış tarihi başlangıçtan önce veya gelecekte olamaz')
    if data.outcome in {'recovered','improved'} and case.record_type == 'treatment':
        applied = db.scalar(select(func.count()).select_from(HealthDailyLog).where(
            HealthDailyLog.case_id == case_id, HealthDailyLog.performed_on <= data.closed_date)) or 0
        if not applied:
            raise HTTPException(409, 'Olumlu tedavi sonucu yazmak için en az bir gerçek uygulama kaydı gerekli')
    case.status = 'closed'
    case.outcome = data.outcome
    case.outcome_notes = data.outcome_notes
    case.closed_date = data.closed_date
    db.commit()
    db.refresh(case)
    _refresh_existing_daily_pdf(db)
    return serialize_case(case)


def daily_report_data(db: Session, on: date):
    cases = db.scalars(select(HealthCase).where(
        HealthCase.status == 'active', HealthCase.start_date <= on,
        or_(HealthCase.duration_days.is_(None), HealthCase.planned_end_date >= on))
        .order_by(HealthCase.start_date, HealthCase.id)).all()
    ids = [row.id for row in cases]
    day_logs = db.scalars(select(HealthDailyLog).where(
        HealthDailyLog.case_id.in_(ids), HealthDailyLog.performed_on == on)).all() if ids else []
    logged = {}
    for log in day_logs:
        logged.setdefault(log.case_id,[]).append(log)
    records = []
    for row in cases:
        if row.planned_end_date < on:
            schedule_status = 'review_expired'
        elif len(logged.get(row.id,[])) >= row.applications_per_day:
            schedule_status = 'done'
        elif len(logged.get(row.id,[])):
            schedule_status = 'partially_done'
        elif row.record_type != 'observation' and not row.vet_approved and row.duration_days is None:
            schedule_status = 'awaiting_approval'
        else:
            schedule_status = 'due'
        records.append({
            'case_id': row.id, 'animal_id': row.animal_id,
            'ear_tag': row.animal.ear_tag, 'pen': row.animal.pen.code if row.animal.pen else '',
            'farm_ear_tag': row.animal.farm_ear_tag,
            'record_type': row.record_type, 'condition_name': row.condition_name,
            'product_name': row.product_name, 'treatment_name': row.treatment_name, 'dosage_text': row.dosage_text,
            'veterinarian': row.veterinarian, 'vet_approved': row.vet_approved,
            'applications_per_day': row.applications_per_day, 'performed_count': len(logged.get(row.id,[])),
            'duration_days': row.duration_days, 'notes': row.notes,
            'start_date': row.start_date.isoformat(), 'planned_end_date': row.planned_end_date.isoformat(),
            'status': schedule_status,
            'performed_by': ', '.join(v.performed_by for v in logged.get(row.id,[])),
            'response': logged[row.id][-1].response if row.id in logged else '',
        })
    reminders = []
    for row in db.scalars(select(Reminder).where(Reminder.is_active == True)).all():  # noqa: E712
        next_date = next_due_date(row)
        if next_date is not None and next_date <= on:
            reminders.append({
                'id': row.id, 'title': row.title, 'category': row.category,
                'notes': row.notes, 'remind_time': row.remind_time,
                'scheduled_for': next_date.isoformat(), 'overdue': next_date < on,
            })
    reminders.sort(key=lambda r: (r['scheduled_for'],r['remind_time'],r['id']))
    return {'date': on.isoformat(), 'cases': records, 'reminders': reminders,
            'totals': {
                'scheduled': len(records),
                'due': sum(r['status'] == 'due' for r in records),
                'done': sum(r['status'] == 'done' for r in records),
                'partially_done': sum(r['status'] == 'partially_done' for r in records),
                'review': sum(r['status'] == 'review_expired' for r in records),
                'awaiting_approval': sum(r['status'] == 'awaiting_approval' for r in records),
                'reminders': len(reminders),
            }}


@router.get('/daily')
def get_daily(request:Request,on: date = Query(default_factory=today_local), db: Session = Depends(get_db)):
    report=daily_report_data(db,on)
    if not allowed(current_user(request),'ajanda.view'):
        report['reminders']=[]
        report['totals']['reminders']=0
    return report


@router.get('/insights')
def historical_insights(condition: str = Query(min_length=2, max_length=140), db: Session = Depends(get_db)):
    target = ' '.join(condition.casefold().split())
    rows = db.scalars(select(HealthCase).where(
        HealthCase.record_type == 'treatment', HealthCase.status == 'closed',
        HealthCase.vet_approved == True)).all()  # noqa: E712
    matches = [r for r in rows if ' '.join(r.condition_name.casefold().split()) == target]
    # Olumlu deneyim verisini göstermek otomatik recete veya etkinlik kaniti degildir.
    groups = {}
    for row in matches:
        key = row.product_name.strip().casefold() or '(ürün belirtilmemiş)'
        bucket = groups.setdefault(key, {'product_name': row.product_name or 'Ürün belirtilmemiş',
            'total': 0, 'positive': 0, 'recovered': 0, 'worsened': 0, 'latest_date': None,
            'veterinarians': set()})
        bucket['total'] += 1
        if row.outcome in {'recovered','improved'}:
            bucket['positive'] += 1
        if row.outcome == 'recovered': bucket['recovered'] += 1
        if row.outcome == 'worsened': bucket['worsened'] += 1
        if row.veterinarian: bucket['veterinarians'].add(row.veterinarian)
        if row.closed_date and (bucket['latest_date'] is None or bucket['latest_date'] < row.closed_date):
            bucket['latest_date'] = row.closed_date
    results = [{**v, 'veterinarians': sorted(v['veterinarians']),
                'latest_date': v['latest_date'].isoformat() if v['latest_date'] else None}
               for v in groups.values()]
    results.sort(key=lambda r: (-r['total'],-r['positive'],r['product_name']))
    return {'condition': condition.strip(), 'completed_vet_approved_cases': len(matches),
            'past_protocols': results,
            'warning': 'Bu rakamlar işletme içi gözlemdir; ilacın etkinliğini kanıtlamaz. Doz, ilaç, süre ve uygulama kararını veteriner hekim vermelidir.'}


@router.get('/print-settings')
def get_print_settings(db: Session = Depends(get_db)):
    row = db.get(HealthPrintSettings, 1)
    if row is None:
        return {'daily_time': '07:00', 'auto_generate': True, 'auto_print': False, 'printer_name': ''}
    return {'daily_time': row.daily_time, 'auto_generate': row.auto_generate,
            'auto_print': row.auto_print, 'printer_name': row.printer_name}


@router.put('/print-settings')
def update_print_settings(data: PrintSettingsIn, db: Session = Depends(get_db)):
    row = db.get(HealthPrintSettings, 1)
    if row is None:
        row = HealthPrintSettings(id=1)
        db.add(row)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return get_print_settings(db)


def report_dir():
    # Mac launcher starts in KUZUCU_ERP directory; allow custom path for deployments/tests.
    folder = Path(os.getenv('KUZUCU_REPORT_DIR', 'raporlar/saglik')).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def pdf_font_name():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    name = 'KUZUCU-TR'
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    candidates = (
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/Library/Fonts/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
    )
    for path in candidates:
        if Path(path).is_file():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return 'Helvetica'


def make_daily_pdf(db: Session, on: date):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

    data = daily_report_data(db, on)
    path = report_dir() / f'{on.isoformat()}_hayvan_sagligi_gunluk.pdf'
    font = pdf_font_name()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=13*mm,
                            rightMargin=13*mm, topMargin=15*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('KZTitle', parent=styles['Title'], fontName=font, fontSize=14,
                                  leading=19, textColor=colors.HexColor('#123a30'), spaceAfter=7)
    section_style = ParagraphStyle('KZHead', fontName=font, fontSize=10.5, leading=14,
                                    textColor=colors.HexColor('#123a30'), spaceBefore=10, spaceAfter=6)
    normal = ParagraphStyle('KZCell', fontName=font, fontSize=7.5, leading=10)
    muted = ParagraphStyle('KZSmall', parent=normal, fontSize=7.5, textColor=colors.HexColor('#545f58'))
    heading = ParagraphStyle('KZTH', parent=normal, textColor=colors.white, fontSize=7.3)
    def P(value, style=normal):
        return Paragraph(html_escape(str(value or '—')).replace('\n','<br/>'), style)
    story = [Paragraph('KUZUCU ERP - GÜNLÜK HAYVAN SAĞLIĞI / İŞ LİSTESİ', title_style),
             P(f'Tarih: {on.strftime("%d.%m.%Y")}   |   Tedavi / aşı kayıtları: {data["totals"]["scheduled"]}   |   Ajanda işi: {data["totals"]["reminders"]}', muted),
             Paragraph('Tedavi / aşı ve kontrol listesi', section_style)]
    statuses = {'due':'YAPILACAK', 'done':'YAPILDI', 'partially_done':'KISMEN YAPILDI', 'awaiting_approval':'VETERİNER ONAYI BEKLİYOR',
                'review_expired':'PLAN SÜRESİ BİTTİ - VETERİNER KONTROLÜ'}
    types = {'treatment':'Tedavi', 'vaccination':'Aşı', 'observation':'Gözlem'}
    rows = [[P(x,heading) for x in ['Küpe / Grup', 'Tür', 'Hastalık / durum', 'Plan / ilaç', 'Tarih aralığı', 'Durum']]]
    for entry in data['cases']:
        plan = ' / '.join(value for value in (entry['treatment_name'], entry['product_name']) if value.strip()) or '—'
        if entry['dosage_text'] and (entry['vet_approved'] or entry['duration_days'] is not None):
            plan += '\n' + entry['dosage_text']
        rows.append([P(entry['ear_tag']+' / '+entry['pen']), P(types.get(entry['record_type'])),
                     P(entry['condition_name']), P(plan),
                     P(date.fromisoformat(entry['start_date']).strftime('%d.%m.%Y')+' - '+date.fromisoformat(entry['planned_end_date']).strftime('%d.%m.%Y')),
                     P(statuses.get(entry['status'], 'DURUM BİLGİSİ') + f' ({entry["performed_count"]}/{entry["applications_per_day"]})')])
    if len(rows) == 1:
        rows.append([P('Bugün için açık sağlık planı yok.')]+['']*5)
    t = Table(rows, colWidths=[31*mm,17*mm,34*mm,38*mm,36*mm,27*mm], repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#174b38')),
                           ('VALIGN',(0,0),(-1,-1),'TOP'), ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#d8e1d9')),
                           ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white]),
                           ('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6)]))
    story.extend([t, Paragraph('Ajanda ve diğer günlük işler', section_style)])
    rem_rows = [[P(x,heading) for x in ['Saat','Bölüm','Yapılacak iş','Not / durum']]]
    for entry in data['reminders']:
        rem_rows.append([P(entry['remind_time']),P(entry['category']),P(entry['title']),
                         P((entry['notes'] or '')+('\nGECİKMİŞ' if entry['overdue'] else ''))])
    if len(rem_rows) == 1:
        rem_rows.append([P('—'),P('—'),P('Bugün bekleyen ajanda işi yok.'),P('—')])
    t2 = Table(rem_rows, colWidths=[21*mm,28*mm,64*mm,70*mm], repeatRows=1, hAlign='LEFT')
    t2.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#174b38')),
                            ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#d8e1d9')),
                            ('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white]),
                            ('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6)]))
    story.extend([t2, Spacer(1,10*mm),
        P('Önemli: Bu belge bilgilendirme ve görev takibi içindir. Veteriner onayı olmadan ilaç, doz veya tedavi süresi değiştirilmez.', muted),
        Spacer(1,5*mm), P('Uygulayan: __________________________       Kontrol eden: __________________________', muted)])
    def footer(canvas, document):
        canvas.setFont(font,7)
        canvas.setFillColor(colors.HexColor('#5d6f63'))
        canvas.drawRightString(A4[0]-13*mm, 8*mm, f'Sayfa {document.page}')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    path.with_suffix('.sha256').write_text(_report_fingerprint(data), encoding='ascii')
    return path


def _report_fingerprint(data):
    """PDF'nin veri anlık görüntüsü; yeni kayıt ve plan/log değişikliği dosyayı yeniler."""
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _pdf_matches_data(path: Path, data):
    try:
        return path.is_file() and path.with_suffix('.sha256').read_text(encoding='ascii').strip() == _report_fingerprint(data)
    except (OSError, UnicodeError):
        return False


def _refresh_existing_daily_pdf(db: Session):
    """Hazırlanmış bugünkü çıktıyı güncel tut; yazıcıyı kendiliğinden çağırma."""
    day = today_local()
    record = db.scalar(select(HealthPrintRun).where(HealthPrintRun.report_date == day))
    if record is None:
        return
    settings = db.get(HealthPrintSettings, 1)
    if settings is not None and not settings.auto_generate and not settings.auto_print:
        return
    path = report_dir() / f'{day.isoformat()}_hayvan_sagligi_gunluk.pdf'
    try:
        if not _pdf_matches_data(path, daily_report_data(db, day)):
            record_generation(db, day, make_daily_pdf(db, day))
    except Exception:
        # İşletme kaydı zaten kalıcıdır; yazdırma dosyası sorunu kaydı başarısız gibi göstermesin.
        logging.getLogger('kuzucu.erp').exception('Sağlık kaydı korundu ancak mevcut günlük PDF yenilenemedi.')


def record_generation(db: Session, day: date, path: Path):
    record = db.scalar(select(HealthPrintRun).where(HealthPrintRun.report_date == day))
    if not record:
        record = HealthPrintRun(report_date=day, pdf_path=str(path))
        db.add(record)
    else:
        record.pdf_path = str(path)
        record.generated_at = datetime.now(TZ)
    db.commit()
    return record


@router.get('/daily.pdf')
def daily_pdf(on: date = Query(default_factory=today_local), db: Session = Depends(get_db)):
    path = make_daily_pdf(db, on)
    record_generation(db, on, path)
    return FileResponse(path, media_type='application/pdf', filename=path.name)


def send_to_printer(path: Path, printer_name: str = ''):
    command = ['lp']
    if printer_name:
        command += ['-d', printer_name]
    command.append(str(path))
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError('Yazdırma aracı bulunamadı. İşletim sisteminin yazıcı ayarlarını kontrol edin.') from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Yazıcı yanıt vermedi') from exc
    if result.returncode:
        logging.getLogger('kuzucu.erp').warning('Yazdırma sistemi hatası: %s', (result.stderr or result.stdout)[:1000])
        raise RuntimeError('Yazdırma tamamlanamadı. Yazıcı bağlantısını ve ayarlarını kontrol edin.')
    return 'Yazdırma işi yazıcıya gönderildi.'


@router.post('/print-today')
def print_today(db: Session = Depends(get_db)):
    settings = db.get(HealthPrintSettings, 1)
    path = make_daily_pdf(db, today_local())
    record = record_generation(db, today_local(), path)
    try:
        result = send_to_printer(path, settings.printer_name if settings else '')
    except RuntimeError as exc:
        logging.getLogger('kuzucu.erp').warning('Sağlık çıktısı yazdırılamadı: %s', exc)
        record.print_error = 'Yazdırma tamamlanamadı. Yazıcı bağlantısını ve ayarlarını kontrol edin.'
        db.commit()
        raise HTTPException(503, record.print_error) from exc
    record.printed_at = datetime.now(TZ)
    record.print_error = ''
    db.commit()
    return {'message': result, 'path': str(path)}


@router.get('/print-status')
def get_print_status(db: Session = Depends(get_db)):
    record = db.scalar(select(HealthPrintRun).order_by(HealthPrintRun.report_date.desc()))
    return {'report_date': record.report_date.isoformat() if record else None,
            'pdf_path': record.pdf_path if record else None,
            'printed_at': record.printed_at.isoformat() if record and record.printed_at else None,
            'print_error': 'Yazdırma tamamlanamadı. Yazıcı bağlantısını ve ayarlarını kontrol edin.' if record and record.print_error else ''}


def scheduled_daily_tick(engine):
    """App açık kaldığı sürece günlük dosyayı üretir; yazıcıyı yalnızca opt-in ile çağırır."""
    day = today_local()
    from sqlalchemy.orm import Session as DirectSession
    with DirectSession(engine) as db:
        settings = db.get(HealthPrintSettings, 1)
        trigger = settings.daily_time if settings else '07:00'
        current = datetime.now(TZ)
        if current.strftime('%H:%M') < trigger:
            return
        if settings is not None and not settings.auto_generate and not settings.auto_print:
            return
        path = report_dir() / f'{day.isoformat()}_hayvan_sagligi_gunluk.pdf'
        record = db.scalar(select(HealthPrintRun).where(HealthPrintRun.report_date == day))
        data = daily_report_data(db, day)
        if record is None or not _pdf_matches_data(path, data):
            path = make_daily_pdf(db, day)
            record = record_generation(db, day, path)
        if settings is not None and settings.auto_print and record.printed_at is None and not record.print_error:
            try:
                send_to_printer(path, settings.printer_name)
                record.printed_at = datetime.now(TZ)
            except RuntimeError as exc:
                logging.getLogger('kuzucu.erp').warning('Otomatik sağlık çıktısı yazdırılamadı: %s', exc)
                record.print_error = 'Yazdırma tamamlanamadı. Yazıcı bağlantısını ve ayarlarını kontrol edin.'
            db.commit()


async def daily_worker(engine):
    """Sadece uygulama çalışırken tetiklenir; işletim sistemi kapalıyken çalışmaz."""
    await asyncio.sleep(10)
    while True:
        try:
            await asyncio.to_thread(scheduled_daily_tick, engine)
        except Exception as exc:
            # Hatalar sunucuyu düşürmez, günlük PDF ekranından tekrar denenebilir.
            print(f'KUZUCU ERP günlük sağlık raporu oluşturulamadı: {exc}', flush=True)
        await asyncio.sleep(60)
