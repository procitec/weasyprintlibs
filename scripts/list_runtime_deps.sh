#!/bin/sh
set -eu
ROOT=${1:-src/weasyprint_libs/lib}
find "$ROOT" -type f -exec sh -c '
  for file do
    if head -c 4 "$file" 2>/dev/null | grep -q "ELF"; then
      echo "=== $file ==="
      ldd "$file" || true
    fi
  done
' sh {} +
