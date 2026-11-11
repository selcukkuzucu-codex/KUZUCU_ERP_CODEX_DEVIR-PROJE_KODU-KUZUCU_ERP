"""Animal health: the veterinarian remains the sole source of treatment decisions."""
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main
from app.animal_health import TZ, scheduled_daily_tick, today_local
from app.db import get_db


def isolate(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "health_test.db"}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setenv('KUZUCU_REPORT_DIR', str(tmp_path / 'raporlar'))
    maker = sessionmaker(bind=engine)
    def local_db():
        with maker() as db:
            yield db
    main.app.dependency_overrides[get_db] = local_db
    return engine


def make_case(animal_id, start, **extra):
    values = dict(animal_id=animal_id, record_type='treatment', condition_name='Solunum belirtileri',
                  symptoms='Gözlenen klinik belirtiler', product_name='Vet planı A', dosage_text='Veteriner talimatı',
                  veterinarian='Dr. Vet', vet_approved=True, applications_per_day=2,
                  start_date=start.isoformat(), planned_end_date=(start+timedelta(days=3)).isoformat(),
                  withdrawal_end_date=(start+timedelta(days=10)).isoformat(), notes='Günlük gözlem')
    values.update(extra)
    return values


def test_health_crud_daily_and_pdf(tmp_path, monkeypatch):
    engine = isolate(tmp_path, monkeypatch)
    today = today_local()
    try:
        with TestClient(main.app) as c:
            pen = c.post('/api/pens', json={'code':'B-01', 'capacity':30}).json()['id']
            animal = c.post('/api/animals',json={'ear_tag':'TR123000011','breed':'Simental',
                'arrival_date':today.isoformat(), 'entry_weight_kg':'220', 'pen_id':pen}).json()['id']
            bad=c.post('/api/animal-health/cases',json=make_case(animal,today,planned_end_date=(today-timedelta(days=1)).isoformat()))
            assert bad.status_code==422
            not_approved=c.post('/api/animal-health/cases',json=make_case(animal,today,vet_approved=False))
            assert not_approved.status_code==201
            assert c.post(f'/api/animal-health/cases/{not_approved.json()["id"]}/logs',
                json={'performed_on':today.isoformat(),'performed_by':'Ahmet','observation':'Takip'}).status_code==409
            normal = c.post('/api/animal-health/cases',json=make_case(animal,today))
            assert normal.status_code==201,normal.text
            case_id=normal.json()['id']
            assert normal.json()['ear_tag']=='TR123000011'
            alert=c.post('/api/reminders',json={'title':'Aşı dolabı kontrolü','category':'Besi','frequency':'daily',
                    'start_date':today.isoformat(),'remind_time':'00:00'})
            assert alert.status_code==201
            report=c.get('/api/animal-health/daily',params={'on':today.isoformat()})
            assert report.status_code==200,report.text
            assert report.json()['totals']['due']==1
            assert report.json()['totals']['awaiting_approval']==1
            assert len(report.json()['reminders'])==1
            assert c.post(f'/api/animal-health/cases/{case_id}/logs',json={
                'performed_on':(today+timedelta(days=1)).isoformat(),'performed_by':'Ali'}).status_code==422
            log_payload={'performed_on':today.isoformat(),'performed_by':'Ali',
                         'observation':'Genel durumu izlendi','response':'improved'}
            l1=c.post(f'/api/animal-health/cases/{case_id}/logs',json=log_payload)
            assert l1.status_code==201,l1.text
            assert l1.json()['application_no']==1
            assert c.get('/api/animal-health/daily',params={'on':today.isoformat()}).json()['totals']['partially_done']==1
            l2=c.post(f'/api/animal-health/cases/{case_id}/logs',json=log_payload)
            assert l2.status_code==201 and l2.json()['application_no']==2
            assert c.post(f'/api/animal-health/cases/{case_id}/logs',json=log_payload).status_code==409
            report=c.get('/api/animal-health/daily',params={'on':today.isoformat()}).json()
            assert report['totals']['done']==1
            assert len(c.get(f'/api/animal-health/cases/{case_id}/logs').json())==2
            pdf=c.get('/api/animal-health/daily.pdf',params={'on':today.isoformat()})
            assert pdf.status_code==200,pdf.text[:200]
            assert pdf.content[:4]==b'%PDF'
            assert (tmp_path/'raporlar'/f'{today.isoformat()}_hayvan_sagligi_gunluk.pdf').exists()
            assert c.get('/api/animal-health/print-status').json()['report_date']==today.isoformat()
            close=c.post(f'/api/animal-health/cases/{case_id}/close',json={
                'closed_date':today.isoformat(),'outcome':'recovered','outcome_notes':'Veteriner değerlendirmesi'})
            assert close.status_code==200,close.text
            assert c.post(f'/api/animal-health/cases/{case_id}/logs',json=log_payload).status_code==409
            assert c.put(f'/api/animal-health/cases/{case_id}',json=make_case(animal,today)).status_code==409
            insight=c.get('/api/animal-health/insights',params={'condition':'SOLUNUM  belirtileri'}).json()
            assert insight['completed_vet_approved_cases']==1
            assert insight['past_protocols'][0]['positive']==1
            assert 'veteriner' in insight['warning'].lower()
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_health_vaccination_observation_and_expired_plan(tmp_path,monkeypatch):
    engine=isolate(tmp_path,monkeypatch)
    today=today_local()
    try:
        with TestClient(main.app) as c:
            pen=c.post('/api/pens',json={'code':'YENIDEN','capacity':100}).json()['id']
            animal=c.post('/api/animals',json={'ear_tag':'K-101','arrival_date':today.isoformat(),
                    'entry_weight_kg':'150','pen_id':pen}).json()['id']
            v=make_case(animal,today,record_type='vaccination',applications_per_day=1,
                        planned_end_date=today.isoformat())
            assert c.post('/api/animal-health/cases',json=v).status_code==201
            assert c.post('/api/animal-health/cases',json={**v,'applications_per_day':3}).status_code==422
            assert c.post('/api/animal-health/cases',json={**v,'vet_approved':True,'veterinarian':''}).status_code==422
            obs=c.post('/api/animal-health/cases',json={**v,'record_type':'observation',
                'condition_name':'Genel durum','product_name':'', 'vet_approved':False, 'veterinarian':''})
            assert obs.status_code==201
            old = c.post('/api/animal-health/cases',json=make_case(animal,today-timedelta(days=8),
                planned_end_date=(today-timedelta(days=3)).isoformat()))
            assert old.status_code==201,old.text
            daily=c.get('/api/animal-health/daily',params={'on':today.isoformat()}).json()
            assert any(r['case_id']==old.json()['id'] and r['status']=='review_expired' for r in daily['cases'])
            assert c.post(f'/api/animal-health/cases/{old.json()["id"]}/logs',json={
                'performed_on':today.isoformat(),'performed_by':'Ali'}).status_code==409
            assert c.post(f'/api/animal-health/cases/{old.json()["id"]}/close',json={
                'closed_date':today.isoformat(),'outcome':'recovered'}).status_code==409
            # Other observations can be logged without veterinarian approval.
            assert c.post(f'/api/animal-health/cases/{obs.json()["id"]}/logs',json={
                'performed_on':today.isoformat(),'performed_by':'Gözlemci'}).status_code==201
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_daily_auto_report_is_optin_for_physical_printer(tmp_path,monkeypatch):
    engine=isolate(tmp_path,monkeypatch)
    calls=[]
    monkeypatch.setattr('app.animal_health.send_to_printer',lambda path,printer_name='': calls.append((str(path),printer_name)) or 'yazıldı')
    try:
        with TestClient(main.app) as c:
            setting=c.get('/api/animal-health/print-settings').json()
            assert setting['auto_generate'] is True and setting['auto_print'] is False
            assert c.put('/api/animal-health/print-settings',json={'daily_time':'00:00',
                'auto_generate':True,'auto_print':False,'printer_name':''}).status_code==200
            scheduled_daily_tick(engine)
            assert Path(c.get('/api/animal-health/print-status').json()['pdf_path']).exists()
            assert not calls
            assert c.put('/api/animal-health/print-settings',json={'daily_time':'00:00',
                'auto_generate':True,'auto_print':True,'printer_name':'Ofis-Yazici'}).status_code==200
            scheduled_daily_tick(engine)
            scheduled_daily_tick(engine)
            assert len(calls)==1 and calls[0][1]=='Ofis-Yazici'
            assert c.get('/api/animal-health/print-status').json()['printed_at']
            assert c.get('/static/health.js').status_code==200
            assert c.get('/static/health.css').status_code==200
            assert 'Sağlık / Tedaviler' in c.get('/').text
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
