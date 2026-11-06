"""Explicit, ephemeral synthetic authentication demo. Never a production entrypoint."""

import os

for name, value in {
    "DATABASE_HOST": "localhost", "DATABASE_PORT": "5432",
    "DATABASE_NAME": "unused_auth_demo", "DATABASE_USER": "synthetic",
    "DATABASE_PASSWORD": "unused", "AUTH_ASSESSMENT_ENABLED": "true",
}.items():
    os.environ.setdefault(name, value)

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.passwords import hash_password
from app.database.auth_tables import assessment_records, initialize_auth_tables, users
from app.database.db import get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
users.create(engine)
initialize_auth_tables(engine)
factory = sessionmaker(bind=engine)
password_hash = hash_password("SyntheticDemo123!")
with engine.begin() as conn:
    conn.execute(insert(users), [
        {"id": 1, "email": "alice@example.com", "password_hash": password_hash, "is_active": True},
        {"id": 2, "email": "bob@example.com", "password_hash": password_hash, "is_active": True},
    ])
    conn.execute(insert(assessment_records), [
        {"id": 1, "owner_id": 1, "note": "Alice synthetic assessment record"},
        {"id": 2, "owner_id": 2, "note": "Bob synthetic assessment record"},
    ])


def demo_database():
    with factory() as db:
        yield db


settings.AUTH_ASSESSMENT_ENABLED = True
app.title = "Vigor synthetic authentication assessment"
app.state.data_mode = "synthetic_auth_demo"
app.dependency_overrides[get_db] = demo_database
