# Laboratorio 06 — Containerización de clinlab

Esta carpeta contiene la adaptación reproducible y containerizada del paquete
`clinlab`, desarrollado inicialmente en el laboratorio 05.

## Objetivo

Construir una imagen ligera, reproducible y sin secretos que permita ejecutar
la suite de pruebas de `clinlab` sin instalar manualmente Python ni sus
dependencias.

## Dependencias reproducibles

El proyecto utiliza `uv.lock` para registrar las versiones resueltas de las
dependencias directas y transitivas.

Para comprobar el lockfile:

```bash
uv lock --check

```

Para crear un entorno de desarrollo y ejecutar las pruebas:

```bash
uv sync --locked --extra dev
uv run --locked --extra dev pytest
```

La reconstrucción aislada del entorno fue comprobada con:

```bash
uv run --isolated --locked --extra dev python -m pytest -q
```

El resultado fue de 58 pruebas aprobadas y 95.19% de cobertura.

Las mediciones de construcción, tamaño, contexto y vulnerabilidades se
documentan en [`docs/imagen.md`](docs/imagen.md).

Los archivos Docker y el workflow de publicación se incorporarán durante las
siguientes actividades del laboratorio.
