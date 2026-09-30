# Laboratorio 07 — Bitácora del stack clínico

## Entorno de trabajo

| Componente | Resultado |
|---|---|
| Equipo | Mac con Apple Silicon |
| Arquitectura del equipo | `arm64` |
| Arquitectura de Docker | `aarch64` |
| Sistema de contenedores | Linux |
| Docker Engine | 29.7.2 |
| Docker Compose | 5.5.1 |
| Rama de trabajo | `lab07-clinical-stack` |

El stack está compuesto por PostgreSQL, JupyterLab y Adminer. PostgreSQL
almacena la información clínica, Jupyter permite ejecutar análisis y Adminer
ofrece una interfaz web opcional para inspeccionar la base.

## 1. Stack mínimo: PostgreSQL y Adminer

### Decisión sobre los puertos

| Servicio | Puerto del host | Puerto del contenedor | Justificación |
|---|---:|---:|---|
| PostgreSQL | 5433 | 5432 | Permite conexiones desde macOS y evita conflictos con una instalación local que utilice 5432. |
| Adminer | 8080 | 8080 | Permite que una persona acceda a la interfaz desde el navegador. |
| JupyterLab | 8888 | 8888 | Permite utilizar los notebooks desde el navegador. |

PostgreSQL necesita publicar el puerto 5433 porque una actividad requiere
conectarse desde la máquina anfitriona. Adminer y Jupyter necesitan puertos
publicados porque son interfaces utilizadas por una persona.

Los contenedores no necesitan publicar puertos para comunicarse entre sí. Esa
comunicación ocurre mediante la red interna de Compose y los nombres de los
servicios.

Adminer se conectó correctamente utilizando:

```text
Sistema: PostgreSQL
Servidor: postgres
Base de datos: clinical
Usuario: clinlab
```

Una consulta ejecutada desde Adminer confirmó la base, el usuario y el puerto
interno de PostgreSQL.

Evidencias:

- `evidencias/lab07_01_adminer_conectado.png`
- `evidencias/lab07_02_adminer_consulta_sql.png`

## 2. Comunicación entre servicios

Jupyter se conectó a PostgreSQL mediante el nombre del servicio definido en
Compose.

La cadena interna, ocultando la contraseña, fue:

```text
postgresql://clinlab:***@postgres:5432/clinical
```

Desde macOS se utilizó:

```text
postgresql://clinlab:***@localhost:5433/clinical
```

La conexión desde el host produjo:

```text
('clinical', 'clinlab', '172.18.0.2/32', 5432)
```

Las cadenas difieren porque `postgres` es un nombre DNS disponible únicamente
dentro de la red de Compose. Desde macOS, el contenedor se alcanza mediante
`localhost` y el puerto publicado 5433. Dentro de la red, PostgreSQL conserva
su puerto normal 5432.

El notebook se almacena en:

```text
notebooks/conexion_postgres.ipynb
```

Evidencias:

- `evidencias/lab07_03_jupyter_conexion_interna.png`
- `evidencias/lab07_04_conexion_desde_macos.png`

## 3. Inicialización de la base

La carpeta `initdb/` contiene dos scripts SQL numerados:

```text
initdb/
├── 01_create_schemas.sql
└── 02_create_tables.sql
```

El primer script crea los esquemas:

- `cdm`
- `results`

El segundo crea las tablas de demostración:

- `cdm.patient_demo`
- `results.analysis_run`
- `results.quality_check`

También inserta el registro inicial `LAB07-P001`.

### Experimento de modificación

Después de la primera inicialización se modificó el segundo script para agregar
`results.quality_check`. Al ejecutar nuevamente:

```bash
docker compose up -d
```

la tabla nueva no apareció.

Esto ocurre porque los scripts de `/docker-entrypoint-initdb.d/` se ejecutan
solamente cuando PostgreSQL inicializa un directorio de datos vacío. No son un
sistema de migraciones y no vuelven a ejecutarse cuando el volumen ya contiene
una base.

Después de ejecutar:

```bash
docker compose down -v
docker compose up -d
```

se creó un volumen nuevo y los scripts se ejecutaron nuevamente. Después de
esperar a que PostgreSQL terminara de inicializarse, la tabla
`results.quality_check` apareció correctamente.

