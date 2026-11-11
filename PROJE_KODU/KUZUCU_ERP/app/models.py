from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Date, DateTime, Numeric, Integer, UniqueConstraint, CheckConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def utc_now(): return datetime.now(timezone.utc)

class Pen(Base):
    __tablename__ = 'pens'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    capacity: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint('capacity > 0',name='positive_pen_capacity'),)

class Animal(Base):
    __tablename__ = 'animals'
    id: Mapped[int] = mapped_column(primary_key=True)
    ear_tag: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    breed: Mapped[str] = mapped_column(String(80), default='Belirtilmedi')
    farm_ear_tag: Mapped[str | None] = mapped_column(String(60), nullable=True, unique=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    arrival_date: Mapped[date] = mapped_column(Date)
    entry_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    pen_id: Mapped[int] = mapped_column(ForeignKey('pens.id'))
    status: Mapped[str] = mapped_column(String(20), default='active')
    pen: Mapped['Pen'] = relationship()
    __table_args__ = (CheckConstraint('entry_weight_kg > 0',name='positive_entry_weight'),)

class Weighing(Base):
    __tablename__ = 'weighings'
    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey('animals.id'))
    measured_at: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12,3))
    __table_args__ = (CheckConstraint('weight_kg > 0',name='positive_weight'),)

class Field(Base):
    __tablename__ = 'fields'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    # Tapu/kadastro Ada No; mevcut pilot parsellerinde boş bırakılabilir.
    ada_no: Mapped[str | None] = mapped_column(String(40), nullable=True)
    satellite_image: Mapped[str | None] = mapped_column(String(150), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    area_decare: Mapped[Decimal] = mapped_column(Numeric(12,3))
    __table_args__ = (CheckConstraint('area_decare > 0',name='positive_field_area'),)

class CropSeason(Base):
    __tablename__ = 'crop_seasons'
    id: Mapped[int] = mapped_column(primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey('fields.id'))
    year: Mapped[int] = mapped_column(Integer)
    crop: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint('field_id','year',name='unique_field_year'),)

class Item(Base):
    __tablename__ = 'items'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(12), default='kg')

class Firm(Base):
    __tablename__ = 'firms'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    tax_no: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    phone: Mapped[str] = mapped_column(String(40), default='')
    address: Mapped[str] = mapped_column(String(600), default='')

class StockMovementRevision(Base):
    __tablename__ = 'stock_movement_revisions'
    id: Mapped[int] = mapped_column(primary_key=True)
    movement_id: Mapped[int] = mapped_column(ForeignKey('stock_movements.id'))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    old_item_id: Mapped[int] = mapped_column(Integer)
    new_item_id: Mapped[int] = mapped_column(Integer)
    old_type: Mapped[str] = mapped_column(String(8))
    new_type: Mapped[str] = mapped_column(String(8))
    old_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    new_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    old_movement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_movement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    old_reference: Mapped[str] = mapped_column(String(100), default='')
    new_reference: Mapped[str] = mapped_column(String(100), default='')
    reason: Mapped[str] = mapped_column(String(300))

class StockMovement(Base):
    __tablename__ = 'stock_movements'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))
    type: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[Decimal] = mapped_column(Numeric(16,3))
    reference: Mapped[str] = mapped_column(String(100), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # Stok hareketinin operasyon tarihi. Eski kayitlarda geriye uyumlu olarak doldurulur.
    movement_date: Mapped[date | None] = mapped_column(Date, default=date.today, nullable=True)
    __table_args__ = (CheckConstraint('quantity > 0',name='positive_stock_quantity'), CheckConstraint("type IN ('IN','OUT')",name='valid_stock_type'))


class Reminder(Base):
    """Ajanda kaydı. Tekrarlayan hatırlatmalarda biten gün, sıradaki tarihi belirler."""
    __tablename__ = 'reminders'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    notes: Mapped[str] = mapped_column(String(1000), default='')
    category: Mapped[str] = mapped_column(String(24), default='Genel')
    frequency: Mapped[str] = mapped_column(String(16), default='once')
    start_date: Mapped[date] = mapped_column(Date)
    remind_time: Mapped[str] = mapped_column(String(5), default='09:00')
    is_active: Mapped[bool] = mapped_column(default=True)
    last_completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (CheckConstraint("frequency IN ('once','daily','weekly','monthly')", name='valid_reminder_frequency'),)


class HealthCase(Base):
    """Hayvanin veterinere bagli saglik olayi / uygulama plani."""
    __tablename__ = 'health_cases'
    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey('animals.id'), index=True)
    record_type: Mapped[str] = mapped_column(String(16), default='treatment')
    condition_name: Mapped[str] = mapped_column(String(140), index=True)
    symptoms: Mapped[str] = mapped_column(String(1500), default='')
    product_name: Mapped[str] = mapped_column(String(180), default='')
    treatment_name: Mapped[str] = mapped_column(String(180), default='')
    repeat_review_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    dosage_text: Mapped[str] = mapped_column(String(120), default='')
    veterinarian: Mapped[str] = mapped_column(String(160), default='')
    vet_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    applications_per_day: Mapped[int] = mapped_column(Integer, default=1)
    start_date: Mapped[date] = mapped_column(Date)
    planned_end_date: Mapped[date] = mapped_column(Date)
    withdrawal_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(String(1500), default='')
    status: Mapped[str] = mapped_column(String(16), default='active')
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    outcome_notes: Mapped[str] = mapped_column(String(1500), default='')
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    animal: Mapped['Animal'] = relationship()
    __table_args__ = (
        CheckConstraint("record_type IN ('treatment','vaccination','observation')", name='health_record_type'),
        CheckConstraint("status IN ('active','closed')", name='health_status_valid'),
        CheckConstraint('planned_end_date >= start_date', name='health_dates_valid'),
    )


