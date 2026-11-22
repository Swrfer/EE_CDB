# Auditoría de unidades

## Resultados cuantitativos

| loinc | analito | unit_concept_id | unidad | codigo_ucum | mediciones | pacientes | porcentaje_unidad_0_nula | minimo | mediana | maximo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2160-0 | Creatinine [Mass/volume] in Serum or Plasma | 8840 | milligram per deciliter | mg/dL | 35354 | 1059 | 0.0 | 0.4 | 2.0 | 20.5 |
| 2345-7 | Glucose [Mass/volume] in Serum or Plasma | 8840 | milligram per deciliter | mg/dL | 35354 | 1059 | 0.0 | 64.0 | 86.1 | 200.0 |
| 4548-4 | Hemoglobin A1c/Hemoglobin.total in Blood | 8554 | percent | % | 46481 | 2462 | 0.0 | 1.9 | 4.2 | 10.3 |

## Veredicto por analito

| loinc | analito | veredicto |
| --- | --- | --- |
| 4548-4 | HbA1c | Sí, en esta base: todas las mediciones usan %. No mezclar con mmol/mol IFCC sin conversión. |
| 2160-0 | Creatinina | Sí, en esta base: todas usan mg/dL. No mezclar con µmol/L; el factor aproximado es 88.4. |
| 2345-7 | Glucosa | Sí, en esta base: todas usan mg/dL. Convertir mmol/L antes de combinar si apareciera. |

Los histogramas se generaron separados por `unit_concept_id`. En esta base cada analito presenta una sola unidad y 0% de unidades nulas o no mapeadas, por lo que sus valores pueden resumirse dentro de cada analito tal como están. Esta limpieza no debe generalizarse a una base real.

## Figuras

- `figuras/histograma_hba1c_por_unidad.png`
- `figuras/histograma_creatinina_por_unidad.png`
- `figuras/histograma_glucosa_por_unidad.png`

## Fuentes

- [LOINC 4548-4](https://loinc.org/4548-4)
- [LOINC 2160-0](https://loinc.org/2160-0)
- [LOINC 2345-7](https://loinc.org/2345-7)
