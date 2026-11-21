# Referencias de entrada

Estos archivos forman parte de la definición del análisis. No son salidas de la
ejecución que se realizará al descomprimir la entrega.

| Archivo | Función |
|---|---|
| `216_GED.csv` | Lista fija de genes candidatos para ambos modelos |
| `LASSO_Cox_signature_lambda_min_confirmada_8genes.csv` | Genes y coeficientes para verificar la reconstrucción LASSO |
| `PLANTILLA_ACRG_clinical.csv` | Encabezados para preparar la entrada clínica; sin datos de pacientes |

## Origen de los candidatos

Los 216 genes derivan de un análisis transcriptómico multicohorte previo que
integró tres datasets GEO y TCGA-STAD. Se comparó cáncer gástrico en estadios
I–II frente a tejido gástrico control y se filtraron los genes del contraste
por los reportados por Hörtenhuber et al. (2017) como relacionados con Ca²⁺.
Referencia: [10.1093/bioinformatics/btx225](https://doi.org/10.1093/bioinformatics/btx225).

La repetición de ese análisis diferencial no forma parte de este proyecto.
TCGA participó en esa selección previa, lo cual limita la independencia del
desarrollo y de sus evaluaciones internas posteriores.

## Referencia LASSO

La referencia contiene VCAN, KCNQ1, SPARC, PRKCG, MATN3, SYT4, HTR2C y MYL4.
El maestro vuelve a ajustar LASSO con los datos TCGA y compara los genes y
coeficientes estimados con esta referencia, con tolerancia absoluta `1e-6`.
No usa el CSV para puntuar en lugar del ajuste ni modifica el ajuste para que
coincida. Si hay discrepancia, se detiene y guarda su diagnóstico.

Este control verifica la reconstrucción de la firma. No convierte sus AUC,
curvas de supervivencia ni evaluaciones externas en resultados predefinidos:
se calculan con los datos de cada ejecución.

## Entrada clínica

La plantilla contiene solo encabezados. Debe completarse con el suplemento
clínico real de ACRG y respetar las unidades y la codificación del estado vital
descritas en el README principal. El archivo clínico real se proporciona por
separado y no debe incorporarse al repositorio de código.
