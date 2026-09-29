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
