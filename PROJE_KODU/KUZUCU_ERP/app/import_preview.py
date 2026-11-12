"""Conservative, read-only DelPro / Excel CSV import preview.
Not a vendor-certified DelPro interface. Never writes to the database.
"""
import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import Animal

router = APIRouter(prefix='/api/imports', tags=['Data import (preview only)'])
ALIASES = {
    'ear_tag': {'ear_tag','kupe_no','kupe_numarasi','kupe','ear tag','animal_id','animal id','hayvan_no'},
    'breed': {'breed','irk','ırk'},
    'arrival_date': {'arrival_date','giris_tarihi','giriş_tarihi','entry_date'},
    'entry_weight_kg': {'entry_weight_kg','giris_kilosu','giriş_kilosu','giris_kg','initial_weight'},
    'pen_code': {'pen_code','padok','padok_kodu','group','grup'},
}

def simplify_header(s):
    return s.strip().lower().replace('\ufeff','').replace(' ','_')

def resolve_columns(cols):
    normalized = {simplify_header(c):c for c in cols}
    return {key: next((normalized[simplify_header(x)] for x in aliases if simplify_header(x) in normalized), None)
            for key,aliases in ALIASES.items()}

@router.post('/animals/preview')
def preview_animals(csv_bytes: bytes = Body(..., media_type='text/csv'), db: Session=Depends(get_db)):
    if len(csv_bytes)>2_000_000: raise HTTPException(413,'Dosya 2 MB sınırını aşıyor')
    try: raw = csv_bytes.decode('utf-8-sig')
    except UnicodeDecodeError: raise HTTPException(422,'UTF-8 CSV gerekli; Excel içinden UTF-8 CSV olarak kaydedin')
    try:
        dialect=csv.Sniffer().sniff(raw[:4096],delimiters=',;\t')
        rows=csv.DictReader(io.StringIO(raw), dialect=dialect)
        if not rows.fieldnames: raise ValueError('Başlık satırı bulunamadı')
        column_map=resolve_columns(rows.fieldnames)
        if not column_map['ear_tag']: raise HTTPException(422,'Küpe/hayvan numarası sütunu bulunamadı')
        existing=set(db.scalars(select(Animal.ear_tag)).all())
        seen=set(); issues=[]; sample=[]; counts={'valid':0,'duplicate_in_file':0,'already_exists':0,'invalid':0}
        for rowno,row in enumerate(rows, start=2):
            if rowno>10001: raise HTTPException(413,'Bir dosyada en fazla 10.000 kayıt önizlenebilir')
            tag=(row.get(column_map['ear_tag']) or '').strip()
            errors=[]
            if not tag: errors.append('Hayvan numarası boş')
            if len(tag)>60: errors.append('Hayvan numarası 60 karakterden uzun')
            if tag and tag in seen: counts['duplicate_in_file']+=1;errors.append('Dosyada tekrar eden numara')
            if tag and tag in existing: counts['already_exists']+=1;errors.append('Veritabanında mevcut')
            if tag: seen.add(tag)
            if column_map['arrival_date']:
                v=(row.get(column_map['arrival_date']) or '').strip()
                if v:
                    try: date.fromisoformat(v)
                    except ValueError: errors.append('Giriş tarihi YYYY-MM-DD olmalı')
            if column_map['entry_weight_kg']:
                v=(row.get(column_map['entry_weight_kg']) or '').strip()
                if v:
                    try:
                        weight=Decimal(v.replace(',','.'))
                        if not weight.is_finite() or weight<=0: raise ValueError()
                    except (InvalidOperation,ValueError):errors.append('Giriş kilosu pozitif sayı olmalı')
            if errors:
                counts['invalid']+=1
                if len(issues)<100:issues.append({'row':rowno,'tag':tag,'problems':errors})
            else:counts['valid']+=1
            if len(sample)<5:sample.append({'row':rowno,'tag':tag,'breed':row.get(column_map['breed']) if column_map['breed'] else None})
    except HTTPException: raise
    except (csv.Error,ValueError) as exc: raise HTTPException(422,f'CSV okunamadı: {str(exc)}')
    return {'mode':'preview_only_no_writes','detected_columns':column_map,'counts':counts,'sample':sample,'issues':issues,
            'notes':['Bu işlem veri kaydetmez.', 'Bu şablon DeLaval tarafından onaylı entegrasyon değildir.',
                     'Gerçek aktarım için padok eşleştirmesi ve eksik alanların kontrolü gerekir.']}
