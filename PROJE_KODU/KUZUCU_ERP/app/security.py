"""Yerel pilot için zorunlu giriş, sunucu tarafında yetkilendirme ve değişiklik denetimi.
Bu mekanizma internete açık canlı ERP güvenlik incelemesinin yerine geçmez.
"""
from __future__ import annotations
import contextvars
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, select, event, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from .db import Base, get_db
from .models import utc_now

actor_context: contextvars.ContextVar[str] = contextvars.ContextVar('kuzucu_actor',default='sistem')

# Every scope has explicit operation grants; reports use dedicated grants.
MODULES = {
 'dashboard':'Genel Bakış', 'tarim.parseller':'Tarım / Parseller', 'tarim.uretim':'Tarım / Üretim Sezonları',
 'hayvanlar.padok':'Hayvanlar / Gruplar', 'hayvanlar.kart':'Hayvanlar / Kayıtlar',
 'hayvanlar.tartim':'Hayvanlar / Tartımlar', 'hayvanlar.buzagi':'Hayvanlar / Buzağılar',
 'hayvanlar.saglik':'Hayvanlar / Sağlık ve Tedavi',
 'stok.urun':'Stok / Ürünler', 'stok.hareket':'Stok / Hareketler',
 'firmalar':'Firmalar / Cariler', 'ajanda':'Ajanda / Hatırlatmalar',
 'entegrasyon':'Entegrasyonlar', 'belge':'Fotoğraf / PDF Okuma',
 'muhasebe.fatura':'Muhasebe / Faturalar',
 'muhasebe.finans':'Muhasebe / Finans (gelecek)',
 'hesap.banka':'Hesap / Banka (gelecek)', 'hesap.kasa':'Hesap / Kasa (gelecek)',
 'hesap.cari':'Hesap / Borç / Alacak', 'personel':'Personel',
 'reports.summary':'Rapor / İşletme Özeti', 'reports.animals':'Rapor / Hayvanlar',
 'reports.weighings':'Rapor / Tartımlar', 'reports.calves':'Rapor / Buzağı Çıkışı',
 'reports.health':'Rapor / Sağlık', 'reports.stock':'Rapor / Stok',
 'reports.fields':'Rapor / Tarım / Parseller', 'reports.production':'Rapor / Üretim / Verim (gelecek)',
 'reports.cost':'Rapor / Maliyet', 'reports.finance':'Rapor / Muhasebe',
 'reports.accounts':'Rapor / Hesap Bilgileri (gelecek)', 'reports.payroll':'Rapor / Personel, Mesai ve İzin',
 'audit':'Kullanıcı İşlem Geçmişi',
}
OPERATIONS=('view','create','edit','delete','export')

class User(Base):
    __tablename__='erp_users'
    id:Mapped[int]=mapped_column(primary_key=True)
    username:Mapped[str]=mapped_column(String(80),unique=True,index=True)
    display_name:Mapped[str]=mapped_column(String(120))
    department:Mapped[str]=mapped_column(String(100),default='')
    password_hash:Mapped[str]=mapped_column(String(256))
    is_admin:Mapped[bool]=mapped_column(Boolean,default=False)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
    permissions_json:Mapped[str]=mapped_column(Text,default='[]')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)

class LoginSession(Base):
    __tablename__='erp_login_sessions'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('erp_users.id'),index=True)
    token_hash:Mapped[str]=mapped_column(String(64),unique=True,index=True)
    csrf_token:Mapped[str]=mapped_column(String(64))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))

class AuditEvent(Base):
    __tablename__='erp_audit_events'
    id:Mapped[int]=mapped_column(primary_key=True)
    happened_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now,index=True)
    actor:Mapped[str]=mapped_column(String(120),default='sistem',index=True)
    table_name:Mapped[str]=mapped_column(String(100),index=True)
    record_id:Mapped[str]=mapped_column(String(80),index=True)
    action:Mapped[str]=mapped_column(String(16))
    changes_json:Mapped[str]=mapped_column(Text,default='{}')

