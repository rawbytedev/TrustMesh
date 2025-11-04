import os

backend = os.getenv("DB_BACKEND", "lmdb")

if backend == "postgres":
    from .db_postgres import DB, DBError
else:
    from .db_lmdb import DB, DBError
