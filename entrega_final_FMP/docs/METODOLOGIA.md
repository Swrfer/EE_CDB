# Metodología

## Diseño y desenlace

Se comparan firmas moleculares pronósticas LASSO-Cox y Random Survival Forest
(RSF) para supervivencia global en cáncer gástrico. Se desarrollan con TCGA-STAD
y se aplican a ACRG (GSE62254) sin ajustar los modelos con sus desenlaces.
La evaluación externa principal es global; I–II es un subanálisis exploratorio.
La expresión génica es la entrada predictora. Edad, sexo y estadio no se incorporan
como predictores de estas firmas.

La lista inicial de 216 candidatos es fija y procede de un análisis diferencial
previo de cáncer I–II frente a tejido gástrico control. El entrenamiento actual
no se restringe a I–II: utiliza la cohorte TCGA elegible completa.

## 1. Adquisición

- TCGA-STAD: `TCGAbiolinks::GDCquery`, `GDCdownload` y `GDCprepare`, con datos de
  expresión `Gene Expression Quantification`, flujo `STAR - Counts` y acceso
  abierto. Se selecciona explícitamente el ensayo `unstranded`.
- Clínica TCGA: `GDCquery_clinic(project = "TCGA-STAD", type = "clinical")`.
- ACRG: descarga HTTPS de `GSE62254_series_matrix.txt.gz`, plataforma GPL570.
  Se comprueban compresión, identificación y fin de tabla. GEOquery lee el
  archivo local con `getGPL = FALSE` y `AnnotGPL = FALSE`.
- Clínica ACRG: CSV o suplemento Excel local proporcionado por separado.

La adquisición conserva consultas, archivos y huellas de procedencia. Los RDS
válidos existentes se reutilizan. No se reciben como entradas modelos ajustados
ni objetos de una sesión manual.

## 2. Estandarización clínica

### TCGA

La expresión se alinea con la clínica por identificador de paciente. Se conservan
muestras de tumor primario, código 01 del barcode TCGA, y el orden de muestras
y genes del procedimiento. Se advierte si hay muestras repetidas por paciente.

- Tiempo: `days_to_death` cuando está disponible; de lo contrario,
  `days_to_last_follow_up`.
- Evento: `Dead = 1`, `Alive = 0`. Los registros sin estado o seguimiento
  válido no se incluyen en el análisis de supervivencia.
- Conversión: días divididos entre 365.
- Estadio: homologación a I, II, III o IV; desconocido permanece sin clasificar.
  El estadio desconocido no excluye de la evaluación global.
- Sexo: se admite información de `gender`, `sex_at_birth` o `sex`.

La exclusión de tiempos no positivos se conserva después de VST. Cambiar ese
orden modificaría las muestras que contribuyen al preprocesamiento.

### ACRG

Se vincula el identificador numérico de la información GEO con `Tumor ID` o
`patient_id`. Se conserva la codificación clínica del suplemento:

| Campo | Regla |
|---|---|
| `FU status` 0/1 | Censura |
| `FU status` 2/3/4 | Muerte |
| `FU status` 5 o estado no clasificable | Excluido de supervivencia |
| `OS_event` alternativo | 0 = censura; 1 = muerte |
| Tiempo | Meses × 30.44 / 365 |
| `pStage` o `stage` | Homologación a I–IV |

La conversión de meses reproduce la definición temporal del análisis. No se
sustituye por meses/12 durante la evaluación. El seguimiento es el documentado
por cada fuente; no se reconstruye una fecha prospectiva de disponibilidad de
la expresión respecto del inicio del seguimiento.

## 3. Preparación de la expresión

### TCGA: conteos a VST

1. Comprobar que los conteos sean numéricos, no negativos y estén identificados
   por gen Ensembl y muestra.
2. Conservar genes con al menos 10 conteos en al menos el 20% de los tumores
   alineados.
3. Crear un `DESeqDataSet` con `design = ~1`, estimar factores de tamaño y
   aplicar `vst(blind = TRUE)`.
4. Retirar la versión de los identificadores Ensembl y anotar con `org.Hs.eg.db`.
   Conservar la primera fila por símbolo después de VST, sin sumar conteos
   por símbolo antes de transformar.
