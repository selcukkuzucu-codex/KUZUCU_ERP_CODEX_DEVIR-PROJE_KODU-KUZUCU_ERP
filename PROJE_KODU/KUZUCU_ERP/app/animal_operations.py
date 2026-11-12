"""Hayvan kimliği arama ve tümüyle başarılı/tümüyle reddedilen toplu işlemler."""
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import csv
import io
import re
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, get_db
from .models import Animal, Pen, Weighing, utc_now
from .security import allowed, current_user, need

router = APIRouter(prefix='/api/animal-operations', tags=['Toplu hayvan işlemleri'])
REASONS = {'slaughter': 'Kesim', 'death': 'Ölüm', 'sale': 'Satış'}


class AnimalExit(Base):
    __tablename__ = 'animal_exits'
    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey('animals.id'), unique=True, index=True)
    exit_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str] = mapped_column(String(240), default='')
    tr_ear_tag: Mapped[str] = mapped_column(String(60))
    farm_ear_tag: Mapped[str | None] = mapped_column(String(60), nullable=True)
    group_no: Mapped[str] = mapped_column(String(80))
    exit_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    __table_args__ = (
        CheckConstraint("reason IN ('slaughter','death','sale')", name='animal_exit_reason_valid'),
        CheckConstraint('exit_kg IS NULL OR exit_kg > 0', name='animal_exit_weight_positive'),
    )


class AnimalGroupTransfer(Base):
    __tablename__ = 'animal_group_transfers'
    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey('animals.id'), index=True)
    transferred_on: Mapped[date] = mapped_column(Date)
    old_pen_id: Mapped[int] = mapped_column(ForeignKey('pens.id'))
    new_pen_id: Mapped[int] = mapped_column(ForeignKey('pens.id'))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    __table_args__ = (UniqueConstraint('animal_id', 'transferred_on', 'new_pen_id', name='animal_transfer_once'),)


def today_local():
    return datetime.now(ZoneInfo('Europe/Istanbul')).date()


def tag_parts(value):
    """Kimlikleri sayıya dönüştürmez; baştaki sıfırlar aynen korunur."""
    if isinstance(value, str):
        return [part.strip() for part in re.split(r'[,;\n]+', value) if part.strip()]
    return [str(part).strip() for part in value if str(part).strip()]


class LookupInput(BaseModel):
    tags: str = Field(min_length=1, max_length=40000)
    active_only: bool = True


class WeighingEntry(BaseModel):
    animal_id: int = Field(gt=0)
    weight_kg: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class BulkWeighings(BaseModel):
    measured_at: date
    entries: list[WeighingEntry] = Field(min_length=1, max_length=1000)


class TransferEntry(BaseModel):
    animal_id: int = Field(gt=0)
    pen_id: int = Field(gt=0)


class BulkTransfers(BaseModel):
    transferred_on: date
    entries: list[TransferEntry] = Field(min_length=1, max_length=1000)


class NewAnimalEntry(BaseModel):
    tr_ear_tag: str = Field(min_length=1, max_length=60)
    farm_ear_tag: str | None = Field(default=None, max_length=60)
    birth_date: date | None = None
    sex: str | None = None
    breed: str = Field(default='Belirtilmedi', max_length=80)
    entry_weight_kg: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    pen_id: int = Field(gt=0)

    @field_validator('tr_ear_tag', 'farm_ear_tag')
    @classmethod
    def single_tag(cls, value):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if any(c in value for c in ',;\n\r'):
            raise ValueError('Bir hayvan kartına yalnızca tek küpe numarası yazın.')
        return value

    @field_validator('sex')
    @classmethod
    def valid_sex(cls, value):
        if value not in (None, 'male', 'female'):
            raise ValueError('Cinsiyet erkek veya dişi olmalıdır.')
        return value


class BulkNewAnimals(BaseModel):
    arrival_date: date
    entries: list[NewAnimalEntry] = Field(min_length=1, max_length=1000)


class ExitEntry(BaseModel):
    animal_id: int = Field(gt=0)
    exit_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)