class FormDraft(Base):
    __tablename__='erp_form_drafts'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('erp_users.id'),index=True)
    form_key:Mapped[str]=mapped_column(String(100))
    data_json:Mapped[str]=mapped_column(Text)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    __table_args__=(UniqueConstraint('user_id','form_key',name='unique_draft_user_form'),)

ROUNDS=260000

def password_hash(value:str)->str:
    if len(value)<10:raise HTTPException(422,'Şifre en az 10 karakter olmalıdır.')
    salt=secrets.token_bytes(16)
    dig=hashlib.pbkdf2_hmac('sha256',value.encode(),salt,ROUNDS)
    return f'pbkdf2-sha256${ROUNDS}${salt.hex()}${dig.hex()}'

def verify_password(value:str, stored:str)->bool:
    try:
        alg, rounds, salt, digest=stored.split('$')
        return alg=='pbkdf2-sha256' and hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',value.encode(),bytes.fromhex(salt),int(rounds)),bytes.fromhex(digest))
    except (ValueError,TypeError):return False

def token_digest(token:str)->str:return hashlib.sha256(token.encode()).hexdigest()

def scopes(user:User)->set[str]:
    if user.is_admin:return {'*'}
    try:return set(json.loads(user.permissions_json))
    except (ValueError,TypeError):return set()

def allowed(user:User, permission:str)->bool:
    return user.is_admin or permission in scopes(user)

def safe_user(u:User):
    return {'id':u.id,'username':u.username,'display_name':u.display_name,'department':u.department,
            'is_admin':u.is_admin,'is_active':u.is_active,'permissions':sorted(scopes(u))}

def current_user(request:Request)->User:
    user=getattr(request.state,'erp_user',None)
    if user is None:raise HTTPException(401,'Önce kullanıcı girişi yapın.')
    return user

def need(request:Request,key:str)->User:
    user=current_user(request)
    if not allowed(user,key):raise HTTPException(403,'Bu işlem için yetkiniz bulunmuyor.')
    return user

router=APIRouter(prefix='/api/auth',tags=['Kullanıcı ve yetkilendirme'])
class Credentials(BaseModel):
    username:str=Field(min_length=3,max_length=80)
    password:str=Field(min_length=10,max_length=200)
    @field_validator('username')
    @classmethod
    def username_valid(cls,value):
        value=value.strip().lower()
        if len(value)<3 or any(ord(c)<32 for c in value):raise ValueError('Geçerli bir kullanıcı adı girin.')
        return value
class Bootstrap(Credentials):
    display_name:str=Field(min_length=2,max_length=120)
class UserIn(Bootstrap):
    department:str=Field(default='',max_length=100)
    is_active:bool=True
    is_admin:bool=False
    permissions:list[str]=Field(default_factory=list,max_length=300)
class UserUpdate(BaseModel):
    username:str|None=Field(default=None,min_length=3,max_length=80)
    display_name:str=Field(min_length=2,max_length=120)
    department:str=Field(default='',max_length=100)
    is_active:bool=True
    is_admin:bool=False
    permissions:list[str]=Field(default_factory=list,max_length=300)
    new_password:str|None=None

class DeleteUserInput(BaseModel):
    password:str=Field(min_length=1,max_length=200)

def grant_list(perms):
    possible={f'{mod}.{op}' for mod in MODULES for op in OPERATIONS}
    unknown=set(perms)-possible
    if unknown:raise HTTPException(422,'Tanımlanmamış yetki seçildi.')
    return json.dumps(sorted(set(perms)),ensure_ascii=False)

def lock_user_changes(db):
    # İki yöneticinin aynı anda birbirini kapatması son aktif yöneticiyi kaldıramaz.
    if db.get_bind().dialect.name=='sqlite':
        if not db.in_transaction():db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    else:
        list(db.scalars(select(User).where(User.is_admin==True,User.is_active==True).with_for_update()))

