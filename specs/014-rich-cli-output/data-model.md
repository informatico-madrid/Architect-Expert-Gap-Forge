# Data Model: Rich Terminal Output para CLI

**Feature**: Rich Terminal Output para CLI  
**Branch**: 014-rich-cli-output

## Overview

Esta feature no introduce nuevas entidades de datos. Es una mejora de presentación en la capa de UI/CLI existente.

## Justification

A diferencia de otras features del proyecto AEGF que involucran:
- Entidades de datos (samples, trajectories, evaluations)
- Modelos de inferencia
- Schemas de configuración

Esta feature es puramente de **presentación/output**. No hay:
- Nuevas tablas o modelos de datos
- Cambios en formatos de archivo
- Nuevas interfaces de almacenamiento

## Components Involucrados

Los únicos "componentes" que cambian son los scripts CLI existentes que modifican su salida de texto plano a salida formateada con Rich.

### Scripts a Modificar

| Módulo | Scripts | Tipo de Cambio |
|--------|---------|----------------|
| audit | 2 | Output formateado |
| curation | 2 | Output formateado |
| discovery | 2 | Output formateado |
| factory | 2 | Output formateado |
| merger | 14 | Output formateado |
| research | 1 | Output formateado |

## State Transitions

No aplica - no hay cambios de estado.

## Validation

No hay validación de datos necesaria - la feature solo cambia cómo se muestra la información existente.
