"""v0.16: girişte olağandışı değer uyarıları ve rapor cümlelerinden tarih çıkarma.

Kesin hatalar HTTP 422 ile kaydı durdurur. Olağandışı ama mümkün değerler HTTP 409
`{"code": "unusual"}` döner; kullanıcı ekranda onaylarsa istek `?onay=1` ile yinelenir.
"""
import calendar
import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, Request

# Varsayılan makul aralıklar. İşletmeye göre gerekirse burada değiştirilebilir.
LIMITS = {
    'animal_min_kg': Decimal('30'),
    'animal_max_kg': Decimal('1200'),
    'calf_max_kg': Decimal('300'),
    'daily_gain_min': Decimal('-1'),
    'daily_gain_max': Decimal('3'),
    'field_max_decare': Decimal('20000'),
    'stock_large_quantity': Decimal('1000000'),
}


def confirmed(request: Request | None) -> bool:
    return bool(request) and request.query_params.get('onay') == '1'


def require_confirmation(request: Request | None, warnings: list[str]):
    """Uyarı varsa ve kullanıcı onaylamadıysa kaydı durdur."""
    warnings = [w for w in warnings if w]
    if warnings and not confirmed(request):
        raise HTTPException(409, {
            'code': 'unusual',
            'message': 'Olağandışı değer var, kontrol edin: ' + ' '.join(warnings),
            'warnings': warnings,
        })


def tr_kg(value) -> str:
    text = format(Decimal(str(value)).normalize(), 'f')
    whole, _, frac = text.partition('.')
    whole = f'{int(whole):,}'.replace(',', '.') if whole.lstrip('-').isdigit() else whole
    return whole + (',' + frac if frac else '')


def tr_date(value: date) -> str:
    return value.strftime('%d.%m.%Y')


def weighing_warnings(animal, weight: Decimal, measured_at: date, previous: list) -> list[str]:
    """previous: (tarih, kg) çiftleri; giriş tartımı dahil."""
    warnings = []
    if weight < LIMITS['animal_min_kg'] or weight > LIMITS['animal_max_kg']:
        warnings.append(f'{tr_kg(weight)} kg besi hayvanı için olağandışı (beklenen {tr_kg(LIMITS["animal_min_kg"])}–{tr_kg(LIMITS["animal_max_kg"])} kg).')
    earlier = [(d, kg) for d, kg in previous if d <= measured_at]
    if any(d == measured_at for d, _ in earlier):
        warnings.append('Bu hayvanın bu tarihte zaten bir tartımı var.')
    earlier = [(d, kg) for d, kg in earlier if d < measured_at]
    if earlier:
        last_day, last_kg = max(earlier, key=lambda x: x[0])
        days = (measured_at - last_day).days
        gain = (weight - Decimal(str(last_kg))) / days
        if gain < LIMITS['daily_gain_min'] or gain > LIMITS['daily_gain_max']:
            warnings.append(f'Son ölçüme ({tr_date(last_day)}, {tr_kg(last_kg)} kg) göre günlük değişim {tr_kg(round(gain, 2))} kg; yazım hatası olabilir.')
    return warnings


# ---------------- Rapor cümlesinden tarih ----------------

MONTHS = {'ocak': 1, 'subat': 2, 'mart': 3, 'nisan': 4, 'mayis': 5, 'haziran': 6, 'temmuz': 7,
          'agustos': 8, 'eylul': 9, 'ekim': 10, 'kasim': 11, 'aralik': 12}
_MONTH_RE = '(' + '|'.join(MONTHS) + ')'


def _norm(text: str) -> str:
    text = str(text or '').lower().replace('ı', 'i')
    return ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_report_dates(query: str, today: date | None = None) -> tuple[date | None, date | None]:
    """'1 Ekim ile 31 Ekim arasında', '01.10.2026-31.10.2026', 'Ekim 2026', 'geçen ay',
    'bu yıl', 'son 30 gün' gibi ifadelerden tarih aralığı çıkarır. Bulamazsa (None, None)."""
    today = today or date.today()
    q = _norm(query)

    numeric = re.findall(r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b', q)
    found = [d for d in (_safe_date(int(y), int(m), int(dd)) for dd, m, y in numeric) if d]
    if len(found) >= 2:
        return min(found[:2]), max(found[:2])
    if len(found) == 1:
        if any(w in q for w in ('sonra', 'itibaren', 'beri')):
            return found[0], None
        if any(w in q for w in ('once', 'kadar')):
            return None, found[0]
        return found[0], found[0]

    # '1 Ekim ile 31 Ekim', '1 ekim 2026 - 15 kasim 2026'
    pairs = re.findall(r'\b(\d{1,2})\s+' + _MONTH_RE + r'(?:\s+(\d{4}))?', q)
    if pairs:
        dates = []
        for dd, month, year in pairs:
            y = int(year) if year else None
            dates.append((int(dd), MONTHS[month], y))
        explicit_year = next((y for _, _, y in dates if y), None)
        resolved = []
        for dd, m, y in dates:
            year = y or explicit_year or today.year
            d = _safe_date(year, m, dd)
            if d:
                resolved.append(d)
        if len(resolved) >= 2:
            start, end = resolved[0], resolved[1]
            if end < start and not any(y for *_, y in dates):
                start = _safe_date(start.year - 1, start.month, start.day) or start
            return min(start, end), max(start, end)
        if len(resolved) == 1:
            if any(w in q for w in ('sonra', 'itibaren', 'beri')):
                return resolved[0], None
            if any(w in q for w in ('once', 'kadar')):
                return None, resolved[0]
            return resolved[0], resolved[0]

    # 'Ekim 2026', '2026 Ekim', 'ekim ayi'
    m = re.search(_MONTH_RE + r'\s+(\d{4})', q) or re.search(r'(\d{4})\s+' + _MONTH_RE, q)
    if m:
        a, b = m.groups()
        month, year = (MONTHS[a], int(b)) if a in MONTHS else (MONTHS[b], int(a))
        return date(year, month, 1), _month_end(year, month)
    m = re.search(_MONTH_RE + r'\s+ay', q)
    if m:
        month = MONTHS[m.group(1)]
        year = today.year if month <= today.month else today.year - 1
        return date(year, month, 1), _month_end(year, month)

    m = re.search(r'son\s+(\d{1,4})\s+gun', q)
    if m:
        return today - timedelta(days=int(m.group(1)) - 1), today
    if 'bugun' in q:
        return today, today
    if 'dun' in q.split() or 'dunku' in q:
        return today - timedelta(days=1), today - timedelta(days=1)
    if 'bu hafta' in q:
        start = today - timedelta(days=today.weekday())
        return start, today
    if 'gecen hafta' in q:
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6)
    if 'bu ay' in q:
        return today.replace(day=1), today
    if 'gecen ay' in q:
        last = today.replace(day=1) - timedelta(days=1)
        return last.replace(day=1), last
    if 'bu yil' in q:
        return date(today.year, 1, 1), today
    if 'gecen yil' in q:
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    m = re.search(r'\b(20\d{2})\s*(?:yili|yilinda|yilindaki)\b', q)
    if m:
        y = int(m.group(1))
        return date(y, 1, 1), date(y, 12, 31)
    return None, None
