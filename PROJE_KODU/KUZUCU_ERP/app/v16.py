"""v0.16: Ana Sayfa göstergeleri, kontrol listesi, yedek durumu ve Hayvan Çıkış Raporu.

Her gösterge kendi bölüm/rapor yetkisiyle hesaplanır; yetkisi olmayan kullanıcıya o veri gönderilmez.
"""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Animal, HealthCase, Item, Pen, Reminder, StockMovement, Weighing
from .security import allowed, current_user, need

router = APIRouter(tags=['Ana Sayfa ve yedek'])

STALE_WEIGHING_DAYS = 45
FEED_WINDOW_DAYS = 30


def _today():
    from .calf import today_local
    return today_local()


def _avg_daily_gain(db):
    """Aktif hayvanlarda son iki ölçüm (giriş tartımı dahil) arasındaki günlük artışın ortalaması."""
    animals = {a.id: a for a in db.scalars(select(Animal).where(Animal.status == 'active'))}
    if not animals:
        return None, 0
    weighings = {}
    for w in db.scalars(select(Weighing).where(Weighing.animal_id.in_(list(animals)))):
        weighings.setdefault(w.animal_id, []).append((w.measured_at, w.weight_kg))
    gains = []
    for animal_id, animal in animals.items():
        points = sorted([(animal.arrival_date, animal.entry_weight_kg)] + weighings.get(animal_id, []))
        if len(points) < 2:
            continue
        (d1, k1), (d2, k2) = points[-2], points[-1]
        days = (d2 - d1).days
        if days > 0:
            gains.append((Decimal(k2) - Decimal(k1)) / days)
    if not gains:
        return None, 0
    return round(sum(gains) / len(gains), 2), len(gains)


def _stock_rows(db):
    items = {i.id: i for i in db.scalars(select(Item))}
    balance = {i: Decimal(0) for i in items}
    out_recent = {i: Decimal(0) for i in items}
    since = _today() - timedelta(days=FEED_WINDOW_DAYS)
    for m in db.scalars(select(StockMovement)):
        if m.item_id not in items:
            continue
        balance[m.item_id] += m.quantity if m.type == 'IN' else -m.quantity
        if m.type == 'OUT' and m.movement_date and m.movement_date >= since:
            out_recent[m.item_id] += m.quantity
    return items, balance, out_recent


def _feed_days(db):
    """Hammadde ürünlerinde: bakiye / son 30 gündeki ortalama günlük çıkış. En az gün kalan ürün."""
    from .finance import ItemSettings
    categories = {s.item_id: s.category for s in db.scalars(select(ItemSettings))}
    items, balance, out_recent = _stock_rows(db)
    best = None
    for item_id, item in items.items():
        if categories.get(item_id) != 'rawmaterial':
            continue
        daily = out_recent[item_id] / FEED_WINDOW_DAYS
        if daily <= 0:
            continue
        days = int(max(balance[item_id], Decimal(0)) / daily)
        if best is None or days < best['days']:
            best = {'days': days, 'item': item.name, 'unit': item.unit}
    return best