class BulkExits(BaseModel):
    exit_date: date
    reason: str
    destination: str = Field(default='', max_length=240)
    entries: list[ExitEntry] = Field(min_length=1, max_length=1000)

    @field_validator('reason')
    @classmethod
    def valid_reason(cls, value):
        if value not in REASONS:
            raise ValueError('Çıkış nedeni kesim, ölüm veya satış olmalıdır.')
        return value


def _need_lookup(request):
    user = current_user(request)
    if not any(allowed(user, key) for key in (
        'hayvanlar.kart.view', 'hayvanlar.kart.create', 'hayvanlar.kart.edit',
        'hayvanlar.tartim.view', 'hayvanlar.tartim.create', 'hayvanlar.saglik.view',
    )):
        raise HTTPException(403, 'Hayvan aramak için yetkiniz bulunmuyor.')


def animal_data(animal, pens):
    return {
        'id': animal.id, 'tr_ear_tag': animal.ear_tag, 'ear_tag': animal.ear_tag,
        'farm_ear_tag': animal.farm_ear_tag, 'breed': animal.breed, 'sex': animal.sex,
        'arrival_date': str(animal.arrival_date), 'entry_weight_kg': str(animal.entry_weight_kg),
        'pen_id': animal.pen_id, 'group_no': pens.get(animal.pen_id, ''),
        'status': animal.status, 'status_label': 'Aktif' if animal.status == 'active' else 'Çıkışı yapılmış',
    }


def resolve_tags(db, tags, active_only=True):
    requested = tag_parts(tags)
    if not requested:
        raise HTTPException(422, 'En az bir küpe numarası yazın.')
    if len(requested) > 1000 or any(len(x) > 60 for x in requested):
        raise HTTPException(422, 'Bir işlemde en fazla 1.000 geçerli küpe numarası kullanılabilir.')
    normalized = {x.lower() for x in requested}
    animals = db.scalars(select(Animal).where(or_(
        func.lower(Animal.ear_tag).in_(normalized), func.lower(Animal.farm_ear_tag).in_(normalized)
    ))).all()
    by_tag = {}
    for animal in animals:
        for tag in {animal.ear_tag, animal.farm_ear_tag} - {None, ''}:
            bucket = by_tag.setdefault(tag.lower(), [])
            if not any(previous.id == animal.id for previous in bucket):
                bucket.append(animal)
    pens = dict(db.execute(select(Pen.id, Pen.code)).all())
    rows, warnings, seen = [], [], set()
    for value in requested:
        candidates = by_tag.get(value.lower(), [])
        if not candidates:
            warnings.append({'tag': value, 'code': 'unknown', 'message': 'Bu küpe numarasıyla kayıtlı hayvan bulunamadı.'})
        elif len(candidates) != 1:
            warnings.append({'tag': value, 'code': 'ambiguous', 'message': 'Bu numara birden fazla hayvanla eşleşiyor; TR veya işletme küpesini açıkça kontrol edin.'})
        else:
            animal = candidates[0]
            if animal.id in seen:
                warnings.append({'tag': value, 'code': 'duplicate', 'message': 'Bu hayvan listeye zaten eklenmiş; ikinci kez eklenmedi.'})
            elif active_only and animal.status != 'active':
                warnings.append({'tag': value, 'code': 'inactive', 'message': 'Bu hayvanın çıkışı yapılmış; aktif hayvan işlemlerine eklenemez.'})
            else:
                seen.add(animal.id)
                rows.append({**animal_data(animal, pens), 'input_tag': value})
    return {'rows': rows, 'warnings': warnings, 'valid': not warnings, 'count': len(rows)}


@router.post('/lookup')
def lookup(data: LookupInput, request: Request, db: Session = Depends(get_db)):
    _need_lookup(request)
    return resolve_tags(db, data.tags, data.active_only)


