# Validación técnica — 18/11/2026

Entorno de prueba: R 4.5.0, ranger 0.17.0 y survival 3.8-3, Linux.
Entorno histórico del autor: R 4.4.0/macOS; ranger 0.18.0 reportado por el autor.

## Pruebas ejecutadas

| Prueba | Resultado | Alcance |
|---|---|---|
| test_funciones_puras.R | PASS | Alineación de genes, puntajes, referencia, cortes, estadios y tiempo cero de ROC |
| test_flujo_sesion_vacia.R | PASS | Maestro LASSO por Rscript y source(), con dobles científicos y sin objetos globales |
| test_rsf_real.R | PASS | Ranger real: selección por folds, ajuste, semillas, puntajes individuales, orden de columnas, genes ausentes y dimensiones |
| test_rsf_desde_archivo.R | PASS | Maestro RSF en proceso vacío, RDS LASSO de entrada, ranger real y cobertura externa completa/incompleta |

La prueba RSF real comprueba que el mismo paciente reciba el mismo puntaje solo
o en lote y que el bosque se reproduzca con las mismas entradas y semillas.
Verifica separación de pacientes entre entrenamiento y validación de cada fold,
concordancia de 0.5 para un marcador constante y predicción con una sola fecha.
Comprueba diagnóstico del desplazamiento de escala entre entradas sintéticas.

La prueba de integración en etapa rsf no permite volver a entrenar LASSO y verifica
que su RDS permanezca intacto. También comprueba la etapa all: el maestro ejecuta
LASSO una vez y encadena RSF leyendo el resultado recién guardado. Comprueba las tablas conjuntas y que un gen seleccionado
ausente en ACRG no recorte la firma ni altere su entrenamiento; deja NA explícitos.
Las figuras y timeROC se sustituyen por dobles en esa prueba de integración.
Los tamaños de bosque se reducen exclusivamente en las pruebas para hacerlas rápidas.

## Límites de la validación

Los datos fuente reales TCGA/ACRG no están en este entorno. No se ejecutaron aquí
el ajuste real de esas cohortes ni sus figuras. Las pruebas no certifican una AUC,
una separación KM o una firma RSF determinada. Esas salidas deben revisarse después
de ejecutar el maestro con los archivos originales del autor.

El procedimiento LASSO se conserva. RSF parte del RDS creado automáticamente por
ese procedimiento, no de cvfit/x/y globales ni de la ejecución manual del usuario.
La publicación de esta entrega se mantiene en la rama entrega/fmp-final.

## Ampliación OOB — 19/11/2026

`tests/test_oob_sin_reentrenar.R`: **PASS**. Crea un bosque sintético con ranger real
y ejecuta el maestro en etapa oob desde un RDS en un proceso vacío. Prohíbe las
funciones de entrenamiento, verifica que rowSums(CHF) coincide con el OOB guardado
y que el C recalculado coincide con 1-prediction.error. Compara MD5 antes/después,
comprueba el rechazo de CHF ausente/no finito y panel desalineado, y confirma la
actualización del README sin alterar el texto fuera de sus marcadores.

En esa prueba, timeROC y figuras se sustituyen por dobles: la AUC de prueba se
calcula exactamente por comparación de pares en datos sintéticos sin censura
antes del año. El RDS real TCGA no se recibió en este entorno; el autor ejecutó
la comprobación en su equipo y sus resultados se documentan en la siguiente sección.

Se repitieron después de la integración las cuatro pruebas anteriores: **PASS**.
La prueba del maestro comprueba también all → LASSO → RSF → comprobación OOB.
Las etiquetas de ACRG se corrigieron a RMA log10, sin modificar cálculos ni modelos.

## Resultado OOB real recibido — 19/11/2026

El autor ejecutó la comprobación sobre su RDS y compartió las tablas y la figura.
AUC aparente/OOB: 0.9513947430 / 0.6529658444; C de Harrell: 0.8978423237 / 0.6196680498.
Se conservaron 378 pacientes, 20 genes, 1000 árboles y refit=FALSE.
Cuatro checks PASS y uno REVISAR_EMPATES (diferencia de C=0.00044260028).
La causa de esa discrepancia no está confirmada con las tablas agregadas; no se
considera una validación completa del panel ni se oculta la observación técnica.
Estos resultados provienen de la ejecución del autor, no de los datos sintéticos.