@router.get('/api/dashboard/insights')
def insights(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    today = _today()
    cards, checks, todos = [], [], []

    if allowed(user, 'hayvanlar.kart.view'):
        active = db.scalar(select(func.count()).select_from(Animal).where(Animal.status == 'active')) or 0
        cards.append({'key': 'active', 'label': 'Aktif besi hayvanı', 'value': f'{active:,}'.replace(',', '.') + ' baş',
                      'note': 'Buzağılar hariç', 'tone': 'neutral', 'target': 'animals'})
    if allowed(user, 'hayvanlar.tartim.view'):
        gain, count = _avg_daily_gain(db)
        cards.append({'key': 'gain', 'label': 'Ortalama günlük artış',
                      'value': (str(gain).replace('.', ',') + ' kg/gün') if gain is not None else 'Tartım yok',
                      'note': f'{count} hayvanın son iki ölçümü' if count else 'En az iki ölçüm gerekir',
                      'tone': 'neutral', 'target': 'weighings'})
    if allowed(user, 'stok.hareket.view'):
        feed = _feed_days(db)
        if feed:
            cards.append({'key': 'feed', 'label': 'Yem stoğu yeter', 'value': f"{feed['days']} gün",
                          'note': f"En az kalan: {feed['item']} (son {FEED_WINDOW_DAYS} gün tüketimine göre)",
                          'tone': 'warn' if feed['days'] < 14 else 'good', 'target': 'stock'})
        else:
            cards.append({'key': 'feed', 'label': 'Yem stoğu yeter', 'value': 'Hesaplanamadı',
                          'note': 'Hammadde türünde ürün ve son 30 günde stok çıkışı gerekir', 'tone': 'neutral', 'target': 'stokgiris'})
    if allowed(user, 'hesap.cari.view'):
        from .finance import LedgerEntry
        sums = {}
        for e in db.scalars(select(LedgerEntry)):
            sums[e.firm_id] = sums.get(e.firm_id, Decimal(0)) + e.signed_amount
        payable = sum((-v for v in sums.values() if v < 0), Decimal(0))
        receivable = sum((v for v in sums.values() if v > 0), Decimal(0))
        cards.append({'key': 'payable', 'label': 'Cari borcumuz', 'value': _tl(payable),
                      'note': f'Alacağımız: {_tl(receivable)}', 'tone': 'neutral', 'target': 'cariler'})

    # ---- Kontrol edilmesi gerekenler ----
    if allowed(user, 'stok.hareket.view'):
        items, balance, _ = _stock_rows(db)
        for item_id, value in balance.items():
            if value < 0:
                checks.append({'level': 'error', 'title': f'{items[item_id].name} stoğu eksiye düşmüş',
                               'detail': f'Bakiye {_num(value)} {items[item_id].unit}. Eksik giriş veya hatalı çıkış olabilir.',
                               'target': 'stock'})
        from .finance import StockAlert
        pending = db.scalar(select(func.count()).select_from(StockAlert).where(StockAlert.acknowledged_at.is_(None))) or 0
        if pending:
            checks.append({'level': 'warn', 'title': f'{pending} stok uyarısı onay bekliyor',
                           'detail': 'Uyarı seviyesinin altına düşen ürünler var.', 'target': 'uyarilar'})
    if allowed(user, 'hayvanlar.kart.view'):
        counts = dict(db.execute(select(Animal.pen_id, func.count()).where(Animal.status == 'active').group_by(Animal.pen_id)).all())
        for pen in db.scalars(select(Pen)):
            if counts.get(pen.id, 0) > pen.capacity:
                checks.append({'level': 'warn', 'title': f'{pen.code} grubunda kapasite aşıldı',
                               'detail': f'{counts[pen.id]} baş / kapasite {pen.capacity}', 'target': 'pens'})
        if allowed(user, 'hayvanlar.tartim.view'):
            last = dict(db.execute(select(Weighing.animal_id, func.max(Weighing.measured_at)).group_by(Weighing.animal_id)).all())
            stale = [a for a in db.scalars(select(Animal).where(Animal.status == 'active'))
                     if (today - (last.get(a.id) or a.arrival_date)).days > STALE_WEIGHING_DAYS]
            if stale:
                sample = ', '.join(a.ear_tag for a in stale[:3]) + (' …' if len(stale) > 3 else '')
                checks.append({'level': 'warn', 'title': f'{len(stale)} hayvan {STALE_WEIGHING_DAYS} günden uzun süredir tartılmadı',
                               'detail': sample, 'target': 'weighings'})
            exited = {a.id: a for a in db.scalars(select(Animal).where(Animal.status != 'active'))}
            if exited:
                from .animal_operations import AnimalExit
                exit_day = dict(db.execute(select(AnimalExit.animal_id, func.max(AnimalExit.exit_date)).group_by(AnimalExit.animal_id)).all())
                wrong = [w for w in db.scalars(select(Weighing).where(Weighing.animal_id.in_(list(exited))))
                         if exit_day.get(w.animal_id) and w.measured_at > exit_day[w.animal_id]]
                if wrong:
                    a = exited[wrong[0].animal_id]
                    checks.append({'level': 'error', 'title': f'Çıkışı yapılmış {len({w.animal_id for w in wrong})} hayvanda çıkıştan sonra tartım var',
                                   'detail': f'Örnek: {a.ear_tag}', 'target': 'weighings'})
    if allowed(user, 'hayvanlar.saglik.view'):
        overdue = db.scalar(select(func.count()).select_from(HealthCase).where(
            HealthCase.status == 'active', HealthCase.planned_end_date < today)) or 0
        if overdue:
            checks.append({'level': 'warn', 'title': f'{overdue} tedavinin bitiş tarihi geçti ama kapatılmadı',
                           'detail': 'Sonucu girip tedaviyi kapatın.', 'target': 'animal-health'})

    if allowed(user, 'ajanda.view'):
        from .agenda import serialize as agenda_serialize
        for r in db.scalars(select(Reminder).where(Reminder.is_active.is_(True))):
            item = agenda_serialize(r)
            if item.get('due'):
                todos.append({'title': r.title, 'tag': r.category or 'Ajanda', 'target': 'reminders'})
        todos = todos[:8]

    from .backup import backup_status
    return {'today': today.isoformat(), 'cards': cards, 'checks': checks[:12], 'todos': todos,
            'backup': _backup_summary(backup_status())}


def _tl(value):
    return _num(round(value, 2)) + ' TL'


def _num(value):
    text = format(Decimal(value).normalize(), 'f') if value else '0'
    whole, _, frac = text.partition('.')
    sign = '-' if whole.startswith('-') else ''
    whole = f'{int(whole.lstrip("-") or 0):,}'.replace(',', '.')
    return sign + whole + (',' + frac[:2] if frac else '')


def _backup_summary(status):
    return {'latest_at': status.get('latest_at'), 'ok': status.get('ok'), 'message': status.get('message')}


@router.get('/api/backups/status')
def backups_status(request: Request):
    current_user(request)
    from .backup import backup_status
    status = backup_status()
    if not current_user(request).is_admin:
        # Klasör yolu ve dosya adları yalnızca yöneticiye gösterilir.
        return _backup_summary(status)
    return status


@router.post('/api/backups/now')
def backup_now(request: Request):
    if not current_user(request).is_admin:
        raise HTTPException(403, 'Elle yedek almayı yalnızca yönetici yapabilir.')
    from .backup import backup_db, backup_status
    engine = getattr(request.app.state, 'db_engine', None)
    if engine is None or backup_db(engine, force=True, label='elle') is None:
        raise HTTPException(500, 'Yedek alınamadı. Yedek klasörünün erişimini ve boş alanı kontrol edin.')
    return {'message': 'Yedek alındı.', **backup_status()}


# ---------------- Hayvan Çıkış Raporu ----------------

REASON_KEYS = {'': None, 'all': None, 'slaughter': 'slaughter', 'death': 'death', 'sale': 'sale'}


def _exit_report(request, db, date_from, date_to, reason, section):
    from .reports import combined_exit_rows
    user = current_user(request)
    if not (allowed(user, 'reports.animals.view') or allowed(user, 'reports.calves.view')):
        raise HTTPException(403, 'Bu raporu görme yetkiniz yok.')
    if reason not in REASON_KEYS and reason != 'calf':
        raise HTTPException(422, 'Geçerli çıkış nedeni seçin.')
    if section not in ('all', 'cattle', 'calf'):
        raise HTTPException(422, 'Geçerli bölüm seçin.')
    if reason == 'calf':
        section, reason_key = 'calf', None
    else:
        reason_key = REASON_KEYS[reason]
    rows = combined_exit_rows(db, request, date_from, date_to, reason_key, section)
    by_reason = {}
    for r in rows:
        bucket = by_reason.setdefault(r['reason_label'], {'label': r['reason_label'], 'count': 0, 'kg': Decimal(0)})
        bucket['count'] += 1
        bucket['kg'] += Decimal(r['exit_kg']) if r['exit_kg'] else Decimal(0)
    total_kg = sum((Decimal(r['exit_kg']) for r in rows if r['exit_kg']), Decimal(0))
    return rows, {'count': len(rows), 'total_kg': str(total_kg),
                  'by_reason': [{**b, 'kg': str(b['kg'])} for b in by_reason.values()]}


@router.get('/api/reports/animal-exits')
def animal_exits(request: Request, date_from: date | None = None, date_to: date | None = None,
                 reason: str = '', section: str = 'all', db: Session = Depends(get_db)):
    rows, totals = _exit_report(request, db, date_from, date_to, reason, section)
    return {'rows': rows, 'totals': totals}


@router.get('/api/reports/animal-exits.csv')
def animal_exits_csv(request: Request, date_from: date | None = None, date_to: date | None = None,
                     reason: str = '', section: str = 'all', db: Session = Depends(get_db)):
    user = current_user(request)
    if not (allowed(user, 'reports.animals.export') or allowed(user, 'reports.calves.export')):
        raise HTTPException(403, 'Bu raporu dışa aktarma yetkiniz yok.')
    rows, totals = _exit_report(request, db, date_from, date_to, reason, section)
    stream = io.StringIO()
    stream.write('﻿')
    writer = csv.writer(stream, delimiter=';')
    writer.writerow(['Tarih', 'Bölüm', 'TR Küpe No', 'İşletme Küpe No', 'Grup No', 'Çıkış Nedeni', 'Nereye Gittiği', 'Çıkış Kilosu (kg)'])

    def safe(value):
        value = str(value or '')
        return "'" + value if value[:1] in ('=', '+', '-', '@', '\t', '\r') else value

    for r in rows:
        writer.writerow([safe(x) for x in (date.fromisoformat(r['exit_date']).strftime('%d.%m.%Y'), r['section'], r['tr_ear_tag'],
                                           r['farm_ear_tag'], r['group_no'], r['reason_label'], r['destination'],
                                           _num(Decimal(r['exit_kg'])) if r['exit_kg'] else '')])
    writer.writerow([])
    writer.writerow(['Toplam', f"{totals['count']} baş", '', '', '', '', '', _num(Decimal(totals['total_kg']))])
    return StreamingResponse(iter([stream.getvalue().encode('utf-8')]), media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition': 'attachment; filename="hayvan_cikis_raporu.csv"'})
