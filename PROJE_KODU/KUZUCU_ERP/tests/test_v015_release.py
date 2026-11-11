"""Sürüm bütünleştirmesi: hesap koruması, Türkçe denetim, özet ve eski şema."""
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
import json
import sqlite3
from threading import Barrier, BrokenBarrierError
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from app import main, finance, camera_documents as capture
from app.db import Base, get_db
from app.models import Calf, CalfConsumption, HealthCase, Reminder
from app.security import AuditEvent, FormDraft, LoginSession, User


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    engine=create_engine(f'sqlite:///{tmp_path / "release.db"}',connect_args={'check_same_thread':False})
    maker=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR',str(tmp_path/'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR',str(tmp_path/'reports'))
    def local_db():
        with maker() as db:yield db
    monkeypatch.setitem(main.app.dependency_overrides,get_db,local_db)
    try:
        with TestClient(main.app) as client:
            yield SimpleNamespace(client=client,engine=engine,maker=maker)
    finally:engine.dispose()


def add_user(client,username='operator',permissions=None):
    result=client.post('/api/auth/users',json={
        'username':username,'password':'TargetPassword!2026','display_name':'Besi Sorumlusu',
        'department':'Besi','permissions':permissions or []})
    assert result.status_code==201,result.text
    return result.json()


def login_as(username,password='TargetPassword!2026'):
    client=TestClient(main.app)
    result=client.post('/api/auth/login',json={'username':username,'password':password})
    assert result.status_code==200,result.text
    client.headers.update({'X-CSRF-Token':result.json()['csrf_token']})
    return client


def update_payload(user,**changes):
    return {key:user[key] for key in ('username','display_name','department','is_active','is_admin','permissions')}|changes


def test_username_change_keeps_account_password_rights_and_historical_actor(pilot):
    owner=pilot.client
    user=add_user(owner,permissions=['hayvanlar.padok.create','hayvanlar.padok.view'])
    operator=login_as('operator')
    group=operator.post('/api/pens',json={'code':'B-01','capacity':20})
    assert group.status_code==201,group.text
    before=owner.get('/api/auth/audit').json()
    actor=next(r['actor'] for r in before if r['entity']=='pens' and r['record_id']==str(group.json()['id']))
    changed=owner.put(f'/api/auth/users/{user["id"]}',json=update_payload(user,username='  YeniOperator  '))
    assert changed.status_code==200,changed.text
    assert changed.json()['id']==user['id'] and changed.json()['username']=='yenioperator'
    assert changed.json()['permissions']==user['permissions']
    assert owner.post('/api/auth/login',json={'username':'operator','password':'TargetPassword!2026'}).status_code==401
    renamed=login_as('yenioperator')
    assert renamed.get('/api/pens').status_code==200
    assert renamed.get('/api/auth/me').json()['user']['id']==user['id']
    # Rename does not rewrite the actor text of immutable past records.
    after=owner.get('/api/auth/audit').json()
    assert next(r['actor'] for r in after if r['entity']=='pens' and r['record_id']==str(group.json()['id']))==actor
    event=next(r for r in after if r['entity']=='erp_users' and r['action']=='DUZENLE')
    assert {'field':'Kullanıcı adı','before':'operator','after':'yenioperator'} in event['display_changes']
    operator.close();renamed.close()


def test_user_rename_rejects_duplicates_invalid_names_and_unprivileged_requests(pilot):
    c=pilot.client
    a=add_user(c,'operator');add_user(c,'existing')
    for name,code in [('existing',409),('  ',422),('ab',422),('bad\x01name',422)]:
        result=c.put(f'/api/auth/users/{a["id"]}',json=update_payload(a,username=name))
        assert result.status_code==code,result.text
    other=login_as('operator')
    assert other.put(f'/api/auth/users/{a["id"]}',json=update_payload(a,username='notallowed')).status_code==403
    other.close()
    assert next(u for u in c.get('/api/auth/users').json() if u['id']==a['id'])['username']=='operator'


@pytest.mark.parametrize('name',['   ',' a ','bad\x01name'])
def test_usernames_are_validated_consistently_before_create_login_and_bootstrap(pilot,name):
    c=pilot.client
    credentials={'username':name,'password':'TargetPassword!2026','display_name':'Besi Sorumlusu'}
    for endpoint in ('/api/auth/users','/api/auth/bootstrap','/api/auth/login'):
        assert c.post(endpoint,json=credentials).status_code==422
    assert len(c.get('/api/auth/users').json())==1


