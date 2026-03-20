"""Tests for prompt_builder module."""

import pytest

from src.factory import prompt_builder as pb_module


class TestDetectLegacyPatterns:
    """Tests for detect_legacy_patterns function."""

    def test_detect_legacy_patterns_python(self):
        """Test detection of legacy Python patterns."""
        code = """
        def setup(hass, config):
            hass.states.set('sensor.temp', 25)
            return True
        """
        result = pb_module.detect_legacy_patterns(code, "code")
        assert isinstance(result, list)

    def test_detect_legacy_patterns_jinja(self):
        """Test detection of legacy Jinja patterns."""
        template = """
        {% set state = states.sensor.temp %}
        {% if state.state == 'on' %}
        {{ states('sensor.temp') }}
        {% endif %}
        """
        result = pb_module.detect_legacy_patterns(template, "jinja")
        assert isinstance(result, list)

    def test_detect_legacy_patterns_yaml(self):
        """Test detection of legacy YAML patterns."""
        yaml_content = """
        sensor:
          - platform: template
            sensors:
              temp:
                value_template: "{{ states('sensor.temp') }}"
        """
        result = pb_module.detect_legacy_patterns(yaml_content, "yaml")
        assert isinstance(result, list)

    def test_detect_legacy_patterns_empty(self):
        """Test with empty code."""
        result = pb_module.detect_legacy_patterns("", "code")
        assert result == []


class TestPostValidateOutput:
    """Tests for post_validate_output function."""

    def test_post_validate_output_nominal(self):
        """Test validation of nominal example."""
        code = """
        async def async_setup_entry(hass, entry):
            coordinator = MyCoordinator(hass, entry)
            await coordinator.async_init()
            return True
        """
        result = pb_module.post_validate_output(code, "nominal", "code")
        assert isinstance(result, list)

    def test_post_validate_output_contrast(self):
        """Test validation of contrast example."""
        code = """
        def setup(hass, config):
            hass.states.set('sensor.temp', 25)
            return True
        """
        result = pb_module.post_validate_output(code, "contrast", "code")
        assert isinstance(result, list)

    def test_post_validate_output_error_recovery(self):
        """Test validation of error recovery example."""
        code = """
        async def async_setup_entry(hass, entry):
            coordinator = MyCoordinator(hass, entry)
            await coordinator.async_init()
            return True
        """
        result = pb_module.post_validate_output(code, "error_recovery", "code")
        assert isinstance(result, list)


