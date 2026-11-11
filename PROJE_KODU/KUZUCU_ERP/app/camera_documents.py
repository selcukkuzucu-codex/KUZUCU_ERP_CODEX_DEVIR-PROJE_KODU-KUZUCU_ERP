"""Onaylı küpe okuma ve belge aktarımı. OCR tek başına işletme kaydı oluşturmaz."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, get_db
from .document_preview import parse_fields
from .models import Animal, Firm, Item, Weighing, utc_now
from .security import allowed, current_user, need

router = APIRouter(prefix='/api/capture', tags=['Kamera ve onaylı belge aktarımı'])
MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 24_000_000


def today_local():
    return datetime.now(ZoneInfo('Europe/Istanbul')).date()


class CapturedDocument(Base):
    __tablename__ = 'captured_documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64), unique=True)
    original_name: Mapped[str] = mapped_column(String(180))
    suffix: Mapped[str] = mapped_column(String(8))
    # Silinen hesapların belgeleri yönetici arşivinde korunur. Kimliği sonradan
    # tekrar kullanılan yeni bir kullanıcı eski belgelerin sahibi sayılmaz.
    owner_id: Mapped[int | None] = mapped_column(ForeignKey('erp_users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DocumentFirmLink(Base):
    __tablename__ = 'document_firm_links'
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('captured_documents.id'))
    firm_id: Mapped[int] = mapped_column(ForeignKey('firms.id'))
    __table_args__ = (UniqueConstraint('document_id', 'firm_id', name='unique_document_firm'),)


class DocumentWeighingRun(Base):
    __tablename__ = 'document_weighing_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('captured_documents.id'), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    weighing_ids: Mapped[str] = mapped_column(Text)


def _any(request, *permissions):
    user = current_user(request)
    if not any(allowed(user, p) for p in permissions):
        raise HTTPException(403, 'Bu işlem için yetkiniz bulunmuyor.')
    return user


def _lock(db):
    if db.bind.dialect.name == 'sqlite':
        if db.in_transaction():
            db.rollback()
        db.execute(text('BEGIN IMMEDIATE'))


def _root():
    root = Path(os.environ.get('KUZUCU_DOCUMENT_DIR', 'data/documents'))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(doc):
    return _root() / (doc.source_key + '.' + doc.suffix)


async def _image(file):
    suffix = (file.filename or '').rsplit('.', 1)[-1].lower()
    if suffix not in ('jpg', 'jpeg', 'png', 'webp'):
        raise HTTPException(422, 'JPG, PNG veya WEBP biçiminde bir fotoğraf seçin.')
    data = await file.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(413, 'Fotoğraf boş olmamalı ve 8 MB sınırını aşmamalıdır.')
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.width * probe.height > MAX_PIXELS:
                raise HTTPException(422, 'Fotoğraf çok büyük. Daha küçük bir kopyasını seçin.')
            if probe.format not in ('JPEG', 'PNG', 'WEBP'):
                raise HTTPException(422, 'Dosyanın içeriği desteklenen bir fotoğraf değil.')
            suffix = {'JPEG':'jpg','PNG':'png','WEBP':'webp'}[probe.format]
            probe.verify()
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert('RGB')
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, 'Fotoğraf açılamadı. Başka bir fotoğraf seçin.') from exc
    return data, image, suffix


def _ocr(image, psm=6, digits=False):
    import pytesseract
    cfg = f'--psm {psm}' + (' -c tessedit_char_whitelist=0123456789TR' if digits else '')
    result = pytesseract.image_to_data(image, lang='tur+eng', config=cfg, output_type=pytesseract.Output.DICT, timeout=5)
    lines = {}
    scores = []
    for i, token in enumerate(result['text']):
        if not token.strip():
            continue
        key = (result['block_num'][i], result['par_num'][i], result['line_num'][i])
        lines.setdefault(key, []).append(token)
        try:
            scores.append(max(0, float(result['conf'][i])))
        except (ValueError, TypeError):
            pass
    return '\n'.join(' '.join(v) for v in lines.values()), round(sum(scores) / len(scores), 1) if scores else 0


def tag_regions(image):
    """Renkli plastik kümelerini ayır; tüm kare OCR'sinden önce küpe alanına odaklan."""
    small = image.copy()
    small.thumbnail((220, 220))
    w, h = small.size
    px = small.load()
    masks = {'tr': set(), 'farm': set(), 'green': set()}
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r > 100 and g > 85 and b < min(r, g) * .73 and r < g * 1.8:
                masks['tr'].add((x, y))
            elif r > 95 and r > g * 1.4 and r > b * 1.25:
                masks['farm'].add((x, y))
            elif g > 60 and g > r * 1.13 and g > b * 1.05:
                masks['green'].add((x, y))
    result = []
    for kind, points in masks.items():
        while points:
            start = points.pop()
            stack, component = [start], [start]
            while stack:
                x, y = stack.pop()
                for point in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if point in points:
                        points.remove(point); stack.append(point); component.append(point)
            if len(component) < max(30, w*h*.002):
                continue
            xs, ys = zip(*component)
            if max(xs)-min(xs) < 12 or max(ys)-min(ys) < 10:
                continue
            sx, sy = image.width/w, image.height/h
            box = (max(0,int((min(xs)-3)*sx)),max(0,int((min(ys)-3)*sy)),min(image.width,int((max(xs)+4)*sx)),min(image.height,int((max(ys)+4)*sy)))
            result.append((len(component), kind, box))
    return [(kind, box) for _, kind, box in sorted(result, reverse=True)[:4]]


