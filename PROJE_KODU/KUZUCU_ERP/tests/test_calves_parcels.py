"""v0.11: old-data compatible animal, parcel image and calf bulk exit tests."""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import sqlite3
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main
from app.db import get_db


def isolate(tmp_path,monkeypatch):
    engine=create_engine(f'sqlite:///{tmp_path/"pilot.db"}',connect_args={'check_same_thread':False})
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setattr(main,'PARCEL_IMAGE_DIR',tmp_path/'uploaded_parcels')
    monkeypatch.setenv('KUZUCU_REPORT_DIR',str(tmp_path/'raporlar'))
    maker=sessionmaker(bind=engine)
    def local_db():
        with maker() as db:yield db
    main.app.dependency_overrides[get_db]=local_db
    return engine


def test_animals_and_parcel_images(tmp_path,monkeypatch):
    eng=isolate(tmp_path,monkeypatch)
    try:
        with TestClient(main.app) as c:
            pen=c.post('/api/pens',json={'code':'BUZ-3','capacity':20}).json()['id']
            birth=(date.today()-timedelta(days=80)).isoformat()
            animal=c.post('/api/animals',json={'tr_ear_tag':'TR-0011','farm_ear_tag':'IS-0001','sex':'female',
                   'birth_date':birth,'breed':'Simental','arrival_date':date.today().isoformat(),
                   'entry_weight_kg':'70.250','pen_id':pen})
            assert animal.status_code==201,animal.text
            a=animal.json();assert a['tr_ear_tag']=='TR-0011' and a['age_days']==80
            assert a['farm_ear_tag']=='IS-0001' and a['sex']=='female'
            duplicate=c.post('/api/animals',json={'tr_ear_tag':'TR-0022','farm_ear_tag':'IS-0001',
                  'arrival_date':date.today().isoformat(),'entry_weight_kg':'80','pen_id':pen})
            assert duplicate.status_code==409
            edit=c.put(f'/api/animals/{a["id"]}',json={'tr_ear_tag':'TR-0011','farm_ear_tag':'IS-0099',
                  'birth_date':birth,'sex':'female','arrival_date':date.today().isoformat(),
                  'entry_weight_kg':'75.750','pen_id':pen})
            assert edit.status_code==200 and edit.json()['farm_ear_tag']=='IS-0099'
            field=c.post('/api/fields',json={'ada_no':'155','code':'42','name':'Kuzey Tarla','area_decare':'35.500'})
            assert field.status_code==201
            id=field.json()['id']
            assert len(c.get('/api/fields?search=155').json())==1
            assert len(c.get('/api/fields?search=kUzEy').json())==1
            assert len(c.get('/api/fields?search=99999').json())==0
            assert c.get(f'/api/fields/{id}/satellite-image').status_code==404
            picture=Image.new('RGB',(20,20),color=(70,135,80));b=BytesIO();picture.save(b,format='PNG')
            resp=c.post(f'/api/fields/{id}/satellite-image',files={'file':('tarla.png',b.getvalue(),'image/png')})
            assert resp.status_code==200,resp.text
            assert c.get(f'/api/fields/{id}/satellite-image').headers['content-type']=='image/jpeg'
            assert c.post(f'/api/fields/{id}/satellite-image',files={'file':('bad.png',b'garbage','image/png')}).status_code==422
            assert c.get('/api/fields').json()[0]['satellite_image']
    finally:
        main.app.dependency_overrides.clear();eng.dispose()