5. Recuperar los candidatos elegibles entre los 216 genes de referencia.
6. Conservar registros con seguimiento positivo y construir la matriz
   paciente × gen alineada con la clínica.

La cobertura, filtros y dimensiones se registran en tablas. La selección TCGA
no se condiciona a la presencia de genes en ACRG.

### ACRG: señal de microarreglo procesada

Los metadatos de GSE62254 describen la entrada como señal RMA transformada en
log10. Se mantiene el siguiente procesamiento:

1. Normalización adicional por cuantiles con `limma`.
2. Transformación `log2(x + 1)` únicamente si el máximo de la matriz supera 50.
   El indicador de aplicación se registra; la señal RMA log10 no se convierte
   automáticamente a log2.
3. Anotación de sondas mediante `hgu133plus2.db` y media de sondas por símbolo.
4. Alineación con la clínica y evaluación de cobertura de cada firma.

La normalización por cuantiles homogeneiza distribuciones dentro de ACRG.
Repetirla sobre una matriz ya procesada se conserva como parte del método;
no demuestra que sea la estrategia de transporte óptima.

### Normalización y transporte

VST atenúa la dependencia media–varianza de conteos, pero no produce unidades
equivalentes a la señal RMA log10. La normalización por cuantiles de ACRG tampoco
armoniza directamente ambas plataformas.

En LASSO se aplica `scale()` al puntaje completo de ACRG. Es una transformación
del marcador calculado con la cohorte, no un Z-score de cada gen. No corrige las
contribuciones relativas de genes cuyas escalas difieren entre tecnologías.
El bosque RSF conserva los puntos de división aprendidos con TCGA, de modo que
valores externos fuera de esos rangos pueden producir predicciones poco variables.

No se aplica normalización por controles no tumorales, Z-score por gen, ComBat
ni transformación a rangos. Los controles no son un requisito para ajustar una
firma pronóstica entre pacientes con cáncer; una referencia no tumoral sería
otra estrategia de armonización que requeriría diseño y evaluación propios.

## 4. LASSO-Cox

| Parámetro | Definición |
|---|---|
| Función | `glmnet::cv.glmnet` |
| Familia | `cox` |
| Penalización | `alpha = 1` |
| Estandarización interna | `standardize = TRUE` |
| Validación cruzada | 10 folds |
| Semilla | 123 |
| Criterio | `type.measure = "deviance"` |
| Lambda seleccionado | `lambda.min` |
| Conservación de predicciones/folds CV | `keep = TRUE` |

Se retienen los coeficientes distintos de cero en `lambda.min`. El puntaje es
la suma de expresión por coeficiente penalizado; mayor puntaje indica peor
pronóstico. La referencia de ocho genes se usa para verificar la reconstrucción
con tolerancia absoluta `1e-6`. La discordancia no se resuelve reemplazando
coeficientes por los del CSV.

Los HR del forest por gen se obtienen de modelos Cox univariados. Son análisis
de asociación y no equivalen a los coeficientes penalizados. La selección conjunta
de un gen no requiere que su asociación univariada tenga p < 0.05.
`keep = TRUE` no convierte las evaluaciones posteriores del modelo final en OOF.

## 5. Random Survival Forest

Se utilizan la misma matriz TCGA elegible, clínica y asignación de folds que
LASSO. Dentro de cada fold, un bosque de selección ordena los genes por
importancia de permutación utilizando únicamente sus pacientes de entrenamiento.
Se evalúan seis combinaciones: paneles de 5, 10 o 20 genes y
`min.node.size` de 10 o 20.

Se elige el mayor C de Harrell medio de validación; en empate, el panel de menos
genes y después el nodo mayor. Se repite la selección de genes en toda TCGA y
se ajusta el bosque final con la configuración elegida.

| Parámetro | Definición |
|---|---|
| Motor | `ranger` |
| Árboles | 1000 |
| `mtry` | `max(1, floor(sqrt(p)))` en cada bosque |
| Nodo del bosque de selección | 15 |
| Nodo del bosque final | Configuración seleccionada: 10 o 20 |
| `min.bucket` | 3 |
| Regla de división | `logrank` |
| Importancia | `permutation` para selección y bosque final |
| Muestreo | Con reemplazo; `sample.fraction = 1` |
| Hilos | 2 |
| Semilla base | 20261118 |
| Semillas finales de selección y ajuste | 20271118 y 20271119 |