Durante el primer intento se consultó la base inmediatamente después de
`up -d`. La consulta falló porque PostgreSQL aún no estaba listo. Esta salida
se conservó como evidencia del problema de sincronización utilizado después en
la actividad 5.

Evidencias:

- `evidencias/lab07_05_initdb_no_reexecution.png`
- `evidencias/lab07_06_initdb_after_volume_reset.png`
- `evidencias/lab07_07_no_healthcheck_startup_race.png`

## 4. Persistencia y bind mount

Se insertó manualmente un paciente con el código:

```text
LAB07-PERSIST
```

Después se evaluaron los tres escenarios solicitados.

| Comando | ¿Sobrevivieron los datos insertados? | Explicación |
|---|---|---|
| `docker compose restart` | Sí | Los contenedores se reiniciaron, pero el volumen de PostgreSQL permaneció intacto. |
| `docker compose down` seguido de `up` | Sí | Se eliminaron los contenedores y la red, pero el volumen nombrado no se eliminó. |
| `docker compose down -v` seguido de `up` | No | La opción `-v` eliminó el volumen. PostgreSQL creó una base nueva y volvió a ejecutar `initdb/`. |

Después de `down -v`, el registro manual `LAB07-PERSIST` desapareció y regresó
únicamente el registro inicial `LAB07-P001`, generado por los scripts SQL.

### Persistencia de notebooks

La configuración de Jupyter incluye el bind mount:

```yaml
volumes:
  - ./notebooks:/workspace/notebooks
```

Se creó `notebooks/bind_mount_test.txt` desde macOS y el archivo apareció
inmediatamente en `/workspace/notebooks` dentro del contenedor, sin reconstruir
la imagen.

El volumen nombrado de PostgreSQL administra datos internos de la base. El bind
mount de Jupyter comparte directamente una carpeta del repositorio con el
contenedor.

Evidencias:

- `evidencias/lab07_08_persistencia_restart.png`
- `evidencias/lab07_09_persistencia_down_up.png`
- `evidencias/lab07_10_persistencia_down_v_up.png`
- `evidencias/lab07_11_bind_mount.png`

## 5. Healthcheck y orden de arranque

### Comportamiento sin healthcheck

En el experimento de reinicialización de la actividad 3 se ejecutaron consultas
inmediatamente después de `docker compose up -d`. La primera falló porque el
socket de PostgreSQL todavía no existía y la siguiente indicó que la base
`clinical` aún no había sido creada.

Esto demostró que un contenedor con estado `running` no necesariamente tiene su
servicio listo para aceptar conexiones.

### Configuración corregida

Se añadió a PostgreSQL un `healthcheck` basado en:

```bash
pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Jupyter y Adminer esperan mediante:

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

Además, la imagen de Jupyter contiene `check_database.py`, que realiza una
conexión real con `psycopg` antes de iniciar JupyterLab.

### Prueba desde cero

Se eliminó el volumen y se reconstruyó el stack mediante:

```bash
docker compose down -v
docker compose up -d --build --wait --wait-timeout 120
```

`docker compose ps` mostró PostgreSQL con estado `healthy`. Después se ejecutó
el notebook en el primer intento:

```bash
docker compose exec -T jupyter \
  jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace \
  /workspace/notebooks/conexion_postgres.ipynb
```

El comando terminó con código de salida `0` y no se encontraron mensajes
`connection refused` ni `could not connect`.

`depends_on` por sí solo controla el orden de creación de los contenedores, pero
no garantiza que PostgreSQL esté preparado. La condición `service_healthy`
retrasa el inicio de Jupyter hasta que `pg_isready` confirma la disponibilidad
real de la base.

Evidencia:

- `evidencias/lab07_12_healthcheck_healthy.png`

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
tanto, el stack falla antes de crear contenedores con una configuración
incompleta.

También se comprobó que `.env` está ignorado, que únicamente `.env.example`
puede versionarse y que la contraseña local no aparece en `compose.yml` ni en
`.env.example`.

Los puertos se publican exclusivamente en `127.0.0.1`, de modo que PostgreSQL,
Adminer y Jupyter son accesibles desde la computadora anfitriona, pero no se
exponen directamente a otros equipos de la red local.

Evidencia:

- `evidencias/lab07_13_env_validation.png`

## 7. Adminer como servicio opcional

Adminer se colocó detrás del perfil `dev`:

```yaml
profiles:
  - dev
