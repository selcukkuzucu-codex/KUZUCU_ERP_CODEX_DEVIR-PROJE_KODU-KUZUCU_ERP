"""Ortak raporda bölüm/rapor yetkileri, tarih filtreleri ve Türkçe çıktılar."""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main, reports
from app.db import get_db
from app.security import User


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    engine=create_engine('sqlite:///'+str(tmp_path/'reports.sqlite3'),connect_args={'check_same_thread':False})
    factory=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR',str(tmp_path/'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR',str(tmp_path/'pdf'))
    def localdb():
        with factory() as s:yield s
    monkeypatch.setitem(main.app.dependency_overrides,get_db,localdb)
    with TestClient(main.app) as c:yield c,factory
    engine.dispose()


def post(c,path,data=None,code=201):
    response=c.post(path,json=data)
    assert response.status_code==code,response.text
    return response.json()


def report(c,query,**filters):
    return post(c,'/api/reports/query',{'query':query,**filters},200)


def test_invoice_product_date_and_cost_filters_match_ledger(pilot):
    c,_=pilot
    item=post(c,'/api/items',{'code':'ARPA','name':'Arpa','unit':'kg'})['id']
    other=post(c,'/api/items',{'code':'ILAC','name':'Deneme İlaç','unit':'adet'})['id']
    firm=post(c,'/api/firms',{'name':'Örnek Firma'})['id']
    for no,day,price in [('ESKI','2026-09-01','10'),('YENI','2026-10-01','20')]:
        invoice=post(c,'/api/finance/invoices',{'kind':'purchase','firm_id':firm,'invoice_no':no,'invoice_date':day,
            'lines':[{'item_id':item,'unit':'kg','quantity':'2.5','unit_price':price,'vat_rate':'20'},
                     {'item_id':other,'unit':'adet','quantity':'1','unit_price':'3','vat_rate':'10'}]})
        post(c,f"/api/finance/invoices/{invoice['id']}/post",code=200)
    data=report(c,'alış faturalarını listele',date_from='2026-10-01',item_id=item,search='Arpa')
    assert data['scope']=='reports.finance' and data['row_count']==1
    row=data['rows'][0]
    assert row[0]=='01.10.2026' and row[1]=='Alış' and row[2]=='YENI' and row[5]=='Arpa'
    assert row[6]=='2,5' and row[-3:]==['50','10','60']
    cost=report(c,'maliyetleri listele',date_from='2026-10-01',firm_id=firm,item_id=item)
    assert cost['rows']==[['ARPA','Arpa','kg','2,5','50','20']]
    assert 'güncel stok' in cost['notice']
    balances=report(c,'cari bakiyeler',date_to='2026-09-30')
    # September 25+5 KDV +3+0.3KDV =33.30 TL; October excluded.
    assert balances['rows']==[['Örnek Firma','0','33,3','-33,3']]
    net=report(c,'stok durumunu göster',date_from='2026-10-01',item_id=item)
    assert net['rows']==[['ARPA','Arpa','2,5','0','2,5','kg']]
    assert 'net değişim' in net['notice']
    assert c.post('/api/reports/query',json={'query':'faturalar','date_from':'2026-11-01','date_to':'2026-10-01'}).status_code==422


def test_personnel_filters_and_leave_labels(pilot):
    c,_=pilot
    person=post(c,'/api/personnel/employees',{'employee_no':'P01','full_name':'Deneme Çalışanı','start_date':'2026-01-01'})
    post(c,'/api/personnel/overtime',{'employee_id':person['id'],'worked_on':'2026-10-01','hours':'2.5'})
    post(c,'/api/personnel/overtime',{'employee_id':person['id'],'worked_on':'2026-10-03','hours':'1'})
    data=report(c,'personel mesaileri',employee_id=person['id'],date_from='2026-10-02',search='Deneme')
    assert data['scope']=='reports.payroll' and data['row_count']==1
    assert data['rows'][0][3:5]==['03.10.2026','1,00']
    post(c,'/api/personnel/leaves',{'employee_id':person['id'],'kind':'weekly','starts_on':'2026-10-04','ends_on':'2026-10-04'})
    leave=report(c,'personel izinleri',employee_id=person['id'])
    assert leave['rows'][0][2]=='Haftalık izin'
    assert report(c,'personel listesi',search='bulunmayan')['rows']==[]


