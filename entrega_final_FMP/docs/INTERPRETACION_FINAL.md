# Interpretación final para el proyecto

En 378 pacientes TCGA-STAD, el RSF de 20 genes mostró un AUC aparente al año
de 0.951 y C de Harrell de 0.898. Al utilizar sus predicciones OOB existentes,
sin reentrenar ni alterar el panel, el AUC fue 0.653 y el C fue 0.620. La caída
evidencia optimismo considerable del desempeño aparente. La evaluación OOB
condiciona en genes y parámetros escogidos con TCGA y puede seguir siendo optimista.

En los 300 pacientes ACRG, la firma LASSO-Cox de ocho genes conservó una
discriminación modesta (AUC al año 0.656; C 0.630), mientras RSF mostró AUC 0.511
y C 0.502. Esta comparación se refiere a las firmas y al procesamiento utilizados.
El desplazamiento VST/RMA log10 y el colapso de puntajes RSF externos impiden
atribuir toda la diferencia exclusivamente al algoritmo. No se demostró utilidad
clínica ni superioridad estadística mediante una prueba pareada de diferencia de AUC.

La CV TCGA (C medio 0.516) evalúa un procedimiento que selecciona genes dentro
de cada fold; el OOB (C 0.620) evalúa el bosque condicionado al panel final
seleccionado con toda la cohorte. No son estimaciones intercambiables.
No se compara OOB RSF con el AUC aparente LASSO para declarar empate o superioridad.

## Nota técnica conservada

El C OOB recalculado y 1-prediction.error de ranger difieren en 0.00044260028.
El check REVISAR_EMPATES es una señal de revisión, no una confirmación de la causa.
La discrepancia es pequeña, no cambia el AUC calculado por timeROC y se mantiene
visible para el profesor. Los demás checks de estructura y conservación del RDS pasaron.

## Qué se mantiene

Las dos firmas finales, sus genes/coeficientes o árboles, las evaluaciones externas
y los resultados originales. OOB se añade como diagnóstico interno complementario,
sin corrección ni optimización adicional del modelo.
