# Laboratorio 07 — Bitácora del stack clínico

## Entorno de trabajo

| Componente | Resultado |
|---|---|
| Equipo | Mac con Apple Silicon |
| Arquitectura del equipo | `arm64` |
| Arquitectura de Docker | `aarch64` |
| Docker Engine | `29.7.2` |
| Docker Compose | `5.5.1` |
| Sistema de contenedores | Linux |

## 1. Stack mínimo

La primera versión del stack contiene PostgreSQL y Adminer.

| Servicio | Puerto interno | Puerto publicado | Justificación |
|---|---:|---:|---|
| PostgreSQL | 5432 | 5433 | Será necesario para comprobar una conexión desde macOS en la actividad 2. Se eligió 5433 para evitar conflictos con una posible instalación local de PostgreSQL. |
| Adminer | 8080 | 8080 | Es necesario para acceder a su interfaz desde el navegador. |

No fue necesario publicar puertos adicionales. Dentro de la red creada por
Docker Compose, Adminer se comunica con PostgreSQL mediante el nombre del
servicio `postgres` y su puerto interno `5432`.

Los dos servicios se levantaron correctamente:

```text
lab07-clinical-stack-adminer-1
lab07-clinical-stack-postgres-1

## 2. Comunicación entre servicios

Se añadió un servicio Jupyter construido desde `Dockerfile.jupyter`. El
directorio local `notebooks/` se monta en `/workspace/notebooks`, por lo que los
archivos guardados desde Jupyter persisten en el equipo anfitrión.

### Conexión desde Jupyter

Jupyter se conectó utilizando el nombre del servicio de PostgreSQL:

```text
postgresql://clinlab:***@postgres:5432/clinical

## 3. Inicialización de la base de datos

La carpeta `initdb/` se montó como:

```text
/docker-entrypoint-initdb.d

## 5. Healthcheck y orden de arranque

### Comportamiento sin healthcheck

En el experimento de reinicialización de la actividad 3 se ejecutaron consultas
inmediatamente después de `docker compose up -d`. La primera falló porque el
socket de PostgreSQL todavía no existía y la siguiente indicó que la base
`clinical` aún no había sido creada.

Esto demostró que un contenedor con estado `running` no necesariamente tiene su
servicio listo para aceptar conexiones. La evidencia se conserva en
`evidencias/lab07_07_no_healthcheck_startup_race.png`.

### Configuración corregida

Se añadió a PostgreSQL un `healthcheck` basado en:

```bash
pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"

## 6. Configuración externa y protección de secretos

La configuración del stack se almacena localmente en `.env`. Este archivo está
excluido mediante `.gitignore` y no se versiona. En su lugar, el repositorio
incluye `.env.example` con nombres de variables y valores de demostración.

Las variables configuradas son:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_HOST_PORT`
- `ADMINER_PORT`
- `JUPYTER_PORT`
- `JUPYTER_TOKEN`

Las variables críticas utilizan la sintaxis `${VAR:?mensaje}`. Al ejecutar
Compose con `POSTGRES_PASSWORD` vacía, la validación terminó con un código
distinto de cero y explicó que la variable obligatoria no tenía valor. Por
tanto, el stack falla de forma temprana antes de crear contenedores con una
configuración incompleta.

También se comprobó que `.env` está ignorado, que únicamente `.env.example`
puede versionarse y que la contraseña local no aparece en `compose.yml` ni en
`.env.example`.

Los puertos se publican exclusivamente en `127.0.0.1`, de modo que Postgres,
Adminer y Jupyter son accesibles desde la computadora anfitriona, pero no se
exponen directamente a otros equipos de la red local.

La evidencia se conserva en
`evidencias/lab07_13_env_validation.png`.
