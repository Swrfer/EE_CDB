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

### Dockerfile con orden deliberadamente ineficiente

El primer Dockerfile copia todo el proyecto antes de instalar `uv` y las
dependencias. Se descargó previamente la imagen base `python:3.12` para evitar
incluir ese tiempo de descarga en la medición.

| Escenario | Orden malo | Orden bueno |
|---|---:|---:|
| Build desde cero (`--no-cache`) | 28.26 s | Pendiente |
| Rebuild tras cambiar código | 364.73 s | Pendiente |
| Rebuild tras cambiar una dependencia | No medido en esta configuración | Pendiente |

Después de modificar una línea de `src/clinlab/__init__.py`, Docker solo
reutilizó la capa anterior a `COPY`. La copia del proyecto, la instalación de
`uv` y `uv sync` se ejecutaron otra vez.

En el build limpio, `uv sync` tardó 14.0 s. En el rebuild tardó 350.2 s,
mientras que la exportación permaneció prácticamente constante: 9.6 s frente
a 9.5 s. Por tanto, la demora extraordinaria ocurrió durante la reinstalación
de dependencias, afectada también por variabilidad de red, y no durante la
exportación de la imagen.

El resultado demuestra que el orden malo elimina el beneficio de la caché:
incluso un cambio que no modifica dependencias obliga a resolverlas e
instalarlas nuevamente.

## 3. Tamaño de imagen

| Imagen o medida | Uso mostrado en disco | Tamaño reportado por `docker image inspect` |
|---|---:|---:|
| `clinlab:bad-order` con `python:3.12` | 2.12 GB | 530,330,419 bytes |

Docker Desktop distingue el espacio utilizado por las capas descomprimidas en
su almacén local del tamaño de contenido reportado para la imagen. Se
conservarán ambas métricas durante la optimización.

## 4. Contexto de construcción

Pendiente de completar antes y después de crear `.dockerignore`.

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
