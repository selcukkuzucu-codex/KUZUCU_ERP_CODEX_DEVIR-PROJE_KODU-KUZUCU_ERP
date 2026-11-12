"""Real stock/cari/VAT lifecycle, file preview atomicity and permission checks."""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import main, finance
from app.db import get_db
from app.models import Item, StockMovement
from app.security import AuditEvent

@pytest.fixture
def pilot(tmp_path,monkeypatch):
    engine=create_engine('sqlite:///'+str(tmp_path/'finance.sqlite3'),connect_args={'check_same_thread':False})
    factory=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR',str(tmp_path/'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR',str(tmp_path/'reports'))
    def localdb():
        with factory() as s:yield s
    main.app.dependency_overrides[get_db]=localdb
    try:
        with TestClient(main.app) as client:yield client,factory
    finally:
        main.app.dependency_overrides.clear();engine.dispose()

def post(client,path,data=None,expected=201):
    r=client.post(path,json=data)
    assert r.status_code==expected,r.text
    return r.json()

def fixture_cards(c,unit='kg'):
    item=post(c,'/api/items',{'code':'ARPA','name':'Arpa','unit':unit})['id']
    firm=post(c,'/api/firms',{'name':'Deneme Tedarikçi','tax_no':'1234567890'})['id']
    return item,firm

def invoice_data(item,firm,no='AL-1',kind='purchase',quantity='10',price='12.50'):
    return {'kind':kind,'firm_id':firm,'invoice_no':no,'invoice_date':str(date.today()),
            'lines':[{'item_id':item,'unit':'kg','quantity':quantity,'unit_price':price,'vat_rate':'20'}]}

def stock(c):
    return Decimal(c.get('/api/stock').json()[0]['balance'])

def test_invoice_vat_post_edit_reverse_and_account_lifecycle(pilot):
    c,factory=pilot;item,firm=fixture_cards(c)
    data=invoice_data(item,firm)
    inv=post(c,'/api/finance/invoices',data)
    assert (Decimal(inv['subtotal']),Decimal(inv['vat_total']),Decimal(inv['total']))==(Decimal('125'),Decimal('25'),Decimal('150'))
    assert stock(c)==0  # draft creates neither stock nor ledger
    assert c.get('/api/finance/accounts').json()['entries']==[]
    posted=post(c,f"/api/finance/invoices/{inv['id']}/post",expected=200)
    assert posted['status']=='posted' and stock(c)==10
    post(c,f"/api/finance/invoices/{inv['id']}/post",expected=200)
    assert stock(c)==10
    assert Decimal(c.get('/api/finance/accounts').json()['firms'][0]['payable'])==150
    data['lines'][0]['quantity']='12'
    updated=c.put(f"/api/finance/invoices/{inv['id']}",json=data)
    assert updated.status_code==200,updated.text
    assert updated.json()['revision']==2 and stock(c)==12
    account=post(c,'/api/finance/accounts',{'name':'Ofis Kasası','kind':'cash','opening_balance':'500'})
    pay={'firm_id':firm,'account_id':account['id'],'direction':'payment','amount':'100',
         'paid_on':str(date.today()),'note':'Fatura ödemesi','source_key':'payment-test-1'}
    post(c,'/api/finance/payments',pay)
    assert post(c,'/api/finance/payments',pay)['duplicate']
    result=c.get('/api/finance/accounts').json()
    assert Decimal(result['accounts'][0]['balance'])==400
    assert Decimal(result['firms'][0]['payable'])==80
    costs=c.get('/api/finance/costs').json()
    assert 'KDV hariç' in costs['method']
    assert Decimal(costs['rows'][0]['average_net_price'])==Decimal('12.5')
    assert Decimal(costs['rows'][0]['estimated_stock_cost'])==150
    post(c,f"/api/finance/invoices/{inv['id']}/cancel",expected=200)
    assert stock(c)==0
    result=c.get('/api/finance/accounts').json()
    assert Decimal(result['firms'][0]['receivable'])==100  # payment survives invoice cancellation
    with factory() as db:
        assert len(db.scalars(select(finance.InvoiceLine)).all())==2  # revisions retained
        assert len(db.scalars(select(StockMovement)).all())==4  # original/reversal entries retained
        assert any(a.table_name=='finance_invoices' for a in db.scalars(select(AuditEvent)))