Las semillas son parámetros numéricos; no indican la fecha de ejecución.
El detalle de CV y los parámetros efectivos se exportan. La media y desviación
entre folds no se interpretan como un intervalo de confianza ni como evaluación
independiente del procedimiento elegido.

La firma RSF comprende el panel y el bosque serializado. No se transforma en
una suma de coeficientes Cox. El puntaje es `rowSums(CHF)` sobre la malla temporal
del bosque: valores mayores indican peor pronóstico. No es una probabilidad.
La importancia no es un HR, dirección de efecto ni valor p.

Antes de predecir ACRG se verifica la cobertura del panel. No se recorta el
panel ni se imputan genes ausentes para forzar una predicción. La aplicación
externa no reajusta los árboles ni utiliza sus desenlaces para seleccionar genes.

## 6. Evaluación de las dos firmas

### Grupos y curvas de supervivencia

Se define alto riesgo como puntaje mayor o igual a la mediana y bajo riesgo
como puntaje menor. Los cortes son descriptivos y dependientes de la cohorte:

| Análisis | Mediana utilizada |
|---|---|
| TCGA global | Global TCGA |
| TCGA I–II | Del subgrupo TCGA I–II |
| ACRG global | Global ACRG |
| ACRG I–II | Se conserva el corte global ACRG |

Se generan Kaplan–Meier, tabla de pacientes en riesgo y log-rank con todo el
seguimiento. Los empates no se reparten artificialmente en dos mitades. Si no
hay dos grupos con observaciones, se informa la limitación de la comparación.

### Concordancia y AUC

El C de Harrell se obtiene del marcador continuo con `survival::concordance`,
`reverse = TRUE`. No se reestima un coeficiente para invertir automáticamente
su dirección y no se calcula C de Uno en este flujo.

`timeROC` utiliza el marcador continuo, evento de muerte, ponderación marginal
por censura y horizonte de un año. Los casos son muertes hasta ese momento;
los controles tienen seguimiento posterior. Los censurados hasta el horizonte
no se reclasifican como controles conocidos. Se registra el soporte temporal.
Los límites del IC de AUC se expresan en escala 0–1.

Se extrae el horizonte solicitado por su valor temporal: cuando `timeROC`
agrega tiempo cero, no se presupone que `AUC[1]` sea el resultado al año.
No se recortan a un año los análisis KM o de concordancia.

### Evaluación aparente, CV y OOB

El desempeño del modelo final sobre TCGA es aparente. La CV participa en la
selección de hiperparámetros RSF y no es una prueba independiente de la
configuración seleccionada. El filtro, VST y lista inicial de candidatos no se
repiten íntegramente desde conteos dentro de cada fold.

OOB utiliza CHF y predicciones aparentes guardados en el estado RSF. No entrena,
no selecciona genes y no modifica el archivo de entrada. Calcula AUC al año
sin IC convencional y C de Harrell con todo el seguimiento. Contrasta este C
con `1 - prediction.error` de `ranger`; una diferencia se marca para revisión.
La etiqueta `REVISAR_EMPATES` no demuestra por sí sola que los empates sean
la causa de la discrepancia.

OOB sigue condicionado al panel y parámetros seleccionados en TCGA. Una caída
frente al desempeño aparente evidencia optimismo, pero no lo corrige ni valida
de forma independiente toda la selección. No debe compararse OOB RSF con AUC
aparente LASSO como si ambos tuvieran el mismo diseño de evaluación.

## 7. Alcance de las conclusiones

La comparación externa describe las firmas y su procesamiento conjunto. El
transporte entre plataformas y las diferencias de población pueden contribuir
al desempeño observado. No se atribuye toda diferencia al algoritmo.

El flujo no incluye pruebas pareadas formales de diferencia de AUC, calibración
de probabilidades, beneficio para decisiones clínicas ni evaluación formal de
riesgos proporcionales. Los subgrupos y las asociaciones posteriores a selección
se interpretan como exploratorios. ACRG ya ha sido examinada durante el proyecto
y no se presenta como validación externa ciega.
