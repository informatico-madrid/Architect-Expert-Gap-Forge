# Adversarial Review Findings: prompt-externalization

**Review Type**: Cynical Review  
**Reviewer**: external-reviewer (adversarial mode)  
**Date**: 2026-04-24  
**Content Reviewed**: 7 `.example.yaml` files + task_review.md + chat.md

---

## Summary

**Issues Found**: 15  
**Critical**: 1 | **Major**: 6 | **Minor**: 8

---

## Critical Issues

### 1. [CRITICAL] T-04 trajectory — Dead YAML (Deferred to Epic 1)
**File**: `src/factory/prompts_trajectory.example.yaml:11-14`

El output usa `.system` key pero el código consumidor en `trajectory_generator.py:216,226` hace `.get("template")`. El archivo contiene el warning pero el problema NO está resuelto — solo documentado. La tarea fue marcada PASS pero el archivo es inútil para el consumidor actual sin un refactor en Epic 1.

---

## Major Issues

### 2. [MAJOR] Inconsistent placeholder syntax — `$var` vs `{var}`
**Files**: Multiple

- `prompts_taxonomy.example.yaml` usa `$context`, `$virtual_filename`, `$name`, `$skeleton`, `$legacy_code`, `$error_msg`, `$blueprint`, `$local_imports`, `$governance_rules`, `$jinja_guide`, `$master`, `$changelog`, `$tools_json`
- `prompts_trajectory.example.yaml` usa `{context}`, `{question}`, `{reasoning}`, `{tool_name}`, `{error_description}`, `{corrective_action}`, `{verification_result}`
- AC-1.5 dice `$var` por convención DSPy, pero el código de producción usa `{var}`

**Verdict**: La especificación misma es inconsistente. El spec-executor siguió el código de producción ({var}) pero violó requirements.md.

### 3. [MAJOR] prompts_judge.example.yaml — Typo semántico
**File**: `src/audit/prompts_judge.example.yaml:10`

```
Your exams test deep understanding of LDI (Legacy-Detection-Index) migration patterns
and Architecture architecture — NOT memorisation of existing code.
```

"Architecture architecture" — duplicación evidente.

### 4. [MAJOR] prompts_calibration.example.yaml — System prompts vacíos
**File**: `src/audit/prompts_calibration.example.yaml`

Los 6 prompts tienen `system` minimalistas:
```yaml
system: |
  top_k, presence_penalty
```

Esto es prácticamente inútil como system prompt para guiar comportamiento del modelo. La metadata es rica, pero si DSPy usa el campo `system` para instrucción, la calidad de guidance es nula.

### 5. [MAJOR] prompts_hard_query.example.yaml — Spanish en forbidden_terms
**File**: `src/factory/prompts_hard_query.example.yaml:9-10`

```yaml
- llama al servicio
- usa el componente
```

FR-2 dice "No Spanish text remains in .example.yaml files (except untranslatable domain terms)". Estos SON frases traducibles ("calls the service", "uses the component"). Si son "domain terms" entonces la definición de domain term es insuficiente.

### 6. [MAJOR] prompts_taxonomy.example.yaml — Inconsistent output protocol
**File**: `src/factory/prompts_taxonomy.example.yaml`

- `system_python_nominal_suffix:55-61` usa `<write_action><path>...</path><content>...</content></write_action>`
- `system_jinja_nominal_suffix:203-208` usa la misma estructura
- Otros prompts usan diferentes formatos de output

El protocolo de output no es consistente entre prompts de mismo nivel.

### 7. [MAJOR] prompts_taxonomy.example.yaml — `$tools_json` sin definición
**File**: `src/factory/prompts_taxonomy.example.yaml:22`

```yaml
AVAILABLE TOOLS:
$tools_json
```

No hay indicación de qué formato tiene esta variable o cómo debe ser sustituida. Si esto se carga en DSPy sin substitución, el modelo verá `$tools_json` literalmente.

---

## Minor Issues

### 8. [MINOR] prompts_taxonomy.example.yaml — Jinja escaping `{{` en JSON
**File**: `src/audit/prompts_judge.example.yaml:107-123`

```yaml
Return ONLY a JSON object with this exact schema (no markdown wrapper):
{{
  "baseline": {{
```

Esto es escaping Jinja2 pero el archivo NO es Jinja — es YAML plain. Si se carga tal cual en DSPy, los `{{` pasan literalmente en el output.

### 9. [MINOR] prompts_backtracking.example.yaml — Header vago
**File**: `src/curation/prompts_backtracking.example.yaml:3`

```yaml
# Source: configs/prompts/
```

Otros archivos especifican el archivo exacto (e.g., "Source: src/export/frontend_taxonomy_prompts.py"). Falta precisión.

### 10. [MINOR] prompts_taxonomy.example.yaml — Campo `system: ""` vacío
**File**: `src/factory/prompts_taxonomy.example.yaml:296,307,322,368,387,404,421,443,453,470,514,532,551`

12 prompts de `user_python_*` y `user_jinja_*` tienen `system: ""` vacío. Si DSPy espera que `system` guíe el comportamiento, estos no funcionarán como se espera.

### 11. [MINOR] Whitespace inconsistente en YAML keys
**Files**: Varios

- `user_python_nominal_hard_anchor_free:323-366` tiene el `user` como lista de 3 items con indentación diferente
- Otros tienen `user` como string multilinea

### 12. [MINOR] prompts_calibration.example.yaml — `system` no tiene trailing newline
**File**: `src/audit/prompts_calibration.example.yaml:9`

```yaml
system: |
  top_k, presence_penalty
user: |
```

El block scalar `|` requiere newline después. Los otros archivos usan `system: |` con contenido en línea siguiente.

### 13. [MINOR] research.md — Claim incorrecto sobre línea 10
**File**: `specs/prompt-externalization/research.md`

El archivo claimaba "configs/stage_5_evaluation/calibration_prompts.yaml.example" existe pero NO existe. Esto fue detectado durante la investigación original.

### 14. [MINOR] T-09 verify script — No valida schema interno
**File**: `specs/prompt-externalization/tasks.md:114-154`

El script de T-09 valida que los archivos parsean y tienen las cuentas correctas, pero NO valida que `.system`/`.user` tienen contenido o que los placeholders son consistentes.

### 15. [MINOR] task_review.md — 0 resolved_at timestamps
**File**: `specs/prompt-externalization/task_review.md`

Todos los entries tienen `resolved_at: <!-- spec-executor fills this -->` lo cual indica que el spec-executor nunca actualizó el campo. Ningún task tiene timestamp de resolución.

---

## Issues Already Known (Documented)

- AC-1.5 `$var` vs `{var}`: conocido, documentado en header de trajectory y en task_review.md
- Dead YAML trajectory: conocido, documentado en header del archivo

---

## Verdict

La revisión adversarial encontró 15 issues. Varios de los que fueron marcados PASS en la revisión original tienen problemas sutiles pero significativos — especialmente:

1. La inconsistencia de placeholder syntax entre archivos
2. Los system prompts de calibration que son prácticamente vacíos
3. El problema de trajectory que fue "resuelto" con documentación en lugar de con código

**Recomendación**: Epic 1 debe abordar estos issues como parte del trabajo de integración DSPy.
