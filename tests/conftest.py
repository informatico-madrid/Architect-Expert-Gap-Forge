#!/usr/bin/env python3
#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Pytest conftest: ensure a minimal prompt taxonomy is loaded for tests.

This session-scoped autouse fixture writes a minimal taxonomy YAML and
invokes `src.factory.prompt_builder.load_taxonomy` so tests that rely on
prompt templates and tools have a stable baseline during the test run.
"""

from __future__ import annotations

import sys
import yaml
from pathlib import Path

import pytest

from src.factory import prompt_builder as pb_module
from src.factory.prompt_builder import load_taxonomy, set_test_state
from src.factory.config import TaxonomyState


@pytest.fixture(scope="session", autouse=True)
def minimal_taxonomy(tmp_path_factory) -> Path:
    """Create and load a minimal taxonomy for the whole test session.

    The taxonomy contains the small set of keys used by the prompt builders
    and avoids KeyError('system') during tests that do not explicitly load
    a taxonomy file.
    """
    tax_dir = tmp_path_factory.mktemp("taxonomy")
    tax_file = tax_dir / "taxonomy_minimal.yaml"
    taxonomy = {
        "ha_error_templates": [{"error": "Error in {entity} at {component}"}],
        "legacy_2023_patterns": [{"legacy_code": "hass.data["}],
        "jinja_ha_error_templates": [{"error": "Jinja error {component}"}],
        "jinja_legacy_2023_patterns": [{"legacy_code": "platform:"}],
        "theory_question_templates": [
            {
                "template": "Write a doctrinal note about {section_title}.",
                "type": "explain",
            }
        ],
        "tools_definition": [
            {
                "name": "write_to_file",
                "arguments": {"path": "<path>", "content": "<content>"},
            }
        ],
        "prompts": {
            "system": {
                "python": {
                    "base": "BASE $tools_json master:$master changelog:$changelog",
                    "nominal_suffix": "NOMINAL",
                    "contrast_suffix": "CONTRAST",
                    "error_recovery_suffix": "ERROR",
                    "blueprint_context": "BLUEPRINT: $blueprint\nLOCAL IMPORTS: $local_imports",
                    "governance_context": "GOVERNANCE: $governance_rules",
                },
                "jinja": {
                    "base": "BASE_JINJA $tools_json jinja:$jinja_guide",
                    "nominal_suffix": "JINJA_NOMINAL",
                    "contrast_suffix": "JINJA_CONTRAST",
                    "error_recovery_suffix": "JINJA_ERROR",
                },
                "theory": "THEORY SYSTEM: master:$master changelog:$changelog",
            },
            "user": {
                "python": {
                    "nominal_easy": "EASY $virtual_filename",
                    "nominal_medium": "MEDIUM $virtual_filename",
                    "nominal_hard_anchor_free": ["ANCHOR_FREE $virtual_filename"],
                    "nominal_hard_anchor": "HARD $virtual_filename",
                    "contrast": "CONTRAST $legacy_code",
                    "error_recovery": "ERROR_RECOVERY",
                    "functional_unit": "FUNCTIONAL UNIT: $virtual_filename\nNAME: $name\nSKELETON:\n$skeleton",
                },
                "jinja": {
                    "nominal_easy": "JINJA_EASY",
                    "nominal_medium": "JINJA_MEDIUM",
                    "nominal_hard_anchor_free": ["JINJA_ANCHOR_FREE"],
                    "nominal_hard_anchor": "JINJA_HARD_ANCHOR",
                    "contrast": "JINJA_CONTRAST",
                    "error_recovery": "JINJA_ERROR_RECOVERY",
                },
            },
        },
    }
    tax_file.write_text(yaml.safe_dump(taxonomy, allow_unicode=True))
    state = load_taxonomy(tax_file)
    set_test_state(state)
    return tax_file


#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Shared pytest fixtures for the AEGF test suite.

All domain objects are constructed here so individual test modules stay
focused on behaviour rather than boilerplate.
"""

import textwrap
from pathlib import Path
from typing import Any, Dict, List
from src.schemas.common import RawRecord
from unittest.mock import MagicMock