def tag_candidates(text, confidence=0, region='unknown'):
    """Eksik rakamı üretmez. Yalnız aynı bölgedeki açık TR/il/numara satırlarını birleştirir."""
    clean = text.upper().replace('İ', 'I')
    rows = []
    # TR satırı ile il kodu ve ana numara bitişik veya alt satırda basılabilir.
    for match in re.finditer(r'\bTR\s*(\d{2})[\s/-]*(\d{6,12})\b', clean):
        rows.append({'value': 'TR'+match[1]+match[2], 'type': 'tr', 'partial': False, 'confidence': confidence})
    for value in re.findall(r'(?<![A-Z0-9])\d{2,14}(?![A-Z0-9])', clean):
        if any(value in r['value'] for r in rows):
            continue
        # Plastik rengi yalnız bölgeyi bulmaya yardımcı olur; küpe türünü
        # kanıtlamaz. İşletme başlığı okunmadıysa kullanıcı alanı seçmelidir.
        is_farm = 'KUZUCU' in clean or 'İŞLETME' in text.upper() or 'ISLETME' in clean
        kind = 'farm' if is_farm else 'unknown'
        partial = len(value) < 4 or region == 'tr' or kind == 'unknown'
        rows.append({'value': value, 'type': kind, 'partial': partial, 'confidence': confidence})
    return rows


def scan_tags(image):
    candidates, evidence = [], []
    regions = tag_regions(image) or [('unknown', (0,0,image.width,image.height))]
    ocr_available = False
    for kind, box in regions:
        crop = image.crop(box)
        crop.thumbnail((1400,1400))
        if crop.width < 650:
            crop = crop.resize((crop.width*2, crop.height*2))
        for angle in (0, -20, 20):
            rotated = crop.rotate(angle, expand=True, fillcolor='white')
            gray = ImageEnhance.Contrast(ImageOps.grayscale(rotated)).enhance(1.6)
            try:
                text_value, confidence = _ocr(gray, 6)
            except Exception:
                continue
            ocr_available = True
            evidence.append({'region': kind, 'angle': angle, 'text': text_value[:600]})
            for row in tag_candidates(text_value, confidence, kind):
                row['region'] = {'tr':'Sarı küpe bölgesi','farm':'Kırmızı küpe bölgesi','green':'Yeşil küpe bölgesi'}.get(kind,'Fotoğraf')
                candidates.append(row)
        # Uzun ve dar basılmış rakamlar genel metin okumasında kaçabilir.
        # Alt bölüm ayrı okunur; farklı geçişteki TR/il bilgisiyle birleştirilmez.
        # Bu geçiş yalnız belirsiz aday sağlar, bir tam kimlik kanıtı sayılmaz.
        if kind != 'unknown' and (box[2]-box[0]) * (box[3]-box[1]) < image.width * image.height * .8:
            digit_source = image.crop(box)
            digit_source.thumbnail((1400,1400))
            digits_crop = digit_source.crop((0, int(digit_source.height*.3), int(digit_source.width*.85), digit_source.height))
            for angle in (0, -20, 20):
                rotated = digits_crop.rotate(angle, expand=True, fillcolor='white')
                focused = ImageOps.autocontrast(rotated.getchannel('R'))
                focused = ImageEnhance.Contrast(focused.resize((focused.width*2, focused.height))).enhance(2)
                try:
                    digit_text, confidence = _ocr(focused, 6, True)
                except Exception:
                    continue
                ocr_available = True
                for value in re.findall(r'(?<![A-Z0-9])\d{4,14}(?![A-Z0-9])', digit_text.upper()):
                    candidates.append({'value':value,'type':'unknown','partial':True,'confidence':confidence,
                                       'region':'Rakam bölgesi; türü ve tamamı doğrulanmalı'})
    merged = {}
    for row in candidates:
        key = (row['type'], row['value'], row['partial'])
        if key not in merged or merged[key]['confidence'] < row['confidence']:
            merged[key] = row
    rows = sorted(merged.values(), key=lambda v:(v['partial'], -v['confidence']))[:18]
    return {'candidates': rows, 'notice': ('Numaraları fotoğrafla karşılaştırın. Eksik veya örtülü rakamlar tamamlanmadı; doğru alanı seçip onaylayın.' if rows else 'Küpe net okunamadı. Daha yakın ve düz bir fotoğraf çekin veya numarayı elle girin.'), 'ocr_available': ocr_available}


