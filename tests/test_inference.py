#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/inference.py.

Covers:
- BaseInferenceClient is an ABC (cannot be instantiated directly)
- VLLMClient.generate() builds correct HTTP payload and returns content
- VLLMClient.generate() with system_prompt and json_mode flags
- VLLMClient.generate_with_retry() exponential-backoff behaviour
- VLLMClient.generate_with_retry() raises RuntimeError after exhausting retries
- GeminiClient raises ImportError when SDK is unavailable
- GeminiClient raises EnvironmentError when GOOGLE_API_KEY is missing
- InferenceRouter._resolve_backend() — 'auto' resolution logic
- InferenceRouter.professor() and .student() return cached client on second call
- InferenceRouter cache isolation between professor() and student()
"""

from __future__ import annotations

import os
from typing import Any, Dict
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from src.audit.inference import (
    BaseInferenceClient,
    InferenceRouter,
    VLLMClient,
    _GEMINI_AVAILABLE,
)

# ---------------------------------------------------------------------------
# Base class contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBaseInferenceClient:
    def test_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseInferenceClient()  # type: ignore[abstract]

    def test_generate_is_abstract(self) -> None:
        assert getattr(BaseInferenceClient.generate, "__isabstractmethod__", False)

    def test_generate_with_retry_is_concrete_template_method(self) -> None:
        """generate_with_retry must be a concrete Template Method, not abstract.
        Subclasses inherit retry + exponential backoff without reimplementing it.
        """
        assert not getattr(
            BaseInferenceClient.generate_with_retry, "__isabstractmethod__", False
        )


# ---------------------------------------------------------------------------
# _backend_name class attribute contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBackendNameContract:
    """Each concrete client must declare _backend_name for log/error messages."""

    def test_vllm_client_backend_name(self) -> None:
        assert VLLMClient._backend_name == "vLLM"

    def test_gemini_client_backend_name(self) -> None:
        from src.audit.inference import GeminiClient

        assert GeminiClient._backend_name == "Gemini"

    def test_base_class_backend_name_is_fallback(self) -> None:
        # Default value exists but subclasses are expected to override it.
        assert BaseInferenceClient._backend_name == "unknown"


# ---------------------------------------------------------------------------
# VLLMClient — generate()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVLLMClientGenerate:
    def _mock_response(self, content: str = "response text") -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {"choices": [{"message": {"content": content}}]}
        resp.raise_for_status.return_value = None
        return resp

    def test_returns_content_from_response(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        with patch(
            "requests.post", return_value=self._mock_response("hello")
        ) as mock_post:
            result = client.generate("say hello")
        assert result == "hello"

    def test_posts_to_correct_endpoint(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        with patch("requests.post", return_value=self._mock_response()) as mock_post:
            client.generate("prompt")
        args, kwargs = mock_post.call_args
        assert "http://localhost:8000/v1/chat/completions" in args

    def test_includes_user_message_in_payload(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        with patch("requests.post", return_value=self._mock_response()) as mock_post:
            client.generate("my prompt")
        _, kwargs = mock_post.call_args
        messages = kwargs["json"]["messages"]
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) == 1
        assert user_msgs[0]["content"] == "my prompt"

    def test_adds_system_prompt_when_provided(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        with patch("requests.post", return_value=self._mock_response()) as mock_post:
            client.generate("prompt", system_prompt="Be concise.")
        _, kwargs = mock_post.call_args
        messages = kwargs["json"]["messages"]
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) == 1
        assert system_msgs[0]["content"] == "Be concise."

    def test_omits_system_message_when_none(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        with patch("requests.post", return_value=self._mock_response()) as mock_post:
            client.generate("prompt", system_prompt=None)
        _, kwargs = mock_post.call_args
        messages = kwargs["json"]["messages"]
        assert all(m["role"] != "system" for m in messages)

    def test_json_mode_sets_response_format(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        with patch(
            "requests.post", return_value=self._mock_response("{}")
        ) as mock_post:
            client.generate("prompt", json_mode=True)
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["response_format"] == {"type": "json_object"}

    def test_no_response_format_without_json_mode(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        with patch("requests.post", return_value=self._mock_response()) as mock_post:
            client.generate("prompt", json_mode=False)
        _, kwargs = mock_post.call_args
        assert "response_format" not in kwargs["json"]

    def test_trailing_slash_stripped_from_api_url(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1/", model="m")
        with patch("requests.post", return_value=self._mock_response()) as mock_post:
            client.generate("p")
        args, _ = mock_post.call_args
        assert not args[0].startswith("http://localhost:8000/v1//")

    def test_propagates_http_error(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="test-model")
        bad_resp = MagicMock()
        bad_resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch("requests.post", return_value=bad_resp):
            with pytest.raises(requests.HTTPError):
                client.generate("prompt")


# ---------------------------------------------------------------------------
# VLLMClient — generate_with_retry()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVLLMClientRetry:
    def test_succeeds_on_first_attempt(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="m")
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        with patch("requests.post", return_value=resp) as mock_post:
            with patch("time.sleep") as mock_sleep:
                result = client.generate_with_retry("p", retries=3)
        assert result == "ok"
        mock_sleep.assert_not_called()

    def test_retries_on_transient_error_and_eventually_succeeds(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="m")
        good_resp = MagicMock()
        good_resp.raise_for_status.return_value = None
        good_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        side_effects = [requests.ConnectionError("timeout"), good_resp]
        with patch("requests.post", side_effect=side_effects):
            with patch("time.sleep"):
                result = client.generate_with_retry("p", retries=3, retry_delay=0.01)
        assert result == "ok"

    def test_raises_runtime_error_after_exhausting_retries(self) -> None:
        client = VLLMClient(api_url="http://localhost:8000/v1", model="m")
        with patch("requests.post", side_effect=requests.ConnectionError("down")):
            with patch("time.sleep"):
                with pytest.raises(
                    RuntimeError, match="vLLM generation failed after 3 attempts"
                ):
                    client.generate_with_retry("p", retries=3, retry_delay=0.01)

    def test_exponential_backoff_delays(self) -> None:
        """Sleep delays must grow: delay*2^0, delay*2^1, delay*2^2."""
        client = VLLMClient(api_url="http://localhost:8000/v1", model="m")
        with patch("requests.post", side_effect=Exception("fail")):
            with patch("time.sleep") as mock_sleep:
                with pytest.raises(RuntimeError):
                    client.generate_with_retry("p", retries=3, retry_delay=1.0)
        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0, 4.0]


# ---------------------------------------------------------------------------
# GeminiClient — availability guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGeminiClientGuards:
    def test_raises_import_error_when_sdk_unavailable(self) -> None:
        # Ensure we can exercise the ImportError path even if the SDK is
        # installed in the environment by monkeypatching the module globals.
        import src.audit.inference as inf
        from unittest.mock import patch as _patch

        # Simulate SDK absence
        inf._GEMINI_AVAILABLE = False
        inf._genai = None
        inf._genai_types = None
        from src.audit.inference import GeminiClient

        with pytest.raises(ImportError, match="google-genai SDK"):
            GeminiClient()

    def test_raises_environment_error_when_api_key_missing(self) -> None:
        # Simulate SDK presence and ensure missing API key raises EnvironmentError
        import src.audit.inference as inf

        inf._GEMINI_AVAILABLE = True
        inf._genai = MagicMock()
        inf._genai_types = MagicMock()
        from src.audit.inference import GeminiClient

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            with pytest.raises(EnvironmentError, match="GOOGLE_API_KEY"):
                GeminiClient()


# ---------------------------------------------------------------------------
# InferenceRouter — _resolve_backend()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInferenceRouterResolveBackend:
    def test_auto_resolves_to_gemini_when_available_and_key_set(self) -> None:
        with patch("src.audit.inference._GEMINI_AVAILABLE", True):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = InferenceRouter._resolve_backend("auto")
        assert result == "gemini"

    def test_auto_resolves_to_vllm_when_gemini_unavailable(self) -> None:
        with patch("src.audit.inference._GEMINI_AVAILABLE", False):
            result = InferenceRouter._resolve_backend("auto")
        assert result == "vllm"

    def test_auto_resolves_to_vllm_when_no_api_key(self) -> None:
        with patch("src.audit.inference._GEMINI_AVAILABLE", True):
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("GOOGLE_API_KEY", None)
                result = InferenceRouter._resolve_backend("auto")
        assert result == "vllm"

    def test_explicit_gemini_passes_through(self) -> None:
        assert InferenceRouter._resolve_backend("gemini") == "gemini"

    def test_explicit_vllm_passes_through(self) -> None:
        assert InferenceRouter._resolve_backend("vllm") == "vllm"


# ---------------------------------------------------------------------------
# InferenceRouter — caching
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInferenceRouterCaching:
    def test_professor_returns_same_client_on_repeated_calls(self) -> None:
        router = InferenceRouter()
        with patch(
            "src.audit.inference.VLLMClient", return_value=MagicMock()
        ) as MockVLLM:
            c1 = router.professor(backend="vllm", api_url="http://x/v1", vllm_model="m")
            c2 = router.professor(backend="vllm", api_url="http://x/v1", vllm_model="m")
        # Client must be instantiated only once
        assert MockVLLM.call_count == 1
        assert c1 is c2

    def test_student_returns_same_client_on_repeated_calls(self) -> None:
        router = InferenceRouter()
        with patch(
            "src.audit.inference.VLLMClient", return_value=MagicMock()
        ) as MockVLLM:
            c1 = router.student(backend="vllm", api_url="http://x/v1", model="m")
            c2 = router.student(backend="vllm", api_url="http://x/v1", model="m")
        assert MockVLLM.call_count == 1
        assert c1 is c2

    def test_professor_and_student_are_independent_cache_entries(self) -> None:
        router = InferenceRouter()
        sentinel_a = MagicMock(name="professor_client")
        sentinel_b = MagicMock(name="student_client")
        with patch(
            "src.audit.inference.VLLMClient",
            side_effect=[sentinel_a, sentinel_b],
        ):
            prof = router.professor(
                backend="vllm", api_url="http://x/v1", vllm_model="m"
            )
            stu = router.student(backend="vllm", api_url="http://x/v1", model="m")
        assert prof is not stu


# ---------------------------------------------------------------------------
# InferenceRouter — Gemini backend paths (covers lines 297, 314)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInferenceRouterGeminiPaths:
    """Test InferenceRouter when it resolves a Gemini client explicitly."""

    def test_professor_creates_gemini_client_when_backend_is_gemini(self) -> None:
        router = InferenceRouter()
        mock_instance = MagicMock(spec=BaseInferenceClient)
        with patch(
            "src.audit.inference.GeminiClient", return_value=mock_instance
        ) as MockGemini:
            client = router.professor(backend="gemini", gemini_model="gemini-2.5-flash")
        MockGemini.assert_called_once_with(model="gemini-2.5-flash")
        assert client is mock_instance

    def test_student_creates_gemini_client_when_backend_is_gemini(self) -> None:
        router = InferenceRouter()
        mock_instance = MagicMock(spec=BaseInferenceClient)
        with patch(
            "src.audit.inference.GeminiClient", return_value=mock_instance
        ) as MockGemini:
            client = router.student(backend="gemini", gemini_model="gemini-2.5-flash")
        MockGemini.assert_called_once_with(model="gemini-2.5-flash")
        assert client is mock_instance

    def test_professor_gemini_client_is_cached(self) -> None:
        router = InferenceRouter()
        mock_instance = MagicMock(spec=BaseInferenceClient)
        with patch(
            "src.audit.inference.GeminiClient", return_value=mock_instance
        ) as MockGemini:
            c1 = router.professor(backend="gemini", gemini_model="gemini-2.5-flash")
            c2 = router.professor(backend="gemini", gemini_model="gemini-2.5-flash")
        MockGemini.assert_called_once()
        assert c1 is c2


# ---------------------------------------------------------------------------
# GeminiClient — with full mock (covers lines 118-119, 130-145, 158-176)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGeminiClientWithMock:
    """Test GeminiClient body paths with fully mocked SDK internals.

    All tests patch ``_genai.Client`` and ``_genai_types.GenerateContentConfig``
    so they run without a real API key and without network I/O.
    """

    def _make_client(
        self,
        mock_genai: Any,
        mock_types: Any,
        mock_response_text: str = "mock response",
    ) -> tuple[Any, MagicMock]:
        """Build a GeminiClient with mocked internals; return (client, genai_client_mock)."""
        from src.audit.inference import GeminiClient

        genai_client_mock = MagicMock()
        response_mock = MagicMock()
        response_mock.text = mock_response_text
        genai_client_mock.models.generate_content.return_value = response_mock
        mock_genai.Client.return_value = genai_client_mock

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-ci-key"}):
            client = GeminiClient(model="gemini-test")
        return client, genai_client_mock

    def test_init_creates_sdk_client_with_api_key(self) -> None:
        from src.audit.inference import GeminiClient

        with patch("src.audit.inference._genai") as mock_genai:
            with patch("src.audit.inference._genai_types"):
                mock_genai.Client.return_value = MagicMock()
                with patch.dict(os.environ, {"GOOGLE_API_KEY": "my-key"}):
                    c = GeminiClient(model="gemini-test")
        mock_genai.Client.assert_called_once_with(api_key="my-key")
        assert c._model == "gemini-test"

    def test_generate_returns_response_text(self) -> None:
        with patch("src.audit.inference._genai") as mock_genai:
            with patch("src.audit.inference._genai_types"):
                client, _ = self._make_client(mock_genai, None)
                result = client.generate("hello world")
        assert result == "mock response"

    def test_generate_returns_empty_string_when_text_is_none(self) -> None:
        with patch("src.audit.inference._genai") as mock_genai:
            with patch("src.audit.inference._genai_types"):
                client, genai_mock = self._make_client(mock_genai, None, "x")
                genai_mock.models.generate_content.return_value.text = None
                result = client.generate("prompt")
        assert result == ""

    def test_generate_passes_system_instruction_when_provided(self) -> None:
        with patch("src.audit.inference._genai") as mock_genai:
            with patch("src.audit.inference._genai_types") as mock_types:
                client, _ = self._make_client(mock_genai, mock_types)
                client.generate("prompt", system_prompt="Be helpful.")
        _, kwargs = mock_types.GenerateContentConfig.call_args
        assert kwargs.get("system_instruction") == "Be helpful."

    def test_generate_sets_response_mime_type_in_json_mode(self) -> None:
        with patch("src.audit.inference._genai") as mock_genai:
            with patch("src.audit.inference._genai_types") as mock_types:
                client, _ = self._make_client(mock_genai, mock_types)
                client.generate("prompt", json_mode=True)
        _, kwargs = mock_types.GenerateContentConfig.call_args
        assert kwargs.get("response_mime_type") == "application/json"

    def test_generate_with_retry_succeeds_after_one_failure(self) -> None:
        with patch("src.audit.inference._genai") as mock_genai:
            with patch("src.audit.inference._genai_types"):
                client, genai_mock = self._make_client(mock_genai, None)
                good = MagicMock()
                good.text = "success"
                genai_mock.models.generate_content.side_effect = [
                    Exception("rate limit"),
                    good,
                ]
                with patch("time.sleep"):
                    result = client.generate_with_retry(
                        "prompt", retries=3, retry_delay=0.01
                    )
        assert result == "success"

    def test_generate_with_retry_raises_after_exhaustion(self) -> None:
        with patch("src.audit.inference._genai") as mock_genai:
            with patch("src.audit.inference._genai_types"):
                client, genai_mock = self._make_client(mock_genai, None)
                genai_mock.models.generate_content.side_effect = Exception(
                    "always fails"
                )
                with patch("time.sleep"):
                    with pytest.raises(RuntimeError, match="Gemini generation failed"):
                        client.generate_with_retry(
                            "prompt", retries=2, retry_delay=0.01
                        )
