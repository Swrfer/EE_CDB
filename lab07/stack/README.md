# Stack clínico con Docker Compose

Entorno reproducible de análisis clínico compuesto por:

- PostgreSQL 17 para almacenamiento de datos.
- JupyterLab para análisis desde notebooks.
- Adminer como cliente web opcional.
- Scripts SQL para inicializar los esquemas `cdm` y `results`.

## Requisitos

- Docker Desktop
- Docker Compose

Comprueba que Docker esté activo:

```bash
docker info
docker compose version
```

## Levantar el stack en tres líneas

Desde la raíz del repositorio:

```bash
cd lab07/stack
cp .env.example .env
docker compose up -d --build --wait
```

Una vez iniciado:

- JupyterLab: <http://localhost:8888>
- PostgreSQL desde el host: `localhost:5433`
- PostgreSQL desde los contenedores: `postgres:5432`

El token de Jupyter y las credenciales iniciales se encuentran en el archivo
local `.env` creado a partir de `.env.example`.

## Levantar Adminer

Adminer pertenece al perfil opcional `dev`:

```bash
docker compose --profile dev up -d --build --wait
```

Después abre:

<http://localhost:8080>

Utiliza los siguientes campos:

```text
Sistema: PostgreSQL
Servidor: postgres
Usuario: valor de POSTGRES_USER en .env
Contraseña: valor de POSTGRES_PASSWORD en .env
Base de datos: valor de POSTGRES_DB en .env
```

## Comprobar el estado

```bash
docker compose ps
```

PostgreSQL debe aparecer con estado `healthy`. Jupyter no comienza hasta que la
base supera su healthcheck y una conexión real mediante `psycopg`.

## Ejecutar el notebook de conexión

```bash
docker compose exec -T jupyter \
  jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace \
  /workspace/notebooks/conexion_postgres.ipynb
```

## Detener el stack

Detener y eliminar contenedores, conservando los datos:

```bash
docker compose --profile dev down
```

Eliminar también el volumen de PostgreSQL:

```bash
docker compose --profile dev down -v
```

La segunda operación borra los datos almacenados y hace que los scripts de
`initdb/` vuelvan a ejecutarse durante el siguiente arranque.

## Estructura

```text
stack/
├── compose.yml
├── Dockerfile.jupyter
├── .env.example
├── .gitignore
├── README.md
├── bitacora.md
├── initdb/
│   ├── 01_create_schemas.sql
│   └── 02_create_tables.sql
├── jupyter/
│   └── check_database.py
├── notebooks/
│   ├── conexion_postgres.ipynb
│   └── bind_mount_test.txt
└── evidencias/
```

## Configuración y secretos

`.env` contiene la configuración local y está excluido del repositorio.
`.env.example` se versiona porque sólo contiene valores de demostración.

`compose.yml` utiliza `${VAR:?mensaje}` para impedir que el stack arranque si
falta una variable crítica. Los puertos se publican únicamente en
`127.0.0.1`.

## Evidencia de los experimentos

Los resultados de persistencia, inicialización, healthchecks, perfiles y
depuración se encuentran en [`bitacora.md`](bitacora.md).