class HealthCatalogEntry(Base):
    """Kullanıcı tarafından biriktirilen ilaç/aşı veya tedavi adı sözlüğü."""
    __tablename__ = 'health_catalog_entries'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(180))
    name_key: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint('kind','name_key',name='health_catalog_kind_name_unique'),
                      CheckConstraint("kind IN ('medication','treatment')",name='health_catalog_kind_valid'))


class HealthDailyLog(Base):
    """Gunluk gercek uygulama ve gozlem: bir vaka icin gunde bir kayit."""
    __tablename__ = 'health_daily_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey('health_cases.id'), index=True)
    performed_on: Mapped[date] = mapped_column(Date)
    application_no: Mapped[int] = mapped_column(Integer, default=1)
    performed_by: Mapped[str] = mapped_column(String(120))
    observation: Mapped[str] = mapped_column(String(1200), default='')
    response: Mapped[str] = mapped_column(String(18), default='not_evaluated')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint('case_id','performed_on','application_no',name='health_daily_application_unique'),)


class HealthPrintSettings(Base):
    __tablename__ = 'health_print_settings'
    id: Mapped[int] = mapped_column(primary_key=True)
    daily_time: Mapped[str] = mapped_column(String(5), default='07:00')
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_print: Mapped[bool] = mapped_column(Boolean, default=False)
    printer_name: Mapped[str] = mapped_column(String(180), default='')


class HealthPrintRun(Base):
    __tablename__ = 'health_print_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    pdf_path: Mapped[str] = mapped_column(String(500))
    printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    print_error: Mapped[str] = mapped_column(String(500), default='')


class Calf(Base):
    """Sut/mama donemindeki buzagi dosyasi; besi hayvanindan ayridir."""
    __tablename__ = 'calves'
    id: Mapped[int] = mapped_column(primary_key=True)
    tr_ear_tag: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    farm_ear_tag: Mapped[str | None] = mapped_column(String(60), nullable=True, unique=True)
    sex: Mapped[str] = mapped_column(String(10))  # male/female
    breed: Mapped[str] = mapped_column(String(80), default='Belirtilmedi')
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    entry_date: Mapped[date] = mapped_column(Date)
    entry_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    planned_days: Mapped[int] = mapped_column(Integer, default=45)
    batch_code: Mapped[str] = mapped_column(String(80), default='', index=True)  # legacy data
    exit_group_no: Mapped[str] = mapped_column(String(80), default='', index=True)
    notes: Mapped[str] = mapped_column(String(1200), default='')
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    __table_args__ = (
        CheckConstraint('entry_kg > 0', name='positive_calf_entry_kg'),
        CheckConstraint('exit_kg IS NULL OR exit_kg > 0', name='positive_calf_exit_kg'),
        CheckConstraint("sex IN ('male','female')", name='valid_calf_sex'),
        CheckConstraint('planned_days > 0', name='positive_calf_planned_days'),
    )


class CalfConsumption(Base):
    __tablename__ = 'calf_consumptions'
    id: Mapped[int] = mapped_column(primary_key=True)
    calf_id: Mapped[int] = mapped_column(ForeignKey('calves.id'), index=True)
    consumed_on: Mapped[date] = mapped_column(Date)
    milk_kg: Mapped[Decimal] = mapped_column(Numeric(12,3), default=0)
    feed_kg: Mapped[Decimal] = mapped_column(Numeric(12,3), default=0)
    notes: Mapped[str] = mapped_column(String(400), default='')
    __table_args__ = (
        UniqueConstraint('calf_id','consumed_on',name='unique_calf_consumption_date'),
        CheckConstraint('milk_kg >= 0',name='positive_calf_milk_kg'),
        CheckConstraint('feed_kg >= 0',name='positive_calf_feed_kg'),
    )


class CalfWeighing(Base):
    __tablename__ = 'calf_weighings'
    id: Mapped[int] = mapped_column(primary_key=True)
    calf_id: Mapped[int] = mapped_column(ForeignKey('calves.id'), index=True)
    measured_on: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12,3))
    __table_args__ = (
        UniqueConstraint('calf_id','measured_on',name='unique_calf_weighing_date'),
        CheckConstraint('weight_kg > 0',name='positive_calf_weighing_kg'),
    )
