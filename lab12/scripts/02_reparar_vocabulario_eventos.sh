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

export JAVA_HOME

caffeinate \
  -i \
  Rscript \
  lab12/scripts/02_reparar_vocabulario_eventos.R \
  2>&1 \
  | tee lab12/evidencias/06_reparacion_vocabulario_eventos.txt
