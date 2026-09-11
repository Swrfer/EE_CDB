# clinlab

Paquete de Python para validar y resumir datos clínicos derivados del laboratorio 2.

## Instalación para desarrollo

```bash
pip install -e ".[dev]"
```

## Cobertura y limitaciones de las pruebas

La suite contiene 58 pruebas y alcanza 95.19% de cobertura de líneas.
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

## Notebook del laboratorio 5

Instalar las herramientas de notebook en el mismo entorno del paquete:

```bash
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --user --name cdb --display-name "Python (cdb)"
python -m jupyterlab
```

Abrir `notebooks/analisis_pacientes.ipynb`, seleccionar **Python (cdb)** y
reiniciar el kernel antes de ejecutar todas las celdas.
Por defecto se buscan los CSV en
`~/EE_CDB/lab02/data/synthea_20000/csv`. Se puede cambiar `DATA_DIR` en la
primera celda o definir `CLINLAB_DATA_DIR` antes de iniciar Jupyter.
No se suben CSV al repositorio.

La primera ejecución limita la auditoría temporal y las observaciones a dos
bloques (`MAX_CHUNKS = 2`, `CHUNKSIZE = 50_000`). La tabla mínima de llaves de
encuentros se carga completa para no crear falsos registros huérfanos.
El prefijo no es una muestra representativa. Para analizar la cohorte completa,
cambiar `MAX_CHUNKS = None`, reiniciar el kernel y ejecutar todo.
El tamaño por bloque no garantiza un límite de memoria total de 200 MiB.

El notebook conserva el núcleo de auditoría, uniones y resumen de HbA1c del
lab 2. Los benchmarks y el formato ancho quedan en el notebook original del
lab 2 y en el historial Git. Las observaciones cualitativas y los eventos
administrativos post mortem no se eliminan automáticamente.

La validación temporal utiliza días de calendario UTC e interpreta las fechas
sin zona como UTC, acorde con la auditoría original de Synthea.
Referencia técnica: https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html

Verificaciones de esta actualización: 58 pruebas aprobadas, cobertura 95.19%,
Ruff y mypy aprobados. Notebook validado estructuralmente y ejecutado por celdas
con CSV sintéticos pequeños; falta ejecutarlo localmente con los CSV completos.
