import os

backend = os.getenv("DB_BACKEND", "lmdb")
print(backend)
if backend == "postgres":
    from .db_postgres import DB, DBError
else:
    from .db_lmdb import DB, DBError
