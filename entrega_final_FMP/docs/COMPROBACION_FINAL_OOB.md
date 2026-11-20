# Última comprobación: OOB sin reentrenar

1. Descomprimir completa la carpeta del proyecto.
2. En una sesión nueva de R, ejecutar:

```r
Sys.setenv(FMP_STAGE = "oob")
source(file.choose(), encoding = "UTF-8")
```

3. Elegir ejecutar_replica_fmp.R; el archivo de funciones se carga automáticamente.
4. Elegir RSF_resultados_para_comparacion.rds, de data_privada/ de la ejecución RSF.
5. Revisar la tabla aparente/OOB y las comprobaciones impresas. Un REVISAR_EMPATES
   requiere revisión antes de interpretar ese C; no se oculta ni fuerza una coincidencia.
6. El maestro crea tablas, ROC PDF/PNG y README propio en comprobacion_OOB/OOB_.../.
   También reemplaza solo la sección OOB del README del proyecto.

No usar RSF_modelo_final.rds: ese objeto aislado no incluye la clínica alineada.
No usar FMP_original_replicada_para_comparacion.rds: es el resultado LASSO.
No ejecutar stage=all en esta comprobación: all sí vuelve a construir ambos modelos.

El marcador es rowSums(CHF), como el del análisis principal. No se cambia a una
probabilidad al año, no se eligen genes ni se ajustan parámetros. La comprobación
lee bosque$chf, no predict(bosque, datos_TCGA), que volvería a producir el marcador
aparente con todos los árboles.

OOB evalúa internamente el bosque condicionado al panel ya seleccionado con TCGA.
No valida de forma independiente la selección de genes ni corrige retrospectivamente
el sobreajuste. Tampoco resuelve el cambio de escala entre RNA-seq y microarreglos.

Para revisar la salida y cerrar la entrega basta compartir la tabla agregada
RSF_COMPROBACION_OOB_metricas.csv y RSF_COMPROBACION_OOB_checks.csv. No hace falta
publicar el RDS, los identificadores ni los puntajes individuales.
