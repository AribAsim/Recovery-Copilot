import pytest
import httpx
import json
from app.core.config import settings
from app.services.llm_client import generate_message
from app.services.llm_classifier import classify

def test_fallback_chain_client(monkeypatch):
    # Enable all providers in settings temporarily
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "openrouter_key")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "nvidia_key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "groq_key")

    call_history = []

    # Mock httpx.post to fail for OpenRouter and NVIDIA, but succeed for Groq
    def mock_post(url, headers, json, timeout=10.0):
        call_history.append(url)
        if "openrouter.ai" in url:
            raise httpx.ConnectError("OpenRouter failed")
        elif "nvidia.com" in url:
            raise httpx.ConnectError("Nvidia NIM failed")
        elif "groq.com" in url:
            class MockResponse:
                def raise_for_status(self):
                    pass
                def json(self):
                    return {
                        "choices": [{
                            "message": {
                                "content": "Recovery text from Groq!"
                            }
                        }]
                    }
            return MockResponse()
        raise ValueError(f"Unexpected URL: {url}")

    monkeypatch.setattr(httpx, "post", mock_post)

    msg = generate_message("retry_in_24h", 100.0)

    # Check that we tried OpenRouter, Nvidia NIM, and finally got success from Groq
    assert msg == "Recovery text from Groq!"
    assert len(call_history) == 3
    assert "openrouter.ai" in call_history[0]
    assert "nvidia.com" in call_history[1]
    assert "groq.com" in call_history[2]


def test_fallback_chain_classifier(monkeypatch):
    # Enable OpenRouter and Nvidia keys in settings
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "openrouter_key")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "nvidia_key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")

    call_history = []

    # Mock httpx.post to fail for OpenRouter but succeed for NVIDIA
    def mock_post(url, headers, json, timeout=10.0):
        call_history.append(url)
        if "openrouter.ai" in url:
            raise httpx.HTTPStatusError("OpenRouter rate limit", request=None, response=None)
        elif "nvidia.com" in url:
            class MockResponse:
                def raise_for_status(self):
                    pass
                def json(self):
                    return {
                        "choices": [{
                            "message": {
                                "content": '{"category": "insufficient_funds", "confidence": 0.85, "reasoning": "Nvidia NIM reasoned"}'
                            }
                        }]
                    }
            return MockResponse()
        raise ValueError(f"Unexpected URL: {url}")

    monkeypatch.setattr(httpx, "post", mock_post)

    res = classify("Declined due to low balance")

    assert res["diagnosis"] == "insufficient_funds"
    assert res["confidence"] == 0.85
    assert res["mode_used"] == "llm"
    assert len(call_history) == 2
    assert "openrouter.ai" in call_history[0]
    assert "nvidia.com" in call_history[1]
