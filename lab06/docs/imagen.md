# Laboratorio 06 — Mediciones de la imagen

## Entorno de trabajo

| Componente | Resultado |
|---|---|
| Equipo | Mac con Apple Silicon |
| Arquitectura del equipo | `arm64` |
| Arquitectura del motor Docker | `aarch64` |
| Sistema de contenedores | Linux |
| Docker Engine | `29.7.2` |
| Docker Buildx | `0.36.1-desktop.1` |
| Docker Scout | `1.24.0` |
| uv | `0.12.13` |
| Espacio disponible antes del laboratorio | 289 GiB |
| Uso inicial de imágenes Docker | 33.64 kB |
| Uso inicial de caché de construcción | 0 B |

Los nombres `arm64` y `aarch64` describen la misma arquitectura. La imagen
`hello-world` utilizada durante la verificación fue la variante `arm64v8`, por
lo que la comprobación inicial se ejecutó de manera nativa y sin emulación
`amd64`.

## 1. Dependencias congeladas

El proyecto utiliza `uv` para resolver y congelar sus dependencias en
`uv.lock`. El archivo fue generado con Python 3.12.14 y uv 0.12.13.

```bash
uv lock
uv lock --check
```

La resolución produjo 123 paquetes. Una vez generado el archivo, la
comprobación posterior tardó aproximadamente 4 ms y no modificó el lockfile.

El archivo `pyproject.toml` declara las dependencias directas mediante rangos de
versiones. En cambio, `uv.lock` registra versiones exactas y los artefactos
disponibles para reproducir una instalación compatible en otra máquina.

La reconstrucción fue verificada mediante un entorno aislado:

```bash
uv run --isolated --locked --extra dev python -m pytest -q
```

Se instalaron 37 paquetes y se ejecutaron correctamente 58 pruebas, con una
cobertura de líneas de 95.19%.

### Ejemplos de dependencias transitivas

| Dependencia transitiva | Versión bloqueada | Procedencia |
|---|---:|---|
| `contourpy` | 1.4.0 | Es requerida por la dependencia directa `matplotlib` 3.11.2. |
| `python-dateutil` | 2.9.0.post0 | Es requerida por las dependencias directas `pandas` 3.0.5 y `matplotlib` 3.11.2. |
| `coverage` | 7.16.0 | Es requerida por la dependencia directa de desarrollo `pytest-cov` 7.1.0. |

Estas bibliotecas no aparecen como requisitos directos de `clinlab` en
`pyproject.toml`, pero son necesarias para que sus dependencias directas
funcionen. El lockfile evita que una instalación futura resuelva versiones
diferentes sin que el cambio quede registrado.

## 2. Caché de construcción

### Comparación del orden de las capas

El primer Dockerfile copia todo el proyecto antes de instalar `uv` y las
dependencias. El segundo copia primero `pyproject.toml` y `uv.lock`, instala el
entorno y copia el código después.

Se descargó previamente la imagen base `python:3.12` para no incluir su
descarga en las mediciones.

| Escenario | Orden malo | Orden bueno |
|---|---:|---:|
| Build desde cero (`--no-cache`) | 28.26 s | 27.93 s |
| Rebuild tras cambiar código | 364.73 s | 2.43 s |
| Rebuild tras cambiar una dependencia | 24.76 s | 25.18 s |

En el Dockerfile mal ordenado, modificar una línea de
`src/clinlab/__init__.py` invalidó `COPY . .`. Como consecuencia, tanto la
instalación de `uv` como `uv sync` se ejecutaron nuevamente. En ese rebuild,
`uv sync` tardó 350.2 s debido también a variabilidad de red, mientras que la
exportación permaneció estable en aproximadamente 9.5 s.

En el Dockerfile bien ordenado, las capas que contienen `pyproject.toml`,
`uv.lock`, `uv` y las dependencias quedaron en caché después del mismo cambio
de código. Solo se copiaron nuevamente `src` y `tests`, y se reconstruyó el
paquete local `clinlab`. Esta operación tardó 1.7 s y el build completo terminó
en 2.43 s.

Para evaluar un cambio real de dependencias se añadió temporalmente
`requests>=2.32` y se regeneró `uv.lock`. Ambos órdenes reconstruyeron las
dependencias y tardaron prácticamente lo mismo: 24.76 s y 25.18 s. Esto
confirma que la optimización conserva la caché cuando cambia el código, pero la
invalida correctamente cuando cambia el entorno.

## 3. Tamaño de imagen

| Imagen o medida | Uso mostrado en disco | Tamaño reportado por `docker image inspect` |
|---|---:|---:|
| `clinlab:bad-order` con `python:3.12` | 2.12 GB | 530,330,419 bytes |
| `clinlab:good-order` con `python:3.12` | 2.13 GB | 530,318,669 bytes |

Docker Desktop distingue el espacio utilizado por las capas descomprimidas en
su almacén local del tamaño de contenido reportado para la imagen. El cambio de
orden mejora la caché, pero no reduce de manera relevante el tamaño final.

## 4. Contexto de construcción

Para evitar comparar transferencias incrementales de BuildKit, la medición
definitiva se realizó con dos copias simultáneas del mismo proyecto. La única
diferencia entre ellas fue la presencia de `.dockerignore`.

| Escenario | Contexto enviado | Tiempo |
|---|---:|---:|
| Sin `.dockerignore` | 529.40 kB | 0.34 s |
| Con `.dockerignore` | 523.47 kB | 0.31 s |
| Reducción | 5.93 kB (1.12%) | 0.03 s |

Sin `.dockerignore` se enviaban archivos que no forman parte de la aplicación:

- `.gitignore`
- `docs/imagen.md`
- Dockerfiles experimentales
- el directorio `evidencias/`
- posibles cachés, coberturas y entornos virtuales
- posibles archivos `.env`

La reducción actual es pequeña porque `uv.lock`, con aproximadamente 472 kB,
representa la mayor parte del contexto y es necesario para la instalación
reproducible. El beneficio de `.dockerignore` también es preventivo: evita que
los futuros reportes, evidencias, cachés o secretos incrementen el contexto o
terminen dentro de una capa.

## 5. Ejecución como usuario no-root

Pendiente de completar.

## 6. Demostración de secretos en capas

Pendiente de completar utilizando exclusivamente un valor falso.

## 7. Escaneo de vulnerabilidades

Pendiente de completar con Docker Scout.

## 8. Pruebas dentro del contenedor

Pendiente de completar.

## 9. Publicación

Pendiente de completar con la URL de GitHub Container Registry y la
verificación externa.
