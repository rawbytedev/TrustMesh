import os

backend = os.getenv("DB_BACKEND", "lmdb")
if backend == "postgrestest":
    from .db_postgres_test import DB, DBError
if backend == "postgres":
    from .db_postgres import DB, DBError
else:
    from .db_lmdb import DB, DBError