def test_animal_exit_filters_group_and_turkish_csv(pilot):
    c,_=pilot
    group=post(c,'/api/pens',{'code':'B-01','capacity':20})['id']
    animal=post(c,'/api/animals',{'tr_ear_tag':'TR00042','farm_ear_tag':'0042','arrival_date':'2026-01-01','entry_weight_kg':'100','pen_id':group,'breed':'Simental'})
    grouped=report(c,'B-01 grubundaki hayvanları listele')
    assert grouped['row_count']==1 and grouped['rows'][0][-1]=='Aktif'
    post(c,'/api/animal-operations/bulk-exit',{'exit_date':'2026-10-01','reason':'sale','destination':'Örnek Alıcı',
        'entries':[{'animal_id':animal['id'],'exit_kg':'250.5'}]},200)
    exited=report(c,'satış yapılan hayvan çıkışları',date_from='2026-10-01',search='0042')
    assert exited['row_count']==1 and exited['rows'][0][-3:]==['Satış','Örnek Alıcı','250,5']
    assert report(c,'aktif hayvanları listele')['rows']==[]
    csv=c.post('/api/reports/export.csv',json={'query':'hayvanları listele'})
    assert csv.status_code==200 and csv.content.startswith(b'\xef\xbb\xbf')
    assert 'Çıkışı yapıldı' in csv.text and ',exited' not in csv.text and ',active' not in csv.text


@pytest.mark.parametrize('query,permissions',[
    ('faturaları listele',['reports.finance.view']),
    ('cari bakiyeler',['reports.finance.view']),
    ('personel izinleri',['reports.summary.view']),
    ('maliyetler',['reports.finance.view']),
    ('hayvan çıkışları',['reports.weighings.view']),
])
def test_sensitive_report_permission_is_checked_before_read(query,permissions):
    import json
    user=User(id=101,username='raporcu',display_name='Rapor Sorumlusu',is_admin=False,is_active=True,permissions_json=json.dumps(permissions))
    request=SimpleNamespace(state=SimpleNamespace(erp_user=user))
    class NoDatabaseRead:
        def __getattr__(self,key):raise AssertionError('Yetki yokken veri okundu: '+key)
    with pytest.raises(HTTPException) as failure:
        reports.evaluate(reports.ReportRequest(query=query),NoDatabaseRead(),request)
    assert failure.value.status_code==403


def test_summary_does_not_bypass_detailed_report_scopes(pilot):
    import json
    c,factory=pilot
    post(c,'/api/pens',{'code':'G01','capacity':5})
    with factory() as db:
        user=User(username='ozetci',display_name='Özet Sorumlusu',is_admin=False,is_active=True,permissions_json=json.dumps(['reports.summary.view']))
        request=SimpleNamespace(state=SimpleNamespace(erp_user=user))
        data=reports.evaluate('işletme genel raporu',db,request)
        assert data['rows']==[]
        user.permissions_json=json.dumps(['reports.summary.view','reports.animals.view'])
        data=reports.evaluate('işletme genel raporu',db,request)
        assert ['Grup sayısı',1] in data['rows']
        assert all(r[0]!='Parsel sayısı' for r in data['rows'])


def test_csv_export_requires_distinct_grant_and_protects_formulas(pilot):
    c,_=pilot
    person=post(c,'/api/personnel/employees',{'employee_no':'P02','full_name':'=Özel Ad','start_date':'2026-01-01'})
    output=c.post('/api/reports/export.csv',json={'query':'personel listesi'})
    assert output.status_code==200 and "'=Özel Ad" in output.text
    user=post(c,'/api/auth/users',{'username':'raporcu','password':'TestReportPassword2026','display_name':'Rapor Sorumlusu',
        'permissions':['reports.payroll.view']})
    login=c.post('/api/auth/login',json={'username':'raporcu','password':'TestReportPassword2026'})
    assert login.status_code==200
    c.headers['X-CSRF-Token']=login.json()['csrf_token']
    assert c.post('/api/reports/query',json={'query':'personel listesi'}).status_code==200
    assert c.post('/api/reports/export.csv',json={'query':'personel listesi'}).status_code==403
    assert c.post('/api/reports/query',json={'query':'faturalar'}).status_code==403


def test_bank_cash_opening_and_period_balance(pilot):
    c,_=pilot
    firm=post(c,'/api/firms',{'name':'Örnek Cari'})['id']
    bank=post(c,'/api/finance/accounts',{'name':'Banka Hesabı','kind':'bank','opening_balance':'1000'})['id']
    post(c,'/api/finance/accounts',{'name':'Küçük Kasa','kind':'cash','opening_balance':'50'})
    post(c,'/api/finance/payments',{'firm_id':firm,'account_id':bank,'paid_on':'2026-10-01','amount':'100','direction':'payment','source_key':'report-bank-payment'})
    before=report(c,'banka hesapları',date_to='2026-09-30')
    after=report(c,'banka hesapları',date_to='2026-10-01')
    assert before['rows']==[['Banka Hesabı','Banka','1.000','1.000']]
    assert after['rows']==[['Banka Hesabı','Banka','1.000','900']]
    assert report(c,'kasa bakiyeleri')['rows']==[['Küçük Kasa','Kasa','50','50']]


def test_specific_invoice_query_is_not_mistaken_for_animal_exit():
    assert reports.selected_kind('hayvan satış faturaları')=='invoices'
    assert reports.selected_kind('personel işten çıkışları')=='personnel'
    assert reports.selected_kind('hayvan satış çıkışları')=='exits'
