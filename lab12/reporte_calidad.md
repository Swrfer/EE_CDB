# Reporte de calidad — Laboratorio 12

## 1. Ruta de conversión

Se eligió **ETL-Synthea**, el paquete de OHDSI orientado a transformar CSV de
Synthea al OMOP CDM. Esta ruta conserva reglas de mapeo reproducibles y evita
construir manualmente cada tabla clínica.

La fuente se generó con Synthea `v3.4.0-18-ga07a65555`. Se comprobó que las 18
tablas de entrada tenían las columnas esperadas por la implementación compatible
con Synthea 3.3.0.

## 2. Implementación

- OMOP CDM: 5.4.
- ETLSyntheaBuilder: 2.1.
- DatabaseConnector: 7.1.0.
- SqlRender: 1.19.4.
- DuckDB de R: 1.5.0.
- Java: 17.0.18.
- Personas convertidas: 5,745.
- Conceptos: 2,026,160.
- Conceptos estándar: 846,202.

Se cargaron los vocabularios SNOMED, ICD10CM, RxNorm, LOINC y ATC, incluidas
`CONCEPT`, `CONCEPT_RELATIONSHIP` y `CONCEPT_ANCESTOR`.

## 3. Conteos de tablas

| tabla | filas |
| --- | --- |
| concept | 2026160 |
| concept_ancestor | 12073517 |
| concept_relationship | 14129144 |
| condition_occurrence | 92084 |
| drug_exposure | 280617 |
| measurement | 3111032 |
| observation | 1596434 |
| observation_period | 5745 |
| person | 5745 |
| procedure_occurrence | 385657 |
| visit_occurrence | 320853 |

## 4. Calidad del mapeo

| dominio | eventos | personas | concept_id_cero | porcentaje_concept_id_cero |
| --- | --- | --- | --- | --- |
| Condition | 92084 | 5655 | 0 | 0 |
| Drug | 280617 | 5461 | 0 | 0 |
| Measurement | 3111032 | 5744 | 0 | 0 |
| Observation | 1596434 | 5745 | 0 | 0 |
| Procedure | 385657 | 5730 | 0 | 0 |
| Visit | 320853 | 5745 | 0 | 0 |

El mayor porcentaje de `concept_id = 0` correspondió a **Condition**
con **0.0%**. Estos eventos pueden perderse en
silencio al definir cohortes exclusivamente con conceptos estándar.

## 5. Caracterización de la población

### Sexo

| sexo | personas | porcentaje |
| --- | --- | --- |
| Sin concepto legible | 5745 | 100 |

La mediana de observación fue de **11516.0 días** por
persona y la media de **11970.85 días**.

### Diagnósticos más frecuentes

| concept_id | concept_name | eventos | personas |
| --- | --- | --- | --- |
| 4281516 | Gingivitis | 10343 | 4680 |
| 40481087 | Viral sinusitis | 5960 | 3684 |
| 4172829 | Limited social contact | 5931 | 3111 |
| 4309238 | Social isolation | 5857 | 3115 |
| 133228 | Dental caries | 4142 | 3079 |
| 4112343 | Acute viral pharyngitis | 3399 | 2580 |
| 4060985 | Body mass index 30+ - obesity | 2800 | 2800 |
| 260139 | Acute bronchitis | 2789 | 2224 |
| 4217975 | Normal pregnancy | 2552 | 1068 |
| 37018196 | Prediabetes | 2175 | 2175 |
| 439777 | Anemia | 2127 | 2127 |
| 4122116 | Tooth eruption disorder | 1455 | 1336 |
| 4059650 | Risk activity involvement | 1451 | 1356 |
| 320128 | Essential hypertension | 1355 | 1355 |
| 436096 | Chronic pain | 1340 | 1340 |
| 257012 | Chronic sinusitis | 1163 | 1162 |
| 435081 | Abnormal findings diagnostic imaging heart+coronary circulat | 979 | 979 |
| 4132891 | Chronic low back pain | 975 | 975 |
| 4185932 | Ischemic heart disease | 969 | 969 |
| 372328 | Otitis media | 900 | 657 |

