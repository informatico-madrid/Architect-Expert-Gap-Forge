#!/bin/bash
echo "Iniciando Ralph Loop..."

while true; do
    # 1. Leer tarea pendiente
    TAREA=$(jq -r '.[] | select(.passes == false) | .task' prd.json | head -n 1)

    if [ -z "$TAREA" ] || [ "$TAREA" == "null" ]; then
        echo "¡Todas las tareas en prd.json están completadas!"
        break
    fi

    echo "Tarea actual: $TAREA"

    # 2. Ejecutar agente CLI (Goose en este caso) conectado a tu modelo local
    goose run "Tu tarea es: $TAREA. Antes de programar, lee '.specify/memory/constitution.md' para conocer las reglas innegociables del proyecto y revisa la carpeta 'specs/' para entender la arquitectura. Escribe el código necesario. Cuando termines, actualiza el archivo 'progress.txt' con un breve resumen de los errores solucionados."

    # 3. Validar con tests
    echo "Ejecutando pruebas..."
    if npm test; then
        echo "Pruebas exitosas."
        # 4. Actualizar estado y Git
        jq '((.[] | select(.task == "'"$TAREA"'" and .passes == false)) | .passes) = true' prd.json > tmp.json && mv tmp.json prd.json
        git add .
        git commit -m "Ralph Loop: Tarea completada - $TAREA"
    else
        echo "Las pruebas fallaron. Deteniendo el bucle."
        break
    fi
    sleep 2
done