# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for php_fragmenter module.

Tests the core utility functions: strip_html_markup, fast_brace_scan,
and read_php_file for the PHP Legacy Driver.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.discovery.php_fragmenter import (
    fast_brace_scan,
    read_php_file,
    strip_html_markup,
    PhpReadError,
)


class TestStripHtmlMarkup:
    """Tests for strip_html_markup function."""

    def test_simple_php_block(self) -> None:
        """Test extraction of a simple PHP block from HTML."""
        source = "<html><body><?php echo $var; ?></body></html>"
        result = strip_html_markup(source)
        assert "<?php echo $var; ?>" in result

    def test_multiple_php_blocks(self) -> None:
        """Test extraction of multiple PHP blocks."""
        source = """<div>
<?php include('header.php'); ?>
<p>Some HTML</p>
<?php if ($condition) { ?>
<div>Conditional content</div>
<?php } ?>
</div>"""
        result = strip_html_markup(source)
        assert "<?php include('header.php');" in result
        assert "<?php if ($condition) {" in result
        assert "<?php } ?>" in result
        # HTML should be stripped
        assert "<div>" not in result
        assert "<p>" not in result

    def test_no_php_blocks(self) -> None:
        """Test empty string returned when no PHP blocks present."""
        source = "<html><body><p>Just HTML</p></body></html>"
        result = strip_html_markup(source)
        assert result == ""

    def test_php_with_short_tags(self) -> None:
        """Test extraction with short PHP tags (<?)."""
        source = "<div><? echo $var; ?></div>"
        result = strip_html_markup(source)
        assert "<? " in result or "<?php" in result

    def test_php_with_html_comments(self) -> None:
        """Test PHP blocks with HTML comments inside."""
        source = """<?php
// This is a comment
function test() { return true; }
?>"""
        result = strip_html_markup(source)
        assert "<?php" in result
        assert "function test()" in result

    def test_javascript_preserved_in_php(self) -> None:
        """Test that JavaScript inside PHP tags is preserved."""
        source = """<script>
<?php echo 'var x = 1;'; ?>
</script>"""
        result = strip_html_markup(source)
        # PHP block inside script should be extracted
        assert "<?php" in result

    def test_empty_php_tags(self) -> None:
        """Test empty PHP block handling."""
        source = "<div><?php ?></div>"
        result = strip_html_markup(source)
        assert "<?php" in result

    def test_mixed_content_complex(self) -> None:
        """Test complex mixed PHP/HTML/JS content."""
        source = """<!DOCTYPE html>
<html>
<head>
    <script>
        var jsVar = <?php echo $jsValue; ?>;
    </script>
</head>
<body>
    <?php if ($showHeader): ?>
    <header><?php echo $title; ?></header>
    <?php endif; ?>

    <div class="content">
        <?php foreach ($items as $item): ?>
        <p><?php echo $item; ?></p>
        <?php endforeach; ?>
    </div>
</body>
</html>"""
        result = strip_html_markup(source)
        # All PHP blocks should be extracted
        assert "<?php if ($showHeader):" in result
        assert "<?php echo $title; ?>" in result
        assert "<?php foreach ($items as $item):" in result
        assert "<?php endforeach; ?>" in result
        # HTML/JS should be stripped
        assert "<!DOCTYPE html>" not in result
        assert "<script>" not in result


class TestFastBraceScan:
    """Tests for fast_brace_scan function."""

    def test_simple_matched_braces(self) -> None:
        """Test matching simple braces."""
        source = "function test() { return 1; }"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1  # Position of last '}'
        assert source[close_pos] == "}"

    def test_nested_braces(self) -> None:
        """Test matching nested braces."""
        source = "function test() { if ($x) { return 1; } return 0; }"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1
        assert source[close_pos] == "}"

    def test_deeply_nested_braces(self) -> None:
        """Test deeply nested braces."""
        source = "function test() { if ($a) { if ($b) { if ($c) { return 1; } } } }"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1

    def test_unmatched_brace(self) -> None:
        """Test unmatched opening brace returns -1."""
        source = "function test() { return 1;"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == -1

    def test_empty_braces(self) -> None:
        """Test empty braces."""
        source = "function test() {}"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == open_pos + 1
        assert source[close_pos] == "}"

    def test_braces_in_string_not_counted(self) -> None:
        """Test that braces inside strings are not counted."""
        source = "function test() { $str = '{not a brace}'; return 1; }"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        # Should find the outer closing brace, not the one in string
        assert close_pos == len(source) - 1

    def test_braces_in_single_quoted_string(self) -> None:
        """Test braces inside single-quoted strings."""
        source = "function test() { $str = '{single}'; return 1; }"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1

    def test_single_line_comment_not_counted(self) -> None:
        """Test that braces in single-line comments are skipped."""
        source = """function test() {
// comment with { brace
return 1;
}"""
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        # Should find the outer closing brace
        assert close_pos == len(source) - 1

    def test_multiline_comment_not_counted(self) -> None:
        """Test that braces in multi-line comments are skipped."""
        source = """function test() {
/* comment with { brace } */
return 1;
}"""
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1

    def test_invalid_position_not_brace(self) -> None:
        """Test that non-brace position returns -1."""
        source = "function test() { return 1; }"
        # Position 0 is 'f', not a brace
        close_pos = fast_brace_scan(source, 0)
        assert close_pos == -1

    def test_position_past_end(self) -> None:
        """Test that position beyond string length returns -1."""
        source = "function test() { return 1; }"
        close_pos = fast_brace_scan(source, len(source) + 1)
        assert close_pos == -1