def test_calves_daily_intake_bulk_exit_adg_csv(tmp_path,monkeypatch):
    eng=isolate(tmp_path,monkeypatch)
    today=date.today();entry=today-timedelta(days=45)
    try:
        with TestClient(main.app) as c:
            ids=[]
            for tag,sex,weight,days in [('TR-C01','male','50',45),('TR-C02','female','40',60)]:
                result=c.post('/api/calves',json={'tr_ear_tag':tag,'farm_ear_tag':tag+'-IS',
                    'sex':sex,'entry_date':entry.isoformat(),'entry_kg':weight,
                    'batch_code':'KASIM-2026','planned_days':days})
                assert result.status_code==201,result.text
                assert result.json()['status']=='active'
                ids.append(result.json()['id'])
            assert c.post('/api/calves',json={'tr_ear_tag':'TR-C01','sex':'male',
                    'entry_date':entry.isoformat(),'entry_kg':'10'}).status_code==409
            bad=c.post(f'/api/calves/{ids[0]}/consumptions',json={
               'consumed_on':(entry-timedelta(days=1)).isoformat(),'milk_kg':'3','feed_kg':'0'})
            assert bad.status_code==422
            payload={'consumed_on':entry.isoformat(),'milk_kg':'4.500','feed_kg':'1.250','notes':'Günlük kontrol'}
            first=c.post(f'/api/calves/{ids[0]}/consumptions',json=payload)
            assert first.status_code==201,first.text
            assert c.post(f'/api/calves/{ids[0]}/consumptions',json=payload).status_code==409
            updated=c.put(f'/api/calves/{ids[0]}/consumptions/{first.json()["id"]}',json={
                **payload,'milk_kg':'5.000'})
            assert updated.status_code==200
            assert c.post(f'/api/calves/{ids[0]}/weighings',json={'measured_on':entry.isoformat(),
                'weight_kg':'52.5'}).status_code==201
            invalid=c.post('/api/calves/bulk-exit',json={'exit_date':today.isoformat(),'entries':[
                {'calf_id':ids[0],'exit_kg':'95'},{'calf_id':999999,'exit_kg':'85'}]})
            assert invalid.status_code==404
            assert all(r['status']=='active' for r in c.get('/api/calves').json())
            bulk=c.post('/api/calves/bulk-exit',json={'exit_date':today.isoformat(),'entries':[
                {'calf_id':ids[0],'exit_kg':'95'},{'calf_id':ids[1],'exit_kg':'85'}]})
            assert bulk.status_code==200,bulk.text
            assert bulk.json()['count']==2
            assert c.post('/api/calves/bulk-exit',json={'exit_date':today.isoformat(),
                    'entries':[{'calf_id':ids[0],'exit_kg':'95'}]}).status_code==409
            rows=c.get('/api/calves?status=exited&batch_code=KASIM-2026').json()
            assert len(rows)==2
            r1=next(r for r in rows if r['id']==ids[0])
            assert r1['days']==45 and r1['gain_kg']=='45.000' and r1['adg_kg_day']=='1.000'
            assert r1['exit_entry_ratio']=='1.900' and r1['gain_percent']=='90.000'
            assert r1['milk_total_kg']=='5.000' and r1['feed_total_kg']=='1.250'
            report=c.get('/api/calves/exit-report?batch_code=KASIM-2026')
            assert report.status_code==200
            summary=report.json()['summary']
            assert summary['count']==2
            assert summary['total_entry_kg']=='90.000' and summary['total_exit_kg']=='180.000'
            assert summary['total_gain_kg']=='90.000' and summary['weighted_adg_kg_day']=='1.000'
            assert summary['overall_exit_entry_ratio']=='2.000'
            assert c.get('/api/calves/exit-report?batch_code=nonexistent').json()['summary']['count']==0
            csv=c.get('/api/calves/exit-report.csv?batch_code=KASIM-2026')
            assert csv.status_code==200 and csv.content.startswith(b'\xef\xbb\xbf') and 'TR-C01' in csv.text
            assert c.get('/static/calves.js').status_code==200
            assert c.get('/static/parcels.js').status_code==200
            assert 'Buzağı Giriş / Çıkış' in c.get('/').text
    finally:
        main.app.dependency_overrides.clear();eng.dispose()


def test_migration_old_database(tmp_path,monkeypatch):
    file=tmp_path/'legacy.db'
    with sqlite3.connect(file) as con:
        con.execute('CREATE TABLE pens (id INTEGER PRIMARY KEY, code VARCHAR(40), capacity INTEGER)')
        con.execute('CREATE TABLE animals (id INTEGER PRIMARY KEY, ear_tag VARCHAR(60), breed VARCHAR(80), arrival_date DATE, entry_weight_kg NUMERIC, pen_id INTEGER, status VARCHAR(20))')
        con.execute('CREATE TABLE fields (id INTEGER PRIMARY KEY, code VARCHAR(40), name VARCHAR(120), area_decare NUMERIC, ada_no VARCHAR(40))')
        con.execute("INSERT INTO pens VALUES(1,'OLD-PEN',10)")
        con.execute("INSERT INTO animals VALUES(1,'TR-LEGACY','Simental','2025-02-01',135,1,'active')")
        con.execute("INSERT INTO fields VALUES(1,'OLD-FIELD','Eski Tarla',50,'87')")
    engine=create_engine(f'sqlite:///{file}',connect_args={'check_same_thread':False})
    monkeypatch.setattr(main,'engine',engine)
    maker=sessionmaker(bind=engine)
    def local_db():
        with maker() as db:yield db
    main.app.dependency_overrides[get_db]=local_db
    try:
        with TestClient(main.app) as c:
            old=c.get('/api/animals').json()
            assert old[0]['ear_tag']=='TR-LEGACY' and old[0]['farm_ear_tag'] is None
            assert old[0]['tr_ear_tag']=='TR-LEGACY' and old[0]['birth_date'] is None
            field=c.get('/api/fields').json()
            assert field[0]['code']=='OLD-FIELD' and field[0]['satellite_image'] is None
            assert c.get('/api/calves').status_code==200
    finally:
        main.app.dependency_overrides.clear();engine.dispose()
