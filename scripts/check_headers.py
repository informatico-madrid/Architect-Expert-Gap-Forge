#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Verificador ligero de cabeceras de archivos fuente.

Este script comprueba que los ficheros Python clave del proyecto incluyen
la cabecera estándar: debe contener la cadena del proyecto
`Architect-Expert-Gap-Forge (AEGF)`, una línea de `Copyright` y
`SPDX-License-Identifier:`.

Uso:
  python scripts/check_headers.py --check

Devuelve código 0 si todo está bien, 1 si hay violaciones.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


INCLUDE_PREFIXES = (
    "src/",
    "tests/",
    "docs/",
    "scripts/",
    "deploy/",
    "diagnose/",
    "examples/",
    "legacy/",
    "infrastructure/",
)

HEADER_TOKENS = (
    "SPDX-License-Identifier:",
    "Architect-Expert-Gap-Forge",
    "Copyright",
)


def git_py_files() -> List[str]:
    """Listar archivos .py versionados por git en el repo.

    Si git no está disponible, hace un fallback a búsqueda recursiva.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "*.py"], check=True, capture_output=True, text=True
        )
        files = out.stdout.splitlines()
    except Exception:
        files = [str(p) for p in Path(".").rglob("*.py") if p.is_file()]

    def in_scope(p: str) -> bool:
        return any(p.startswith(pref) for pref in INCLUDE_PREFIXES) or ("/" not in p)

    # Filter to only include files that actually exist on disk
    return [p for p in files if in_scope(p) and Path(p).is_file()]


def check_file(path: str) -> Tuple[bool, List[str]]:
    p = Path(path)
    try:
        content = p.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - IO issues
        return False, [f"read-error: {exc}"]
    head = content[:4096]
    missing = [t for t in HEADER_TOKENS if t not in head]
    return (len(missing) == 0, missing)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Comprobar y fallar si hay problemas"
    )
    args = parser.parse_args(argv)

    files = git_py_files()
    violations = []
    for f in files:
        ok, missing = check_file(f)
        if not ok:
            violations.append((f, missing))

    if violations:
        print("ERROR: Se han encontrado archivos sin la cabecera requerida:\n")
        for f, missing in violations:
            print(f" - {f}: faltan tokens -> {missing}")
        print()
        print("Cabecera mínima esperada (ejemplo):")
        print("""
#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Your Name <you@example.com>
# SPDX-License-Identifier: Apache-2.0
""")
        print(
            "Para corregir: añadir la cabecera a los ficheros afectados y volver a intentar."
        )
        return 1

    print("OK: Todas las cabeceras críticas están presentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