@router.get('/groups')
def groups(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    if not any(allowed(user, key) for key in ('hayvanlar.kart.create', 'hayvanlar.kart.edit', 'hayvanlar.padok.view')):
        raise HTTPException(403, 'Grup listesini görme yetkiniz bulunmuyor.')
    return [{'id': p.id, 'code': p.code, 'capacity': p.capacity}
            for p in db.scalars(select(Pen).order_by(Pen.code))]


def _active_batch(db, entries, on):
    ids = [x.animal_id for x in entries]
    if len(set(ids)) != len(ids):
        raise HTTPException(409, 'Aynı hayvan aynı toplu işlemde iki kez bulunamaz.')
    if on > today_local():
        raise HTTPException(422, 'İşlem tarihi gelecekte olamaz.')
    found = {a.id: a for a in db.scalars(select(Animal).where(Animal.id.in_(ids))).all()}
    for animal_id in ids:
        animal = found.get(animal_id)
        if animal is None:
            raise HTTPException(404, 'Listedeki hayvanlardan biri bulunamadı; hiçbir işlem kaydedilmedi.')
        if animal.status != 'active':
            raise HTTPException(409, f'{animal.ear_tag} küpeli hayvanın çıkışı yapılmış; hiçbir işlem kaydedilmedi.')
        if on < animal.arrival_date:
            raise HTTPException(422, f'{animal.ear_tag} için işlem tarihi giriş tarihinden önce olamaz.')
    return found


def _commit(db):
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, 'Bu işlem daha önce kaydedilmiş veya kayıtlar çakışıyor. Hiçbir kısmi işlem kaydedilmedi.') from error


@router.post('/bulk-weighings', status_code=201)
def bulk_weighings(data: BulkWeighings, request: Request, db: Session = Depends(get_db)):
    need(request, 'hayvanlar.tartim.create')
    _active_batch(db, data.entries, data.measured_at)
    for row in data.entries:
        duplicate = db.scalar(select(Weighing.id).where(Weighing.animal_id == row.animal_id,
                              Weighing.measured_at == data.measured_at, Weighing.weight_kg == row.weight_kg))
        if duplicate is not None:
            raise HTTPException(409, 'Aynı hayvan, tarih ve kilo ile tartım zaten kayıtlı; hiçbir satır kaydedilmedi.')
    for row in data.entries:
        db.add(Weighing(animal_id=row.animal_id, measured_at=data.measured_at, weight_kg=row.weight_kg))
    _commit(db)
    return {'count': len(data.entries), 'message': 'Seçilen hayvanların tartımları kaydedildi.'}


@router.post('/bulk-transfer')
def bulk_transfer(data: BulkTransfers, request: Request, db: Session = Depends(get_db)):
    need(request, 'hayvanlar.kart.edit')
    animals = _active_batch(db, data.entries, data.transferred_on)
    target_ids = {row.pen_id for row in data.entries}
    pens = {p.id: p for p in db.scalars(select(Pen).where(Pen.id.in_(target_ids))).all()}
    counts = Counter(dict(db.execute(select(Animal.pen_id, func.count(Animal.id)).where(
                     Animal.status == 'active').group_by(Animal.pen_id)).all()))
    for row in data.entries:
        animal = animals[row.animal_id]
        if row.pen_id not in pens:
            raise HTTPException(404, 'Hedef gruplardan biri bulunamadı; hiçbir hayvan taşınmadı.')
        if animal.pen_id == row.pen_id:
            raise HTTPException(409, f'{animal.ear_tag} küpeli hayvan zaten seçilen grupta.')
        latest = db.scalar(select(func.max(AnimalGroupTransfer.transferred_on)).where(
                           AnimalGroupTransfer.animal_id == animal.id))
        if latest and data.transferred_on < latest:
            raise HTTPException(422, 'Grup değişim tarihi önceki değişimden önce olamaz.')
        counts[animal.pen_id] -= 1
        counts[row.pen_id] += 1
    if any(counts[pen_id] > pen.capacity for pen_id, pen in pens.items()):
        raise HTTPException(409, 'İşlem sonunda hedef grup kapasitesi aşılıyor; hiçbir hayvan taşınmadı.')
    for row in data.entries:
        animal = animals[row.animal_id]
        db.add(AnimalGroupTransfer(animal_id=animal.id, transferred_on=data.transferred_on,
                                  old_pen_id=animal.pen_id, new_pen_id=row.pen_id))
        animal.pen_id = row.pen_id
    _commit(db)
    return {'count': len(data.entries), 'message': 'Seçilen hayvanların grup değişimleri kaydedildi.'}


