# Justificación del concept set — diabetes tipo 2

## Pregunta y condición

La condición final es **diabetes mellitus tipo 2 activa en población general adulta**. La cohorte servirá para estudiar resultados metabólicos y uso de servicios en personas con diabetes tipo 2. Inicialmente se evaluó cáncer gástrico, pero el concepto estándar correspondiente solo capturó **2 pacientes**, por debajo del mínimo operativo de 50; por eso se cambió de forma explícita a diabetes tipo 2, con **457 pacientes**.

## Concepto semilla

El concepto semilla es **Type 2 diabetes mellitus** (`concept_id = 201826`, código SNOMED `44054006`). Es estándar (`S`), vigente, del dominio `Condition` y clase `Disorder`. Su padre inmediato es **Diabetes mellitus** (`201820`). Tiene **14 descendientes** estándar vigentes en la jerarquía disponible.

## Decisiones clínicas

| concept_id | nombre | incluido | por qué |
| --- | --- | --- | --- |
| 43531010 | Pre-existing type 2 diabetes mellitus in pregnancy | No | La diabetes preexistente en embarazo pertenece al contexto obstétrico excluido. |
| 4129519 | Pregnancy and type 2 diabetes mellitus | No | La diabetes asociada al embarazo es un contexto obstétrico distinto de la cohorte general adulta. |
| 45766052 | Type 2 diabetes mellitus in remission | No | La remisión no representa enfermedad activa para la pregunta de investigación. |
| 37163431 | Ketosis-resistant diabetes mellitus | Sí | Forma resistente a cetosis incluida como subtipo de diabetes tipo 2. |
| 4063043 | Pre-existing type 2 diabetes mellitus | Sí | Diabetes tipo 2 preexistente; conserva la entidad clínica de interés. |
| 4099651 | Type 2 diabetes mellitus with ulcer | Sí | La úlcera es una complicación, pero el paciente conserva diabetes tipo 2 activa. |

Se revisaron **todos los 14 descendientes disponibles**. El enunciado solicita 20, pero la rama completa contiene menos de 20; una muestra de 20 habría requerido duplicar elementos. La revisión exhaustiva es más informativa y elimina error de muestreo. La semilla fija prevista era `20261122`, aunque no fue necesario muestrear.

## Versiones y efecto en la cohorte

| version | conceptos | pacientes_distintos | eventos | diferencia_pacientes_vs_A | diferencia_porcentual_vs_A |
| --- | --- | --- | --- | --- | --- |
| A_estricta | 1 | 457 | 457 | 0 | 0.0 |
| B_amplia | 15 | 457 | 457 | 0 | 0.0 |
| C_razonada | 12 | 457 | 457 | 0 | 0.0 |

La versión A contiene únicamente el concepto semilla; la B añade todos los descendientes; la C excluye el contexto obstétrico y la remisión. Aunque el número de conceptos cambia de **1** a **15** y luego a **12**, las tres versiones capturan **457 pacientes**. Esto ocurre porque en esta instancia de Synthea los eventos observados usan el concepto semilla y ninguno de sus descendientes; no significa que las definiciones sean equivalentes en otra base OMOP.

## Sensibilidad y valor predictivo positivo

La versión B maximiza sensibilidad, pero admite embarazo y remisión, entidades que no responden a la pregunta sobre diabetes tipo 2 activa en población general. La versión C favorece el valor predictivo positivo al retirar esos contextos y puede perder algunos casos verdaderos con codificación ambigua. Para esta pregunta, incluir casos obstétricos o en remisión distorsionaría más la interpretación que perderlos, por lo que se adopta **C — razonada** como definición final. En una base real se validaría el balance con revisión clínica de expedientes.

## Traducción ICD-10-CM

Se tradujeron 12 códigos con la relación `Maps to`, respetando dirección, estándar del destino y vigencia de conceptos y relación. Hubo **11 códigos 1:N**, **0 sin mapeo** y **23 filas** después del join. Los conteos epidemiológicos no deben hacerse directamente sobre esas filas porque un código puede producir varios conceptos estándar.

## Fuentes

- [ATHENA — OHDSI](https://athena.ohdsi.org/), metadatos, jerarquías y relaciones del vocabulario descargado.
- [OMOP CDM v5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html), estructura de `CONCEPT`, `CONCEPT_RELATIONSHIP` y `CONCEPT_ANCESTOR`.
