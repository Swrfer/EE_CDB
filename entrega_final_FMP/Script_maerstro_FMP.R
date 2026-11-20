# Entrega: 2026-11-20.
# UNICO PUNTO DE ENTRADA: LASSO-Cox confirmado y RSF.
# R interactivo: source(file.choose(), encoding = "UTF-8") y elegir ESTE archivo.
# Terminal: Rscript --vanilla Script_maerstro_FMP.R --acrg-clinical="/ruta/ACRG.csv"
# El archivo de funciones se carga automaticamente. No ejecutar bloques manuales.

resultado_fmp <- local({
  # 1. Encontrar el proyecto a partir de este archivo, no del directorio de R.
  archivos <- Filter(function(z) is.character(z) && length(z) == 1L,
    lapply(sys.frames(), function(e) e$ofile))
  args_r <- commandArgs(trailingOnly = FALSE)
  archivo_maestro <- if (length(archivos)) tail(archivos, 1L)[[1L]] else {
    sub("^--file=", "", args_r[grepl("^--file=", args_r)])[1L]
  }
  if (is.na(archivo_maestro) || !file.exists(archivo_maestro)) {
    stop("Ejecuta este archivo completo mediante source() o Rscript.")
  }
  base <- dirname(normalizePath(archivo_maestro))

  # 2. Cargar funciones en un entorno propio. No se buscan cvfit, x o y
  # en la sesion del usuario: todos se crearan dentro del flujo.
  modulo <- new.env(parent = environment())
  source(file.path(base, "Funciones_fmp_comparacion.R"), local = modulo,
    encoding = "UTF-8")

  # 3. Elegir la etapa: all (descarga y analisis), download, lasso, rsf, oob u organize.
  # Sys.setenv(FMP_STAGE="oob") ejecuta SOLO la comprobacion del bosque
  # ya guardado en RSF_resultados_para_comparacion.rds. No entrena modelos.
  # Sys.setenv(FMP_STAGE="rsf") permite ejecutar solo el nuevo bloque,
  # leyendo el RDS final producido automaticamente por LASSO.
  # Para todo desde cero: Sys.setenv(FMP_STAGE="all").
  # La unica entrada local es el CSV clinico ACRG. Las referencias van incluidas.
  # El inicio instala paquetes faltantes y descarga TCGA/GEO si faltan sus RDS.
  # Las descargas quedan en data/raw/; despues se reutilizan sin cambiar sus bytes.
  # FMP_ACRG_CLINICAL o --acrg-clinical= indican el CSV; en R se puede seleccionar.
  # --install=never y --download=never permiten una ejecucion offline con cache.
  # La consulta nueva registra fecha, ensayo unstranded y archivos GDC disponibles.
  cfg <- modulo$fmp_configuracion(base, argumentos = commandArgs(trailingOnly = TRUE))

  # organize importa una ejecucion anterior con FMP_LEGACY_RUN, sin red ni ajustes.
  # Todos los bloques comparten resultados/{figuras,tablas}/{lasso,rsf,comparacion,oob}.
  # 4. El inicio descarga/instala antes de entrar al analisis.
  # El bloque LASSO conserva el procedimiento que ya se comprobo:
  # - fmp_importar_tcga(): alinear conteos crudos y clinica.
  # - fmp_preparar_tcga(): filtro, VST original y anotacion; produce x e y.
  # - fmp_ajustar_lasso(): cv.glmnet, semilla 123, 10 folds, lambda.min.
  # - fmp_figuras_lasso(): CV, trayectoria de ocho genes y coeficientes.
  # - fmp_evaluar(): KM global/I-II, C de Harrell y timeROC de TCGA.
  # - fmp_importar_acrg(): normalizacion original y puntaje congelado.
  # - fmp_evaluar(): los mismos resultados externos en ACRG.
  # 5. El bloque RSF lee esas mismas entradas preparadas. Selecciona genes
  # y parametros SOLO en TCGA usando los folds guardados por LASSO.
  # Congela el bosque y luego comprueba cobertura y predice en ACRG.
  # Produce importancia, KM global/I-II, C de Harrell y timeROC al anio.
  # Finalmente reune tablas y curvas ROC de ambos modelos, sin modificar LASSO.
  # En la etapa oob se omiten los bloques de entrenamiento: se lee CHF OOB,
  # se compara su AUC/C con los aparentes y se guarda resultados/docs/README_oob.md.
  modulo$ejecutar_proyecto_fmp(cfg)
})

# El unico objeto de salida contiene todo lo generado en esta ejecucion:
# resultado_fmp$lasso$cvfit, resultado_fmp$tcga$x, resultado_fmp$tcga$y,
# resultado_fmp$KM_Cindex, resultado_fmp$timeROC y resultado_fmp$folders.
# Los datos/modelos quedan en data/privados/lasso|rsf|oob; no publicar data/.
# La nueva salida RSF queda en resultado_fmp$rsf; sus rutas, en $rsf$folders.