@router.post('/bulk-create', status_code=201)
def bulk_create(data: BulkNewAnimals, request: Request, db: Session = Depends(get_db)):
    need(request, 'hayvanlar.kart.create')
    if data.arrival_date > today_local():
        raise HTTPException(422, 'Giriş tarihi gelecekte olamaz.')
    tr_tags, farm_tags = [], []
    pens = {p.id: p for p in db.scalars(select(Pen)).all()}
    incoming = Counter()
    for row in data.entries:
        if not row.tr_ear_tag:
            raise HTTPException(422, 'Her hayvan için TR küpe numarası gereklidir.')
        tr_tags.append(row.tr_ear_tag.lower())
        if row.farm_ear_tag:
            farm_tags.append(row.farm_ear_tag.lower())
        if row.birth_date and row.birth_date > data.arrival_date:
            raise HTTPException(422, 'Doğum tarihi giriş tarihinden sonra olamaz.')
        if row.pen_id not in pens:
            raise HTTPException(404, 'Seçilen gruplardan biri bulunamadı.')
        incoming[row.pen_id] += 1
    if len(set(tr_tags)) != len(tr_tags) or len(set(farm_tags)) != len(farm_tags):
        raise HTTPException(409, 'Toplu listede yinelenen TR veya işletme küpe numarası var.')
    all_tags = tr_tags + farm_tags
    tag_owners = {}
    for index, row in enumerate(data.entries):
        for value in {row.tr_ear_tag.lower(), row.farm_ear_tag.lower() if row.farm_ear_tag else None} - {None}:
            if value in tag_owners and tag_owners[value] != index:
                raise HTTPException(409, 'Aynı numara farklı hayvanların TR ve işletme küpesi olarak kullanılamaz.')
            tag_owners[value] = index
    if db.scalar(select(Animal.id).where(or_(func.lower(Animal.ear_tag).in_(all_tags),
                                           func.lower(Animal.farm_ear_tag).in_(all_tags)))) is not None:
        raise HTTPException(409, 'TR veya işletme küpe numaralarından biri zaten kayıtlı.')
    occupied = dict(db.execute(select(Animal.pen_id, func.count(Animal.id)).where(
                    Animal.status == 'active', Animal.pen_id.in_(incoming)).group_by(Animal.pen_id)).all())
    if any(occupied.get(pen_id, 0) + count > pens[pen_id].capacity for pen_id, count in incoming.items()):
        raise HTTPException(409, 'Toplu giriş hedef grubun kapasitesini aşıyor; hiçbir hayvan eklenmedi.')
    created = []
    for row in data.entries:
        animal = Animal(ear_tag=row.tr_ear_tag, farm_ear_tag=row.farm_ear_tag, birth_date=row.birth_date,
                        sex=row.sex, breed=row.breed.strip() or 'Belirtilmedi',
                        arrival_date=data.arrival_date, entry_weight_kg=row.entry_weight_kg,
                        pen_id=row.pen_id, status='active')
        db.add(animal)
        created.append(animal)
    _commit(db)
    return {'count': len(created), 'rows': [animal_data(a, {k: p.code for k, p in pens.items()}) for a in created],
            'message': 'Toplu hayvan girişleri kaydedildi.'}


