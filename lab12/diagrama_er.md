# Diagrama entidad-relación

```mermaid
erDiagram
    PERSON {
        bigint person_id PK
        integer gender_concept_id FK
        integer year_of_birth
    }
    OBSERVATION_PERIOD {
        bigint observation_period_id PK
        bigint person_id FK
        date observation_period_start_date
        date observation_period_end_date
    }
    VISIT_OCCURRENCE {
        bigint visit_occurrence_id PK
        bigint person_id FK
        integer visit_concept_id FK
    }
    CONDITION_OCCURRENCE {
        bigint condition_occurrence_id PK
        bigint person_id FK
        integer condition_concept_id FK
        bigint visit_occurrence_id FK
    }
    DRUG_EXPOSURE {
        bigint drug_exposure_id PK
        bigint person_id FK
        integer drug_concept_id FK
        bigint visit_occurrence_id FK
    }
    MEASUREMENT {
        bigint measurement_id PK
        bigint person_id FK
        integer measurement_concept_id FK
        bigint visit_occurrence_id FK
    }
    CONCEPT {
        integer concept_id PK
        string concept_name
        string domain_id
        string vocabulary_id
    }
    CONCEPT_RELATIONSHIP {
        integer concept_id_1 FK
        integer concept_id_2 FK
        string relationship_id
    }
    CONCEPT_ANCESTOR {
        integer ancestor_concept_id FK
        integer descendant_concept_id FK
    }
    PERSON ||--o{ OBSERVATION_PERIOD : tiene
    PERSON ||--o{ VISIT_OCCURRENCE : realiza
    PERSON ||--o{ CONDITION_OCCURRENCE : presenta
    PERSON ||--o{ DRUG_EXPOSURE : recibe
    PERSON ||--o{ MEASUREMENT : tiene
    VISIT_OCCURRENCE ||--o{ CONDITION_OCCURRENCE : contiene
    VISIT_OCCURRENCE ||--o{ DRUG_EXPOSURE : contiene
    VISIT_OCCURRENCE ||--o{ MEASUREMENT : contiene
    CONCEPT ||--o{ CONDITION_OCCURRENCE : define
    CONCEPT ||--o{ DRUG_EXPOSURE : define
    CONCEPT ||--o{ MEASUREMENT : define
    CONCEPT ||--o{ CONCEPT_RELATIONSHIP : relaciona
    CONCEPT ||--o{ CONCEPT_ANCESTOR : jerarquiza
```

## Comparación con OMOP CDM 5.4

1. El esquema conserva las columnas de OMOP 5.4, pero sólo se poblaron las
   tablas y dominios necesarios. Es una simplificación legítima del ETL.
2. Los `*_datetime` afectados quedaron nulos porque Synthea aporta fechas sin
   hora verificable y DuckDB presentó una incompatibilidad de conversión. Los
   `*_date` permanecen disponibles y no se inventaron horas inexistentes.
