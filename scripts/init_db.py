"""Create database tables against DATABASE_URL. Run once before first app start.

Run with: python -m scripts.init_db

Schema creation is intentionally not a side effect of importing/starting the app —
that would race across multiple app instances and hide connectivity issues behind an
import error. A real deployment would use Alembic migrations instead of create_all;
this is the minimal equivalent for local/dev setup.
"""
from app.database import Base, engine
from app import models  # noqa: F401  (ensures models are registered on Base.metadata)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Tables created (or already present).")


if __name__ == "__main__":
    init_db()
