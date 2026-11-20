# Comparación de firmas pronósticas LASSO-Cox y Random Survival Forest en cáncer gástrico

Autor: **Alejandro García Colorado**.

Curso: **Ciencia de datos aplicada en biomedicina y en la industria farmacéutica/de
la salud: de la academia a la industria**, Doctorado en Ciencias Biomédicas,
**Universidad Nacional Autónoma de México (UNAM)**.
Profesor: **Dr. Antonio Daniel Martínez Gutiérrez**.
Documentación actualizada el **20 de noviembre de 2026**.

## Estado de esta entrega

Carpeta independiente: **entrega_final_FMP**, destinada a
[Swrfer/EE_CDB](https://github.com/Swrfer/EE_CDB), rama de trabajo `entrega/fmp-final`.

El maestro incorpora instalación de dependencias faltantes y descarga de TCGA-STAD
(conteos y clínica) y GSE62254. **La única entrada local externa es el CSV clínico ACRG**.
La lista de 216 genes y la referencia LASSO se distribuyen con el código.
No depende de objetos de R ni de modelos creados durante las pruebas.

Los resultados incluidos corresponden a la ejecución histórica confirmada:
**LASSO de ocho genes y RSF de 20 genes**. La comprobación OOB de ese bosque dio
AUC al año **0.6530** y C de Harrell **0.6197**, sin reentrenamiento.
El autor informó una reproducción integral correcta en su Mac el 20/11/2026,
antes de reorganizar las carpetas. La ejecución con la nueva organización está
en curso según su último reporte. El primer intento en otro equipo, también con
R 4.4.0/macOS ARM, se detuvo durante la instalación de dependencias. Esta versión
corrige ese instalador; la réplica integral en ese equipo sigue pendiente.
Las pruebas de programación aquí documentadas se distinguen de esas ejecuciones
con cohortes reales.

Una consulta nueva puede cambiar datos, anotaciones u orden y, por tanto, el ajuste.
Se conservan las entradas descargadas, la consulta, las huellas y sessionInfo.
Si la firma LASSO no coincide con la referencia a tolerancia 1e-6, el flujo se detiene
y guarda la comparación. No sustituye coeficientes para forzar coincidencia.

## Inicio rápido en otra computadora: ejecutar en R o RStudio

1. Descomprimir el ZIP actualizado en una **carpeta nueva** y disponer del CSV
   clínico ACRG proporcionado por el autor. Tener R instalado, internet y espacio
   para las descargas. El CSV puede estar en cualquier carpeta: se selecciona
   explícitamente en el primer paso del código.
2. Abrir una sesión nueva de R o RStudio y ejecutar **todo el bloque siguiente**.
   El **primer selector** es para el CSV clínico ACRG. El **segundo selector** es
   para `Script_maerstro_FMP.R` de la carpeta recién descomprimida. El maestro
   resuelve su propia ubicación; no hay que copiar rutas del equipo del autor
   ni configurar `setwd()` con su directorio de OneDrive.
3. Esperar a que terminen todos los bloques. Las tablas, figuras e informes se
   publican en `resultados/`; la finalización se registra en
   `resultados/docs/ULTIMA_EJECUCION_COMPLETA.csv`.

```r
# 1. Seleccionar el CSV clinico ACRG
message("Selecciona el CSV clinico de ACRG")
archivo_acrg <- normalizePath(
  file.choose(),
  mustWork = TRUE
)

# 2. Usar la carpeta de datos del proyecto nuevo
Sys.unsetenv(c("FMP_DATA_DIR", "FMP_LEGACY_RUN"))

# 3. Ejecutar todo; instalar solamente dependencias faltantes
Sys.setenv(
  FMP_STAGE = "all",
  FMP_DOWNLOAD = "missing",
  FMP_INSTALL = "missing",
  FMP_ACRG_CLINICAL = archivo_acrg
)

# 4. Seleccionar Script_maerstro_FMP.R de la carpeta nueva
message("Selecciona Script_maerstro_FMP.R")
source(file.choose(), encoding = "UTF-8")
```

**En el equipo del autor**, donde los paquetes ya están disponibles, puede
cambiarse únicamente `FMP_INSTALL = "missing"` por `FMP_INSTALL = "never"` para
impedir cualquier instalación. En otro equipo se recomienda `"missing"`:
comprueba los paquetes y sus dependencias obligatorias. Conserva los que cargan
y cumplen los requisitos de versión. Si un paquete instalado falla por una
dependencia ausente, repara primero esa dependencia. Solo se instala o actualiza
un paquete cuando falta o no satisface un requisito; no hay actualización general.
Los binarios compatibles tienen prioridad en macOS/Windows, sin preguntar por
compilar versiones más recientes. [Detalles y prueba de instalación](docs/INSTALACION_R44.md).

Si R ya tiene como directorio de trabajo la carpeta de entrega, la última línea
puede ser `source("Script_maerstro_FMP.R", encoding = "UTF-8")` y se evita el
segundo selector. El archivo `Funciones_fmp_comparacion.R` debe permanecer junto
al maestro; este lo carga automáticamente.

**Qué significa desde cero:** usar el ZIP limpio y el CSV clínico, sin copiar los
RDS descargados ni los modelos de una ejecución anterior. `missing` descarga
solo entradas ausentes; si se reutiliza una carpeta que ya tiene esos RDS,
se reutilizan sus archivos y se está comprobando una reejecución con caché.
Los resultados agregados incluidos en el ZIP no son entradas para entrenar.

**Dos incidencias de configuración observadas:** el error `legacy-run` aparece
cuando se selecciona `organize`, que requiere una ejecución anterior. El bloque
anterior fija `all`. El error de CSV aparece si la ruta clínica configurada no
existe: este bloque la establece a partir del archivo seleccionado. La búsqueda
automática por nombre se limita a `data/raw/ACRG_clinical.csv` y a los nombres
alternativos documentados; dejar el CSV junto a los scripts no lo coloca en
esa ruta. Seleccionarlo explícitamente evita depender de su ubicación.

## Pregunta de investigación

**¿Qué capacidad tienen las firmas construidas con LASSO-Cox y RSF, a partir de genes
modulados por Ca²⁺ alterados en cáncer gástrico temprano, para ordenar el riesgo de
muerte y discriminar la supervivencia global de pacientes con cáncer gástrico,
y cómo se comportan al aplicarse a una cohorte externa?**

El objetivo es comparar las firmas concretas y sus procedimientos de aplicación.
La diferencia de desempeño externo también puede reflejar el transporte entre
tecnologías, no únicamente el algoritmo. No se plantea su uso inmediato en decisiones clínicas.

## Alcance acordado

- Desarrollo en toda la cohorte elegible de TCGA-STAD; no hay un test TCGA apartado en el análisis principal actual.
- Evaluación externa principal en **ACRG completa**, sin combinar cohortes.
- Supervivencia global a lo largo de todo el seguimiento para KM y C de Harrell.
- Discriminación al **año** mediante ROC dependiente del tiempo; tiempos en años.
- Subanálisis I–II conservados como exploratorios, fuera de la conclusión externa principal.
- Variables predictoras: expresión génica. Edad, sexo y estadio no entran en estas firmas moleculares.
- El flujo completo reproduce los ajustes desde los datos; no modifica los métodos para
  mejorar resultados. La etapa oob únicamente lee el bosque guardado y no reentrena.
- No se realiza Z-score por gen, armonización con tejidos no tumorales, ComBat ni transformación a rangos.
- Proyecto transcriptómico centrado en firmas pronósticas; no implementa SQL/OMOP.

Los 216 GED proceden de un análisis transcriptómico previo que integró **tres
datasets GEO y TCGA-STAD**, comparando cáncer gástrico **estadios I–II frente a
tejido gástrico control (TGC)**. Tras el análisis diferencial se filtraron los genes
con la lista de genes vinculados con señalización por Ca²⁺ de **Hörtenhuber et al.
(2017)**, DOI: [10.1093/bioinformatics/btx225](https://doi.org/10.1093/bioinformatics/btx225).

Esa selección originó la propuesta de firma LASSO-Cox. En esta entrega los 216
candidatos son una entrada científica fija; no se vuelve a ejecutar el análisis
multicohorte previo. Las accesiones de los tres GEO y los umbrales de ese estudio
previo no se aportaron en esta revisión y no se inventan. **TCGA participó en la
selección previa**, que tampoco se repite dentro de la validación cruzada.
**Esto no significa que el entrenamiento actual incluya únicamente estadios I–II.**
La cohorte principal contiene los estadios disponibles en TCGA; I–II es un subgrupo.

## Datos, obtención y procedencia

| Fuente | Obtención en el maestro | Contenido utilizado |
|---|---|---|
| TCGA-STAD / GDC | TCGAbiolinks: GDCquery, GDCdownload y GDCprepare; STAR - Counts abiertos | Conteos crudos del ensayo **unstranded** |
| Clínica TCGA-STAD | GDCquery_clinic(project="TCGA-STAD", type="clinical") | Seguimiento, estado vital, estadio e identificadores |
| ACRG, GSE62254 | Descarga HTTPS de Series Matrix y GEOquery::getGEO(filename=..., getGPL=FALSE), GPL570 | ExpressionSet procesado a nivel de sondas |
| Clínica ACRG | **CSV proporcionado por el usuario**, exportado del suplemento clínico ACRG | Tumor ID, OS (months), FU status y pStage; esquema alternativo documentado |
| 216 candidatos | referencias/216_GED.csv | Lista fija del estudio previo |

La consulta TCGA reproduce los filtros de proyecto, categoría, tipo y workflow del
script histórico, sin filtrar por supervivencia. El filtrado de tumores primarios
se realiza después en la preparación original. Se selecciona explícitamente
`unstranded`; el nombre del ensayo del antiguo objeto sin metadatos no se considera
recuperado retroactivamente.

Para GEO se descarga directamente `GSE62254_series_matrix.txt.gz` desde el
servidor HTTPS oficial de NCBI y se lee localmente con `getGPL=FALSE` y
`AnnotGPL=FALSE`. La anotación de sondas sigue usando hgu133plus2.db. Se verifica
gzip, identificación GSE62254/GPL570 y tabla completa; una respuesta HTML o una
matriz incompleta no se acepta. Hay hasta tres intentos y se conserva un archivo
anterior incompleto con otro nombre. Ver [recuperación de errores](docs/ERRORES_Y_REANUDACION.md).

Las tres entradas descargadas se guardan en `data/raw/`. Solo se descargan objetos
que falten. No se necesita abrir una sesión manual ni ejecutar un bloque antiguo.
Las descargas se guardan de forma atómica; una caché RDS ilegible no se reemplaza
silenciosamente. Si se interrumpe una descarga, se puede volver a ejecutar el maestro;
los objetos RDS completos se conservan y TCGAbiolinks reutiliza sus archivos GDC.

Cada adquisición guarda `procedencia_descargas.csv`, la consulta GDC en RDS y su
tabla de archivos, el estado/release reportado por GDC cuando es accesible y
`sessionInfo_descarga.txt`. Se registra fecha UTC y MD5. Una entrada preexistente
sin fecha documentada no recibe una fecha histórica inferida. La clínica del CSV
se incorpora a las huellas de la ejecución del modelo.

`referencias/procedencia_scripts.json` conserva las huellas de los scripts históricos.
`referencias/procedencia_entrega.json` describe esta entrega.
`resultados/PROCEDENCIA_RESULTADOS.csv` identifica las tablas y figuras
históricas recibidas, con SHA256. No se modificaron estimaciones; únicamente se
sustituyó una ruta personal por una relativa en el resumen de preparación TCGA.

## Cohortes y estandarización clínica

**TCGA.** Se alinea la clínica con los barcodes de expresión por identificador de
paciente y se conservan tumores primarios (código de muestra 01). Se mantienen el orden
de muestras y el orden de genes del procedimiento original.

- OS.time: days_to_death si existe; en caso contrario days_to_last_follow_up.
- OS.event: Dead=1 y Alive=0; los registros sin seguimiento/estado válidos se excluyen.
- Se conserva el filtro de tiempo positivo después de VST, para replicar el original.
- El código homologa gender desde sex_at_birth o sex cuando hace falta.
- Los estadios se homologan como I, II, III y IV; el estadio desconocido no excluye del análisis global.

| Paso confirmado de TCGA | Número |
|---|---:|
| Tumores primarios alineados con clínica antes de excluir tiempos no positivos | 399 |
| Excluidos por tiempo no positivo en este paso | 21 |
| Muestras y pacientes en los modelos | 378 |
| Muertes durante todo el seguimiento | 158 |
| Pacientes I–II | 168 |
| Muertes I–II durante todo el seguimiento | 50 |

En la ejecución confirmada hay una muestra por paciente (378 muestras y 378 pacientes).
El código avisa si una nueva entrada contiene muestras repetidas del mismo paciente.

**ACRG.** Se vinculan los perfiles GEO con Tumor ID del CSV clínico, manteniendo la
alineación expresión–clínica. Se reproduce la codificación del script original:
FU status 2/3/4 → muerte; 0/1 → censura. Los códigos distintos quedan sin clasificar.
Son 300 pacientes, con 152 muertes durante el seguimiento; el subgrupo I–II contiene
126 pacientes y 36 muertes.

**Unidades.** TCGA: días/365. ACRG: meses×30.44/365, conservando la conversión histórica
para reproducir exactamente el horizonte; no se sustituye por meses/12 a mitad del análisis.
El origen temporal es el del seguimiento clínico del repositorio. Este trabajo no
reconstruye una ventana longitudinal previa a una fecha de uso clínico del modelo;
la disponibilidad del perfil molecular respecto al inicio del seguimiento debe
considerarse antes de proponer una aplicación prospectiva.

## Preparación de la expresión

### TCGA: conteos → VST → símbolos → candidatos

1. Se requieren conteos crudos, numéricos, no negativos, con filas Ensembl y barcodes.
2. Se conservan genes con ≥10 conteos en ≥20% de los tumores alineados. Quedan 28,207 filas de 60,660.
3. Se crea un DESeqDataSet con design=~1, se estiman factores de tamaño y se aplica `vst(blind=TRUE)`.
4. Se retira la versión Ensembl y se anota con org.Hs.eg.db. Se conserva la primera fila
   anotada por símbolo después de VST; no se suman conteos antes de transformar.
5. Entre 21,094 símbolos retenidos se recuperan **210 de los 216 candidatos**.
6. Se conservan los pacientes con tiempo positivo y se crea la matriz paciente×gen.

Los seis candidatos no elegibles después del filtro/anotación son CALHM1, CALML5,
FFAR1, GUCA1C, MYH2 y RPTN. Se registra esa exclusión; no se confunde con el antiguo
panel compartido de 208 genes. La presencia en ACRG no interviene en la selección TCGA.

**Acierto técnico:** VST atenúa la dependencia entre media y varianza propia de los conteos,
y se mantiene el mismo procesamiento para ambos modelos. **Límite:** VST no crea por sí
misma unidades equivalentes a las de un microarreglo.

### ACRG: señal procesada RMA en log10

**Corrección de documentación:** los metadatos GEO identifican VALUE como
`log10-transformed RMA signal intensity` (por ejemplo, GSM1523863). Los archivos
anteriores llamaban a esta entrada “log2”; esa etiqueta era incorrecta para la ejecución
confirmada. Se corrige la descripción, sin alterar las estimaciones ya obtenidas.

Se conserva la secuencia del código original: normalización adicional por cuantiles
con limma, aplicación de log2(x+1) solo si max>50 y media de sondas por símbolo tras
anotar con hgu133plus2.db. **En la ejecución confirmada additional_log2=FALSE**:
se mantuvo la escala log10 de la señal procesada; no se aplicó una segunda transformación log.

La normalización por cuantiles iguala distribuciones dentro de esta cohorte, pero no
armoniza directamente ACRG con TCGA. Su repetición sobre datos ya procesados se conservó
por fidelidad al script histórico; no se demuestra aquí que sea la preparación óptima.

Los ocho genes LASSO y los 20 RSF tienen cobertura completa en ACRG. El puntaje LASSO
se estandariza como `scale(puntaje)` dentro de ACRG. **Esto no es Z-score de cada gen**
y no soluciona la incompatibilidad de expresión entre plataformas.

No se implementó la propuesta complementaria de normalizar por referencias no tumorales.
Los controles no son un requisito para construir una firma pronóstica entre pacientes
con cáncer; podrían servir como referencia técnica para otra estrategia de transporte.

## Construcción de las firmas

### LASSO-Cox confirmado

Se ajusta `cv.glmnet` con family="cox", alpha=1, standardize=TRUE, 10 folds,
semilla 123, type.measure="deviance" y keep=TRUE. Se elige **lambda.min** por el
mínimo error de verosimilitud parcial en CV, no por buscar el mayor AUC.

- lambda.min: **0.0643854763669058**.
- lambda.1se: **0.135525255957141**.
- La referencia de ocho genes coincide con el ajuste a tolerancia absoluta 1e-6.
- `keep=TRUE` conserva los folds; no convierte automáticamente los resultados posteriores en OOF.

El marcador es la suma de expresión por coeficiente penalizado:
`risk_score = Σ expresión_VST(g) × coeficiente(g)`.

| Gen | Coeficiente por unidad VST | Dirección del puntaje |
|---|---:|---|
| VCAN | 0.005347754 | Mayor riesgo |
| KCNQ1 | -0.035561995 | Menor riesgo |
| SPARC | 0.036948349 | Mayor riesgo |
| PRKCG | -0.005030458 | Menor riesgo |
| MATN3 | 0.073926351 | Mayor riesgo |
| SYT4 | 0.041297398 | Mayor riesgo |
| HTR2C | 0.028519804 | Mayor riesgo |
| MYL4 | 0.026482423 | Mayor riesgo |

La dirección describe el aporte al puntaje, no causalidad ni un efecto experimental.
Los HR del forest por gen proceden de Cox univariados y no son estos coeficientes
penalizados. PRKCG puede ser seleccionado conjuntamente aunque su asociación
univariada no alcance p<0.05.

### RSF confirmado

Se usan los mismos 210 candidatos elegibles, pacientes y folds TCGA de LASSO.
Dentro de cada fold se ordenan genes con un bosque de selección por importancia
por permutación, utilizando únicamente el entrenamiento de ese fold.

Se comparan seis combinaciones: paneles de 5/10/20 genes y min.node.size=10/20.
Se elige el mayor C de Harrell medio de validación; empate: menos genes y luego
nodo mayor. Se vuelve a seleccionar el panel en todo TCGA y se congela el bosque final.

| Parámetro final | Valor |
|---|---|
| Genes | 20 |
| Árboles | 1000 |
| mtry de selección / final | 14 / 4 |
| min.node.size de selección / final | 15 / 20 |
| min.bucket | 3 |
| División | logrank |
| Importancia | permutation |
| Muestreo | Con reemplazo; sample.fraction=1 |
| Hilos | 2 |
| Semilla base | 20261118 |
| Semillas de selección / final | 20271118 / 20271119 |

Las semillas finales son sumas numéricas de la semilla base; no son fechas de ejecución.
El panel incluye MATN3, SYT4, SLC35G1, FKBP10, MYL4, UNC13C, NPY, HTR2C, ATP13A5,
FAT3, CDH19, VCAN, CDH2, KCNQ1, F2R, LRP1B, KCNB1, S100G, INAFM2 y GJB2.
Comparte seis genes con LASSO: MATN3, SYT4, MYL4, HTR2C, VCAN y KCNQ1.

RSF no asigna un coeficiente fijo por gen. La firma requiere el panel **y el bosque
serializado**. La figura de importancia muestra el bosque de selección en TCGA;
la tabla distingue esa importancia de la obtenida dentro del panel final.
La importancia no equivale a un HR, una dirección de efecto ni un valor p.

El marcador utilizado es `rowSums(CHF)` en la malla temporal del bosque, con mayor
valor indicando peor pronóstico. **No es una probabilidad de muerte ni un porcentaje.**

El mejor C medio de CV fue **0.5159**, SD **0.0918**, con 20 genes y nodo 20.
Las seis configuraciones oscilaron entre aproximadamente 0.498 y 0.516.
Esa CV se utilizó para seleccionar parámetros; el mejor valor no es una prueba
independiente de la configuración elegida. El filtro inicial y el VST ya estaban
fijados, de modo que tampoco se presenta como CV anidada del pipeline completo.

## Evaluación de supervivencia y discriminación

- KM y log-rank comparan grupos descriptivos con todo el seguimiento.
- C de Harrell evalúa el orden del marcador continuo con todo el seguimiento;
  se usa reverse=TRUE porque mayor puntaje indica peor supervivencia.
- timeROC evalúa un año: casos con muerte hasta el horizonte y controles con
  seguimiento posterior. Los censurados antes del año no se reclasifican como controles conocidos.
- AUC se calcula con el marcador continuo, no con Alto/Bajo.
- Los IC95% confirmados de AUC se obtuvieron con timeROC 0.4; sus límites expresados
  por el paquete en porcentaje se convirtieron a proporción.
- El C del marcador fijo se separa del C de un Cox de asociación reestimado. Aquí
  no se reporta C de Uno, que correspondía a otro enfoque anterior.

**Cortes KM:** Alto ≥ mediana; Bajo < mediana. TCGA global usa su mediana global;
TCGA I–II, la propia del subgrupo. ACRG global usa su mediana global; ACRG I–II
conserva ese corte global ACRG. No se busca un corte por p mínimo.
Son cortes de cohorte, no umbrales clínicos transportables. Los empates pueden impedir
una división equilibrada; no se fuerzan dos mitades.

## Resultados confirmados

Fuente: tablas recibidas el 19/11/2026; no son resultados calculados aquí sobre matrices de pacientes.

| Modelo | Evaluación | Población | n | AUC al año (IC95%) | C de Harrell | p log-rank |
|---|---|---|---:|---:|---:|---:|
| LASSO-Cox | TCGA (aparente) | Global | 378 | 0.659 (0.587–0.731) | 0.640 | 7.55e-06 |
| LASSO-Cox | TCGA (aparente) | I–II (exploratorio) | 168 | 0.691 (0.567–0.814) | 0.676 | 0.0101 |
| LASSO-Cox | ACRG (externa) | Global | 300 | 0.656 (0.575–0.738) | 0.630 | 0.000955 |
| LASSO-Cox | ACRG (externa) | I–II (exploratorio) | 126 | 0.632 (0.398–0.866) | 0.588 | 0.556 |
| RSF | TCGA (aparente) | Global | 378 | 0.951 (0.931–0.972) | 0.898 | 6.96e-55 |
| RSF | TCGA (aparente) | I–II (exploratorio) | 168 | 0.955 (0.923–0.986) | 0.910 | 3.27e-19 |
| RSF | ACRG (externa) | Global | 300 | 0.511 (0.480–0.542) | 0.502 | 0.854 |
| RSF | ACRG (externa) | I–II (exploratorio) | 126 | 0.424 (0.271–0.576) | 0.493 | 0.986 |

**Todos los resultados TCGA de esta tabla son aparentes:** corresponden al modelo
final sobre sus pacientes de desarrollo. No son AUC de test, OOF ni OOB.
Los IC convencionales no corrigen el optimismo por desarrollar y seleccionar el modelo en esos pacientes.

ACRG global incluye 48 muertes hasta un año, 252 pacientes seguidos más allá del
año y ninguna censura previa. El subgrupo I–II contiene solo seis muertes al año;
su AUC tiene mucha incertidumbre. KM y C utilizan además los eventos posteriores:
152 muertes globales y 36 en I–II durante todo el seguimiento.

### Hallazgos e interpretación

1. **Réplica LASSO lograda:** coinciden los ocho genes y coeficientes confirmados.
   Esa coincidencia no certifica por sí sola todas las métricas históricas del autor,
   cuyas referencias numéricas completas no se aportaron.
2. **LASSO conserva señal externa moderada:** AUC global ACRG=0.656 y C=0.630,
   con separación KM global. Esto no demuestra calibración ni utilidad clínica.
3. **RSF tiene fuerte optimismo aparente:** C de Harrell TCGA=0.898 frente a C
   medio de CV≈0.516. El AUC aparente es 0.951. La discordancia entre ajuste y
   evaluación interna indica una capacidad de generalización limitada del procedimiento ensayado.
4. **RSF no muestra discriminación externa útil bajo esta aplicación directa:**
   AUC ACRG global=0.511 y C=0.502. La diferencia con LASSO es descriptiva;
   aquí no se realizó una prueba pareada formal de diferencia de AUC.
5. **La cobertura de genes es completa; la escala no es comparable:** en 15/20 genes
   RSF todos los valores ACRG están por debajo del mínimo TCGA. En cada uno de los
   cinco restantes, al menos el 94% también queda por debajo.
6. **Colapso de puntajes RSF externos:** 378 puntajes distintos en TCGA y solo 11 en
   300 pacientes ACRG; 288 empatan en la mediana. El corte produce 9 pacientes de
   bajo riesgo y 291 de alto riesgo; en I–II, 4 y 122. Los KM de esos grupos son
   muy desequilibrados y no constituyen evidencia de un umbral clínico válido.

El desplazamiento de expresión es compatible con que muchos pacientes ACRG sigan
rutas similares en los árboles. No se demuestra una causa biológica específica ni
se atribuye toda la caída externa a la plataforma: la CV TCGA ya mostró rendimiento débil.
La conclusión se refiere a estas firmas y este procesamiento, no a una superioridad
universal de LASSO sobre RSF.

## Comprobación final OOB, sin reentrenamiento

Se lee `RSF_resultados_para_comparacion.rds`, que contiene el bosque final, sus
salidas OOB y la clínica TCGA en el orden preservado. No basta con las tablas CSV
ni con un RDS de LASSO. No se llama a ranger(), glmnet(), predict() ni se recalculan genes.

Se usa el CHF OOB ya guardado por ranger. Para cada paciente, ese CHF se obtuvo con
los árboles que no lo incluyeron en su muestra de entrenamiento. Se mantiene el
mismo marcador `rowSums(CHF)`, calculando AUC al año y C de Harrell global.
Se contrasta el C OOB con `1 - prediction.error` del objeto ranger. Una discrepancia
se marca REVISAR_EMPATES para revisar alineación y tratamiento de tiempos empatados.
Se compara MD5 antes/después para comprobar que el RDS de entrada no se modificó.

**Límite central:** los genes y parámetros finales se eligieron usando TCGA. OOB
no valida independientemente esa selección; se informa como diagnóstico interno
condicionado al panel. Una caída aparente–OOB indica optimismo, pero un OOB alto
tampoco sustituiría una evaluación externa. No se calculan IC convencionales OOB
porque las predicciones comparten árboles y etapas de selección.

<!-- INICIO_RESULTADOS_OOB -->
**Comprobación ejecutada por el autor el 19/11/2026**, sobre el bosque ya guardado,
sin reentrenamiento: 378 pacientes, 20 genes y 1000 árboles.

| Evaluación RSF en TCGA global | AUC al año | C de Harrell |
|---|---:|---:|
| Aparente | 0.9514 | 0.8978 |
| OOB, condicionado al panel seleccionado | 0.6530 | 0.6197 |
| Diferencia aparente − OOB | 0.2984 | 0.2782 |

El AUC baja 0.2984 unidades de la escala 0–1 (29.84 puntos porcentuales de AUC,
no una reducción equivalente de precisión). Esto evidencia optimismo importante
en el rendimiento aparente; no significa que se haya corregido el sobreajuste.
El C usa todo el seguimiento y el AUC evalúa un año; no se interpretan como la misma métrica.

Las comprobaciones muestran cuatro PASS: CHF completo/finito, panel conservado,
filas clínicas preservadas y RDS de entrada conservado byte a byte.
**Una comprobación queda en REVISAR_EMPATES:** el C recalculado con survival difiere
de 1-prediction.error de ranger en **0.00044260028**. Es una discrepancia pequeña;
la causa concreta no está confirmada con los archivos agregados recibidos.
No se atribuye automáticamente a empates ni se declara que todos los checks pasaron.
El cálculo de AUC es separado y esta observación no modifica los valores de AUC reportados.

El panel y los parámetros se eligieron previamente con TCGA: este OOB puede
seguir siendo optimista y no valida independientemente la selección de genes.
La comparación externa principal sigue siendo ACRG global: AUC LASSO=0.656 y RSF=0.511.
No se equipara el AUC OOB RSF con el AUC aparente LASSO como si fueran evaluaciones equivalentes.

La CV previa (C medio=0.5159) repitió la selección dentro de los folds. OOB del
bosque final (C=0.6197) condiciona en el panel elegido con toda la cohorte; por eso
responden preguntas diferentes y no tienen que coincidir.

[Tabla OOB](resultados/tablas/oob/RSF_COMPROBACION_OOB_metricas.csv),
[comprobaciones](resultados/tablas/oob/RSF_COMPROBACION_OOB_checks.csv)
y [figura aparente/OOB](resultados/figuras/oob/RSF_ROC_aparente_vs_OOB_1anio.png).
<!-- FIN_RESULTADOS_OOB -->

## Reproducir la comprobación OOB ya realizada

Después de una ejecución completa, el estado RSF queda en
`data/privados/rsf/RSF_resultados_para_comparacion.rds`. El maestro lo encuentra
sin objetos precargados. Desde R:

```r
Sys.setenv(FMP_STAGE = "oob", FMP_INSTALL = "never", FMP_DOWNLOAD = "never")
source("Script_maerstro_FMP.R", encoding = "UTF-8")
```

Por terminal, desde la carpeta de entrega:

```bash
Rscript --vanilla Script_maerstro_FMP.R --stage=oob --install=never --download=never
```

Un estado ubicado en otra carpeta se indica con `--state="/ruta/RSF_resultados_para_comparacion.rds"`
o `FMP_RSF_STATE`. Se leen las predicciones CHF OOB ya guardadas; no se ajusta el
bosque. Figuras PDF/PNG: `resultados/figuras/oob/`; métricas y comprobaciones:
`resultados/tablas/oob/`; informe: `resultados/docs/README_oob.md`.
El README principal mantiene el resumen histórico y enlaza las salidas de la
última ejecución publicada. Los valores de esa ejecución se consultan en las tablas.

## Organizar una ejecución anterior sin recalcular

La etapa `organize` copia tablas, figuras, informes y estados RDS del formato
anterior al nuevo. **No instala paquetes, no descarga datos y no entrena modelos.**
Verifica por MD5 las copias de matrices/modelos y figuras; mantiene intactas las
carpetas originales. Incluye tanto el PDF como el PNG OOB cuando existen en origen.
No crea un PDF si solamente se recibió un PNG.

Desde R, con los dos scripts nuevos en la carpeta de entrega:

```r
Sys.setenv(
  FMP_STAGE = "organize",
  FMP_LEGACY_RUN = "resultados_replica_FMP/replica_20261120_114731",
  FMP_INSTALL = "never",
  FMP_DOWNLOAD = "never"
)
source("Script_maerstro_FMP.R", encoding = "UTF-8")
```

Por terminal:

```bash
Rscript --vanilla Script_maerstro_FMP.R --stage=organize --legacy-run="resultados_replica_FMP/replica_20261120_114731" --install=never --download=never
```

También se acepta `--legacy-run="resultados_replica_FMP"` si su
`ULTIMA_EJECUCION_COMPLETA.csv` apunta a carpetas existentes. Al trasladar la
entrega a otro equipo, las rutas absolutas del registro viejo pueden dejar de
existir; en ese caso se indica directamente la réplica LASSO completa, con su
RSF y OOB anidados. Si hay varias salidas posibles se solicita una ruta inequívoca,
sin seleccionar automáticamente una por fecha.

Los RDS originales se copian sin alterar sus bytes. Para que RSF pueda leer un
estado LASSO antiguo ya organizado se añade un índice adyacente con sus tablas
agregadas; no se sustituyen genes ni coeficientes. La procedencia de la copia queda
en `resultados/docs/migracion_origen.csv`.

## Ejecutar desde cero: CSV → descarga → modelos → evaluación

Se necesita R y acceso a internet. El instalador comprueba las versiones y la
carga real de los paquetes. Resuelve Depends, Imports y LinkingTo antes de
instalar; no incluye Suggests. Conserva los paquetes utilizables y no realiza
una actualización general. `--install=never` impide cualquier instalación.
Para R 4.4 usa los repositorios de Bioconductor 3.20 y CRAN. En macOS/Windows da
prioridad a binarios compatibles aunque exista una fuente más reciente; las
fuentes de datos o R puro se permiten cuando no hay binario. No fuerza fuentes
compiladas en esos sistemas ni instala R o compiladores del sistema operativo.
La instalación por dependencias se hace sin preguntas interactivas. No se fija
un lockfile completo: las versiones y errores se registran en `data/instalacion/`.
Consultar [instalación con R 4.4](docs/INSTALACION_R44.md) para comprobar solo los
paquetes antes de descargar las cohortes.

**Única entrada del usuario:** un CSV clínico ACRG, sin expresión génica.
Se admiten coma, punto y coma y tabulador. Mantener la unidad **meses** explícita.

| Formato del suplemento | Formato alternativo explícito |
|---|---|
| Tumor ID | patient_id (ID numérico que corresponde a GEO) |
| OS (months) | OS_months |
| FU status… (el encabezado largo original también se admite) | OS_event (0=censura, 1=muerte) |
| pStage | stage |

No mezclar FU status con OS_event en el mismo CSV. Los códigos FU 0/1 son censura,
2/3/4 muerte y 5 queda excluido como en el original. No se infieren unidades de
una columna llamada solamente OS_time. pStage/stage es necesario para interpretar
los subgrupos I–II; su ausencia deja el estadio desconocido.
La [plantilla](referencias/PLANTILLA_ACRG_clinical.csv) contiene solo encabezados.
El Excel original sigue admitido por compatibilidad.

Para ejecutar en R o RStudio, seguir el bloque de [inicio rápido](#inicio-rápido-en-otra-computadora-ejecutar-en-r-o-rstudio):
primero seleccionar el CSV, después fijar la configuración y finalmente ejecutar
el maestro. `FMP_ACRG_CLINICAL` establece su ubicación sin depender del nombre
o de una ruta guardada anteriormente.

Por terminal, desde la carpeta de entrega:

```bash
Rscript --vanilla Script_maerstro_FMP.R --stage=all --acrg-clinical="/ruta/ACRG.csv"
```

Los comandos que empiezan por **Rscript** se ejecutan en la terminal, no en la
consola de R. El maestro adquiere conteos y clínica TCGA y expresión GEO, guarda
las entradas y ejecuta preparación → LASSO → RSF → comparación → OOB.
Los objetos cvfit, x, y y los modelos se crean dentro del flujo.
El código de producción no carga pruebas ni resultados sintéticos.

Para guardar primero las descargas sin entrenar:

```bash
Rscript --vanilla Script_maerstro_FMP.R --stage=download --acrg-clinical="/ruta/ACRG.csv"
```

Después se ejecuta `--stage=all` con el mismo CSV: reutiliza los RDS descargados.
Una ejecución local con esas entradas se indica con `--download=never --install=never`.
`--data-dir` cambia la caché; `--output-dir` cambia la raíz pública de resultados.
Los modelos permanecen en `data/privados/` del proyecto.

| Etapa | Acción |
|---|---|
| install | Instala/comprueba dependencias; no requiere CSV ni descarga cohortes o entrena |
| download | Descarga entradas faltantes; no entrena |
| all | Prepara datos y ejecuta LASSO, RSF, comparación y OOB |
| lasso | Ejecuta LASSO; inicia un conjunto de salidas nuevo e invalida los estados RSF/OOB anteriores |
| rsf | Lee el estado LASSO existente; entrena RSF y ejecuta comparación/OOB |
| oob | Lee el estado RSF existente; comprueba OOB sin entrenar |
| organize | Copia una ejecución anterior al nuevo orden; no calcula modelos ni métricas |

En `rsf` y `oob`, los estados se buscan automáticamente en `data/privados/lasso/`
y `data/privados/rsf/`. `--state=RDS` permite indicar otro archivo. Para RSF se
conservan las tablas y figuras LASSO asociadas al estado; no se vuelve a ajustar
LASSO. No se usan objetos temporales de una sesión de pruebas.

La ejecución se prepara temporalmente dentro de `data/`. Al terminar todos los
bloques solicitados, se publica en `resultados/` y se escribe
`resultados/docs/ULTIMA_EJECUCION_COMPLETA.csv`. Un fallo previo a la publicación
conserva los resultados anteriores. Si falla el reemplazo de carpetas se intenta
restaurar inmediatamente el conjunto anterior; el error informa si alguna
restauración requiere atención manual. Se conserva **un único respaldo anterior**
en `data/respaldos/ultima_ejecucion/`; el siguiente reemplazo correcto rota ese
respaldo. Una ejecución `lasso` aislada deja solo sus resultados activos para no
mezclar ajustes de fechas distintas. `oob` conserva las salidas LASSO/RSF y cambia
solo su comprobación. Usar `data/` y `resultados/` en el mismo volumen.

**Límite de reproducibilidad:** instalar faltantes y consultar repositorios permite
ejecutar el procedimiento, pero no fija retrospectivamente versiones, releases
u orden de las entradas históricas. La coincidencia exacta requiere conservar los
archivos y el entorno utilizados; el control de firma lo informa.
El autor informó reproducción completa en su Mac el **20/11/2026** con la versión
anterior a esta reorganización. La ejecución con estas rutas nuevas está en curso,
según su reporte; su finalización y la comprobación por una segunda persona
quedan pendientes.

## Organización de la entrega — 20/11/2026

| Ruta | Contenido |
|---|---|
| Script_maerstro_FMP.R | Único punto de entrada; nombre solicitado por el autor |
| Funciones_fmp_comparacion.R | Preparación, adquisición, LASSO, RSF, evaluación y organización |
| data/raw/ | Descargas y CSV clínico ACRG; local, excluido de Git |
| data/privados/lasso/, rsf/, oob/ | Matrices, modelos, folds y puntajes individuales; excluidos de Git |
| data/respaldos/ultima_ejecucion/ | Un respaldo de la salida reemplazada; excluido de Git |
| resultados/figuras/lasso/, rsf/, comparacion/, oob/ | Figuras PDF/PNG de cada bloque |
| resultados/tablas/lasso/, rsf/, comparacion/, oob/ | Resultados agregados |
| resultados/docs/ | Configuraciones, informes, registro y una copia del código ejecutado |
| referencias/ | 216 genes, coeficientes confirmados y procedencia histórica |
| docs/ | Métodos, diccionario e instrucciones generales |
| tests/ | Pruebas de programación; no forman parte del análisis científico |

Se eliminan las subcarpetas fechadas de LASSO, RSF y OOB. Las fechas reales UTC
quedan en registros; la **fecha de esta versión es 2026-11-20**. Se mantienen las
fechas históricas y las semillas originales, que son parámetros numéricos.
Los dos scripts permanecen en la raíz. Esta reorganización no cambia el
preprocesamiento, la selección de genes, las semillas ni las fórmulas de evaluación;
los cambios de evaluación se limitan a nombres/rutas de archivos.
Los resultados agregados incluidos son los recibidos previamente, con sus bytes
conservados; el PNG OOB se reubicó en `figuras/oob/`. El PDF OOB de la ejecución
nueva del autor se incorporará con `organize` o en la próxima ejecución completa.
El código se mantiene en una rama separada de main.

## Figuras útiles para presentar

1. [LASSO: coeficientes](resultados/figuras/lasso/LASSO_coeficientes.png)
   e [importancia del panel RSF](resultados/figuras/rsf/RSF_importancia_panel.png): describen firmas con medidas distintas.
2. [ROC global ACRG](resultados/figuras/comparacion/ACRG_ROC_global_1anio.png):
   evidencia externa principal; acompañar de AUC e incertidumbre, sin declarar una diferencia significativa no probada.
3. KM global [LASSO ACRG](resultados/figuras/lasso/ACRG_KM_global.png)
   y [RSF ACRG](resultados/figuras/rsf/ACRG_KM_global.png): mostrar el desequilibrio de grupos RSF.
4. [ROC aparente/OOB de RSF](resultados/figuras/oob/RSF_ROC_aparente_vs_OOB_1anio.png):
   figura clave para explicar el optimismo, sin afirmar que la selección de genes quedó validada.

La [ROC global TCGA](resultados/figuras/comparacion/TCGA_ROC_global_1anio.png)
y los KM de desarrollo se etiquetan como aparentes. Trayectorias, CV y subgrupos I–II
pueden ir a material complementario. Las figuras originales conservan el formato de p
con muchos decimales; las tablas de este README los redondean solo para lectura.

## Entorno y pruebas de programación

Entorno de resultados confirmados: R 4.4.0, DESeq2 1.46.0, org.Hs.eg.db 3.20.0,
glmnet 4.1.10, survival 3.8.6, timeROC 0.4 y hgu133plus2.db 3.13.0.
Para el resultado histórico se reportó ranger 0.18.0 sin sessionInfo adjunto.
Cada nueva ejecución guarda automáticamente su versión efectiva en sessionInfo.

Dependencias del flujo completo: DESeq2, SummarizedExperiment, AnnotationDbi,
org.Hs.eg.db, glmnet, survival, ggplot2, survminer, GEOquery, Biobase, limma,
hgu133plus2.db, readxl, timeROC y ranger. La etapa oob solo requiere survival y timeROC. La adquisición agrega TCGAbiolinks cuando haga falta; para R 4.4 se consultan directamente los repositorios Bioconductor 3.20.
El inicio conserva paquetes utilizables, instala las dependencias necesarias y registra el entorno de cada
ejecución. No representa un lockfile exacto del entorno histórico.

```bash
Rscript --vanilla tests/test_funciones_puras.R
Rscript --vanilla tests/test_flujo_sesion_vacia.R
Rscript --vanilla tests/test_rsf_real.R
Rscript --vanilla tests/test_rsf_desde_archivo.R
Rscript --vanilla tests/test_oob_sin_reentrenar.R
Rscript --vanilla tests/test_descarga_y_csv.R
Rscript --vanilla tests/test_geo_https_y_reanudacion.R
```

Las seis pruebas originales pasaron en R 4.5.0/Linux, ranger 0.17.0 y survival 3.8-3, con datos
sintéticos. Se comprueban predicciones individuales, orden de genes, cobertura,
semillas, separación de folds, ejecución en sesión vacía y lectura OOB sin modificar
el RDS ni entrenar. En las pruebas del maestro, gráficos y timeROC se sustituyen por
dobles; la prueba OOB usa una AUC empírica exacta en una simulación sin censura antes
del año. No se ejecutó aquí timeROC real sobre cohortes de pacientes.
La nueva prueba de adquisición usa el maestro real en un proceso vacío, CSV real
sintético y servicios remotos/instalación simulados; comprueba caché, retorno
ExpressionSet explícito y reanudación parcial. No se descargó TCGA completo ni se
volvieron a entrenar las cohortes reales en este entorno.
Tras el primer fallo real en GEO se volvió a ejecutar la prueba de adquisición,
ahora simulando ese fallo después de guardar TCGA, y se añadió la prueba HTTPS:
ambas PASS. Se descargó además la matriz real NCBI y se verificó su gzip completo,
300 muestras y 54,675 filas de sondas. Esto no equivale a ejecutar aquí GEOquery
ni los modelos sobre esa matriz. Ver [VALIDACION_PROGRAMACION.md](VALIDACION_PROGRAMACION.md).

## Limitaciones y aciertos

**Aciertos documentados:** cohorte y genes alineados; tiempos explícitos en años;
réplica LASSO comprobada; pool de candidatos fijado antes de comprobar cobertura
externa; parámetros/semillas/folds guardados; métricas continuas separadas de KM;
IC de AUC y soporte de eventos disponibles; fallos de transporte conservados y
comprobaciones reproducibles sin forzar resultados favorables.

**Limitaciones:**

- Selección previa de GED y procesamiento global TCGA fuera de la CV; rendimiento aparente optimista.
- Selección de genes/hiperparámetros no validada de forma independiente por OOB.
- ACRG ya explorada; la evaluación externa es exploratoria, no ciega.
- Plataformas y escalas no armonizadas; se comparan procedimientos completos, no un efecto puro del algoritmo.
- Cortes relativos de cohorte; no hay un umbral clínico absoluto aplicable a un paciente aislado.
- Pocos eventos tempranos en I–II ACRG y grupos RSF externos muy desequilibrados.
- p de KM y HR después de selección de genes son exploratorios; no demuestran causalidad ni utilidad clínica.
- No se demostró calibración de probabilidades ni beneficio para decisiones terapéuticas.
- Los supuestos de riesgos proporcionales no se evaluaron formalmente en este flujo final.
- El entorno y los releases históricos no se recuperan retrospectivamente; las nuevas
  descargas sí registran procedencia y ensayo. La reproducción exacta exige entradas y versiones conservadas.

## Privacidad y preparación de la entrega

Los datos proceden de repositorios públicos; los identificadores, matrices clínicas,
conteos, RDS y predicciones individuales se mantienen fuera del repositorio.
No se incorporan credenciales. Revisar términos de uso de las fuentes antes de distribuir datos.
Las tablas y figuras incluidas son agregadas; se conservaron sus archivos de procedencia.

La entrega contiene código, referencias, resultados agregados, documentación y
pruebas técnicas. El autor confirmó el alcance del curso; no se añaden requisitos
ni nuevos análisis ajenos a la comparación pronóstica.
El registro exacto del entorno se genera automáticamente al ejecutar cada bloque.
Se conserva el historial de Swrfer/EE_CDB; la integración en main es un paso posterior.

## Declaración de uso de IA

ChatGPT/Codex apoyó la refactorización, programación, generación de documentación,
organización de archivos y pruebas técnicas con datos sintéticos. El autor ejecutó
los análisis con sus datos, revisó los resultados y definió el alcance científico.
Las decisiones de investigación, la interpretación y la responsabilidad del trabajo
corresponden al autor. La asistencia técnica no constituye validación clínica.

## Referencias y documentación primaria

- [Hörtenhuber et al. (2017): genes de señalización por Ca²⁺](https://doi.org/10.1093/bioinformatics/btx225).
- [TCGAbiolinks: descarga y preparación](https://bioconductor.org/packages/release/bioc/vignettes/TCGAbiolinks/inst/doc/download_prepare.html).
- [GEOquery: getGEO](https://seandavi.github.io/GEOquery/reference/getGEO.html).
- [Bioconductor: instalación](https://bioconductor.org/install/).
- [TCGA-STAD / GDC](https://portal.gdc.cancer.gov/projects/TCGA-STAD).
- [ACRG, GSE62254](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE62254).
- [GSM1523863: metadatos de procesamiento y señal RMA log10](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM1523863).
- [Cristescu et al.: estudio ACRG](https://doi.org/10.1038/nm.3850).
- [glmnet: modelos Cox penalizados](https://glmnet.stanford.edu/articles/Coxnet.html).
- [DESeq2: normalización y transformación](https://doi.org/10.1186/s13059-014-0550-8).
- [ranger: predicción OOB y C de Harrell](https://imbs-hl.github.io/ranger/reference/ranger.html).
- [timeROC: documentación del paquete](https://cran.r-project.org/package=timeROC).
- [Ambroise y McLachlan: sesgo por selección de genes](https://doi.org/10.1073/pnas.102102699).
- [TRIPOD: reporte y validación de modelos](https://doi.org/10.1136/bmj.g7594).
