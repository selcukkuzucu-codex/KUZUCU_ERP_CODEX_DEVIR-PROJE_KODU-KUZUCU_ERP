"""v0.16: tarihli rapor cümleleri, Hayvan Çıkış Raporu, olağandışı giriş uyarıları,
stoktan ürün ekleme, çıkışta yedek ve Ana Sayfa göstergeleri."""
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import backup, main
from app.checks import parse_report_dates
from app.db import get_db

TODAY = date(2026, 11, 11)


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'v016.sqlite3'), connect_args={'check_same_thread': False})
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR', str(tmp_path / 'pdf'))

    def localdb():
        with factory() as s:
            yield s
    monkeypatch.setitem(main.app.dependency_overrides, get_db, localdb)
    with TestClient(main.app) as c:
        yield c, tmp_path
    engine.dispose()


def post(c, path, data=None, code=201):
    response = c.post(path, json=data)
    assert response.status_code == code, response.text
    return response.json()


def animal(c, tag='TR001', pen=None, arrival='2026-09-01', kg='300'):
    pen = pen or post(c, '/api/pens', {'code': 'G-' + tag, 'capacity': 10})['id']
    return post(c, '/api/animals', {'tr_ear_tag': tag, 'arrival_date': arrival, 'entry_weight_kg': kg, 'pen_id': pen})


# ---------------- Rapor cümlesinden tarih ----------------

@pytest.mark.parametrize('text,expected', [
    ('1 Ekim ile 31 Ekim arasında kesilen hayvanlar', (date(2026, 10, 1), date(2026, 10, 31))),
    ('01.10.2026 - 15.10.2026 kesim', (date(2026, 10, 1), date(2026, 10, 15))),
    ('Ekim 2026 kesilen hayvanlar', (date(2026, 10, 1), date(2026, 10, 31))),
    ('2026 şubat hayvan çıkışları', (date(2026, 2, 1), date(2026, 2, 28))),
    ('geçen ay ölen hayvanlar', (date(2026, 10, 1), date(2026, 10, 31))),
    ('bu yıl satılan hayvanlar', (date(2026, 1, 1), TODAY)),
    ('son 30 gün kesilenler', (TODAY - timedelta(days=29), TODAY)),
    ('15 Aralık ile 10 Ocak arası', (date(2025, 12, 15), date(2026, 1, 10))),
    ('kesilen hayvanlar', (None, None)),
])
def test_parse_report_dates(text, expected):
    assert parse_report_dates(text, TODAY) == expected


def test_sentence_dates_and_calves_in_exit_report(pilot):
    c, _ = pilot
    a = animal(c, 'TR100')
    b = animal(c, 'TR101')
    post(c, '/api/animal-operations/bulk-exit', {'exit_date': '2026-10-05', 'reason': 'slaughter', 'destination': 'Mezbaha',
         'entries': [{'animal_id': a['id'], 'exit_kg': '550'}]}, 200)
    post(c, '/api/animal-operations/bulk-exit', {'exit_date': '2026-11-02', 'reason': 'slaughter', 'destination': 'Mezbaha',
         'entries': [{'animal_id': b['id'], 'exit_kg': '600'}]}, 200)
    result = post(c, '/api/reports/query', {'query': '1 Ekim 2026 ile 31 Ekim 2026 arasında kesilen hayvanlar'}, 200)
    assert result['scope'] == 'reports.animals' and result['row_count'] == 1
    assert result['rows'][0][2] == 'TR100' and result['date_from'] == '2026-10-01' and result['date_to'] == '2026-10-31'
    assert 'Toplam 1 baş, 550 kg' in result['notice']
    # Eski yazımla ("kesim") ve tarih kutularıyla da çalışır; kutular cümleye üstün gelir.
    boxed = post(c, '/api/reports/query', {'query': 'Ekim 2026 kesim hayvan çıkışları', 'date_from': '2026-11-01'}, 200)
    assert [r[2] for r in boxed['rows']] == ['TR101']

    calf = post(c, '/api/calves', {'tr_ear_tag': 'TRB1', 'sex': 'female', 'entry_date': '2026-08-01', 'entry_kg': '45',
                                   'planned_days': 45, 'group_no': 'C1'})
    post(c, f"/api/calves/{calf['id']}/exit", {'exit_date': '2026-10-10', 'exit_kg': '95'}, 200)
    both = c.get('/api/reports/animal-exits', params={'date_from': '2026-10-01', 'date_to': '2026-10-31'}).json()
    assert {r['section'] for r in both['rows']} == {'Besi', 'Buzağı'}
    assert both['totals']['count'] == 2 and both['totals']['total_kg'] == '645.000'
    only_calf = c.get('/api/reports/animal-exits', params={'reason': 'calf'}).json()
    assert [r['tr_ear_tag'] for r in only_calf['rows']] == ['TRB1']
    csv = c.get('/api/reports/animal-exits.csv', params={'date_from': '2026-10-01', 'date_to': '2026-10-31'})
    assert csv.status_code == 200 and csv.content.startswith(b'\xef\xbb\xbf')
    assert 'Buzağı çıkışı' in csv.text and 'Toplam;2 baş' in csv.text
    assert c.get('/api/reports/animal-exits', params={'date_from': '2026-11-01', 'date_to': '2026-10-01'}).status_code == 422


