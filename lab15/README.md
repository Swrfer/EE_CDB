# Laboratorio 15 — Concept sets de medicamentos y laboratorios

## Propósito

Construir concept sets reutilizables de exposición farmacológica y HbA1c, auditar unidades y mapear un catálogo local mexicano sin ocultar ambigüedad.

## Decisiones principales

- Se eligió **lisinopril** para A/B/C porque metformina solo tenía una presentación observada.
- La versión final para un estudio renal es **C — lisinopril sin combinaciones con hidroclorotiazida**.
- HbA1c se construyó mediante `Has component` con `LP286151-8`, excluyendo dispositivos, paneles, metas clínicas y glucosa estimada.
- RxNorm Extension no estaba presente; los 331 productos observados sí resolvieron a ingredientes RxNorm estándar.

## Resultados

- Top 20: 3 productos con múltiples ingredientes.
- A10B: 42 ingredientes, 2 productos y 246 pacientes.
- Fuera de A10B: 329 de 331 productos observados.
- Lisinopril A/B/C: 1014, 1024, 1014 pacientes.
- Catálogo local: 15 filas; 80% con confianza alta, una dudosa y dos no mapeables.

## Archivos

- `concept_sets/01_lisinopril.sql`
- `concept_sets/02_atc_a10b.sql`
- `concept_sets/03_hba1c.sql`
- `mapeo_catalogo_local.csv`
- `auditoria_unidades.md`
- `notebooks/analisis_rxnorm_loinc.ipynb`
- `evidencias/analisis/*.csv`
- `figuras/*.png`

## Reproducibilidad

```bash
python lab15/scripts/01_generar_lab15.py
```

Vocabularios: RxNorm 20260601, ATC 2026-02-01, LOINC 2.82, UCUM Version 1.8.2. Fecha de consulta: 2026-11-22.

Fuentes: [RxNav](https://mor.nlm.nih.gov/RxNav/), [LOINC](https://loinc.org/), [Compendio Nacional de Insumos para la Salud](https://www.gob.mx/csg/articulos/compendio-nacional-de-insumos-para-la-salud-367182).