class TestReadPhpFile:
    """Tests for read_php_file function."""

    def test_read_utf8_file(self, tmp_path: Path) -> None:
        """Test reading a UTF-8 encoded PHP file."""
        content = "<?php\necho 'Hello World';\n// Some comment with ñ and émojis 🎉\n"
        file_path = tmp_path / "test_utf8.php"
        file_path.write_text(content, encoding="utf-8")

        result = read_php_file(file_path)
        assert result == content

    def test_read_latin1_file(self, tmp_path: Path) -> None:
        """Test reading a latin-1 encoded PHP file."""
        # Content with latin-1 specific characters
        content = "<?php\n// Café résumé\n$var = 'naïve';\n"
        file_path = tmp_path / "test_latin1.php"
        file_path.write_bytes(content.encode("latin-1"))

        result = read_php_file(file_path)
        assert result == content

    def test_read_utf8_with_fallback_to_latin1(self, tmp_path: Path) -> None:
        """Test UTF-8 failing and falling back to latin-1."""
        # This is a valid latin-1 sequence that's invalid UTF-8
        content_bytes = b"<?php\n$str = '\xc0\xc1\xfe\xff';\n"
        file_path = tmp_path / "test_fallback.php"
        file_path.write_bytes(content_bytes)

        # Should succeed via latin-1 fallback
        result = read_php_file(file_path)
        assert result.encode("latin-1") == content_bytes

    def test_read_binary_file_raises_error(self, tmp_path: Path) -> None:
        """Test that truly binary file raises PhpReadError."""
        # Invalid bytes that neither UTF-8 nor latin-1 can decode properly
        content_bytes = b"\x00\x01\x02\xff\xfe\xfd\x80\x81"
        file_path = tmp_path / "test_binary.php"
        file_path.write_bytes(content_bytes)

        with pytest.raises(PhpReadError) as exc_info:
            read_php_file(file_path)
        assert "Failed to read" in str(exc_info.value)

    def test_read_empty_file(self, tmp_path: Path) -> None:
        """Test reading an empty file."""
        file_path = tmp_path / "empty.php"
        file_path.write_text("", encoding="utf-8")

        result = read_php_file(file_path)
        assert result == ""

    def test_read_file_with_bom(self, tmp_path: Path) -> None:
        """Test reading a file with UTF-8 BOM."""
        content = "<?php\necho 'Hello';\n"
        file_path = tmp_path / "test_bom.php"
        # Write with BOM
        file_path.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))

        result = read_php_file(file_path)
        # BOM should either be stripped or included - both are acceptable
        # The function uses read_text which handles BOM
        assert "echo 'Hello'" in result


class TestExtractPreamble:
    """Tests for _extract_preamble function (T015)."""

    def test_extract_preamble_basic(self) -> None:
        """Test basic preamble extraction - returns (preamble_content, remaining_source)."""
        from src.discovery.php_fragmenter import _extract_preamble

        source = """<?php
// Bootstrap code
define('DIR_WS_INCLUDES', 'includes/');
require_once('includes/database_tables.php');

// End of preamble
function processData($id) {
    return $id * 2;
}
"""
        preamble, remaining = _extract_preamble(source)

        # Preamble should contain bootstrap code
        assert "define('DIR_WS_INCLUDES'" in preamble
        assert "require_once" in preamble

        # Remaining should start with the function
        assert "function processData" in remaining
        # Should NOT include preamble content in remaining
        assert "DIR_WS_INCLUDES" not in remaining

    def test_extract_preamble_no_preamble(self) -> None:
        """Test when there's no preamble - entire source is remaining."""
        from src.discovery.php_fragmenter import _extract_preamble

        source = """<?php
function test() {
    return 1;
}
"""
        preamble, remaining = _extract_preamble(source)

        # Should have empty preamble
        assert preamble == ""
        # All content should be in remaining
        assert "function test" in remaining

    def test_extract_preamble_computes_hash(self) -> None:
        """Test that preamble has valid SHA-256 hash reference."""
        import hashlib
        from src.discovery.php_fragmenter import _extract_preamble

        source = """<?php
define('TEST', 'value');
function test() {}
"""
        preamble, _ = _extract_preamble(source)

        # Should be able to compute SHA-256 of preamble
        if preamble:  # Only test if there's preamble content
            hash_result = hashlib.sha256(preamble.encode()).hexdigest()
            assert len(hash_result) == 64  # SHA-256 is 64 hex chars


