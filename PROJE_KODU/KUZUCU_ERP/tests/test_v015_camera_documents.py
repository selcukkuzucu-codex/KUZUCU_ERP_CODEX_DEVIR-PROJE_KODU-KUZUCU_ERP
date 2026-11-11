"""Küpe adayları, kimlik doğrulama ve fotoğraftan atomik tartım aktarımı."""
from datetime import date
from io import BytesIO
import json
import shutil

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app import camera_documents as capture, main
from app.db import get_db
from app.models import Animal, Firm, Item, Pen, StockMovement, Weighing
from app.finance import Invoice, LedgerEntry
from app.security import User, password_hash


def photo(text='Fotoğraf'):
    image=Image.new('RGB',(1000,300),'white')
    draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',42)
    draw.text((30,45),text,font=font,fill='black')
    buf=BytesIO();image.save(buf,format='PNG');return buf.getvalue()


@pytest.fixture
def capture_client(tmp_path,monkeypatch):
    engine=create_engine(f'sqlite:///{tmp_path / "camera.db"}',connect_args={'check_same_thread':False})
    maker=sessionmaker(bind=engine,expire_on_commit=False)
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR',str(tmp_path/'backups'))
    monkeypatch.setenv('KUZUCU_DOCUMENT_DIR',str(tmp_path/'documents'))
    def localdb():
        with maker() as db:yield db
    main.app.dependency_overrides[get_db]=localdb
    try:
        with TestClient(main.app) as client:
            with maker() as db:
                pen=Pen(code='FOTO-1',capacity=1000);db.add(pen);db.flush()
                animals=[Animal(ear_tag=f'TR4200{i:06}',farm_ear_tag=f'{i:05}',arrival_date=date(2026,1,1),entry_weight_kg=100,pen_id=pen.id,status='active') for i in range(1,503)]
                db.add_all(animals);db.add(Firm(name='Fotoğraf Test Firması'));db.commit()
                late_id=animals[-1].id
            yield client,maker,late_id
    finally:
        main.app.dependency_overrides.clear();engine.dispose()


def upload(client,monkeypatch,text='Tarih 08.11.2026\n00502 350,5 kg'):
    monkeypatch.setattr(capture,'_ocr',lambda *a,**kw:(text,90))
    response=client.post('/api/capture/documents/preview',files={'file':('deneme.png',photo(), 'image/png')})
    assert response.status_code==200,response.text
    return response.json()


def test_partial_candidate_is_not_completed_and_separate_types_preserve_zeroes():
    assert capture.tag_candidates('98',83,'green')==[{'value':'98','type':'unknown','partial':True,'confidence':83}]
    assert capture.tag_candidates('KUZUCU\n0020013',92,'farm')[0]['value']=='0020013'
    tr=capture.tag_candidates('TR 42\n6808084',88,'tr')
    assert tr==[{'value':'TR426808084','type':'tr','partial':False,'confidence':88}]
    assert all(r['partial'] for r in capture.tag_candidates('6769',60,'tr'))
    assert capture.tag_candidates('20013',70,'unknown')[0]['type']=='unknown'
    assert capture.tag_candidates('20013',70,'farm')[0]['type']=='unknown'  # Renk tür kanıtı değildir.


def test_real_tesseract_reads_synthetic_tag_without_mock():
    if not shutil.which('tesseract'):pytest.skip('Tesseract kurulu değil')
    data=photo('TR 42 6808084')
    text,confidence=capture._ocr(Image.open(BytesIO(data)),6)
    rows=capture.tag_candidates(text,confidence,'tr')
    assert any(r['value']=='TR426808084' and not r['partial'] for r in rows),repr(text)


def test_focused_digit_pass_never_invents_a_tr_prefix_or_ear_type(monkeypatch):
    monkeypatch.setattr(capture,'tag_regions',lambda image:[('farm',(0,0,80,80))])
    monkeypatch.setattr(capture,'_ocr',lambda image,psm=6,digits=False:('20013',40) if digits else ('TR42',70))
    scanned=capture.scan_tags(Image.new('RGB',(100,100),'yellow'))
    assert scanned['ocr_available']
    assert scanned['candidates']==[{'value':'20013','type':'unknown','partial':True,'confidence':40,
                                   'region':'Rakam bölgesi; türü ve tamamı doğrulanmalı'}]


