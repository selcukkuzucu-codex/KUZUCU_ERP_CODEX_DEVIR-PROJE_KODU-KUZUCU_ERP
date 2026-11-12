"""Personel, mesai ve izin kayıtları; hukuki hak veya ücret tahmini yapılmaz."""
import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, get_db
from .models import utc_now
from .security import creator_map, need

router = APIRouter(prefix='/api/personnel', tags=['Personel'])
STATUS_LABELS = {'active': 'Çalışıyor', 'left': 'İşten ayrıldı', 'planned': 'Ayrılışı planlandı', 'not_started': 'İşe başlamadı'}
LEAVE_LABELS = {'weekly': 'Haftalık izin', 'annual': 'Yıllık izin'}


class Employee(Base):
    __tablename__ = 'personnel_employees'
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(120), default='')
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str] = mapped_column(String(40), default='')
    notes: Mapped[str] = mapped_column(String(1000), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (CheckConstraint('end_date IS NULL OR end_date >= start_date', name='personnel_employment_dates'),)


class Overtime(Base):
    __tablename__ = 'personnel_overtime'
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('personnel_employees.id'), index=True)
    worked_on: Mapped[date] = mapped_column(Date)
    hours: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    notes: Mapped[str] = mapped_column(String(1000), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint('employee_id', 'worked_on', name='personnel_overtime_day'),
                      CheckConstraint('hours > 0 AND hours <= 24', name='personnel_overtime_hours'))


class PersonnelLeave(Base):
    __tablename__ = 'personnel_leaves'
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('personnel_employees.id'), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(String(1000), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (CheckConstraint("kind IN ('weekly','annual')", name='personnel_leave_kind'),
                      CheckConstraint('ends_on >= starts_on', name='personnel_leave_dates'))


class AnnualAllowance(Base):
    __tablename__ = 'personnel_allowances'
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('personnel_employees.id'), index=True)
    year: Mapped[int] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint('employee_id', 'year', name='personnel_allowance_year'),
                      CheckConstraint('days >= 0', name='personnel_allowance_days'))


class EmployeeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    employee_no: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=2, max_length=120)
    department: str = Field(default='', max_length=120)
    start_date: date
    end_date: date | None = None
    phone: str = Field(default='', max_length=40)
    notes: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError('İşten ayrılış tarihi işe giriş tarihinden önce olamaz.')
        return self


class OvertimeIn(BaseModel):
    employee_id: int = Field(gt=0)
    worked_on: date
    hours: Decimal = Field(gt=0, le=24, max_digits=5, decimal_places=2, allow_inf_nan=False)
    notes: str = Field(default='', max_length=1000)


class LeaveIn(BaseModel):
    employee_id: int = Field(gt=0)
    kind: Literal['weekly', 'annual']
    starts_on: date
    ends_on: date
    notes: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError('İzin bitişi başlangıçtan önce olamaz.')
        if not 2000 <= self.starts_on.year <= self.ends_on.year <= 2200:
            raise ValueError('İzin yılı 2000 ile 2200 arasında olmalı.')
        return self


class AllowanceIn(BaseModel):
    days: int = Field(ge=0, le=100000, strict=True)


def lock_write(db):
    # SQLite pilotunda çakışma ve kalan izin kontrolü ile kayıt aynı yazma
    # işlemi içinde tutulur; eşzamanlı iki istek hakkı birlikte tüketemez.
    if db.get_bind().dialect.name == 'sqlite' and not db.in_transaction():
        db.execute(text('BEGIN IMMEDIATE'))


def commit(db):
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, 'Aynı bilgilerle kayıt zaten bulunuyor. Listeyi yenileyip kontrol edin.') from error


def employee(db, employee_id):
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(404, 'Personel kaydı bulunamadı.')
    return row


