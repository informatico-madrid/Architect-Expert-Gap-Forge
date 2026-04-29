#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for anchor dataset providers (VLLM, OpenAI, Gemini)."""

from __future__ import annotations

import json
from unittest import mock

import pytest

from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord
from infrastructure.anchor_dataset.anchor_providers import (
    PROVIDER_MAP,
    GeminiProvider,
    OpenAIProvider,
    VLLMProvider,
    get_provider,
)
from infrastructure.anchor_dataset.errors import ConfigurationError
from tests.factories import build_anchor_record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_record_dict() -> dict:
    """Return a plain dict that round-trips through AnchorRecord."""
    r = build_anchor_record()
    return r.model_dump()


def _valid_json_response(record: dict | None = None) -> dict:
    """Build a mock LLM JSON response body."""
    if record is None:
        record = _valid_record_dict()
    return {
        "choices": [{"message": {"content": json.dumps(record)}}],
    }


def _make_mock_response(json_body: dict) -> mock.Mock:
    resp = mock.Mock()
    resp.json.return_value = json_body
    resp.raise_for_status = mock.Mock()
    return resp


# ---------------------------------------------------------------------------
# VLLMProvider — name
# ---------------------------------------------------------------------------


class TestVLLMProviderName:
    def test_name_returns_vllm(self):
        assert VLLMProvider().name == "vllm"

    def test_name_with_custom_url(self):
        assert VLLMProvider(vllm_url="http://x:8000").name == "vllm"


# ---------------------------------------------------------------------------
# VLLMProvider — successful generation
# ---------------------------------------------------------------------------


class TestVLLMProviderGenerate:
    def test_returns_anchor_record_on_valid_json(self):
        provider = VLLMProvider()
        mock_resp = _make_mock_response(_valid_json_response())
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert isinstance(result, AnchorRecord)
        assert result.id == "anchor_001_00"

    def test_auth_fallback_when_env_missing(self, monkeypatch):
        monkeypatch.delenv("VLLM_API_KEY", raising=False)
        provider = VLLMProvider()
        mock_resp = _make_mock_response(_valid_json_response())
        with mock.patch("requests.post", return_value=mock_resp) as post_fn:
            provider.generate("sys", "user")
        auth = post_fn.call_args[1]["headers"]["Authorization"]
        assert auth == "Bearer sk-master-bunker-2026"

    def test_auth_uses_env_key_when_present(self, monkeypatch):
        monkeypatch.setenv("VLLM_API_KEY", "my-secret-key")
        provider = VLLMProvider()
        mock_resp = _make_mock_response(_valid_json_response())
        with mock.patch("requests.post", return_value=mock_resp) as post_fn:
            provider.generate("sys", "user")
        auth = post_fn.call_args[1]["headers"]["Authorization"]
        assert auth == "Bearer my-secret-key"

    def test_send_correct_payload_structure(self):
        provider = VLLMProvider(model="my-model")
        mock_resp = _make_mock_response(_valid_json_response())
        with mock.patch("requests.post", return_value=mock_resp) as post_fn:
            provider.generate("sys prompt", "user prompt")
        call_args = post_fn.call_args[1]
        payload = call_args["json"]
        assert payload["model"] == "my-model"
        assert payload["response_format"] == {"type": "json_object"}
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"

    def test_custom_url_used(self):
        provider = VLLMProvider(vllm_url="http://custom:9000/v1/chat")
        mock_resp = _make_mock_response(_valid_json_response())
        with mock.patch("requests.post", return_value=mock_resp) as post_fn:
            provider.generate("sys", "user")
        assert post_fn.call_args[0][0] == "http://custom:9000/v1/chat"


# ---------------------------------------------------------------------------
# VLLMProvider — failure modes
# ---------------------------------------------------------------------------