def normalize_tag(value):
    return re.sub(r'[\s./-]+', '', str(value or '')).upper()


def match_animal(db, tr_tag='', farm_tag=''):
    tr, farm = normalize_tag(tr_tag), normalize_tag(farm_tag)
    if not tr and not farm:
        return {'animal':None, 'state':'empty', 'message':'TR veya işletme küpe numarasını girin.'}
    # Keep identifiers as strings, including all leading zeroes; do not match suffixes.
    matches = []
    for tag, attr in ((tr,'ear_tag'),(farm,'farm_ear_tag')):
        if tag:
            found = [a for a in db.scalars(select(Animal)) if normalize_tag(getattr(a,attr)) == tag]
            if len(found)>1:
                return {'animal':None,'state':'ambiguous','message':'Numara birden fazla hayvanla eşleşti. Kayıtları kontrol edin.'}
            matches.append(found[0] if found else None)
    found = [a for a in matches if a is not None]
    if len({a.id for a in found}) > 1:
        return {'animal':None,'state':'conflict','message':'TR ve işletme küpeleri farklı hayvanlarla eşleşiyor. İşlem durduruldu.'}
    if len(matches)>1 and found and None in matches:
        return {'animal':None,'state':'conflict','message':'İki küpe birlikte doğrulanamadı. Numaraları kontrol edin veya yalnız doğruladığınız küpeyi kullanın.'}
    if not found:
        return {'animal':None,'state':'missing','message':'Bu küpeyle kayıtlı hayvan bulunamadı. Numarayı kontrol edin.'}
    a = found[0]
    return {'animal':{'id':a.id,'tr_tag':a.ear_tag,'farm_tag':a.farm_ear_tag or '', 'status':a.status},'state':'matched','message':'Kayıtlı hayvan bulundu.'}


class MatchIn(BaseModel):
    tr_tag: str = Field(default='', max_length=60)
    farm_tag: str = Field(default='', max_length=60)


@router.post('/ear-tags')
async def ear_tags(request:Request, file:UploadFile=File(...)):
    _any(request,'hayvanlar.kart.view','hayvanlar.kart.create','hayvanlar.saglik.view','hayvanlar.saglik.create')
    _, image, _ = await _image(file)
    return await run_in_threadpool(scan_tags,image)


@router.post('/match')
def match(data:MatchIn, request:Request, db:Session=Depends(get_db)):
    _any(request,'hayvanlar.kart.view','hayvanlar.kart.create','hayvanlar.saglik.view','hayvanlar.saglik.create',
         'hayvanlar.tartim.view','hayvanlar.tartim.create')
    return match_animal(db,data.tr_tag,data.farm_tag)


def number(value):
    raw = str(value or '').strip().replace(' ', '')
    # OCR document values are in Turkish notation; frontend sends canonical strings.
    if ',' in raw:
        raw = raw.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+', raw):
        raw = raw.replace('.', '')
    try:
        value = Decimal(raw)
        if not value.is_finite():raise InvalidOperation
        return str(value)
    except InvalidOperation:
        return ''


