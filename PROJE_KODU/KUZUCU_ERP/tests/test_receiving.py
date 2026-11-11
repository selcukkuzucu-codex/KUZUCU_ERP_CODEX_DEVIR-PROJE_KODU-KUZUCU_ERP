from fastapi.testclient import TestClient
from app.main import app

def test_receipt_before_invoice_and_discrepancy():
    with TestClient(app) as c:
        item=c.post('/api/items',json={'code':'KANTAR-TEST-ARPA','name':'Test Arpa','unit':'kg'})
        assert item.status_code==201, item.text
        iid=item.json()['id']
        receipt=c.post('/api/receiving/weighings',json={'supplier_tax_id':'1234567890','item_id':iid,'weigh_ticket_no':'TEST-TICKET-0001','gross_kg':'40000','tare_kg':'15200','delivery_note_no':'IRS001'})
        assert receipt.status_code==201,receipt.text
        rid=receipt.json()['id']
        assert receipt.json()['net_kg']=='24800.000'
        assert c.post(f'/api/receiving/weighings/{rid}/accept').status_code==200
        assert c.post(f'/api/receiving/weighings/{rid}/accept').status_code==409
        invoice=c.post('/api/receiving/invoices',json={'supplier_tax_id':'1234567890','invoice_no':'TEST-2026-01','line_no':1,'item_id':iid,'delivery_note_no':'IRS001','quantity_kg':'25000'})
        assert invoice.status_code==201,invoice.text
        comp=c.post('/api/receiving/compare',json={'receipt_id':rid,'invoice_line_id':invoice.json()['id']})
        assert comp.status_code==200,comp.text
        assert comp.json()['status']=='DISCREPANCY'
        assert comp.json()['difference_kg']=='200.000'
        assert any(x['receipt_id']==rid for x in c.get('/api/receiving/alerts').json())