class TestVLLMProviderFailures:
    def test_none_on_json_parse_error(self):
        """Malformed content string -> None."""
        provider = VLLMProvider()
        bad_body = {"choices": [{"message": {"content": "not json"}}]}
        mock_resp = _make_mock_response(bad_body)
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_none_on_missing_choices_key(self):
        provider = VLLMProvider()
        bad_body = {"data": "no choices"}
        mock_resp = _make_mock_response(bad_body)
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_none_on_connection_error(self):
        import requests as req

        provider = VLLMProvider()
        with mock.patch(
            "requests.post",
            side_effect=req.exceptions.ConnectionError("fail"),
        ):
            result = provider.generate("sys", "user")
        assert result is None

    def test_retries_on_connection_error_then_returns_none(self):
        """Should retry MAX_RETRIES (3) times, then return None."""
        import requests as req

        provider = VLLMProvider()
        with mock.patch(
            "requests.post",
            side_effect=req.exceptions.ConnectionError("fail"),
        ) as post_fn:
            result = provider.generate("sys", "user")
        assert post_fn.call_count == provider.MAX_RETRIES
        assert result is None

    def test_retries_on_timeout_then_returns_none(self):
        import requests as req

        provider = VLLMProvider()
        with mock.patch(
            "requests.post",
            side_effect=req.exceptions.Timeout("timed out"),
        ) as post_fn:
            result = provider.generate("sys", "user")
        assert post_fn.call_count == provider.MAX_RETRIES
        assert result is None

    def test_none_on_http_error(self):
        provider = VLLMProvider()
        mock_resp = mock.Mock()
        mock_resp.raise_for_status.side_effect = Exception("400 bad")
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None


# ---------------------------------------------------------------------------
# OpenAIProvider — name
# ---------------------------------------------------------------------------


class TestOpenAIProviderName:
    def test_name_returns_openai(self):
        assert OpenAIProvider().name == "openai"

    def test_name_with_custom_model(self):
        assert OpenAIProvider(model="gpt-3.5-turbo").name == "openai"


# ---------------------------------------------------------------------------
# OpenAIProvider — successful generation
# ---------------------------------------------------------------------------


class TestOpenAIProviderGenerate:
    def test_returns_anchor_record_on_valid_json(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = OpenAIProvider()
        mock_resp = mock.Mock()
        mock_resp.json.return_value = _valid_json_response()
        mock_resp.raise_for_status = mock.Mock()

        mock_client = mock.Mock()
        mock_client.__enter__ = mock.Mock(return_value=mock_client)
        mock_client.__exit__ = mock.Mock(return_value=False)
        mock_client.post = mock.Mock(return_value=mock_resp)

        with mock.patch("httpx.Client", return_value=mock_client):
            result = provider.generate("sys", "user")
        assert isinstance(result, AnchorRecord)
        assert result.id == "anchor_001_00"

    def test_none_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = OpenAIProvider().generate("sys", "user")
        assert result is None

    def test_http_error_captured(self, monkeypatch):
        import httpx as hx

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = OpenAIProvider()
        mock_resp = mock.Mock()
        mock_resp.raise_for_status.side_effect = hx.HTTPError("500")
        mock_client = mock.Mock()
        mock_client.__enter__ = mock.Mock(return_value=mock_client)
        mock_client.__exit__ = mock.Mock(return_value=False)
        mock_client.post = mock.Mock(return_value=mock_resp)
        with mock.patch("httpx.Client", return_value=mock_client):
            result = provider.generate("sys", "user")
        assert result is None


# ---------------------------------------------------------------------------
# OpenAIProvider — failure modes
# ---------------------------------------------------------------------------


class TestOpenAIProviderFailures:
    def test_bad_json_content_returns_none(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = OpenAIProvider()
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "bad"}}]}
        mock_resp.raise_for_status = mock.Mock()
        mock_client = mock.Mock()
        mock_client.__enter__ = mock.Mock(return_value=mock_client)
        mock_client.__exit__ = mock.Mock(return_value=False)
        mock_client.post = mock.Mock(return_value=mock_resp)
        with mock.patch("httpx.Client", return_value=mock_client):
            result = provider.generate("sys", "user")
        assert result is None

    def test_retries_on_http_error(self, monkeypatch):
        import httpx as hx

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = OpenAIProvider()
        mock_resp = mock.Mock()
        mock_resp.raise_for_status.side_effect = hx.HTTPError("fail")
        mock_client = mock.Mock()
        mock_client.__enter__ = mock.Mock(return_value=mock_client)
        mock_client.__exit__ = mock.Mock(return_value=False)
        mock_client.post = mock.Mock(return_value=mock_resp)
        with mock.patch("httpx.Client", return_value=mock_client) as client_fn:
            provider.generate("sys", "user")
        assert client_fn.call_count == 3