@router.post('/bulk-exit')
def bulk_exit(data: BulkExits, request: Request, db: Session = Depends(get_db)):
    need(request, 'hayvanlar.kart.edit')
    animals = _active_batch(db, data.entries, data.exit_date)
    destination = data.destination.strip()
    if data.reason != 'death' and not destination:
        raise HTTPException(422, 'Kesim veya satış için nereye gittiği yazılmalıdır.')
    if data.reason != 'death' and any(row.exit_kg is None for row in data.entries):
        raise HTTPException(422, 'Kesim veya satış için her hayvanın çıkış kilosu gereklidir.')
    if db.scalar(select(AnimalExit.id).where(AnimalExit.animal_id.in_(animals))) is not None:
        raise HTTPException(409, 'Listedeki hayvanlardan birinin çıkışı zaten kayıtlı.')
    for row in data.entries:
        last_weighing = db.scalar(select(func.max(Weighing.measured_at)).where(Weighing.animal_id == row.animal_id))
        last_transfer = db.scalar(select(func.max(AnimalGroupTransfer.transferred_on)).where(AnimalGroupTransfer.animal_id == row.animal_id))
        if (last_weighing and data.exit_date < last_weighing) or (last_transfer and data.exit_date < last_transfer):
            raise HTTPException(422, 'Çıkış tarihi kayıtlı son tartım veya grup değişiminden önce olamaz.')
    for row in data.entries:
        animal = animals[row.animal_id]
        group = db.get(Pen, animal.pen_id)
        db.add(AnimalExit(animal_id=row.animal_id, exit_date=data.exit_date, reason=data.reason,
                          destination=destination, exit_kg=row.exit_kg, tr_ear_tag=animal.ear_tag,
                          farm_ear_tag=animal.farm_ear_tag, group_no=group.code))
        animal.status = 'exited'
    _commit(db)
    return {'count': len(data.entries), 'reason_label': REASONS[data.reason], 'message': 'Toplu hayvan çıkışı kaydedildi.'}


def exit_rows(db, date_from=None, date_to=None, reason=None):
    query = select(AnimalExit)
    if date_from:
        query = query.where(AnimalExit.exit_date >= date_from)
    if date_to:
        query = query.where(AnimalExit.exit_date <= date_to)
    if reason:
        if reason not in REASONS:
            raise HTTPException(422, 'Geçerli çıkış nedeni seçin.')
        query = query.where(AnimalExit.reason == reason)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, 'Başlangıç tarihi bitiş tarihinden sonra olamaz.')
    return [{'id': e.id, 'animal_id': e.animal_id, 'tr_ear_tag': e.tr_ear_tag, 'farm_ear_tag': e.farm_ear_tag,
             'exit_date': str(e.exit_date), 'reason': e.reason, 'reason_label': REASONS[e.reason],
             'destination': e.destination, 'exit_kg': str(e.exit_kg) if e.exit_kg is not None else None,
             'group_no': e.group_no} for e in db.scalars(query.order_by(AnimalExit.exit_date.desc(), AnimalExit.id.desc()))]


@router.get('/exits')
def exits(request: Request, date_from: date | None = None, date_to: date | None = None,
          reason: str | None = None, db: Session = Depends(get_db)):
    need(request, 'reports.animals.view')
    rows = exit_rows(db, date_from, date_to, reason)
    return {'rows': rows, 'count': len(rows)}


@router.get('/exits.csv')
def exits_csv(request: Request, date_from: date | None = None, date_to: date | None = None,
              reason: str | None = None, db: Session = Depends(get_db)):
    need(request, 'reports.animals.view')
    need(request, 'reports.animals.export')
    rows = exit_rows(db, date_from, date_to, reason)
    stream = io.StringIO()
    stream.write('\ufeff')
    writer = csv.writer(stream)
    writer.writerow(['Tarih', 'TR Küpe No', 'İşletme Küpe No', 'Grup No', 'Çıkış Nedeni', 'Nereye Gittiği', 'Çıkış Kilosu (kg)'])
    def safe(value):
        value = str(value or '')
        return "'" + value if value[:1] in ('=', '+', '-', '@', '\t', '\r') else value
    for row in rows:
        values = {**row, 'exit_date': date.fromisoformat(row['exit_date']).strftime('%d.%m.%Y')}
        values['exit_kg'] = (format(Decimal(row['exit_kg']), ',.3f').rstrip('0').rstrip('.').translate(
            str.maketrans(',.', '.,')) if row['exit_kg'] is not None else 'Bilinmiyor')
        writer.writerow([safe(values[x]) for x in ('exit_date', 'tr_ear_tag', 'farm_ear_tag', 'group_no', 'reason_label', 'destination', 'exit_kg')])
    return StreamingResponse(iter([stream.getvalue().encode('utf-8')]), media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition': 'attachment; filename="hayvan_cikislari.csv"'})
