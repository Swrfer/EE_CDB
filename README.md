# clinlab

Paquete de Python para validar y resumir datos clínicos derivados del laboratorio 2.

## Instalación para desarrollo

```bash
pip install -e ".[dev]"

## Cobertura y limitaciones de las pruebas

La suite contiene 56 pruebas y alcanza 95.19% de cobertura de líneas.
`pytest` muestra las líneas pendientes y exige un mínimo de 80%.

- En `joins.py` faltan pruebas para la ausencia de las columnas identificadoras y para la selección de todas las columnas mediante `patient_columns=None`.
- En `validation.py` faltan pruebas de los errores por columnas requeridas ausentes en encuentros y pacientes.
- Estas omisiones dejan comportamientos públicos sin verificar; se documentan como limitación, aunque se supera el umbral solicitado. La cobertura de líneas no garantiza que todas las combinaciones de datos estén probadas.

## Controles antes de cada commit

Con el entorno de desarrollo activado, ejecutar en cada clon:

```bash
python -m pip install -e ".[dev]"
pre-commit install
pre-commit run --all-files
```

Los hooks locales utilizan Python, Ruff y mypy del entorno activo.
Revisan el código con Ruff, comprueban su formato y ejecutan mypy
sobre `src/`. Si algún control falla, el commit se rechaza.

Para corregir el formato:

```bash
ruff format src/ tests/
```

Después de corregir los archivos, hay que volver a agregarlos con
`git add` y repetir el commit.
