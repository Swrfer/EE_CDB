#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(
  git rev-parse \
    --show-toplevel
)"

cd "$RAIZ"

JAVA_HOME="$(
  java \
    -XshowSettings:properties \
    -version \
    2>&1 \
  | awk \
      -F'= ' \
      '/^[[:space:]]*java.home = / {
        print $2
        exit
      }'
)"

if [[ -z "$JAVA_HOME" ]]
then
  echo "ERROR: no se pudo determinar JAVA_HOME."
  exit 1
fi

export JAVA_HOME

DISPONIBLE_KB="$(
  df \
    -Pk \
    . \
  | awk \
      'NR == 2 {
        print $4
      }'
)"

MINIMO_KB=$((15 * 1024 * 1024))

if (( DISPONIBLE_KB < MINIMO_KB ))
then
  echo "ERROR: se requieren al menos 15 GB libres."
  df -h .
  exit 1
fi

echo "===== ESPACIO DISPONIBLE ====="

df \
  -h \
  .

echo "===== TAMAÑO DE ENTRADAS ====="

du \
  -sh \
  lab10/data/raw/synthea_5000/csv \
  lab12/data/raw/athena

echo "===== JAVA_HOME ====="

echo "$JAVA_HOME"

echo "===== INICIAR ETL ====="

caffeinate \
  -i \
  Rscript \
  lab12/scripts/01_convertir_omop.R \
  2>&1 \
  | tee lab12/evidencias/04_etl_completo.txt