import pytest
import yaml

from src.audit.schema import (
    AuditReport,
    ExamRecord,
    InferenceResult,
    SampleRecord,
    ScoreCard,
)


# ---------------------------------------------------------------------------
# Domain entity factories
# ---------------------------------------------------------------------------


def make_sample(
    id: str = "sample-001",
    example_type: str = "nominal",
    evol_difficulty: str = "medium",
    fragment_name: str = "climate_entity",
    source_file: str = "components/climate/__init__.py",
    user_prompt: str = "Implement a CoordinatorEntity for a climate sensor.",
    reference_response: str = "<think>I need to use modern HA APIs.</think>\n```python\npass\n```",
    gold_injected: bool = True,
    ldi: float = 0.85,
    reference_standards: str = "Use entry.runtime_data, CoordinatorEntity, async_setup_entry.",
    gap_analysis: str = "Missing DataUpdateCoordinator pattern.",
) -> SampleRecord:
    """Construct a minimal but valid SampleRecord."""
    return SampleRecord(
        id=id,
        example_type=example_type,
        evol_difficulty=evol_difficulty,
        fragment_name=fragment_name,
        source_file=source_file,
        user_prompt=user_prompt,
        reference_response=reference_response,
        gold_injected=gold_injected,
        ldi=ldi,
        reference_standards=reference_standards,
        gap_analysis=gap_analysis,
    )


def make_exam_record(sample: SampleRecord | None = None, **kwargs: Any) -> ExamRecord:
    """Construct a minimal ExamRecord from an optional base sample."""
    base = sample or make_sample()
    defaults: Dict[str, Any] = {
        "exam_question": "Implement a climate entity using CoordinatorEntity.",
        "eval_criteria": ["Uses entry.runtime_data", "Proper error handling"],
        "target_patterns": ["CoordinatorEntity", "async_setup_entry"],
    }
    defaults.update(kwargs)
    return ExamRecord.from_sample(base, **defaults)