def cookie_response(result,db,user,req):
    token=secrets.token_urlsafe(42)
    csrf=secrets.token_urlsafe(32)
    until=utc_now()+timedelta(hours=12)
    db.add(LoginSession(user_id=user.id,token_hash=token_digest(token),csrf_token=csrf,expires_at=until))
    db.commit()
    response=JSONResponse({**result,'user':safe_user(user),'csrf_token':csrf})
    response.set_cookie('kuzucu_session',token,httponly=True,samesite='strict',secure=req.url.scheme=='https',max_age=12*3600,path='/')
    return response

@router.get('/setup')
def setup(db:Session=Depends(get_db)):
    return {'needs_setup': db.query(User.id).first() is None}

@router.post('/bootstrap')
def bootstrap(data:Bootstrap,request:Request,db:Session=Depends(get_db)):
    # Ilk yonetici sadece bilgisayarin kendisinde olusturulabilir.
    if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
        raise HTTPException(403,'İlk yönetici yalnızca bu bilgisayardan oluşturulabilir.')
    if db.query(User.id).first() is not None:
        raise HTTPException(409,'Yönetici zaten oluşturulmuş. Lütfen giriş yapın.')
    user=User(username=data.username.strip().lower(),display_name=data.display_name.strip(),password_hash=password_hash(data.password),is_admin=True,permissions_json='[]')
    db.add(user)
    try:db.commit();db.refresh(user)
    except Exception:
        db.rollback();raise HTTPException(409,'Kullanıcı oluşturulamadı. Yeniden deneyin.')
    return cookie_response({'message':'Yönetici hesabı oluşturuldu.'},db,user,request)

@router.post('/login')
def login(data:Credentials,request:Request,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.username==data.username.strip().lower()))
    if user is None or not user.is_active or not verify_password(data.password,user.password_hash):
        raise HTTPException(401,'Kullanıcı adı veya şifre hatalı.')
    return cookie_response({'message':'Giriş başarılı.'},db,user,request)

@router.post('/logout')
def logout(request:Request,db:Session=Depends(get_db)):
    token=request.cookies.get('kuzucu_session','')
    if token: db.query(LoginSession).filter(LoginSession.token_hash==token_digest(token)).delete();db.commit()
    r=JSONResponse({'message':'Çıkış yapıldı.'});r.delete_cookie('kuzucu_session',path='/');return r

@router.get('/me')
def me(request:Request):
    u=current_user(request)
    return {'user':safe_user(u),'csrf_token':request.state.erp_session.csrf_token,'modules':MODULES,'operations':OPERATIONS}

@router.get('/users')
def users(request:Request,db:Session=Depends(get_db)):
    if not current_user(request).is_admin:
        raise HTTPException(403,'Kullanıcı listesine yalnızca yönetici erişebilir.')
    return [safe_user(x) for x in db.scalars(select(User).order_by(User.username))]

@router.post('/users',status_code=201)
def add_user(data:UserIn,request:Request,db:Session=Depends(get_db)):
    u=current_user(request)
    if not u.is_admin:raise HTTPException(403,'Kullanıcı yönetimi yalnızca yöneticidedir.')
    obj=User(username=data.username.strip().lower(),display_name=data.display_name.strip(),department=data.department,
             is_admin=data.is_admin,is_active=data.is_active,permissions_json=grant_list(data.permissions),password_hash=password_hash(data.password))
    db.add(obj)
    try:db.commit();db.refresh(obj)
    except Exception:db.rollback();raise HTTPException(409,'Kullanıcı adı kullanımda.')
    return safe_user(obj)

