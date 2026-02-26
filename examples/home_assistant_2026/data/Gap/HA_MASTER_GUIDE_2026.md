# HA MASTER GUIDE 2026

## LEYES DE ARQUITECTURA (Del Manifiesto)

Estas leyes son obligatorias y deben seguirse en todas las integraciones y el Teacher. Las reglas están expresadas en forma imperativa.

**LEY — RUNTIME_DATA**
- DEBE tiparse todo `runtime_data` de las integraciones (ej: `type MyIntegrationConfigEntry = ConfigEntry[MyClient]`).
- DEBE declararse `py.typed` cuando la integración exponga tipos públicos.
- SE PROHÍBE persistir `runtime_data` en lugares globales sin versión ni namespace; todo dato runtime debe ser versionado y namespaced por `entry_id`.

**LEY — integration_type (manifest.json)**
- TODO `manifest.json` DEBE incluir el campo `integration_type` con uno de los valores canónicos: `hub`, `device`, `service`, `other`.
- DEBE existir una comprobación de esquema en CI que valide `integration_type` y `schema_version`.
- SE PROHÍBE usar valores ad-hoc fuera de los permitidos sin documentar una excepción en el repositorio.

**LEY — ENUMS para device_class y unit_of_measurement**
- SE PROHÍBE el uso de constantes globales tipo string para `device_class` o `unit_of_measurement`.
- DEBE utilizarse Enums canónicos (`SensorDeviceClass`, `UnitOfMeasurement`) definidos en la librería central.
- Cualquier mapeo a cadenas legadas DEBE implementarse en una capa de compatibilidad y estar cubierto por tests automatizados.

**LEY — async_forward_entry_setups**
- DEBE utilizarse la API asíncrona para reenviar la configuración a plataformas (`async_forward_entry_setups`) y estos flujos DEBEN ser no bloqueantes.
- DEBE capturarse y manejarse explícitamente: en caso de timeout o error transitorio lanzar `ConfigEntryNotReady`; en fallos de autenticación lanzar `ConfigEntryAuthFailed`.
- SE PROHÍBE realizar I/O bloqueante dentro del flujo de `async_forward_entry_setups`; cualquier operación bloqueante DEBE ejecutarse en `async_add_executor_job`.

**LEY — SETUP DE PLATAFORMAS Y GESTIÓN DE ERRORES**
- SE PROHÍBE el uso del método singular `async_forward_entry_setup`.
- DEBE usarse obligatoriamente la versión plural y awaitable: `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`.
- SE PROHÍBE capturar excepciones genéricas (`Exception`) en los DataUpdateCoordinators.
- DEBE elevarse `homeassistant.exceptions.UpdateFailed` para comunicar errores de comunicación o de API de forma estandarizada.

---

## ESTÁNDARES DE CODIFICACIÓN PLATINO (De AGENTS.md)

- **Python:** REQUERIDO Python 3.13+; usar features modernos (pattern matching, walrus, dataclasses).
- **Tipado estricto:** DEBE aplicarse type hints completos a funciones, métodos y variables; incluir `py.typed` para cumplimiento PEP-561.
- **Strings:** DEBE usar `f-strings` (no usar `%` ni `.format()` para nuevos cambios).
- **Dataclasses:** Usar `dataclasses` cuando proceda para estructuras inmutables/ligeras.
- **Herramientas:** Formateo con `ruff`; lint con `pylint`/`ruff`; type checking con `mypy`.
- **Tests:** DEBE incluir tests `pytest` para comportamiento crítico y migraciones.
- **Errores:** Para errores de actualización de datos externos DEBE lanzarse `UpdateFailed(f"...")` con la información mínima útil; SE PROHÍBE usar excepciones genéricas salvo en flujos de configuración y tareas en background (casos permitidos explicados en CI).
- **I/O y Async:** TODO I/O externo DEBE ser asíncrono; operaciones bloqueantes DEBEN ejecutarse en ejecutor (`hass.async_add_executor_job`). Evitar `time.sleep()` y llamadas bloqueantes en el loop.
- **Logging:** Mensajes sin punto final, sin nombres de integración y sin datos sensibles; usar logging perezoso (`%s`) para variables.

---

## PROTOCOLO DE COMPORTAMIENTO (De AGENTS.md)

- **BREVEDAD:** Las respuestas generadas DEBEN ser concisas y enfocadas; evitar verborrea innecesaria.
- **NO INVENTAR IDs:** SE PROHÍBE inventar IDs. Los identificadores DEBEN provenir de `external_id`, `uuid` o del origen autorizado; para datos externos, DEBE conservarse `external_id` y usarlo para deduplicación.
- **ÁREAS / ETIQUETAS:** DEBE usarse un sistema de `areas`/`tags` para clasificar mensajes, tareas y entidades (ej: `area:lighting`, `tag:energy`).
- **TONO Y LENGUAJE:** Documentación y mensajes de código DEBEN usar English (American) en comentarios y nombres; para UIs y mensajes al usuario, seguir localización.
- **METADATOS:** Cada integración DEBE declarar `schema_version`, `integration_type` y ejemplos mínimos en su `manifest.json`.

---

## APÉNDICE TÉCNICO

Resumen representativo de dependencias detectadas en el periodo 2024-07 → 2026-02 (no listar cada bump):

- `aiohttp >= 3.13.3`
- `aioesphomeapi >= 43.9.1`
- `bleak-esphome >= 3.6.0`
- `yt-dlp ~ 2026.02.04` (fecha-tagged release)

Para el changelog técnico completo y las entradas filtradas consulte el apéndice generado:

- [data_factory/data/raw/technical_changelog_2026.md](data_factory/data/raw/technical_changelog_2026.md)

---

Fecha de generación: 2026-02-10
Fuente: fusión de [data_factory/data/raw/MANIFIESTO_ARQUITECTURA_HA_2026.md](data_factory/data/raw/MANIFIESTO_ARQUITECTURA_HA_2026.md) y [data_factory/data/raw/AGENTS.md.txt](data_factory/data/raw/AGENTS.md.txt)
