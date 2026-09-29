import os

import psycopg


database_url = os.environ["DATABASE_URL"]

print("Comprobando conexión con PostgreSQL...", flush=True)

with psycopg.connect(
    database_url,
    connect_timeout=5,
) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user;")
        database, user = cursor.fetchone()

print(
    f"Conexión con PostgreSQL lista: database={database}, user={user}",
    flush=True,
)
