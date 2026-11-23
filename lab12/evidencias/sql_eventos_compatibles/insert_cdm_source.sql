insert into cdm.cdm_source (
cdm_source_name,
cdm_source_abbreviation,
cdm_holder,
source_description,
source_documentation_reference,
cdm_etl_reference,
source_release_date,
cdm_release_date,
cdm_version,
vocabulary_version,
cdm_version_concept_id
)
select
'Synthea synthetic health database',
'Synthea',
'OHDSI',
'Synthea 3.4.0-18 compatible con ETL-Synthea 3.3.0; OMOP CDM v5.4',
'https://synthetichealth.github.io/synthea/',
'https://github.com/OHDSI/ETL-Synthea',
CURRENT_DATE, -- NB: Set this value to the day the source data was pulled
CURRENT_DATE,
'5.4',
vocabulary_version,
756265
from cdm.vocabulary
where vocabulary_id = 'None';

