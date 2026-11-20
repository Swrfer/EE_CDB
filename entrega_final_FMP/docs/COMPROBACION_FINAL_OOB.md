# Comprobación final OOB — entrega 20/11/2026

Esta etapa usa el bosque ya guardado y sus predicciones CHF OOB. No vuelve a
entrenar ni cambia el panel. Su rendimiento sigue condicionado por la selección
previa de genes y parámetros; no valida de forma independiente toda la firma.

Desde una sesión nueva de R en la carpeta del proyecto:

```r
Sys.setenv(FMP_STAGE="oob", FMP_INSTALL="never", FMP_DOWNLOAD="never")
source("Script_maerstro_FMP.R", encoding="UTF-8")
```

Se localiza automáticamente
`data/privados/rsf/RSF_resultados_para_comparacion.rds`. Si está en otra ruta,
indicarla con `FMP_RSF_STATE` o con `--state=RDS` por terminal.
No ejecutar `all` para esta comprobación: esa etapa sí construye ambos modelos.

Salidas:

- `resultados/figuras/oob/`: ROC aparente/OOB en PDF y PNG.
- `resultados/tablas/oob/`: métricas, diferencias y comprobaciones.
- `resultados/docs/README_oob.md`: interpretación de esta ejecución.
- `data/privados/oob/`: predicciones y objetos ROC; no publicar.

Se verifica el MD5 del estado RSF antes y después. Se conserva un único respaldo
de los archivos reemplazados al publicar. La sección histórica del README principal
mantiene sus valores recibidos; las tablas enlazadas muestran la última ejecución.