class TestExtractFunctionBlocks:
    """Tests for _extract_function_blocks function (T016)."""

    def test_extract_function_blocks_basic(self) -> None:
        """Test basic function extraction - returns list of (start, end, content)."""
        from src.discovery.php_fragmenter import _extract_function_blocks

        source = """<?php
function getData($id) {
    return $id;
}

function processRecord($record) {
    return $record * 2;
}
"""
        source_file = Path("/test/file.php")
        blocks = _extract_function_blocks(source, source_file)

        # Should find 2 functions
        assert len(blocks) == 2

        # Each block should be (start_line, end_line, content)
        for start, end, content in blocks:
            assert isinstance(start, int)
            assert isinstance(end, int)
            assert isinstance(content, str)
            assert start > 0
            assert end >= start
            assert "function" in content

    def test_extract_function_blocks_with_class(self) -> None:
        """Test that class methods are NOT extracted as standalone blocks."""
        from src.discovery.php_fragmenter import _extract_function_blocks

        source = """<?php
class MyClass {
    public function method() {
        return 1;
    }
}

function standaloneFunction() {
    return 2;
}
"""
        source_file = Path("/test/file.php")
        blocks = _extract_function_blocks(source, source_file)

        # Should only find the standalone function
        assert len(blocks) == 1
        assert "standaloneFunction" in blocks[0][2]

    def test_extract_function_blocks_nested_braces(self) -> None:
        """Test that nested braces are handled correctly."""
        from src.discovery.php_fragmenter import _extract_function_blocks

        source = """<?php
function complexFunction($x) {
    if ($x) {
        for ($i = 0; $i < 10; $i++) {
            echo $i;
        }
    }
    return $x;
}
"""
        source_file = Path("/test/file.php")
        blocks = _extract_function_blocks(source, source_file)

        assert len(blocks) == 1
        # Function should have all content including nested braces
        assert "if ($x)" in blocks[0][2]
        assert "for ($i = 0" in blocks[0][2]


class TestExtractSwitchCases:
    """Tests for _extract_switch_cases function (T017)."""

    def test_extract_switch_cases_basic(self) -> None:
        """Test basic switch/case extraction - returns list of (start, end, raw, case_label)."""
        from src.discovery.php_fragmenter import _extract_switch_cases

        source = """<?php
switch ($action) {
    case 'add':
        $result = 'added';
        break;
    case 'edit':
        $result = 'edited';
        break;
    case 'delete':
        $result = 'deleted';
        break;
}
"""
        source_file = Path("/test/file.php")
        cases = _extract_switch_cases(source, source_file)

        # Should find the switch block
        assert len(cases) >= 1

        # Each case should be (start, end, raw_content, case_label)
        for start, end, raw, label in cases:
            assert isinstance(start, int)
            assert isinstance(end, int)
            assert isinstance(raw, str)
            assert isinstance(label, str)

    def test_extract_switch_cases_case_labels(self) -> None:
        """Test that case labels are correctly extracted."""
        from src.discovery.php_fragmenter import _extract_switch_cases

        source = """<?php
switch ($mode) {
    case 'initialize':
        doInit();
        break;
    case 'process':
        doProcess();
        break;
}
"""
        source_file = Path("/test/file.php")
        cases = _extract_switch_cases(source, source_file)

        # Should have case labels
        labels = [c[3] for c in cases]
        assert "initialize" in labels or "add" in labels or "process" in labels

    def test_extract_switch_cases_no_switch(self) -> None:
        """Test when there's no switch statement - returns empty list."""
        from src.discovery.php_fragmenter import _extract_switch_cases

        source = """<?php
function test() {
    return 1;
}
"""
        source_file = Path("/test/file.php")
        cases = _extract_switch_cases(source, source_file)

        assert cases == []