def test_deletion_uses_target_password_and_revokes_only_target_sessions_and_drafts(pilot):
    c=pilot.client
    user=add_user(c,permissions=['hayvanlar.padok.create','hayvanlar.padok.view'])
    other=login_as('operator')
    assert other.put('/api/auth/drafts/animal_entry',json={'values':{'breed':'Simental'}}).status_code==200
    assert other.post('/api/pens',json={'code':'KEEP','capacity':20}).status_code==201
    for payload,code in [({},422),({'password':''},422),({'password':'LegacyTestPassword2026'},403)]:
        denied=c.request('DELETE',f'/api/auth/users/{user["id"]}',json=payload)
        assert denied.status_code==code,denied.text
        assert other.get('/api/auth/me').status_code==200
    missing_csrf=c.request('DELETE',f'/api/auth/users/{user["id"]}',json={'password':'TargetPassword!2026'},headers={'X-CSRF-Token':''})
    assert missing_csrf.status_code==403
    unprivileged=other.request('DELETE',f'/api/auth/users/{user["id"]}',json={'password':'TargetPassword!2026'})
    assert unprivileged.status_code==403
    removed=c.request('DELETE',f'/api/auth/users/{user["id"]}',json={'password':'TargetPassword!2026'})
    assert removed.status_code==200,removed.text
    assert other.get('/api/auth/me').status_code==401
    assert c.post('/api/auth/login',json={'username':'operator','password':'TargetPassword!2026'}).status_code==401
    assert c.get('/api/auth/me').status_code==200
    assert c.get('/api/pens').json()[0]['code']=='KEEP'
    audit=c.get('/api/auth/audit').json()
    assert any(r['entity']=='erp_users' and r['record_id']==str(user['id']) and r['action']=='SIL' for r in audit)
    assert any(r['entity']=='pens' and 'operator' in r['actor'] for r in audit)
    assert 'TargetPassword' not in json.dumps(audit)
    with pilot.maker() as db:
        assert db.get(User,user['id']) is None
        assert not db.scalars(select(LoginSession).where(LoginSession.user_id==user['id'])).all()
        assert not db.scalars(select(FormDraft).where(FormDraft.user_id==user['id'])).all()
    other.close()


def test_own_admin_cannot_be_deleted_and_anonymous_delete_is_denied(pilot):
    c=pilot.client
    owner=c.get('/api/auth/me').json()['user']
    result=c.request('DELETE',f'/api/auth/users/{owner["id"]}',json={'password':'LegacyTestPassword2026'})
    assert result.status_code==409
    anonymous=TestClient(main.app)
    assert anonymous.request('DELETE',f'/api/auth/users/{owner["id"]}',json={'password':'LegacyTestPassword2026'}).status_code==401
    anonymous.close()


def test_deleted_users_documents_remain_private_when_sqlite_reuses_the_user_id(pilot,tmp_path,monkeypatch):
    c=pilot.client
    monkeypatch.setenv('KUZUCU_DOCUMENT_DIR',str(tmp_path/'documents'))
    monkeypatch.setattr(capture,'_ocr',lambda *args,**kwargs:('Özel firma belgesi',90))
    buffer=BytesIO();Image.new('RGB',(200,120),'white').save(buffer,format='PNG')
    photo=buffer.getvalue()
    permissions=['belge.create','belge.view','firmalar.view','firmalar.edit','hayvanlar.tartim.create']
    user=add_user(c,'oldphotouser',permissions=permissions)
    firm=c.post('/api/firms',json={'name':'Belge Firması','tax_no':'1234567890'}).json()['id']
    operator=login_as('oldphotouser')
    upload=operator.post('/api/capture/documents/preview',files={'file':('ozel.png',photo,'image/png')})
    assert upload.status_code==200,upload.text
    document=upload.json();link={'source_key':document['source_key'],'firm_id':firm}
    assert operator.post('/api/capture/documents/firm',json=link).status_code==200
    assert operator.get(document['file_url']).status_code==200
    assert c.request('DELETE',f'/api/auth/users/{user["id"]}',json={'password':'TargetPassword!2026'}).status_code==200
    replacement=add_user(c,'newphotouser',permissions=permissions)
    assert replacement['id']==user['id']  # SQLite without AUTOINCREMENT reuses the highest deleted id.
    newcomer=login_as('newphotouser')
    assert newcomer.get(document['file_url']).status_code==404
    assert newcomer.get(f'/api/capture/documents/firm/{firm}').json()==[]
    assert newcomer.post('/api/capture/documents/firm',json=link).status_code==404
    attempted={'source_key':document['source_key'],'rows':[{'animal_id':1,'tag':'TR-001','measured_at':str(date.today()),'weight_kg':'200'}]}
    assert newcomer.post('/api/capture/documents/weighings',json=attempted).status_code==404
    assert newcomer.post('/api/capture/documents/preview',files={'file':('ayni.png',photo,'image/png')}).status_code==409
    assert c.get(document['file_url']).status_code==200
    assert len(c.get(f'/api/capture/documents/firm/{firm}').json())==1
    with pilot.maker() as db:
        assert db.get(capture.CapturedDocument,document['document_id']).owner_id is None
    operator.close();newcomer.close()