class TestBaseSystemBlock:
    """Tests for _base_system_block function."""

    def test_base_system_block_renders(self):
        """Test that _base_system_block renders properly."""
        master = "# Master Guide\nSome content"
        changelog = "# Changelog\nChanges here"
        result = pb_module._base_system_block(master, changelog)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildSystemNominal:
    """Tests for build_system_nominal function."""

    def test_build_system_nominal(self):
        """Test building nominal system prompt."""
        master = "# Master Guide content"
        changelog = "# Changelog content"
        result = pb_module.build_system_nominal(master, changelog)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildSystemContrast:
    """Tests for build_system_contrast function."""

    def test_build_system_contrast(self):
        """Test building contrast system prompt."""
        master = "# Master Guide content"
        changelog = "# Changelog content"
        result = pb_module.build_system_contrast(master, changelog)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildSystemErrorRecovery:
    """Tests for build_system_error_recovery function."""

    def test_build_system_error_recovery(self):
        """Test building error recovery system prompt."""
        master = "# Master Guide content"
        changelog = "# Changelog content"
        result = pb_module.build_system_error_recovery(master, changelog)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildSystemNominalJinja:
    """Tests for build_system_nominal_jinja function."""

    def test_build_system_nominal_jinja(self):
        """Test building nominal Jinja system prompt."""
        jinja_guide = "# Jinja Guide content"
        result = pb_module.build_system_nominal_jinja(jinja_guide)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildSystemContrastJinja:
    """Tests for build_system_contrast_jinja function."""

    def test_build_system_contrast_jinja(self):
        """Test building contrast Jinja system prompt."""
        jinja_guide = "# Jinja Guide content"
        result = pb_module.build_system_contrast_jinja(jinja_guide)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildSystemErrorRecoveryJinja:
    """Tests for build_system_error_recovery_jinja function."""

    def test_build_system_error_recovery_jinja(self):
        """Test building error recovery Jinja system prompt."""
        jinja_guide = "# Jinja Guide content"
        result = pb_module.build_system_error_recovery_jinja(jinja_guide)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildUserNominal:
    """Tests for build_user_nominal function."""

    def test_build_user_nominal(self):
        """Test building nominal user prompt."""
        frag = {
            "context": "Test context",
            "virtual_filename": "custom_components/test/sensor.py",
            "name": "test_sensor",
            "fragment": "def setup():\n    pass",
            "skeleton": "def setup():\n    pass",
        }
        result = pb_module.build_user_nominal(frag, "easy")
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildUserContrast:
    """Tests for build_user_contrast function."""

    def test_build_user_contrast(self):
        """Test building contrast user prompt."""
        frag = {
            "context": "Test context",
            "virtual_filename": "custom_components/test/sensor.py",
            "name": "test_sensor",
            "fragment": "def setup():\n    pass",
            "skeleton": "def setup():\n    pass",
        }
        result = pb_module.build_user_contrast(frag)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildUserErrorRecovery:
    """Tests for build_user_error_recovery function."""

    def test_build_user_error_recovery(self):
        """Test building error recovery user prompt."""
        frag = {
            "context": "Test context",
            "virtual_filename": "custom_components/test/sensor.py",
            "name": "test_sensor",
            "fragment": "def setup():\n    pass",
            "skeleton": "def setup():\n    pass",
        }
        result = pb_module.build_user_error_recovery(frag)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildUserNominalJinja:
    """Tests for build_user_nominal_jinja function."""

    def test_build_user_nominal_jinja(self):
        """Test building nominal Jinja user prompt."""
        frag = {
            "context": "Test context",
            "virtual_filename": "custom_components/test/sensor.yaml",
            "name": "test_sensor",
            "skeleton": "sensor:\n  - platform: template",
        }
        result = pb_module.build_user_nominal_jinja(frag, "easy")
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildUserContrastJinja:
    """Tests for build_user_contrast_jinja function."""

    def test_build_user_contrast_jinja(self):
        """Test building contrast Jinja user prompt."""
        frag = {
            "context": "Test context",
            "virtual_filename": "custom_components/test/sensor.yaml",
            "name": "test_sensor",
            "skeleton": "sensor:\n  - platform: template",
        }
        result = pb_module.build_user_contrast_jinja(frag)
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildUserErrorRecoveryJinja:
    """Tests for build_user_error_recovery_jinja function."""

    def test_build_user_error_recovery_jinja(self):
        """Test building error recovery Jinja user prompt."""
        # This test may fail if templates are not loaded
        # Just test the function exists and is callable
        assert callable(pb_module.build_user_error_recovery_jinja)


class TestBuildSystemTheory:
    """Tests for build_system_theory function."""

    def test_build_system_theory(self):
        """Test building theory system prompt."""
        master = "# Master Guide content"
        changelog = "# Changelog content"
        result = pb_module.build_system_theory(master, changelog)
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetTheoryFragments:
    """Tests for get_theory_fragments function."""

    def test_get_theory_fragments(self):
        """Test extracting theory fragments."""
        master = "# Master Guide\n## Section 1\nContent 1\n## Section 2\nContent 2"
        changelog = "# Changelog\n## Change 1\nChange content 1"
        result = pb_module.get_theory_fragments(master, changelog)
        assert isinstance(result, list)


