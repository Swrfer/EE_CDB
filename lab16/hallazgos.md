# Hallazgos de jerarquías OMOP

## 1. Recursiva frente a CONCEPT_ANCESTOR

La recursiva de `Type 2 diabetes mellitus` encontró **9 ancestros distintos** y
`CONCEPT_ANCESTOR` encontró **8**. Coinciden en los ocho ancestros clínicos. La
diferencia es `SNOMED CT Concept` (`4008453`), raíz técnica no estándar alcanzada
por las aristas `Is a`, pero omitida de la clausura clínica precomputada.

## 2. RELATIONSHIP

| tipos_relacion | jerarquicas | definen_ancestria | ambas | solo_jerarquicas | solo_ancestria |
| --- | --- | --- | --- | --- | --- |
| 724 | 124 | 63 | 55 | 69 | 8 |

Los conjuntos no coinciden: una relación puede describirse como jerárquica para
navegación sin participar en la construcción de `CONCEPT_ANCESTOR`, y algunas
relaciones de ancestría se usan para normalización entre vocabularios aunque no
se marquen como jerárquicas.

### Cinco relaciones de lisinopril

| relationship_id | explicacion |
| --- | --- |
| RxNorm ing of | Conecta el ingrediente con productos y formas que lo contienen; sí define ancestría. |
| Has brand name | Relaciona el ingrediente con nombres comerciales; es jerárquica en metadatos, pero no define CONCEPT_ANCESTOR. |
| Mapped from | Muestra conceptos no estándar que se normalizan hacia lisinopril en sentido inverso a Maps to. |
| RxNorm - ATC pr lat | Enlace lateral primario entre RxNorm y una clase o combinación ATC; no es una relación de descendencia. |
| Has form | Vincula el ingrediente general con una forma precisa, como lisinopril anhidro. |

## 3. Caso real de poli-jerarquía

El par seleccionado fue `Disease` (`4274025`) ← `Gingivitis` (`4281516`).
`CONCEPT_ANCESTOR` reporta una distancia mínima de 4 y máxima de 8; la recursiva
reconstruyó **13 caminos**. Dos rutas representativas son:

1. Gingivitis -> Inflammatory disorder of jaw region -> Inflammatory disorder of head -> Disorder of head -> Disease
2. Gingivitis -> Inflammatory disorder of digestive tract -> Inflammatory disorder of digestive system -> Inflammation of specific body systems -> Disorder of body system -> Disease

Clínicamente tiene sentido: la gingivitis es simultáneamente una inflamación de
tejidos de la cabeza/mandíbula y una enfermedad de la cavidad oral, que SNOMED
también organiza dentro del tracto digestivo. No son duplicados erróneos, sino
clasificaciones válidas desde perspectivas anatómicas y patológicas diferentes.

## 4. Daño del solapamiento

| conteo_A_filas_join | conteo_B_conceptos | conteo_C_pacientes | eventos_unicos | filas_duplicadas_por_solapamiento |
| --- | --- | --- | --- | --- |
| 327 | 2 | 165 | 165 | 162 |

Las ramas `Heart failure` y `Chronic congestive heart failure` se solapan. El
`COUNT(*)` cuenta nuevamente los eventos que pertenecen a ambas ramas; el conteo
de conceptos responde cuántos diagnósticos estándar distintos aparecen, y solo
`COUNT(DISTINCT person_id)` responde cuántos pacientes tienen la condición.

## 5. Conceptos retirados

| conceptos_retirados | conceptos_D | conceptos_U | pacientes_antes | pacientes_despues | diferencia_pacientes |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 457 | 457 | 0 |

El concept set razonado de diabetes tipo 2 no contiene conceptos `D` ni `U`.
Por ello no hay reemplazos que aplicar y el número permanece en 457 pacientes.
La consulta queda generalizada en `jerarquias.sql` para detectar cambios en una
futura versión del vocabulario.

## 6. Trazabilidad de pacientes

Se documentaron los pacientes `1456`, `1112` y `635`. El tercero fue escogido
mediante una selección independiente del flujo principal. En esta base los tres
entran directamente por `Type 2 diabetes mellitus`; la consulta parametrizable
también funciona si un evento entra por un descendiente del concept set.