def test_sale_insufficient_stock_and_multiline_atomicity(pilot):
    c,factory=pilot;item,firm=fixture_cards(c)
    post(c,'/api/stock-movements',{'item_id':item,'type':'IN','quantity':'10'})
    data=invoice_data(item,firm,'SAT-1','sale','6')
    data['lines'].append(dict(data['lines'][0]))
    inv=post(c,'/api/finance/invoices',data)
    r=c.post(f"/api/finance/invoices/{inv['id']}/post")
    assert r.status_code==409,r.text
    assert stock(c)==10
    assert c.get('/api/finance/accounts').json()['entries']==[]
    with factory() as db:assert db.get(finance.Invoice,inv['id']).status=='draft'
    # Failed edit must not reverse stock or change persisted invoice revision.
    data['lines']=data['lines'][:1]
    assert c.put(f"/api/finance/invoices/{inv['id']}",json=data).status_code==200
    post(c,f"/api/finance/invoices/{inv['id']}/post",expected=200)
    assert stock(c)==4
    data['lines'][0]['quantity']='11'
    assert c.put(f"/api/finance/invoices/{inv['id']}",json=data).status_code==409
    assert stock(c)==4

def test_explicit_receipt_link_prevents_duplicate_stock_and_source_invoice(pilot):
    c,_=pilot;item,firm=fixture_cards(c)
    move=post(c,'/api/stock-movements',{'item_id':item,'type':'IN','quantity':'10','reference':'KANTAR-15'})
    data=invoice_data(item,firm);data['source_document']='a'*64
    data['lines'][0]['linked_movement_id']=move['id']
    inv=post(c,'/api/finance/invoices',data)
    post(c,f"/api/finance/invoices/{inv['id']}/post",expected=200)
    assert stock(c)==10
    assert c.post('/api/finance/invoices',json=data).status_code==409
    data['invoice_no']='AL-2'
    assert c.post('/api/finance/invoices',json=data).status_code==409  # source document uniqueness
    data['source_document']=None
    other=post(c,'/api/finance/invoices',data)
    assert c.post(f"/api/finance/invoices/{other['id']}/post").status_code==409
    post(c,f"/api/finance/invoices/{inv['id']}/cancel",expected=200)
    assert stock(c)==10  # external receipt is not silently removed

def test_alert_persistence_ack_24_hours_and_episode(pilot,monkeypatch):
    c,factory=pilot;item,_=fixture_cards(c)
    response=c.put(f'/api/finance/items/{item}/settings',json={'category':'rawmaterial','alarm_threshold':'5'})
    assert response.status_code==200,response.text
    rows=c.get('/api/finance/alerts').json();assert len(rows)==1
    id=rows[0]['id'];created=finance.now_utc()
    # Repeated polling and replenishment do not dismiss an unacknowledged alert.
    assert len(c.get('/api/finance/alerts').json())==1
    post(c,'/api/stock-movements',{'item_id':item,'type':'IN','quantity':'10'})
    assert len(c.get('/api/finance/alerts').json())==1
    post(c,f'/api/finance/alerts/{id}/ack',expected=200)
    monkeypatch.setattr(finance,'now_utc',lambda:created+timedelta(hours=23))
    assert len(c.get('/api/finance/alerts').json())==1
    monkeypatch.setattr(finance,'now_utc',lambda:created+timedelta(hours=25))
    assert c.get('/api/finance/alerts').json()==[]
    post(c,'/api/stock-movements',{'item_id':item,'type':'OUT','quantity':'8'})
    new=c.get('/api/finance/alerts').json()
    assert len(new)==1 and new[0]['id']!=id
    assert new[0]['acknowledged_at'] is None