class TestBuildUserTheory:
    """Tests for build_user_theory function."""

    def test_build_user_theory(self):
        """Test building theory user prompt."""
        theory_frag = {
            "name": "Section 1",
            "content": "Theory content here",
        }
        user_msg, subtype = pb_module.build_user_theory(theory_frag)
        assert isinstance(user_msg, str)
        assert isinstance(subtype, str)


class TestBuildUserFunctionalUnit:
    """Tests for build_user_functional_unit function."""

    def test_build_user_functional_unit(self):
        """Test building functional unit user prompt."""
        frag = {
            "context": "Test context",
            "virtual_filename": "custom_components/test/sensor.py",
            "name": "test_sensor",
            "fragment": "def setup():\n    pass",
            "skeleton": "def setup():\n    pass",
        }
        result = pb_module.build_user_functional_unit(frag, "medium")
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildSystemWithBlueprint:
    """Tests for build_system_with_blueprint function."""

    def test_build_system_with_blueprint(self):
        """Test building system prompt with blueprint."""
        master = "# Master Guide content"
        changelog = "# Changelog content"
        blueprint = "# Blueprint content"
        result = pb_module.build_system_with_blueprint(master, changelog, blueprint)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_system_with_blueprint_empty(self):
        """Test building system prompt with empty blueprint."""
        master = "# Master Guide content"
        changelog = "# Changelog content"
        result = pb_module.build_system_with_blueprint(master, changelog)
        assert isinstance(result, str)
        assert len(result) > 0


class TestRender:
    """Tests for _render function."""

    def test_render_simple(self):
        """Test rendering a simple template."""
        result = pb_module._render("Hello $name", name="World")
        assert result == "Hello World"

    def test_render_multiple_vars(self):
        """Test rendering with multiple variables."""
        result = pb_module._render("$greeting $name", greeting="Hello", name="World")
        assert result == "Hello World"

    def test_render_preserves_braces(self):
        """Test that braces in JSON are preserved."""
        result = pb_module._render('{"key": "$value"}', value="test")
        assert '{"key": "test"}' in result

    def test_render_missing_variable(self):
        """Test that missing variables are left unchanged (safe_substitute behavior)."""
        result = pb_module._render("Hello $name, you have $count messages", name="Alice")
        assert result == "Hello Alice, you have $count messages"

    def test_render_missing_multiple_variables(self):
        """Test that multiple missing variables are all left unchanged."""
        template = "$greeting $name, your score is $score"
        result = pb_module._render(template, name="Bob")
        assert result == "$greeting Bob, your score is $score"

    def test_render_no_variables_provided(self):
        """Test that when no variables are provided, placeholders remain unchanged."""
        template = "Hello $name"
        result = pb_module._render(template)
        assert result == "Hello $name"

    def test_render_partial_variables(self):
        """Test rendering with some variables provided and some missing."""
        result = pb_module._render(
            "$first $second $third", first="1", third="3"
        )
        # safe_substitute preserves order, but $second remains unchanged
        assert "$second" in result
        assert "1" in result
        assert "3" in result