def test_lookup_searches_all_records_preserves_zeroes_and_refuses_conflicting_pair(capture_client):
    client,_,late_id=capture_client
    response=client.post('/api/capture/match',json={'farm_tag':'00502'})
    assert response.status_code==200 and response.json()['animal']['id']==late_id
    assert client.post('/api/capture/match',json={'farm_tag':'502'}).json()['state']=='missing'
    result=client.post('/api/capture/match',json={'tr_tag':'TR4200000001','farm_tag':'00502'}).json()
    assert result['state']=='conflict' and result['animal'] is None
    assert client.post('/api/capture/match',json={'tr_tag':'TR4200000001','farm_tag':'99999'}).json()['state']=='conflict'


def test_document_parser_handles_turkish_values_and_invoice_lines():
    result=capture.document_fields('Tarih: 08.11.2026\n00023 350,5 kg\nTR426808084 410 kg')
    assert result['kind']=='weighing'
    assert result['weights']==[{'tag':'00023','weight_kg':'350.5','measured_at':'2026-11-08'},{'tag':'TR426808084','weight_kg':'410','measured_at':'2026-11-08'}]
    invoice=capture.document_fields('Fatura No: FT-2026\nTarih 08.11.2026\nArpa 1.250,5 kg 8,50 10\nKDV 10')
    assert invoice['kind']=='invoice' and invoice['invoice_no']=='FT-2026'
    assert invoice['invoice_lines'][0]=={'name':'Arpa','quantity':'1250.5','unit':'kg','unit_price':'8.50','vat_rate':'10'}
    assert invoice['weights']==[]  # Fiyat/KDV rakamları hayvan küpesi sanılmamalı.
    assert capture.document_fields('TR 42 6808084 410 kg')['weights'][0]['tag']=='TR426808084'


def test_photo_preview_does_not_write_animals_or_weighings_and_commit_is_idempotent(capture_client,monkeypatch):
    client,maker,late_id=capture_client
    result=upload(client,monkeypatch)
    assert result['kind']=='weighing' and result['weights'][0]['animal_id']==late_id
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(Weighing))==0
        assert db.scalar(select(func.count()).select_from(Animal))==502
    payload={'source_key':result['source_key'],'rows':[{'animal_id':late_id,'tag':'00502','measured_at':'2026-11-08','weight_kg':'350.5'}]}
    saved=client.post('/api/capture/documents/weighings',json=payload)
    assert saved.status_code==200 and saved.json()['count']==1,saved.text
    assert not saved.json()['duplicate']
    assert client.post('/api/capture/documents/weighings',json=payload).json()['duplicate']
    payload['rows'][0]['weight_kg']='351'
    assert client.post('/api/capture/documents/weighings',json=payload).status_code==409
    with maker() as db:assert db.scalar(select(func.count()).select_from(Weighing))==1
    assert client.get(result['file_url']).headers['content-type'].startswith('image/png')


def test_bad_weight_row_rolls_back_every_row_and_firm_attachment_is_not_invoice(capture_client,monkeypatch):
    client,maker,late_id=capture_client
    result=upload(client,monkeypatch)
    payload={'source_key':result['source_key'],'rows':[{'animal_id':late_id,'tag':'00502','measured_at':'2026-11-08','weight_kg':'350.5'},{'animal_id':1,'tag':'00502','measured_at':'2026-11-08','weight_kg':'360'}]}
    assert client.post('/api/capture/documents/weighings',json=payload).status_code==422
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(Weighing))==0
        firm=db.scalar(select(Firm));firm_id=firm.id
    link={'source_key':result['source_key'],'firm_id':firm_id}
    assert client.post('/api/capture/documents/firm',json=link).json()['duplicate'] is False
    assert client.post('/api/capture/documents/firm',json=link).json()['duplicate'] is True
    assert len(client.get(f'/api/capture/documents/firm/{firm_id}').json())==1
    with maker() as db:assert db.scalar(select(func.count()).select_from(capture.DocumentFirmLink))==1