def test_two_admins_cannot_concurrently_delete_the_last_active_administrator(pilot):
    c=pilot.client
    first=c.get('/api/auth/me').json()['user']
    second=add_user(c,'otheradmin')
    promoted=c.put(f'/api/auth/users/{second["id"]}',json=update_payload(second,is_admin=True))
    assert promoted.status_code==200
    other=login_as('otheradmin')
    barrier=Barrier(2)
    def align_unlocked_count(connection,cursor,statement,parameters,context,executemany):
        # Without an early write lock, both requests can see two administrators.
        # With the lock, the first request proceeds after the short timeout and
        # the second sees the updated count, preserving the invariant.
        if 'count(' in statement.lower() and 'erp_users' in statement:
            try:barrier.wait(timeout=.3)
            except BrokenBarrierError:pass
    event.listen(pilot.engine,'after_cursor_execute',align_unlocked_count)
    try:
        def remove(client,user_id,password):
            return client.request('DELETE',f'/api/auth/users/{user_id}',json={'password':password}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            left=pool.submit(remove,c,second['id'],'TargetPassword!2026')
            right=pool.submit(remove,other,first['id'],'LegacyTestPassword2026')
            codes=[left.result(),right.result()]
        assert codes.count(200)==1 and all(code in (200,401,409) for code in codes),codes
        with pilot.maker() as db:
            assert len(db.scalars(select(User).where(User.is_active==True,User.is_admin==True)).all())==1
    finally:
        event.remove(pilot.engine,'after_cursor_execute',align_unlocked_count)
        other.close()


def test_audit_presents_old_and_unknown_records_in_turkish_without_exposing_secrets(pilot):
    with pilot.maker() as db:
        db.add_all([
            AuditEvent(actor='sistem',table_name='erp_users',record_id='101',action='DUZENLE',changes_json=json.dumps({
                'username':{'once':'ozel.name','new':'yeni.name'},'sex':{'once':'male','new':'female'},
                'is_active':{'once':False,'new':True},'password_hash':'NeverDisplayHash'})),
            AuditEvent(actor='sistem',table_name='health_print_runs',record_id='102',action='EKLE',changes_json=json.dumps({'print_error':'FileNotFoundError: printer failed'})),
            AuditEvent(actor='sistem',table_name='unregistered_table',record_id='103',action='UNKNOWN_ACTION',changes_json=json.dumps({'status':{'once':'INTERNAL_STATE','new':'UNKNOWN_STATE'},'unknown_field':'INTERNAL_TOKEN'})),
        ]);db.commit()
    audit=pilot.client.get('/api/auth/audit').json()
    known=next(r for r in audit if r['record_id']=='101')
    assert known['entity_label']=='Kullanıcılar' and known['action_label']=='Düzenleme'
    assert {'field':'Cinsiyet','before':'Erkek','after':'Dişi'} in known['display_changes']
    assert {'field':'Aktiflik','before':'Hayır','after':'Evet'} in known['display_changes']
    assert {'field':'Kullanıcı adı','before':'ozel.name','after':'yeni.name'} in known['display_changes']
    assert 'NeverDisplayHash' not in json.dumps(known['display_changes'])
    printable=next(r for r in audit if r['record_id']=='102')
    assert printable['entity_label']=='Günlük Sağlık Çıktıları'
    assert 'FileNotFoundError' not in json.dumps(printable['display_changes'])
    unknown=next(r for r in audit if r['record_id']=='103')
    assert unknown['entity_label']=='Diğer kayıtlar' and unknown['action_label']=='Kayıt işlemi'
    display=json.dumps(unknown['display_changes'])
    assert 'INTERNAL_' not in display and 'UNKNOWN_' not in display and 'unknown_field' not in display


def add_animal(c,pen,tag,sex='male',breed='Simental'):
    r=c.post('/api/animals',json={'tr_ear_tag':tag,'farm_ear_tag':f'IS-{tag}',
        'arrival_date':str(date.today()-timedelta(days=30)),'entry_weight_kg':'100',
        'pen_id':pen,'sex':sex,'breed':breed})
    assert r.status_code==201,r.text
    return r.json()


def add_calf(c,tag,sex='female',breed='Holstein',milk_phase=None):
    r=c.post('/api/calves',json={'tr_ear_tag':tag,'sex':sex,'breed':breed,'entry_kg':'50',
        'entry_date':str(date.today()-timedelta(days=30)),'milk_phase':milk_phase})
    assert r.status_code==201,r.text
    return r.json()


def test_dashboard_counts_visible_animals_once_and_keeps_milk_status_explicit(pilot):
    c=pilot.client
    pen=c.post('/api/pens',json={'code':'G01','capacity':20}).json()['id']
    add_animal(c,pen,'TR-DUP','male','Simental')
    add_animal(c,pen,'TR-FEMALE','female','Holstein')
    add_animal(c,pen,'TR-UNKNOWN',None,'Belirtilmedi')
    add_calf(c,'TR-DUP','male','Simental',True)
    add_calf(c,'TR-CALF','female','Jersey',True)
    add_calf(c,'TR-LEGACY','female','Holstein')
    gone=add_calf(c,'TR-EXITED','male','Angus',True)
    assert c.post(f'/api/calves/{gone["id"]}/exit',json={'exit_date':str(date.today()),'exit_kg':'100'}).status_code==200
    dashboard=c.get('/api/dashboard').json()
    assert dashboard['active_total']==5 and dashboard['active_animals']==3
    assert (dashboard['male_total'],dashboard['female_total'],dashboard['unknown_sex_total'])==(1,3,1)
    assert dashboard['milk_calves']=={'male':1,'female':1,'unknown_sex':0,'phase_unknown':1}
    assert {r['breed']:r['total'] for r in dashboard['breeds']}=={'Simental':1,'Holstein':2,'Jersey':1,'Belirtilmedi':1}
    add_user(c,'summaryonly',permissions=['dashboard.view'])
    restricted=login_as('summaryonly')
    limited=restricted.get('/api/dashboard').json()
    assert all(limited[key] is None for key in ['active_total','male_total','female_total','breeds','milk_calves','area_decare','pens'])
    restricted.close()
    calf_user=add_user(c,'calfonly',permissions=['dashboard.view','hayvanlar.buzagi.view'])
    restricted=login_as('calfonly')
    limited=restricted.get('/api/dashboard').json()
    assert limited['active_total']==3 and limited['active_animals'] is None
    assert limited['male_total']==1 and limited['female_total']==2
    restricted.close()


def test_invoice_movements_cannot_be_edited_outside_the_invoice_ledger(pilot):
    c=pilot.client
    item=c.post('/api/items',json={'code':'ARPA','name':'Arpa','unit':'kg'}).json()['id']
    firm=c.post('/api/firms',json={'name':'Tedarikçi','tax_no':'1234567890'}).json()['id']
    invoice={'kind':'purchase','firm_id':firm,'invoice_no':'AL-1','invoice_date':str(date.today()),
        'lines':[{'item_id':item,'unit':'kg','quantity':'10','unit_price':'5','vat_rate':'20'}]}
    created=c.post('/api/finance/invoices',json=invoice)
    assert created.status_code==201,created.text
    invoice_id=created.json()['id']
    assert c.post(f'/api/finance/invoices/{invoice_id}/post').status_code==200
    history=c.get('/api/stock-movements/history').json()['groups'][0]['movements']
    owned=next(row for row in history if row['reference'].startswith('FATURA:'))
    update={'item_id':item,'type':'IN','quantity':'20','movement_date':str(date.today()),'reference':'Silinmiş bağlantı','reason':'Yetkisiz düzeltme yolu'}
    assert c.put(f'/api/stock-movements/{owned["id"]}',json=update).status_code==409
    assert Decimal(c.get('/api/stock').json()[0]['balance'])==10
    assert Decimal(c.get('/api/finance/accounts').json()['firms'][0]['payable'])==60
    assert c.post(f'/api/finance/invoices/{invoice_id}/cancel').status_code==200
    # Both original and reversal remain protected after invoice cancellation.
    for row in c.get('/api/stock-movements/history').json()['groups'][0]['movements']:
        assert c.put(f'/api/stock-movements/{row["id"]}',json=update).status_code==409
    # A pre-existing receipt linked by a posted invoice is protected too.
    receipt=c.post('/api/stock-movements',json={'item_id':item,'type':'IN','quantity':'10','reference':'KANTAR-1'}).json()
    invoice['invoice_no']='AL-2';invoice['lines'][0]['linked_movement_id']=receipt['id']
    linked=c.post('/api/finance/invoices',json=invoice).json()['id']
    assert c.post(f'/api/finance/invoices/{linked}/post').status_code==200
    assert c.put(f'/api/stock-movements/{receipt["id"]}',json=update).status_code==409
    assert Decimal(c.get('/api/stock').json()[0]['balance'])==10


def test_stock_threshold_crossings_are_recorded_without_waiting_for_alert_poll(pilot):
    c=pilot.client
    item=c.post('/api/items',json={'code':'ILAC','name':'İlaç','unit':'adet'}).json()['id']
    assert c.put(f'/api/finance/items/{item}/settings',json={'category':'medicine','alarm_threshold':'5'}).status_code==200
    # First low-stock episode is created by settings. Replenishment followed by
    # depletion must create a second episode even if alerts were never polled.
    assert c.post('/api/stock-movements',json={'item_id':item,'type':'IN','quantity':'10'}).status_code==201
    assert c.post('/api/stock-movements',json={'item_id':item,'type':'OUT','quantity':'8'}).status_code==201
    with pilot.maker() as db:
        rows=db.scalars(select(finance.StockAlert).where(finance.StockAlert.item_id==item)).all()
        assert len(rows)==2
        assert {r.balance_at_creation for r in rows}=={Decimal(0),Decimal(2)}


def test_startup_migrates_v014_sqlite_twice_without_guessing_old_units_or_health_approval(tmp_path,monkeypatch):
    # Start with production table definitions and remove only the newly introduced
    # columns from copied DDL; no live database or external artifact is required.
    engine=create_engine(f'sqlite:///{tmp_path / "old.db"}',connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    new_columns={'calves':{'group_no','purchase_price_tl','milk_phase','exit_group_snapshot'},
                 'calf_consumptions':{'milk_litres','group_no_snapshot'},
                 'health_cases':{'duration_days'},'reminders':{'interval_count'}}
    with engine.begin() as con:
        for table,columns in new_columns.items():
            ddl=con.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),{'name':table}).scalar()
            lines=ddl.splitlines()
            lines=[line for line in lines if not any(line.lstrip().startswith(name+' ') for name in columns)
                   and 'nonnegative_calf_price' not in line and 'nonnegative_calf_milk_litres' not in line]
            ddl='\n'.join(lines).replace(',\n)', '\n)')
            con.exec_driver_sql(f'DROP TABLE {table}')
            con.exec_driver_sql(ddl)
        con.exec_driver_sql("INSERT INTO calves (id,tr_ear_tag,farm_ear_tag,sex,breed,entry_date,entry_kg,planned_days,batch_code,exit_group_no,notes) VALUES (1,'TR-OLD','0001','male','Simental','2026-01-01',50,45,'Eski Alım','Eski Çıkış','koru')")
        con.exec_driver_sql("INSERT INTO calf_consumptions (id,calf_id,consumed_on,milk_kg,feed_kg,notes) VALUES (1,1,'2026-01-02',3.25,1.5,'Eski kg')")
        con.exec_driver_sql("INSERT INTO reminders (id,title,notes,category,frequency,start_date,remind_time,is_active,created_at) VALUES (1,'Eski Ajanda','','Genel','monthly','2026-01-31','09:00',1,'2026-01-01 00:00:00')")
        con.exec_driver_sql("INSERT INTO pens (id,code,capacity) VALUES (1,'ESKI-GRUP',20)")
        con.exec_driver_sql("INSERT INTO animals (id,ear_tag,breed,arrival_date,entry_weight_kg,pen_id,status) VALUES (1,'TR-HEALTH','Holstein','2025-01-01',100,1,'active')")
        con.exec_driver_sql("""INSERT INTO health_cases
            (id,animal_id,record_type,condition_name,symptoms,product_name,treatment_name,
             repeat_review_confirmed,dosage_text,veterinarian,vet_approved,applications_per_day,
             start_date,planned_end_date,withdrawal_end_date,notes,status,outcome_notes,created_at)
            VALUES (1,1,'treatment','Geçmiş hastalık','Eski belirti','Eski ilaç','Eski tedavi',
                    0,'Eski doz','Eski hekim',1,2,'2026-01-01','2026-01-10','2026-01-20',
                    'Geçmiş sağlık notu','active','','2026-01-01 00:00:00')""")
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR',str(tmp_path/'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR',str(tmp_path/'reports'))
    maker=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    def local_db():
        with maker() as db:yield db
    monkeypatch.setitem(main.app.dependency_overrides,get_db,local_db)
    try:
        for _ in range(2):
            with TestClient(main.app) as c:
                assert c.get('/').status_code==200
                assert c.get('/api/calves').status_code==200
                with maker() as db:
                    calf=db.get(Calf,1);old=db.get(CalfConsumption,1);reminder=db.get(Reminder,1)
                    assert calf.group_no is None and calf.purchase_price_tl is None and calf.milk_phase is None
                    assert calf.batch_code=='Eski Alım' and calf.exit_group_no=='Eski Çıkış'
                    assert old.milk_kg==Decimal('3.25') and old.milk_litres is None and old.feed_kg==Decimal('1.5')
                    assert reminder.interval_count==1 and reminder.start_date==date(2026,1,31)
                    assert 'duration_days' in {r[1] for r in db.execute(text('PRAGMA table_info(health_cases)'))}
                    health=db.get(HealthCase,1)
                    assert health.duration_days is None and health.vet_approved is True
                    assert health.start_date==date(2026,1,1) and health.planned_end_date==date(2026,1,10)
                    assert health.symptoms=='Eski belirti' and health.veterinarian=='Eski hekim'
                    assert health.withdrawal_end_date==date(2026,1,20) and health.notes=='Geçmiş sağlık notu'
        # The earliest startup backup really holds the pre-migration schema and
        # business values, rather than a blank or already modified database.
        backups=sorted((tmp_path/'backups').glob('kuzucu_once-acilis-oncesi_*.sqlite3'))
        assert backups
        restored=tmp_path/'restored.sqlite3'
        with sqlite3.connect(backups[0]) as source,sqlite3.connect(restored) as recovery:
            source.backup(recovery)
        with sqlite3.connect(restored) as recovered:
            assert recovered.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert 'group_no' not in {r[1] for r in recovered.execute('PRAGMA table_info(calves)')}
            assert recovered.execute('SELECT milk_kg,feed_kg FROM calf_consumptions').fetchone()==(3.25,1.5)
            assert recovered.execute('SELECT veterinarian,vet_approved FROM health_cases').fetchone()==('Eski hekim',1)
    finally:engine.dispose()


