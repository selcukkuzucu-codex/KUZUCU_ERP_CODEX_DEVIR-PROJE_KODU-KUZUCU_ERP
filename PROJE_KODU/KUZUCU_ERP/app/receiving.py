"""KZC ERP: goods-receipt / invoice reconciliation pilot.

Operational scale weights are authoritative for physical stock. Invoices never
post stock. This is a demo API; authentication/approval roles must precede use.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import String, Numeric, ForeignKey, DateTime, UniqueConstraint, select
from sqlalchemy.orm import Session, Mapped, mapped_column
from .db import Base, get_db
from .models import Item, StockMovement

router = APIRouter(prefix='/api/receiving', tags=['Kantar - Fatura Mutabakatı'])

def now(): return datetime.now(timezone.utc)

class GoodsReceipt(Base):
    __tablename__='goods_receipts'
    id:Mapped[int]=mapped_column(primary_key=True)
    supplier_tax_id:Mapped[str]=mapped_column(String(30),index=True)
    item_id:Mapped[int]=mapped_column(ForeignKey('items.id'))
    weigh_ticket_no:Mapped[str]=mapped_column(String(80),unique=True)
    delivery_note_no:Mapped[str]=mapped_column(String(80),default='')
    vehicle_plate:Mapped[str]=mapped_column(String(25),default='')
    gross_kg:Mapped[Decimal]=mapped_column(Numeric(16,3))
    tare_kg:Mapped[Decimal]=mapped_column(Numeric(16,3))
    net_kg:Mapped[Decimal]=mapped_column(Numeric(16,3))
    status:Mapped[str]=mapped_column(String(24),default='WEIGHED')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class PurchaseInvoiceLine(Base):
    __tablename__='purchase_invoice_lines'
    id:Mapped[int]=mapped_column(primary_key=True)
    supplier_tax_id:Mapped[str]=mapped_column(String(30),index=True)
    invoice_no:Mapped[str]=mapped_column(String(100))
    line_no:Mapped[int]=mapped_column()
    item_id:Mapped[int]=mapped_column(ForeignKey('items.id'))
    delivery_note_no:Mapped[str]=mapped_column(String(80),default='')
    quantity_kg:Mapped[Decimal]=mapped_column(Numeric(16,3))
    status:Mapped[str]=mapped_column(String(24),default='DRAFT')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    __table_args__=(UniqueConstraint('supplier_tax_id','invoice_no','line_no',name='uq_supplier_invoice_line'),)

class Reconciliation(Base):
    __tablename__='receipt_invoice_matches'
    id:Mapped[int]=mapped_column(primary_key=True)
    receipt_id:Mapped[int]=mapped_column(ForeignKey('goods_receipts.id'))
    invoice_line_id:Mapped[int]=mapped_column(ForeignKey('purchase_invoice_lines.id'))
    difference_kg:Mapped[Decimal]=mapped_column(Numeric(16,3))
    status:Mapped[str]=mapped_column(String(24))
    note:Mapped[str]=mapped_column(String(300),default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    __table_args__=(UniqueConstraint('receipt_id','invoice_line_id',name='uq_receipt_invoice_match'),)

class ReceiptIn(BaseModel):
    supplier_tax_id:str=Field(min_length=5,max_length=30)
    item_id:int
    weigh_ticket_no:str=Field(min_length=1,max_length=80)
    delivery_note_no:str=''
    vehicle_plate:str=''
    gross_kg:Decimal=Field(gt=0)
    tare_kg:Decimal=Field(ge=0)

class InvoiceLineIn(BaseModel):
    supplier_tax_id:str=Field(min_length=5,max_length=30)
    invoice_no:str=Field(min_length=1,max_length=100)
    line_no:int=Field(ge=1)
    item_id:int
    delivery_note_no:str=''
    quantity_kg:Decimal=Field(gt=0)

class CompareIn(BaseModel):
    receipt_id:int
    invoice_line_id:int
    tolerance_kg:Decimal=Field(default=Decimal('0'),ge=0)
    tolerance_percent:Decimal=Field(default=Decimal('0'),ge=0)

@router.post('/weighings',status_code=201)
def create_weighing(data:ReceiptIn, db:Session=Depends(get_db)):
    if db.get(Item,data.item_id) is None:raise HTTPException(404,'Stok kartı bulunamadı')
    item=db.get(Item,data.item_id)
    if item.unit.lower()!='kg':raise HTTPException(422,'Kantar kaydı yalnızca kg stok birimiyle yapılabilir')
    net=data.gross_kg-data.tare_kg
    if net<=0:raise HTTPException(422,'Brüt tartım daradan büyük olmalı')
    if db.scalar(select(GoodsReceipt.id).where(GoodsReceipt.weigh_ticket_no==data.weigh_ticket_no)):
        raise HTTPException(409,'Kantar fişi zaten mevcut')
    obj=GoodsReceipt(**data.model_dump(),net_kg=net)
    db.add(obj);db.commit();db.refresh(obj)
    return {'id':obj.id,'net_kg':str(obj.net_kg),'status':obj.status}

@router.post('/invoices',status_code=201)
def create_invoice_line(data:InvoiceLineIn,db:Session=Depends(get_db)):
    if not db.get(Item,data.item_id):raise HTTPException(404,'Stok kartı bulunamadı: önce taslak kart eşleştirin')
    existing=db.scalar(select(PurchaseInvoiceLine.id).where(PurchaseInvoiceLine.supplier_tax_id==data.supplier_tax_id,PurchaseInvoiceLine.invoice_no==data.invoice_no,PurchaseInvoiceLine.line_no==data.line_no))
    if existing:raise HTTPException(409,'Aynı fatura satırı zaten kaydedilmiş')
    obj=PurchaseInvoiceLine(**data.model_dump());db.add(obj);db.commit();db.refresh(obj)
    return {'id':obj.id,'status':obj.status,'quantity_kg':str(obj.quantity_kg)}

@router.post('/weighings/{receipt_id}/accept')
def accept_receipt(receipt_id:int,db:Session=Depends(get_db)):
    obj=db.get(GoodsReceipt,receipt_id)
    if obj is None: raise HTTPException(404,'Kantar fişi bulunamadı')
    if obj.status!='WEIGHED':raise HTTPException(409,'Bu kabul zaten işlendi')
    # Lock the source receipt in production DB (SELECT FOR UPDATE) to prevent concurrent posting.
    db.add(StockMovement(item_id=obj.item_id,type='IN',quantity=obj.net_kg,reference=f'RECEIPT:{obj.id}'))
    obj.status='ACCEPTED';db.commit()
    return {'status':obj.status,'stock_in_kg':str(obj.net_kg)}

@router.post('/compare')
def compare(data:CompareIn,db:Session=Depends(get_db)):
    receipt=db.get(GoodsReceipt,data.receipt_id)
    invoice=db.get(PurchaseInvoiceLine,data.invoice_line_id)
    if not receipt or not invoice:raise HTTPException(404,'Kantar veya fatura satırı bulunamadı')
    if receipt.supplier_tax_id!=invoice.supplier_tax_id or receipt.item_id!=invoice.item_id:
        raise HTTPException(409,'Firma/vergi numarası veya ürün uyuşmuyor')
    if receipt.delivery_note_no and invoice.delivery_note_no and receipt.delivery_note_no!=invoice.delivery_note_no:
        raise HTTPException(409,'İrsaliye numaraları farklı; manuel inceleme gerekli')
    if db.scalar(select(Reconciliation.id).where(Reconciliation.receipt_id==receipt.id,Reconciliation.invoice_line_id==invoice.id)):
        raise HTTPException(409,'Bu eşleşme daha önce yapılmış')
    diff=invoice.quantity_kg-receipt.net_kg
    percent=abs(diff)/receipt.net_kg*100
    # Both absolute and relative thresholds apply; exceeding either means alert.
    matched=abs(diff)<=data.tolerance_kg and percent<=data.tolerance_percent
    status='MATCHED' if matched else 'DISCREPANCY'
    row=Reconciliation(receipt_id=receipt.id,invoice_line_id=invoice.id,difference_kg=diff,status=status)
    db.add(row);invoice.status='RECONCILED' if matched else 'REVIEW_REQUIRED';db.commit();db.refresh(row)
    return {'match_id':row.id,'status':status,'weighed_kg':str(receipt.net_kg),'invoice_kg':str(invoice.quantity_kg),'difference_kg':str(diff),'difference_percent':str(percent.quantize(Decimal('0.01'))),'alert':not matched}

@router.get('/alerts')
def alerts(db:Session=Depends(get_db)):
    rows=db.scalars(select(Reconciliation).where(Reconciliation.status=='DISCREPANCY').order_by(Reconciliation.id.desc())).all()
    return [{'id':r.id,'receipt_id':r.receipt_id,'invoice_line_id':r.invoice_line_id,'difference_kg':str(r.difference_kg),'status':r.status} for r in rows]

@router.get('/pending')
def pending(db:Session=Depends(get_db)):
    receipts=db.scalars(select(GoodsReceipt)).all()
    invoices=db.scalars(select(PurchaseInvoiceLine)).all()
    reconciled_receipts=set(db.scalars(select(Reconciliation.receipt_id)).all())
    reconciled_invoices=set(db.scalars(select(Reconciliation.invoice_line_id)).all())
    return {'unmatched_receipts':[{'id':r.id,'ticket':r.weigh_ticket_no,'net_kg':str(r.net_kg)} for r in receipts if r.id not in reconciled_receipts], 'unmatched_invoices':[{'id':i.id,'invoice':i.invoice_no,'quantity_kg':str(i.quantity_kg)} for i in invoices if i.id not in reconciled_invoices]}
