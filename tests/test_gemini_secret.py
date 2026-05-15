from types import SimpleNamespace

import pytest

from gemini_secret import _secret_resource_name, resolve_gemini_api_key


class DummyConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_resolve_gemini_api_key_uses_local_env_fallback(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY_SECRET_REF", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "local-key")

    assert resolve_gemini_api_key(DummyConfig()) == "local-key"


def test_resolve_gemini_api_key_reads_secret_manager(monkeypatch):
    calls = []

    class FakeSecretClient:
        def access_secret_version(self, request):
            calls.append(request["name"])
            payload = SimpleNamespace(data=b"secret-key\n")
            return SimpleNamespace(payload=payload)

    monkeypatch.setenv("GOOGLE_API_KEY_SECRET_REF", "gemini-api-key")
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setattr("gemini_secret._secret_manager_client", lambda: FakeSecretClient())

    assert resolve_gemini_api_key(DummyConfig()) == "secret-key"
    assert calls == ["projects/test-project/secrets/gemini-api-key/versions/latest"]


@pytest.mark.parametrize(
    ("secret_ref", "expected"),
    [
        (
            "projects/my-project/secrets/gemini-api-key",
            "projects/my-project/secrets/gemini-api-key/versions/latest",
        ),
        (
            "projects/my-project/secrets/gemini-api-key/versions/2",
            "projects/my-project/secrets/gemini-api-key/versions/2",
        ),
    ],
)
def test_secret_resource_name_accepts_full_secret_refs(secret_ref, expected):
    assert _secret_resource_name(secret_ref, "latest", None) == expected


def test_secret_resource_name_requires_project_for_short_secret_refs():
    with pytest.raises(EnvironmentError, match="no Google Cloud project id"):
        _secret_resource_name("gemini-api-key", "latest", None)