def test_unavailable_backup_target_stops_startup_before_any_schema_or_data_change(tmp_path,monkeypatch,capsys):
    engine=create_engine(f'sqlite:///{tmp_path / "unchanged.db"}',connect_args={'check_same_thread':False})
    with engine.begin() as con:
        con.exec_driver_sql('CREATE TABLE fields (id INTEGER PRIMARY KEY,code VARCHAR(40),name VARCHAR(120),area_decare NUMERIC(12,3))')
        con.exec_driver_sql("INSERT INTO fields VALUES (1,'ESKI','Korunacak Tarla',12.5)")
    target=tmp_path/'not-a-directory'
    target.write_text('Önceden var olan dosya',encoding='utf-8')
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR',str(target))
    try:
        with pytest.raises(RuntimeError,match='Açılış öncesi yedek alınamadı'):
            with TestClient(main.app):pass
        with engine.connect() as con:
            assert {r[1] for r in con.execute(text('PRAGMA table_info(fields)'))}=={'id','code','name','area_decare'}
            assert con.execute(text('SELECT code,name,area_decare FROM fields')).one()==('ESKI','Korunacak Tarla',12.5)
            assert {r[0] for r in con.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}=={'fields'}
        assert target.read_text(encoding='utf-8')=='Önceden var olan dosya'
        assert 'FileExistsError' not in capsys.readouterr().out
    finally:engine.dispose()
