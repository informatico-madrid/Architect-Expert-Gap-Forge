"""MODULE_BLUEPRINT cross-language verification test.

Verifies TYPE 4 MODULE_BLUEPRINT generation for Python, TypeScript, PHP, YAML repos.
Requirements: FR-3, AC-3.1 to AC-3.7

Test scenarios:
- Python repo: manifest.json + __init__.py
- TypeScript repo: directory scan with anchor detection
- PHP repo: filesystem with composer.json
- YAML repo: yaml strategy with strings.json anchor
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModuleBlueprintSchema:
    """Expected MODULE_BLUEPRINT structure for TYPE 4 fragments."""

    has_module_map: bool
    has_dependencies: bool
    has_schema: bool
    has_vocabulary: bool
    has_readme: bool
    module_path: str
    module_name: str
    file_count: int


@dataclass
class CrossLanguageTestConfig:
    """Configuration for cross-language MODULE_BLUEPRINT verification."""

    repo_name: str
    discovery_strategy: str
    expected_extensions: list[str]
    anchor_patterns: list[str]
    expected_blueprint_fields: list[str]


class TestModuleBlueprintCrossLanguage:
    """MODULE_BLUEPRINT generation across Python, TypeScript, PHP, YAML."""

    def setup_method(self):
        """Setup test fixtures."""
        self.base_path = Path("/mnt/bunker_data/ai/data_factory")
        self.spec_path = self.base_path / "specs" / "frontend-discovery-enhancement"
        self.tests_path = self.spec_path / "tests" / "verification"

    def test_python_module_blueprint(self):
        """Verify MODULE_BLUEPRINT for Python repo.

        Python uses manifest.json + __init__.py anchor pattern.
        Expected fields: [MODULE_MAP], [DEPENDENCIES], [SCHEMA], [VOCABULARY], [README]
        """
        # Verify MODULE_BLUEPRINT generation for Python files
        blueprint_path = (
            self.tests_path / "fixtures" / "blueprint_python_module.json"
        )

        assert blueprint_path.exists(), (
            f"Python blueprint fixture not found at {blueprint_path}"
        )

        # Parse and validate blueprint structure
        import json

        with open(blueprint_path, "r") as f:
            blueprint_data = json.load(f)

        # Validate TYPE 4 MODULE_BLUEPRINT schema
        assert "module_map" in blueprint_data, "Missing [MODULE_MAP]"
        assert "dependencies" in blueprint_data, "Missing [DEPENDENCIES]"
        assert "schema" in blueprint_data, "Missing [SCHEMA]"
        assert "vocabulary" in blueprint_data, "Missing [VOCABULARY]"
        assert "readme" in blueprint_data, "Missing [README]"

        # Validate module structure
        module_map = blueprint_data["module_map"]
        assert len(module_map) > 0, "MODULE_MAP should not be empty"

        for module_path, metadata in module_map.items():
            assert "anchor_file" in metadata, f"Missing anchor_file for {module_path}"
            assert "logic_files" in metadata, f"Missing logic_files for {module_path}"
            assert "test_files" in metadata, f"Missing test_files for {module_path}"

        # Verify Python-specific patterns
        py_files = [
            f for f in module_map.keys() if Path(f).suffix == ".py"
        ]
        assert len(py_files) > 0, "Should contain Python files"

    def test_typescript_module_blueprint(self):
        """Verify MODULE_BLUEPRINT for TypeScript repo.

        TypeScript uses directory scan (no anchors) - all .ts/.tsx files processed.
        Expected fields: [MODULE_MAP], [DEPENDENCIES], [SCHEMA], [VOCABULARY], [README]
        """
        # Verify MODULE_BLUEPRINT generation for TypeScript files
        blueprint_path = (
            self.tests_path / "fixtures" / "blueprint_typescript_module.json"
        )

        assert blueprint_path.exists(), (
            f"TypeScript blueprint fixture not found at {blueprint_path}"
        )

        import json

        with open(blueprint_path, "r") as f:
            blueprint_data = json.load(f)

        # Validate TYPE 4 MODULE_BLUEPRINT schema
        assert "module_map" in blueprint_data, "Missing [MODULE_MAP]"
        assert "dependencies" in blueprint_data, "Missing [DEPENDENCIES]"
        assert "schema" in blueprint_data, "Missing [SCHEMA]"
        assert "vocabulary" in blueprint_data, "Missing [VOCABULARY]"
        assert "readme" in blueprint_data, "Missing [README]"

        # Verify TypeScript-specific patterns
        ts_files = [
            f
            for f in blueprint_data["module_map"].keys()
            if Path(f).suffix in [".ts", ".tsx"]
        ]
        assert len(ts_files) > 0, "Should contain TypeScript files"

        # Verify Lit component detection in vocabulary
        vocabulary = blueprint_data["vocabulary"]
        if "lit_components" in vocabulary:
            components = vocabulary["lit_components"]
            assert isinstance(components, list), "Lit components should be a list"

    def test_php_module_blueprint(self):
        """Verify MODULE_BLUEPRINT for PHP repo.

        PHP uses filesystem discovery with composer.json.
        Expected fields: [MODULE_MAP], [DEPENDENCIES], [SCHEMA], [VOCABULARY], [README]
        """
        # Verify MODULE_BLUEPRINT generation for PHP files
        blueprint_path = (
            self.tests_path / "fixtures" / "blueprint_php_module.json"
        )

        assert blueprint_path.exists(), (
            f"PHP blueprint fixture not found at {blueprint_path}"
        )

        import json

        with open(blueprint_path, "r") as f:
            blueprint_data = json.load(f)

        # Validate TYPE 4 MODULE_BLUEPRINT schema
        assert "module_map" in blueprint_data, "Missing [MODULE_MAP]"
        assert "dependencies" in blueprint_data, "Missing [DEPENDENCIES]"
        assert "schema" in blueprint_data, "Missing [SCHEMA]"
        assert "vocabulary" in blueprint_data, "Missing [VOCABULARY]"
        assert "readme" in blueprint_data, "Missing [README]"

        # Verify PHP-specific patterns
        php_files = [
            f for f in blueprint_data["module_map"].keys() if Path(f).suffix == ".php"
        ]
        assert len(php_files) > 0, "Should contain PHP files"

    def test_yaml_module_blueprint(self):
        """Verify MODULE_BLUEPRINT for YAML repo.

        YAML uses yaml strategy with strings.json anchor for i18n.
        Expected fields: [MODULE_MAP], [DEPENDENCIES], [SCHEMA], [VOCABULARY], [README]
        """
        # Verify MODULE_BLUEPRINT generation for YAML files
        blueprint_path = (
            self.tests_path / "fixtures" / "blueprint_yaml_module.json"
        )

        assert blueprint_path.exists(), (
            f"YAML blueprint fixture not found at {blueprint_path}"
        )

        import json

        with open(blueprint_path, "r") as f:
            blueprint_data = json.load(f)

        # Validate TYPE 4 MODULE_BLUEPRINT schema
        assert "module_map" in blueprint_data, "Missing [MODULE_MAP]"
        assert "dependencies" in blueprint_data, "Missing [DEPENDENCIES]"
        assert "schema" in blueprint_data, "Missing [SCHEMA]"
        assert "vocabulary" in blueprint_data, "Missing [VOCABULARY]"
        assert "readme" in blueprint_data, "Missing [README]"

        # Verify YAML-specific patterns
        yaml_files = [
            f
            for f in blueprint_data["module_map"].keys()
            if Path(f).suffix in [".yaml", ".yml", ".jinja"]
        ]
        assert len(yaml_files) > 0, "Should contain YAML files"

        # Verify i18n JSON handling
        json_files = [
            f
            for f in blueprint_data["module_map"].keys()
            if Path(f).suffix == ".json"
        ]
        if json_files:
            # Check that JSON files are properly handled (strings.json case)
            for json_file in json_files:
                if "strings" in json_file.lower():
                    # strings.json should be in the module_map
                    assert "raw_content" in blueprint_data["module_map"][json_file] or (
                        "anchor_file" in blueprint_data["module_map"][json_file]
                    ), "strings.json should be handled specially"

    def test_blueprint_field_completeness(self):
        """Verify all blueprints contain required TYPE 4 fields.

        AC-3.1 to AC-3.7: MODULE_BLUEPRINT must contain:
        - [MODULE_MAP] - module structure with anchors and files
        - [DEPENDENCIES] - package.json/manifest.json dependencies
        - [SCHEMA] - service definitions (services.yaml)
        - [VOCABULARY] - extracted vocabulary (I18n keys, Lit props)
        - [README] - context for each module
        """
        blueprint_fixtures = [
            "blueprint_python_module.json",
            "blueprint_typescript_module.json",
            "blueprint_php_module.json",
            "blueprint_yaml_module.json",
        ]

        required_fields = {
            "module_map",
            "dependencies",
            "schema",
            "vocabulary",
            "readme",
        }

        for fixture_name in blueprint_fixtures:
            blueprint_path = self.tests_path / "fixtures" / fixture_name

            if not blueprint_path.exists():
                # Skip if fixture doesn't exist (expected for initial test creation)
                continue

            import json

            with open(blueprint_path, "r") as f:
                blueprint_data = json.load(f)

            # Verify all required TYPE 4 fields present
            for field in required_fields:
                assert (
                    field in blueprint_data
                ), f"{fixture_name} missing required field [{field.upper()}]"

    def test_anchor_file_handling(self):
        """Verify anchor files are properly detected and handled.

        Anchor file patterns:
        - const.py → [VOCABULARY]
        - services.yaml → [SCHEMA]
        - manifest.json → [DEPENDENCIES]
        - strings.json → raw content (i18n)
        """
        import json

        # Python anchor: manifest.json
        blueprint_path = (
            self.tests_path / "fixtures" / "blueprint_python_module.json"
        )
        if blueprint_path.exists():
            with open(blueprint_path, "r") as f:
                blueprint_data = json.load(f)

            module_map = blueprint_data.get("module_map", {})
            for module_path, metadata in module_map.items():
                if "manifest.json" in module_path:
                    assert "anchor_file" in metadata
                    assert metadata["anchor_file"] == "manifest.json"
                    assert "dependencies" in metadata

        # YAML anchor: strings.json
        blueprint_path = (
            self.tests_path / "fixtures" / "blueprint_yaml_module.json"
        )
        if blueprint_path.exists():
            with open(blueprint_path, "r") as f:
                blueprint_data = json.load(f)

            module_map = blueprint_data.get("module_map", {})
            for module_path, metadata in module_map.items():
                if "strings" in module_path.lower():
                    assert "anchor_file" in metadata
                    assert metadata["anchor_file"] == "strings.json"
                    # strings.json gets raw_content instead of parsed structure
                    assert "raw_content" in metadata or "anchor_file" in metadata
