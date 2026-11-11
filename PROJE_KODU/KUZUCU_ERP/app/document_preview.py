"""Belge analizi: veritabanina YAZMAZ, yalnizca onizleme."""
from io import BytesIO
import re
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pypdf import PdfReader
from PIL import Image
router=APIRouter(prefix='/api/documents', tags=['documents'])
MAX_BYTES=8*1024*1024

def parse_fields(text: str):
    fields={'Belge türü':'','Firma / Cari':'','VKN / TCKN':'','Fatura / İrsaliye No':'','Tarih':'','Genel Toplam':'','Miktar (kg)':''}
    patterns={'VKN / TCKN':r'(?:VKN|V\.K\.N\.|Vergi\s*(?:No|Numarası)|TCKN)\s*[:#-]?\s*(\d{10,11})', 'Fatura / İrsaliye No':r'(?:Fatura\s*(?:No|Numarası)|İrsaliye\s*No|Belge\s*No)\s*[:#-]?\s*([A-Za-z0-9/-]{5,40})', 'Tarih':r'(?:Tarih|Date)\s*[:#-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})','Genel Toplam':r'(?:GENEL\s*TOPLAM|ÖDENECEK\s*TUTAR|TOPLAM\s*TUTAR)\s*[:₺TL ]*([\d.,]+)', 'Miktar (kg)':r'(?:Net\s*(?:Kg|Ağırlık|Kilo)|NET\s*MİKTAR)\s*[: ]*([\d.,]+)'}
    for label,pattern in patterns.items():
        m=re.search(pattern,text,re.I)
        if m:fields[label]=m.group(1).strip()
    return fields

@router.post('/preview')
async def document_preview(file:UploadFile=File(...),kind:str=Form('invoice')):
    name=file.filename or ''
    suffix=name.lower().rsplit('.',1)[-1] if '.' in name else ''
    if suffix not in ('pdf','png','jpg','jpeg','webp'):raise HTTPException(400,'Yalnızca PDF, JPG, PNG, WEBP destekleniyor')
    data=await file.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise HTTPException(413,'Dosya 8 MB sınırını aşıyor')
    text='';notice='Önizleme tamamlandı. Alanları özgün belgeyle karşılaştırın; otomatik muhasebe/stok kaydı yapılmadı.'
    try:
        if suffix=='pdf':
            reader=PdfReader(BytesIO(data))
            if len(reader.pages)>15:raise HTTPException(400,'Pilot sürümde PDF en fazla 15 sayfa olabilir')
            text='\n'.join((p.extract_text() or '') for p in reader.pages)
            if not text.strip():notice='Bu PDF taranmış görüntü içeriyor olabilir. OCR görüntü/PDF desteği henüz kurulmadı; OCR servis entegrasyonu gerekiyor.'
        else:
            with Image.open(BytesIO(data)) as im:
                im.verify()
            try:
                import pytesseract
                with Image.open(BytesIO(data)) as im:
                    text=pytesseract.image_to_string(im,lang='tur+eng')
            except Exception:
                notice='Görsel dosyası kabul edildi fakat OCR kullanılabilir değil. Windows üzerinde Tesseract OCR ve Türkçe dil dosyası kurulmalı; henüz alanlar çıkarılamadı.'
    except HTTPException:raise
    except Exception as exc:raise HTTPException(422,'Belge okunamadı; başka bir dosya deneyin') from exc
    fields=parse_fields(text);fields['Belge türü']={'invoice':'Fatura','weighbridge':'Kantar fişi','other':'Diğer belge'}.get(kind,'Diğer belge')
    return {'filename':name,'fields':fields,'text':text[:12000],'notice':notice}