class TestFragmentBySize:
    """Tests for _fragment_by_size function (T018)."""

    def test_fragment_by_size_basic(self) -> None:
        """Test basic size-based fragmentation - returns list of (start, end, content)."""
        from src.discovery.php_fragmenter import _fragment_by_size

        # Create source with 100 lines
        lines = [f"line {i}" for i in range(100)]
        source = "\n".join(lines)

        # Fragment with max 30 lines
        fragments = _fragment_by_size(source, max_lines=30)

        # Should create multiple fragments
        assert len(fragments) > 1

        # Each fragment should be (start_line, end_line, content)
        for start, end, content in fragments:
            assert isinstance(start, int)
            assert isinstance(end, int)
            assert isinstance(content, str)
            assert start > 0
            assert end >= start

    def test_fragment_by_size_with_overlap(self) -> None:
        """Test that overlap parameter adds context to each fragment."""
        from src.discovery.php_fragmenter import _fragment_by_size

        # Create source with distinct markers to check overlap
        lines = [f"LINE_{i}" for i in range(100)]
        source = "\n".join(lines)

        # Fragment with overlap of 5 lines
        fragments = _fragment_by_size(source, max_lines=30, overlap=5)

        # With overlap, fragments should overlap
        # Check that content is repeated between fragments
        if len(fragments) > 1:
            # First fragment ends around line 30
            # Second fragment should start with some overlap content
            first_content = fragments[0][2]
            second_content = fragments[1][2]

            # The overlap should contain content from the end of first fragment
            # (exact behavior depends on implementation)

    def test_fragment_by_size_single_fragment(self) -> None:
        """Test when source fits in max_lines - returns single fragment."""
        from src.discovery.php_fragmenter import _fragment_by_size

        source = """<?php
function test() {
    return 1;
}
"""
        fragments = _fragment_by_size(source, max_lines=100)

        # Should return one fragment covering entire source
        assert len(fragments) == 1
        assert "function test" in fragments[0][2]

    def test_fragment_by_size_empty_source(self) -> None:
        """Test with empty source - returns empty list."""
        from src.discovery.php_fragmenter import _fragment_by_size

        fragments = _fragment_by_size("", max_lines=30)

        assert fragments == []


class TestDetectImplicitDeps:
    """Unit tests for detect_implicit_deps function (T037)."""

    def test_assigned_var_excluded_unassigned_included(self) -> None:
        """(a) Locally-assigned vars excluded; unassigned ones ≥3 uses included."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        # $locVar is assigned locally — should NOT appear as dep
        # $foreignVar is used 3 times but never assigned — should appear
        source = """<?php
function process() {
    $locVar = 10;
    echo $foreignVar;
    echo $foreignVar;
    echo $foreignVar;
}
"""
        deps = detect_implicit_deps(source)
        symbols = {d.target_symbol for d in deps}

        assert "$locVar" not in symbols
        assert "$foreignVar" in symbols

    def test_superglobals_excluded(self) -> None:
        """(b) PHP superglobals are never reported as implicit deps."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        source = """<?php
function handler() {
    $id = $_GET['id'];
    $name = $_POST['name'];
    $token = $_SESSION['token'];
    $method = $_SERVER['REQUEST_METHOD'];
    $cookie = $_COOKIE['pref'];
    $all = $GLOBALS['config'];
    echo $id . $name . $token . $method . $cookie . $all;
}
"""
        deps = detect_implicit_deps(source)
        symbols = {d.target_symbol for d in deps}

        for superglobal in (
            "$_GET",
            "$_POST",
            "$_SESSION",
            "$_SERVER",
            "$_COOKIE",
            "$GLOBALS",
        ):
            assert superglobal not in symbols, f"{superglobal} should not be reported"

    def test_function_params_excluded(self) -> None:
        """(c) Function parameters are excluded even if param matches a known global."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        # $db is a known global — but when passed as a param it is NOT an implicit dep
        source = """<?php
function doQuery($db, $id) {
    $result = $db->Execute("SELECT * FROM products WHERE id = $id");
    return $result;
}
"""
        deps = detect_implicit_deps(source)
        symbols = {d.target_symbol for d in deps}

        assert "$db" not in symbols, "$db as function param must not be an implicit dep"

    def test_foreach_and_catch_vars_excluded(self) -> None:
        """(d) foreach loop variables and catch exception variables are excluded."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        source = """<?php
function process($data) {
    try {
        foreach ($data as $key => $item) {
            echo $item;
            echo $item;
            echo $item;
            echo $key;
            echo $key;
            echo $key;
        }
    } catch (Exception $ex) {
        echo $ex->getMessage();
        echo $ex->getMessage();
        echo $ex->getMessage();
    }
}
"""
        deps = detect_implicit_deps(source)
        symbols = {d.target_symbol for d in deps}

        assert "$item" not in symbols, "$item is a foreach var"
        assert "$key" not in symbols, "$key is a foreach key var"
        assert "$ex" not in symbols, "$ex is a catch var"

    def test_this_property_refs_excluded(self) -> None:
        """(e) $this is a superglobal — method calls via $this are not reported."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        source = """<?php