def test_exit_report_permissions(pilot):
    c, _ = pilot
    post(c, '/api/auth/users', {'username': 'calisan', 'password': 'CalisanParola2026', 'display_name': 'Çalışan',
                                'permissions': ['hayvanlar.kart.view']})
    login = c.post('/api/auth/login', json={'username': 'calisan', 'password': 'CalisanParola2026'})
    c.headers['X-CSRF-Token'] = login.json()['csrf_token']
    assert c.get('/api/reports/animal-exits').status_code == 403
    assert c.get('/api/reports/animal-exits.csv').status_code == 403
    assert c.post('/api/backups/now').status_code == 403
    status = c.get('/api/backups/status').json()
    assert 'directory' not in status  # klasör yolu yalnız yöneticiye


# ---------------- Olağandışı giriş uyarıları ----------------

def test_weighing_hard_errors_and_confirmable_warnings(pilot):
    c, _ = pilot
    a = animal(c, 'TR200', arrival='2026-09-01', kg='300')
    url = f"/api/animals/{a['id']}/weighings"
    future = (date.today() + timedelta(days=5)).isoformat()
    assert c.post(url, json={'measured_at': future, 'weight_kg': '320'}).status_code == 422
    assert c.post(url, json={'measured_at': '2026-08-01', 'weight_kg': '320'}).status_code == 422
    warn = c.post(url, json={'measured_at': '2026-10-01', 'weight_kg': '3900'})
    assert warn.status_code == 409 and warn.json()['detail']['code'] == 'unusual'
    assert any('olağandışı' in w for w in warn.json()['detail']['warnings'])
    jump = c.post(url, json={'measured_at': '2026-09-02', 'weight_kg': '330'})
    assert jump.status_code == 409 and 'günlük değişim' in jump.json()['detail']['message']
    assert c.post(url, json={'measured_at': '2026-10-01', 'weight_kg': '345'}).status_code == 201
    assert c.post(url + '?onay=1', json={'measured_at': '2026-10-02', 'weight_kg': '900'}).status_code == 201
    post(c, '/api/animal-operations/bulk-exit', {'exit_date': '2026-10-05', 'reason': 'death', 'destination': '',
         'entries': [{'animal_id': a['id']}]}, 200)
    exited = c.post(url + '?onay=1', json={'measured_at': '2026-10-06', 'weight_kg': '350'})
    assert exited.status_code == 409 and 'Çıkışı yapılmış' in exited.json()['detail']


