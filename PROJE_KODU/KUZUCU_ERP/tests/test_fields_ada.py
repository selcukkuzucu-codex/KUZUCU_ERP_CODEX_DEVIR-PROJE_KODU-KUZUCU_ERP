from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import main
from app.db import get_db


def test_legacy_sqlite_migration_and_ada_edit(tmp_path, monkeypatch):
    # v0.5 veritabanı: fields tablosunda Ada No yok.
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}", connect_args={'check_same_thread': False})
    with legacy_engine.begin() as conn:
        conn.execute(text('CREATE TABLE fields (id INTEGER PRIMARY KEY, code VARCHAR(40) UNIQUE, name VARCHAR(120), area_decare NUMERIC(12,3))'))
        conn.execute(text("INSERT INTO fields (code, name, area_decare) VALUES ('P-001', 'Eski tarla', 12.5)"))
    monkeypatch.setattr(main, 'engine', legacy_engine)
    sessions = sessionmaker(bind=legacy_engine)
    def get_test_db():
        with sessions() as db:
            yield db
    main.app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(main.app) as client:
            fields = client.get('/api/fields').json()
            assert len(fields) == 1 and fields[0]['ada_no'] is None
            old = fields[0]
            changed = client.put(f"/api/fields/{old['id']}", json={'ada_no':'074', 'code':'P-001', 'name':'Eski tarla', 'area_decare':'12.500'})
            assert changed.status_code == 200 and changed.json()['ada_no'] == '074'
            new = client.post('/api/fields', json={'ada_no':'112', 'code':'P-002', 'name':'Deneme parsel', 'area_decare':'44.25'})
            assert new.status_code == 201
            same_code = client.put(f"/api/fields/{old['id']}", json={'ada_no':'074', 'code':'P-002', 'name':'Eski tarla', 'area_decare':'12.500'})
            assert same_code.status_code == 409
            report = client.post('/api/reports/query',json={'query':'parselleri listele'}).json()
            assert report['columns'][0] == 'Ada No'
            assert any(row[0]=='074' and row[1]=='P-001' for row in report['rows'])
        with legacy_engine.connect() as conn:
            assert 'ada_no' in {row[1] for row in conn.execute(text('PRAGMA table_info(fields)'))}
    finally:
        main.app.dependency_overrides.clear()
        legacy_engine.dispose()
