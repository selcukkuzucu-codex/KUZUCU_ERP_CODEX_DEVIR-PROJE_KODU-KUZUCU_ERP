"""Rule-based, read-only Turkish report queries; no arbitrary SQL or AI-generated execution."""
import csv
import io
import re
import unicodedata
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import Animal, Pen, Field as LandField, Item, StockMovement, Weighing
from .security import need

router=APIRouter(prefix='/api/reports', tags=['Raporlar'])
class ReportRequest(BaseModel):
    query: str = Field(min_length=2,max_length=500)

def norm(s):
    s=s.lower().replace('ı','i')
    return ''.join(ch for ch in unicodedata.normalize('NFKD',s) if not unicodedata.combining(ch))

def evaluate(query,db):
    q=norm(query)
    if any(x in q for x in ('tum', 'butun', 'hepsi', 'genel', 'ozet')) and any(x in q for x in ('isletme', 'durum', 'rapor')):
        return {'title':'İşletme özeti','columns':['Gösterge','Değer'], 'rows':[['Aktif hayvan',sum(a.status=='active' for a in db.scalars(select(Animal)).all())],['Parsel sayısı',len(db.scalars(select(LandField)).all())],['Padok sayısı',len(db.scalars(select(Pen)).all())]]}
    if any(x in q for x in ('stok','depo','hammadde','arpa','misir','silaj','yem')):
        items=db.scalars(select(Item).order_by(Item.code)).all()
        mvs=db.scalars(select(StockMovement)).all()
        rows=[]
        for item in items:
            if any(x in q for x in ('arpa','misir','silaj')) and not any(x in norm(item.name) for x in ('arpa','misir','silaj') if x in q):continue
            qty=sum((m.quantity if m.type=='IN' else -m.quantity for m in mvs if m.item_id==item.id),Decimal(0))
            rows.append([item.code,item.name,str(qty),item.unit])
        return {'title':'Stok durumu','columns':['Kod','Ürün','Bakiye','Birim'],'rows':rows}
    if any(x in q for x in ('tarla','parsel','dekar','arazi')):
        rows=[[f.ada_no or '',f.code,f.name,str(f.area_decare)] for f in db.scalars(select(LandField).order_by(LandField.code))]
        return {'title':'Parsel listesi','columns':['Ada No','Parsel Kodu','Parsel','Dekar'],'rows':rows}
    if any(x in q for x in ('tartim','kilo','agirlik')):
        animals={a.id:a for a in db.scalars(select(Animal))}
        rows=[]
        for w in db.scalars(select(Weighing).order_by(Weighing.measured_at.desc()).limit(500)):
            a=animals.get(w.animal_id)
            if a:rows.append([a.ear_tag,str(w.measured_at),str(w.weight_kg)])
        return {'title':'Son tartımlar (en fazla 500)','columns':['Küpe','Tarih','Ağırlık kg'],'rows':rows}
    if any(x in q for x in ('hayvan','besi','kupe','padok','sigir')):
        pens={p.id:p.code for p in db.scalars(select(Pen))}
        matched=re.search(r'\b(?:padok\s*)?([a-z]+[- ]?\d+)\b',q)
        filter_pen=(matched.group(1).replace(' ','-').upper() if matched and ('padok' in q) else None)
        rows=[]
        for a in db.scalars(select(Animal).order_by(Animal.ear_tag).limit(5000)):
            pen=pens.get(a.pen_id,'')
            if filter_pen and norm(pen)!=norm(filter_pen):continue
            if ('aktif' in q) and a.status!='active':continue
            rows.append([a.ear_tag,a.breed,pen,str(a.entry_weight_kg),a.status])
        return {'title':'Hayvan listesi'+(f' · {filter_pen}' if filter_pen else ''),'columns':['Küpe','Irk','Padok','Giriş kg','Durum'],'rows':rows}
    raise HTTPException(422,detail='Bu isteği henüz rapora dönüştüremiyorum. Örnek: "aktif hayvanları listele", "stok durumunu göster", "parselleri listele", "son tartımları göster". Maliyet veya SAP raporları için veri entegrasyonu gerekir.')

def report_scope(result):
    name=result['title']
    if 'Stok' in name:return 'reports.stock'
    if 'Parsel' in name:return 'reports.fields'
    if 'tartım' in name:return 'reports.weighings'
    if 'Hayvan' in name:return 'reports.animals'
    return 'reports.summary'

@router.post('/query')
def query_report(req:ReportRequest,request:Request,db:Session=Depends(get_db)):
    result=evaluate(req.query,db)
    need(request,report_scope(result)+'.view')
    result['scope']=report_scope(result)
    result['row_count']=len(result['rows'])
    result['mode']='Kural tabanlı, gerçek kayıtlar; yapay zekâ bağlantısı yok'
    return result

@router.post('/export.csv')
def export_report(req:ReportRequest,request:Request,db:Session=Depends(get_db)):
    result=evaluate(req.query,db)
    need(request,report_scope(result)+'.view')
    need(request,report_scope(result)+'.export')
    buf=io.StringIO();buf.write('\ufeff')
    writer=csv.writer(buf);writer.writerow(result['columns'])
    def safe_cell(value):
        value=str(value or '')
        return "'"+value if value[:1] in ('=','+','-','@','\t','\r') else value
    writer.writerows([[safe_cell(x) for x in row] for row in result['rows']])
    return StreamingResponse(iter([buf.getvalue().encode('utf-8')]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="kzc_rapor.csv"'})