def test_parcel_area_and_stock_shortage_messages(pilot):
    c, _ = pilot
    big = c.post('/api/fields', json={'code': 'P-1', 'name': 'Tarla', 'area_decare': '125000'})
    assert big.status_code == 409 and big.json()['detail']['code'] == 'unusual'
    assert c.post('/api/fields?onay=1', json={'code': 'P-1', 'name': 'Tarla', 'area_decare': '125000'}).status_code == 201
    item = post(c, '/api/items', {'code': 'ARPA', 'name': 'Arpa', 'unit': 'kg'})
    post(c, '/api/stock-movements', {'item_id': item['id'], 'type': 'IN', 'quantity': '1000', 'movement_date': '2026-10-01'})
    short = c.post('/api/stock-movements', json={'item_id': item['id'], 'type': 'OUT', 'quantity': '5000', 'movement_date': '2026-10-02'})
    assert short.status_code == 409 and 'elde 1.000, çıkış 5.000' in short.json()['detail']


def test_invoice_price_far_from_average_needs_confirmation(pilot):
    c, _ = pilot
    firm = post(c, '/api/firms', {'name': 'Yemci', 'tax_no': None, 'phone': '', 'address': ''})
    item = post(c, '/api/items', {'code': 'ARPA', 'name': 'Arpa', 'unit': 'kg'})
    line = lambda price: {'item_id': item['id'], 'unit': 'kg', 'quantity': '1000', 'unit_price': price, 'vat_rate': '10'}
    first = post(c, '/api/finance/invoices', {'kind': 'purchase', 'firm_id': firm['id'], 'invoice_no': 'A1',
                 'invoice_date': '2026-10-01', 'lines': [line('8.40')]})
    post(c, f"/api/finance/invoices/{first['id']}/post", None, 200)
    odd = c.post('/api/finance/invoices', json={'kind': 'purchase', 'firm_id': firm['id'], 'invoice_no': 'A2',
                 'invoice_date': '2026-10-02', 'lines': [line('85')]})
    assert odd.status_code == 409 and 'ortalaması 8,4 TL' in odd.json()['detail']['message']
    assert c.post('/api/finance/invoices?onay=1', json={'kind': 'purchase', 'firm_id': firm['id'], 'invoice_no': 'A2',
                  'invoice_date': '2026-10-02', 'lines': [line('85')]}).status_code == 201


# ---------------- Stoktan yeni ürün ----------------

def test_new_item_from_stock_screen_rules(pilot):
    c, _ = pilot
    item = post(c, '/api/items', {'code': ' SILAJ ', 'name': ' Mısır Silajı ', 'unit': 'Litre'})
    assert item['code'] == 'SILAJ' and item['name'] == 'Mısır Silajı' and item['unit'] == 'lt'
    assert 'Ürün kodu zaten kayıtlı' in c.post('/api/items', json={'code': 'silaj', 'name': 'Başka', 'unit': 'kg'}).json()['detail']
    assert 'Bu adla ürün zaten kayıtlı' in c.post('/api/items', json={'code': 'S2', 'name': 'mısır silajı', 'unit': 'kg'}).json()['detail']
    assert c.post('/api/items', json={'code': 'S3', 'name': 'Saman', 'unit': 'çuval'}).status_code == 422
    settings = c.put(f"/api/finance/items/{item['id']}/settings", json={'category': 'rawmaterial', 'alarm_threshold': '20000'})
    assert settings.status_code == 200, settings.text


# ---------------- Yedek ----------------

def test_logout_takes_backup_and_status(pilot):
    c, tmp = pilot
    status = c.get('/api/backups/status').json()
    assert status['directory'].endswith('backups')
    out = c.post('/api/auth/logout')
    assert out.status_code == 200 and out.json()['backup_ok'] is True and 'Yedek alındı' in out.json()['message']
    assert list((tmp / 'backups').glob('kuzucu_cikis_*.sqlite3'))


def test_manual_backup_by_admin(pilot):
    c, tmp = pilot
    r = c.post('/api/backups/now')
    assert r.status_code == 200 and r.json()['count'] >= 1
    assert list((tmp / 'backups').glob('kuzucu_elle_*.sqlite3'))