@router.put('/users/{user_id}')
def edit_user(user_id:int,data:UserUpdate,request:Request,db:Session=Depends(get_db)):
    u=current_user(request)
    if not u.is_admin:raise HTTPException(403,'Kullanıcı yönetimi yalnızca yöneticidedir.')
    lock_user_changes(db)
    obj=db.get(User,user_id)
    if not obj:raise HTTPException(404,'Kullanıcı bulunamadı.')
    if obj.id==u.id and (not data.is_admin or not data.is_active):
        raise HTTPException(409,'Kendi yönetici yetkinizi veya hesabınızı kapatamazsınız.')
    if obj.is_admin and (not data.is_admin or not data.is_active):
        count=db.query(User).filter(User.is_admin==True,User.is_active==True).count()
        if count<=1:raise HTTPException(409,'Son aktif yönetici kapatılamaz.')
    if data.username is not None:
        username=data.username.strip().lower()
        if len(username)<3 or any(ord(ch)<32 for ch in username):raise HTTPException(422,'Kullanıcı adı en az 3 karakter olmalı ve kontrol karakteri içermemelidir.')
        if db.scalar(select(User.id).where(User.username==username,User.id!=obj.id)):
            raise HTTPException(409,'Kullanıcı adı kullanımda. Başka bir ad seçin.')
        obj.username=username
    obj.display_name=data.display_name.strip();obj.department=data.department
    obj.is_active=data.is_active;obj.is_admin=data.is_admin;obj.permissions_json=grant_list(data.permissions)
    if data.new_password:
        if len(data.new_password)>200:raise HTTPException(422,'Şifre en fazla 200 karakter olmalıdır.')
        obj.password_hash=password_hash(data.new_password)
    if not data.is_active:db.query(LoginSession).filter(LoginSession.user_id==obj.id).delete()
    db.commit();return safe_user(obj)

@router.delete('/users/{user_id}')
def delete_user(user_id:int,data:DeleteUserInput,request:Request,db:Session=Depends(get_db)):
    actor=current_user(request)
    if not actor.is_admin:raise HTTPException(403,'Kullanıcı silme işlemini yalnızca yönetici yapabilir.')
    lock_user_changes(db)
    obj=db.get(User,user_id)
    if obj is None:raise HTTPException(404,'Kullanıcı bulunamadı.')
    if obj.id==actor.id:raise HTTPException(409,'Giriş yaptığınız hesabı silemezsiniz.')
    if obj.is_admin and obj.is_active and db.query(User).filter(User.is_admin==True,User.is_active==True).count()<=1:
        raise HTTPException(409,'Son aktif yönetici silinemez.')
    if not verify_password(data.password,obj.password_hash):
        raise HTTPException(403,'Silinecek kullanıcının şifresi hatalı. Kullanıcı silinmedi.')
    db.query(LoginSession).filter(LoginSession.user_id==obj.id).delete()
    db.query(FormDraft).filter(FormDraft.user_id==obj.id).delete()
    from .camera_documents import CapturedDocument
    for document in db.scalars(select(CapturedDocument).where(CapturedDocument.owner_id==obj.id)):
        document.owner_id=None
    db.delete(obj)
    db.commit()
    return {'deleted':True,'message':'Kullanıcı silindi. Geçmiş işlem kayıtları korundu.'}

@router.get('/audit')
def audit(request:Request,limit:int=200,db:Session=Depends(get_db)):
    from .translations import TABLE_LABELS, ACTION_LABELS, describe_changes
    need(request,'audit.view')
    rows=db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(min(max(limit,1),1000)))
    return [{'id':a.id,'when':a.happened_at,'actor':a.actor,'entity':a.table_name,'record_id':a.record_id,
             'action':a.action,'changes':json.loads(a.changes_json),
             'entity_label':TABLE_LABELS.get(a.table_name,'Diğer kayıtlar'),
             'action_label':ACTION_LABELS.get(a.action,'Kayıt işlemi'),
             'display_changes':describe_changes(json.loads(a.changes_json),MODULES)} for a in rows]

class DraftInput(BaseModel):
    values:dict[str,str|int|float|bool|None]=Field(default_factory=dict,max_length=120)
@router.get('/drafts/{form_key}')
def get_draft(form_key:str,request:Request,db:Session=Depends(get_db)):
    u=current_user(request)
    x=db.scalar(select(FormDraft).where(FormDraft.user_id==u.id,FormDraft.form_key==form_key))
    return {'values':json.loads(x.data_json) if x else {},'updated_at':x.updated_at.isoformat() if x else None}