def make_scorecard(
    record_id: str = "sample-001",
    sample_id: str = "sample-001",  # Alias for record_id
    example_type: str = "nominal",
    fragment_name: str = "climate_entity",
    ha_modernity: float = 0.9,
    reasoning_depth: float = 0.8,
    functionality: float = 0.85,
    completeness: float = 0.9,
    style: float = 0.7,
    composite_score: float = 0.86,
) -> ScoreCard:
    """Construct a ScoreCard with sensible defaults."""
    return ScoreCard(
        record_id=record_id,
        sample_id=sample_id,
        example_type=example_type,
        fragment_name=fragment_name,
        ha_modernity=ha_modernity,
        reasoning_depth=reasoning_depth,
        functionality=functionality,
        completeness=completeness,
        style=style,
        composite_score=composite_score,
        delta_vs_baseline=0.05,
        judge_reasoning="Model shows correct API usage.",
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_record() -> SampleRecord:
    """A single valid SampleRecord."""
    return make_sample()


@pytest.fixture
def exam_record(sample_record: SampleRecord) -> ExamRecord:
    """An ExamRecord derived from the base sample_record fixture."""
    return make_exam_record(sample_record)


@pytest.fixture
def scorecard() -> ScoreCard:
    """A single ScoreCard with default values."""
    return make_scorecard()


@pytest.fixture
def audit_report(scorecard: ScoreCard) -> AuditReport:
    """A minimal AuditReport with one scorecard."""
    return AuditReport(
        timestamp="2026-03-03T00:00:00",
        dataset_path="data/audit/baseline.jsonl",
        base_model="qwen3-5-35b-a3b-nvfp4",
        adapter_model="platinum_adapter",
        judge_model="gemini-2.5-flash",
        sample_size=1,
        type_distribution={"nominal": 1},
        scorecards=[scorecard],
        final_grade=86.0,
        verdict="PASS",
    )


@pytest.fixture
def multi_sample_records() -> List[SampleRecord]:
    """A list of SampleRecords covering all four canonical example_types."""
    types = ["nominal", "contrast", "error_recovery", "theory"]
    records: List[SampleRecord] = []
    for i, et in enumerate(types):
        for j in range(3):  # 3 records per type → 12 total
            records.append(
                make_sample(
                    id=f"{et}-{j:03d}",
                    example_type=et,
                    ldi=0.5 + j * 0.1,
                )
            )
    return records


@pytest.fixture
def raw_records() -> List[RawRecord]:
    """Raw JSONL-like dicts as returned by load_jsonl(), used for sampling tests."""
    types = ["nominal", "contrast", "error_recovery", "theory"]
    records: List[Dict[str, Any]] = []
    for i, et in enumerate(types):
        for j in range(4):
            records.append(
                {
                    "id": f"{et}-{j:03d}",
                    "metadata": {
                        "example_type": et,
                        "evol_difficulty": "medium",
                        "fragment_name": f"fragment_{j}",
                        "source_file": "components/sensor/__init__.py",
                        "gold_injected": True,
                        "ldi": 0.7 + j * 0.05,
                        "reference_standards": "Use entry.runtime_data.",
                        "gap_analysis": "Missing CoordinatorEntity.",
                    },
                    "conversation": [
                        {"role": "user", "content": f"Implement sensor {j}."},
                        {
                            "role": "assistant",
                            "content": f"<think>Thinking...</think>\n```python\npass\n```",
                        },
                    ],
                }
            )
    return records


@pytest.fixture
def prompts_yaml_path(tmp_path: Path) -> Path:
    """Write a minimal eval_prompts.yaml into a temp dir and return the path."""
    content = textwrap.dedent("""\
        test_group:
          system: "You are a test assistant."
          user: "Hello {name}, answer {question}."
        another_group:
          system: "Second system prompt."
          user: "Second user prompt."
    """)
    p = tmp_path / "eval_prompts.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def gap_dir(tmp_path: Path) -> Path:
    """Create a temporary gap_dir with the three required master docs."""
    d = tmp_path / "gap"
    d.mkdir()
    (d / "HA_MASTER_GUIDE_2026.md").write_text(
        "# Master Guide content", encoding="utf-8"
    )
    (d / "technical_changelog_2026.md").write_text(
        "# Changelog content", encoding="utf-8"
    )
    (d / "HA_JINJA_YAML_GUIDE_2026.md").write_text(
        "# Jinja guide content", encoding="utf-8"
    )
    return d


@pytest.fixture
def mock_inference_client() -> MagicMock:
    """A MagicMock that conforms to BaseInferenceClient's interface."""
    client = MagicMock()
    client.generate.return_value = '{"result": "ok"}'
    client.generate_with_retry.return_value = '{"result": "ok"}'
    return client


# =============================================================================
# ADDITIONAL TEST FIXTURES - Use these for creating tests
# =============================================================================


@pytest.fixture
def sample_records() -> List[SampleRecord]:
    """A list of SampleRecords for batch testing."""
    types = ["nominal", "contrast", "error_recovery", "theory"]
    records: List[SampleRecord] = []
    for i, et in enumerate(types):
        for j in range(3):
            records.append(
                make_sample(
                    id=f"{et}-{j:03d}",
                    example_type=et,
                    ldi=0.5 + j * 0.1,
                )
            )
    return records


@pytest.fixture
def empty_sample_record() -> SampleRecord:
    """A SampleRecord with minimal/empty fields."""
    return SampleRecord(
        id="empty-001",
        example_type="nominal",
        evol_difficulty="easy",
        fragment_name="empty",
        source_file="test.py",
        user_prompt="",
        reference_response="",
        gold_injected=False,
        ldi=0.0,
        reference_standards="",
        gap_analysis="",
    )


@pytest.fixture
def invalid_sample_record() -> dict:
    """An invalid sample record (dict format) for error testing."""
    return {
        "id": "invalid-001",
        "metadata": {
            "example_type": "invalid_type",
            "evol_difficulty": "unknown",
            "fragment_name": "",
            "source_file": "",
            "gold_injected": False,
            "ldi": 1.5,  # Invalid: > 1.0
            "reference_standards": "",
            "gap_analysis": "",
        },
        "conversation": [],
    }


@pytest.fixture
def mock_api_response_success() -> dict:
    """A successful API response for mocking."""
    return {
        "status": "success",
        "data": {"result": "expected_value"},
        "message": "Operation completed",
    }


@pytest.fixture
def mock_api_response_error() -> dict:
    """An error API response for mocking."""
    return {
        "status": "error",
        "error": {"code": 500, "message": "Internal server error"},
    }


@pytest.fixture
def temp_json_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file for testing file I/O."""
    import json

    data = {"key": "value", "number": 42}
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")
    return file_path


# =============================================================================
# PHP LEGACY DRIVER FIXTURES
# =============================================================================

PHP_LEGACY_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "php_legacy"


def pytest_configure(config):
    """Register custom pytest marks for PHP legacy driver tests."""
    config.addinivalue_line(
        "markers", "php_legacy: marks tests for PHP legacy driver functionality"
    )
    config.addinivalue_line(
        "markers", "php_legacy_unit: marks unit tests for PHP legacy driver"
    )
    config.addinivalue_line(
        "markers",
        "php_legacy_integration: marks integration tests for PHP legacy driver",
    )


@pytest.fixture
def php_legacy_fixtures_dir() -> Path:
    """Return the path to the PHP legacy fixtures directory."""
    return PHP_LEGACY_FIXTURES_DIR


@pytest.fixture
def php_legacy_sample_content() -> str:
    """Load a sample PHP content for testing fragment extraction.

    This fixture provides a minimal PHP file with common legacy patterns
    including functions, includes, and database calls.
    """
    return """<?php
// Sample PHP file for testing
global $languages_id, $db;

include(DIR_WS_INCLUDES . 'application_top.php');

function tep_db_query($query) {
    return mysql_query($query);
}

function get_categories() {
    global $db;
    $query = "SELECT * FROM categories WHERE categories_id = '" . $languages_id . "'";
    return tep_db_query($query);
}

// Switch case block
switch ($action) {
    case 'edit':
        tep_redirect(FILENAME_EDIT);
        break;
    case 'delete':
        $_SESSION['customer_id'] = $customer_id;
        break;
}
?>"""


# Minimal fallback content used when specific fixtures don't exist yet
PHP_LEGACY_FALLBACK_CONTENT = """<?php
// Sample PHP file for testing
global $languages_id, $db;

include(DIR_WS_INCLUDES . 'application_top.php');

function tep_db_query($query) {
    return mysql_query($query);
}

function get_categories() {
    global $db;
    $query = "SELECT * FROM categories WHERE categories_id = '" . $languages_id . "'";
    return tep_db_query($query);
}

// Switch case block
switch ($action) {
    case 'edit':
        tep_redirect(FILENAME_EDIT);
        break;
    case 'delete':
        $_SESSION['customer_id'] = $customer_id;
        break;
}
?>"""


@pytest.fixture
def php_legacy_oscommerce_fixture() -> str:
    """Load the osCommerce categories fixture for integration tests."""
    from tests.fixtures.php_legacy import load_php_fixture

    try:
        return load_php_fixture("oscommerce_categories.php")
    except FileNotFoundError:
        # Return minimal fixture if file not yet created (T002)
        return PHP_LEGACY_FALLBACK_CONTENT


@pytest.fixture
def php_legacy_wordpress_fixture() -> str:
    """Load the WordPress ajax actions fixture for integration tests."""
    from tests.fixtures.php_legacy import load_php_fixture

    try:
        return load_php_fixture("wordpress_ajax_actions.php")
    except FileNotFoundError:
        return PHP_LEGACY_FALLBACK_CONTENT


@pytest.fixture
def php_legacy_zencart_fixture() -> str:
    """Load the ZenCart customers fixture for integration tests."""
    from tests.fixtures.php_legacy import load_php_fixture

    try:
        return load_php_fixture("zencart_customers.php")
    except FileNotFoundError:
        return PHP_LEGACY_FALLBACK_CONTENT