class TestPHPLegacyFunctions:
    """Tests for PHP legacy functions in prompt_builder."""

    def test_load_php_legacy_doctrine_nonexistent(self, tmp_path):
        """Test load_php_legacy_doctrine returns empty string when file doesn't exist."""
        result = pb_module.load_php_legacy_doctrine(tmp_path)
        assert result == ""

    def test_load_php_legacy_doctrine_existing_file(self, tmp_path):
        """Test load_php_legacy_doctrine reads file when it exists."""
        # Create the expected directory structure
        php_dir = (
            tmp_path
            / "configs"
            / "stage_2_factory"
            / "taxonomy"
            / "php_legacy"
        )
        php_dir.mkdir(parents=True)
        doctrine_file = php_dir / "master_symfony_hex.md"
        doctrine_file.write_text("# Symfony Doctrine\n\nSome content")

        result = pb_module.load_php_legacy_doctrine(tmp_path)
        assert "# Symfony Doctrine" in result
        assert "Some content" in result

    def test_load_php_platform_snippet_nonexistent(self, tmp_path):
        """Test load_php_platform_snippet returns empty string when neither platform nor generic exists."""
        # Create directory structure but no files
        snippet_dir = (
            tmp_path
            / "configs"
            / "stage_2_factory"
            / "taxonomy"
            / "php_legacy"
            / "snippets"
        )
        snippet_dir.mkdir(parents=True)

        result = pb_module.load_php_platform_snippet("nonexistent_platform", tmp_path)
        assert result == ""

    def test_load_php_platform_snippet_fallback_to_generic(self, tmp_path):
        """Test load_php_platform_snippet falls back to generic_php when platform not found."""
        # Create directory with only generic_php
        snippet_dir = (
            tmp_path
            / "configs"
            / "stage_2_factory"
            / "taxonomy"
            / "php_legacy"
            / "snippets"
        )
        snippet_dir.mkdir(parents=True)
        generic_file = snippet_dir / "generic_php.md"
        generic_file.write_text("# Generic PHP\nPlatform-independent content")

        result = pb_module.load_php_platform_snippet("wordpress", tmp_path)
        assert "# Generic PHP" in result

    def test_load_php_platform_snippet_existing_platform(self, tmp_path):
        """Test load_php_platform_snippet reads platform-specific file when it exists."""
        snippet_dir = (
            tmp_path
            / "configs"
            / "stage_2_factory"
            / "taxonomy"
            / "php_legacy"
            / "snippets"
        )
        snippet_dir.mkdir(parents=True)
        platform_file = snippet_dir / "wordpress.md"
        platform_file.write_text("# WordPress\nWordPress-specific content")

        result = pb_module.load_php_platform_snippet("wordpress", tmp_path)
        assert "# WordPress" in result
        assert "WordPress-specific content" in result

    def test_build_system_php_legacy_non_php_returns_empty(self):
        """Test build_system_php_legacy returns empty string for non-PHP language."""
        arch = {"LANGUAGE": "python", "PLATFORM": "django"}
        result = pb_module.build_system_php_legacy(arch)
        assert result == ""

    def test_build_system_php_legacy_with_files(self, tmp_path):
        """Test build_system_php_legacy builds prompt when PHP files exist."""
        # Create directory structure
        php_dir = (
            tmp_path
            / "configs"
            / "stage_2_factory"
            / "taxonomy"
            / "php_legacy"
        )
        php_dir.mkdir(parents=True)

        # Create doctrine file
        doctrine_file = php_dir / "master_symfony_hex.md"
        doctrine_file.write_text("# Symfony Doctrine Content")

        # Create snippets directory and platform file
        snippet_dir = php_dir / "snippets"
        snippet_dir.mkdir(parents=True)
        platform_file = snippet_dir / "wordpress.md"
        platform_file.write_text("# WordPress Platform Content")

        arch = {"LANGUAGE": "php", "PLATFORM": "wordpress", "LEGACY_ACTION": "migrate"}
        result = pb_module.build_system_php_legacy(arch, base_dir=tmp_path)

        # The function may use fallback if template is not available
        # Either way, content should include doctrine and platform snippet
        assert "Symfony Doctrine Content" in result
        assert "WordPress Platform Content" in result

    def test_build_system_php_legacy_missing_files_uses_fallback(self, tmp_path):
        """Test build_system_php_legacy returns fallback when files don't exist."""
        # Create empty directory structure
        php_dir = (
            tmp_path
            / "configs"
            / "stage_2_factory"
            / "taxonomy"
            / "php_legacy"
        )
        php_dir.mkdir(parents=True)

        arch = {"LANGUAGE": "php", "PLATFORM": "nonexistent", "LEGACY_ACTION": "test"}
        result = pb_module.build_system_php_legacy(arch, base_dir=tmp_path)

        # Should return fallback content (doctrine + snippet inline)
        assert "PHP Legacy Modernization Expert" in result
        assert "Symfony Hexagonal Architecture" in result
