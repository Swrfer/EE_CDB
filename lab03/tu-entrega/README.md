# Laboratorio 03 — EDA de una cohorte con diabetes tipo 2

## Objetivo

Realizar un análisis exploratorio de una cohorte sintética de pacientes con diabetes
mellitus tipo 2 y presentar los resultados mediante figuras y una tabla de
características basales interpretables para un público clínico.

## Datos

Los datos proceden de la población de Synthea 4.0.0 generada durante el
Laboratorio 02 con la semilla `20260822`.

Los archivos originales no se incluyen en GitHub debido a su tamaño. El
notebook utiliza localmente:

- `patients.csv`;
- `encounters.csv`;
- `observations.csv`.

La cohorte se definió mediante los códigos registrados como motivo de
encuentro:

- `44054006`: diabetes mellitus tipo 2;
- `368581000119106`: neuropatía debida a diabetes mellitus tipo 2.

La cohorte final contiene 500 pacientes.

## Entorno

El análisis se ejecutó con el entorno Conda `cdb` y las bibliotecas:

- pandas;
- NumPy;
- Matplotlib;
- Seaborn;
- Plotly;
- Pillow;
- Kaleido;
- JupyterLab.

## Contenido

- `eda_cohorte.ipynb`: análisis exploratorio completo.
- `figuras/figura_multipanel_cohorte_diabetes.pdf`: figura vectorial.
- `figuras/figura_multipanel_cohorte_diabetes.png`: figura a 300 dpi.
- `figuras/comparacion_matplotlib_seaborn_plotly.png`: comparación visual.
- `figuras/distribucion_edad_plotly.html`: figura interactiva.
- `resultados/tabla1_caracteristicas_basales.csv`: Tabla 1.

## Análisis realizados

1. Definición y validación de la cohorte.
2. Distribución de edad por sexo.
3. Evolución temporal de HbA1c.
4. Comorbilidades basales frecuentes.
5. Identificación gráfica de problemas de calidad.
6. Figura multipanel 2×2.
7. Comparación entre Matplotlib, Seaborn y Plotly.
8. Construcción de la Tabla 1.
9. Exportación en PDF vectorial y PNG a 300 dpi.

## Hallazgos principales

1. Las mujeres presentaron una edad ligeramente mayor al primer registro:
   mediana de 54 años frente a 51 años en hombres.
2. La mediana de HbA1c alcanzó 7.1 % durante el año anterior al primer
   registro y disminuyó durante el seguimiento.
3. La gingivitis fue la comorbilidad basal registrada con mayor frecuencia,
   con una prevalencia de 56.2 %.

## Limitaciones

La cohorte y sus comorbilidades se definieron mediante los motivos registrados
en los encuentros, ya que la cohorte original no contenía `conditions.csv`.
Los datos son sintéticos y mostraron patrones de medición propios de una
simulación. Los resultados no representan evidencia obtenida de pacientes
reales.

## Reproducción

Desde la raíz del repositorio:

```bash
conda activate cdb
cd lab03/tu-entrega
jupyter lab