def turkey_today():
    """İşletme Türkiye saatine göre çalışır; bilgisayar başka saat dilimindeyse de gün kaymaz."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo('Europe/Istanbul')).date()


def status_of(row):
    today = turkey_today()
    if row.start_date > today:
        return 'not_started'
    if row.end_date:
        return 'left' if row.end_date <= today else 'planned'
    return 'active'


def employee_dict(row):
    state = status_of(row)
    return {column.name: getattr(row, column.name) for column in Employee.__table__.columns} | {
        'status': state, 'status_label': STATUS_LABELS[state]}


def selected_employees(db, employee_id=None, status='', search=''):
    if status and status not in STATUS_LABELS:
        raise HTTPException(422, 'Geçerli personel durumunu seçin.')
    query = select(Employee).order_by(Employee.full_name, Employee.id)
    if employee_id is not None:
        query = query.where(Employee.id == employee_id)
    if search.strip():
        value = '%' + search.strip() + '%'
        query = query.where(or_(Employee.employee_no.ilike(value), Employee.full_name.ilike(value), Employee.department.ilike(value)))
    return [row for row in db.scalars(query) if not status or status_of(row) == status]


def check_range(date_from, date_to):
    if date_from and date_to and date_to < date_from:
        raise HTTPException(422, 'Bitiş tarihi başlangıçtan önce olamaz.')


def check_employment(row, start, end):
    if start < row.start_date or (row.end_date and end > row.end_date):
        raise HTTPException(409, 'İşlem tarihleri personelin işe giriş ve ayrılış döneminde olmalı.')


def year_days(start, end, year):
    start, end = max(start, date(year, 1, 1)), min(end, date(year, 12, 31))
    return max(0, (end - start).days + 1)


def annual_reserved(db, employee_id, year, exclude=None):
    query = select(PersonnelLeave).where(PersonnelLeave.employee_id == employee_id, PersonnelLeave.kind == 'annual',
                                       PersonnelLeave.starts_on <= date(year, 12, 31), PersonnelLeave.ends_on >= date(year, 1, 1))
    if exclude is not None:
        query = query.where(PersonnelLeave.id != exclude)
    return sum(year_days(row.starts_on, row.ends_on, year) for row in db.scalars(query))


def balance(db, row, year):
    allowance = db.scalar(select(AnnualAllowance).where(AnnualAllowance.employee_id == row.id, AnnualAllowance.year == year))
    used = planned = 0
    today = turkey_today()
    for leave in db.scalars(select(PersonnelLeave).where(PersonnelLeave.employee_id == row.id, PersonnelLeave.kind == 'annual')):
        total = year_days(leave.starts_on, leave.ends_on, year)
        elapsed = year_days(leave.starts_on, min(leave.ends_on, today), year) if leave.starts_on <= today else 0
        used += elapsed
        planned += total - elapsed
    return {'employee_id': row.id, 'employee_no': row.employee_no, 'full_name': row.full_name, 'year': year,
            'allocated_days': allowance.days if allowance else None, 'used_days': used, 'planned_days': planned,
            'remaining_days': allowance.days - used - planned if allowance else None}


def row_info(db, row):
    person = employee(db, row.employee_id)
    result = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    result.update(employee_no=person.employee_no, full_name=person.full_name, department=person.department,
                  status=status_of(person), status_label=STATUS_LABELS[status_of(person)])
    if isinstance(row, PersonnelLeave):
        result.update(kind_label=LEAVE_LABELS[row.kind], days=(row.ends_on - row.starts_on).days + 1)
    if isinstance(row, Overtime):
        result['hours'] = str(row.hours)
    return result


@router.get('/employees')
def list_employees(request: Request, status: str = '', search: str = '', db: Session = Depends(get_db)):
    need(request, 'personel.view')
    rows = selected_employees(db, status=status, search=search)
    actors = creator_map(db, Employee.__tablename__, [row.id for row in rows])
    return [employee_dict(row) | {'created_by': actors.get(row.id, 'Eski kayıt')} for row in rows]


@router.post('/employees', status_code=201)
def create_employee(data: EmployeeIn, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.create')
    lock_write(db)
    if db.scalar(select(Employee.id).where(Employee.employee_no == data.employee_no)) is not None:
        raise HTTPException(409, 'Personel numarası zaten kayıtlı.')
    row = Employee(**data.model_dump())
    db.add(row)
    commit(db)
    db.refresh(row)
    return employee_dict(row)


@router.put('/employees/{employee_id}')
def update_employee(employee_id: int, data: EmployeeIn, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.edit')
    lock_write(db)
    row = employee(db, employee_id)
    if db.scalar(select(Employee.id).where(Employee.employee_no == data.employee_no, Employee.id != employee_id)) is not None:
        raise HTTPException(409, 'Personel numarası başka bir kayıtta kullanılıyor.')
    for overtime in db.scalars(select(Overtime).where(Overtime.employee_id == employee_id)):
        check_employment(data, overtime.worked_on, overtime.worked_on)
    for leave in db.scalars(select(PersonnelLeave).where(PersonnelLeave.employee_id == employee_id)):
        check_employment(data, leave.starts_on, leave.ends_on)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    commit(db)
    db.refresh(row)
    return employee_dict(row)


@router.get('/overtime')
def list_overtime(request: Request, employee_id: int | None = None, date_from: date | None = None,
                  date_to: date | None = None, status: str = '', db: Session = Depends(get_db)):
    need(request, 'personel.view')
    check_range(date_from, date_to)
    ids = [row.id for row in selected_employees(db, employee_id, status)]
    query = select(Overtime).where(Overtime.employee_id.in_(ids)).order_by(Overtime.worked_on.desc(), Overtime.id.desc())
    if date_from:
        query = query.where(Overtime.worked_on >= date_from)
    if date_to:
        query = query.where(Overtime.worked_on <= date_to)
    return [row_info(db, row) for row in db.scalars(query)]


def validate_overtime(db, data, exclude=None):
    person = employee(db, data.employee_id)
    check_employment(person, data.worked_on, data.worked_on)
    if data.worked_on > turkey_today():
        raise HTTPException(422, 'Gelecek günün mesaisi gerçekleşmiş olarak kaydedilemez.')
    duplicate = select(Overtime.id).where(Overtime.employee_id == data.employee_id, Overtime.worked_on == data.worked_on)
    if exclude is not None:
        duplicate = duplicate.where(Overtime.id != exclude)
    if db.scalar(duplicate) is not None:
        raise HTTPException(409, 'Bu personelin aynı gün için mesai kaydı var; Düzenle işlemini kullanın.')
    if db.scalar(select(PersonnelLeave.id).where(PersonnelLeave.employee_id == data.employee_id,
                 PersonnelLeave.starts_on <= data.worked_on, PersonnelLeave.ends_on >= data.worked_on)) is not None:
        raise HTTPException(409, 'Bu tarihte izin kaydı bulunduğu için mesai kaydedilemez.')


@router.post('/overtime', status_code=201)
def create_overtime(data: OvertimeIn, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.create')
    lock_write(db)
    validate_overtime(db, data)
    row = Overtime(**data.model_dump())
    db.add(row)
    commit(db)
    db.refresh(row)
    return row_info(db, row)


@router.put('/overtime/{record_id}')
def update_overtime(record_id: int, data: OvertimeIn, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.edit')
    lock_write(db)
    row = db.get(Overtime, record_id)
    if row is None:
        raise HTTPException(404, 'Mesai kaydı bulunamadı.')
    validate_overtime(db, data, record_id)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    commit(db)
    db.refresh(row)
    return row_info(db, row)


@router.delete('/overtime/{record_id}', status_code=204)
def delete_overtime(record_id: int, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.delete')
    lock_write(db)
    row = db.get(Overtime, record_id)
    if row is None:
        raise HTTPException(404, 'Mesai kaydı bulunamadı.')
    db.delete(row)
    commit(db)


@router.get('/leaves')
def list_leaves(request: Request, employee_id: int | None = None, date_from: date | None = None,
                date_to: date | None = None, status: str = '', db: Session = Depends(get_db)):
    need(request, 'personel.view')
    check_range(date_from, date_to)
    ids = [row.id for row in selected_employees(db, employee_id, status)]
    query = select(PersonnelLeave).where(PersonnelLeave.employee_id.in_(ids)).order_by(PersonnelLeave.starts_on.desc(), PersonnelLeave.id.desc())
    if date_from:
        query = query.where(PersonnelLeave.ends_on >= date_from)
    if date_to:
        query = query.where(PersonnelLeave.starts_on <= date_to)
    return [row_info(db, row) for row in db.scalars(query)]


def validate_leave(db, data, exclude=None):
    person = employee(db, data.employee_id)
    check_employment(person, data.starts_on, data.ends_on)
    overlapping = select(PersonnelLeave.id).where(PersonnelLeave.employee_id == data.employee_id,
                    PersonnelLeave.starts_on <= data.ends_on, PersonnelLeave.ends_on >= data.starts_on)
    if exclude is not None:
        overlapping = overlapping.where(PersonnelLeave.id != exclude)
    if db.scalar(overlapping) is not None:
        raise HTTPException(409, 'Bu tarih aralığında başka bir izin kaydı var.')
    if db.scalar(select(Overtime.id).where(Overtime.employee_id == data.employee_id,
                 Overtime.worked_on >= data.starts_on, Overtime.worked_on <= data.ends_on)) is not None:
        raise HTTPException(409, 'İzin döneminde mesai kaydı var. Önce çakışan kaydı kontrol edin.')
    if data.kind == 'annual':
        for year in range(data.starts_on.year, data.ends_on.year + 1):
            allowance = db.scalar(select(AnnualAllowance).where(AnnualAllowance.employee_id == person.id, AnnualAllowance.year == year))
            if allowance is None:
                raise HTTPException(409, f'{year} yılı için yıllık izin hakkını önce tanımlayın; hak otomatik tahmin edilmez.')
            if annual_reserved(db, person.id, year, exclude) + year_days(data.starts_on, data.ends_on, year) > allowance.days:
                raise HTTPException(409, f'{year} yılı için kalan yıllık izin hakkı yetersiz.')


@router.post('/leaves', status_code=201)
def create_leave(data: LeaveIn, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.create')
    lock_write(db)
    validate_leave(db, data)
    row = PersonnelLeave(**data.model_dump())
    db.add(row)
    commit(db)
    db.refresh(row)
    return row_info(db, row)


@router.put('/leaves/{record_id}')
def update_leave(record_id: int, data: LeaveIn, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.edit')
    lock_write(db)
    row = db.get(PersonnelLeave, record_id)
    if row is None:
        raise HTTPException(404, 'İzin kaydı bulunamadı.')
    validate_leave(db, data, record_id)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    commit(db)
    db.refresh(row)
    return row_info(db, row)


@router.delete('/leaves/{record_id}', status_code=204)
def delete_leave(record_id: int, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.delete')
    lock_write(db)
    row = db.get(PersonnelLeave, record_id)
    if row is None:
        raise HTTPException(404, 'İzin kaydı bulunamadı.')
    db.delete(row)
    commit(db)


@router.put('/allowances/{employee_id}/{year}')
def set_allowance(employee_id: int, year: int, data: AllowanceIn, request: Request, db: Session = Depends(get_db)):
    need(request, 'personel.edit')
    lock_write(db)
    employee(db, employee_id)
    if not 2000 <= year <= 2200:
        raise HTTPException(422, 'İzin yılı 2000 ile 2200 arasında olmalı.')
    if annual_reserved(db, employee_id, year) > data.days:
        raise HTTPException(409, 'Tanımlanan hak kayıtlı yıllık izin günlerinden az olamaz.')
    row = db.scalar(select(AnnualAllowance).where(AnnualAllowance.employee_id == employee_id, AnnualAllowance.year == year))
    if row is None:
        row = AnnualAllowance(employee_id=employee_id, year=year, days=data.days)
        db.add(row)
    else:
        row.days = data.days
    commit(db)
    return {'employee_id': employee_id, 'year': year, 'days': row.days}


@router.get('/balances')
def get_balances(request: Request, employee_id: int | None = None, year: int = Query(default_factory=lambda: turkey_today().year, ge=2000, le=2200),
                  db: Session = Depends(get_db)):
    need(request, 'reports.payroll.view')
    return [balance(db, row, year) for row in selected_employees(db, employee_id)]


def report_data(db, employee_id=None, status='', date_from=None, date_to=None, kind='summary', year=None):
    check_range(date_from, date_to)
    if kind not in ('summary', 'employees', 'overtime', 'leaves', 'employment'):
        raise HTTPException(422, 'Geçerli personel rapor türünü seçin.')
    year = year or turkey_today().year
    if not 2000 <= year <= 2200:
        raise HTTPException(422, 'İzin yılı 2000 ile 2200 arasında olmalı.')
    people = selected_employees(db, employee_id, status)
    ids = [person.id for person in people]
    overtime = list(db.scalars(select(Overtime).where(Overtime.employee_id.in_(ids)).order_by(Overtime.worked_on, Overtime.id)))
    leaves = list(db.scalars(select(PersonnelLeave).where(PersonnelLeave.employee_id.in_(ids)).order_by(PersonnelLeave.starts_on, PersonnelLeave.id)))
    overtime = [row for row in overtime if (not date_from or row.worked_on >= date_from) and (not date_to or row.worked_on <= date_to)]
    leaves = [row for row in leaves if (not date_from or row.ends_on >= date_from) and (not date_to or row.starts_on <= date_to)]
    names = {person.id: person for person in people}
    trdate = lambda value: value.strftime('%d.%m.%Y') if value else '—'
    trhours = lambda value: format(value, '.2f').replace('.', ',')
    included_days = lambda row: max(0, (min(row.ends_on, date_to or row.ends_on) - max(row.starts_on, date_from or row.starts_on)).days + 1)
    if kind == 'overtime':
        columns = ['Personel No', 'Ad Soyad', 'Bölüm', 'Tarih', 'Mesai saati', 'Açıklama']
        rows = [[names[row.employee_id].employee_no, names[row.employee_id].full_name, names[row.employee_id].department,
                 trdate(row.worked_on), trhours(row.hours), row.notes] for row in overtime]
    elif kind == 'leaves':
        columns = ['Personel No', 'Ad Soyad', 'İzin türü', 'Başlangıç', 'Bitiş', 'Seçili dönemdeki gün', 'Açıklama']
        rows = [[names[row.employee_id].employee_no, names[row.employee_id].full_name, LEAVE_LABELS[row.kind],
                 trdate(row.starts_on), trdate(row.ends_on), included_days(row), row.notes] for row in leaves]
    elif kind == 'employment':
        columns = ['Personel No', 'Ad Soyad', 'Bölüm', 'İşlem', 'Tarih']
        rows = []
        for person in people:
            for label, when in [('İşe giriş', person.start_date), ('İşten ayrılış', person.end_date)]:
                if when and (not date_from or when >= date_from) and (not date_to or when <= date_to):
                    rows.append([person.employee_no, person.full_name, person.department, label, trdate(when)])
    elif kind == 'employees':
        columns = ['Personel No', 'Ad Soyad', 'Bölüm', 'İşe giriş', 'İşten ayrılış', 'Durum']
        rows = [[person.employee_no, person.full_name, person.department, trdate(person.start_date), trdate(person.end_date),
                 STATUS_LABELS[status_of(person)]] for person in people
                if (not date_from or not person.end_date or person.end_date >= date_from) and (not date_to or person.start_date <= date_to)]
    else:
        columns = ['Personel No', 'Ad Soyad', 'Bölüm', 'Durum', 'Mesai saati', 'Haftalık izin günü', 'Yıllık izin günü',
                   'Yıllık hak', 'Kullanılan yıllık izin', 'Planlanan yıllık izin', 'Kalan yıllık izin']
        rows = []
        for person in people:
            quota = balance(db, person, year)
            rows.append([person.employee_no, person.full_name, person.department, STATUS_LABELS[status_of(person)],
                         trhours(sum((row.hours for row in overtime if row.employee_id == person.id), Decimal(0))),
                         sum(included_days(row) for row in leaves if row.employee_id == person.id and row.kind == 'weekly'),
                         sum(included_days(row) for row in leaves if row.employee_id == person.id and row.kind == 'annual'),
                         quota['allocated_days'] if quota['allocated_days'] is not None else 'Tanımlanmadı',
                         quota['used_days'], quota['planned_days'], quota['remaining_days'] if quota['remaining_days'] is not None else 'Tanımlanmadı'])
    return {'title': 'Personel, Mesai ve İzin Raporu', 'columns': columns, 'rows': rows, 'row_count': len(rows),
            'year': year, 'scope': 'reports.payroll',
            'notice': 'İzin günleri başlangıç ve bitiş dahil takvim günüdür. Yıllık hak elle tanımlanır; mesai ücreti veya hukuki hak hesaplanmaz.',
            'summary': {'employee_count': len(people), 'overtime_hours': str(sum((row.hours for row in overtime), Decimal(0))),
                        'weekly_leave_days': sum(included_days(row) for row in leaves if row.kind == 'weekly'),
                        'annual_leave_days': sum(included_days(row) for row in leaves if row.kind == 'annual')}}


@router.get('/reports')
def personnel_report(request: Request, employee_id: int | None = None, status: str = '', date_from: date | None = None,
                     date_to: date | None = None, kind: str = 'summary', year: int | None = None, db: Session = Depends(get_db)):
    need(request, 'reports.payroll.view')
    return report_data(db, employee_id, status, date_from, date_to, kind, year)


@router.get('/reports.csv')
def personnel_csv(request: Request, employee_id: int | None = None, status: str = '', date_from: date | None = None,
                  date_to: date | None = None, kind: str = 'summary', year: int | None = None, db: Session = Depends(get_db)):
    need(request, 'reports.payroll.view')
    need(request, 'reports.payroll.export')
    result = report_data(db, employee_id, status, date_from, date_to, kind, year)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(result['columns'])
    def safe(value):
        value = str(value if value is not None else '')
        return "'" + value if value[:1] in ('=', '+', '-', '@', '\t', '\r') else value
    writer.writerows([[safe(value) for value in row] for row in result['rows']])
    return StreamingResponse(iter([('\ufeff' + output.getvalue()).encode('utf-8')]), media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition': 'attachment; filename="personel_mesai_izin.csv"'})