def document_fields(text_value, kind='auto'):
    fields = parse_fields(text_value)
    date_match = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', text_value)
    iso = ''
    if date_match:
        try: iso = date(int(date_match[3]), int(date_match[2]), int(date_match[1])).isoformat()
        except ValueError: pass
    weights = []
    for line in text_value.splitlines():
        # Explicit tag followed by a separate kg value. Never infer missing tag digits.
        # Satır bütünü küpe ve kilo olmalı. Ürün/fiyat/KDV satırının sonundaki
        # sayıları bir hayvan kimliği sanarak tartım listesine taşımayız.
        m = re.fullmatch(r'\s*((?:TR\s*\d{2}[ -]*\d{6,12})|(?:\d{2,14}))\s*(?:[;|:]\s*|\s+)(\d{1,5}(?:[.,]\d{1,3})?)\s*(?:KG|KİLO|KILO)?\s*', line, re.I)
        if m:
            tag = normalize_tag(m[1]); kg = number(m[2])
            if kg and Decimal(kg)>0:
                weights.append({'tag':tag,'measured_at':iso or today_local().isoformat(),'weight_kg':kg})
    invoice_evidence = bool(re.search(r'FATURA|KDV|VERGİ|VERGI', text_value,re.I))
    inferred = kind if kind in ('invoice','weighing','other') else ('invoice' if invoice_evidence else ('weighing' if weights else 'other'))
    # Product line heuristic is only a draft: item and firm need explicit user selection.
    lines = []
    pattern = r'^(.+?)\s+(\d[\d.,]*)\s+(KG|LT|LİTRE|LITRE|ADET|TON)\s+(\d[\d.,]*)\s+%?\s*(\d{1,2})\s*$'
    for line in text_value.splitlines():
        m = re.search(pattern,line,re.I)
        if m:
            lines.append({'name':m[1].strip(),'quantity':number(m[2]),'unit':{'LİTRE':'lt','LITRE':'lt'}.get(m[3].upper(),m[3].lower()),'unit_price':number(m[4]),'vat_rate':m[5]})
    return {'kind':inferred,'fields':fields,'invoice_date':iso,'invoice_no':fields['Fatura / İrsaliye No'],'weights':weights[:200],'invoice_lines':lines[:100]}


def _source(db, key, request):
    user = current_user(request)
    doc = db.scalar(select(CapturedDocument).where(CapturedDocument.source_key==key))
    if not doc or (doc.owner_id != user.id and not user.is_admin):
        raise HTTPException(404,'Belge bulunamadı. Fotoğrafı yeniden yükleyin.')
    return doc


@router.post('/documents/preview')
async def preview(request:Request, file:UploadFile=File(...), kind:str=Form('auto'), db:Session=Depends(get_db)):
    user = need(request,'belge.create')
    data, image, suffix = await _image(file)
    try:
        text_value, confidence = await run_in_threadpool(_ocr,image,6)
        notice = 'Önizlemeyi fotoğrafla karşılaştırın; firma, ürün ve numaraları doğruladıktan sonra kaydedin.'
    except Exception:
        text_value, confidence = '', 0
        notice = 'Görüntüden yazı okunamadı. Alanları elle doldurabilirsiniz. Metin okuma için Tesseract ve Türkçe dil desteği gerekir.'
    key = hashlib.sha256(data).hexdigest()
    doc = db.scalar(select(CapturedDocument).where(CapturedDocument.source_key==key))
    if doc and doc.owner_id != user.id and not user.is_admin:
        raise HTTPException(409,'Bu belge daha önce farklı bir kullanıcı tarafından yüklenmiş. Yöneticiye başvurun.')
    if not doc:
        doc = CapturedDocument(source_key=key, original_name=Path(file.filename or 'Fotoğraf').name[:180], suffix=suffix, owner_id=user.id)
        dest = _path(doc)
        if not dest.exists():
            dest.write_bytes(data)
        db.add(doc)
        try:db.commit()
        except IntegrityError:
            db.rollback()
            doc = _source(db,key,request)
    result = document_fields(text_value,kind)
    if allowed(user,'hayvanlar.tartim.view') or allowed(user,'hayvanlar.tartim.create'):
        for row in result['weights']:
            found = match_animal(db, tr_tag=row['tag']) if row['tag'].startswith('TR') else match_animal(db,farm_tag=row['tag'])
            row.update({'animal_id':found['animal']['id'] if found['animal'] else None, 'match_message':found['message']})
    else:
        result['weights'] = []
    return {**result,'source_key':key,'document_id':doc.id,'filename':doc.original_name,'text':text_value[:12000],'confidence':confidence,'notice':notice,'file_url':f'/api/capture/documents/{doc.id}/file'}


@router.get('/documents/catalog')
def catalog(request:Request, db:Session=Depends(get_db)):
    user = need(request,'belge.view')
    return {'firms':[{'id':f.id,'name':f.name,'tax_no':f.tax_no or ''} for f in db.scalars(select(Firm).order_by(Firm.name))] if allowed(user,'firmalar.view') else [],
            'items':[{'id':i.id,'name':i.name,'unit':i.unit} for i in db.scalars(select(Item).order_by(Item.name))] if allowed(user,'stok.urun.view') else []}