def workbook(rows):
    book=Workbook();sheet=book.active
    sheet.append(['Ürün Kodu','Ürün Adı','Birim','Miktar','Tarih','Belge'])
    for row in rows:sheet.append(row)
    output=BytesIO();book.save(output);return output.getvalue()

def test_excel_preview_no_writes_commit_idempotent_and_atomic(pilot):
    c,factory=pilot
    raw=workbook([['YEM','Yem','kg','30.000',str(date.today()),'F-1'],['ILAC','İlaç','adet',12,str(date.today()),'F-2']])
    preview=c.post('/api/finance/stock-import/preview',files={'file':('stok.xlsx',raw,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert preview.status_code==200,preview.text
    data=preview.json();assert not data['errors'] and data['rows'][0]['quantity']=='30000'
    with factory() as db:
        assert db.scalars(select(Item)).all()==[]
        assert db.scalars(select(StockMovement)).all()==[]
    bad={'source_key':data['source_key'],'rows':[dict(r) for r in data['rows']]}
    bad['rows'][1]['quantity']='-1'
    assert c.post('/api/finance/stock-import/commit',json=bad).status_code==422
    with factory() as db:assert db.scalars(select(Item)).all()==[]
    result=post(c,'/api/finance/stock-import/commit',{'source_key':data['source_key'],'rows':data['rows']},expected=200)
    assert result=={'count':2,'duplicate':False}
    assert post(c,'/api/finance/stock-import/commit',{'source_key':data['source_key'],'rows':data['rows']},expected=200)['duplicate']
    with factory() as db:assert len(db.scalars(select(StockMovement)).all())==2

def test_unpriced_cost_and_invoice_unit_validation(pilot):
    c,_=pilot;item,firm=fixture_cards(c)
    data=invoice_data(item,firm);data['lines'][0]['unit']='lt'
    assert c.post('/api/finance/invoices',json=data).status_code==422
    post(c,'/api/stock-movements',{'item_id':item,'type':'IN','quantity':'10'})
    row=c.get('/api/finance/costs').json()['rows'][0]
    assert row['average_net_price'] is None and row['estimated_stock_cost'] is None
    assert Decimal(row['unpriced_incoming'])==10

def test_excel_invalid_preview_cannot_commit_subset_or_modified_rows(pilot):
    c,_=pilot
    raw=workbook([['A','Arpa','kg',10,str(date.today()),''],['B','Buğday','kg',-1,str(date.today()),'']])
    p=c.post('/api/finance/stock-import/preview',files={'file':('stok.xlsx',raw)}).json()
    assert p['errors'] and len(p['rows'])==1
    assert c.post('/api/finance/stock-import/commit',json={'source_key':p['source_key'],'rows':p['rows']}).status_code==409
    raw=workbook([['A','Arpa','kg',10,str(date.today()),'']])
    p=c.post('/api/finance/stock-import/preview',files={'file':('stok.xlsx',raw)}).json()
    p['rows'][0]['quantity']='20'
    assert c.post('/api/finance/stock-import/commit',json={'source_key':p['source_key'],'rows':p['rows']}).status_code==409
    assert c.get('/api/items').json()==[]

def test_finance_permissions_and_export_scope(pilot):
    admin,_=pilot
    post(admin,'/api/auth/users',{'username':'stockreader','password':'ReaderPassword2026','display_name':'Stok Okuyucu',
                               'permissions':['stok.hareket.view']})
    with TestClient(main.app) as op:
        signed=op.post('/api/auth/login',json={'username':'stockreader','password':'ReaderPassword2026'})
        op.headers.update({'X-CSRF-Token':signed.json()['csrf_token']})
        assert op.get('/api/finance/alerts').status_code==200
        assert op.get('/api/finance/catalog').json()['firms']==[]
        for url in ['/api/finance/invoices','/api/finance/accounts','/api/finance/costs','/api/finance/reports/invoices.csv']:
            assert op.get(url).status_code==403,url
        assert op.post('/api/finance/accounts',json={'name':'Yetkisiz','kind':'cash'}).status_code==403
        assert op.post('/api/finance/stock-import/preview',files={'file':('stok.xlsx',workbook([]))}).status_code==403