@router.put('/drafts/{form_key}')
def put_draft(form_key:str,data:DraftInput,request:Request,db:Session=Depends(get_db)):
    u=current_user(request)
    if len(form_key)>100 or len(json.dumps(data.values,ensure_ascii=False))>30000:
        raise HTTPException(422,'Taslak çok büyük.')
    x=db.scalar(select(FormDraft).where(FormDraft.user_id==u.id,FormDraft.form_key==form_key))
    if not x:x=FormDraft(user_id=u.id,form_key=form_key,data_json='{}');db.add(x)
    x.data_json=json.dumps(data.values,ensure_ascii=False);x.updated_at=utc_now()
    db.commit();return {'saved':True}
@router.delete('/drafts/{form_key}')
def delete_draft(form_key:str,request:Request,db:Session=Depends(get_db)):
    u=current_user(request)
    db.query(FormDraft).filter(FormDraft.user_id==u.id,FormDraft.form_key==form_key).delete();db.commit()
    return {'deleted':True}

PUBLIC_PATHS={'/','/api/auth/setup','/api/auth/bootstrap','/api/auth/login','/api/health'}

def permission_for(path:str,method:str):
    parts=path.strip('/').split('/')
    if len(parts)<2 or parts[0]!='api':return None
    name=parts[1]
    if name in ('finance','personnel','animal-operations','capture'):return None
    if path=='/api/calves/resolve-exit-tags':return 'hayvanlar.buzagi.view'
    op='view' if method in ('GET','HEAD') else 'edit' if method in ('PUT','PATCH') else 'delete' if method=='DELETE' else 'create'
    fixed={'dashboard':'dashboard','pens':'hayvanlar.padok','animals':'hayvanlar.kart','fields':'tarim.parseller',
        'seasons':'tarim.uretim','items':'stok.urun','stock':'stok.hareket','stock-movements':'stok.hareket',
        'firms':'firmalar','reminders':'ajanda','calves':'hayvanlar.buzagi','animal-health':'hayvanlar.saglik',
        'receiving':'stok.hareket','documents':'belge','imports':'entegrasyon','integrations':'entegrasyon'}
    if name=='auth':
        if len(parts)>2 and parts[2] in ('me','logout','drafts','audit','users'):
            if parts[2]=='audit':return 'audit.view'
            if parts[2]=='users':return None # server enforces admin in all handlers
            return None
        return '!deny'
    if method=='GET' and name=='animals' and len(parts)==2:
        return '|hayvanlar.kart.view|hayvanlar.saglik.view|hayvanlar.tartim.view'
    if name=='animals' and 'weighings' in parts:return f'hayvanlar.tartim.{op}'
    if method=='GET' and name=='pens':return '|hayvanlar.padok.view|hayvanlar.kart.view|hayvanlar.saglik.view'
    if method=='GET' and name=='items':return '|stok.urun.view|stok.hareket.view'
    if method=='GET' and name=='fields':return '|tarim.parseller.view|tarim.uretim.view'
    if name=='breeds':return None # checked against either animal or calf visibility in handler
    if name=='reports':return None # fine-grained report check inside handler
    if name=='calves' and len(parts)>2 and parts[2].startswith('exit-report'):
        return '&reports.calves.view&reports.calves.export' if parts[2].endswith('.csv') else 'reports.calves.view'
    if name=='animal-health' and len(parts)>2:
        if parts[2]=='insights':return 'reports.health.view'
        if parts[2]=='daily.pdf':return '&reports.health.view&reports.health.export&ajanda.view'
        if parts[2] in ('print-today','print-settings') and method!='GET':return '&reports.health.export&ajanda.view'
    if name=='stock-movements' and len(parts)>3 and parts[3]=='revisions':return 'audit.view'
    if name in fixed:return f'{fixed[name]}.{op}'
    return '!deny'

