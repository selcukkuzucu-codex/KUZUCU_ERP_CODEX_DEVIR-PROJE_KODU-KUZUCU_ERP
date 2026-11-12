"""v0.13: mandatory sign-in, report isolation, auditing and manual calf bulk exit."""
from datetime import date,timedelta
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from app import main
from app.db import get_db
from app.security import AuditEvent, User

def make_client(tmp_path,monkeypatch):
    dbfile=tmp_path/'pilot.db'
    engine=create_engine('sqlite:///'+str(dbfile),connect_args={'check_same_thread':False})
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR',str(tmp_path/'yedek'))
    SessionLocal=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    def localdb():
        with SessionLocal() as s:yield s
    main.app.dependency_overrides[get_db]=localdb
    return engine,SessionLocal

def make_admin(client,username='owner'):
    r=client.post('/api/auth/bootstrap',json={'username':username,'password':'TestPassword!2026','display_name':'Yönetici'})
    assert r.status_code==200,r.text
    csrf=r.json()['csrf_token']
    return {'X-CSRF-Token':csrf}

def test_security_rights_audit_drafts(tmp_path,monkeypatch):
    engine,Maker=make_client(tmp_path,monkeypatch)
    try:
        with TestClient(main.app) as admin:
            assert admin.get('/api/pens').status_code==401
            assert admin.get('/api/auth/setup').json()['needs_setup']
            headers=make_admin(admin)
            assert not admin.get('/api/auth/setup').json()['needs_setup']
            assert admin.post('/api/pens',json={'code':'A-01','capacity':30}).status_code==403  # csrf required
            a=admin.post('/api/pens',headers=headers,json={'code':'A-01','capacity':30})
            assert a.status_code==201,a.text
            item=admin.post('/api/items',headers=headers,json={'code':'ARPA','name':'Arpa','unit':'kg'}).json()['id']
            stock=admin.post('/api/stock-movements',headers=headers,json={'item_id':item,'type':'IN','quantity':'30000','movement_date':str(date.today())})
            assert stock.status_code==201,stock.text
            movements=admin.get('/api/stock-movements/history').json()['groups'][0]['movements']
            assert movements[0]['created_by']=='Yönetici (owner)'
            assert movements[0]['quantity']=='30000.000'
            new=admin.post('/api/auth/users',headers=headers,json={'username':'operator','password':'OperatorPassword1','display_name':'Besi Sorumlusu',
                'permissions':['hayvanlar.buzagi.view','hayvanlar.buzagi.create','reports.calves.view','reports.stock.view']})
            assert new.status_code==201,new.text
            with TestClient(main.app) as op:
                login=op.post('/api/auth/login',json={'username':'operator','password':'OperatorPassword1'})
                assert login.status_code==200,login.text
                oh={'X-CSRF-Token':login.json()['csrf_token']}
                assert op.get('/api/pens').status_code==403
                assert op.get('/api/firms').status_code==403
                assert op.get('/api/calves').status_code==200
                assert op.get('/api/stock-movements/history').status_code==403
                assert op.post('/api/reports/query',headers=oh,json={'query':'stok durumunu göster'}).status_code==200
                assert op.post('/api/reports/query',headers=oh,json={'query':'parselleri listele'}).status_code==403
                assert op.post('/api/reports/export.csv',headers=oh,json={'query':'stok durumunu göster'}).status_code==403
                assert op.put('/api/auth/drafts/calves_form',headers=oh,json={'values':{'entry_kg':'45,50'}}).status_code==200
                assert op.get('/api/auth/drafts/calves_form').json()['values']['entry_kg']=='45,50'
                assert op.delete('/api/auth/drafts/calves_form',headers=oh).status_code==200
                assert op.get('/api/auth/drafts/calves_form').json()['values']=={}
                assert op.post('/api/calves',json={'tr_ear_tag':'TR-R1'}).status_code==403
                assert op.get('/api/auth/audit').status_code==403
            audit=admin.get('/api/auth/audit').json()
            assert any(x['actor']=='Yönetici (owner)' and x['entity']=='stock_movements' and x['action']=='EKLE' for x in audit)
            assert admin.post('/api/auth/bootstrap',json={'username':'hacker','password':'HackerPassword!','display_name':'Hacker'}).status_code==409
            assert admin.get('/api/auth/users').status_code==200
            assert admin.post('/api/auth/logout',headers=headers).status_code==200
            assert admin.get('/api/auth/me').status_code==401
    finally:
        main.app.dependency_overrides.clear();engine.dispose()

def test_breed_bulk_exit_manual_and_report(tmp_path,monkeypatch):
    engine,Maker=make_client(tmp_path,monkeypatch)
    try:
        with TestClient(main.app) as c:
            hdr=make_admin(c)
            d=date.today()-timedelta(days=45)
            ids=[]
            for tag,weight in [('11','45'),('12','50')]:
                r=c.post('/api/calves',headers=hdr,json={'tr_ear_tag':'TR'+tag,'farm_ear_tag':'IS'+tag,'breed':'Simental','sex':'male','entry_date':d.isoformat(),'entry_kg':weight,'notes':'Açıklama'})
                assert r.status_code==201,r.text
                ids.append(r.json()['id'])
            assert 'Simental' in c.get('/api/breeds').json()
            bad=c.post('/api/calves/bulk-exit',headers=hdr,json={'exit_date':date.today().isoformat(),'exit_group_no':'CIKIS-01','entries':[{'calf_id':ids[0],'exit_kg':'100'},{'calf_id':11111,'exit_kg':'88'}]})
            assert bad.status_code==404
            assert all(x['status']=='active' for x in c.get('/api/calves').json())
            out=c.post('/api/calves/bulk-exit',headers=hdr,json={'exit_date':date.today().isoformat(),'exit_group_no':'CIKIS-01','entries':[{'calf_id':ids[0],'exit_kg':'100'},{'calf_id':ids[1],'exit_kg':'105'}]})
            assert out.status_code==200,out.text
            report=c.get('/api/calves/exit-report?exit_group_no=CIKIS-01').json()
            assert report['summary']['count']==2
            assert all(x['exit_group_no']=='CIKIS-01' for x in report['rows'])
            assert report['summary']['weighted_adg_kg_day']=='1.222'
            assert 'Toplu Çıkış No' in c.get('/api/calves/exit-report.csv?exit_group_no=CIKIS-01').text
            assert 'calfBulkSearch' in c.get('/static/calves.js').text
            assert 'permission-box' in c.get('/static/security-ui.js').text
    finally:
        main.app.dependency_overrides.clear();engine.dispose()
