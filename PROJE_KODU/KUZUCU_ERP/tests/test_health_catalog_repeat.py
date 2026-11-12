"""v0.12: İlaç/tedavi seçme sözlüğü ve 10 günlük tekrar-ilaç uyarısı."""
from datetime import timedelta

from fastapi.testclient import TestClient

from app import main
from app.animal_health import today_local
from test_animal_health import isolate, make_case


def _animal(client, tag):
    pen = client.post('/api/pens', json={'code': f'P-{tag}', 'capacity': 30})
    assert pen.status_code == 201, pen.text
    return client.post('/api/animals', json={'ear_tag': tag,
        'arrival_date': today_local().isoformat(), 'entry_weight_kg': '250',
        'pen_id': pen.json()['id']}).json()['id']


def test_catalog_and_repeat_warning_on_second_course(tmp_path, monkeypatch):
    engine = isolate(tmp_path, monkeypatch)
    today = today_local()
    try:
        with TestClient(main.app) as c:
            animal = _animal(c, 'TR-SAME-001')
            other = _animal(c, 'TR-OTHER-002')
            first = make_case(animal, today-timedelta(days=7),
                              planned_end_date=(today-timedelta(days=4)).isoformat(),
                              product_name='İlaç A', treatment_name='Solunum Takip Protokolü')
            r = c.post('/api/animal-health/cases', json=first)
            assert r.status_code == 201, r.text
            first_id = r.json()['id']
            catalog = c.get('/api/animal-health/catalog').json()
            assert catalog['medications'] == ['İlaç A']
            assert catalog['treatments'] == ['Solunum Takip Protokolü']
            assert c.post('/api/animal-health/catalog', json={
                'kind': 'medication', 'name': '  ilaç  a  '}).status_code == 201
            assert len(c.get('/api/animal-health/catalog').json()['medications']) == 1
            assert c.post('/api/animal-health/catalog', json={
                'kind': 'treatment', 'name': 'Viral Hastalık Takibi'}).status_code == 201
            assert len(c.get('/api/animal-health/catalog').json()['treatments']) == 2
            assert c.post('/api/animal-health/catalog', json={'kind':'bad','name':'X'}).status_code == 422

            # Aynı tedavi planı içinde veterinerin öngördüğü 2 doz engellenmemeli.
            log = {'performed_on': (today-timedelta(days=6)).isoformat(),
                   'performed_by': 'Personel', 'response': 'improved'}
            assert c.post(f'/api/animal-health/cases/{first_id}/logs', json=log).status_code == 201
            assert c.post(f'/api/animal-health/cases/{first_id}/logs', json=log).status_code == 201
            matches = c.get('/api/animal-health/repeat-check', params={
                'animal_id': animal, 'product_name':'ilaç a', 'on': today.isoformat()}).json()
            assert matches['warning'] and matches['matches'][0]['days_ago'] == 6
            assert 'TR-SAME-001' == matches['matches'][0]['ear_tag']
            assert not c.get('/api/animal-health/repeat-check', params={
                'animal_id': other, 'product_name':'İlaç A', 'on': today.isoformat()}).json()['warning']

            duplicate = make_case(animal, today, product_name='ilaç a',
                                  treatment_name='Aynı ürün yeni planı')
            denied = c.post('/api/animal-health/cases', json=duplicate)
            assert denied.status_code == 409
            assert denied.json()['detail']['code'] == 'SAME_MEDICATION_WITHIN_10_DAYS'
            # Onaylı olmayan plan saklanabilir ama uygulama kaydı engellenir.
            draft = c.post('/api/animal-health/cases', json={**duplicate,'vet_approved':False})
            assert draft.status_code == 201, draft.text
            draft_id = draft.json()['id']
            assert c.post(f'/api/animal-health/cases/{draft_id}/logs',json={
                'performed_on':today.isoformat(),'performed_by':'Ali'}).status_code == 409
            assert c.put(f'/api/animal-health/cases/{draft_id}',json=duplicate).status_code == 409
            approved = c.put(f'/api/animal-health/cases/{draft_id}',json={
                **duplicate, 'repeat_review_confirmed':True})
            assert approved.status_code == 200, approved.text
            assert approved.json()['repeat_review_confirmed'] is True
            performed = c.post(f'/api/animal-health/cases/{draft_id}/logs',json={
                'performed_on':today.isoformat(),'performed_by':'Ali'})
            assert performed.status_code == 201, performed.text
            # 11 gün sonra artık bu eşiğe takılmaz.
            future = today+timedelta(days=11)
            assert not c.get('/api/animal-health/repeat-check',params={
                'animal_id':animal,'product_name':'İlaç A','on':future.isoformat()}).json()['warning']
            # Başka hayvanda aynı ad tekrar olabilir.
            assert c.post('/api/animal-health/cases',json=make_case(
                other,today,product_name='İlaç A')).status_code == 201
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_first_application_checks_other_active_case(tmp_path, monkeypatch):
    engine = isolate(tmp_path, monkeypatch)
    today = today_local()
    try:
        with TestClient(main.app) as c:
            a = _animal(c,'TR-COMPARE')
            # Aynı anda iki plan açılmış ancak henüz uygulama yapılmamış.
            one = c.post('/api/animal-health/cases',json=make_case(a,today,
                product_name='Ürün D',applications_per_day=1)).json()['id']
            two = c.post('/api/animal-health/cases',json=make_case(a,today,
                product_name='Ürün D',applications_per_day=1)).json()['id']
            log={'performed_on':today.isoformat(),'performed_by':'Veteriner'}
            assert c.post(f'/api/animal-health/cases/{one}/logs',json=log).status_code == 201
            blocked = c.post(f'/api/animal-health/cases/{two}/logs',json=log)
            assert blocked.status_code == 409
            assert blocked.json()['detail']['code'] == 'SAME_MEDICATION_WITHIN_10_DAYS'
            permitted = c.post(f'/api/animal-health/cases/{two}/logs',json={
                **log,'repeat_review_confirmed':True})
            assert permitted.status_code == 201
            assert c.get('/api/animal-health/cases',params={'animal_id':a}).json()[0]['repeat_review_confirmed'] is True
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