## Instalación, descarga y CSV — ampliación final

Se añadió test_descarga_y_csv.R y se ejecutaron las seis pruebas: PASS en R 4.5.0,
Linux, ranger 0.17.0 y survival 3.8-3. La prueba nueva comprueba la lectura CSV
(con coma, punto y coma, códigos FU y OS_event explícito), rechazo de unidades
ambiguas, caché atómica, retorno GEO ExpressionSet explícito y reanudación parcial.
Inicia el maestro real en un proceso --vanilla con solo un CSV local. Las llamadas
GDC/GEO y la instalación se sustituyen por servicios simulados exclusivamente en
la copia temporal del test. Los datos sintéticos no se exportan al proyecto.

Las cinco pruebas anteriores siguen pasando. El ajuste y evaluación científica
se conservan; los cambios se limitan a adquisición, instalación, CSV, procedencia
y orquestación. La selección del ensayo de nuevas descargas es unstranded y queda
registrada; no se atribuye retroactivamente ese ensayo al objeto histórico.
No se instaló aquí el entorno científico completo ni se descargó TCGA real.
La validación integral con datos vivos y el CSV del autor queda pendiente.

## Corrección de conexión GEO — 20/11/2026

El autor informó una descarga/preparación TCGA completada y un error de conexión
al iniciar getGEO(GSE62254). No se dispone de traceback para atribuir con certeza
la conexión interna concreta. Se reemplazó esa adquisición por descarga directa
HTTPS de la misma Series Matrix oficial y lectura local sin GPL adicional.
Las funciones de instalación, VST, LASSO, RSF y evaluación permanecen iguales.

- test_descarga_y_csv.R: PASS, incluido fallo GEO después de guardar TCGA y
  reanudación sin modificar las huellas de sus dos RDS.
- test_geo_https_y_reanudacion.R: PASS; rechaza HTML y gzip/tabla incompletos,
  reintenta, conserva un archivo anterior inválido y reutiliza una matriz válida.
- Descarga real desde NCBI por HTTPS en este entorno: 85,256,104 bytes;
  300 muestras, 54,675 sondas, gzip leído hasta EOF y marcador de fin de tabla.
  MD5 observado: be14c49340c65d7b16dfd072d178622c.
- El validador R de producción aceptó esa matriz real. No se ejecutó el parser
  GEOquery ni se instalaron paquetes ni se ajustaron modelos reales aquí.

El nuevo transporte evita el listado automático de GEO y la descarga GPL. No
prueba que esas fueran necesariamente las causas del mensaje original.

## Organización compartida — 20/11/2026

El autor informó ejecución integral correcta en su Mac tras la corrección GEO.
Esta versión cambia la organización y los nombres de los dos scripts. No se han
vuelto a descargar cohortes, instalado paquetes ni entrenado modelos en esta revisión.
La reproducción completa de la versión reorganizada y la réplica independiente
por una compañera del laboratorio quedan pendientes.

Resultado: **seis pruebas PASS**, más comprobación de sintaxis y estructura.

Pruebas de esta revisión: funciones puras; maestro LASSO por Rscript/source en
sesión vacía; descarga/CSV y GEO con servicios simulados; organización/transacciones;
RSF desde RDS y flujo all con FMP_TEST_NO_FIT=true. Los pasos de ajuste se sustituyen
por dobles exclusivamente en las copias temporales de las pruebas.
No se ejecutan las pruebas que ajustan bosques reales en esta revisión.
La prueba de organización verifica copia MD5 de figuras OOB PDF/PNG, conservación
de los estados originales, ausencia de anidamientos, respaldo único, fallo antes
de publicar y restauración tras un fallo durante la publicación.
La comprobación estructural compara los cuerpos de las funciones científicas con
el ZIP recibido: el ajuste, las semillas, las transformaciones y los cálculos
OOB se mantienen. Las funciones de figuras/evaluación cambian solo sus rutas.

Se verificaron además 44 tablas/figuras históricas conservadas byte a byte y los enlaces locales del README.
