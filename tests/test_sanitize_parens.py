"""Regression tests: preservation of inline backticked code with parentheses.

These cases were observed in forensic traces where inline backticks
containing parentheses (e.g. `requests.get(url)`) were removed by the
sanitizer. The test must fail on the buggy implementation and pass
after the sanitizer is adjusted to preserve code-like backtick spans.
"""

from src.curation.backtracking_rewriter import _sanitize_generated_reasoning


def test_preserve_backticked_call_with_parentheses() -> None:
    text = "Usa `requests.get(url)` para realizar la petición HTTP."
    result = _sanitize_generated_reasoning(text)

    assert "`requests.get(url)`" in result, "Inline backticked call was deleted"


def test_preserve_backticked_call_with_commas_and_args() -> None:
    text = (
        "Invoca `discovery_flow.async_create_flow(hass, DOMAIN, data)` "
        "desde el flujo de descubrimiento."
    )
    result = _sanitize_generated_reasoning(text)

    assert "`discovery_flow.async_create_flow(hass, DOMAIN, data)`" in result, (
        "Complex inline identifier with parentheses and commas was deleted"
    )