def test_prune_keeps_recent_daily_and_monthly(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, 'KEEP_MIN', 3)
    now = datetime(2026, 11, 11, 12, 0)
    made = []
    for days_ago, hours in [(0, 1), (0, 2), (1, 5), (5, 1), (5, 2), (10, 1), (40, 1), (41, 1), (75, 1), (75, 2)]:
        f = tmp_path / f'kuzucu_otomatik_{days_ago}_{hours}.sqlite3'
        f.write_bytes(b'x')
        ts = (now - timedelta(days=days_ago, hours=hours)).timestamp()
        os.utime(f, (ts, ts))
        made.append((days_ago, hours, f))
    other = tmp_path / 'kisisel_dosya.sqlite3'
    other.write_bytes(b'y')
    os.utime(other, (0, 0))
    removed = backup.prune_backups(tmp_path, now=now)
    left = {(d, h) for d, h, f in made if f.exists()}
    assert (0, 1) in left and (0, 2) in left and (1, 5) in left      # son 2 gün
    assert (5, 1) in left and (5, 2) not in left                      # günde bir
    assert (10, 1) in left
    assert len({(40, 1), (41, 1)} & left) == 1                        # aynı ay: bir tane
    assert (75, 1) in left and (75, 2) not in left
    assert other.exists() and removed == 3


# ---------------- Ana Sayfa ----------------

def test_dashboard_insights_empty_and_with_data(pilot):
    c, _ = pilot
    empty = c.get('/api/dashboard/insights')
    assert empty.status_code == 200, empty.text
    labels = {x['label'] for x in empty.json()['cards']}
    assert {'Aktif besi hayvanı', 'Ortalama günlük artış', 'Yem stoğu yeter'} <= labels
    pen = post(c, '/api/pens', {'code': 'G-1', 'capacity': 1})['id']
    a = animal(c, 'TR300', pen=pen, arrival='2026-09-01', kg='300')
    post(c, f"/api/animals/{a['id']}/weighings", {'measured_at': '2026-09-16', 'weight_kg': '322.5'})
    item = post(c, '/api/items', {'code': 'ARPA', 'name': 'Arpa', 'unit': 'kg'})
    c.put(f"/api/finance/items/{item['id']}/settings", json={'category': 'rawmaterial', 'alarm_threshold': None})
    from app.calf import today_local
    d = today_local()
    post(c, '/api/stock-movements', {'item_id': item['id'], 'type': 'IN', 'quantity': '3000', 'movement_date': (d - timedelta(days=20)).isoformat()})
    post(c, '/api/stock-movements', {'item_id': item['id'], 'type': 'OUT', 'quantity': '1500', 'movement_date': (d - timedelta(days=2)).isoformat()})
    data = c.get('/api/dashboard/insights').json()
    cards = {x['key']: x for x in data['cards']}
    assert cards['active']['value'] == '1 baş'
    assert cards['gain']['value'] == '1,50 kg/gün'
    assert cards['feed']['value'] == '30 gün' and 'Arpa' in cards['feed']['note']
    assert any('tartılmadı' in x['title'] for x in data['checks'])  # son tartım 16 Eylül: 45 günden eski


def test_dashboard_insights_respect_permissions(pilot):
    c, _ = pilot
    post(c, '/api/auth/users', {'username': 'izleyici', 'password': 'IzleyiciParola2026', 'display_name': 'İzleyici',
                                'permissions': ['dashboard.view']})
    login = c.post('/api/auth/login', json={'username': 'izleyici', 'password': 'IzleyiciParola2026'})
    c.headers['X-CSRF-Token'] = login.json()['csrf_token']
    data = c.get('/api/dashboard/insights').json()
    assert data['cards'] == [] and data['checks'] == [] and data['todos'] == []


def test_static_v016_assets_and_names():
    static = Path(main.__file__).parent / 'static'
    index = (static / 'index.html').read_text(encoding='utf-8')
    assert "['dashboard','Ana Sayfa']" in index and 'Genel Bakış' not in index
    assert "['cariler','Cariler']" in index and "['firms'," not in index and "['hesaplar'," not in index
    assert '/static/v16.js?v=016' in index and '/static/v16.css?v=016' in index and 'kuzucu_logo.png' in index
    v16 = (static / 'v16.js').read_text(encoding='utf-8')
    assert 'window.renderNav' in v16 and 'cikisraporu' in v16
    assert (static / 'fonts' / 'inter-latin-ext-400-normal.woff2').is_file()