def test_file_validation_csrf_and_permission_checks(capture_client,monkeypatch):
    client,maker,_=capture_client
    monkeypatch.setattr(capture,'_ocr',lambda *a,**kw:('',0))
    # Yanlış dosya uzantısı geçerli fotoğrafın gerçek MIME türünü değiştirmez.
    renamed=client.post('/api/capture/documents/preview',files={'file':('renamed.jpg',photo(),'image/jpeg')})
    assert renamed.status_code==200
    assert client.get(renamed.json()['file_url']).headers['content-type'].startswith('image/png')
    bad=client.post('/api/capture/ear-tags',files={'file':('image.jpg',b'not a picture','image/jpeg')})
    assert bad.status_code==422
    bad=client.post('/api/capture/documents/preview',files={'file':('page.html',b'<html>','text/html')})
    assert bad.status_code==422
    large=client.post('/api/capture/ear-tags',files={'file':('large.png',b'x'*(capture.MAX_BYTES+1),'image/png')})
    assert large.status_code==413
    csrf=client.headers.pop('X-CSRF-Token')
    assert client.post('/api/capture/match',json={'farm_tag':'00502'}).status_code==403
    client.headers['X-CSRF-Token']=csrf
    with maker() as db:
        db.add(User(username='limitedphoto',display_name='Sınırlı Fotoğraf',password_hash=password_hash('LimitedPhoto2026'),permissions_json='[]',is_admin=False,is_active=True));db.commit()
    login=client.post('/api/auth/login',json={'username':'limitedphoto','password':'LimitedPhoto2026'})
    client.headers['X-CSRF-Token']=login.json()['csrf_token']
    assert client.post('/api/capture/ear-tags',files={'file':('a.png',photo(),'image/png')}).status_code==403
    assert client.get('/api/capture/documents/catalog').status_code==403
    assert client.post('/api/capture/match',json={'farm_tag':'00502'}).status_code==403
    assert client.post('/api/capture/documents/weighings',json={'source_key':'a'*64,'rows':[{'animal_id':1,'tag':'00001','measured_at':'2026-11-08','weight_kg':'350'}]}).status_code==403


def test_weighing_operator_can_verify_animal_but_cannot_read_another_users_document(capture_client,monkeypatch):
    client,maker,late_id=capture_client
    original=upload(client,monkeypatch)
    with maker() as db:
        db.add(User(username='weightphoto',display_name='Tartım Sorumlusu',
                    password_hash=password_hash('WeightPhotoTest2026'),is_admin=False,is_active=True,
                    permissions_json=json.dumps(['belge.create','belge.view','hayvanlar.tartim.create'])))
        db.commit()
    login=client.post('/api/auth/login',json={'username':'weightphoto','password':'WeightPhotoTest2026'})
    client.headers['X-CSRF-Token']=login.json()['csrf_token']
    found=client.post('/api/capture/match',json={'farm_tag':'00502'})
    assert found.status_code==200 and found.json()['animal']['id']==late_id
    assert client.get(original['file_url']).status_code==404
    payload={'source_key':original['source_key'],'rows':[{'animal_id':late_id,'tag':'00502','measured_at':'2026-11-08','weight_kg':'350.5'}]}
    assert client.post('/api/capture/documents/weighings',json=payload).status_code==404
    assert client.post('/api/capture/documents/preview',files={'file':('same.png',photo(),'image/png')}).status_code==409
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(Weighing))==0


def test_reviewed_invoice_photo_uses_source_to_prevent_repeated_stock_and_accounts(capture_client,monkeypatch):
    client,maker,_=capture_client
    result=upload(client,monkeypatch,'Fatura No: FOT-2026\nTarih 08.11.2026\nArpa 1.250,5 kg 8,50 10\nKDV 10')
    assert result['kind']=='invoice' and result['weights']==[]
    with maker() as db:
        item=Item(code='OCR-ARPA',name='Arpa',unit='kg');db.add(item);db.commit()
        item_id=item.id;firm_id=db.scalar(select(Firm.id))
        assert db.scalar(select(func.count()).select_from(Invoice))==0
        assert db.scalar(select(func.count()).select_from(StockMovement))==0
    row=result['invoice_lines'][0]
    payload={'kind':'purchase','firm_id':firm_id,'invoice_no':result['invoice_no'],
             'invoice_date':result['invoice_date'],'source_document':result['source_key'],
             'lines':[{'item_id':item_id,**{k:row[k] for k in ('quantity','unit','unit_price','vat_rate')}}]}
    draft=client.post('/api/finance/invoices',json=payload)
    assert draft.status_code==201,draft.text
    assert draft.json()['subtotal']=='10629.25' and draft.json()['vat_total']=='1062.93'
    invoice_id=draft.json()['id']
    assert client.post(f'/api/finance/invoices/{invoice_id}/post').status_code==200
    assert client.post(f'/api/finance/invoices/{invoice_id}/post').status_code==200
    assert client.post('/api/finance/invoices',json=payload).status_code==409
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(Invoice))==1
        assert db.scalar(select(func.count()).select_from(StockMovement))==1
        assert db.scalar(select(func.count()).select_from(LedgerEntry))==1
