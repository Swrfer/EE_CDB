# Comparación de firmas pronósticas LASSO-Cox y Random Survival Forest en cáncer gástrico

**Autor:** Alejandro García Colorado.  
**Curso:** Ciencia de datos aplicada en biomedicina y en la industria farmacéutica/de la salud: de la academia a la industria.  
**Programa:** Doctorado en Ciencias Biomédicas, Universidad Nacional Autónoma de México (UNAM).  
**Profesor:** Dr. Antonio Daniel Martínez Gutiérrez.  
**Versión de la entrega:** 20 de noviembre de 2026.  
**Repositorio:** [Swrfer/EE_CDB](https://github.com/Swrfer/EE_CDB).

## 1. Pregunta de investigación y objetivo

¿Qué rendimiento pronóstico presentan las firmas moleculares construidas con
LASSO-Cox y Random Survival Forest (RSF), a partir de genes modulados por Ca²⁺
alterados en cáncer gástrico temprano, para evaluar la supervivencia global de
pacientes con cáncer gástrico, y cómo se comportan en una cohorte externa?

El objetivo es reconstruir una firma LASSO-Cox, desarrollar una firma RSF con las
mismas entradas de expresión y supervivencia y comparar su discriminación y
estratificación pronóstica. El desarrollo utiliza TCGA-STAD; la evaluación externa
principal corresponde a toda la cohorte ACRG (GSE62254). Los análisis de estadios
I–II se consideran exploratorios.

## 2. Alcance y contenido de la entrega

La entrega contiene código, documentación, pruebas técnicas y referencias de
entrada. **No contiene tablas de resultados, figuras, datos descargados, modelos,
predicciones ni objetos de sesiones anteriores.** Las carpetas `data/raw/` y
`resultados/` están vacías al descomprimir. El maestro genera sus archivos al
ejecutarse; no requiere objetos como `cvfit`, `x` o `y` en la sesión de R.

Se distribuyen dos entradas científicas fijas en `referencias/`:

- La lista de **216 genes candidatos**, procedente de un análisis transcriptómico
  multicohorte previo de tres datasets GEO y TCGA-STAD. El contraste fue cáncer
  gástrico en estadios I–II frente a tejido gástrico control, seguido del filtrado
  por los genes relacionados con Ca²⁺ de Hörtenhuber et al. (2017).
- La referencia de **ocho genes y coeficientes LASSO-Cox**, utilizada exclusivamente
  para comprobar la reconstrucción del ajuste. No sustituye los coeficientes
  estimados a partir de los datos.

El análisis diferencial multicohorte que originó los 216 candidatos queda fuera
de este flujo. La reproducción comienza con esa lista fija y la adquisición de
datos procesados de repositorios: conteos STAR de GDC y Series Matrix de GEO.
No incluye procesamiento de FASTQ ni de archivos CEL.

## 3. Requisitos e información clínica ACRG

Se necesita R, conexión a internet, espacio para varios GB de descargas y permisos
de escritura en la carpeta del proyecto y en alguna biblioteca de R. El entorno
de referencia es **R 4.4.0, macOS ARM y Bioconductor 3.20**. El instalador conserva
los paquetes que cargan y cumplen los requisitos; instala o actualiza únicamente
los necesarios. No instala R ni compiladores del sistema.

La única entrada local externa es el **archivo clínico ACRG**. Se recomienda CSV;
también se admite el suplemento original en Excel (`.xls` o `.xlsx`). El archivo
no se distribuye en este ZIP. Debe contener una de estas estructuras:

| Información | Encabezado del suplemento | Encabezado alternativo |
|---|---|---|
| Identificador numérico vinculado a GEO | `Tumor ID` | `patient_id` |
| Supervivencia global en meses | `OS (months)` | `OS_months` |
| Estado de seguimiento | `FU status` | `OS_event` |
| Estadio | `pStage` | `stage` |

Con `FU status`, los códigos 0/1 corresponden a censura, 2/3/4 a muerte y 5 queda
excluido. Con `OS_event`, 0 es censura y 1 es muerte. **No incluir ambas columnas
de estado en el mismo archivo.** La unidad del tiempo debe estar explícita en el
encabezado. No se interpreta una columna ambigua llamada únicamente `OS_time`.
El estadio se requiere para los subanálisis; si falta se registra como desconocido.

El CSV puede usar coma, punto y coma o tabulador como separador. La
[plantilla clínica](referencias/PLANTILLA_ACRG_clinical.csv) contiene únicamente
encabezados: debe completarse con la información clínica real. No basta con
cambiar la extensión de un Excel a `.csv`; debe exportarse al formato elegido.

## 4. Ejecución completa desde R o RStudio

1. Descomprimir el ZIP en una carpeta nueva y conservar juntos
   `Script_maerstro_FMP.R`, `Funciones_fmp_comparacion.R` y `referencias/`.
2. Abrir una sesión nueva de R o RStudio, sin restaurar `.RData`.
3. Ejecutar **todo el bloque siguiente**. En el primer selector, elegir el archivo
   clínico ACRG. En el segundo, elegir `Script_maerstro_FMP.R` de la carpeta nueva.

```r
# 1. Seleccionar el archivo clinico ACRG: CSV o suplemento Excel
message("Selecciona el archivo clinico ACRG")
archivo_acrg <- normalizePath(file.choose(), mustWork = TRUE)

# 2. Evitar rutas y estados de otros proyectos
Sys.unsetenv(c(
  "FMP_DATA_DIR", "FMP_LEGACY_RUN",
  "FMP_LASSO_STATE", "FMP_RSF_STATE"
))

# 3. Ejecutar todos los bloques y adquirir solo lo que falte
Sys.setenv(
  FMP_STAGE = "all",
  FMP_INSTALL = "missing",
  FMP_DOWNLOAD = "missing",
  FMP_ACRG_CLINICAL = archivo_acrg
)

# 4. Seleccionar Script_maerstro_FMP.R
message("Selecciona Script_maerstro_FMP.R")
source(file.choose(), encoding = "UTF-8")
```

El maestro resuelve su ubicación: no es necesario copiar una ruta de otro equipo
ni usar `setwd()`. Carga automáticamente el archivo de funciones y crea todos
los objetos intermedios. Si el directorio de trabajo ya es la carpeta del
proyecto, la última línea puede sustituirse por:

```r
source("Script_maerstro_FMP.R", encoding = "UTF-8")
```

El nombre del maestro es exactamente **`Script_maerstro_FMP.R`**. No ejecutar
solo el archivo de funciones ni bloques seleccionados del maestro.

## 5. Ejecución completa desde la terminal

Los siguientes comandos se ejecutan en **Terminal**, no en la consola de R.
Sustituir las rutas de ejemplo por las del equipo. Mantener las comillas cuando
la ruta tenga espacios. `Rscript` debe estar disponible en el sistema.

```bash
cd "/ruta/entrega_final_FMP"

Rscript --vanilla Script_maerstro_FMP.R \
  --stage=all \
  --install=missing \
  --download=missing \
  --acrg-clinical="/ruta/ACRG_clinical.csv"
```

Para usar el suplemento Excel, indicar su ruta en `--acrg-clinical`.
`--vanilla` evita restaurar una sesión anterior. Los argumentos explícitos de la
terminal tienen prioridad sobre las variables `FMP_*` del entorno.

**Desde cero** significa ejecutar en una carpeta nueva, sin copiar descargas ni
modelos anteriores. `missing` reutiliza archivos completos si ya existen; volver
a ejecutar sobre la misma carpeta comprueba una reejecución con caché.

## 6. Datos adquiridos y flujo de análisis

| Entrada | Adquisición | Archivo generado en `data/raw/` |
|---|---|---|
| Expresión TCGA-STAD | GDC, `STAR - Counts`, acceso abierto; ensayo `unstranded` | `tcga_counts_metadata.rds` |
| Clínica TCGA-STAD | `GDCquery_clinic` | `tcga_clinical_original.rds` |
| Expresión ACRG | GSE62254/GPL570, Series Matrix oficial por HTTPS | `GSE62254_eset.rds` |
| Clínica ACRG | Archivo local seleccionado o indicado por argumento | Se lee desde la ruta proporcionada |

La descarga TCGA se divide en bloques de 20 archivos. GEO se descarga como matriz
comprimida, se valida y se lee localmente sin descargar la anotación GPL; las
sondas se anotan con `hgu133plus2.db`. La consulta, procedencia, huellas y entorno
de adquisición se registran en `data/raw/`.

El flujo `all` ejecuta, en este orden:

1. Comprobación e instalación de dependencias necesarias.
2. Descarga de las entradas ausentes y lectura de la clínica ACRG.
3. Alineación de clínica y expresión; preparación de TCGA y ACRG.
4. Ajuste LASSO-Cox, comprobación de la firma y evaluación TCGA/ACRG.
5. Selección y ajuste RSF con TCGA; evaluación TCGA/ACRG y comparación de firmas.
6. Comprobación aparente/OOB del bosque guardado, sin reentrenarlo en esta etapa.
7. Publicación de tablas, figuras, informes y registro de finalización.

## 7. Métodos de preparación, modelado y evaluación

**Expresión TCGA.** Se conservan tumores primarios y genes con al menos 10 conteos
en al menos el 20% de las muestras alineadas. Se aplica DESeq2 con `design = ~1`,
estimación de factores de tamaño y `vst(blind = TRUE)`. Después se anotan Ensembl
a símbolos y se conserva la primera fila por símbolo. Se seleccionan los
candidatos elegibles y los registros con seguimiento positivo.

**Expresión ACRG.** La Series Matrix contiene señal RMA en escala log10. El flujo
conserva normalización adicional por cuantiles, `log2(x + 1)` únicamente si el
máximo supera 50, y media de sondas por símbolo. El puntaje LASSO completo se
estandariza con `scale()` dentro de ACRG. Esto no equivale a estandarizar cada gen
ni armoniza las unidades VST y microarreglo.

**LASSO-Cox.** `cv.glmnet`, familia Cox, `alpha = 1`, estandarización interna,
10 folds, semilla 123, pérdida de verosimilitud parcial y selección con
`lambda.min`. El puntaje suma expresión por coeficiente penalizado. Se comprueban
genes y coeficientes frente a la referencia con tolerancia absoluta `1e-6`;
una discrepancia detiene el flujo y se documenta.

**RSF.** Utiliza los mismos pacientes, candidatos TCGA elegibles y folds de
LASSO. Dentro de cada fold se seleccionan genes por importancia de permutación
usando solo su entrenamiento. Se comparan paneles de 5/10/20 genes y tamaños de
nodo 10/20, con 1000 árboles. Se elige la combinación con mayor C de Harrell
medio de validación, se selecciona el panel en todo TCGA y se ajusta el bosque
final antes de aplicarlo a ACRG. El marcador es `rowSums(CHF)`; no es una
probabilidad de muerte ni un conjunto de coeficientes lineales.

**Evaluación.** Kaplan–Meier y log-rank describen grupos de riesgo; el C de
Harrell utiliza el marcador continuo y todo el seguimiento. `timeROC` evalúa
discriminación acumulativa/dinámica al año con censura. Calcular AUC al año
no recorta a un año las curvas KM ni el análisis de concordancia. Se generan
evaluaciones globales e I–II para ambos modelos y cohortes.

**OOB.** La comprobación utiliza las predicciones ya almacenadas de los árboles
que no incluyeron a cada paciente en su muestra de entrenamiento. Conserva el
panel y el bosque y contrasta el rendimiento aparente con el OOB. No repite
la selección de genes ni de hiperparámetros.

Los parámetros, reglas clínicas, cortes KM y límites de interpretación se
describen en [Metodología](docs/METODOLOGIA.md).

## 8. Organización y verificación de las salidas

| Ruta | Contenido generado o distribuido |
|---|---|
| `Script_maerstro_FMP.R` | Punto único de entrada |
| `Funciones_fmp_comparacion.R` | Funciones de adquisición, preparación, modelos y evaluación |
| `referencias/` | Lista de candidatos, referencia LASSO y plantilla clínica |
| `docs/` | Documentación del proyecto |
| `tests/` | Pruebas técnicas separadas del análisis |
| `data/raw/` | Datos descargados y procedencia; inicialmente vacía |
| `data/instalacion/` | Plan, acciones y versiones del instalador |
| `data/privados/lasso/`, `rsf/`, `oob/` | Matrices, folds, modelos y predicciones individuales |
| `data/respaldos/ultima_ejecucion/` | Un respaldo del conjunto reemplazado |
| `resultados/figuras/lasso/`, `rsf/`, `comparacion/`, `oob/` | Figuras PDF y PNG |
| `resultados/tablas/lasso/`, `rsf/`, `comparacion/`, `oob/` | Tablas agregadas |
| `resultados/docs/` | Informes, configuración, advertencias, huellas, código ejecutado y `sessionInfo()` |

Todos los bloques comparten la misma raíz `resultados/`; no se crean réplicas
fechadas anidadas. La ejecución se prepara temporalmente y se publica al
completar los bloques solicitados. Un fallo previo conserva la salida anterior;
por ello, la existencia de figuras por sí sola no acredita una ejecución nueva.

Para comprobar una ejecución completa, revisar:

- `resultados/docs/ULTIMA_EJECUCION_COMPLETA.csv`: etapas `lasso`, `rsf` y `oob`,
  acción `all` y fecha/hora UTC de finalización.
- `resultados/tablas/lasso/estado_reproduccion_firma.csv`: coincidencia de la firma.
- `resultados/tablas/comparacion/COMPARACION_MAESTRA_timeROC.csv` y
  `COMPARACION_MAESTRA_KM_Cindex.csv`: comparación de las firmas.
- `resultados/tablas/oob/RSF_COMPROBACION_OOB_checks.csv`: controles de la
  comprobación OOB; revisar cada estado, no solo la finalización.
- `resultados/docs/*_advertencias.csv` y `*_sessionInfo.txt`: advertencias y
  versiones efectivas de cada bloque.

En R interactivo también queda el objeto `resultado_fmp`. Para futuras etapas
se utilizan los RDS guardados; no es necesario conservar la sesión de R abierta.

## 9. Ejecución por etapas y reanudación

La etapa `all` es la opción para reproducir el proyecto completo. Las demás
permiten comprobar dependencias o ejecutar bloques de forma separada:

| Etapa | Acción y requisito |
|---|---|
| `install` | Instala/comprueba paquetes; no requiere clínica ni descarga cohortes |
| `download` | Adquiere entradas; requiere el archivo clínico; no ajusta modelos |
| `lasso` | Ajusta y evalúa LASSO; inicia un conjunto de salidas sin RSF/OOB anteriores |
| `rsf` | Lee el estado LASSO guardado; ajusta RSF, compara y comprueba OOB |
| `oob` | Lee el estado RSF guardado; no entrena modelos |
| `organize` | Importa una ejecución del formato anterior; requiere `--legacy-run`; no se usa desde cero |

Por ejemplo, para comprobar solo paquetes o descargar antes de ajustar:

```bash
Rscript --vanilla Script_maerstro_FMP.R --stage=install --install=missing

Rscript --vanilla Script_maerstro_FMP.R \
  --stage=download --install=missing --download=missing \
  --acrg-clinical="/ruta/ACRG_clinical.csv"
```

Después se ejecuta `all` para completar el análisis. `--install=never` impide
instalaciones y `--download=never` impide adquirir entradas ausentes. Estas
opciones requieren paquetes y archivos ya disponibles; no corresponden a una
primera ejecución en un equipo sin dependencias.

`--data-dir` cambia la caché de entrada; `--output-dir` cambia la raíz de
resultados. Los estados locales permanecen en `data/privados/` del proyecto.
Para OOB y recuperación consultar los documentos enlazados abajo.

## 10. Límites de interpretación y reproducibilidad

- TCGA se utiliza para desarrollar las firmas; su rendimiento sobre esos mismos
  pacientes es aparente. No hay un conjunto de prueba TCGA apartado en este flujo.
- La selección previa de los 216 genes incluyó TCGA. Ni esa selección ni toda la
  preparación desde conteos se repiten dentro de la validación cruzada de RSF.
- La CV elige parámetros; OOB evalúa el bosque condicionado a la selección
  realizada. Ninguno constituye una evaluación independiente de todo el proceso.
- VST y señal RMA log10 no son unidades equivalentes. Los cuantiles y la
  estandarización del puntaje no resuelven por sí solos el transporte entre
  plataformas. Se generan diagnósticos por gen y de variabilidad de puntajes.
- Los cortes por mediana dependen de la cohorte. Los empates y pocos eventos en
  subgrupos pueden limitar su interpretación. Una AUC al año tampoco resume
  todos los aspectos del pronóstico durante el seguimiento completo.
- ACRG se presenta como evaluación externa exploratoria. No se realiza una
  prueba pareada formal de diferencia de AUC, calibración de probabilidades ni
  evaluación de beneficio clínico. No se declara superioridad universal de un
  algoritmo por esta comparación.
- El instalador registra las versiones, pero no impone un lockfile completo.
  Cambios de repositorios, anotaciones, entradas u orden pueden modificar el
  ajuste. La coincidencia exacta requiere entradas y entorno equivalentes.

Los datos descargados, modelos e identificadores se mantienen fuera del
repositorio mediante `.gitignore`. Este ZIP no incorpora archivos clínicos reales
ni resultados previos. Las referencias fijas se explican en
[referencias/README.md](referencias/README.md).

## 11. Documentación complementaria

- [Metodología](docs/METODOLOGIA.md).
- [Instalación y entorno R 4.4](docs/INSTALACION_R44.md).
- [Errores, advertencias y reanudación](docs/ERRORES_Y_REANUDACION.md).
- [Diccionario de salidas](docs/DICCIONARIO_SALIDAS.md).
- [Comprobación OOB sin reentrenamiento](docs/COMPROBACION_FINAL_OOB.md).
- [Criterios de interpretación](docs/INTERPRETACION.md).
- [Validación técnica y pruebas](docs/VALIDACION_TECNICA.md).

ChatGPT/Codex apoyó la programación, documentación y pruebas técnicas. Las
decisiones científicas y la interpretación del trabajo corresponden al autor.

## 12. Fuentes

- [Hörtenhuber et al. (2017), genes relacionados con Ca²⁺](https://doi.org/10.1093/bioinformatics/btx225).
- [TCGA-STAD, Genomic Data Commons](https://portal.gdc.cancer.gov/projects/TCGA-STAD).
- [GSE62254, ACRG](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE62254).
- [Cristescu et al., estudio ACRG](https://doi.org/10.1038/nm.3850).
- [GSM1523863, descripción de señal RMA log10](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM1523863).
- [TCGAbiolinks, adquisición de datos](https://bioconductor.org/packages/release/bioc/vignettes/TCGAbiolinks/inst/doc/download_prepare.html).
- [GEOquery, lectura de datos GEO](https://seandavi.github.io/GEOquery/reference/getGEO.html).
- [DESeq2](https://doi.org/10.1186/s13059-014-0550-8).
- [glmnet, modelos Cox](https://glmnet.stanford.edu/articles/Coxnet.html).
- [ranger](https://imbs-hl.github.io/ranger/reference/ranger.html).
- [timeROC](https://cran.r-project.org/package=timeROC).