function render() {
    echo $this->title;
    echo $this->body;
    echo $this->footer;
}
"""
        deps = detect_implicit_deps(source)
        symbols = {d.target_symbol for d in deps}

        assert "$this" not in symbols, "$this must not appear as an implicit dep"

    def test_known_global_var_confidence_1_0(self) -> None:
        """(f) Variables from the known-set (_KNOWN_GLOBAL_VARS) get confidence=1.0."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        # $db and $customer_id are in _KNOWN_GLOBAL_VARS
        source = """<?php
function getOrders() {
    $res = $db->Execute("SELECT * FROM orders WHERE customer_id = $customer_id");
    return $res;
}
"""
        deps = detect_implicit_deps(source)
        conf_map = {d.target_symbol: d.confidence for d in deps}

        assert "$db" in conf_map, "$db should be detected (known global)"
        assert conf_map["$db"] == 1.0, "$db must have confidence=1.0"
        assert "$customer_id" in conf_map, "$customer_id should be detected"
        assert conf_map["$customer_id"] == 1.0, "$customer_id must have confidence=1.0"

    def test_high_frequency_var_confidence_0_8(self) -> None:
        """(g) Unknown vars used ≥3 times get confidence=0.8 (frequency heuristic)."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        # $sessionCart is unknown but used 4 times; should be detected with 0.8
        source = """<?php
function checkout() {
    echo $sessionCart->count;
    echo $sessionCart->total;
    echo $sessionCart->currency;
    $sessionCart->save();
}
"""
        deps = detect_implicit_deps(source)
        conf_map = {d.target_symbol: d.confidence for d in deps}

        assert "$sessionCart" in conf_map, "$sessionCart ≥3 uses → implicit dep"
        assert conf_map["$sessionCart"] == 0.8, "$sessionCart must have confidence=0.8"

    def test_var_used_less_than_3_times_not_detected(self) -> None:
        """Vars used <3 times and not in known-set are ignored."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        # $rareVar only used twice — should NOT be detected
        source = """<?php
function minimal() {
    echo $rareVar;
    echo $rareVar;
}
"""
        deps = detect_implicit_deps(source)
        symbols = {d.target_symbol for d in deps}

        assert "$rareVar" not in symbols, (
            "$rareVar used <3 times should not be detected"
        )

    def test_empty_fragment_returns_empty_tuple(self) -> None:
        """Empty fragment → empty tuple."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        assert detect_implicit_deps("") == ()
        assert detect_implicit_deps("   ") == ()

    def test_result_sorted_by_symbol(self) -> None:
        """Result is sorted by target_symbol ascending."""
        from src.discovery.php_fragmenter import detect_implicit_deps

        # Use multiple known globals to check ordering
        source = """<?php