# ---------------------------------------------------------------------------
# GeminiProvider — name
# ---------------------------------------------------------------------------


class TestGeminiProviderName:
    def test_name_returns_gemini(self):
        assert GeminiProvider().name == "gemini"

    def test_name_with_custom_model(self):
        assert GeminiProvider(model="gemini-1.5-pro").name == "gemini"


# ---------------------------------------------------------------------------
# GeminiProvider — successful generation
# ---------------------------------------------------------------------------


class TestGeminiProviderGenerate:
    def test_returns_anchor_record_on_valid_json(self, monkeypatch):
        """GeminiProvider returns AnchorRecord when the SDK returns valid JSON.

        Uses monkeypatch.setattr to replace the genai.Client constructor
        within the generate() method's scope.
        """
        monkeypatch.setenv("GOOGLE_API_KEY", "gk-test")
        provider = GeminiProvider()

        mock_response = mock.Mock()
        mock_response.text = json.dumps(_valid_record_dict())

        mock_client_instance = mock.Mock()
        mock_client_instance.models.generate_content.return_value = mock_response

        monkeypatch.setattr(
            "google.genai.Client",
            mock.Mock(return_value=mock_client_instance),
        )

        result = provider.generate("sys", "user")
        assert isinstance(result, AnchorRecord)
        assert result.id == "anchor_001_00"

    def test_none_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        result = GeminiProvider().generate("sys", "user")
        assert result is None


# ---------------------------------------------------------------------------
# GeminiProvider — failure modes
# ---------------------------------------------------------------------------


class TestGeminiProviderFailures:
    def test_none_when_sdk_not_installed(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with mock.patch.dict("sys.modules", {"google.genai": None}):
            result = GeminiProvider().generate("sys", "user")
        assert result is None

    def test_api_error_captured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "gk-test")
        provider = GeminiProvider()

        mock_client_instance = mock.Mock()
        # Use the real genai.errors.APIError since the provider catches it
        import google.genai as real_genai

        mock_client_instance.models.generate_content.side_effect = (
            real_genai.errors.APIError(429, {"error": "rate limited"})
        )

        monkeypatch.setattr(
            "google.genai.Client",
            mock.Mock(return_value=mock_client_instance),
        )

        result = provider.generate("sys", "user")
        assert result is None


# ---------------------------------------------------------------------------
# PROVIDER_MAP
# ---------------------------------------------------------------------------


class TestProviderMap:
    def test_contains_expected_keys(self):
        assert set(PROVIDER_MAP.keys()) == {"vllm", "openai", "gemini"}

    def test_values_are_classes(self):
        assert PROVIDER_MAP["vllm"] is VLLMProvider
        assert PROVIDER_MAP["openai"] is OpenAIProvider
        assert PROVIDER_MAP["gemini"] is GeminiProvider


# ---------------------------------------------------------------------------
# get_provider factory
# ---------------------------------------------------------------------------


class TestGetProvider:
    def test_returns_vllm(self):
        assert get_provider("vllm").name == "vllm"

    def test_returns_openai(self):
        assert get_provider("openai").name == "openai"

    def test_returns_gemini(self):
        assert get_provider("gemini").name == "gemini"

    def test_raises_on_unknown_provider(self):
        with pytest.raises(ConfigurationError, match="Unknown provider: foobar"):
            get_provider("foobar")

    def test_raises_on_unknown_provider_lists_available(self):
        with pytest.raises(ConfigurationError, match="Available:.*vllm"):
            get_provider("baz")
