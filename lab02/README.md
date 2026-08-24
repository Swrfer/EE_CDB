# Laboratorio 02: análisis de pacientes con presupuesto de memoria

Análisis reproducible de datos clínicos sintéticos mediante pandas, Polars
y PySpark. El laboratorio evalúa tipos de datos, consumo de memoria,
procesamiento por bloques, calidad de los datos, uniones, transformación a
formato ancho y comparación de motores de procesamiento.

## 1. Datos

Los datos fueron generados con
[Synthea 4.0.0](https://github.com/synthetichealth/synthea/releases),
utilizando Massachusetts como localización y la semilla `20260822`.

El comando utilizado para generar la población sintética fue:

```bash
java -jar synthea-with-dependencies.jar \
  -s 20260822 \
  -p 20000 \
  Massachusetts
```

Aunque se solicitaron 20,000 pacientes, el archivo final contiene 23,006
registros. Esto se debe al funcionamiento de la simulación y a la inclusión
de pacientes fallecidos generados durante el proceso.

Para este laboratorio se utilizaron los siguientes archivos:

| Archivo | Registros | Tamaño aproximado |
|---|---:|---:|
| `patients.csv` | 23,006 | 6.6 MB |
| `encounters.csv` | 1,399,646 | 443 MB |
| `observations.csv` | 17,677,231 | 2.9 GB |

Los archivos deben colocarse dentro de la siguiente carpeta:

```text
lab02/data/synthea_20000/csv/
├── patients.csv
├── encounters.csv
└── observations.csv
```

Los archivos CSV no se incluyen en el repositorio debido a su tamaño.

## 2. Estructura del laboratorio

```text
lab02/
├── analisis_pacientes.ipynb
├── README.md
├── actividad7_chunks.py
├── actividad7_streaming.py
├── data/
│   └── synthea_20000/
│       └── csv/
│           ├── patients.csv
│           ├── encounters.csv
│           └── observations.csv
└── results/
    ├── actividad7_metricas_streaming.json
    ├── actividad7_resultados_streaming.csv
    ├── actividad8_pandas.csv
    ├── actividad8_polars.csv
    ├── actividad8_pyspark.csv
    └── actividad8_comparacion_motores.csv
```

## 3. Equipo utilizado

El análisis se realizó localmente en una MacBook Pro con las siguientes
características:

- Chip Apple M4 Pro.
- 24 GB de memoria RAM.
- GPU de 16 núcleos.
- 500 GB de almacenamiento.
- macOS.
- OpenJDK 17.

## 4. Entorno de ejecución

El laboratorio se desarrolló con un entorno Conda llamado `cdb` y las
siguientes versiones principales:

- Python 3.12.14
- pandas 2.3.3
- NumPy 2.5.2
- PyArrow 25.0.0
- Polars 1.43.2
- PySpark 4.2.0
- OpenJDK 17
- JupyterLab 4.5.9

### Creación del entorno

Los siguientes comandos son instrucciones de reproducibilidad. No es
necesario ejecutarlos si el entorno `cdb` ya existe.

Para crear el entorno desde cero:

```bash
conda create -n cdb -c conda-forge \
  python=3.12 \
  pandas \
  numpy \
  pyarrow \
  polars \
  pyspark \
  psutil \
  matplotlib \
  seaborn \
  jupyterlab \
  ipykernel
```

Para activar el entorno:

```bash
conda activate cdb
```

Para registrarlo como kernel de Jupyter:

```bash
python -m ipykernel install \
  --user \
  --name cdb \
  --display-name "Python (cdb)"
```

Estos comandos deben ejecutarse en la Terminal, no dentro del notebook.

## 5. Reproducción del análisis

Una vez instalado el entorno y colocados los datos en la ruta indicada,
el análisis puede reproducirse con los siguientes pasos.

En la Terminal:

```bash
conda activate cdb
cd ~/EE_CDB/lab02
jupyter lab
```

Después:

1. Abrir `analisis_pacientes.ipynb`.
2. Seleccionar el kernel asociado al entorno `cdb`.
3. Confirmar que el intérprete corresponde a:

```text
/opt/anaconda3/envs/cdb/bin/python
```

4. Ejecutar las celdas del notebook en orden.
5. No ejecutar varias implementaciones pesadas simultáneamente.
6. Esperar a que cada proceso termine antes de iniciar el siguiente.

Las actividades de comparación ejecutan pandas, Polars y PySpark en procesos
independientes. Esto permite medir la memoria de cada motor por separado y
liberarla cuando termina la ejecución.

## 6. Resultados de optimización de memoria

La asignación explícita de tipos redujo el consumo de memoria de
`patients.csv` de 26.965 a 5.751 MiB, equivalente a una reducción de
78.672 %.

Para `encounters.csv`, la memoria disminuyó de 1,079.623 a 376.658 MiB,
equivalente a una reducción de 65.112 %.

Para `observations.csv`, la memoria ingenua estimada fue de 10,158.207 MiB
y la memoria optimizada fue de 2,002.195 MiB, equivalente a una reducción
de 80.290 %.

| Archivo | Memoria ingenua (MiB) | Memoria optimizada (MiB) | Reducción |
|---|---:|---:|---:|
| `patients.csv` | 26.965 | 5.751 | 78.672 % |
| `encounters.csv` | 1,079.623 | 376.658 | 65.112 % |
| `observations.csv` | 10,158.207 | 2,002.195 | 80.290 % |

## 7. Procesamiento con presupuesto de memoria

El archivo `observations.csv` se procesó mediante lectura secuencial con
`csv.reader`.

Este método procesó las 17,677,231 filas sin cargar el archivo completo en
memoria y produjo los siguientes resultados:

| Métrica | Resultado |
|---|---:|
| Filas procesadas | 17,677,231 |
| Tiempo | 29.223 s |
| Memoria inicial | 23.781 MiB |
| Memoria pico | 24.047 MiB |
| Incremento de memoria | 0.266 MiB |
| Presupuesto establecido | 200 MiB |
| Cumplimiento del presupuesto | Sí |

Los conteos, sumas y medias se validaron contra los resultados obtenidos con
pandas por bloques. Ambos métodos produjeron resultados equivalentes.

## 8. Comparación de pandas, Polars y PySpark

Los tres motores ejecutaron el mismo pipeline:

1. Lectura de las columnas `CODE` y `VALUE`.
2. Conversión de `VALUE` a formato numérico cuando fue posible.
3. Agrupación por código clínico.
4. Cálculo del número total de observaciones.
5. Cálculo del número de valores numéricos.
6. Cálculo de suma y media por código.

Los tres motores procesaron 17,677,231 filas, identificaron 295 códigos y
produjeron resultados equivalentes.

| Motor | Filas | Códigos | Tiempo pipeline (s) | Tiempo total (s) | Memoria pico (MiB) | Aceleración vs. pandas |
|---|---:|---:|---:|---:|---:|---:|
| pandas | 17,677,231 | 295 | 15.248 | 16.037 | 338.219 | 1.000 |
| Polars | 17,677,231 | 295 | 1.980 | 2.231 | 3,072.812 | 7.188 |
| PySpark | 17,677,231 | 295 | 9.806 | 18.778 | 911.875 | 0.854 |

En 81 códigos no existían valores convertibles a número. pandas representó
la suma vacía como `0`, mientras que PySpark la representó como `NULL`. Esta
diferencia se normalizó antes de la validación y no modificó los conteos ni
las medias.

## 9. Recomendación

Para este volumen concreto de datos utilizaría **Polars** cuando el objetivo
principal fuera ejecutar transformaciones y agregaciones repetidas con la
mayor rapidez posible. Sobre el archivo de 2.9 GB, Polars completó la
ejecución total en 2.231 segundos, aproximadamente 7.2 veces más rápido que
pandas. En una computadora con 24 GB de RAM, su pico de 3,072.812 MiB
continúa siendo manejable.

La elección, sin embargo, depende de las restricciones del proyecto. Si
priorizara la facilidad de uso, la compatibilidad con el ecosistema
científico de Python y un consumo de memoria más moderado, utilizaría
**pandas**. En este análisis alcanzó un pico de 338.219 MiB y produjo los
mismos resultados, aunque tardó 16.037 segundos.

Si existiera un presupuesto rígido inferior a 200 MiB, no utilizaría ninguno
de los tres pipelines tal como fueron evaluados. En ese escenario elegiría
la lectura secuencial con `csv.reader`, que procesó el archivo completo con
un pico de solamente 24.047 MiB, a cambio de un mayor tiempo de ejecución.

Cambiaría a **PySpark** cuando los datos o las transformaciones dejaran de
caber de forma segura en una sola computadora o cuando fuera necesario
distribuir el procesamiento entre varios nodos. Como regla operativa,
reconsideraría la solución local cuando el pico de memoria esperado superara
entre 50 % y 60 % de la RAM disponible, aproximadamente 12–14 GB en el equipo
utilizado.

PySpark no proporcionó una ventaja para el archivo actual. Aunque su pipeline
tardó 9.806 segundos, el tiempo total aumentó a 18.778 segundos por el costo
de iniciar Java y la sesión de Spark. Su principal ventaja aparecería con
volúmenes considerablemente mayores, múltiples archivos o infraestructura
distribuida.

Por tanto, para este laboratorio recomendaría Polars cuando se priorice la
velocidad, pandas cuando se busque un equilibrio entre facilidad de uso y
memoria, `csv.reader` ante límites estrictos de memoria y PySpark cuando sea
necesario escalar el procesamiento fuera de una sola computadora.

## 10. Reproducibilidad y buenas prácticas

Para mejorar la reproducibilidad del análisis se aplicaron las siguientes
medidas:

- Uso de la semilla `20260822` para generar los datos.
- Registro de la versión de Synthea.
- Registro de las versiones de Python y sus dependencias.
- Construcción de rutas mediante `pathlib`.
- Definición explícita de tipos de datos.
- Validación de cardinalidad en las uniones.
- Procesamiento por bloques o streaming de archivos grandes.
- Ejecución independiente de los motores comparados.
- Validación de los resultados entre pandas, Polars y PySpark.
- Medición de tiempo y memoria.
- Conservación de resultados pequeños en la carpeta `results/`.
- Exclusión de los archivos clínicos grandes del repositorio.

Los datos son completamente sintéticos y no contienen información
identificable de pacientes reales.

## 11. Archivos que no deben subirse al repositorio

Debido a su tamaño, no deben subirse a GitHub:

```text
data/
*.jar
.ipynb_checkpoints/
__pycache__/
.DS_Store
```

Estas rutas pueden incluirse posteriormente en un archivo `.gitignore`.

## 12. Entregables

El laboratorio se entrega mediante:

- `analisis_pacientes.ipynb`, con código, resultados y narrativa Markdown.
- `README.md`, con el origen de los datos y las instrucciones de reproducción.
- Tabla comparativa de pandas, Polars y PySpark dentro del notebook y del
  README.
- Resultados pequeños generados durante las actividades dentro de `results/`.

El notebook debe leerse como un documento analítico y no solamente como una
colección de celdas de código.