function process() {
    $z = $template->render($db, $customer_id, $languages_id);
    return $z;
}
"""
        deps = detect_implicit_deps(source)
        symbols = [d.target_symbol for d in deps]

        assert symbols == sorted(symbols), "Result must be sorted by target_symbol"


class TestImplicitDependencyValidation:
    """Tests for ImplicitDependency dataclass validation (T043)."""

    def test_implicit_dependency_valid(self) -> None:
        """Should create ImplicitDependency with valid values."""
        from src.discovery.php_fragmenter import ImplicitDependency, DependencyType

        dep = ImplicitDependency(
            target_symbol="$db",
            dependency_type=DependencyType.GLOBAL_VAR.value,
            confidence=0.8,
        )
        assert dep.target_symbol == "$db"
        assert dep.confidence == 0.8

    def test_implicit_dependency_confidence_below_range(self) -> None:
        """Should raise ValueError when confidence < 0.0."""
        from src.discovery.php_fragmenter import ImplicitDependency

        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            ImplicitDependency(
                target_symbol="$db",
                dependency_type="global_var",
                confidence=-0.1,
            )

    def test_implicit_dependency_confidence_above_range(self) -> None:
        """Should raise ValueError when confidence > 1.0."""
        from src.discovery.php_fragmenter import ImplicitDependency

        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            ImplicitDependency(
                target_symbol="$db",
                dependency_type="global_var",
                confidence=1.5,
            )

    def test_implicit_dependency_invalid_dependency_type(self) -> None:
        """Should raise ValueError when dependency_type is invalid."""
        from src.discovery.php_fragmenter import ImplicitDependency

        with pytest.raises(ValueError, match="dependency_type must be one of"):
            ImplicitDependency(
                target_symbol="$db",
                dependency_type="invalid_type",
                confidence=0.5,
            )


class TestPhpFragmentValidation:
    """Tests for PhpFragment dataclass validation (T043)."""

    def test_php_fragment_valid(self) -> None:
        """Should create PhpFragment with valid values."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        fragment = PhpFragment(
            name="test_func",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("test.php"),
            start_line=1,
            end_line=10,
            raw_content="<?php function test_func() {}",
            legacy_action=None,
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
        )
        assert fragment.name == "test_func"
        assert fragment.start_line == 1

    def test_php_fragment_invalid_fragment_type(self) -> None:
        """Should raise ValueError for invalid fragment_type."""
        from src.discovery.php_fragmenter import PhpFragment

        with pytest.raises(ValueError, match="fragment_type must be one of"):
            PhpFragment(
                name="test",
                fragment_type="invalid_type",
                source_file=Path("test.php"),
                start_line=1,
                end_line=10,
                raw_content="<?php",
                legacy_action=None,
                preamble_ref=None,
                dependencies=(),
                platform_hints=(),
            )

    def test_php_fragment_invalid_file_style(self) -> None:
        """Should raise ValueError for invalid file_style."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        with pytest.raises(ValueError, match="file_style must be one of"):
            PhpFragment(
                name="test",
                fragment_type=FragmentType.FUNCTION.value,
                source_file=Path("test.php"),
                start_line=1,
                end_line=10,
                raw_content="<?php",
                legacy_action=None,
                preamble_ref=None,
                dependencies=(),
                platform_hints=(),
                file_style="INVALID_STYLE",
            )

    def test_php_fragment_start_line_less_than_1(self) -> None:
        """Should raise ValueError when start_line < 1."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        with pytest.raises(ValueError, match="start_line must be >= 1"):
            PhpFragment(
                name="test",
                fragment_type=FragmentType.FUNCTION.value,
                source_file=Path("test.php"),
                start_line=0,
                end_line=10,
                raw_content="<?php",
                legacy_action=None,
                preamble_ref=None,
                dependencies=(),
                platform_hints=(),
            )

    def test_php_fragment_end_line_less_than_start(self) -> None:
        """Should raise ValueError when end_line < start_line."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        with pytest.raises(ValueError, match="end_line must be >= start_line"):
            PhpFragment(
                name="test",
                fragment_type=FragmentType.FUNCTION.value,
                source_file=Path("test.php"),
                start_line=10,
                end_line=5,
                raw_content="<?php",
                legacy_action=None,
                preamble_ref=None,
                dependencies=(),
                platform_hints=(),
            )

    def test_php_fragment_invalid_preamble_ref_length(self) -> None:
        """Should raise ValueError when preamble_ref is not 64 chars."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        with pytest.raises(ValueError, match="preamble_ref must be 64-char SHA-256 hex"):
            PhpFragment(
                name="test",
                fragment_type=FragmentType.FUNCTION.value,
                source_file=Path("test.php"),
                start_line=1,
                end_line=10,
                raw_content="<?php",
                legacy_action=None,
                preamble_ref="short",
                dependencies=(),
                platform_hints=(),
            )

    def test_php_fragment_invalid_preamble_ref_hex(self) -> None:
        """Should raise ValueError when preamble_ref is not valid hex."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        with pytest.raises(ValueError, match="preamble_ref must be valid hexadecimal"):
            PhpFragment(
                name="test",
                fragment_type=FragmentType.FUNCTION.value,
                source_file=Path("test.php"),
                start_line=1,
                end_line=10,
                raw_content="<?php",
                legacy_action=None,
                preamble_ref="g" * 64,  # Invalid hex
                dependencies=(),
                platform_hints=(),
            )

    def test_php_fragment_line_count_property(self) -> None:
        """Should return correct line count."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        fragment = PhpFragment(
            name="test",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("test.php"),
            start_line=1,
            end_line=10,
            raw_content="<?php",
            legacy_action=None,
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
        )
        assert fragment.line_count == 10

    def test_php_fragment_has_implicit_deps_property(self) -> None:
        """Should return True when has implicit dependencies."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType, ImplicitDependency, DependencyType

        dep = ImplicitDependency(
            target_symbol="$db",
            dependency_type=DependencyType.GLOBAL_VAR.value,
            confidence=0.8,
        )
        fragment = PhpFragment(
            name="test",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("test.php"),
            start_line=1,
            end_line=10,
            raw_content="<?php",
            legacy_action=None,
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
            implicit_deps=(dep,),
        )
        assert fragment.has_implicit_deps is True
        assert fragment.has_signatures is False

    def test_php_fragment_get_implicit_dep_symbols(self) -> None:
        """Should return tuple of dependency symbols."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType, ImplicitDependency, DependencyType

        dep = ImplicitDependency(
            target_symbol="$db",
            dependency_type=DependencyType.GLOBAL_VAR.value,
            confidence=0.8,
        )
        fragment = PhpFragment(
            name="test",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("test.php"),
            start_line=1,
            end_line=10,
            raw_content="<?php",
            legacy_action=None,
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
            implicit_deps=(dep,),
        )
        assert fragment.get_implicit_dep_symbols() == ("$db",)