@router.get('/documents/{document_id}/file')
def source_file(document_id:int, request:Request, db:Session=Depends(get_db)):
    need(request,'belge.view')
    doc=db.get(CapturedDocument,document_id)
    if not doc:raise HTTPException(404,'Belge bulunamadı.')
    _source(db,doc.source_key,request)
    if not _path(doc).is_file():raise HTTPException(404,'Belge dosyası bulunamadı.')
    return FileResponse(_path(doc),media_type={'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','webp':'image/webp'}[doc.suffix],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})


class WeightRow(BaseModel):
    animal_id: int = Field(gt=0)
    tag: str = Field(min_length=1,max_length=60)
    measured_at: date
    weight_kg: Decimal = Field(gt=0,le=5000,max_digits=9,decimal_places=3)


class WeighingImport(BaseModel):
    source_key: str = Field(pattern=r'^[a-f0-9]{64}$')
    rows: list[WeightRow] = Field(min_length=1,max_length=200)


@router.post('/documents/weighings')
def save_weighings(data:WeighingImport, request:Request, db:Session=Depends(get_db)):
    need(request,'belge.create');need(request,'hayvanlar.tartim.create')
    _lock(db)
    doc = _source(db,data.source_key,request)
    digest=hashlib.sha256(json.dumps([r.model_dump(mode='json') for r in data.rows],sort_keys=True).encode()).hexdigest()
    done=db.scalar(select(DocumentWeighingRun).where(DocumentWeighingRun.document_id==doc.id))
    if done:
        if done.content_hash!=digest:raise HTTPException(409,'Bu belgenin tartımları daha önce farklı bilgilerle kaydedilmiş. Tartımlar bölümünden kontrol edin.')
        return {'count':len(json.loads(done.weighing_ids)),'duplicate':True,'message':'Bu belgenin tartımları zaten kaydedilmiş; yeniden kayıt oluşturulmadı.'}
    seen=set();records=[]
    for row in data.rows:
        animal=db.get(Animal,row.animal_id)
        if not animal or normalize_tag(row.tag) not in (normalize_tag(animal.ear_tag),normalize_tag(animal.farm_ear_tag)):
            raise HTTPException(422,'Küpe ile seçilen hayvan uyuşmuyor. Tüm satırları kontrol edin.')
        if animal.id in seen:raise HTTPException(422,'Aynı hayvan listede birden fazla kez bulunuyor.')
        if row.measured_at>today_local() or row.measured_at<animal.arrival_date:
            raise HTTPException(422,'Tartım tarihi giriş tarihinden önce veya bugünden sonra olamaz.')
        seen.add(animal.id)
        records.append(Weighing(animal_id=animal.id,measured_at=row.measured_at,weight_kg=row.weight_kg))
    db.add_all(records);db.flush()
    db.add(DocumentWeighingRun(document_id=doc.id,content_hash=digest,weighing_ids=json.dumps([r.id for r in records])))
    try:db.commit()
    except IntegrityError as exc:
        db.rollback();raise HTTPException(409,'Belge aynı anda işlenmiş olabilir. Tartımları kontrol edin.') from exc
    return {'count':len(records),'duplicate':False,'message':'Tartımlar kayıtlı hayvanlara eklendi.'}


class FirmImport(BaseModel):
    source_key:str = Field(pattern=r'^[a-f0-9]{64}$')
    firm_id:int = Field(gt=0)


@router.post('/documents/firm')
def attach_firm(data:FirmImport, request:Request, db:Session=Depends(get_db)):
    need(request,'belge.create');need(request,'firmalar.edit')
    _lock(db);doc=_source(db,data.source_key,request)
    if not db.get(Firm,data.firm_id):raise HTTPException(404,'Firma bulunamadı. Önce doğru firma kartını oluşturun.')
    existing=db.scalar(select(DocumentFirmLink).where(DocumentFirmLink.document_id==doc.id,DocumentFirmLink.firm_id==data.firm_id))
    if not existing:
        db.add(DocumentFirmLink(document_id=doc.id,firm_id=data.firm_id));db.commit()
    return {'duplicate':bool(existing),'message':'Belge seçilen firmanın dosyasına eklendi. Hesap veya stok hareketi oluşturulmadı.'}


@router.get('/documents/firm/{firm_id}')
def firm_documents(firm_id:int, request:Request, db:Session=Depends(get_db)):
    need(request,'belge.view');need(request,'firmalar.view')
    user=current_user(request)
    query=select(CapturedDocument).join(DocumentFirmLink,DocumentFirmLink.document_id==CapturedDocument.id).where(DocumentFirmLink.firm_id==firm_id)
    if not user.is_admin:query=query.where(CapturedDocument.owner_id==user.id)
    return [{'id':d.id,'filename':d.original_name,'file_url':f'/api/capture/documents/{d.id}/file'} for d in db.scalars(query)]