```

Al ejecutar:

```bash
docker compose up -d --wait
```

solamente se iniciaron PostgreSQL y Jupyter. Adminer no apareció en
`docker compose ps` y el puerto 8080 no fue publicado.

Para solicitar explícitamente la interfaz web se utilizó:

```bash
docker compose --profile dev up -d --wait
```

En este segundo caso se iniciaron PostgreSQL, Jupyter y Adminer. La interfaz
quedó disponible mediante `127.0.0.1:8080`.

Este diseño mantiene fuera del stack normal un servicio que sólo se necesita
durante inspección o desarrollo, sin eliminar la posibilidad de activarlo con
un único argumento.

Evidencias:

- `evidencias/lab07_14_profile_without_adminer.png`
- `evidencias/lab07_15_profile_with_adminer.png`

## 8. Depuración intencional: contraseña discordante

Para provocar un fallo controlado se conservó el volumen de PostgreSQL y se
cambió temporalmente `POSTGRES_PASSWORD` únicamente en el archivo local
`.env`. De esta manera, PostgreSQL mantuvo la contraseña con la que había sido
inicializado, mientras que Jupyter recibió una credencial diferente.

Durante el primer intento Jupyter continuó conectándose correctamente porque la
terminal conservaba una versión exportada de `POSTGRES_PASSWORD`. Las variables
del entorno de la shell tienen prioridad sobre los valores de `.env`. Después
de ejecutar `unset POSTGRES_PASSWORD` y recrear el servicio, el fallo apareció
correctamente.

### Paso 1: `docker compose ps`

Se ejecutó:

```bash
docker compose ps -a
```

PostgreSQL permaneció activo y saludable, mientras que Jupyter terminó durante
la comprobación inicial de la conexión. Esto permitió localizar el problema en
Jupyter o en su configuración, en lugar de asumir que toda la base de datos
había fallado.

Evidencia:

- `evidencias/lab07_16_debug_ps.png`

### Paso 2: `docker compose logs jupyter`

Se inspeccionaron los registros mediante:

```bash
docker compose logs --no-color --tail=80 jupyter
```

Los registros mostraron que Jupyter intentó conectarse a PostgreSQL antes de
iniciar el servidor y recibió el siguiente mensaje:

```text
password authentication failed for user "clinlab"
```

El error confirmó que PostgreSQL estaba accesible, pero rechazaba la
autenticación presentada por Jupyter.

Evidencia:

- `evidencias/lab07_17_debug_logs.png`

### Paso 3: `docker compose exec`

Se inspeccionó desde el interior del stack la configuración recibida por el
servicio y se repitió la comprobación de conexión. El contenedor resolvía el
nombre `postgres` y alcanzaba el puerto interno `5432`, pero no podía
autenticarse con la contraseña discordante.

Evidencia:

- `evidencias/lab07_18_debug_exec.png`

### Diagnóstico final

La red de Compose, la resolución del nombre del servicio y PostgreSQL
funcionaban correctamente. El fallo se debía exclusivamente a que Jupyter y la
base utilizaban contraseñas diferentes.

Se restauró el archivo `.env`, se eliminó la variable exportada de la shell y se
recrearon los servicios. PostgreSQL, Jupyter y Adminer regresaron al estado
saludable, y los registros volvieron a mostrar una conexión exitosa.

El experimento confirmó la utilidad del orden de depuración:

```text
ps → logs → exec
```

`ps` permitió identificar el servicio afectado, `logs` mostró el error de
autenticación y `exec` permitió comprobar desde dentro del stack qué
configuración y conectividad veía el contenedor.

## 9. Prueba de reproducibilidad en un clon limpio

Primero se apagó el stack original y se eliminó su volumen:

```bash
docker compose --profile dev down -v
```

Después se creó un clon limpio del repositorio en un directorio temporal
diferente. El clon contenía `.env.example`, pero no el archivo local `.env`.

La preparación y el arranque se realizaron con los pasos documentados:

```bash
cp .env.example .env

docker compose up \
  -d \
  --build \
  --wait \
  --wait-timeout 120