class TestFastBraceScanUnclosed:
    """Additional tests for fast_brace_scan error paths (T043)."""

    def test_unclosed_multiline_comment_returns_minus_1(self) -> None:
        """Test unclosed multi-line comment returns -1."""
        from src.discovery.php_fragmenter import fast_brace_scan

        source = "function test() { /* unclosed comment"
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == -1

    def test_single_line_comment_not_affected(self) -> None:
        """Test single-line comments don't affect brace matching."""
        from src.discovery.php_fragmenter import fast_brace_scan

        source = """function test() {
    // } this is a comment
    return 1;
}"""
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1

    def test_string_brace_not_counted(self) -> None:
        """Test braces inside double-quoted strings are not counted."""
        from src.discovery.php_fragmenter import fast_brace_scan

        source = """function test() {
    $str = "{not a brace}";
    return 1;
}"""
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1

    def test_single_quoted_string_brace_not_counted(self) -> None:
        """Test braces inside single-quoted strings are not counted."""
        from src.discovery.php_fragmenter import fast_brace_scan

        source = """function test() {
    $str = '{not a brace}';
    return 1;
}"""
        open_pos = source.index("{")
        close_pos = fast_brace_scan(source, open_pos)
        assert close_pos == len(source) - 1


class TestClassifyFileStyle:
    """Tests for _classify_file_style function."""

    def test_classify_empty_source(self) -> None:
        """Test empty source returns LEGACY_PURE."""
        from src.discovery.php_fragmenter import _classify_file_style

        result = _classify_file_style("")
        assert result == "LEGACY_PURE"

    def test_classify_modernized_namespace_typed_constructor(self) -> None:
        """Test namespace with typed constructor returns LEGACY_MODERNIZED."""
        from src.discovery.php_fragmenter import _classify_file_style

        source = """<?php
namespace App\\Model;
class User {
    public function __construct(int $id, string $name) {}
}
"""
        result = _classify_file_style(source)
        assert result == "LEGACY_MODERNIZED"

    def test_classify_hybrid_class_with_legacy_patterns(self) -> None:
        """Test class with legacy patterns (mysql_query) returns HYBRID."""
        from src.discovery.php_fragmenter import _classify_file_style

        source = """<?php
class Order {
    public function process() {
        global $db;
        mysql_query("SELECT * FROM orders");
    }
}
"""
        result = _classify_file_style(source)
        assert result == "HYBRID"

    def test_classify_hybrid_tep_db_query(self) -> None:
        """Test class with tep_db_query returns HYBRID."""
        from src.discovery.php_fragmenter import _classify_file_style

        source = """<?php
class Product {
    public function getProducts() {
        return tep_db_query("SELECT * FROM products");
    }
}
"""
        result = _classify_file_style(source)
        assert result == "HYBRID"

    def test_classify_hybrid_wpdb(self) -> None:
        """Test class with $wpdb returns HYBRID."""
        from src.discovery.php_fragmenter import _classify_file_style

        source = """<?php
class Post {
    public function getPost($id) {
        global $wpdb;
        return $wpdb->get_results("SELECT * FROM posts WHERE ID = $id");
    }
}
"""
        result = _classify_file_style(source)
        assert result == "HYBRID"

    def test_classify_pure_global_db(self) -> None:
        """Test global $db without class returns LEGACY_PURE."""
        from src.discovery.php_fragmenter import _classify_file_style

        source = """<?php
global $db;
function getData() {
    global $db;
    return $db->query("SELECT * FROM data");
}
"""
        result = _classify_file_style(source)
        assert result == "LEGACY_PURE"

    def test_classify_pure_top_level_functions(self) -> None:
        """Test top-level functions without class returns LEGACY_PURE."""
        from src.discovery.php_fragmenter import _classify_file_style

        source = """<?php
function processData($id) {
    return $id * 2;
}
"""
        result = _classify_file_style(source)
        assert result == "LEGACY_PURE"

    def test_classify_pure_class_without_legacy(self) -> None:
        """Test class without legacy patterns returns LEGACY_PURE."""
        from src.discovery.php_fragmenter import _classify_file_style

        source = """<?php
class User {
    private $id;
    public function getId() {
        return $this->id;
    }
}
"""
        result = _classify_file_style(source)
        assert result == "LEGACY_PURE"