### Visitas

| personas | visitas | media_visitas_por_persona | mediana_visitas_por_persona |
| --- | --- | --- | --- |
| 5745 | 320853 | 55.8491 | 36 |

| concept_id | tipo_visita | visitas | personas | media_visitas_por_persona |
| --- | --- | --- | --- | --- |
| 9202 | Outpatient Visit | 301349 | 5745 | 52.4541 |
| 9203 | Emergency Room Visit | 12938 | 4065 | 3.1828 |
| 9201 | Inpatient Visit | 6566 | 2714 | 2.4193 |

## 6. Concepto estándar frente a origen

| concept_id | concept_name | eventos_estandar | personas_estandar | codigo_origen_mas_frecuente | eventos_origen | personas_origen | diferencia_eventos | diferencia_porcentaje |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4281516 | Gingivitis | 10343 | 4680 | 66383009 | 10343 | 4680 | 0 | 0 |

Para **Gingivitis** (`concept_id = 4281516`) se
contaron **10343 eventos** por concepto estándar, frente a
**10343** para el código fuente más frecuente
(`66383009`). En esta base ambos conteos coinciden porque la condición seleccionada apareció con un solo código de origen. Esto no contradice OMOP: en otras fuentes varios códigos pueden converger en el mismo concepto estándar, mientras que los códigos sin mapeo se representan con `concept_id = 0`.

## 7. Ventana de observación

| eventos_sin_filtrar | eventos_dentro_observacion | eventos_fuera_observacion | diferencia_porcentaje | personas_sin_filtrar | personas_dentro_observacion |
| --- | --- | --- | --- | --- | --- |
| 92084 | 91385 | 699 | 0.7591 | 5655 | 5655 |

Sin filtrar se contaron **92084.0 eventos** y dentro de
la ventana quedaron **91385.0**. La diferencia
fue **0.7591%**. Ignorar `OBSERVATION_PERIOD` puede
incluir eventos fuera del seguimiento y sesgar denominadores, incidencia y
tiempo hasta evento.

## 8. Conceptos revisados para ATHENA

| concept_id | concept_name | vocabulary_id | domain_id | standard_concept | eventos | personas | conceptos_hijos | codigo_origen_ejemplo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4281516 | Gingivitis | SNOMED | Condition | S | 10343 | 4680 | 76 | 66383009 |
| 40481087 | Viral sinusitis | SNOMED | Condition | S | 5960 | 3684 | 1 | 444814009 |
| 4172829 | Limited social contact | SNOMED | Condition | S | 5931 | 3111 | 1 | 423315002 |

Los descendientes se calcularon con `CONCEPT_ANCESTOR`; el código de origen es
el más frecuente observado para cada concepto estándar.

## 9. Simplificaciones documentadas

1. Se corrigió la materialización inicial del vocabulario dentro del esquema
   `cdm` antes de construir los mapas.
2. Los campos `*_datetime` afectados se dejaron nulos porque la fuente aporta
   fechas sin hora verificable; los campos `*_date` se conservaron.
3. `condition_era`, `drug_era`, `device_exposure`, `death`,
   `payer_plan_period` y `cost` no se materializaron porque no intervienen en
   las consultas exigidas y presentaron incompatibilidades específicas con
   DuckDB.

## 10. Comparación con Eunomia

| metrica | synthea_propio | eunomia |
| --- | --- | --- |
| Personas | 5745 | 2694 |
| Categorías de sexo | 1 | 2 |
| Mediana de días de observación | 11516 | 13868 |
| Visitas | 320853 | 1037 |
| Media de visitas por persona | 55.8491 | 0.3849 |
| Diagnóstico más frecuente | Gingivitis | Viral sinusitis |
| Eventos del diagnóstico más frecuente | 10343 | 17268 |

Eunomia se utilizó como base OMOP de demostración. La base propia contiene una población mayor y una densidad de visitas distinta. También cambia el diagnóstico dominante, porque ambas bases fueron generadas para escenarios clínicos diferentes. La semejanza estructural con OMOP no implica igualdad en distribución de enfermedades, seguimiento o utilización de servicios.