```

PostgreSQL alcanzó el estado `healthy` y Jupyter inició correctamente sin pasos
manuales adicionales. Adminer no se levantó porque pertenece al perfil
opcional `dev`.

La conexión desde el notebook también se verificó dentro del clon:

```bash
docker compose exec \
  -T \
  jupyter \
  jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace \
  /workspace/notebooks/conexion_postgres.ipynb
```

La ejecución terminó con código de salida `0`. El notebook se conectó a
PostgreSQL mediante el nombre del servicio `postgres` y consultó correctamente
la base `clinical`.

Evidencia:

- `evidencias/lab07_19_clean_clone.png`

### Resultado

La prueba confirmó que un clon sin el archivo `.env` original puede levantar el
stack copiando `.env.example`, sin depender del entorno Conda, de paquetes
Python instalados en macOS ni del volumen creado durante experimentos
anteriores.

No se obtuvo una validación adicional de un compañero antes del cierre del
laboratorio. Por tanto, no se declara una confirmación humana externa. La
prueba en un clon limpio y un directorio independiente verifica la
reproducibilidad técnica, pero esta limitación queda documentada explícitamente.

## 10. Comparación con la solución de referencia

La solución de referencia se consultó únicamente después de terminar las
actividades anteriores. Se comparó su archivo `compose.yml` con la
implementación desarrollada en este laboratorio.

### Diferencia 1: tratamiento de variables críticas

La referencia proporciona valores predeterminados para las credenciales:

```yaml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-omop}
```

La implementación propia exige que las variables estén definidas:

```yaml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Define POSTGRES_PASSWORD in .env}
```

**Evaluación:** la implementación propia es mejor para este laboratorio. La
referencia facilita un arranque inmediato, pero puede iniciar
inadvertidamente con credenciales conocidas. La forma `${VAR:?mensaje}`
detiene la creación del stack cuando falta una variable crítica y permite
identificar el problema antes de iniciar los contenedores.

### Diferencia 2: publicación de puertos

La referencia publica los puertos sobre todas las interfaces del equipo y usa
valores fijos:

```yaml
ports:
  - "5432:5432"
```

La implementación propia los restringe a la interfaz local y permite cambiar el
puerto mediante `.env`:

```yaml
ports:
  - "127.0.0.1:${POSTGRES_HOST_PORT:?Define POSTGRES_HOST_PORT in .env}:5432"
```

**Evaluación:** la implementación propia es mejor para un entorno local de
análisis. Restringir la publicación a `127.0.0.1` evita exponer PostgreSQL,
Adminer y Jupyter a otros equipos de la red. El puerto configurable también
reduce conflictos con servicios instalados en la máquina anfitriona.

### Diferencia 3: Adminer y alcance de los bind mounts

En la referencia, Adminer forma parte del arranque normal y Jupyter monta todo
el directorio del proyecto:

```yaml
volumes:
  - ./:/home/jovyan/work
```

En la implementación propia, Adminer utiliza el perfil opcional `dev` y Jupyter
solo monta la carpeta de notebooks:

```yaml
profiles:
  - dev
```

```yaml
volumes:
  - ./notebooks:/workspace/notebooks
```

**Evaluación:** la implementación propia es mejor para reducir la superficie de
ejecución. El stack normal solo inicia PostgreSQL y Jupyter, mientras que
Adminer se solicita explícitamente con `--profile dev`. Además, el contenedor
de Jupyter recibe únicamente los archivos que necesita editar y no todo el
directorio del stack. La referencia resulta más cómoda para explorar todos los
archivos desde Jupyter, pero concede un acceso más amplio del necesario.

### Conclusión

Las dos implementaciones usan un volumen nombrado para PostgreSQL, scripts de
inicialización, un healthcheck real y `depends_on` con
`condition: service_healthy`. Por tanto, su arquitectura básica es
equivalente.

La solución propia añade decisiones más conservadoras para este escenario:
variables críticas obligatorias, puertos limitados a `localhost`, versiones de
imagen fijadas, Adminer opcional y un bind mount limitado a los notebooks.
Estas diferencias priorizan seguridad, reproducibilidad y mínimo acceso sin
cambiar la finalidad del stack.