async def auth_middleware(request:Request,call_next):
    path=request.url.path
    if path.startswith('/static/') or path in PUBLIC_PATHS:
        return await call_next(request)
    from .db import SessionLocal
    # Both local launcher and test fixtures may override get_db; auth is bound to the same database
    # via request.app.state.auth_session_factory in lifespan.
    factory=getattr(request.app.state,'auth_session_factory',SessionLocal)
    with factory() as db:
        raw=request.cookies.get('kuzucu_session','')
        login_session=db.scalar(select(LoginSession).where(LoginSession.token_hash==token_digest(raw))) if raw else None
        now=utc_now()
        def valid_expiry(s):
            if not s:return False
            exp=s.expires_at
            if exp.tzinfo is None:exp=exp.replace(tzinfo=timezone.utc)
            return exp>now
        user=db.get(User,login_session.user_id) if valid_expiry(login_session) else None
        if not user or not user.is_active:return JSONResponse({'detail':'Oturum kapandı. Lütfen giriş yapın.'},status_code=401)
        perm=permission_for(path,request.method)
        permitted = (not perm or (perm.startswith('|') and any(allowed(user,x) for x in perm.split('|') if x))
                     or (perm.startswith('&') and all(allowed(user,x) for x in perm.split('&') if x))
                     or allowed(user,perm))
        if perm=='!deny' or not permitted:
            return JSONResponse({'detail':'Bu bölüm veya işlem için yetkiniz bulunmuyor.'},status_code=403)
        if request.method not in ('GET','HEAD','OPTIONS'):
            if not hmac.compare_digest(request.headers.get('x-csrf-token',''),login_session.csrf_token):
                return JSONResponse({'detail':'Güvenlik doğrulaması başarısız. Sayfayı yenileyin.'},status_code=403)
        request.state.erp_user=user
        request.state.erp_session=login_session
        marker=actor_context.set(f'{user.display_name} ({user.username})')
        try:return await call_next(request)
        finally:actor_context.reset(marker)

SENSITIVE={'password_hash','token_hash','csrf_token','data_json'}
def _val(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,(datetime,)):return value.isoformat()
    if isinstance(value,Decimal):return str(value)
    if isinstance(value,(list,tuple,set)):return [_val(v) for v in value]
    try:return value.isoformat()
    except AttributeError:return str(value)

@event.listens_for(Session,'before_flush')
def collect_modified(session,flush_context,instances):
    if session.info.get('audit_busy'):return
    changes=[]
    for obj in list(session.dirty)+list(session.deleted):
        if not hasattr(obj,'__table__') or isinstance(obj,(AuditEvent,LoginSession,FormDraft)):continue
        state=inspect(obj)
        diff={}
        for col in obj.__table__.columns:
            if col.name in SENSITIVE:continue
            hist=state.attrs[col.name].history
            if hist.has_changes():diff[col.name]={'once':_val(hist.deleted[0]) if hist.deleted else None,
                                                    'new':_val(hist.added[0]) if hist.added else None}
        if diff or obj in session.deleted:
            changes.append((obj.__table__.name,str(getattr(obj,'id','')),
                           'SIL' if obj in session.deleted else 'DUZENLE',diff))
    session.info['pending_audit']=changes

@event.listens_for(Session,'after_flush')
def save_audit(session,ctx):
    # Direct DB insert shares the same transaction as domain data, so audit cannot
    # appear committed without the matching data commit (or vice versa).
    events=list(session.info.pop('pending_audit',[]))
    for obj in session.new:
        if not hasattr(obj,'__table__') or isinstance(obj,(AuditEvent,LoginSession,FormDraft)):continue
        vals={col.name:_val(getattr(obj,col.name,None)) for col in obj.__table__.columns if col.name not in SENSITIVE}
        events.append((obj.__table__.name,str(getattr(obj,'id','')),'EKLE',vals))
    if not events:return
    actor=actor_context.get()
    session.connection().execute(AuditEvent.__table__.insert(),[{'actor':actor,'table_name':name,'record_id':key,
         'action':action,'changes_json':json.dumps(changes,ensure_ascii=False)} for name,key,action,changes in events])

def creator_map(db:Session,table:str,ids:list[int]):
    if not ids:return {}
    rows=db.scalars(select(AuditEvent).where(AuditEvent.table_name==table,AuditEvent.record_id.in_([str(i) for i in ids]),AuditEvent.action=='EKLE').order_by(AuditEvent.id.asc())).all()
    out={}
    for row in rows:out.setdefault(int(row.record_id),row.actor)
    return out