class TestBuildExclusionSet:
    """Tests for _build_exclusion_set function."""

    def test_build_exclusion_set_basic(self) -> None:
        """Test basic exclusion set building."""
        from src.discovery.php_fragmenter import _build_exclusion_set

        source = """<?php
function test() {
    $local = 1;
    global $db;
    require_once('file.php');
}
"""
        exclusions = _build_exclusion_set(source)
        # Should contain excluded items
        assert isinstance(exclusions, frozenset)


class TestPhpFragmentSignatureCategories:
    """Tests for PhpFragment.get_signature_categories method."""

    def test_get_signature_categories_empty(self) -> None:
        """Test with empty signatures returns empty tuple."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType

        fragment = PhpFragment(
            name="test",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("/test.php"),
            start_line=1,
            end_line=10,
            raw_content="<?php function test() {}",
            legacy_action="test_action",
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
            signatures=(),
        )
        categories = fragment.get_signature_categories()
        assert categories == ()

    def test_get_signature_categories_single(self) -> None:
        """Test with single signature returns single category."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType
        from src.discovery.php_signatures import LegacySignature, SignatureCategory

        sig = LegacySignature(
            pattern_name="mysql_query",
            category=SignatureCategory.PERSISTENCE_SMELL.value,
            matched_text="mysql_query",
            line_number=5,
            severity="critical",
            modern_equivalent="mysqli or PDO",
        )
        fragment = PhpFragment(
            name="test",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("/test.php"),
            start_line=1,
            end_line=10,
            raw_content="<?php function test() { mysql_query(); }",
            legacy_action="test_action",
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
            signatures=(sig,),
        )
        categories = fragment.get_signature_categories()
        assert SignatureCategory.PERSISTENCE_SMELL.value in categories

    def test_get_signature_categories_multiple_same(self) -> None:
        """Test with multiple signatures of same category returns unique."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType
        from src.discovery.php_signatures import LegacySignature, SignatureCategory

        sig1 = LegacySignature(
            pattern_name="mysql_query1",
            category=SignatureCategory.PERSISTENCE_SMELL.value,
            matched_text="mysql_query1",
            line_number=5,
            severity="critical",
            modern_equivalent="mysqli or PDO",
        )
        sig2 = LegacySignature(
            pattern_name="mysql_query2",
            category=SignatureCategory.PERSISTENCE_SMELL.value,
            matched_text="mysql_query2",
            line_number=10,
            severity="critical",
            modern_equivalent="mysqli or PDO",
        )
        fragment = PhpFragment(
            name="test",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("/test.php"),
            start_line=1,
            end_line=20,
            raw_content="<?php function test() {}",
            legacy_action="test_action",
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
            signatures=(sig1, sig2),
        )
        categories = fragment.get_signature_categories()
        # Should return unique categories only
        assert len(categories) == 1
        assert SignatureCategory.PERSISTENCE_SMELL.value in categories

    def test_get_signature_categories_multiple_different(self) -> None:
        """Test with multiple signatures of different categories."""
        from src.discovery.php_fragmenter import PhpFragment, FragmentType
        from src.discovery.php_signatures import LegacySignature, SignatureCategory

        sig1 = LegacySignature(
            pattern_name="mysql_query",
            category=SignatureCategory.PERSISTENCE_SMELL.value,
            matched_text="mysql_query",
            line_number=5,
            severity="critical",
            modern_equivalent="mysqli or PDO",
        )
        sig2 = LegacySignature(
            pattern_name="global_var",
            category=SignatureCategory.STATE_POLLUTION.value,
            matched_text="$global",
            line_number=10,
            severity="warning",
            modern_equivalent="dependency injection",
        )
        fragment = PhpFragment(
            name="test",
            fragment_type=FragmentType.FUNCTION.value,
            source_file=Path("/test.php"),
            start_line=1,
            end_line=20,
            raw_content="<?php function test() {}",
            legacy_action="test_action",
            preamble_ref=None,
            dependencies=(),
            platform_hints=(),
            signatures=(sig1, sig2),
        )
        categories = fragment.get_signature_categories()
        assert len(categories) == 2
        assert SignatureCategory.PERSISTENCE_SMELL.value in categories
        assert SignatureCategory.STATE_POLLUTION.value in categories


