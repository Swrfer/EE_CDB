#!/usr/bin/env bash
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)

JAR="$ROOT/tools/synthea/synthea-with-dependencies.jar"
OUTPUT="$ROOT/lab10/data/raw/synthea_5000"
CSV_DIR="$OUTPUT/csv"

REQUIRED_FILES=(
  patients.csv
  encounters.csv
  conditions.csv
  medications.csv
  observations.csv
)

if [[ ! -f "$JAR" ]]
then
  echo "ERROR: no se encontró Synthea en:"
  echo "$JAR"
  exit 1
fi

complete=true

for file in "${REQUIRED_FILES[@]}"
do
  if [[ ! -s "$CSV_DIR/$file" ]]
  then
    complete=false
  fi
done

if [[ "$complete" == true ]]
then
  echo "La cohorte completa ya existe; no se regenerará."
else
  if [[ -d "$CSV_DIR" ]] && find "$CSV_DIR" -type f -print -quit | grep -q .
  then
    echo "ERROR: existe una generación parcial en:"
    echo "$CSV_DIR"
    echo "Revísala antes de volver a ejecutar."
    exit 1
  fi

  mkdir -p "$OUTPUT"

  echo "===== COMANDO REPRODUCIBLE ====="
  echo "Semilla: 20261102"
  echo "Población solicitada: 5000"
  echo "Estado simulado: Massachusetts"
  echo "Salida: $OUTPUT"

  java     -jar "$JAR"     -s 20261102     -p 5000     --exporter.baseDirectory="$OUTPUT"     --exporter.csv.export=true     --exporter.fhir.export=false     Massachusetts
fi

echo "===== VALIDAR ARCHIVOS OBLIGATORIOS ====="

missing=0

for file in "${REQUIRED_FILES[@]}"
do
  path="$CSV_DIR/$file"

  if [[ -s "$path" ]]
  then
    rows=$(($(wc -l < "$path") - 1))
    echo "OK: $file | $rows filas"
  else
    echo "FALTA O ESTÁ VACÍO: $file"
    missing=$((missing + 1))
  fi
done

if (( missing > 0 ))
then
  echo "ERROR: faltan $missing archivos obligatorios."
  exit 1
fi

patients=$(($(wc -l < "$CSV_DIR/patients.csv") - 1))

if (( patients < 5000 ))
then
  echo "ERROR: solo se generaron $patients pacientes."
  exit 1
fi

echo "===== RESULTADO ====="
echo "Pacientes generados: $patients"
echo "Directorio CSV: $CSV_DIR"
echo "Validación: correcta"
