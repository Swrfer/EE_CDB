# Laboratorio 06 — Containerización de clinlab

[![Lab 06 Container Image](https://github.com/Swrfer/EE_CDB/actions/workflows/lab06-image.yml/badge.svg)](https://github.com/Swrfer/EE_CDB/actions/workflows/lab06-image.yml)

Esta carpeta contiene la versión reproducible y containerizada del paquete
`clinlab`, desarrollado inicialmente en el laboratorio 05.

## Imagen publicada

La imagen está disponible públicamente en GitHub Container Registry:

```text
ghcr.io/swrfer/clinlab:0.1.0
```

Para descargarla y ejecutar las pruebas no es necesario instalar Python,
Conda ni las dependencias del proyecto:

```bash
docker pull ghcr.io/swrfer/clinlab:0.1.0

docker run --rm \
  ghcr.io/swrfer/clinlab:0.1.0 \
  pytest -q
```

También está disponible mediante el SHA completo del commit de publicación:

```text
ghcr.io/swrfer/clinlab:5f20b0e7d9aa5cc5622d8b47313772312e808bed
```

Ambas etiquetas apuntan al índice OCI:

```text
sha256:db7db1dd67039b537dc369aa2b8b72dd151e09d35704884d3ddb7dee283bd999
```

La imagen incluye manifiestos para:

- `linux/amd64`
- `linux/arm64`

## Dependencias reproducibles

`pyproject.toml` declara las dependencias directas y `uv.lock` registra las
versiones resueltas de las dependencias directas y transitivas.

Para comprobar el lockfile y reconstruir el entorno:

```bash
uv lock --check

uv run \
  --isolated \
  --locked \
  --extra dev \
  python -m pytest -q
```

La reconstrucción aislada ejecutó 58 pruebas con 95.19% de cobertura.

## Construcción local

Para construir la imagen definitiva:

```bash
docker build \
  -f Dockerfile \
  -t clinlab:final \
  .
```

Para ejecutar las pruebas:

```bash
docker run --rm \
  clinlab:final \
  pytest -q
```

Para verificar que no se ejecuta como root:

```bash
docker run --rm \
  clinlab:final \
  id
```

La identidad esperada es:

```text
uid=10001(clinlab) gid=10001(clinlab) groups=10001(clinlab)
```

## Características de la imagen final

| Característica | Resultado |
|---|---:|
| Base | `python:3.12-slim` |
| Construcción | Multi-stage |
| Tamaño local | 132.51 MB |
| Usuario | `10001:10001` |
| Pruebas | 58 aprobadas |
| Cobertura | 95.19% |
| Plataformas publicadas | AMD64 y ARM64 |
| Vulnerabilidades críticas encontradas | 3 |
| Vulnerabilidades altas encontradas | 53 |

La imagen utiliza `.dockerignore`, no incorpora archivos `.env` y separa la
etapa de construcción de la etapa de ejecución.

## Publicación automática

El workflow `.github/workflows/lab06-image.yml` construye y prueba la imagen en
los pull requests. Después de un push a `main`, publica automáticamente en GHCR
las etiquetas de versión y SHA.

La publicación incluye procedencia, SBOM y manifiestos para AMD64 y ARM64.

## Archivos principales

```text
lab06/
├── Dockerfile
├── Dockerfile.alpine
├── Dockerfile.bad-order
├── Dockerfile.good-order
├── Dockerfile.multistage
├── Dockerfile.slim-base
├── Dockerfile.slim-no-cache
├── .dockerignore
├── pyproject.toml
├── uv.lock
├── src/
├── tests/
└── docs/
    └── imagen.md
```

## Mediciones y evidencia

Los tiempos de construcción, tamaños, contexto, experimento con Alpine,
demostración de secretos, escaneo de vulnerabilidades y pruebas se documentan
en [`docs/imagen.md`](docs/imagen.md).

La imagen pública fue comprobada localmente en Apple Silicon ARM64. El workflow
también la construyó y probó en un runner Linux AMD64 de GitHub Actions. No se
obtuvo una confirmación adicional de un compañero antes del cierre del
laboratorio; esta limitación queda declarada explícitamente.
